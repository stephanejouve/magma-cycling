"""Tests for _mcp/handlers/handoff.py — context-handoff-save and resume."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling._mcp.handlers.handoff import (
    _latest_unconsumed,
    _write_snapshot,
    handle_context_handoff_resume,
    handle_context_handoff_save,
)
from magma_cycling.models.handoff import HandoffSnapshot


@pytest.fixture
def handoff_dir(tmp_path: Path) -> Path:
    """Empty handoff dir under tmp."""
    d = tmp_path / "handoff"
    d.mkdir()
    return d


@pytest.fixture
def mock_config(handoff_dir: Path):
    """Patch get_data_config() so handoff_dir points to tmp."""
    cfg = MagicMock()
    cfg.handoff_dir = handoff_dir
    with patch("magma_cycling.config.get_data_config", return_value=cfg):
        yield cfg


def _tc_payload(result):
    """Unwrap the single TextContent result into a dict."""
    assert len(result) == 1
    return json.loads(result[0].text)


class TestWriteSnapshot:
    def test_writes_json_file_with_timestamp_name(self, handoff_dir: Path):
        snap = HandoffSnapshot(created_at=datetime(2026, 4, 19, 23, 30))
        path = _write_snapshot(snap, handoff_dir)
        assert path.name == "2026-04-19-2330.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["created_at"] == "2026-04-19T23:30:00"

    def test_same_minute_collision_falls_back_to_second_precision(self, handoff_dir: Path):
        ts = datetime(2026, 4, 19, 23, 30, 15)
        snap1 = HandoffSnapshot(created_at=ts)
        snap2 = HandoffSnapshot(created_at=ts)
        p1 = _write_snapshot(snap1, handoff_dir)
        p2 = _write_snapshot(snap2, handoff_dir)
        assert p1 != p2
        assert p1.name == "2026-04-19-2330.json"
        assert p2.name == "2026-04-19-233015.json"


class TestLatestUnconsumed:
    def test_empty_dir_returns_none(self, handoff_dir: Path):
        assert _latest_unconsumed(handoff_dir) is None

    def test_missing_dir_returns_none(self, tmp_path: Path):
        assert _latest_unconsumed(tmp_path / "does_not_exist") is None

    def test_picks_latest_by_created_at(self, handoff_dir: Path):
        older = HandoffSnapshot(created_at=datetime(2026, 4, 19, 8, 0))
        newer = HandoffSnapshot(created_at=datetime(2026, 4, 19, 20, 0))
        _write_snapshot(older, handoff_dir)
        _write_snapshot(newer, handoff_dir)
        found = _latest_unconsumed(handoff_dir)
        assert found is not None
        _, snap = found
        assert snap.created_at == newer.created_at

    def test_skips_consumed_snapshots(self, handoff_dir: Path):
        consumed = HandoffSnapshot(created_at=datetime(2026, 4, 19, 20, 0), consumed=True)
        fresh = HandoffSnapshot(created_at=datetime(2026, 4, 19, 8, 0))
        _write_snapshot(consumed, handoff_dir)
        _write_snapshot(fresh, handoff_dir)
        found = _latest_unconsumed(handoff_dir)
        assert found is not None
        _, snap = found
        assert snap.created_at == fresh.created_at

    def test_skips_invalid_json_file(self, handoff_dir: Path):
        (handoff_dir / "garbage.json").write_text("{ not valid")
        good = HandoffSnapshot(created_at=datetime(2026, 4, 19, 20, 0))
        _write_snapshot(good, handoff_dir)
        found = _latest_unconsumed(handoff_dir)
        assert found is not None


@pytest.mark.asyncio
class TestHandleSave:
    async def test_save_minimal(self, mock_config, handoff_dir: Path):
        result = await handle_context_handoff_save({})
        payload = _tc_payload(result)
        assert payload["status"] == "saved"
        assert Path(payload["path"]).exists()
        assert payload["summary"]["decisions_pending"] == 0
        assert payload["summary"]["has_user_mood"] is False

    async def test_save_full(self, mock_config, handoff_dir: Path):
        result = await handle_context_handoff_save(
            {
                "decisions_pending": ["a", "b"],
                "open_questions": ["q1"],
                "user_mood": "fatigué",
                "next_actions": ["do X"],
                "referenced_files": ["/tmp/file.png"],
            }
        )
        payload = _tc_payload(result)
        assert payload["summary"] == {
            "decisions_pending": 2,
            "open_questions": 1,
            "next_actions": 1,
            "referenced_files": 1,
            "has_user_mood": True,
        }
        data = json.loads(Path(payload["path"]).read_text())
        assert data["decisions_pending"] == ["a", "b"]
        assert data["user_mood"] == "fatigué"
        assert data["consumed"] is False

    async def test_save_handles_none_fields(self, mock_config, handoff_dir: Path):
        result = await handle_context_handoff_save({"decisions_pending": None, "user_mood": None})
        payload = _tc_payload(result)
        assert payload["status"] == "saved"


@pytest.mark.asyncio
class TestHandleResume:
    async def test_resume_empty(self, mock_config, handoff_dir: Path):
        result = await handle_context_handoff_resume({})
        payload = _tc_payload(result)
        assert payload["status"] == "empty"
        assert payload["snapshot"] is None

    async def test_resume_marks_consumed(self, mock_config, handoff_dir: Path):
        snap = HandoffSnapshot(
            created_at=datetime(2026, 4, 19, 20, 0),
            decisions_pending=["choice A"],
        )
        path = _write_snapshot(snap, handoff_dir)
        result = await handle_context_handoff_resume({})
        payload = _tc_payload(result)
        assert payload["status"] == "resumed"
        assert payload["snapshot"]["decisions_pending"] == ["choice A"]
        assert payload["snapshot"]["consumed"] is True
        # Disk reflects consumed=True
        on_disk = json.loads(path.read_text())
        assert on_disk["consumed"] is True

    async def test_resume_peek_does_not_consume(self, mock_config, handoff_dir: Path):
        snap = HandoffSnapshot(created_at=datetime(2026, 4, 19, 20, 0))
        path = _write_snapshot(snap, handoff_dir)
        result = await handle_context_handoff_resume({"peek": True})
        payload = _tc_payload(result)
        assert payload["status"] == "peeked"
        on_disk = json.loads(path.read_text())
        assert on_disk["consumed"] is False

    async def test_resume_then_resume_returns_empty(self, mock_config, handoff_dir: Path):
        snap = HandoffSnapshot(created_at=datetime(2026, 4, 19, 20, 0))
        _write_snapshot(snap, handoff_dir)
        first = _tc_payload(await handle_context_handoff_resume({}))
        second = _tc_payload(await handle_context_handoff_resume({}))
        assert first["status"] == "resumed"
        assert second["status"] == "empty"

    async def test_resume_picks_latest_of_multiple(self, mock_config, handoff_dir: Path):
        older = HandoffSnapshot(created_at=datetime(2026, 4, 19, 8, 0), user_mood="matin")
        newer = HandoffSnapshot(created_at=datetime(2026, 4, 19, 20, 0), user_mood="soir")
        _write_snapshot(older, handoff_dir)
        _write_snapshot(newer, handoff_dir)
        result = await handle_context_handoff_resume({})
        payload = _tc_payload(result)
        assert payload["snapshot"]["user_mood"] == "soir"


@pytest.mark.asyncio
async def test_save_resume_roundtrip(mock_config, handoff_dir: Path):
    """End-to-end: save a snapshot, resume returns exactly what was saved."""
    save = await handle_context_handoff_save(
        {
            "decisions_pending": ["Sweet Spot ou Tempo mercredi ?"],
            "user_mood": "bien reposé",
            "next_actions": ["trancher mardi soir"],
        }
    )
    saved = _tc_payload(save)
    assert saved["status"] == "saved"

    resumed = _tc_payload(await handle_context_handoff_resume({}))
    snap = resumed["snapshot"]
    assert snap["decisions_pending"] == ["Sweet Spot ou Tempo mercredi ?"]
    assert snap["user_mood"] == "bien reposé"
    assert snap["next_actions"] == ["trancher mardi soir"]


@pytest.mark.asyncio
async def test_multiple_saves_preserve_history(mock_config, handoff_dir: Path):
    """Each save creates a new file; old files remain on disk."""
    with patch("magma_cycling._mcp.handlers.handoff.datetime") as mock_dt:
        # first save at 08:00
        mock_dt.now.return_value = datetime(2026, 4, 19, 8, 0)
        await handle_context_handoff_save({"user_mood": "A"})
        # second save at 20:00
        mock_dt.now.return_value = datetime(2026, 4, 19, 20, 0)
        await handle_context_handoff_save({"user_mood": "B"})

    files = list(handoff_dir.glob("*.json"))
    assert len(files) == 2
    # The latest-resume semantics already tested above — just confirm both persist.
    moods = sorted(json.loads(f.read_text())["user_mood"] for f in files)
    assert moods == ["A", "B"]
