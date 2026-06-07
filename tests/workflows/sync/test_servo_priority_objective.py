"""Tests for priority_objective awareness in ServoEvaluationMixin.

PR 3 of issue #401 — auto-servo prend conscience de la fenêtre prep autour
de la date de l'objectif. Couvre le helper `_get_priority_objective_window`
(unitaire, exhaustif sur les edges) puis l'injection de la directive dans
le prompt servo via `run_servo_adjustment` (intégration légère).
"""

from __future__ import annotations

from unittest.mock import MagicMock

from magma_cycling.workflows.sync import servo_evaluation
from magma_cycling.workflows.sync.servo_evaluation import (
    PRIORITY_OBJECTIVE_BUILD_PHASE_MAX_DAYS,
    PRIORITY_OBJECTIVE_RACE_WEEK_MAX_DAYS,
    ServoEvaluationMixin,
    _get_priority_objective_window,
)


class _FakeSync(ServoEvaluationMixin):
    """Minimal stand-in for DailySync to test the mixin."""

    def __init__(self):
        self.client = MagicMock()
        self.ai_analyzer = MagicMock()
        self.servo_criteria = {
            "decoupling_threshold": 7.5,
            "sleep_threshold_hours": 7.0,
            "feel_threshold": 4,
            "tsb_threshold": -10,
        }


def _po(days, **extra):
    return {
        "name": extra.get("name", "Les Copains 81km"),
        "type": extra.get("type", "granfondo"),
        "target_date": extra.get("target_date", "2026-07-04"),
        "days_until_target": days,
        **{k: v for k, v in extra.items() if k in {"distance_km", "notes", "priority"}},
    }


class TestGetPriorityObjectiveWindow:
    """Helper `_get_priority_objective_window` — exhaustive edge coverage."""

    def test_none_payload_returns_none(self):
        assert _get_priority_objective_window(None) is None

    def test_non_dict_payload_returns_none(self):
        assert _get_priority_objective_window("garbage") is None

    def test_missing_days_until_target_returns_none(self):
        assert _get_priority_objective_window({"name": "x", "target_date": "2026-07-04"}) is None

    def test_non_int_days_returns_none(self):
        assert _get_priority_objective_window(_po("twenty")) is None  # type: ignore

    def test_past_event_returns_none(self):
        """Negative days_until_target → no taper logic to enforce post-event."""
        assert _get_priority_objective_window(_po(-3)) is None

    def test_too_early_returns_none(self):
        """Beyond build-phase window (>21 days) → no override yet."""
        assert _get_priority_objective_window(_po(22)) is None
        assert _get_priority_objective_window(_po(100)) is None

    def test_race_week_zero_day(self):
        out = _get_priority_objective_window(_po(0))
        assert out["window"] == "race_week"
        assert out["days_until_target"] == 0
        assert out["block_load_increase"] is True
        assert "J-0" in out["prompt_directive"]
        assert "Les Copains 81km" in out["prompt_directive"]
        assert "NE PROPOSE AUCUNE augmentation" in out["prompt_directive"]

    def test_race_week_upper_edge(self):
        """J-7 (PRIORITY_OBJECTIVE_RACE_WEEK_MAX_DAYS) still belongs to race window."""
        out = _get_priority_objective_window(_po(PRIORITY_OBJECTIVE_RACE_WEEK_MAX_DAYS))
        assert out["window"] == "race_week"
        assert out["block_load_increase"] is True

    def test_build_phase_lower_edge(self):
        """J-8 (one day past race week max) belongs to build phase."""
        out = _get_priority_objective_window(_po(PRIORITY_OBJECTIVE_RACE_WEEK_MAX_DAYS + 1))
        assert out["window"] == "build_phase"
        assert out["block_load_increase"] is False
        assert "BUILD PHASE" in out["prompt_directive"]
        assert "J-8" in out["prompt_directive"]

    def test_build_phase_upper_edge(self):
        """J-21 (PRIORITY_OBJECTIVE_BUILD_PHASE_MAX_DAYS) still belongs to build window."""
        out = _get_priority_objective_window(_po(PRIORITY_OBJECTIVE_BUILD_PHASE_MAX_DAYS))
        assert out["window"] == "build_phase"
        assert out["block_load_increase"] is False

    def test_directive_carries_event_name_and_date(self):
        po = _po(15, name="Marmotte", target_date="2026-07-04")
        out = _get_priority_objective_window(po)
        assert "Marmotte" in out["prompt_directive"]
        assert "2026-07-04" in out["prompt_directive"]


class TestRunServoAdjustmentInjection:
    """Integration: run_servo_adjustment injects the directive in the prompt only when in window."""

    def _setup_sync_with_captured_prompt(self):
        sync = _FakeSync()
        captured = {}

        def fake_analyze(prompt):
            captured["prompt"] = prompt
            return ""

        sync.ai_analyzer.analyze_session = fake_analyze
        return sync, captured

    def _patch_remaining_sessions(self, monkeypatch):
        fake_coach = MagicMock()
        fake_session = MagicMock()
        fake_session.session_id = "S100-MON-END"
        fake_session.session_date = "2026-06-09"
        fake_coach.load_remaining_sessions.return_value = [fake_session]
        monkeypatch.setattr(
            "magma_cycling.workflow_coach.WorkflowCoach", lambda servo_mode=True: fake_coach
        )
        monkeypatch.setattr(
            servo_evaluation, "format_remaining_sessions_compact", lambda _: "(planning)"
        )

    def test_no_directive_when_priority_objective_none(self, monkeypatch):
        sync, captured = self._setup_sync_with_captured_prompt()
        self._patch_remaining_sessions(monkeypatch)
        sync.run_servo_adjustment(
            week_id="S100",
            activity={"id": 1},
            metrics={"tsb": -12},
            analysis=None,
        )
        prompt = captured.get("prompt", "")
        assert "Objectif prioritaire" not in prompt
        assert "RACE WEEK" not in prompt
        assert "BUILD PHASE" not in prompt

    def test_no_directive_when_out_of_window(self, monkeypatch):
        sync, captured = self._setup_sync_with_captured_prompt()
        self._patch_remaining_sessions(monkeypatch)
        sync.run_servo_adjustment(
            week_id="S100",
            activity={"id": 1},
            metrics={"tsb": -12},
            analysis=None,
            priority_objective=_po(60),  # too early
        )
        prompt = captured.get("prompt", "")
        assert "Objectif prioritaire" not in prompt

    def test_build_phase_directive_inserted(self, monkeypatch):
        sync, captured = self._setup_sync_with_captured_prompt()
        self._patch_remaining_sessions(monkeypatch)
        sync.run_servo_adjustment(
            week_id="S100",
            activity={"id": 1},
            metrics={"tsb": -12},
            analysis=None,
            priority_objective=_po(15),
        )
        prompt = captured.get("prompt", "")
        assert "Objectif prioritaire — fenêtre prep" in prompt
        assert "BUILD PHASE" in prompt
        assert "J-15" in prompt

    def test_race_week_directive_inserted(self, monkeypatch):
        sync, captured = self._setup_sync_with_captured_prompt()
        self._patch_remaining_sessions(monkeypatch)
        sync.run_servo_adjustment(
            week_id="S100",
            activity={"id": 1},
            metrics={"tsb": -12},
            analysis=None,
            priority_objective=_po(3),
        )
        prompt = captured.get("prompt", "")
        assert "Objectif prioritaire — fenêtre prep" in prompt
        assert "RACE WEEK" in prompt
        assert "NE PROPOSE AUCUNE augmentation" in prompt
        assert "J-3" in prompt

    def test_directive_appears_before_strict_rules(self, monkeypatch):
        """Sanity-check : the directive block sits *before* the 'RÈGLES STRICTES' marker."""
        sync, captured = self._setup_sync_with_captured_prompt()
        self._patch_remaining_sessions(monkeypatch)
        sync.run_servo_adjustment(
            week_id="S100",
            activity={"id": 1},
            metrics={"tsb": -12},
            analysis=None,
            priority_objective=_po(5),
        )
        prompt = captured.get("prompt", "")
        directive_pos = prompt.find("RACE WEEK")
        rules_pos = prompt.find("RÈGLES STRICTES")
        assert directive_pos > 0 and rules_pos > 0
        assert directive_pos < rules_pos
