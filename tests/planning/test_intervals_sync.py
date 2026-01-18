"""Tests for intervals_sync module (Sprint R3 Module 3)."""

from datetime import date, datetime
from unittest.mock import Mock, patch

import pytest

from cyclisme_training_logs.config.athlete_profile import AthleteProfile
from cyclisme_training_logs.planning.calendar import TrainingCalendar, WorkoutType
from cyclisme_training_logs.planning.intervals_sync import (
    CalendarDiff,
    IntervalsSync,
    SyncStatusReport,
)


@pytest.fixture
def athlete_profile():
    """Create test athlete profile."""
    return AthleteProfile(
        age=54,
        category="master",
        recovery_capacity="good",
        sleep_dependent=True,
        ftp=240,
        weight=72.5,
    )


@pytest.fixture
def calendar(athlete_profile):
    """Create test calendar with sessions."""
    cal = TrainingCalendar(year=2026, athlete_profile=athlete_profile)

    # Add 3 sessions (Mon/Wed/Fri)
    cal.add_session(
        session_date=date(2026, 1, 20),  # Monday
        workout_type=WorkoutType.ENDURANCE,
        planned_tss=80,
        duration_min=90,
        intensity_pct=70.0,
        notes="Base endurance",
    )

    cal.add_session(
        session_date=date(2026, 1, 22),  # Wednesday
        workout_type=WorkoutType.TEMPO,
        planned_tss=65,
        duration_min=60,
        intensity_pct=85.0,
        notes="Sweet spot",
    )

    cal.add_session(
        session_date=date(2026, 1, 24),  # Friday
        workout_type=WorkoutType.RECOVERY,
        planned_tss=30,
        duration_min=45,
        intensity_pct=55.0,
        notes="Active recovery",
    )

    return cal


@pytest.fixture
def mock_intervals_client():
    """Create mock Intervals.icu client."""
    mock_client = Mock()
    return mock_client


class TestCalendarDiff:
    """Tests for CalendarDiff dataclass."""

    def test_has_changes_empty(self):
        """Test has_changes() with no changes."""
        diff = CalendarDiff(
            added_remote=[],
            removed_remote=[],
            moved_remote=[],
            modified_remote=[],
        )
        assert not diff.has_changes()

    def test_has_changes_with_removed(self):
        """Test has_changes() with removed workouts."""
        diff = CalendarDiff(
            added_remote=[],
            removed_remote=[{"date": date(2026, 1, 22), "name": "Tempo"}],
            moved_remote=[],
            modified_remote=[],
        )
        assert diff.has_changes()

    def test_has_changes_with_added(self):
        """Test has_changes() with added workouts."""
        diff = CalendarDiff(
            added_remote=[{"date": date(2026, 1, 23), "name": "Extra"}],
            removed_remote=[],
            moved_remote=[],
            modified_remote=[],
        )
        assert diff.has_changes()

    def test_has_changes_with_modified(self):
        """Test has_changes() with modified workouts."""
        diff = CalendarDiff(
            added_remote=[],
            removed_remote=[],
            moved_remote=[],
            modified_remote=[{"date": date(2026, 1, 20), "delta_tss": -15}],
        )
        assert diff.has_changes()


class TestSyncStatusReport:
    """Tests for SyncStatusReport dataclass."""

    def test_summary_synced(self):
        """Test summary() when synced."""
        diff = CalendarDiff(
            added_remote=[],
            removed_remote=[],
            moved_remote=[],
            modified_remote=[],
        )
        report = SyncStatusReport(
            last_check=datetime.now(),
            is_synced=True,
            diff=diff,
            warnings=[],
        )

        summary = report.summary()
        assert "✅ Calendrier synchronisé" in summary

    def test_summary_with_changes(self):
        """Test summary() with changes."""
        diff = CalendarDiff(
            added_remote=[{"date": "2026-01-23"}],
            removed_remote=[{"date": "2026-01-22"}],
            moved_remote=[],
            modified_remote=[{"date": "2026-01-20"}],
        )
        report = SyncStatusReport(
            last_check=datetime.now(),
            is_synced=False,
            diff=diff,
            warnings=[],
        )

        summary = report.summary()
        assert "⚠️ Changements détectés:" in summary
        assert "1 workouts supprimés par coach" in summary
        assert "1 workouts ajoutés par coach" in summary
        assert "1 workouts modifiés par coach" in summary


class TestIntervalsSync:
    """Tests for IntervalsSync class."""

    def test_init(self):
        """Test IntervalsSync initialization."""
        with patch("cyclisme_training_logs.planning.intervals_sync.create_intervals_client"):
            sync = IntervalsSync()
            assert sync.client is not None

    def test_fetch_remote_calendar_empty(self, mock_intervals_client):
        """Test fetch_remote_calendar() with no events."""
        mock_intervals_client.get_events.return_value = []

        with patch(
            "cyclisme_training_logs.planning.intervals_sync.create_intervals_client"
        ) as mock_create:
            mock_create.return_value = mock_intervals_client

            sync = IntervalsSync()
            calendar = sync.fetch_remote_calendar(
                start_date=date(2026, 1, 20),
                end_date=date(2026, 1, 26),
            )

            assert calendar == {}
            mock_intervals_client.get_events.assert_called_once_with(
                oldest="2026-01-20",
                newest="2026-01-26",
            )

    def test_fetch_remote_calendar_with_workouts(self, mock_intervals_client):
        """Test fetch_remote_calendar() with workouts."""
        mock_intervals_client.get_events.return_value = [
            {
                "id": 89100872,
                "category": "WORKOUT",
                "name": "S077-01-END-Endurance",
                "start_date_local": "2026-01-20T17:00:00",
                "description": "Endurance workout",
            },
            {
                "id": 89100873,
                "category": "NOTE",  # Should be filtered out
                "name": "Recovery note",
                "start_date_local": "2026-01-21T17:00:00",
            },
            {
                "id": 89100874,
                "category": "WORKOUT",
                "name": "S077-03-TEMPO-Tempo",
                "start_date_local": "2026-01-22T17:00:00",
                "description": "Tempo workout",
            },
        ]

        with patch(
            "cyclisme_training_logs.planning.intervals_sync.create_intervals_client"
        ) as mock_create:
            mock_create.return_value = mock_intervals_client

            sync = IntervalsSync()
            calendar = sync.fetch_remote_calendar(
                start_date=date(2026, 1, 20),
                end_date=date(2026, 1, 26),
            )

            # Should have 2 workouts (NOTE filtered out)
            assert len(calendar) == 2
            assert date(2026, 1, 20) in calendar
            assert date(2026, 1, 22) in calendar
            assert calendar[date(2026, 1, 20)]["name"] == "S077-01-END-Endurance"

    def test_detect_changes_no_changes(self, calendar, mock_intervals_client):
        """Test detect_changes() when local and remote are synced."""
        # Mock remote calendar matching local
        mock_intervals_client.get_events.return_value = [
            {
                "id": 1,
                "category": "WORKOUT",
                "name": "S077-01-ENDURANCE-Base",
                "start_date_local": "2026-01-20T17:00:00",
            },
            {
                "id": 2,
                "category": "WORKOUT",
                "name": "S077-03-TEMPO-SweetSpot",
                "start_date_local": "2026-01-22T17:00:00",
            },
            {
                "id": 3,
                "category": "WORKOUT",
                "name": "S077-05-RECOVERY-Active",
                "start_date_local": "2026-01-24T17:00:00",
            },
        ]

        with patch(
            "cyclisme_training_logs.planning.intervals_sync.create_intervals_client"
        ) as mock_create:
            mock_create.return_value = mock_intervals_client

            sync = IntervalsSync()
            diff = sync.detect_changes(
                local_calendar=calendar,
                start_date=date(2026, 1, 20),
                end_date=date(2026, 1, 26),
            )

            assert not diff.has_changes()
            assert len(diff.removed_remote) == 0
            assert len(diff.added_remote) == 0
            assert len(diff.modified_remote) == 0

    def test_detect_changes_workout_removed_by_coach(self, calendar, mock_intervals_client):
        """Test detect_changes() when coach deletes a workout."""
        # Mock remote calendar missing Wednesday workout
        mock_intervals_client.get_events.return_value = [
            {
                "id": 1,
                "category": "WORKOUT",
                "name": "S077-01-ENDURANCE-Base",
                "start_date_local": "2026-01-20T17:00:00",
            },
            # Wednesday (2026-01-22) missing - coach deleted it
            {
                "id": 3,
                "category": "WORKOUT",
                "name": "S077-05-RECOVERY-Active",
                "start_date_local": "2026-01-24T17:00:00",
            },
        ]

        with patch(
            "cyclisme_training_logs.planning.intervals_sync.create_intervals_client"
        ) as mock_create:
            mock_create.return_value = mock_intervals_client

            sync = IntervalsSync()
            diff = sync.detect_changes(
                local_calendar=calendar,
                start_date=date(2026, 1, 20),
                end_date=date(2026, 1, 26),
            )

            assert diff.has_changes()
            assert len(diff.removed_remote) == 1
            assert diff.removed_remote[0]["date"] == date(2026, 1, 22)
            assert "TEMPO" in diff.removed_remote[0]["name"]

    def test_detect_changes_workout_added_by_coach(self, calendar, mock_intervals_client):
        """Test detect_changes() when coach adds a workout."""
        # Mock remote calendar with extra Saturday workout
        mock_intervals_client.get_events.return_value = [
            {
                "id": 1,
                "category": "WORKOUT",
                "name": "S077-01-ENDURANCE-Base",
                "start_date_local": "2026-01-20T17:00:00",
            },
            {
                "id": 2,
                "category": "WORKOUT",
                "name": "S077-03-TEMPO-SweetSpot",
                "start_date_local": "2026-01-22T17:00:00",
            },
            {
                "id": 3,
                "category": "WORKOUT",
                "name": "S077-05-RECOVERY-Active",
                "start_date_local": "2026-01-24T17:00:00",
            },
            {
                "id": 4,
                "category": "WORKOUT",
                "name": "S077-06-INT-CoachAdded",
                "start_date_local": "2026-01-25T09:00:00",  # Saturday - coach added
            },
        ]

        with patch(
            "cyclisme_training_logs.planning.intervals_sync.create_intervals_client"
        ) as mock_create:
            mock_create.return_value = mock_intervals_client

            sync = IntervalsSync()
            diff = sync.detect_changes(
                local_calendar=calendar,
                start_date=date(2026, 1, 20),
                end_date=date(2026, 1, 26),
            )

            assert diff.has_changes()
            assert len(diff.added_remote) == 1
            assert diff.added_remote[0]["date"] == date(2026, 1, 25)
            assert "CoachAdded" in diff.added_remote[0]["name"]

    def test_detect_changes_workout_modified_by_coach(self, calendar, mock_intervals_client):
        """Test detect_changes() when coach modifies a workout."""
        # Mock remote calendar with modified Wednesday workout (changed type)
        mock_intervals_client.get_events.return_value = [
            {
                "id": 1,
                "category": "WORKOUT",
                "name": "S077-01-ENDURANCE-Base",
                "start_date_local": "2026-01-20T17:00:00",
            },
            {
                "id": 2,
                "category": "WORKOUT",
                "name": "S077-03-RECOVERY-CoachModified",  # Was TEMPO, now RECOVERY
                "start_date_local": "2026-01-22T17:00:00",
            },
            {
                "id": 3,
                "category": "WORKOUT",
                "name": "S077-05-RECOVERY-Active",
                "start_date_local": "2026-01-24T17:00:00",
            },
        ]

        with patch(
            "cyclisme_training_logs.planning.intervals_sync.create_intervals_client"
        ) as mock_create:
            mock_create.return_value = mock_intervals_client

            sync = IntervalsSync()
            diff = sync.detect_changes(
                local_calendar=calendar,
                start_date=date(2026, 1, 20),
                end_date=date(2026, 1, 26),
            )

            assert diff.has_changes()
            assert len(diff.modified_remote) == 1
            assert diff.modified_remote[0]["date"] == date(2026, 1, 22)

    def test_get_sync_status_synced(self, calendar, mock_intervals_client):
        """Test get_sync_status() when synced."""
        # Mock remote calendar matching local
        mock_intervals_client.get_events.return_value = [
            {
                "id": 1,
                "category": "WORKOUT",
                "name": "S077-01-ENDURANCE-Base",
                "start_date_local": "2026-01-20T17:00:00",
            },
            {
                "id": 2,
                "category": "WORKOUT",
                "name": "S077-03-TEMPO-SweetSpot",
                "start_date_local": "2026-01-22T17:00:00",
            },
            {
                "id": 3,
                "category": "WORKOUT",
                "name": "S077-05-RECOVERY-Active",
                "start_date_local": "2026-01-24T17:00:00",
            },
        ]

        with patch(
            "cyclisme_training_logs.planning.intervals_sync.create_intervals_client"
        ) as mock_create:
            mock_create.return_value = mock_intervals_client

            sync = IntervalsSync()
            status = sync.get_sync_status(
                calendar=calendar,
                start_date=date(2026, 1, 20),
                end_date=date(2026, 1, 26),
            )

            assert status.is_synced
            assert len(status.warnings) == 0
            assert "✅ Calendrier synchronisé" in status.summary()

    def test_get_sync_status_with_changes(self, calendar, mock_intervals_client):
        """Test get_sync_status() with changes detected."""
        # Mock remote calendar with changes
        mock_intervals_client.get_events.return_value = [
            {
                "id": 1,
                "category": "WORKOUT",
                "name": "S077-01-ENDURANCE-Base",
                "start_date_local": "2026-01-20T17:00:00",
            },
            # Wednesday missing (removed by coach)
            {
                "id": 3,
                "category": "WORKOUT",
                "name": "S077-05-RECOVERY-Active",
                "start_date_local": "2026-01-24T17:00:00",
            },
            {
                "id": 4,
                "category": "WORKOUT",
                "name": "S077-06-INT-CoachAdded",
                "start_date_local": "2026-01-25T09:00:00",  # Added by coach
            },
        ]

        with patch(
            "cyclisme_training_logs.planning.intervals_sync.create_intervals_client"
        ) as mock_create:
            mock_create.return_value = mock_intervals_client

            sync = IntervalsSync()
            status = sync.get_sync_status(
                calendar=calendar,
                start_date=date(2026, 1, 20),
                end_date=date(2026, 1, 26),
            )

            assert not status.is_synced
            assert len(status.warnings) == 2
            assert "⚠️ Changements détectés:" in status.summary()
            assert "supprimé" in status.warnings[0]
            assert "ajouté" in status.warnings[1]
