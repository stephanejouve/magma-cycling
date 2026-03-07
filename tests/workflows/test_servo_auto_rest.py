"""Tests for auto rest_day application in daily-sync servo evaluation."""

import json
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.planning.models import WeeklyPlan
from magma_cycling.update_session_status import STATUSES_TO_DELETE, sync_with_intervals


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


class TestAutoRestDayApplication:
    """Test daily-sync auto-applies rest_day."""

    @patch("magma_cycling.config.create_intervals_client")
    @patch("magma_cycling.update_session_status.sync_with_intervals")
    def test_auto_rest_day_updates_planning(self, mock_sync, mock_client, mock_control_tower):
        """Test _apply_auto_rest_day updates planning JSON."""
        from magma_cycling.workflows.sync.servo_evaluation import (
            ServoEvaluationMixin,
        )

        mock_sync.return_value = True
        mock_client.return_value = MagicMock()

        mixin = ServoEvaluationMixin()
        mod = {
            "action": "rest_day",
            "target_date": "2026-03-03",
            "current_workout": "S999-02-INT-Interval-V001",
            "reason": "TSB -22, sommeil 4.8h",
        }

        mixin._apply_auto_rest_day(mod, "S999")

        # Verify planning JSON updated
        planning_file = mock_control_tower / "week_planning_S999.json"
        plan = WeeklyPlan.from_json(planning_file)
        session = plan.planned_sessions[1]
        assert session.status == "rest_day"
        assert session.skip_reason == "TSB -22, sommeil 4.8h"

        # Verify sync called with correct params
        mock_sync.assert_called_once()
        call_kwargs = mock_sync.call_args[1]
        assert call_kwargs["new_status"] == "rest_day"
        assert call_kwargs["session_id"] == "S999-02"
        assert call_kwargs["session_date"] == "2026-03-03"

    @patch("magma_cycling.config.create_intervals_client")
    @patch("magma_cycling.update_session_status.sync_with_intervals")
    def test_auto_rest_day_session_not_found(self, mock_sync, mock_client, mock_control_tower):
        """Test _apply_auto_rest_day handles missing session gracefully."""
        from magma_cycling.workflows.sync.servo_evaluation import (
            ServoEvaluationMixin,
        )

        mixin = ServoEvaluationMixin()
        mod = {
            "action": "rest_day",
            "target_date": "2026-03-09",
            "current_workout": "S999-99",
            "reason": "Fatigue",
        }

        # Should not raise
        mixin._apply_auto_rest_day(mod, "S999")

        # Sync should not be called (session not found)
        mock_sync.assert_not_called()

    @patch("magma_cycling.config.create_intervals_client")
    @patch("magma_cycling.update_session_status.sync_with_intervals")
    def test_cancel_treated_as_rest_day(self, mock_sync, mock_client, mock_control_tower):
        """Test that cancel action is treated same as rest_day."""
        from magma_cycling.workflows.sync.servo_evaluation import (
            ServoEvaluationMixin,
        )

        mock_sync.return_value = True
        mock_client.return_value = MagicMock()

        mixin = ServoEvaluationMixin()
        mod = {
            "action": "cancel",
            "target_date": "2026-03-03",
            "current_workout": "S999-02",
            "reason": "Blessure",
        }

        mixin._apply_auto_rest_day(mod, "S999")

        # Planning should be updated with rest_day status
        planning_file = mock_control_tower / "week_planning_S999.json"
        plan = WeeklyPlan.from_json(planning_file)
        session = plan.planned_sessions[1]
        assert session.status == "rest_day"


class TestSyncIntervalsRestDay:
    """Test sync_with_intervals handles rest_day status."""

    def test_rest_day_in_statuses_to_delete(self):
        """Test rest_day is in STATUSES_TO_DELETE."""
        assert "rest_day" in STATUSES_TO_DELETE

    def test_sync_rest_day_converts_to_note(self):
        """Test rest_day converts event to NOTE with [REPOS] tag."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {
                "id": 42,
                "name": "S999-02-INT-Interval-V001",
                "category": "WORKOUT",
                "description": "Sweet Spot 3x10",
            }
        ]
        mock_client.update_event.return_value = True

        result = sync_with_intervals(
            client=mock_client,
            session_id="S999-02",
            session_date="2026-03-03",
            new_status="rest_day",
            reason="TSB -22, sommeil 4.8h",
        )

        assert result is True
        mock_client.update_event.assert_called_once()
        call_args = mock_client.update_event.call_args
        update_data = call_args[0][1]
        assert update_data["name"] == "[REPOS] S999-02-INT-Interval-V001"
        assert update_data["category"] == "NOTE"
        assert "😴 SÉANCE REPOS" in update_data["description"]
        assert "TSB -22, sommeil 4.8h" in update_data["description"]

    def test_sync_rest_day_creates_note_when_no_event(self):
        """Test rest_day creates NOTE when no event exists."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = []
        mock_client.create_event.return_value = {"id": 99}

        session_info = {
            "name": "Interval",
            "type": "INT",
            "version": "V001",
            "description": "Sweet Spot 3x10",
            "tss_planned": 70,
            "duration_min": 65,
        }

        result = sync_with_intervals(
            client=mock_client,
            session_id="S999-02",
            session_date="2026-03-03",
            new_status="rest_day",
            reason="Fatigue accumulée",
            session_info=session_info,
        )

        assert result is True
        mock_client.create_event.assert_called_once()
        call_args = mock_client.create_event.call_args
        event_data = call_args[0][0]
        assert event_data["name"] == "[REPOS] S999-02-INT-Interval-V001"
        assert event_data["category"] == "NOTE"
        assert "😴 SÉANCE REPOS" in event_data["description"]

    def test_sync_rest_day_skips_already_tagged(self):
        """Test rest_day skips event already tagged [REPOS]."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {
                "id": 42,
                "name": "[REPOS] S999-02-INT-Interval-V001",
                "category": "NOTE",
                "description": "Already repos",
            }
        ]

        result = sync_with_intervals(
            client=mock_client,
            session_id="S999-02",
            session_date="2026-03-03",
            new_status="rest_day",
        )

        assert result is True
        mock_client.update_event.assert_not_called()
