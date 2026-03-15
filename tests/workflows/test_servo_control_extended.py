"""Extended tests for servo_control — _update_planning_json, _apply_lighten, routing."""

import json
from unittest.mock import patch

import pytest

from magma_cycling.planning.models import WeeklyPlan
from magma_cycling.workflows.coach.servo_control import ServoControlMixin

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def planning_data():
    """Sample planning data with multiple sessions."""
    return {
        "week_id": "S999",
        "start_date": "2026-03-02",
        "end_date": "2026-03-08",
        "created_at": "2026-02-01T20:00:00Z",
        "last_updated": "2026-02-01T20:00:00Z",
        "version": 1,
        "athlete_id": "iXXXXXX",
        "tss_target": 350,
        "planned_sessions": [
            {
                "session_id": "S999-01",
                "date": "2026-03-02",
                "name": "Endurance",
                "type": "END",
                "version": "V001",
                "tss_planned": 50,
                "duration_min": 60,
                "description": "Endurance Z2",
                "status": "planned",
                "intervals_id": None,
                "description_hash": None,
            },
            {
                "session_id": "S999-02",
                "date": "2026-03-04",
                "name": "SweetSpot",
                "type": "INT",
                "version": "V001",
                "tss_planned": 70,
                "duration_min": 65,
                "description": "Sweet Spot 3x10",
                "status": "planned",
                "intervals_id": 12345,
                "description_hash": None,
            },
            {
                "session_id": "S999-03",
                "date": "2026-03-06",
                "name": "Endurance Long",
                "type": "END",
                "version": "V001",
                "tss_planned": 80,
                "duration_min": 90,
                "description": "Endurance longue Z2",
                "status": "planned",
                "intervals_id": None,
                "description_hash": None,
            },
        ],
    }


@pytest.fixture
def mock_control_tower(tmp_path, planning_data):
    """Mock Control Tower to use tmp_path for planning."""
    from magma_cycling.planning.control_tower import planning_tower

    original_planning_dir = planning_tower.planning_dir
    original_backup_dir = planning_tower.backup_system.planning_dir
    planning_tower.planning_dir = tmp_path
    planning_tower.backup_system.planning_dir = tmp_path

    planning_file = tmp_path / "week_planning_S999.json"
    with open(planning_file, "w", encoding="utf-8") as f:
        json.dump(planning_data, f, indent=2)

    yield tmp_path

    planning_tower.planning_dir = original_planning_dir
    planning_tower.backup_system.planning_dir = original_backup_dir


# ---------------------------------------------------------------------------
# _update_planning_json
# ---------------------------------------------------------------------------


class TestUpdatePlanningJson:
    """Tests for _update_planning_json."""

    def test_updates_session_fields(self, mock_control_tower):
        """Updates session type, tss, description via Control Tower."""
        mixin = ServoControlMixin()
        new_workout = {
            "code": "S999-01-REC-Recovery-V001",
            "session_id": "S999-01",
            "name": "Recovery",
            "type": "REC",
            "tss": 25,
            "description": "Recovery spin 40min Z1",
        }

        result = mixin._update_planning_json(
            week_id="S999",
            date="2026-03-02",
            new_workout=new_workout,
            old_workout="S999-01-END-Endurance-V001",
            reason="Fatigue accumulée",
        )

        assert result is True

        # Verify planning file updated
        plan = WeeklyPlan.from_json(mock_control_tower / "week_planning_S999.json")
        session = plan.planned_sessions[0]
        assert session.session_type == "REC"
        assert session.tss_planned == 25
        assert session.status == "modified"

    def test_returns_false_for_missing_date(self, mock_control_tower):
        """Returns False when no session matches the target date."""
        mixin = ServoControlMixin()
        new_workout = {
            "code": "S999-99-REC-V001",
            "type": "REC",
            "tss": 20,
            "description": "Test",
        }

        result = mixin._update_planning_json(
            week_id="S999",
            date="2099-01-01",
            new_workout=new_workout,
            old_workout="OLD",
            reason="test",
        )

        assert result is False

    def test_returns_false_for_missing_week(self, mock_control_tower):
        """Returns False when week planning file doesn't exist."""
        mixin = ServoControlMixin()
        new_workout = {"code": "X", "type": "REC", "tss": 20, "description": "Test"}

        result = mixin._update_planning_json(
            week_id="S000",
            date="2026-03-02",
            new_workout=new_workout,
            old_workout="OLD",
            reason="test",
        )

        assert result is False


# ---------------------------------------------------------------------------
# _apply_lighten
# ---------------------------------------------------------------------------


class TestApplyLighten:
    """Tests for _apply_lighten."""

    def test_auto_mode_stores_recommendation(self, mock_control_tower):
        """In auto_mode, stores recommendation without applying."""
        mixin = ServoControlMixin()
        mixin.auto_mode = True
        mixin.workout_templates = {
            "recovery_active_30tss": {
                "name": "Recovery Active 30 TSS",
                "type": "REC",
                "tss": 30,
                "duration_minutes": 45,
                "description": "45min Z1-Z2 easy spin",
                "workout_code_pattern": "S{week_id}-{day_num}-REC-V001",
                "intervals_icu_format": "[WARMUP 10:00 Z1]",
            },
        }

        mod = {
            "action": "lighten",
            "target_date": "2026-03-04",
            "current_workout": "S999-02-INT-SweetSpot-V001",
            "template_id": "recovery_active_30tss",
            "reason": "Découplage 11.2%",
        }

        mixin._apply_lighten(mod, "S999")

        assert hasattr(mixin, "_servo_recommendations")
        assert len(mixin._servo_recommendations) == 1
        rec = mixin._servo_recommendations[0]
        assert rec["template"] == "Recovery Active 30 TSS"
        assert rec["tss"] == 30
        assert rec["status"] == "pending_manual_application"

    def test_unknown_template_prints_error(self, mock_control_tower, capsys):
        """Prints error for unknown template_id."""
        mixin = ServoControlMixin()
        mixin.auto_mode = True
        mixin.workout_templates = {}

        mod = {
            "action": "lighten",
            "target_date": "2026-03-04",
            "current_workout": "S999-02-INT",
            "template_id": "nonexistent_template",
            "reason": "test",
        }

        mixin._apply_lighten(mod, "S999")

        captured = capsys.readouterr()
        assert "Template inconnu" in captured.out

    @patch("sys.stdin")
    def test_non_tty_stores_recommendation(self, mock_stdin, mock_control_tower):
        """Non-tty mode stores recommendation without interactive prompt."""
        mock_stdin.isatty.return_value = False

        mixin = ServoControlMixin()
        mixin.auto_mode = False
        mixin.workout_templates = {
            "recovery_short_20tss": {
                "name": "Recovery Short 20 TSS",
                "type": "REC",
                "tss": 20,
                "duration_minutes": 30,
                "description": "30min Z1",
                "workout_code_pattern": "S{week_id}-{day_num}-REC-V001",
                "intervals_icu_format": "[STEADY 30:00 Z1]",
            },
        }

        mod = {
            "action": "lighten",
            "target_date": "2026-03-04",
            "current_workout": "CODE",
            "template_id": "recovery_short_20tss",
            "reason": "Sommeil < 5h",
        }

        mixin._apply_lighten(mod, "S999")

        assert hasattr(mixin, "_servo_recommendations")
        assert len(mixin._servo_recommendations) == 1


# ---------------------------------------------------------------------------
# apply_planning_modifications — routing
# ---------------------------------------------------------------------------


class TestApplyPlanningModificationsRouting:
    """Tests for apply_planning_modifications dispatch logic."""

    def test_empty_modifications_no_op(self, capsys):
        """Empty list prints 'maintained' message."""
        mixin = ServoControlMixin()
        mixin.apply_planning_modifications([], "S999")

        captured = capsys.readouterr()
        assert "maintenu" in captured.out

    @patch.object(ServoControlMixin, "_apply_lighten")
    def test_lighten_action_routed(self, mock_lighten):
        """Lighten action dispatches to _apply_lighten."""
        mixin = ServoControlMixin()
        mods = [
            {
                "action": "lighten",
                "target_date": "2026-03-04",
                "current_workout": "CODE",
                "template_id": "recovery_active_30tss",
                "reason": "Fatigue",
            },
        ]

        mixin.apply_planning_modifications(mods, "S999")
        mock_lighten.assert_called_once_with(mods[0], "S999")

    def test_reschedule_prints_warning(self, capsys):
        """Reschedule prints not-implemented warning."""
        mixin = ServoControlMixin()
        mods = [
            {
                "action": "reschedule",
                "target_date": "2026-03-04",
                "current_workout": "CODE",
                "reason": "test",
            },
        ]

        mixin.apply_planning_modifications(mods, "S999")

        captured = capsys.readouterr()
        assert "reschedule" in captured.out

    def test_unknown_action_prints_warning(self, capsys):
        """Unknown action prints warning."""
        mixin = ServoControlMixin()
        mods = [
            {
                "action": "teleport",
                "target_date": "2026-03-04",
                "current_workout": "CODE",
                "reason": "test",
            },
        ]

        mixin.apply_planning_modifications(mods, "S999")

        captured = capsys.readouterr()
        assert "inconnue" in captured.out

    @patch.object(ServoControlMixin, "_apply_lighten")
    @patch.object(ServoControlMixin, "_apply_rest_day")
    def test_multiple_modifications_dispatched(self, mock_rest, mock_lighten):
        """Multiple modifications each dispatch to correct handler."""
        mixin = ServoControlMixin()
        mods = [
            {
                "action": "lighten",
                "target_date": "2026-03-04",
                "current_workout": "A",
                "template_id": "t1",
                "reason": "r1",
            },
            {
                "action": "rest_day",
                "target_date": "2026-03-06",
                "current_workout": "B",
                "reason": "r2",
            },
        ]

        mixin.apply_planning_modifications(mods, "S999")

        mock_lighten.assert_called_once_with(mods[0], "S999")
        mock_rest.assert_called_once_with(mods[1], "S999")
