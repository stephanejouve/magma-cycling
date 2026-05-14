"""Tests for the wellness archive helpers (PR2 + PR2bis plan iso-config)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from magma_cycling.config.data_repo import (
    DEFAULT_SHARED_ROOT_FILES,
    LEGACY_ROOT_ENV,
    ROOT_ENV,
    WELLNESS_SUBDIR,
)
from magma_cycling.wellness import (
    archive_wellness_day,
    resolve_wellness_dir,
    wellness_archive_exists,
    wellness_archive_path,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for v in (ROOT_ENV, LEGACY_ROOT_ENV):
        monkeypatch.delenv(v, raising=False)


class TestResolveWellnessDir:
    def test_uses_training_data_root(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        assert resolve_wellness_dir() == tmp_path / WELLNESS_SUBDIR

    def test_uses_legacy_training_data_repo(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(LEGACY_ROOT_ENV, str(tmp_path))
        assert resolve_wellness_dir() == tmp_path / WELLNESS_SUBDIR

    def test_fallback_when_no_env(self):
        assert resolve_wellness_dir() == Path.home() / "data" / "wellness"


class TestPathBuilders:
    def test_archive_path_format(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        assert wellness_archive_path("2026-05-14") == tmp_path / WELLNESS_SUBDIR / "2026-05-14.json"

    def test_invalid_date_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            wellness_archive_path("14/05/2026")
        with pytest.raises(ValueError):
            wellness_archive_path("2026-5-14")  # missing zero-pad

    def test_exists_false_when_absent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        assert wellness_archive_exists("2026-05-14") is False


class TestArchiveWellnessDay:
    def test_writes_json_atomically(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        payload = {
            "id": "2026-05-14",
            "ctl": 41.0,
            "atl": 38.2,
            "sleepSecs": 25200,
            "weight": 84.7,
        }
        target = archive_wellness_day("2026-05-14", payload)
        assert target == tmp_path / WELLNESS_SUBDIR / "2026-05-14.json"
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert loaded == payload
        assert wellness_archive_exists("2026-05-14") is True
        # No .tmp leftover
        assert not target.with_suffix(target.suffix + ".tmp").exists()

    def test_creates_parent_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        wellness_dir = tmp_path / WELLNESS_SUBDIR
        assert not wellness_dir.exists()
        archive_wellness_day("2026-05-14", {"id": "2026-05-14"})
        assert wellness_dir.is_dir()

    def test_payload_id_mismatch_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        with pytest.raises(ValueError, match="mismatches"):
            archive_wellness_day("2026-05-14", {"id": "2026-05-15"})

    def test_payload_without_id_accepted(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        # Edge case: lib sometimes returns entries with no id (incomplete day)
        target = archive_wellness_day("2026-05-14", {"ctl": 40.0})
        assert target.is_file()

    def test_overwrites_existing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        archive_wellness_day("2026-05-14", {"id": "2026-05-14", "ctl": 40})
        archive_wellness_day("2026-05-14", {"id": "2026-05-14", "ctl": 50})
        loaded = json.loads(wellness_archive_path("2026-05-14").read_text(encoding="utf-8"))
        assert loaded["ctl"] == 50


class TestWhitelistContainsWellness:
    def test_default_whitelist_contains_wellness_pattern(self):
        assert "data/wellness/**" in DEFAULT_SHARED_ROOT_FILES
