"""Tests for the decision log archive (PR8 plan iso-config)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from magma_cycling.config.data_repo import (
    DECISIONS_SUBDIR,
    DEFAULT_SHARED_ROOT_FILES,
    LEGACY_ROOT_ENV,
    ROOT_ENV,
)
from magma_cycling.decisions import (
    DecisionCategory,
    DecisionRecord,
    ImpactHorizon,
    decision_archive_path,
    next_decision_seq,
    record_decision,
    resolve_decisions_dir,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for v in (ROOT_ENV, LEGACY_ROOT_ENV):
        monkeypatch.delenv(v, raising=False)


class TestDecisionRecordModel:
    def test_valid_record(self):
        r = DecisionRecord(
            week_id="S094",
            title="Bump CTL target to 50",
            category=DecisionCategory.TARGET_CHANGE,
            description="After S093 retro, raise CTL target by 5 over 3 weeks",
            impact_horizon=ImpactHorizon.S_PLUS_1,
        )
        assert r.references == []

    def test_week_id_must_match_pattern(self):
        with pytest.raises(ValidationError, match="week_id"):
            DecisionRecord(
                week_id="93",
                title="t",
                category=DecisionCategory.TARGET_CHANGE,
                description="d",
                impact_horizon=ImpactHorizon.S_PLUS_1,
            )

    def test_naive_recorded_at_rejected(self):
        with pytest.raises(ValidationError, match="timezone-aware"):
            DecisionRecord(
                week_id="S094",
                title="t",
                category=DecisionCategory.TARGET_CHANGE,
                description="d",
                impact_horizon=ImpactHorizon.S_PLUS_1,
                recorded_at=datetime(2026, 5, 14, 8, 0),
            )

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            DecisionRecord(
                week_id="S094",
                title="t",
                category=DecisionCategory.TARGET_CHANGE,
                description="d",
                impact_horizon=ImpactHorizon.S_PLUS_1,
                bogus="x",  # type: ignore[call-arg]
            )

    def test_frozen(self):
        r = DecisionRecord(
            week_id="S094",
            title="t",
            category=DecisionCategory.TARGET_CHANGE,
            description="d",
            impact_horizon=ImpactHorizon.S_PLUS_1,
        )
        with pytest.raises(ValidationError):
            r.title = "new"  # type: ignore[misc]


class TestResolver:
    def test_uses_training_data_root(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        assert resolve_decisions_dir() == tmp_path / DECISIONS_SUBDIR

    def test_fallback_when_no_env(self):
        assert resolve_decisions_dir() == Path.home() / "data" / "decisions"


class TestPathBuilders:
    def test_archive_path_zero_padded(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        assert decision_archive_path("S094", 3) == (
            tmp_path / DECISIONS_SUBDIR / "decision-S094-03.md"
        )

    def test_invalid_week_id_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        with pytest.raises(ValueError, match="week_id"):
            decision_archive_path("94", 1)

    def test_invalid_seq_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        with pytest.raises(ValueError, match="seq"):
            decision_archive_path("S094", 0)


class TestNextDecisionSeq:
    def test_returns_1_when_dir_absent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        assert next_decision_seq("S094") == 1

    def test_increments_existing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        d = tmp_path / DECISIONS_SUBDIR
        d.mkdir(parents=True)
        (d / "decision-S094-01.md").write_text("x", encoding="utf-8")
        (d / "decision-S094-02.md").write_text("x", encoding="utf-8")
        assert next_decision_seq("S094") == 3

    def test_isolated_by_week(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        d = tmp_path / DECISIONS_SUBDIR
        d.mkdir(parents=True)
        (d / "decision-S094-01.md").write_text("x", encoding="utf-8")
        (d / "decision-S094-02.md").write_text("x", encoding="utf-8")
        assert next_decision_seq("S095") == 1

    def test_handles_gaps(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        d = tmp_path / DECISIONS_SUBDIR
        d.mkdir(parents=True)
        (d / "decision-S094-01.md").write_text("x", encoding="utf-8")
        (d / "decision-S094-05.md").write_text("x", encoding="utf-8")
        # Always max+1, never fill gaps (decision IDs are permanent)
        assert next_decision_seq("S094") == 6


class TestRecordDecision:
    def test_writes_markdown_with_front_matter(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        target = record_decision(
            DecisionRecord(
                week_id="S094",
                title="Bump CTL target",
                category=DecisionCategory.TARGET_CHANGE,
                description="After S093 retro, +5 CTL over 3w",
                impact_horizon=ImpactHorizon.S_PLUS_2,
                references=["bilan_final_s093.md"],
                recorded_at=datetime(2026, 5, 14, 8, 30, tzinfo=timezone.utc),
            )
        )
        assert target == tmp_path / DECISIONS_SUBDIR / "decision-S094-01.md"
        text = target.read_text(encoding="utf-8")
        assert text.startswith("---\n")
        front_str, _, body = text.partition("\n---\n")
        front = yaml.safe_load(front_str[4:])  # strip leading "---\n"
        assert front["week_id"] == "S094"
        assert front["category"] == "target_change"
        assert front["impact_horizon"] == "S+2"
        assert front["references"] == ["bilan_final_s093.md"]
        assert "Bump CTL target" in body
        assert "After S093 retro" in body
        # No .tmp leftover
        assert not target.with_suffix(target.suffix + ".tmp").exists()

    def test_sequential_writes_assign_distinct_seqs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        common = {
            "week_id": "S094",
            "category": DecisionCategory.MODAL_SWITCH,
            "description": "x",
            "impact_horizon": ImpactHorizon.S_PLUS_1,
        }
        p1 = record_decision(DecisionRecord(title="d1", **common))
        p2 = record_decision(DecisionRecord(title="d2", **common))
        assert p1.name == "decision-S094-01.md"
        assert p2.name == "decision-S094-02.md"

    def test_recorded_at_auto_stamped_when_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        target = record_decision(
            DecisionRecord(
                week_id="S094",
                title="t",
                category=DecisionCategory.POST_INCIDENT,
                description="d",
                impact_horizon=ImpactHorizon.S_PLUS_1,
            )
        )
        front_str = target.read_text(encoding="utf-8").split("\n---\n")[0][4:]
        front = yaml.safe_load(front_str)
        # Auto-stamped → parseable ISO
        datetime.fromisoformat(front["recorded_at"])


class TestWhitelistContainsDecisions:
    def test_default_whitelist_contains_decisions_pattern(self):
        assert "data/decisions/**" in DEFAULT_SHARED_ROOT_FILES
