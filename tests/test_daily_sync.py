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
from unittest.mock import MagicMock, Mock, patch

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


class TestDetectDuplicatesEdgeCases:
    """Test additional branches in _detect_duplicate_activities."""

    @pytest.fixture
    def ds(self, tmp_path):
        with patch("cyclisme_training_logs.daily_sync.create_intervals_client"):
            return DailySync(
                tracking_file=tmp_path / "tracking.json",
                reports_dir=tmp_path / "reports",
                enable_ai_analysis=False,
            )

    def test_none_activity_skipped(self, ds):
        """None items in list are skipped."""
        activities = [
            None,
            {
                "id": 123,
                "start_date_local": "2026-03-02T10:00:00",
                "name": "Valid",
                "icu_training_load": 50,
            },
        ]
        result = ds._detect_duplicate_activities(activities)
        assert len(result) == 1
        assert result[0]["id"] == 123

    def test_invalid_start_date_kept(self, ds):
        """Activity with invalid start_date_local kept (no duplicate detection)."""
        activities = [
            {
                "id": 123,
                "start_date_local": "not-a-date",
                "name": "Invalid Date",
            }
        ]
        result = ds._detect_duplicate_activities(activities)
        assert len(result) == 1

    def test_duplicate_prefers_highest_tss_when_no_paired_no_zwift(self, ds):
        """No paired_event_id, no Zwift → highest TSS wins."""
        activities = [
            {
                "id": 100,
                "start_date_local": "2026-03-02T10:00:00",
                "name": "Low TSS",
                "icu_training_load": 30,
                "source": "WAHOO",
            },
            {
                "id": 200,
                "start_date_local": "2026-03-02T10:00:05",
                "name": "High TSS",
                "icu_training_load": 55,
                "source": "GARMIN",
            },
        ]
        result = ds._detect_duplicate_activities(activities)
        assert len(result) == 1
        assert result[0]["id"] == 200

    def test_duplicate_prefers_zwift_over_tss(self, ds):
        """Zwift source wins over higher TSS from another source."""
        activities = [
            {
                "id": 100,
                "start_date_local": "2026-03-02T10:00:00",
                "name": "Zwift",
                "icu_training_load": 50,
                "source": "ZWIFT",
            },
            {
                "id": 200,
                "start_date_local": "2026-03-02T10:00:05",
                "name": "Wahoo",
                "icu_training_load": 60,
                "source": "WAHOO",
            },
        ]
        result = ds._detect_duplicate_activities(activities)
        assert len(result) == 1
        assert result[0]["id"] == 100


class TestCheckActivitiesVerbose:
    """Test check_activities verbose=False path."""

    @pytest.fixture
    def ds(self, tmp_path):
        with patch("cyclisme_training_logs.daily_sync.create_intervals_client") as mock_client:
            mock_client.return_value = MagicMock()
            ds = DailySync(
                tracking_file=tmp_path / "tracking.json",
                reports_dir=tmp_path / "reports",
                enable_ai_analysis=False,
                verbose=False,
            )
            return ds

    def test_verbose_false_suppresses_output(self, ds, capsys):
        """verbose=False path uses devnull suppression."""
        with patch.object(ds, "_check_activities_internal", return_value=([], [])):
            result = ds.check_activities(date(2026, 2, 23))
        captured = capsys.readouterr()
        # No output when verbose=False
        assert captured.out == ""
        assert result == ([], [])


class TestIsLowEffortSocialRide:
    """Test DailySync._is_low_effort_social_ride method."""

    @pytest.fixture
    def daily_sync_instance(self, tmp_path):
        with patch("cyclisme_training_logs.daily_sync.create_intervals_client"):
            return DailySync(
                tracking_file=tmp_path / "tracking.json",
                reports_dir=tmp_path / "reports",
                enable_ai_analysis=False,
            )

    def test_high_tss_returns_false(self, daily_sync_instance):
        """TSS >= 30 → not a social ride regardless of other criteria."""
        activity = {"icu_training_load": 30, "average_watts": 10, "np": 100}
        result = daily_sync_instance._is_low_effort_social_ride(activity, {})
        assert result is False

    def test_low_tss_low_power_ratio_returns_true(self, daily_sync_instance):
        """TSS < 30, avg_power < 50% of NP → social ride."""
        activity = {"icu_training_load": 20, "average_watts": 40, "np": 100}
        result = daily_sync_instance._is_low_effort_social_ride(activity, {})
        assert result is True

    def test_low_tss_acceptable_power_ratio_no_keywords(self, daily_sync_instance):
        """TSS < 30, normal ratio, no keywords → not a social ride."""
        activity = {
            "icu_training_load": 20,
            "average_watts": 80,
            "np": 100,
            "description": "sortie tranquille",
        }
        result = daily_sync_instance._is_low_effort_social_ride(activity, {})
        assert result is False

    def test_social_keyword_accompagnement(self, daily_sync_instance):
        """TSS < 30 + keyword 'accompagnement' → True."""
        activity = {
            "icu_training_load": 25,
            "average_watts": 80,
            "np": 100,
            "description": "Sortie accompagnement débutant",
        }
        result = daily_sync_instance._is_low_effort_social_ride(activity, {})
        assert result is True

    def test_social_keyword_arrets(self, daily_sync_instance):
        """TSS < 30 + keyword 'arrêts' → True."""
        activity = {
            "icu_training_load": 10,
            "average_watts": 80,
            "np": 100,
            "description": "Balade avec arrêts fréquents",
        }
        result = daily_sync_instance._is_low_effort_social_ride(activity, {})
        assert result is True

    def test_no_np_power_check_skipped(self, daily_sync_instance):
        """NP=0 → power ratio check skipped, relies on keywords."""
        activity = {
            "icu_training_load": 25,
            "average_watts": 60,
            "np": 0,
            "description": "sortie tranquille",
        }
        result = daily_sync_instance._is_low_effort_social_ride(activity, {})
        assert result is False


class TestShouldTriggerServo:
    """Test DailySync.should_trigger_servo method."""

    @pytest.fixture
    def ds(self, tmp_path):
        with patch("cyclisme_training_logs.daily_sync.create_intervals_client"):
            return DailySync(
                tracking_file=tmp_path / "tracking.json",
                reports_dir=tmp_path / "reports",
                enable_ai_analysis=False,
            )

    def test_no_metrics_no_trigger(self, ds):
        """All metrics None → no trigger."""
        metrics = {"decoupling": None, "sleep_hours": None, "feel": None, "tsb": None}
        triggered, reasons = ds.should_trigger_servo(metrics)
        assert triggered is False
        assert reasons == []

    def test_decoupling_above_threshold(self, ds):
        """Decoupling > 7.5% → trigger."""
        metrics = {"decoupling": 8.0, "sleep_hours": None, "feel": None, "tsb": None}
        triggered, reasons = ds.should_trigger_servo(metrics)
        assert triggered is True
        assert any("Découplage" in r for r in reasons)

    def test_decoupling_below_threshold(self, ds):
        """Decoupling <= 7.5% → no trigger."""
        metrics = {"decoupling": 7.0, "sleep_hours": None, "feel": None, "tsb": None}
        triggered, reasons = ds.should_trigger_servo(metrics)
        assert triggered is False

    def test_sleep_below_threshold(self, ds):
        """Sleep < 7h → trigger."""
        metrics = {"decoupling": None, "sleep_hours": 5.5, "feel": None, "tsb": None}
        triggered, reasons = ds.should_trigger_servo(metrics)
        assert triggered is True
        assert any("Sommeil" in r for r in reasons)

    def test_sleep_above_threshold(self, ds):
        """Sleep >= 7h → no trigger."""
        metrics = {"decoupling": None, "sleep_hours": 7.5, "feel": None, "tsb": None}
        triggered, reasons = ds.should_trigger_servo(metrics)
        assert triggered is False

    def test_feel_passable_triggers(self, ds):
        """Feel=4 (Passable) → trigger."""
        metrics = {"decoupling": None, "sleep_hours": None, "feel": 4, "tsb": None}
        triggered, reasons = ds.should_trigger_servo(metrics)
        assert triggered is True
        assert any("Passable" in r for r in reasons)

    def test_feel_mauvais_triggers(self, ds):
        """Feel=5 (Mauvais) → trigger."""
        metrics = {"decoupling": None, "sleep_hours": None, "feel": 5, "tsb": None}
        triggered, reasons = ds.should_trigger_servo(metrics)
        assert triggered is True
        assert any("Mauvais" in r for r in reasons)

    def test_feel_moyen_no_trigger(self, ds):
        """Feel=3 (Moyen) → below threshold, no trigger."""
        metrics = {"decoupling": None, "sleep_hours": None, "feel": 3, "tsb": None}
        triggered, reasons = ds.should_trigger_servo(metrics)
        assert triggered is False

    def test_tsb_below_threshold(self, ds):
        """TSB < -10 → trigger."""
        metrics = {"decoupling": None, "sleep_hours": None, "feel": None, "tsb": -15}
        triggered, reasons = ds.should_trigger_servo(metrics)
        assert triggered is True
        assert any("TSB" in r for r in reasons)

    def test_tsb_above_threshold(self, ds):
        """TSB >= -10 → no trigger."""
        metrics = {"decoupling": None, "sleep_hours": None, "feel": None, "tsb": -5}
        triggered, reasons = ds.should_trigger_servo(metrics)
        assert triggered is False

    def test_multiple_reasons(self, ds):
        """Multiple criteria exceeded → all reasons returned."""
        metrics = {"decoupling": 9.0, "sleep_hours": 5.0, "feel": 4, "tsb": -20}
        triggered, reasons = ds.should_trigger_servo(metrics)
        assert triggered is True
        assert len(reasons) >= 3

    def test_social_ride_suppresses_decoupling(self, ds):
        """High decoupling on social ride → no trigger (false positive)."""
        metrics = {"decoupling": 9.0, "sleep_hours": None, "feel": None, "tsb": None}
        activity = {
            "icu_training_load": 20,
            "average_watts": 40,
            "np": 100,
            "description": "",
        }
        triggered, reasons = ds.should_trigger_servo(metrics, activity=activity)
        assert triggered is False


class TestExtractMetricsFromActivity:
    """Test DailySync.extract_metrics_from_activity method."""

    @pytest.fixture
    def ds(self, tmp_path):
        with patch("cyclisme_training_logs.daily_sync.create_intervals_client"):
            return DailySync(
                tracking_file=tmp_path / "tracking.json",
                reports_dir=tmp_path / "reports",
                enable_ai_analysis=False,
            )

    def test_basic_extraction_no_wellness(self, ds):
        """Extract tss_actual and duration from activity without wellness."""
        activity = {
            "icu_training_load": 75,
            "moving_time": 4500,  # 75 minutes
            "decoupling": 3.2,
            "feel": 2,
        }
        metrics = ds.extract_metrics_from_activity(activity, analysis=None, wellness_pre=None)

        assert metrics["tss_actual"] == 75
        assert metrics["duration_actual_min"] == 75
        assert metrics["decoupling"] == 3.2
        assert metrics["feel"] is None  # feel only extracted from wellness block

    def test_sleep_extracted_from_wellness(self, ds):
        """Sleep in seconds converted to hours."""
        activity = {"icu_training_load": 50, "moving_time": 3600}
        wellness = {"sleepSecs": 25200, "ctl": 50.0, "atl": 55.0}  # 7h

        metrics = ds.extract_metrics_from_activity(activity, analysis=None, wellness_pre=wellness)

        assert metrics["sleep_hours"] == pytest.approx(7.0)

    def test_tsb_extracted_from_wellness(self, ds):
        """TSB extracted from wellness via extract_wellness_metrics."""
        activity = {"icu_training_load": 50, "moving_time": 3600}
        wellness = {"ctl": 50.0, "atl": 60.0}  # TSB = -10

        metrics = ds.extract_metrics_from_activity(activity, analysis=None, wellness_pre=wellness)

        assert metrics["tsb"] == pytest.approx(-10.0)

    def test_missing_activity_fields(self, ds):
        """Missing activity fields default gracefully."""
        activity = {}
        metrics = ds.extract_metrics_from_activity(activity, analysis=None, wellness_pre=None)

        assert metrics["tss_actual"] is None
        assert metrics["duration_actual_min"] == 0
        assert metrics["decoupling"] is None


# ---------------------------------------------------------------------------
# Sprint R14 Phase 0 — Nouvelles classes de tests (couverture 29% → 60%)
# ---------------------------------------------------------------------------


def _make_ds(tmp_path, **kwargs):
    """Helper: créer un DailySync sans credentials réels."""
    with patch("cyclisme_training_logs.daily_sync.create_intervals_client"):
        return DailySync(
            tracking_file=tmp_path / "tracking.json",
            reports_dir=tmp_path / "reports",
            **kwargs,
        )


class TestExtractSessionId:
    """Test _extract_session_id — pure function, aucun I/O."""

    @pytest.fixture
    def ds(self, tmp_path):
        return _make_ds(tmp_path)

    def test_full_name_returns_week_and_session(self, ds):
        result = ds._extract_session_id("S079-02-INT-SweetSpotModere-V001")
        assert result == ("S079", "S079-02")

    def test_short_name_returns_week_and_session(self, ds):
        result = ds._extract_session_id("S082-05")
        assert result == ("S082", "S082-05")

    def test_no_match_returns_none(self, ds):
        result = ds._extract_session_id("Regular Ride")
        assert result is None

    def test_empty_string_returns_none(self, ds):
        result = ds._extract_session_id("")
        assert result is None

    def test_partial_match_returns_none(self, ds):
        result = ds._extract_session_id("S07-02")  # only 2 digits week
        assert result is None


class TestFindMatchingActivity:
    """Test _find_matching_activity — pure matching logic."""

    @pytest.fixture
    def ds(self, tmp_path):
        return _make_ds(tmp_path)

    def _workout(self, wid=99, name="S082-03-INT-SweetSpot-V001", dt="2026-02-24T10:00:00+00:00"):
        return {"id": wid, "start_date_local": dt, "name": name}

    def test_match_by_paired_event_id(self, ds):
        workout = self._workout(wid=99)
        activities = [
            {
                "id": 456,
                "paired_event_id": 99,
                "start_date_local": "2026-02-24T10:05:00+00:00",
                "name": "Ride",
            },
        ]
        result = ds._find_matching_activity(workout, activities)
        assert result is not None
        assert result["id"] == 456

    def test_match_by_session_code_and_temporal(self, ds):
        workout = self._workout(wid=999, name="S082-03-INT-SweetSpot")
        activities = [
            {
                "id": 456,
                "start_date_local": "2026-02-24T12:00:00+00:00",
                "name": "S082-03 actual ride",
            },
        ]
        result = ds._find_matching_activity(workout, activities)
        assert result is not None
        assert result["id"] == 456

    def test_no_match_returns_none(self, ds):
        workout = self._workout()
        result = ds._find_matching_activity(workout, [])
        assert result is None

    def test_none_activity_in_list_skipped(self, ds):
        workout = self._workout()
        result = ds._find_matching_activity(workout, [None])
        assert result is None

    def test_activity_outside_tolerance_not_matched(self, ds):
        workout = self._workout(dt="2026-02-20T10:00:00+00:00", name="S082-03-INT")
        activities = [
            {"id": 456, "start_date_local": "2026-02-24T10:00:00+00:00", "name": "S082-03 ride"},
        ]
        result = ds._find_matching_activity(workout, activities, tolerance_hours=24)
        assert result is None

    def test_activity_missing_start_date_skipped(self, ds):
        workout = self._workout(name="S082-03-INT")
        activities = [{"id": 456, "name": "S082-03 ride"}]  # no start_date_local
        result = ds._find_matching_activity(workout, activities)
        assert result is None


class TestCheckActivitiesInternalCounts:
    """Test _check_activities_internal planned/unplanned counting (lines 433-439)."""

    @pytest.fixture
    def ds(self, tmp_path):
        return _make_ds(tmp_path, verbose=True)

    def test_planned_and_unplanned_counted(self, ds):
        activities = [
            {
                "id": 1,
                "start_date_local": "2026-02-24T10:00:00",
                "type": "Ride",
                "name": "Planned",
                "paired_event_id": 100,
            },
            {
                "id": 2,
                "start_date_local": "2026-02-24T14:00:00",
                "type": "Ride",
                "name": "Unplanned",
            },
        ]
        ds.client.get_activities = Mock(return_value=activities)
        ds.tracker.is_analyzed = Mock(return_value=False)

        new_acts, completed_acts = ds._check_activities_internal(date(2026, 2, 24))

        assert len(new_acts) == 2
        assert len(completed_acts) == 2

    def test_already_analyzed_excluded_from_new(self, ds):
        activities = [
            {"id": 1, "start_date_local": "2026-02-24T10:00:00", "type": "Ride", "name": "Old"},
        ]
        ds.client.get_activities = Mock(return_value=activities)
        ds.tracker.is_analyzed = Mock(return_value=True)  # already analyzed

        new_acts, completed_acts = ds._check_activities_internal(date(2026, 2, 24))

        assert len(new_acts) == 0
        assert len(completed_acts) == 1


class TestCheckPlanningChangesErrors:
    """Test check_planning_changes error paths (lines 460-470)."""

    @pytest.fixture
    def ds(self, tmp_path):
        return _make_ds(tmp_path)

    def test_file_not_found_returns_status_none(self, ds):
        with patch("cyclisme_training_logs.daily_sync.planning_tower") as mock_tower:
            mock_tower.read_week.side_effect = FileNotFoundError("no file")
            result = ds.check_planning_changes("S999", date(2026, 2, 17), date(2026, 2, 23))
        assert result == {"status": None, "diff": None}

    def test_json_decode_error_returns_status_none(self, ds):
        with patch("cyclisme_training_logs.daily_sync.planning_tower") as mock_tower:
            mock_tower.read_week.side_effect = json.JSONDecodeError("err", "", 0)
            result = ds.check_planning_changes("S999", date(2026, 2, 17), date(2026, 2, 23))
        assert result == {"status": None, "diff": None}


class TestExtractExistingAnalysisEarlyReturn:
    """Test _extract_existing_analysis early return when history_manager is None."""

    @pytest.fixture
    def ds(self, tmp_path):
        return _make_ds(tmp_path, enable_ai_analysis=False)

    def test_no_history_manager_returns_none(self, ds):
        ds.history_manager = None
        result = ds._extract_existing_analysis("Test Ride", "i123456", "24/02/2026")
        assert result is None

    def test_history_manager_returns_empty_content(self, ds):
        mock_hm = Mock()
        mock_hm.read_history.return_value = None
        ds.history_manager = mock_hm
        result = ds._extract_existing_analysis("Test Ride", "i123456", "24/02/2026")
        assert result is None


class TestUpdateCompletedSessions:
    """Test update_completed_sessions — uses planning_tower + intervals_client."""

    @pytest.fixture
    def ds(self, tmp_path):
        ds = _make_ds(tmp_path)
        ds.intervals_client = Mock()  # attribute name differs from self.client
        return ds

    def test_empty_activities_returns_empty(self, ds):
        result = ds.update_completed_sessions([])
        assert result == {}

    def test_activities_no_valid_dates_returns_empty(self, ds):
        result = ds.update_completed_sessions([{"id": 1, "name": "No date"}])
        assert result == {}

    def test_api_exception_returns_empty(self, ds):
        activities = [{"id": 1, "start_date_local": "2026-02-24T10:00:00+00:00", "name": "Ride"}]
        ds.intervals_client.get_events.side_effect = Exception("API error")
        result = ds.update_completed_sessions(activities)
        assert result == {}

    def test_workouts_no_session_id_returns_empty(self, ds):
        """Workouts without matching S###-## pattern → no sessions updated."""
        activities = [{"id": 1, "start_date_local": "2026-02-24T10:00:00+00:00", "name": "Ride"}]
        ds.intervals_client.get_events.return_value = [
            {
                "category": "WORKOUT",
                "name": "Regular Workout",
                "id": 99,
                "start_date_local": "2026-02-24T10:00:00+00:00",
            },
        ]
        result = ds.update_completed_sessions(activities)
        assert result == {}

    def test_matched_session_marked_completed(self, ds):
        """Workout matched to activity → session status set to 'completed'."""
        activities = [
            {
                "id": 456,
                "start_date_local": "2026-02-24T10:00:00+00:00",
                "name": "S082-03 actual",
                "paired_event_id": 99,
            },
        ]
        ds.intervals_client.get_events.return_value = [
            {
                "category": "WORKOUT",
                "name": "S082-03-INT-SweetSpot-V001",
                "id": 99,
                "start_date_local": "2026-02-24T10:00:00+00:00",
            },
        ]
        mock_session = Mock()
        mock_session.session_id = "S082-03"
        mock_session.status = "uploaded"
        mock_plan = Mock()
        mock_plan.planned_sessions = [mock_session]

        with patch("cyclisme_training_logs.daily_sync.planning_tower") as mock_tower:
            mock_tower.modify_week.return_value.__enter__ = Mock(return_value=mock_plan)
            mock_tower.modify_week.return_value.__exit__ = Mock(return_value=False)
            ds.update_completed_sessions(activities)

        assert mock_session.status == "completed"

    def test_already_completed_session_not_changed(self, ds):
        """Session already 'completed' → status unchanged."""
        activities = [
            {
                "id": 456,
                "start_date_local": "2026-02-24T10:00:00+00:00",
                "name": "S082-03 actual",
                "paired_event_id": 99,
            },
        ]
        ds.intervals_client.get_events.return_value = [
            {
                "category": "WORKOUT",
                "name": "S082-03-INT-SweetSpot-V001",
                "id": 99,
                "start_date_local": "2026-02-24T10:00:00+00:00",
            },
        ]
        mock_session = Mock()
        mock_session.session_id = "S082-03"
        mock_session.status = "completed"
        mock_plan = Mock()
        mock_plan.planned_sessions = [mock_session]

        with patch("cyclisme_training_logs.daily_sync.planning_tower") as mock_tower:
            mock_tower.modify_week.return_value.__enter__ = Mock(return_value=mock_plan)
            mock_tower.modify_week.return_value.__exit__ = Mock(return_value=False)
            ds.update_completed_sessions(activities)

        assert mock_session.status == "completed"  # unchanged

    def test_planning_file_not_found_handled(self, ds):
        """FileNotFoundError from planning_tower is caught."""
        activities = [
            {
                "id": 456,
                "start_date_local": "2026-02-24T10:00:00+00:00",
                "name": "S082-03 actual",
                "paired_event_id": 99,
            },
        ]
        ds.intervals_client.get_events.return_value = [
            {
                "category": "WORKOUT",
                "name": "S082-03-INT-SweetSpot-V001",
                "id": 99,
                "start_date_local": "2026-02-24T10:00:00+00:00",
            },
        ]
        with patch("cyclisme_training_logs.daily_sync.planning_tower") as mock_tower:
            mock_tower.modify_week.side_effect = FileNotFoundError("no planning")
            result = ds.update_completed_sessions(activities)

        # Should complete without raising
        assert isinstance(result, dict)


class TestBackupExistingReport:
    """Test _backup_existing_report — file I/O with tmp_path."""

    @pytest.fixture
    def ds(self, tmp_path):
        return _make_ds(tmp_path)

    def test_no_existing_file_returns_none(self, ds, tmp_path):
        report_file = tmp_path / "reports" / "daily_report_2026-02-24.md"
        result = ds._backup_existing_report(report_file)
        assert result is None

    def test_existing_file_creates_backup(self, ds, tmp_path):
        report_file = tmp_path / "reports" / "daily_report_2026-02-24.md"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text("# Old report")

        backup = ds._backup_existing_report(report_file)

        assert backup is not None
        assert backup.exists()
        assert backup.read_text() == "# Old report"
        assert "backups" in str(backup.parent)


class TestGenerateReport:
    """Test generate_report — writes markdown to file."""

    @pytest.fixture
    def ds(self, tmp_path):
        return _make_ds(tmp_path)

    def test_basic_report_no_activities(self, ds):
        report = ds.generate_report(
            check_date=date(2026, 2, 24),
            new_activities=[],
            planning_changes={"diff": None, "status": None},
        )
        assert report.exists()
        content = report.read_text()
        assert "24/02/2026" in content
        assert "Aucune nouvelle activité" in content
        assert "Aucune modification" in content

    def test_report_with_activities(self, ds):
        activities = [
            {
                "id": 123,
                "name": "Tempo Ride",
                "type": "Ride",
                "icu_training_load": 80,
                "moving_time": 4500,
                "paired_activity_id": None,
            },
        ]
        report = ds.generate_report(
            check_date=date(2026, 2, 24),
            new_activities=activities,
            planning_changes={"diff": None, "status": None},
        )
        content = report.read_text()
        assert "Tempo Ride" in content
        assert "80" in content  # TSS

    def test_report_with_ai_analysis(self, ds):
        activities = [
            {
                "id": 123,
                "name": "Sweet Spot",
                "type": "Ride",
                "icu_training_load": 90,
                "moving_time": 5400,
                "paired_activity_id": None,
            },
        ]
        analyses = {123: "Excellente séance de sweet spot."}
        report = ds.generate_report(
            check_date=date(2026, 2, 24),
            new_activities=activities,
            planning_changes={"diff": None, "status": None},
            analyses=analyses,
        )
        content = report.read_text()
        assert "Excellente séance" in content

    def test_report_with_servo_no_modifications(self, ds):
        servo_result = {"modifications": [], "ai_response": ""}
        report = ds.generate_report(
            check_date=date(2026, 2, 24),
            new_activities=[],
            planning_changes={"diff": None, "status": None},
            servo_result=servo_result,
        )
        content = report.read_text()
        assert "Aucune modification recommandée" in content

    def test_report_with_servo_modifications(self, ds):
        servo_result = {
            "modifications": [
                {
                    "action": "lighten",
                    "target_date": "2026-02-25",
                    "current_workout": "INT",
                    "template_id": "RECUP_COURTE",
                    "reason": "fatigue",
                },
            ],
            "ai_response": "Recommandation: alléger la séance de demain.",
        }
        report = ds.generate_report(
            check_date=date(2026, 2, 24),
            new_activities=[],
            planning_changes={"diff": None, "status": None},
            servo_result=servo_result,
        )
        content = report.read_text()
        assert "2026-02-25" in content
        assert "lighten" in content

    def test_report_with_ctl_analysis_no_alerts(self, ds):
        ctl_analysis = {
            "ctl_current": 55.0,
            "atl_current": 58.0,
            "tsb_current": -3.0,
            "ftp_current": 220,
            "ftp_target": 250,
            "ctl_minimum_for_ftp": 50.0,
            "ctl_optimal_for_ftp": 62.0,
            "alerts": [],
            "recommendations": [],
            "phase_recommendation": None,
            "pid_peaks_recommendation": None,
        }
        report = ds.generate_report(
            check_date=date(2026, 2, 24),
            new_activities=[],
            planning_changes={"diff": None, "status": None},
            ctl_analysis=ctl_analysis,
        )
        content = report.read_text()
        assert "CTL dans les normes" in content
        assert "55.0" in content

    def test_report_with_ctl_analysis_with_alerts(self, ds):
        ctl_analysis = {
            "ctl_current": 30.0,
            "atl_current": 35.0,
            "tsb_current": -5.0,
            "ftp_current": 220,
            "ftp_target": 250,
            "ctl_minimum_for_ftp": 50.0,
            "ctl_optimal_for_ftp": 62.0,
            "alerts": ["CTL critique: 30.0 < 50 minimum"],
            "recommendations": ["Augmenter le volume"],
            "phase_recommendation": None,
            "pid_peaks_recommendation": None,
        }
        report = ds.generate_report(
            check_date=date(2026, 2, 24),
            new_activities=[],
            planning_changes={"diff": None, "status": None},
            ctl_analysis=ctl_analysis,
        )
        content = report.read_text()
        assert "CTL critique" in content
        assert "Augmenter le volume" in content

    def test_report_overwrites_existing_with_backup(self, ds, tmp_path):
        """Second report for same date creates backup of first."""
        check_date = date(2026, 2, 24)
        planning_changes = {"diff": None, "status": None}

        # First report
        ds.generate_report(
            check_date=check_date, new_activities=[], planning_changes=planning_changes
        )
        # Second report — should backup first
        ds.generate_report(
            check_date=check_date, new_activities=[], planning_changes=planning_changes
        )

        backups_dir = tmp_path / "reports" / "backups"
        assert backups_dir.exists()
        backups = list(backups_dir.glob("*.md"))
        assert len(backups) == 1

    def test_report_with_planning_diff_removed_and_added(self, ds):
        """Planning diff with removed + added workouts written to report."""
        mock_diff = Mock()
        mock_diff.has_changes.return_value = True
        mock_diff.removed_remote = [{"date": "2026-02-25", "name": "Old Workout"}]
        mock_diff.added_remote = [{"date": "2026-02-26", "name": "New Workout", "id": 42}]
        mock_diff.modified_remote = []

        report = ds.generate_report(
            check_date=date(2026, 2, 24),
            new_activities=[],
            planning_changes={"diff": mock_diff, "status": Mock()},
        )
        content = report.read_text()
        assert "Old Workout" in content
        assert "New Workout" in content

    def test_report_with_planning_diff_modified(self, ds):
        """Planning diff with modified workout written to report."""
        mock_diff = Mock()
        mock_diff.has_changes.return_value = True
        mock_diff.removed_remote = []
        mock_diff.added_remote = []
        mock_diff.modified_remote = [
            {
                "date": "2026-02-25",
                "local": {"name": "Local Workout"},
                "remote": {"name": "Remote Workout", "id": 99},
                "diff": "+ some change",
            },
        ]

        report = ds.generate_report(
            check_date=date(2026, 2, 24),
            new_activities=[],
            planning_changes={"diff": mock_diff, "status": Mock()},
        )
        content = report.read_text()
        assert "Local Workout" in content
        assert "Remote Workout" in content

    def test_report_with_compensation_result(self, ds):
        """Compensation section written when compensation_result provided."""
        compensation_result = {"context": Mock(), "recommendations": Mock()}
        with patch(
            "cyclisme_training_logs.daily_sync.format_compensation_section",
            return_value="## Compensation\n\nAugmenter volume.\n",
        ):
            report = ds.generate_report(
                check_date=date(2026, 2, 24),
                new_activities=[],
                planning_changes={"diff": None, "status": None},
                compensation_result=compensation_result,
            )
        content = report.read_text()
        assert "Augmenter volume" in content

    def test_report_with_phase_and_pid_recommendation(self, ds):
        """Phase recommendation and PID/peaks recommendation sections written."""
        ctl_analysis = {
            "ctl_current": 55.0,
            "atl_current": 58.0,
            "tsb_current": -3.0,
            "ftp_current": 220,
            "ftp_target": 250,
            "ctl_minimum_for_ftp": 50.0,
            "ctl_optimal_for_ftp": 62.0,
            "alerts": [],
            "recommendations": [],
            "phase_recommendation": Mock(),
            "pid_peaks_recommendation": Mock(),
        }
        with (
            patch(
                "cyclisme_training_logs.daily_sync.format_phase_recommendation",
                return_value="Phase: Build\n",
            ),
            patch(
                "cyclisme_training_logs.daily_sync.format_integrated_recommendation",
                return_value="PID: +3 CTL/week\n",
            ),
        ):
            report = ds.generate_report(
                check_date=date(2026, 2, 24),
                new_activities=[],
                planning_changes={"diff": None, "status": None},
                ctl_analysis=ctl_analysis,
            )
        content = report.read_text()
        assert "Phase: Build" in content
        assert "PID: +3 CTL/week" in content


class TestUpdateCompletedSessionsEdgeCases:
    """Additional edge cases for update_completed_sessions."""

    @pytest.fixture
    def ds(self, tmp_path):
        ds = _make_ds(tmp_path)
        ds.intervals_client = Mock()
        return ds

    def _activities(self):
        return [
            {
                "id": 456,
                "start_date_local": "2026-02-24T10:00:00+00:00",
                "name": "S082-03 actual",
                "paired_event_id": 99,
            }
        ]

    def _workouts(self):
        return [
            {
                "category": "WORKOUT",
                "name": "S082-03-INT-SweetSpot-V001",
                "id": 99,
                "start_date_local": "2026-02-24T10:00:00+00:00",
            }
        ]

    def test_session_not_found_in_planning(self, ds):
        """Session_id from workout not found in plan — still returns activity map."""
        ds.intervals_client.get_events.return_value = self._workouts()
        mock_plan = Mock()
        mock_plan.planned_sessions = []  # No sessions → not found in planning

        with patch("cyclisme_training_logs.daily_sync.planning_tower") as mock_tower:
            mock_tower.modify_week.return_value.__enter__ = Mock(return_value=mock_plan)
            mock_tower.modify_week.return_value.__exit__ = Mock(return_value=False)
            result = ds.update_completed_sessions(self._activities())

        # activity_to_session_map is populated from matching, not from planning update
        assert isinstance(result, dict)

    def test_generic_exception_in_planning_tower(self, ds):
        """Generic exception from planning_tower.modify_week is caught."""
        ds.intervals_client.get_events.return_value = self._workouts()

        with patch("cyclisme_training_logs.daily_sync.planning_tower") as mock_tower:
            mock_tower.modify_week.side_effect = RuntimeError("unexpected error")
            result = ds.update_completed_sessions(self._activities())

        assert isinstance(result, dict)


class TestCheckPlanningChangesSuccess:
    """Test check_planning_changes happy path (lines 473-511)."""

    @pytest.fixture
    def ds(self, tmp_path):
        return _make_ds(tmp_path)

    def test_no_changes_returns_status(self, ds):
        """Success path with no planning diff returns status."""
        mock_plan = Mock()
        mock_plan.planned_sessions = []

        mock_status = Mock()
        mock_status.diff = Mock()
        mock_status.diff.has_changes.return_value = False
        mock_status.summary.return_value = "OK"
        mock_sync_instance = Mock()
        mock_sync_instance.get_sync_status.return_value = mock_status

        with (
            patch("cyclisme_training_logs.daily_sync.planning_tower") as mock_tower,
            patch("cyclisme_training_logs.daily_sync.AthleteProfile") as mock_ap,
            patch("cyclisme_training_logs.daily_sync.TrainingCalendar", return_value=Mock()),
            patch(
                "cyclisme_training_logs.daily_sync.IntervalsSync", return_value=mock_sync_instance
            ),
        ):
            mock_tower.read_week.return_value = mock_plan
            mock_ap.from_env.return_value = Mock()
            result = ds.check_planning_changes("S082", date(2026, 2, 17), date(2026, 2, 23))

        assert result["status"] is mock_status
        assert result["diff"] is mock_status.diff

    def test_with_changes_returns_status(self, ds):
        """Success path with planning diff returns status."""
        mock_plan = Mock()
        mock_session = Mock()
        mock_session.session_date = date(2026, 2, 17)  # Monday, not Sunday
        mock_session.session_type = "INT"
        mock_session.tss_planned = 80
        mock_session.duration_min = 60
        mock_session.description = "Sweet spot"
        mock_session.description_hash = "abc123"
        mock_plan.planned_sessions = [mock_session]

        mock_status = Mock()
        mock_status.diff = Mock()
        mock_status.diff.has_changes.return_value = True
        mock_status.summary.return_value = "1 change"
        mock_sync_instance = Mock()
        mock_sync_instance.get_sync_status.return_value = mock_status
        mock_calendar = Mock()
        mock_cal_session = Mock()
        mock_calendar.add_session.return_value = mock_cal_session

        with (
            patch("cyclisme_training_logs.daily_sync.planning_tower") as mock_tower,
            patch("cyclisme_training_logs.daily_sync.AthleteProfile") as mock_ap,
            patch("cyclisme_training_logs.daily_sync.TrainingCalendar", return_value=mock_calendar),
            patch(
                "cyclisme_training_logs.daily_sync.IntervalsSync", return_value=mock_sync_instance
            ),
        ):
            mock_tower.read_week.return_value = mock_plan
            mock_ap.from_env.return_value = Mock()
            result = ds.check_planning_changes("S082", date(2026, 2, 17), date(2026, 2, 23))

        assert result["status"] is mock_status


class TestCheckActivitiesPublicMethod:
    """Test check_activities public method — verbose=True branch (line 395)."""

    @pytest.fixture
    def ds(self, tmp_path):
        return _make_ds(tmp_path, verbose=True)

    def test_verbose_true_calls_internal(self, ds):
        """check_activities with verbose=True executes _check_activities_internal."""
        ds.client.get_activities = Mock(return_value=[])
        new_acts, completed_acts = ds.check_activities(date(2026, 2, 24))
        assert new_acts == []
        assert completed_acts == []


class TestCheckPlanningChangesSundaySession:
    """Test check_planning_changes skips Sunday sessions (line 489)."""

    @pytest.fixture
    def ds(self, tmp_path):
        return _make_ds(tmp_path)

    def test_sunday_session_skipped(self, ds):
        """Session on Sunday (weekday=6) is not added to calendar."""
        mock_plan = Mock()
        mock_session = Mock()
        mock_session.session_date = date(2026, 2, 22)  # Sunday
        mock_plan.planned_sessions = [mock_session]

        mock_status = Mock()
        mock_status.diff = Mock()
        mock_status.diff.has_changes.return_value = False
        mock_status.summary.return_value = "OK"
        mock_sync_instance = Mock()
        mock_sync_instance.get_sync_status.return_value = mock_status
        mock_calendar = Mock()

        with (
            patch("cyclisme_training_logs.daily_sync.planning_tower") as mock_tower,
            patch("cyclisme_training_logs.daily_sync.AthleteProfile") as mock_ap,
            patch("cyclisme_training_logs.daily_sync.TrainingCalendar", return_value=mock_calendar),
            patch(
                "cyclisme_training_logs.daily_sync.IntervalsSync", return_value=mock_sync_instance
            ),
        ):
            mock_tower.read_week.return_value = mock_plan
            mock_ap.from_env.return_value = Mock()
            result = ds.check_planning_changes("S082", date(2026, 2, 16), date(2026, 2, 22))

        # Sunday session skipped → add_session not called
        mock_calendar.add_session.assert_not_called()
        assert result["status"] is mock_status


class TestExtractExistingAnalysisWithContent:
    """Test _extract_existing_analysis when history has content."""

    @pytest.fixture
    def ds(self, tmp_path):
        return _make_ds(tmp_path)

    def test_activity_found_in_history(self, ds):
        """Returns analysis section when activity found in history."""
        history = (
            "### Test Ride\nID : i123456\nDate : 24/02/2026\n\nExcellent séance.\n\n"
            "### Next Ride\nID : i789\nDate : 25/02/2026\n\nAnother entry.\n"
        )
        mock_hm = Mock()
        mock_hm.read_history.return_value = history
        ds.history_manager = mock_hm

        result = ds._extract_existing_analysis("Test Ride", "i123456", "24/02/2026")

        assert result is not None
        assert "Excellent séance" in result

    def test_activity_not_found_in_history(self, ds):
        """Returns None when activity not found in history."""
        history = "### Other Ride\nID : i999\nDate : 25/02/2026\n\nContent.\n"
        mock_hm = Mock()
        mock_hm.read_history.return_value = history
        ds.history_manager = mock_hm

        result = ds._extract_existing_analysis("Test Ride", "i123456", "24/02/2026")

        assert result is None

    def test_exception_in_history_read_returns_none(self, ds):
        """Exception during history read returns None."""
        mock_hm = Mock()
        mock_hm.read_history.side_effect = RuntimeError("read error")
        ds.history_manager = mock_hm

        result = ds._extract_existing_analysis("Test Ride", "i123456", "24/02/2026")

        assert result is None

    def test_activity_last_entry_no_next_section(self, ds):
        """Activity is the last entry — no next ### section."""
        history = "### Test Ride\nID : i123456\nDate : 24/02/2026\n\nFinal analysis.\n"
        mock_hm = Mock()
        mock_hm.read_history.return_value = history
        ds.history_manager = mock_hm

        result = ds._extract_existing_analysis("Test Ride", "i123456", "24/02/2026")

        assert result is not None
        assert "Final analysis" in result


class TestDetectDuplicatesNoneStartTime:
    """Test _detect_duplicate_activities with None start_dt case (lines 303-304)."""

    @pytest.fixture
    def ds(self, tmp_path):
        return _make_ds(tmp_path)

    def test_activity_with_none_start_time_grouped_alone(self, ds):
        """Activity with unparseable date is placed in its own group."""
        activities = [
            {"id": 1, "start_date_local": "invalid-date", "name": "Bad date"},
            {"id": 2, "start_date_local": "2026-02-24T10:00:00", "name": "Valid"},
        ]
        result = ds._detect_duplicate_activities(activities)
        # Both activities should be returned (no deduplication)
        assert len(result) == 2
