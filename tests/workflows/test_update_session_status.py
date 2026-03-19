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
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.planning.models import WeeklyPlan
from magma_cycling.update_session_status import (
    STATUSES_TO_DELETE,
    find_event_by_session,
    main,
    sync_with_intervals,
)


class TestUpdateSessionStatusLocal:
    """Test local JSON updates without Intervals.icu sync."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Mock Control Tower to use tmp_path for planning."""
        from magma_cycling.planning.control_tower import planning_tower

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
        from magma_cycling.weekly_planner import WeeklyPlanner

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
        from magma_cycling.weekly_planner import WeeklyPlanner

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
        from magma_cycling.weekly_planner import WeeklyPlanner

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
        from magma_cycling.weekly_planner import WeeklyPlanner

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
        from magma_cycling.weekly_planner import WeeklyPlanner

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

    def test_sync_replaced_event_converts_to_note(self):
        """Test that replaced status converts event to NOTE with [REMPLACÉE] tag."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {
                "id": 789,
                "name": "S999-03 Tempo",
                "category": "WORKOUT",
                "description": "Tempo ride",
            }
        ]
        mock_client.update_event.return_value = {"id": 789}

        result = sync_with_intervals(
            mock_client, "S999-03", "2026-03-04", "replaced", reason="Changed to intervals"
        )

        assert result is True
        call_args = mock_client.update_event.call_args
        update_data = call_args[0][1]
        assert "[REMPLACÉE]" in update_data["name"]
        assert update_data["category"] == "NOTE"

    def test_sync_rest_day_event_converts_to_note(self):
        """Test that rest_day status converts event to NOTE with [REPOS] tag."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {
                "id": 321,
                "name": "S999-04 Recovery",
                "category": "WORKOUT",
                "description": "Easy ride",
            }
        ]
        mock_client.update_event.return_value = {"id": 321}

        result = sync_with_intervals(
            mock_client, "S999-04", "2026-03-05", "rest_day", reason="Fatigue accumulée"
        )

        assert result is True
        call_args = mock_client.update_event.call_args
        update_data = call_args[0][1]
        assert "[REPOS]" in update_data["name"]
        assert update_data["category"] == "NOTE"

    def test_sync_modified_updates_description(self):
        """Test that modified status appends modification note to event."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {
                "id": 555,
                "name": "S999-02 Intervals",
                "category": "WORKOUT",
                "description": "Original intervals",
            }
        ]
        mock_client.update_event.return_value = {"id": 555}

        result = sync_with_intervals(
            mock_client, "S999-02", "2026-03-03", "modified", reason="Reduced intensity"
        )

        assert result is True
        call_args = mock_client.update_event.call_args
        update_data = call_args[0][1]
        assert "MODIFIED" in update_data["description"]
        assert "Reduced intensity" in update_data["description"]
        assert "Original intervals" in update_data["description"]

    def test_sync_modified_no_event_returns_true(self):
        """Test that modified with no event found returns True gracefully."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = []

        result = sync_with_intervals(
            mock_client, "S999-99", "2026-03-02", "modified", reason="Test"
        )

        assert result is True
        mock_client.update_event.assert_not_called()

    def test_sync_completed_no_action(self):
        """Test that completed status takes no action."""
        mock_client = MagicMock()

        result = sync_with_intervals(mock_client, "S999-01", "2026-03-02", "completed")

        assert result is True
        mock_client.update_event.assert_not_called()
        mock_client.create_event.assert_not_called()

    def test_sync_unknown_status_returns_true(self):
        """Test that unknown status returns True with no action."""
        mock_client = MagicMock()

        result = sync_with_intervals(mock_client, "S999-01", "2026-03-02", "planned")

        assert result is True
        mock_client.update_event.assert_not_called()

    def test_sync_cancelled_no_event_creates_note(self):
        """Test that cancelled with no event creates a new NOTE."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = []
        mock_client.create_event.return_value = {"id": 999}

        session_info = {
            "name": "EnduranceDouce",
            "type": "END",
            "version": "V001",
            "description": "Easy endurance ride",
            "tss_planned": 50,
            "duration_min": 60,
        }

        result = sync_with_intervals(
            mock_client,
            "S999-01",
            "2026-03-02",
            "cancelled",
            reason="Maladie",
            session_info=session_info,
        )

        assert result is True
        mock_client.create_event.assert_called_once()
        call_args = mock_client.create_event.call_args
        event_data = call_args[0][0]
        assert event_data["category"] == "NOTE"
        assert "[ANNULÉE]" in event_data["name"]
        assert "Maladie" in event_data["description"]

    def test_sync_cancelled_no_event_no_session_info(self):
        """Test that cancelled with no event and no session_info returns True."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = []

        result = sync_with_intervals(
            mock_client, "S999-01", "2026-03-02", "cancelled", reason="Fatigue"
        )

        assert result is True
        mock_client.create_event.assert_not_called()

    def test_sync_cancelled_create_event_fails(self):
        """Test that failed create_event returns False."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = []
        mock_client.create_event.return_value = None

        session_info = {
            "name": "Test",
            "type": "END",
            "version": "V001",
            "description": "Test",
            "tss_planned": 50,
            "duration_min": 60,
        }

        result = sync_with_intervals(
            mock_client,
            "S999-01",
            "2026-03-02",
            "cancelled",
            reason="Test",
            session_info=session_info,
        )

        assert result is False

    def test_sync_event_with_none_id_returns_false(self):
        """Test that event with None id returns False."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {
                "id": None,
                "name": "S999-01 Test",
                "category": "WORKOUT",
                "description": "Test",
            }
        ]

        result = sync_with_intervals(mock_client, "S999-01", "2026-03-02", "cancelled")

        assert result is False
        mock_client.update_event.assert_not_called()

    def test_sync_modified_event_with_none_id_returns_false(self):
        """Test that modified with None event id returns False."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {
                "id": None,
                "name": "S999-01 Test",
                "category": "WORKOUT",
                "description": "Test",
            }
        ]

        result = sync_with_intervals(
            mock_client, "S999-01", "2026-03-02", "modified", reason="Test"
        )

        assert result is False

    def test_sync_modified_update_fails(self):
        """Test that failed update for modified returns False."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {
                "id": 123,
                "name": "S999-01 Test",
                "category": "WORKOUT",
                "description": "Test",
            }
        ]
        mock_client.update_event.return_value = None

        result = sync_with_intervals(
            mock_client, "S999-01", "2026-03-02", "modified", reason="Test"
        )

        assert result is False

    def test_sync_already_marked_sautee(self):
        """Test that already marked [SAUTÉE] is not updated again."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {
                "id": 123,
                "name": "[SAUTÉE] S999-01 Test",
                "category": "NOTE",
                "description": "Already skipped",
            }
        ]

        result = sync_with_intervals(mock_client, "S999-01", "2026-03-02", "skipped")

        assert result is True
        mock_client.update_event.assert_not_called()

    def test_sync_already_marked_remplacee(self):
        """Test that already marked [REMPLACÉE] is not updated again."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {
                "id": 123,
                "name": "[REMPLACÉE] S999-01 Test",
                "category": "NOTE",
                "description": "Already replaced",
            }
        ]

        result = sync_with_intervals(mock_client, "S999-01", "2026-03-02", "replaced")

        assert result is True
        mock_client.update_event.assert_not_called()

    def test_sync_already_marked_repos(self):
        """Test that already marked [REPOS] is not updated again."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {
                "id": 123,
                "name": "[REPOS] S999-01 Test",
                "category": "NOTE",
                "description": "Already rest",
            }
        ]

        result = sync_with_intervals(mock_client, "S999-01", "2026-03-02", "rest_day")

        assert result is True
        mock_client.update_event.assert_not_called()


class TestStatusConstants:
    """Test status constants."""

    def test_statuses_to_delete_contains_expected(self):
        """Test STATUSES_TO_DELETE constant."""
        assert "cancelled" in STATUSES_TO_DELETE
        assert "skipped" in STATUSES_TO_DELETE
        assert "replaced" in STATUSES_TO_DELETE
        assert "completed" not in STATUSES_TO_DELETE

    def test_rest_day_in_statuses_to_delete(self):
        """Test rest_day is also in STATUSES_TO_DELETE."""
        assert "rest_day" in STATUSES_TO_DELETE

    def test_statuses_to_delete_count(self):
        """Test exact count of STATUSES_TO_DELETE."""
        assert len(STATUSES_TO_DELETE) == 4


class TestFindEventBySessionEdgeCases:
    """Additional edge case tests for find_event_by_session."""

    def test_find_event_empty_events_list(self):
        """Test with empty events list."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = []

        event = find_event_by_session(mock_client, "S999-01", "2026-03-02")
        assert event is None

    def test_find_event_passes_correct_dates(self):
        """Test that correct dates are passed to get_events."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = []

        find_event_by_session(mock_client, "S999-01", "2026-03-15")

        mock_client.get_events.assert_called_once_with(oldest="2026-03-15", newest="2026-03-15")

    def test_find_event_returns_first_match(self):
        """Test that first matching event is returned when multiple match."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {"id": 100, "name": "S999-01-END-Test-V001", "category": "WORKOUT"},
            {"id": 200, "name": "S999-01-END-Test-V002", "category": "WORKOUT"},
        ]

        event = find_event_by_session(mock_client, "S999-01", "2026-03-02")
        assert event["id"] == 100

    def test_find_event_partial_match(self):
        """Test that partial session_id in name still matches."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {"id": 100, "name": "S999-01-END-EnduranceDouce-V001"},
        ]

        event = find_event_by_session(mock_client, "S999-01", "2026-03-02")
        assert event is not None

    def test_find_event_missing_name_key(self):
        """Test event with missing name key uses empty string."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = [{"id": 100}]

        event = find_event_by_session(mock_client, "S999-01", "2026-03-02")
        assert event is None


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


class TestSyncCreateNote:
    """Tests for sync_with_intervals creating NOTE when no event found."""

    def test_sync_create_note_cancelled(self):
        """Test cancelled status creates NOTE with [ANNULÉE] tag when no event."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = []
        mock_client.create_event.return_value = {"id": 777}

        session_info = {
            "name": "TempoRide",
            "type": "TMP",
            "version": "V001",
            "description": "Tempo 45min",
            "tss_planned": 65,
            "duration_min": 60,
        }

        result = sync_with_intervals(
            mock_client,
            "S074-05",
            "2026-03-05",
            "cancelled",
            reason="Blessure genou",
            session_info=session_info,
        )

        assert result is True
        call_args = mock_client.create_event.call_args[0][0]
        assert call_args["category"] == "NOTE"
        assert "[ANNULÉE]" in call_args["name"]
        assert "Blessure genou" in call_args["description"]
        assert "Tempo 45min" in call_args["description"]

    def test_sync_create_note_skipped(self):
        """Test skipped status creates NOTE with [SAUTÉE] tag when no event."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = []
        mock_client.create_event.return_value = {"id": 888}

        session_info = {
            "name": "Intervals",
            "type": "INT",
            "version": "V002",
            "description": "VO2max intervals",
            "tss_planned": 80,
            "duration_min": 75,
        }

        result = sync_with_intervals(
            mock_client,
            "S074-03",
            "2026-03-03",
            "skipped",
            reason="Voyage pro",
            session_info=session_info,
        )

        assert result is True
        call_args = mock_client.create_event.call_args[0][0]
        assert "[SAUTÉE]" in call_args["name"]
        assert "Voyage pro" in call_args["description"]

    def test_sync_create_note_replaced(self):
        """Test replaced status creates NOTE with [REMPLACÉE] tag when no event."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = []
        mock_client.create_event.return_value = {"id": 444}

        session_info = {
            "name": "SweetSpot",
            "type": "SST",
            "version": "V001",
            "description": "Sweet spot 2x20",
            "tss_planned": 70,
            "duration_min": 65,
        }

        result = sync_with_intervals(
            mock_client,
            "S074-04",
            "2026-03-04",
            "replaced",
            reason="Changement programme",
            session_info=session_info,
        )

        assert result is True
        call_args = mock_client.create_event.call_args[0][0]
        assert "[REMPLACÉE]" in call_args["name"]

    def test_sync_create_note_rest_day(self):
        """Test rest_day status creates NOTE with [REPOS] tag when no event."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = []
        mock_client.create_event.return_value = {"id": 555}

        session_info = {
            "name": "Recovery",
            "type": "REC",
            "version": "V001",
            "description": "Easy spin",
            "tss_planned": 30,
            "duration_min": 40,
        }

        result = sync_with_intervals(
            mock_client,
            "S074-06",
            "2026-03-06",
            "rest_day",
            reason="Fatigue accumulée",
            session_info=session_info,
        )

        assert result is True
        call_args = mock_client.create_event.call_args[0][0]
        assert "[REPOS]" in call_args["name"]


class TestMainCLI:
    """Tests for main() CLI entry point."""

    @pytest.fixture
    def mock_planning_tower(self, tmp_path):
        """Mock Control Tower with tmp_path planning."""
        from magma_cycling.planning.control_tower import planning_tower

        original_dir = planning_tower.planning_dir
        planning_tower.planning_dir = tmp_path
        planning_tower.backup_system.planning_dir = tmp_path

        # Create planning file
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
            ],
        }
        planning_file = tmp_path / "week_planning_S999.json"
        with open(planning_file, "w", encoding="utf-8") as f:
            json.dump(planning_data, f, indent=2)

        yield tmp_path

        planning_tower.planning_dir = original_dir
        planning_tower.backup_system.planning_dir = original_dir

    def test_main_local_only(self, mock_planning_tower):
        """Test main with local update only (no --sync)."""
        with patch(
            "sys.argv",
            [
                "prog",
                "--week-id",
                "S999",
                "--session",
                "S999-01",
                "--status",
                "completed",
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_main_cancelled_requires_reason(self, mock_planning_tower):
        """Test main exits with error when cancelled without --reason."""
        with patch(
            "sys.argv",
            [
                "prog",
                "--week-id",
                "S999",
                "--session",
                "S999-01",
                "--status",
                "cancelled",
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code != 0

    def test_main_cancelled_with_reason(self, mock_planning_tower):
        """Test main with cancelled + reason succeeds locally."""
        with patch(
            "sys.argv",
            [
                "prog",
                "--week-id",
                "S999",
                "--session",
                "S999-01",
                "--status",
                "cancelled",
                "--reason",
                "Fatigue",
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_main_session_not_found(self, mock_planning_tower):
        """Test main exits 1 when session ID does not exist."""
        with patch(
            "sys.argv",
            [
                "prog",
                "--week-id",
                "S999",
                "--session",
                "S999-99",
                "--status",
                "completed",
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_sync_no_credentials(self, mock_planning_tower):
        """Test main with --sync but no credentials exits 0."""
        with (
            patch(
                "sys.argv",
                [
                    "prog",
                    "--week-id",
                    "S999",
                    "--session",
                    "S999-01",
                    "--status",
                    "completed",
                    "--sync",
                ],
            ),
            patch(
                "magma_cycling.update_session_status.create_intervals_client",
                side_effect=ValueError("No credentials"),
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_main_sync_success(self, mock_planning_tower):
        """Test main with --sync and successful sync."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = []

        with (
            patch(
                "sys.argv",
                [
                    "prog",
                    "--week-id",
                    "S999",
                    "--session",
                    "S999-01",
                    "--status",
                    "completed",
                    "--sync",
                ],
            ),
            patch(
                "magma_cycling.update_session_status.create_intervals_client",
                return_value=mock_client,
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
