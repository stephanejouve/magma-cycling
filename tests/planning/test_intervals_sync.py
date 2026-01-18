"""
Tests for intervals_sync module.

Tests bidirectional sync between local training plans/calendars and Intervals.icu.
"""

from datetime import date
from unittest.mock import Mock, patch

import pytest

from cyclisme_training_logs.config.athlete_profile import AthleteProfile
from cyclisme_training_logs.planning.calendar import TrainingCalendar, WorkoutType
from cyclisme_training_logs.planning.intervals_sync import IntervalsSync, SyncStatus
from cyclisme_training_logs.planning.planning_manager import (
    ObjectiveType,
    PriorityLevel,
    TrainingObjective,
    TrainingPlan,
)


@pytest.fixture
def master_profile():
    """Master athlete profile (54 years)."""
    return AthleteProfile(
        age=54,
        category="master",
        recovery_capacity="good",
        sleep_dependent=True,
        ftp=220,
        weight=83.8,
    )


class TestSyncStatus:
    """Tests for SyncStatus dataclass."""

    def test_sync_status_defaults(self):
        """Test SyncStatus with default values."""
        status = SyncStatus(success=True)
        assert status.success is True
        assert status.events_created == 0
        assert status.events_updated == 0
        assert status.events_deleted == 0
        assert status.errors == []
        assert status.warnings == []

    def test_sync_status_with_values(self):
        """Test SyncStatus with custom values."""
        status = SyncStatus(
            success=True,
            events_created=5,
            events_updated=3,
            events_deleted=1,
            errors=["error1"],
            warnings=["warning1"],
        )
        assert status.success is True
        assert status.events_created == 5
        assert status.events_updated == 3
        assert status.events_deleted == 1
        assert status.errors == ["error1"]
        assert status.warnings == ["warning1"]

    def test_sync_status_to_dict(self):
        """Test SyncStatus.to_dict() serialization."""
        status = SyncStatus(
            success=True,
            events_created=2,
            errors=["error1", "error2"],
        )
        result = status.to_dict()
        assert result["success"] is True
        assert result["events_created"] == 2
        assert result["errors"] == ["error1", "error2"]


class TestIntervalsSync:
    """Tests for IntervalsSync class."""

    @patch("cyclisme_training_logs.planning.intervals_sync.create_intervals_client")
    def test_init_success(self, mock_create_client):
        """Test successful initialization."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        sync = IntervalsSync()

        assert sync.client == mock_client
        mock_create_client.assert_called_once()

    @patch("cyclisme_training_logs.planning.intervals_sync.create_intervals_client")
    def test_init_missing_credentials(self, mock_create_client):
        """Test initialization fails with missing credentials."""
        mock_create_client.side_effect = ValueError("Credentials not configured")

        with pytest.raises(ValueError, match="Credentials not configured"):
            IntervalsSync()

    @patch("cyclisme_training_logs.planning.intervals_sync.create_intervals_client")
    def test_push_plan_to_intervals_success(self, mock_create_client):
        """Test successful plan push to Intervals.icu."""
        # Setup mock client
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        mock_client.create_event.return_value = {"id": 123, "name": "Test Event"}

        # Create a plan with objectives
        plan = TrainingPlan(
            name="test-plan",
            start_date=date(2026, 1, 20),
            end_date=date(2026, 2, 16),
            objectives=[
                TrainingObjective(
                    name="Gran Fondo",
                    target_date=date(2026, 2, 2),
                    objective_type=ObjectiveType.EVENT,
                    priority=PriorityLevel.HIGH,
                ),
                TrainingObjective(
                    name="FTP Test",
                    target_date=date(2026, 2, 10),
                    objective_type=ObjectiveType.FTP_TARGET,
                    priority=PriorityLevel.MEDIUM,
                    target_value=250,
                ),
            ],
        )

        # Push plan
        sync = IntervalsSync()
        status = sync.push_plan_to_intervals(plan)

        # Verify
        assert status.success is True
        assert status.events_created == 2
        assert len(status.errors) == 0
        assert mock_client.create_event.call_count == 2

    @patch("cyclisme_training_logs.planning.intervals_sync.create_intervals_client")
    def test_push_plan_to_intervals_partial_failure(self, mock_create_client):
        """Test plan push with some event creation failures."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        # First event succeeds, second fails
        mock_client.create_event.side_effect = [
            {"id": 123, "name": "Event 1"},
            None,  # Failure
        ]

        plan = TrainingPlan(
            name="test-plan",
            start_date=date(2026, 1, 20),
            end_date=date(2026, 2, 16),
            objectives=[
                TrainingObjective(
                    name="Objective 1",
                    target_date=date(2026, 2, 1),
                    objective_type=ObjectiveType.EVENT,
                    priority=PriorityLevel.HIGH,
                ),
                TrainingObjective(
                    name="Objective 2",
                    target_date=date(2026, 2, 10),
                    objective_type=ObjectiveType.MILESTONE,
                    priority=PriorityLevel.MEDIUM,
                ),
            ],
        )

        sync = IntervalsSync()
        status = sync.push_plan_to_intervals(plan)

        assert status.success is True  # At least one succeeded
        assert status.events_created == 1
        assert len(status.errors) == 1
        assert "Objective 2" in status.errors[0]

    @patch("cyclisme_training_logs.planning.intervals_sync.create_intervals_client")
    def test_push_plan_empty_objectives(self, mock_create_client):
        """Test pushing plan with no objectives."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        plan = TrainingPlan(
            name="test-plan",
            start_date=date(2026, 1, 20),
            end_date=date(2026, 2, 16),
            objectives=[],
        )

        sync = IntervalsSync()
        status = sync.push_plan_to_intervals(plan)

        assert status.success is False  # No events created
        assert status.events_created == 0
        mock_client.create_event.assert_not_called()

    @patch("cyclisme_training_logs.planning.intervals_sync.create_intervals_client")
    def test_sync_calendar_create_new_sessions(self, mock_create_client, master_profile):
        """Test syncing calendar creates new workout events."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        mock_client.get_events.return_value = []  # No existing events
        mock_client.get_activities.return_value = []
        mock_client.create_event.return_value = {"id": 123}

        calendar = TrainingCalendar(year=2026, athlete_profile=master_profile)
        calendar.add_session(
            session_date=date(2026, 1, 20),
            workout_type=WorkoutType.ENDURANCE,
            planned_tss=100,
        )
        calendar.add_session(
            session_date=date(2026, 1, 22),
            workout_type=WorkoutType.TEMPO,
            planned_tss=80,
        )

        sync = IntervalsSync()
        status = sync.sync_calendar(
            calendar=calendar,
            start_date=date(2026, 1, 20),
            end_date=date(2026, 1, 26),
        )

        assert status.success is True
        assert status.events_created == 2
        assert status.events_updated == 0
        assert mock_client.create_event.call_count == 2

    @patch("cyclisme_training_logs.planning.intervals_sync.create_intervals_client")
    def test_sync_calendar_update_existing_sessions(self, mock_create_client, master_profile):
        """Test syncing calendar updates existing workout events."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        # Mock existing events in Intervals.icu
        mock_client.get_events.return_value = [
            {
                "id": 100,
                "category": "WORKOUT",
                "name": "S003-01-END",
                "start_date_local": "2026-01-20",
            },
        ]
        mock_client.get_activities.return_value = []
        mock_client.update_event.return_value = {"id": 100, "name": "S003-01-END"}

        calendar = TrainingCalendar(year=2026, athlete_profile=master_profile)
        calendar.add_session(
            session_date=date(2026, 1, 20),
            workout_type=WorkoutType.ENDURANCE,
            planned_tss=100,
        )

        sync = IntervalsSync()
        status = sync.sync_calendar(
            calendar=calendar,
            start_date=date(2026, 1, 20),
            end_date=date(2026, 1, 26),
        )

        assert status.success is True
        assert status.events_created == 0
        assert status.events_updated == 1
        mock_client.update_event.assert_called_once()

    @patch("cyclisme_training_logs.planning.intervals_sync.create_intervals_client")
    def test_sync_calendar_import_activities(self, mock_create_client, master_profile):
        """Test syncing imports completed activities to calendar."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        mock_client.get_events.return_value = []

        # Mock completed activity in Intervals.icu
        mock_client.get_activities.return_value = [
            {
                "id": "i123",
                "start_date_local": "2026-01-20T08:00:00",
                "icu_training_load": 105,  # Actual TSS
            }
        ]
        mock_client.create_event.return_value = {"id": 123}

        calendar = TrainingCalendar(year=2026, athlete_profile=master_profile)
        calendar.add_session(
            session_date=date(2026, 1, 20),
            workout_type=WorkoutType.ENDURANCE,
            planned_tss=100,
        )

        sync = IntervalsSync()
        status = sync.sync_calendar(
            calendar=calendar,
            start_date=date(2026, 1, 20),
            end_date=date(2026, 1, 26),
        )

        # Check that actual TSS was updated from activity
        session = calendar.sessions[date(2026, 1, 20)]
        assert session.actual_tss == 105
        assert status.success is True

    @patch("cyclisme_training_logs.planning.intervals_sync.create_intervals_client")
    def test_sync_calendar_empty_calendar(self, mock_create_client, master_profile):
        """Test syncing empty calendar."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        mock_client.get_events.return_value = []
        mock_client.get_activities.return_value = []

        calendar = TrainingCalendar(year=2026, athlete_profile=master_profile)

        sync = IntervalsSync()
        status = sync.sync_calendar(
            calendar=calendar,
            start_date=date(2026, 1, 20),
            end_date=date(2026, 1, 26),
        )

        assert status.success is True
        assert status.events_created == 0
        assert status.events_updated == 0

    @patch("cyclisme_training_logs.planning.intervals_sync.create_intervals_client")
    def test_update_workout_intervals_create_new(self, mock_create_client):
        """Test updating workout creates new event if not exists."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        mock_client.get_events.return_value = []  # No existing workout
        mock_client.create_event.return_value = {"id": 123, "name": "Test Workout"}

        sync = IntervalsSync()
        status = sync.update_workout_intervals(
            workout_date=date(2026, 1, 20),
            workout_data={
                "name": "S003-01-END",
                "description": "60min @ 70% FTP",
                "planned_tss": 100,
            },
        )

        assert status.success is True
        assert status.events_created == 1
        assert status.events_updated == 0
        mock_client.create_event.assert_called_once()

    @patch("cyclisme_training_logs.planning.intervals_sync.create_intervals_client")
    def test_update_workout_intervals_update_existing(self, mock_create_client):
        """Test updating workout updates existing event."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        # Mock existing workout
        mock_client.get_events.return_value = [
            {
                "id": 100,
                "category": "WORKOUT",
                "name": "S003-01-END",
                "start_date_local": "2026-01-20",
            }
        ]
        mock_client.update_event.return_value = {"id": 100, "name": "S003-01-END"}

        sync = IntervalsSync()
        status = sync.update_workout_intervals(
            workout_date=date(2026, 1, 20),
            workout_data={
                "name": "S003-01-END",
                "description": "Updated: 90min @ 70% FTP",
                "planned_tss": 120,
            },
        )

        assert status.success is True
        assert status.events_created == 0
        assert status.events_updated == 1
        mock_client.update_event.assert_called_once()

    @patch("cyclisme_training_logs.planning.intervals_sync.create_intervals_client")
    def test_update_workout_intervals_api_failure(self, mock_create_client):
        """Test update workout handles API failure gracefully."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        mock_client.get_events.return_value = []
        mock_client.create_event.return_value = None  # API failure

        sync = IntervalsSync()
        status = sync.update_workout_intervals(
            workout_date=date(2026, 1, 20),
            workout_data={"name": "Test", "description": "Test"},
        )

        assert status.success is False
        assert status.events_created == 0
        assert len(status.errors) == 1

    @patch("cyclisme_training_logs.planning.intervals_sync.create_intervals_client")
    def test_fetch_plan_status_no_activities(self, mock_create_client):
        """Test fetching plan status with no completed activities."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        mock_client.get_events.return_value = []
        mock_client.get_activities.return_value = []

        plan = TrainingPlan(
            name="test-plan",
            start_date=date(2026, 1, 20),
            end_date=date(2026, 2, 16),
            objectives=[
                TrainingObjective(
                    name="Objective 1",
                    target_date=date(2026, 2, 1),
                    objective_type=ObjectiveType.EVENT,
                    priority=PriorityLevel.HIGH,
                ),
            ],
        )

        sync = IntervalsSync()
        status = sync.fetch_plan_status(plan)

        assert status["plan_id"] == "test-plan"
        assert status["objectives_total"] == 1
        assert status["objectives_completed"] == 0
        assert status["completion_percent"] == 0
        assert len(status["objectives"]) == 1
        assert status["objectives"][0]["completed"] is False

    @patch("cyclisme_training_logs.planning.intervals_sync.create_intervals_client")
    def test_fetch_plan_status_with_completed_activities(self, mock_create_client):
        """Test fetching plan status with completed activities."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        mock_client.get_events.return_value = []

        # Mock completed activity on objective date
        mock_client.get_activities.return_value = [
            {
                "id": "i123",
                "start_date_local": "2026-02-01T08:00:00",
                "icu_training_load": 100,
            }
        ]

        plan = TrainingPlan(
            name="test-plan",
            start_date=date(2026, 1, 20),
            end_date=date(2026, 2, 16),
            objectives=[
                TrainingObjective(
                    name="Objective 1",
                    target_date=date(2026, 2, 1),
                    objective_type=ObjectiveType.EVENT,
                    priority=PriorityLevel.HIGH,
                ),
                TrainingObjective(
                    name="Objective 2",
                    target_date=date(2026, 2, 10),
                    objective_type=ObjectiveType.FTP_TARGET,
                    priority=PriorityLevel.MEDIUM,
                ),
            ],
        )

        sync = IntervalsSync()
        status = sync.fetch_plan_status(plan)

        assert status["objectives_total"] == 2
        assert status["objectives_completed"] == 1
        assert status["completion_percent"] == 50
        assert status["objectives"][0]["completed"] is True
        assert status["objectives"][1]["completed"] is False

    @patch("cyclisme_training_logs.planning.intervals_sync.create_intervals_client")
    def test_fetch_plan_status_empty_plan(self, mock_create_client):
        """Test fetching status for plan with no objectives."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        mock_client.get_events.return_value = []
        mock_client.get_activities.return_value = []

        plan = TrainingPlan(
            name="empty-plan",
            start_date=date(2026, 1, 20),
            end_date=date(2026, 2, 16),
            objectives=[],
        )

        sync = IntervalsSync()
        status = sync.fetch_plan_status(plan)

        assert status["objectives_total"] == 0
        assert status["objectives_completed"] == 0
        assert status["completion_percent"] == 0

    @patch("cyclisme_training_logs.planning.intervals_sync.create_intervals_client")
    def test_fetch_plan_status_api_error(self, mock_create_client):
        """Test fetch_plan_status handles API errors gracefully."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        mock_client.get_events.side_effect = Exception("API Error")

        plan = TrainingPlan(
            name="test-plan",
            start_date=date(2026, 1, 20),
            end_date=date(2026, 2, 16),
            objectives=[
                TrainingObjective(
                    name="Objective 1",
                    target_date=date(2026, 2, 1),
                    objective_type=ObjectiveType.EVENT,
                    priority=PriorityLevel.HIGH,
                ),
            ],
        )

        sync = IntervalsSync()
        status = sync.fetch_plan_status(plan)

        assert "error" in status
        assert "API Error" in status["error"]
        assert status["completion_percent"] == 0
