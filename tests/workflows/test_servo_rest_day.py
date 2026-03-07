"""Tests for rest_day action in servo control (workflow-coach)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.planning.models import WeeklyPlan


@pytest.fixture
def planning_data():
    """Sample planning data with sessions."""
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
                "date": "2026-03-03",
                "name": "Interval",
                "type": "INT",
                "version": "V001",
                "tss_planned": 70,
                "duration_min": 65,
                "description": "Sweet Spot 3x10",
                "status": "planned",
                "intervals_id": 12345,
                "description_hash": None,
            },
        ],
    }


@pytest.fixture
def mock_control_tower(tmp_path, planning_data):
    """Mock Control Tower to use tmp_path for planning."""
    from magma_cycling.planning.control_tower import planning_tower

    original_planning_dir = planning_tower.planning_dir
    planning_tower.planning_dir = tmp_path
    planning_tower.backup_system.planning_dir = tmp_path

    planning_file = tmp_path / "week_planning_S999.json"
    with open(planning_file, "w", encoding="utf-8") as f:
        json.dump(planning_data, f, indent=2)

    yield tmp_path

    planning_tower.planning_dir = original_planning_dir
    planning_tower.backup_system.planning_dir = original_planning_dir


class TestApplyRestDay:
    """Test _apply_rest_day updates planning JSON with status=rest_day."""

    def test_rest_day_updates_planning_json(self, mock_control_tower):
        """Test that rest_day sets session.status to rest_day in planning."""
        from magma_cycling.workflows.coach.servo_control import ServoControlMixin

        mixin = ServoControlMixin()
        mod = {
            "action": "rest_day",
            "target_date": "2026-03-03",
            "current_workout": "S999-02-INT-Interval-V001",
            "reason": "TSB -22, sommeil 4.8h",
        }

        with patch.object(mixin, "auto_mode", True, create=True):
            mixin._apply_rest_day(mod, "S999")

        # In auto_mode, recommendation is stored but not applied
        assert hasattr(mixin, "_servo_recommendations")
        assert len(mixin._servo_recommendations) == 1
        assert mixin._servo_recommendations[0]["action"] == "rest_day"

    @patch("magma_cycling.config.create_intervals_client")
    @patch("magma_cycling.update_session_status.sync_with_intervals")
    def test_execute_rest_day_updates_planning(self, mock_sync, mock_client, mock_control_tower):
        """Test _execute_rest_day updates planning and syncs Intervals.icu."""
        from magma_cycling.workflows.coach.servo_control import ServoControlMixin

        mock_sync.return_value = True
        mock_client.return_value = MagicMock()

        mixin = ServoControlMixin()
        mod = {
            "action": "rest_day",
            "target_date": "2026-03-03",
            "current_workout": "S999-02-INT-Interval-V001",
            "reason": "TSB -22, sommeil 4.8h",
        }

        mixin._execute_rest_day(mod, "S999")

        # Verify planning JSON updated
        planning_file = mock_control_tower / "week_planning_S999.json"
        plan = WeeklyPlan.from_json(planning_file)
        session = plan.planned_sessions[1]
        assert session.status == "rest_day"
        assert session.skip_reason == "TSB -22, sommeil 4.8h"

        # Verify sync called
        mock_sync.assert_called_once()
        call_kwargs = mock_sync.call_args[1]
        assert call_kwargs["new_status"] == "rest_day"
        assert call_kwargs["session_id"] == "S999-02"


class TestApplyRestDayNonInteractive:
    """Test rest_day in non-interactive mode (auto_mode)."""

    def test_auto_mode_stores_recommendation(self, mock_control_tower):
        """Test that auto_mode stores recommendation without applying."""
        from magma_cycling.workflows.coach.servo_control import ServoControlMixin

        mixin = ServoControlMixin()
        mixin.auto_mode = True
        mod = {
            "action": "rest_day",
            "target_date": "2026-03-03",
            "current_workout": "S999-02-INT",
            "reason": "Fatigue accumulée",
        }

        mixin._apply_rest_day(mod, "S999")

        assert hasattr(mixin, "_servo_recommendations")
        assert len(mixin._servo_recommendations) == 1
        rec = mixin._servo_recommendations[0]
        assert rec["action"] == "rest_day"
        assert rec["status"] == "pending_manual_application"
        assert rec["date"] == "2026-03-03"

    @patch("sys.stdin")
    def test_non_tty_stores_recommendation(self, mock_stdin, mock_control_tower):
        """Test that non-tty mode stores recommendation."""
        from magma_cycling.workflows.coach.servo_control import ServoControlMixin

        mock_stdin.isatty.return_value = False

        mixin = ServoControlMixin()
        mixin.auto_mode = False
        mod = {
            "action": "rest_day",
            "target_date": "2026-03-03",
            "current_workout": "S999-02-INT",
            "reason": "Sommeil < 5h",
        }

        mixin._apply_rest_day(mod, "S999")

        assert hasattr(mixin, "_servo_recommendations")
        assert len(mixin._servo_recommendations) == 1


class TestServoPromptContainsRestDay:
    """Test that servo prompt documents the rest_day action."""

    def test_coach_prompt_contains_rest_day(self):
        """Test workflow-coach servo prompt includes rest_day action."""
        import inspect

        from magma_cycling.workflows.coach.servo_control import ServoControlMixin

        source = inspect.getsource(ServoControlMixin.step_6b_servo_control)
        assert '"action": "rest_day"' in source
        assert "rest_day" in source

    def test_sync_prompt_contains_rest_day(self):
        """Test daily-sync servo prompt includes rest_day action."""
        import inspect

        from magma_cycling.workflows.sync.servo_evaluation import ServoEvaluationMixin

        source = inspect.getsource(ServoEvaluationMixin.run_servo_adjustment)
        assert '"action": "rest_day"' in source
        assert "rest_day" in source


class TestApplyPlanningModificationsRouting:
    """Test that apply_planning_modifications routes rest_day and cancel correctly."""

    @patch.object(
        __import__(
            "magma_cycling.workflows.coach.servo_control", fromlist=["ServoControlMixin"]
        ).ServoControlMixin,
        "_apply_rest_day",
    )
    def test_rest_day_routed(self, mock_apply_rest_day):
        """Test rest_day action is routed to _apply_rest_day."""
        from magma_cycling.workflows.coach.servo_control import ServoControlMixin

        mixin = ServoControlMixin()
        modifications = [
            {
                "action": "rest_day",
                "target_date": "2026-03-03",
                "current_workout": "CODE",
                "reason": "Fatigue",
            }
        ]

        mixin.apply_planning_modifications(modifications, "S999")
        mock_apply_rest_day.assert_called_once_with(modifications[0], "S999")

    @patch.object(
        __import__(
            "magma_cycling.workflows.coach.servo_control", fromlist=["ServoControlMixin"]
        ).ServoControlMixin,
        "_apply_rest_day",
    )
    def test_cancel_routed_to_rest_day(self, mock_apply_rest_day):
        """Test cancel action is routed to _apply_rest_day (same treatment)."""
        from magma_cycling.workflows.coach.servo_control import ServoControlMixin

        mixin = ServoControlMixin()
        modifications = [
            {
                "action": "cancel",
                "target_date": "2026-03-03",
                "current_workout": "CODE",
                "reason": "Blessure",
            }
        ]

        mixin.apply_planning_modifications(modifications, "S999")
        mock_apply_rest_day.assert_called_once_with(modifications[0], "S999")
