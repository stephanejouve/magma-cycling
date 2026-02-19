"""
Tests for daily_sync tool.

Tests the daily synchronization functionality including:
- Week calculation
- Activity tracking
- Duplicate detection
- Daily sync initialization

Author: Claude Sonnet 4.5
Created: 2026-02-19
"""

import json
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from cyclisme_training_logs.daily_sync import (
    ActivityTracker,
    DailySync,
    calculate_current_week_info,
)


class TestCalculateCurrentWeekInfo:
    """Test calculate_current_week_info function."""

    @patch("cyclisme_training_logs.daily_sync.get_week_config")
    def test_calculate_current_week_info_default(self, mock_get_config):
        """Test calculating current week info for today."""
        # Mock config with S001 reference date
        mock_config = MagicMock()
        mock_config.get_s001_date_obj.return_value = date(2024, 7, 15)  # S001 Monday
        mock_get_config.return_value = mock_config

        # Calculate for a specific date (S002 would be one week later)
        test_date = date(2024, 7, 22)  # One week after S001

        week_id, start_date = calculate_current_week_info(test_date)

        assert week_id == "S002"
        assert start_date == date(2024, 7, 22)

    @patch("cyclisme_training_logs.daily_sync.get_week_config")
    def test_calculate_current_week_info_far_future(self, mock_get_config):
        """Test calculating week info for future date."""
        mock_config = MagicMock()
        mock_config.get_s001_date_obj.return_value = date(2024, 7, 15)  # S001
        mock_get_config.return_value = mock_config

        # Test S100 (99 weeks after S001)
        test_date = date(2024, 7, 15) + timedelta(weeks=99)

        week_id, start_date = calculate_current_week_info(test_date)

        assert week_id == "S100"
        assert start_date == date(2024, 7, 15) + timedelta(weeks=99)

    @patch("cyclisme_training_logs.daily_sync.get_week_config")
    @patch("cyclisme_training_logs.daily_sync.date")
    def test_calculate_current_week_info_uses_today_by_default(self, mock_date, mock_get_config):
        """Test that None uses today's date."""
        mock_today = date(2024, 7, 22)
        mock_date.today.return_value = mock_today

        mock_config = MagicMock()
        mock_config.get_s001_date_obj.return_value = date(2024, 7, 15)
        mock_get_config.return_value = mock_config

        week_id, start_date = calculate_current_week_info(target_date=None)

        # Should calculate based on today
        mock_date.today.assert_called_once()


class TestActivityTracker:
    """Test ActivityTracker class."""

    @pytest.fixture
    def temp_tracking_file(self, tmp_path):
        """Create temp tracking file."""
        return tmp_path / "tracking.json"

    def test_init_new_file(self, temp_tracking_file):
        """Test initialization with new tracking file."""
        tracker = ActivityTracker(temp_tracking_file)

        assert tracker.tracking_file == temp_tracking_file
        assert tracker.data == {}

    def test_init_existing_file(self, temp_tracking_file):
        """Test initialization with existing tracking file."""
        # Create existing tracking file
        existing_data = {
            "2026-03-02": {
                "activities": [
                    {
                        "id": 123,
                        "name": "Test Workout",
                        "analyzed": True,
                    }
                ]
            }
        }

        temp_tracking_file.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_tracking_file, "w") as f:
            json.dump(existing_data, f)

        tracker = ActivityTracker(temp_tracking_file)

        assert tracker.data == existing_data

    def test_is_analyzed_true(self, temp_tracking_file):
        """Test checking if activity is analyzed (true case)."""
        # Create tracker with existing activity
        existing_data = {
            "2026-03-02": {"activities": [{"id": 123, "name": "Test", "analyzed": True}]}
        }

        temp_tracking_file.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_tracking_file, "w") as f:
            json.dump(existing_data, f)

        tracker = ActivityTracker(temp_tracking_file)

        result = tracker.is_analyzed(123, date(2026, 3, 2))

        assert result is True

    def test_is_analyzed_false_no_date(self, temp_tracking_file):
        """Test checking if activity is analyzed (no date)."""
        tracker = ActivityTracker(temp_tracking_file)

        result = tracker.is_analyzed(123, date(2026, 3, 2))

        assert result is False

    def test_is_analyzed_false_different_id(self, temp_tracking_file):
        """Test checking if activity is analyzed (different ID)."""
        existing_data = {
            "2026-03-02": {"activities": [{"id": 456, "name": "Test", "analyzed": True}]}
        }

        temp_tracking_file.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_tracking_file, "w") as f:
            json.dump(existing_data, f)

        tracker = ActivityTracker(temp_tracking_file)

        result = tracker.is_analyzed(123, date(2026, 3, 2))

        assert result is False

    def test_mark_analyzed_new_date(self, temp_tracking_file):
        """Test marking activity as analyzed (new date)."""
        tracker = ActivityTracker(temp_tracking_file)

        activity = {
            "id": 123,
            "start_date_local": "2026-03-02T10:00:00",
            "name": "Test Workout",
            "type": "Ride",
            "icu_training_load": 50,
        }

        analyzed_at = datetime(2026, 3, 2, 18, 0, 0)

        tracker.mark_analyzed(activity, analyzed_at)

        # Verify data was saved
        assert "2026-03-02" in tracker.data
        assert len(tracker.data["2026-03-02"]["activities"]) == 1
        assert tracker.data["2026-03-02"]["activities"][0]["id"] == 123

        # Verify file was created
        assert temp_tracking_file.exists()

    def test_mark_analyzed_existing_date(self, temp_tracking_file):
        """Test marking activity as analyzed (existing date)."""
        existing_data = {
            "2026-03-02": {"activities": [{"id": 456, "name": "Old Activity", "analyzed": True}]}
        }

        temp_tracking_file.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_tracking_file, "w") as f:
            json.dump(existing_data, f)

        tracker = ActivityTracker(temp_tracking_file)

        activity = {
            "id": 123,
            "start_date_local": "2026-03-02T14:00:00",
            "name": "New Workout",
            "type": "Ride",
            "icu_training_load": 60,
        }

        analyzed_at = datetime(2026, 3, 2, 18, 0, 0)

        tracker.mark_analyzed(activity, analyzed_at)

        # Verify both activities present
        assert len(tracker.data["2026-03-02"]["activities"]) == 2

    def test_mark_analyzed_with_paired_event_id(self, temp_tracking_file):
        """Test marking activity with paired_event_id (planned activity)."""
        tracker = ActivityTracker(temp_tracking_file)

        activity = {
            "id": 123,
            "paired_event_id": 999,  # Planned workout ID
            "start_date_local": "2026-03-02T10:00:00",
            "name": "Planned Workout",
            "type": "Ride",
            "icu_training_load": 50,
        }

        analyzed_at = datetime(2026, 3, 2, 18, 0, 0)

        tracker.mark_analyzed(activity, analyzed_at)

        # Verify paired_event_id is used as tracking ID
        assert tracker.data["2026-03-02"]["activities"][0]["id"] == 999
        assert tracker.data["2026-03-02"]["activities"][0]["activity_id"] == 123
        assert tracker.data["2026-03-02"]["activities"][0]["paired_event_id"] == 999


class TestDailySyncInit:
    """Test DailySync initialization."""

    @pytest.fixture
    def temp_paths(self, tmp_path):
        """Create temp paths for testing."""
        tracking_file = tmp_path / "tracking.json"
        reports_dir = tmp_path / "reports"
        return tracking_file, reports_dir

    @patch("cyclisme_training_logs.daily_sync.create_intervals_client")
    def test_init_basic(self, mock_create_client, temp_paths):
        """Test basic initialization."""
        tracking_file, reports_dir = temp_paths

        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        daily_sync = DailySync(
            tracking_file=tracking_file,
            reports_dir=reports_dir,
            enable_ai_analysis=False,
            enable_auto_servo=False,
        )

        assert daily_sync.client is not None
        assert daily_sync.tracker is not None
        assert daily_sync.reports_dir == reports_dir
        assert daily_sync.enable_ai_analysis is False
        assert daily_sync.enable_auto_servo is False

        # Reports dir should be created
        assert reports_dir.exists()

    @patch("cyclisme_training_logs.daily_sync.create_intervals_client")
    @patch("cyclisme_training_logs.daily_sync.get_ai_config")
    @patch("cyclisme_training_logs.daily_sync.AIProviderFactory")
    def test_init_with_ai_analysis(
        self, mock_ai_factory, mock_get_ai_config, mock_create_client, temp_paths
    ):
        """Test initialization with AI analysis enabled."""
        tracking_file, reports_dir = temp_paths

        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Mock AI config
        mock_config = MagicMock()
        mock_config.get_available_providers.return_value = ["anthropic"]
        mock_config.get_provider_config.return_value = {"api_key": "test"}
        mock_get_ai_config.return_value = mock_config

        # Mock AI analyzer
        mock_analyzer = MagicMock()
        mock_ai_factory.create.return_value = mock_analyzer

        daily_sync = DailySync(
            tracking_file=tracking_file,
            reports_dir=reports_dir,
            enable_ai_analysis=True,
            enable_auto_servo=False,
        )

        assert daily_sync.enable_ai_analysis is True
        assert daily_sync.ai_analyzer is not None
        assert daily_sync.prompt_generator is not None
        assert daily_sync.history_manager is not None

    @patch("cyclisme_training_logs.daily_sync.create_intervals_client")
    @patch("cyclisme_training_logs.daily_sync.get_ai_config")
    def test_init_ai_analysis_no_provider(self, mock_get_ai_config, mock_create_client, temp_paths):
        """Test initialization with AI analysis but no provider configured."""
        tracking_file, reports_dir = temp_paths

        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Mock AI config with no providers
        mock_config = MagicMock()
        mock_config.get_available_providers.return_value = []
        mock_get_ai_config.return_value = mock_config

        daily_sync = DailySync(
            tracking_file=tracking_file,
            reports_dir=reports_dir,
            enable_ai_analysis=True,
            enable_auto_servo=False,
        )

        # AI analysis should be disabled due to missing provider
        assert daily_sync.enable_ai_analysis is False
        assert daily_sync.ai_analyzer is None


class TestDailySyncDetectDuplicates:
    """Test DailySync._detect_duplicate_activities method."""

    @pytest.fixture
    def daily_sync_instance(self, tmp_path):
        """Create DailySync instance for testing."""
        with patch("cyclisme_training_logs.daily_sync.create_intervals_client"):
            return DailySync(
                tracking_file=tmp_path / "tracking.json",
                reports_dir=tmp_path / "reports",
                enable_ai_analysis=False,
            )

    def test_detect_duplicate_activities_empty_list(self, daily_sync_instance):
        """Test duplicate detection with empty list."""
        result = daily_sync_instance._detect_duplicate_activities([])

        assert result == []

    def test_detect_duplicate_activities_no_duplicates(self, daily_sync_instance):
        """Test duplicate detection with no duplicates."""
        activities = [
            {
                "id": 123,
                "start_date_local": "2026-03-02T10:00:00",
                "name": "Workout 1",
            },
            {
                "id": 456,
                "start_date_local": "2026-03-02T14:00:00",
                "name": "Workout 2",
            },
        ]

        result = daily_sync_instance._detect_duplicate_activities(activities)

        # Should return both activities (no duplicates)
        assert len(result) == 2

    def test_detect_duplicate_activities_with_duplicates(self, daily_sync_instance):
        """Test duplicate detection with actual duplicates."""
        activities = [
            {
                "id": 123,
                "start_date_local": "2026-03-02T10:00:00",
                "name": "Zwift Workout",
                "icu_training_load": 50,
                "source": "ZWIFT",
            },
            {
                "id": 456,
                "start_date_local": "2026-03-02T10:00:15",  # 15 seconds later
                "name": "Wahoo Workout",
                "icu_training_load": 48,
                "source": "WAHOO",
            },
        ]

        result = daily_sync_instance._detect_duplicate_activities(activities)

        # Should keep only one (within 30 second tolerance)
        assert len(result) == 1

    def test_detect_duplicate_prefers_paired_event(self, daily_sync_instance):
        """Test that duplicate detection prefers activity with paired_event_id."""
        activities = [
            {
                "id": 123,
                "start_date_local": "2026-03-02T10:00:00",
                "name": "Workout",
                "icu_training_load": 50,
                # No paired_event_id
            },
            {
                "id": 456,
                "start_date_local": "2026-03-02T10:00:10",  # 10 seconds later
                "name": "Planned Workout",
                "icu_training_load": 52,
                "paired_event_id": 999,  # Linked to planned workout
            },
        ]

        result = daily_sync_instance._detect_duplicate_activities(activities)

        # Should keep the one with paired_event_id
        assert len(result) == 1
        assert result[0]["id"] == 456
        assert result[0]["paired_event_id"] == 999
