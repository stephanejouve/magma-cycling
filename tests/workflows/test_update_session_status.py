"""
Tests for update_session_status tool.

Tests the session status update tool including:
- Local JSON updates (without sync)
- Intervals.icu synchronization
- Status validation
- Error handling

Author: Claude Sonnet 4.5
Created: 2026-02-19
"""

import json
from datetime import date
from unittest.mock import MagicMock

import pytest

from cyclisme_training_logs.planning.models import WeeklyPlan
from cyclisme_training_logs.update_session_status import (
    STATUSES_TO_DELETE,
    find_event_by_session,
    sync_with_intervals,
)


class TestUpdateSessionStatusLocal:
    """Test local JSON updates without Intervals.icu sync."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Mock Control Tower to use tmp_path for planning."""
        from cyclisme_training_logs.planning.control_tower import planning_tower

        # Save original path
        original_planning_dir = planning_tower.planning_dir

        # Override with tmp_path
        planning_tower.planning_dir = tmp_path
        planning_tower.backup_system.planning_dir = tmp_path

        yield tmp_path

        # Restore original path
        planning_tower.planning_dir = original_planning_dir
        planning_tower.backup_system.planning_dir = original_planning_dir

    @pytest.fixture
    def temp_planning_file(self, tmp_path, mock_config):
        """Create temporary planning file for tests."""
        planning_data = {
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
                    "name": "Session1",
                    "type": "END",
                    "version": "V001",
                    "tss_planned": 50,
                    "duration_min": 60,
                    "description": "Test session",
                    "status": "planned",
                    "intervals_id": None,
                    "description_hash": None,
                },
                {
                    "session_id": "S999-02",
                    "date": "2026-03-03",
                    "name": "Session2",
                    "type": "INT",
                    "version": "V001",
                    "tss_planned": 70,
                    "duration_min": 65,
                    "description": "Test session 2",
                    "status": "planned",
                    "intervals_id": 12345,
                    "description_hash": None,
                },
            ],
        }

        planning_file = tmp_path / "week_planning_S999.json"
        with open(planning_file, "w", encoding="utf-8") as f:
            json.dump(planning_data, f, indent=2)

        return planning_file

    def test_update_session_to_completed(self, temp_planning_file, tmp_path, mock_config):
        """Test updating session status to completed."""
        from cyclisme_training_logs.weekly_planner import WeeklyPlanner

        # Create planner
        planner = WeeklyPlanner(
            week_number="S999",
            start_date=date(2026, 3, 2),
            project_root=tmp_path,
        )
        planner.planning_dir = tmp_path

        # Update status
        success = planner.update_session_status("S999-01", "completed")

        assert success is True

        # Verify in JSON
        plan = WeeklyPlan.from_json(temp_planning_file)
        assert plan.planned_sessions[0].status == "completed"

    def test_update_session_to_cancelled_with_reason(
        self, temp_planning_file, tmp_path, mock_config
    ):
        """Test updating session to cancelled with reason."""
        from cyclisme_training_logs.weekly_planner import WeeklyPlanner

        planner = WeeklyPlanner(
            week_number="S999",
            start_date=date(2026, 3, 2),
            project_root=tmp_path,
        )
        planner.planning_dir = tmp_path

        # Cancel with reason
        success = planner.update_session_status("S999-01", "cancelled", reason="Fatigue")

        assert success is True

        # Verify
        plan = WeeklyPlan.from_json(temp_planning_file)
        assert plan.planned_sessions[0].status == "cancelled"
        assert plan.planned_sessions[0].skip_reason == "Fatigue"

    def test_update_session_to_skipped(self, temp_planning_file, tmp_path, mock_config):
        """Test updating session to skipped."""
        from cyclisme_training_logs.weekly_planner import WeeklyPlanner

        planner = WeeklyPlanner(
            week_number="S999",
            start_date=date(2026, 3, 2),
            project_root=tmp_path,
        )
        planner.planning_dir = tmp_path

        # Skip with reason
        success = planner.update_session_status("S999-02", "skipped", reason="Weather")

        assert success is True

        # Verify
        plan = WeeklyPlan.from_json(temp_planning_file)
        assert plan.planned_sessions[1].status == "skipped"
        assert plan.planned_sessions[1].skip_reason == "Weather"

    def test_update_nonexistent_session_fails(self, temp_planning_file, tmp_path, mock_config):
        """Test that updating nonexistent session returns False."""
        from cyclisme_training_logs.weekly_planner import WeeklyPlanner

        planner = WeeklyPlanner(
            week_number="S999",
            start_date=date(2026, 3, 2),
            project_root=tmp_path,
        )
        planner.planning_dir = tmp_path

        # Try to update nonexistent session
        success = planner.update_session_status("S999-99", "completed")

        assert success is False

    def test_last_updated_is_modified(self, temp_planning_file, tmp_path, mock_config):
        """Test that last_updated timestamp is updated."""
        from cyclisme_training_logs.weekly_planner import WeeklyPlanner

        # Load original
        plan_before = WeeklyPlan.from_json(temp_planning_file)
        initial_timestamp = plan_before.last_updated

        # Update session
        planner = WeeklyPlanner(
            week_number="S999",
            start_date=date(2026, 3, 2),
            project_root=tmp_path,
        )
        planner.planning_dir = tmp_path

        import time

        time.sleep(0.1)

        planner.update_session_status("S999-01", "completed")

        # Verify timestamp changed
        plan_after = WeeklyPlan.from_json(temp_planning_file)
        assert plan_after.last_updated > initial_timestamp


class TestFindEventBySession:
    """Test find_event_by_session function."""

    def test_find_event_by_session_id_in_name(self):
        """Test finding event when session_id is in event name."""
        # Mock client
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {"id": 123, "name": "S999-01 EnduranceDouce", "category": "WORKOUT"},
            {"id": 456, "name": "S999-02 Intervals", "category": "WORKOUT"},
        ]

        # Find event
        event = find_event_by_session(mock_client, "S999-01", "2026-03-02")

        assert event is not None
        assert event["id"] == 123
        assert "S999-01" in event["name"]

    def test_find_event_no_match(self):
        """Test finding event when no match exists."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {"id": 123, "name": "Other session", "category": "WORKOUT"}
        ]

        event = find_event_by_session(mock_client, "S999-99", "2026-03-02")

        assert event is None

    def test_find_event_exception_returns_none(self):
        """Test that exceptions in find_event return None."""
        mock_client = MagicMock()
        mock_client.get_events.side_effect = Exception("API Error")

        event = find_event_by_session(mock_client, "S999-01", "2026-03-02")

        assert event is None


class TestSyncWithIntervals:
    """Test sync_with_intervals function."""

    def test_sync_cancelled_event_converts_to_note(self, capsys):
        """Test that cancelled status converts event to NOTE."""
        # Mock client
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {
                "id": 123,
                "name": "S999-01 EnduranceDouce",
                "category": "WORKOUT",
                "description": "Original workout description",
            }
        ]
        mock_client.update_event.return_value = {"id": 123, "category": "NOTE"}

        # Sync cancelled
        result = sync_with_intervals(
            mock_client, "S999-01", "2026-03-02", "cancelled", reason="Fatigue"
        )

        assert result is True

        # Verify update_event was called
        mock_client.update_event.assert_called_once()
        call_args = mock_client.update_event.call_args
        assert call_args[0][0] == 123  # event_id
        update_data = call_args[0][1]
        assert update_data["category"] == "NOTE"
        assert "[ANNULÉE]" in update_data["name"]
        assert "Fatigue" in update_data["description"]

    def test_sync_skipped_event(self):
        """Test that skipped status converts event to NOTE with [SAUTÉE] tag."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {"id": 456, "name": "S999-02 Intervals", "category": "WORKOUT", "description": "Test"}
        ]
        mock_client.update_event.return_value = {"id": 456}

        result = sync_with_intervals(
            mock_client, "S999-02", "2026-03-03", "skipped", reason="Weather"
        )

        assert result is True

        call_args = mock_client.update_event.call_args
        update_data = call_args[0][1]
        assert "[SAUTÉE]" in update_data["name"]
        assert "Weather" in update_data["description"]

    def test_sync_already_marked_event_returns_true(self):
        """Test that already marked events return True without update."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {
                "id": 123,
                "name": "[ANNULÉE] S999-01 EnduranceDouce",
                "category": "NOTE",
                "description": "Already cancelled",
            }
        ]

        result = sync_with_intervals(mock_client, "S999-01", "2026-03-02", "cancelled")

        assert result is True
        # Should not call update_event
        mock_client.update_event.assert_not_called()

    def test_sync_no_event_found_returns_true(self):
        """Test that missing event returns True (graceful failure)."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = []

        result = sync_with_intervals(mock_client, "S999-99", "2026-03-02", "cancelled")

        # Should return True even if no event found
        assert result is True


class TestStatusConstants:
    """Test status constants."""

    def test_statuses_to_delete_contains_expected(self):
        """Test STATUSES_TO_DELETE constant."""
        assert "cancelled" in STATUSES_TO_DELETE
        assert "skipped" in STATUSES_TO_DELETE
        assert "replaced" in STATUSES_TO_DELETE
        assert "completed" not in STATUSES_TO_DELETE


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_sync_update_event_fails(self):
        """Test handling when update_event fails."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {"id": 123, "name": "S999-01 Test", "category": "WORKOUT", "description": "Test"}
        ]
        mock_client.update_event.return_value = None  # Failure

        result = sync_with_intervals(mock_client, "S999-01", "2026-03-02", "cancelled")

        assert result is False

    def test_sync_update_event_exception(self):
        """Test handling when update_event raises exception."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {"id": 123, "name": "S999-01 Test", "category": "WORKOUT", "description": "Test"}
        ]
        mock_client.update_event.side_effect = Exception("API Error")

        # Should handle exception gracefully
        with pytest.raises(Exception):
            sync_with_intervals(mock_client, "S999-01", "2026-03-02", "cancelled")
