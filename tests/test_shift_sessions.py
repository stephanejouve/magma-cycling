"""
Tests for shift_sessions tool.

Validates session shifting, swapping, and Intervals.icu synchronization.

Author: Claude Sonnet 4.5
Created: 2026-02-19
"""

import json
from datetime import date

import pytest

from cyclisme_training_logs.planning.models import Session, WeeklyPlan
from cyclisme_training_logs.shift_sessions import SessionShifter


class TestSessionShifter:
    """Test SessionShifter functionality."""

    @pytest.fixture
    def temp_planning_file(self, tmp_path):
        """Create temporary planning file for tests."""
        planning_data = {
            "week_id": "S999",
            "start_date": "2026-03-02",  # Monday
            "end_date": "2026-03-08",  # Sunday
            "created_at": "2026-02-01T20:00:00Z",
            "last_updated": "2026-02-01T20:00:00Z",
            "version": 1,
            "athlete_id": "i151223",
            "tss_target": 350,
            "planned_sessions": [
                {
                    "session_id": "S999-01",
                    "date": "2026-03-02",  # Monday
                    "name": "Session1",
                    "type": "END",
                    "version": "V001",
                    "tss_planned": 50,
                    "duration_min": 60,
                    "description": "Test session 1",
                    "status": "completed",  # Already done
                    "intervals_id": 12345,
                    "description_hash": None,
                },
                {
                    "session_id": "S999-02",
                    "date": "2026-03-03",  # Tuesday
                    "name": "Session2",
                    "type": "INT",
                    "version": "V001",
                    "tss_planned": 70,
                    "duration_min": 65,
                    "description": "Test session 2",
                    "status": "planned",
                    "intervals_id": None,
                    "description_hash": None,
                },
                {
                    "session_id": "S999-03",
                    "date": "2026-03-04",  # Wednesday
                    "name": "Session3",
                    "type": "END",
                    "version": "V001",
                    "tss_planned": 55,
                    "duration_min": 60,
                    "description": "Test session 3",
                    "status": "planned",
                    "intervals_id": 67890,
                    "description_hash": None,
                },
            ],
        }

        planning_file = tmp_path / "week_planning_S999.json"
        with open(planning_file, "w", encoding="utf-8") as f:
            json.dump(planning_data, f, indent=2)

        return planning_file

    @pytest.fixture
    def shifter(self, temp_planning_file):
        """Create SessionShifter instance."""
        planning_dir = temp_planning_file.parent
        return SessionShifter(week_id="S999", planning_dir=planning_dir)

    def test_load_planning(self, shifter):
        """Test loading planning from JSON."""
        assert shifter.week_id == "S999"
        assert len(shifter.plan.planned_sessions) == 3
        assert shifter.plan.start_date == date(2026, 3, 2)

    def test_shift_sessions_forward(self, shifter):
        """Test shifting sessions forward by 1 day."""
        # Shift from day 2 (Tuesday) forward by 1 day
        modified = shifter.shift_sessions(from_day=2, shift_days=1)

        # Should skip completed session (S999-01)
        # Should shift S999-02 and S999-03
        assert len(modified) == 2
        assert shifter.plan.planned_sessions[1].session_date == date(2026, 3, 4)  # Tue → Wed
        assert shifter.plan.planned_sessions[2].session_date == date(2026, 3, 5)  # Wed → Thu

    def test_shift_with_renumber(self, shifter):
        """Test shifting sessions with renumbering."""
        # Shift from day 2 forward by 1 day with renumbering
        shifter.shift_sessions(from_day=2, shift_days=1, renumber=True)

        # S999-02 (Tue) → Wed becomes S999-03
        # S999-03 (Wed) → Thu becomes S999-04
        assert shifter.plan.planned_sessions[1].session_id == "S999-03"
        assert shifter.plan.planned_sessions[2].session_id == "S999-04"

    def test_shift_respects_completed_status(self, shifter):
        """Test that completed sessions are not shifted."""
        # Try to shift from day 1 (Monday, which is completed)
        shifter.shift_sessions(from_day=1, shift_days=1)

        # Completed session should not be in modified list
        assert shifter.plan.planned_sessions[0].session_date == date(2026, 3, 2)  # Unchanged

    def test_swap_sessions_by_id(self, shifter):
        """Test swapping two sessions by ID."""
        # Swap S999-02 (Tuesday) and S999-03 (Wednesday)
        session1, session2 = shifter.swap_sessions(session1_id="S999-02", session2_id="S999-03")

        assert session1.session_date == date(2026, 3, 4)  # S999-02 moved to Wednesday
        assert session2.session_date == date(2026, 3, 3)  # S999-03 moved to Tuesday

    def test_swap_sessions_by_day(self, shifter):
        """Test swapping sessions by day of week."""
        # Swap day 2 (Tuesday) and day 3 (Wednesday)
        session1, session2 = shifter.swap_sessions(day1=2, day2=3)

        assert session1.session_date == date(2026, 3, 4)  # Tue → Wed
        assert session2.session_date == date(2026, 3, 3)  # Wed → Tue

    def test_swap_prevents_completed_session(self, shifter):
        """Test that swapping with completed session is prevented."""
        with pytest.raises(ValueError, match="already completed"):
            # Try to swap S999-01 (completed) with S999-02
            shifter.swap_sessions(session1_id="S999-01", session2_id="S999-02")

    def test_insert_rest_day(self, shifter):
        """Test inserting rest day and shifting subsequent sessions."""
        # Insert rest day on Friday (day 5) - after all existing sessions
        rest_session = shifter.insert_rest_day(5, description="Recovery day")

        # Check rest day was created
        assert rest_session.session_id == "S999-05"
        assert rest_session.status == "rest_day"
        assert rest_session.session_date == date(2026, 3, 6)  # Friday

        # Check we now have 4 sessions (3 original + 1 rest day)
        assert len(shifter.plan.planned_sessions) == 4

        # Original sessions should remain unchanged (no sessions after day 5 to shift)
        assert shifter.plan.planned_sessions[0].session_date == date(2026, 3, 2)  # Monday
        assert shifter.plan.planned_sessions[1].session_date == date(2026, 3, 3)  # Tuesday
        assert shifter.plan.planned_sessions[2].session_date == date(2026, 3, 4)  # Wednesday

    def test_remove_session(self, shifter):
        """Test removing a session."""
        # Remove S999-03
        removed = shifter.remove_session("S999-03")

        assert removed is True
        assert len(shifter.plan.planned_sessions) == 2
        assert all(s.session_id != "S999-03" for s in shifter.plan.planned_sessions)

    def test_save_updates_timestamp(self, shifter, temp_planning_file):
        """Test that saving updates last_updated timestamp."""
        old_timestamp = shifter.plan.last_updated

        # Modify and save
        shifter.shift_sessions(from_day=2, shift_days=1)
        shifter.save(dry_run=False, sync=False)

        # Reload and check timestamp
        plan = WeeklyPlan.from_json(temp_planning_file)
        assert plan.last_updated > old_timestamp

    def test_dry_run_does_not_save(self, shifter, temp_planning_file):
        """Test that dry run doesn't save changes."""
        # Get original state
        original_data = temp_planning_file.read_text()

        # Modify with dry run
        shifter.shift_sessions(from_day=2, shift_days=1)
        shifter.save(dry_run=True, sync=False)

        # File should be unchanged
        assert temp_planning_file.read_text() == original_data

    def test_modified_sessions_tracking(self, shifter):
        """Test that modified sessions are tracked for sync."""
        # Initially no modified sessions
        assert len(shifter.modified_sessions) == 0

        # Shift some sessions
        shifter.shift_sessions(from_day=2, shift_days=1)

        # Should track modified sessions
        assert len(shifter.modified_sessions) == 2

        # Each entry should be (session, old_date)
        for session, old_date in shifter.modified_sessions:
            assert isinstance(session, Session)
            assert isinstance(old_date, date)

    def test_swap_tracks_both_sessions(self, shifter):
        """Test that swap tracks both modified sessions."""
        # Swap two sessions
        shifter.swap_sessions(session1_id="S999-02", session2_id="S999-03")

        # Should track both sessions
        assert len(shifter.modified_sessions) == 2


class TestValidation:
    """Test validation and error handling."""

    def test_missing_planning_file(self, tmp_path):
        """Test error when planning file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            SessionShifter(week_id="S999", planning_dir=tmp_path)

    def test_swap_requires_parameters(self, tmp_path):
        """Test that swap requires either session IDs or days."""
        # Create minimal planning file
        planning_data = {
            "week_id": "S999",
            "start_date": "2026-03-02",
            "end_date": "2026-03-08",
            "created_at": "2026-02-01T20:00:00Z",
            "last_updated": "2026-02-01T20:00:00Z",
            "version": 1,
            "athlete_id": "i151223",
            "tss_target": 0,
            "planned_sessions": [],
        }

        planning_file = tmp_path / "week_planning_S999.json"
        with open(planning_file, "w", encoding="utf-8") as f:
            json.dump(planning_data, f, indent=2)

        shifter = SessionShifter(week_id="S999", planning_dir=tmp_path)

        with pytest.raises(ValueError, match="Must specify either session IDs or days"):
            shifter.swap_sessions()


class TestDisplaySummary:
    """Test display summary functionality."""

    def test_display_summary(self, tmp_path, capsys):
        """Test that display summary shows planning state."""
        # Create planning with sessions
        planning_data = {
            "week_id": "S999",
            "start_date": "2026-03-02",
            "end_date": "2026-03-08",
            "created_at": "2026-02-01T20:00:00Z",
            "last_updated": "2026-02-01T20:00:00Z",
            "version": 1,
            "athlete_id": "i151223",
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
                    "description": "Test",
                    "status": "planned",
                    "intervals_id": None,
                    "description_hash": None,
                }
            ],
        }

        planning_file = tmp_path / "week_planning_S999.json"
        with open(planning_file, "w", encoding="utf-8") as f:
            json.dump(planning_data, f, indent=2)

        shifter = SessionShifter(week_id="S999", planning_dir=tmp_path)
        shifter.display_summary()

        # Check output
        captured = capsys.readouterr()
        assert "S999" in captured.out
        assert "Session1" in captured.out
