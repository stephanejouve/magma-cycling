"""Extended tests for shift_sessions — sync, edge cases, error handling.

Extends test_shift_sessions.py with:
- sync_session_changes with mock IntervalsClient
- Boundary overflow (shift beyond week)
- Shift backward
- Shift from session_id
- Insert rest day on existing session (error)
- Remove non-existent session
- Shift requires from_session_id or from_day
- Session not found errors
"""

import json
from datetime import date
from unittest.mock import MagicMock

import pytest

from magma_cycling.planning.models import WeeklyPlan
from magma_cycling.shift_sessions import SessionShifter


@pytest.fixture
def planning_data():
    """Base planning data for tests."""
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
                "description": "Easy ride",
                "status": "completed",
                "intervals_id": 11111,
                "description_hash": None,
            },
            {
                "session_id": "S999-02",
                "date": "2026-03-03",
                "name": "Intervals",
                "type": "INT",
                "version": "V001",
                "tss_planned": 70,
                "duration_min": 65,
                "description": "VO2max",
                "status": "planned",
                "intervals_id": 22222,
                "description_hash": None,
            },
            {
                "session_id": "S999-04",
                "date": "2026-03-05",
                "name": "Sweet Spot",
                "type": "FTP",
                "version": "V001",
                "tss_planned": 65,
                "duration_min": 70,
                "description": "Threshold",
                "status": "planned",
                "intervals_id": None,
                "description_hash": None,
            },
            {
                "session_id": "S999-06",
                "date": "2026-03-07",
                "name": "Long Ride",
                "type": "END",
                "version": "V001",
                "tss_planned": 90,
                "duration_min": 120,
                "description": "Weekend ride",
                "status": "planned",
                "intervals_id": 44444,
                "description_hash": None,
            },
        ],
    }


@pytest.fixture
def shifter(tmp_path, planning_data):
    """Create SessionShifter from temp file."""
    planning_file = tmp_path / "week_planning_S999.json"
    with open(planning_file, "w", encoding="utf-8") as f:
        json.dump(planning_data, f, indent=2)
    return SessionShifter(week_id="S999", planning_dir=tmp_path)


class TestSyncSessionChanges:
    """Test sync_session_changes with mock IntervalsClient."""

    def test_sync_updates_events(self, shifter):
        """Test successful sync with Intervals.icu."""
        shifter.shift_sessions(from_day=2, shift_days=1)

        client = MagicMock()
        client.get_event.return_value = {"id": 22222, "start_date_local": "2026-03-03"}
        client.update_event.return_value = True

        result = shifter.sync_session_changes(client)

        assert result is True
        assert client.update_event.called

    def test_sync_skips_no_intervals_id(self, shifter):
        """Test sync skips sessions without intervals_id."""
        # S999-04 has no intervals_id
        shifter.shift_sessions(from_session_id="S999-04", shift_days=1, stop_at_completed=False)

        client = MagicMock()
        result = shifter.sync_session_changes(client)

        # Should succeed without calling update_event for the no-id session
        assert result is True

    def test_sync_no_modifications(self, shifter):
        """Test sync with no modified sessions."""
        client = MagicMock()
        result = shifter.sync_session_changes(client)

        assert result is True
        client.get_event.assert_not_called()

    def test_sync_handles_missing_event(self, shifter):
        """Test sync handles event not found on Intervals.icu."""
        shifter.shift_sessions(from_day=2, shift_days=1)

        client = MagicMock()
        client.get_event.return_value = None

        shifter.sync_session_changes(client)

        # Not all synced, but shouldn't crash
        client.update_event.assert_not_called()

    def test_sync_handles_api_error(self, shifter):
        """Test sync handles API errors gracefully."""
        shifter.shift_sessions(from_day=2, shift_days=1)

        client = MagicMock()
        client.get_event.side_effect = Exception("API down")

        # Should not raise
        result = shifter.sync_session_changes(client)
        assert result is False


class TestShiftEdgeCases:
    """Test edge cases for shift operations."""

    def test_shift_backward(self, shifter):
        """Test shifting sessions backward."""
        # Shift from Thursday (day 4=S999-04) backward by 1
        shifter.shift_sessions(from_session_id="S999-04", shift_days=-1)

        # S999-04 was on 2026-03-05 (Thu) → 2026-03-04 (Wed)
        session = next(s for s in shifter.plan.planned_sessions if s.session_id == "S999-04")
        assert session.session_date == date(2026, 3, 4)

    def test_shift_boundary_overflow_skipped(self, shifter):
        """Test sessions outside week boundaries are skipped."""
        # Shift S999-06 (Saturday) forward by 2 → would be Monday next week
        shifter.shift_sessions(from_session_id="S999-06", shift_days=2)

        # Should be skipped (outside week boundaries)
        session = next(s for s in shifter.plan.planned_sessions if s.session_id == "S999-06")
        assert session.session_date == date(2026, 3, 7)  # Unchanged

    def test_shift_from_session_id(self, shifter):
        """Test shifting from a specific session_id."""
        modified = shifter.shift_sessions(from_session_id="S999-04", shift_days=1)

        # Only S999-04 and S999-06 should be shifted (skip completed S999-01)
        assert len(modified) == 2

    def test_shift_requires_from_param(self, shifter):
        """Test ValueError when neither from_session_id nor from_day given."""
        with pytest.raises(ValueError, match="Must specify either"):
            shifter.shift_sessions()

    def test_shift_session_not_found(self, shifter):
        """Test ValueError when session_id not found."""
        with pytest.raises(ValueError, match="not found"):
            shifter.shift_sessions(from_session_id="S999-99")

    def test_shift_no_sessions_after_day(self, shifter):
        """Test ValueError when no sessions on or after day."""
        # No session on Sunday (day 7) or later
        with pytest.raises(ValueError, match="No sessions found"):
            shifter.shift_sessions(from_day=8)

    def test_shift_all_completed_not_shifted(self, shifter):
        """Test that stop_at_completed=True skips completed sessions."""
        shifter.shift_sessions(from_day=1, shift_days=1, stop_at_completed=True)

        # S999-01 is completed, should be skipped
        completed = next(s for s in shifter.plan.planned_sessions if s.session_id == "S999-01")
        assert completed.session_date == date(2026, 3, 2)


class TestInsertRestDayEdgeCases:
    """Test insert_rest_day edge cases."""

    def test_insert_rest_on_existing_session(self, shifter):
        """Test error when inserting rest on day with existing session."""
        # Day 2 (Tuesday) already has S999-02
        with pytest.raises(ValueError, match="already exists"):
            shifter.insert_rest_day(2)


class TestSwapEdgeCases:
    """Test swap edge cases."""

    def test_swap_nonexistent_session_by_id(self, shifter):
        """Test error swapping non-existent session by ID."""
        with pytest.raises(ValueError, match="not found"):
            shifter.swap_sessions(session1_id="S999-02", session2_id="S999-99")

    def test_swap_nonexistent_session_by_day(self, shifter):
        """Test error swapping on day with no session."""
        with pytest.raises(ValueError, match="No session found"):
            shifter.swap_sessions(day1=2, day2=3)  # Day 3 has no session


class TestRemoveEdgeCases:
    """Test remove_session edge cases."""

    def test_remove_nonexistent_session(self, shifter):
        """Test removing non-existent session returns False."""
        result = shifter.remove_session("S999-99")
        assert result is False
        assert len(shifter.plan.planned_sessions) == 4  # Unchanged


class TestControlTowerMode:
    """Test Control Tower mode behavior."""

    def test_init_with_plan(self, tmp_path, planning_data):
        """Test initialization with plan (Control Tower mode)."""
        planning_file = tmp_path / "week_planning_S999.json"
        with open(planning_file, "w", encoding="utf-8") as f:
            json.dump(planning_data, f, indent=2)
        plan = WeeklyPlan.from_json(planning_file)
        shifter = SessionShifter(week_id="S999", plan=plan)

        assert shifter.planning_file is None
        assert len(shifter.plan.planned_sessions) == 4

    def test_save_control_tower_mode(self, tmp_path, planning_data):
        """Test save in Control Tower mode."""
        planning_file = tmp_path / "week_planning_S999.json"
        with open(planning_file, "w", encoding="utf-8") as f:
            json.dump(planning_data, f, indent=2)
        plan = WeeklyPlan.from_json(planning_file)
        shifter = SessionShifter(week_id="S999", plan=plan)

        result = shifter.save(dry_run=False, sync=False)

        assert result is True
