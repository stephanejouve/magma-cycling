"""
Tests for planned_sessions_checker tool.

Tests the session compliance checker including:
- Planned workout retrieval
- Activity matching logic
- Skipped session detection
- Markdown report generation
- Error handling

Author: Claude Sonnet 4.5
Created: 2026-02-19
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from cyclisme_training_logs.planned_sessions_checker import PlannedSessionsChecker


class TestPlannedSessionsCheckerInit:
    """Test PlannedSessionsChecker initialization."""

    def test_init_with_credentials(self):
        """Test initialization with valid credentials."""
        checker = PlannedSessionsChecker(athlete_id="iXXXXXX", api_key="test_api_key_12345")

        assert checker.athlete_id == "iXXXXXX"
        assert checker.api is not None

    def test_api_client_is_created(self):
        """Test that IntervalsClient is properly instantiated."""
        checker = PlannedSessionsChecker(athlete_id="iXXXXXX", api_key="test_key")

        # Verify API client has required methods
        assert hasattr(checker.api, "get_events")
        assert hasattr(checker.api, "get_activities")


class TestGetPlannedWorkouts:
    """Test get_planned_workouts method."""

    @pytest.fixture
    def mock_checker(self):
        """Create checker with mocked API."""
        checker = PlannedSessionsChecker(athlete_id="iXXXXXX", api_key="test_key")
        checker.api = MagicMock()
        return checker

    def test_get_planned_workouts_filters_by_category(self, mock_checker):
        """Test that only WORKOUT category events are returned."""
        # Mock API response with mixed categories
        mock_checker.api.get_events.return_value = [
            {"id": 1, "name": "Workout 1", "category": "WORKOUT"},
            {"id": 2, "name": "Note 1", "category": "NOTE"},
            {"id": 3, "name": "Workout 2", "category": "WORKOUT"},
            {"id": 4, "name": "Race", "category": "RACE"},
        ]

        workouts = mock_checker.get_planned_workouts("2026-01-01", "2026-01-07")

        assert len(workouts) == 2
        assert all(w["category"] == "WORKOUT" for w in workouts)

    def test_get_planned_workouts_with_custom_category(self, mock_checker):
        """Test filtering by custom category."""
        mock_checker.api.get_events.return_value = [
            {"id": 1, "name": "Race 1", "category": "RACE"},
            {"id": 2, "name": "Workout 1", "category": "WORKOUT"},
        ]

        races = mock_checker.get_planned_workouts("2026-01-01", "2026-01-07", category="RACE")

        assert len(races) == 1
        assert races[0]["category"] == "RACE"

    def test_get_planned_workouts_handles_api_error(self, mock_checker):
        """Test error handling when API fails."""
        mock_checker.api.get_events.side_effect = Exception("API Error")

        workouts = mock_checker.get_planned_workouts("2026-01-01", "2026-01-07")

        assert workouts == []

    def test_get_planned_workouts_empty_result(self, mock_checker):
        """Test handling of empty result set."""
        mock_checker.api.get_events.return_value = []

        workouts = mock_checker.get_planned_workouts("2026-01-01", "2026-01-07")

        assert workouts == []


class TestFindMatchingActivity:
    """Test _find_matching_activity method."""

    @pytest.fixture
    def mock_checker(self):
        """Create checker for testing."""
        checker = PlannedSessionsChecker(athlete_id="iXXXXXX", api_key="test_key")
        return checker

    def test_match_by_session_code(self, mock_checker):
        """Test matching by session code (S081-01) in activity name."""
        workout = {
            "start_date_local": "2026-03-02T10:00:00Z",
            "name": "S081-01",  # Simple code
        }

        activities = [
            {
                "id": 123,
                "start_date_local": "2026-03-02T10:15:00Z",
                "name": "Sortie vélo S081-01",  # Code in activity name
            },
            {
                "id": 456,
                "start_date_local": "2026-03-02T11:00:00Z",
                "name": "S081-02 Intervals",
            },
        ]

        match = mock_checker._find_matching_activity(workout, activities)

        assert match is not None
        assert match["id"] == 123

    def test_match_by_workout_name(self, mock_checker):
        """Test matching by workout name in activity name."""
        workout = {
            "start_date_local": "2026-03-02T10:00:00Z",
            "name": "ENDURANCE DOUCE",
        }

        activities = [
            {
                "id": 789,
                "start_date_local": "2026-03-02T10:30:00Z",
                "name": "Endurance Douce - Sortie récup",
            }
        ]

        match = mock_checker._find_matching_activity(workout, activities)

        assert match is not None
        assert match["id"] == 789

    def test_match_by_activity_name_in_workout(self, mock_checker):
        """Test inverse matching (activity name in workout)."""
        workout = {
            "start_date_local": "2026-03-02T10:00:00Z",
            "name": "VÉLO ROUTE ENDURANCE",
        }

        activities = [
            {
                "id": 999,
                "start_date_local": "2026-03-02T10:00:00Z",
                "name": "VÉLO ROUTE",
            }
        ]

        match = mock_checker._find_matching_activity(workout, activities)

        assert match is not None
        assert match["id"] == 999

    def test_no_match_time_too_far(self, mock_checker):
        """Test no match when time difference exceeds tolerance."""
        workout = {
            "start_date_local": "2026-03-02T10:00:00Z",
            "name": "S081-01 EnduranceDouce",
        }

        activities = [
            {
                "id": 123,
                "start_date_local": "2026-03-02T20:00:00Z",  # 10 hours later
                "name": "S081-01 Sortie",
            }
        ]

        # Default tolerance is 6 hours
        match = mock_checker._find_matching_activity(workout, activities)

        assert match is None

    def test_match_with_custom_tolerance(self, mock_checker):
        """Test matching with custom time tolerance."""
        workout = {
            "start_date_local": "2026-03-02T10:00:00Z",
            "name": "S081-01",  # Simple code
        }

        activities = [
            {
                "id": 123,
                "start_date_local": "2026-03-02T20:00:00Z",  # 10 hours later
                "name": "S081-01 Sortie",  # Code matches
            }
        ]

        # Use 24h tolerance
        match = mock_checker._find_matching_activity(workout, activities, tolerance_hours=24)

        assert match is not None
        assert match["id"] == 123

    def test_no_match_different_names(self, mock_checker):
        """Test no match when names don't overlap."""
        workout = {
            "start_date_local": "2026-03-02T10:00:00Z",
            "name": "S081-01 EnduranceDouce",
        }

        activities = [
            {
                "id": 456,
                "start_date_local": "2026-03-02T10:15:00Z",
                "name": "S081-02 Completely Different",
            }
        ]

        match = mock_checker._find_matching_activity(workout, activities)

        assert match is None


class TestDetectSkippedSessions:
    """Test detect_skipped_sessions method."""

    @pytest.fixture
    def mock_checker(self):
        """Create checker with mocked API."""
        checker = PlannedSessionsChecker(athlete_id="iXXXXXX", api_key="test_key")
        checker.api = MagicMock()
        return checker

    def test_detect_skipped_sessions_basic(self, mock_checker):
        """Test basic skipped session detection."""
        # Mock planned workout (past date, naive datetime to match production behavior)
        past_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")
        mock_checker.api.get_events.return_value = [
            {
                "id": 123,
                "start_date_local": past_date,
                "name": "S081-01 EnduranceDouce",
                "category": "WORKOUT",
                "load": 50,
                "duration": 3600,
                "description": "Test workout",
            }
        ]

        # Mock no matching activities
        mock_checker.api.get_activities.return_value = []

        skipped = mock_checker.detect_skipped_sessions("2026-01-01", "2026-12-31")

        assert len(skipped) == 1
        assert skipped[0]["status"] == "SKIPPED"
        assert skipped[0]["planned_id"] == 123
        assert skipped[0]["planned_tss"] == 50

    def test_detect_skipped_excludes_future_workouts(self, mock_checker):
        """Test that future workouts are excluded by default."""
        # Mock future workout (naive datetime)
        future_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")
        mock_checker.api.get_events.return_value = [
            {
                "id": 456,
                "start_date_local": future_date,
                "name": "S081-05 Future Workout",
                "category": "WORKOUT",
                "load": 70,
                "duration": 4200,
                "description": "Future session",
            }
        ]

        mock_checker.api.get_activities.return_value = []

        skipped = mock_checker.detect_skipped_sessions(
            "2026-01-01", "2026-12-31", exclude_future=True
        )

        # Future workout should not be in skipped list
        assert len(skipped) == 0

    def test_detect_skipped_includes_future_when_disabled(self, mock_checker):
        """Test including future workouts when exclude_future=False."""
        future_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")
        mock_checker.api.get_events.return_value = [
            {
                "id": 456,
                "start_date_local": future_date,
                "name": "S081-05 Future Workout",
                "category": "WORKOUT",
                "load": 70,
                "duration": 4200,
            }
        ]

        mock_checker.api.get_activities.return_value = []

        skipped = mock_checker.detect_skipped_sessions(
            "2026-01-01", "2026-12-31", exclude_future=False
        )

        assert len(skipped) == 1

    def test_detect_skipped_matches_executed_workout(self, mock_checker):
        """Test that executed workouts are not marked as skipped."""
        workout_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")

        mock_checker.api.get_events.return_value = [
            {
                "id": 123,
                "start_date_local": workout_date,
                "name": "S081-01",  # Simple code
                "category": "WORKOUT",
                "load": 50,
                "duration": 3600,
            }
        ]

        # Mock matching activity
        activity_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")
        mock_checker.api.get_activities.return_value = [
            {
                "id": 999,
                "start_date_local": activity_date,
                "name": "S081-01 Sortie vélo",  # Contains code
            }
        ]

        skipped = mock_checker.detect_skipped_sessions("2026-01-01", "2026-12-31")

        # Workout was executed, should not be skipped
        assert len(skipped) == 0

    def test_detect_skipped_handles_api_error(self, mock_checker):
        """Test handling when activities API fails."""
        mock_checker.api.get_events.return_value = [
            {
                "id": 123,
                "start_date_local": "2026-03-02T10:00:00Z",
                "name": "S081-01 Test",
                "category": "WORKOUT",
            }
        ]

        mock_checker.api.get_activities.side_effect = Exception("API Error")

        skipped = mock_checker.detect_skipped_sessions("2026-01-01", "2026-12-31")

        # Should return empty list on error
        assert skipped == []

    def test_detect_skipped_no_planned_workouts(self, mock_checker):
        """Test handling when no planned workouts exist."""
        mock_checker.api.get_events.return_value = []

        skipped = mock_checker.detect_skipped_sessions("2026-01-01", "2026-12-31")

        assert skipped == []


class TestGenerateSkippedSessionMarkdown:
    """Test generate_skipped_session_markdown method."""

    @pytest.fixture
    def mock_checker(self):
        """Create checker for testing."""
        checker = PlannedSessionsChecker(athlete_id="iXXXXXX", api_key="test_key")
        return checker

    def test_generate_markdown_basic(self, mock_checker):
        """Test markdown generation with basic data."""
        skipped_session = {
            "planned_name": "S081-01 EnduranceDouce",
            "planned_date": "2026-03-02",
            "day_of_week": "Monday",
            "days_ago": 3,
            "planned_tss": 50,
            "planned_duration": 3600,  # 60 minutes
        }

        markdown = mock_checker.generate_skipped_session_markdown(skipped_session)

        assert "S081-01 EnduranceDouce" in markdown
        assert "[SAUTÉE]" in markdown
        assert "50 TSS" in markdown
        assert "60min" in markdown
        assert "3 jour" in markdown

    def test_generate_markdown_with_metrics(self, mock_checker):
        """Test markdown generation with pre-session metrics."""
        skipped_session = {
            "planned_name": "S081-02 Intervals",
            "planned_date": "2026-03-03",
            "day_of_week": "Tuesday",
            "days_ago": 2,
            "planned_tss": 70,
            "planned_duration": 4200,  # 70 minutes
        }

        metrics_pre = {
            "ctl": 65.5,
            "atl": 55.2,
            "tsb": 10.3,
        }

        markdown = mock_checker.generate_skipped_session_markdown(skipped_session, metrics_pre)

        assert "65.5" in markdown  # CTL
        assert "55.2" in markdown  # ATL
        assert "10.3" in markdown  # TSB

    def test_generate_markdown_no_metrics(self, mock_checker):
        """Test markdown generation without metrics (N/A values)."""
        skipped_session = {
            "planned_name": "S081-03 Test",
            "planned_date": "2026-03-04",
            "day_of_week": "Wednesday",
            "days_ago": 1,
            "planned_tss": 60,
            "planned_duration": 3600,
        }

        markdown = mock_checker.generate_skipped_session_markdown(skipped_session)

        assert "N/A" in markdown  # Metrics should show N/A

    def test_generate_markdown_plural_days(self, mock_checker):
        """Test plural 'jours' for multiple days."""
        skipped_session = {
            "planned_name": "Test",
            "planned_date": "2026-03-01",
            "day_of_week": "Monday",
            "days_ago": 5,
            "planned_tss": 50,
            "planned_duration": 3600,
        }

        markdown = mock_checker.generate_skipped_session_markdown(skipped_session)

        assert "5 jours" in markdown


class TestMainFunction:
    """Test main CLI function."""

    @patch("cyclisme_training_logs.planned_sessions_checker.PlannedSessionsChecker")
    @patch("cyclisme_training_logs.planned_sessions_checker.get_data_config")
    @patch("builtins.open", create=True)
    def test_main_with_valid_config(self, mock_open, mock_get_config, mock_checker_class):
        """Test main function with valid configuration."""
        from io import StringIO

        from cyclisme_training_logs.planned_sessions_checker import main

        # Mock config file content
        mock_config_data = '{"athlete_id": "iXXXXXX", "api_key": "test_key"}'
        mock_open.return_value.__enter__.return_value = StringIO(mock_config_data)

        # Mock checker instance
        mock_checker = MagicMock()
        mock_checker.detect_skipped_sessions.return_value = []
        mock_checker_class.return_value = mock_checker

        # Mock config
        mock_config = MagicMock()
        mock_config.week_planning_dir = MagicMock()
        mock_get_config.return_value = mock_config

        # Run main (should not raise exception)
        try:
            main()
        except FileNotFoundError:
            # Expected when config file doesn't actually exist in test environment
            pass
