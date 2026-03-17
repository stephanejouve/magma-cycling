"""Tests for WeeklyAggregator API-dependent methods.

Extends test_weekly_aggregator.py with mock IntervalsClient to cover:
- collect_raw_data (full pipeline)
- _fetch_weekly_activities (enrichment)
- _fetch_daily_metrics
- _fetch_wellness_data
- _fetch_planned_workouts
- _extract_gear_metrics
- format_output
- _compute_compliance
- Edge cases: no API, empty data, None values
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.analyzers.weekly_aggregator import WeeklyAggregator


@pytest.fixture
def mock_api():
    """Create a mock IntervalsClient."""
    api = MagicMock()
    api.athlete_id = "i12345"
    return api


@pytest.fixture
def aggregator(mock_api):
    """Create WeeklyAggregator with mocked API."""
    with patch(
        "magma_cycling.analyzers.weekly_aggregator.create_intervals_client", return_value=mock_api
    ):
        agg = WeeklyAggregator(week="S090", start_date=date(2026, 3, 9))
    return agg


@pytest.fixture
def aggregator_no_api():
    """Create WeeklyAggregator without API."""
    with patch(
        "magma_cycling.analyzers.weekly_aggregator.create_intervals_client",
        side_effect=ValueError("No API"),
    ):
        agg = WeeklyAggregator(week="S090", start_date=date(2026, 3, 9))
    return agg


class TestFetchWeeklyActivities:
    """Test _fetch_weekly_activities with mock API."""

    def test_enriches_each_activity(self, aggregator, mock_api):
        """Test that each activity is enriched via get_activity."""
        mock_api.get_activities.return_value = [
            {"id": "i100", "name": "Session A", "start_date_local": "2026-03-09"},
            {"id": "i101", "name": "Session B", "start_date_local": "2026-03-10"},
        ]
        mock_api.get_activity.side_effect = [
            {
                "id": "i100",
                "name": "Session A",
                "icu_training_load": 55,
                "start_date_local": "2026-03-09",
            },
            {
                "id": "i101",
                "name": "Session B",
                "icu_training_load": 70,
                "start_date_local": "2026-03-10",
            },
        ]

        activities = aggregator._fetch_weekly_activities()

        assert len(activities) == 2
        assert activities[0]["icu_training_load"] == 55
        assert activities[1]["icu_training_load"] == 70
        assert mock_api.get_activity.call_count == 2

    def test_fallback_on_get_activity_error(self, aggregator, mock_api):
        """Test fallback to basic data when get_activity fails."""
        mock_api.get_activities.return_value = [
            {"id": "i100", "name": "Session A", "start_date_local": "2026-03-09"},
        ]
        mock_api.get_activity.side_effect = Exception("API error")

        activities = aggregator._fetch_weekly_activities()

        assert len(activities) == 1
        assert activities[0]["name"] == "Session A"

    def test_activity_without_id(self, aggregator, mock_api):
        """Test activity without ID is kept as-is."""
        mock_api.get_activities.return_value = [
            {"name": "No ID session", "start_date_local": "2026-03-09"},
        ]

        activities = aggregator._fetch_weekly_activities()

        assert len(activities) == 1
        assert activities[0]["name"] == "No ID session"
        mock_api.get_activity.assert_not_called()

    def test_no_api_returns_empty(self, aggregator_no_api):
        """Test returns empty list when API not available."""
        assert aggregator_no_api._fetch_weekly_activities() == []

    def test_sorted_by_date(self, aggregator, mock_api):
        """Test activities are sorted by start_date_local."""
        mock_api.get_activities.return_value = [
            {"id": "i101", "name": "B", "start_date_local": "2026-03-11"},
            {"id": "i100", "name": "A", "start_date_local": "2026-03-09"},
        ]
        mock_api.get_activity.side_effect = [
            {"id": "i101", "name": "B", "start_date_local": "2026-03-11"},
            {"id": "i100", "name": "A", "start_date_local": "2026-03-09"},
        ]

        activities = aggregator._fetch_weekly_activities()

        assert activities[0]["name"] == "A"
        assert activities[1]["name"] == "B"


class TestFetchDailyMetrics:
    """Test _fetch_daily_metrics with mock API."""

    def test_fetches_7_days(self, aggregator, mock_api):
        """Test metrics are fetched for each day of the week."""
        mock_api.get_wellness.return_value = [{"ctl": 60.0, "atl": 55.0, "tsb": 5.0}]

        metrics = aggregator._fetch_daily_metrics()

        assert len(metrics) == 7
        assert mock_api.get_wellness.call_count == 7
        assert metrics[0]["ctl"] == 60.0

    def test_handles_empty_wellness(self, aggregator, mock_api):
        """Test handles days with no wellness data."""
        mock_api.get_wellness.return_value = []

        metrics = aggregator._fetch_daily_metrics()

        assert metrics == []

    def test_handles_api_error(self, aggregator, mock_api):
        """Test handles API errors gracefully."""
        mock_api.get_wellness.side_effect = Exception("API error")

        metrics = aggregator._fetch_daily_metrics()

        assert metrics == []

    def test_no_api_returns_empty(self, aggregator_no_api):
        """Test returns empty when no API."""
        assert aggregator_no_api._fetch_daily_metrics() == []

    def test_dict_wellness_response(self, aggregator, mock_api):
        """Test handles dict wellness response (not list)."""
        mock_api.get_wellness.return_value = {"ctl": 50.0, "atl": 45.0, "tsb": 5.0}

        metrics = aggregator._fetch_daily_metrics()

        assert len(metrics) == 7


class TestFetchWellnessData:
    """Test _fetch_wellness_data."""

    def test_fetches_wellness_for_week(self, aggregator, mock_api):
        """Test wellness data is collected for each day."""
        mock_api.get_wellness.return_value = [
            {"sleepQuality": 3, "sleepSecs": 27000, "weight": 84.0, "hrvSDNN": 45, "restingHR": 55}
        ]

        wellness = aggregator._fetch_wellness_data()

        assert len(wellness) == 7
        first_day = wellness["2026-03-09"]
        assert first_day["sleep_quality"] == 3
        assert first_day["sleep_hours"] == 7.5
        assert first_day["weight"] == 84.0

    def test_no_api_returns_empty(self, aggregator_no_api):
        """Test returns empty dict when no API."""
        assert aggregator_no_api._fetch_wellness_data() == {}


class TestFetchPlannedWorkouts:
    """Test _fetch_planned_workouts."""

    def test_filters_workout_category(self, aggregator, mock_api):
        """Test only WORKOUT events are returned."""
        mock_api.get_events.return_value = [
            {"category": "WORKOUT", "name": "Sweet Spot"},
            {"category": "NOTE", "name": "Rest note"},
            {"category": "WORKOUT", "name": "Intervals"},
        ]

        planned = aggregator._fetch_planned_workouts()

        assert len(planned) == 2
        assert all(p["category"] == "WORKOUT" for p in planned)

    def test_no_api_returns_empty(self, aggregator_no_api):
        """Test returns empty when no API."""
        assert aggregator_no_api._fetch_planned_workouts() == []

    def test_api_error_returns_empty(self, aggregator, mock_api):
        """Test returns empty on API error."""
        mock_api.get_events.side_effect = Exception("API error")

        assert aggregator._fetch_planned_workouts() == []


class TestExtractGearMetrics:
    """Test _extract_gear_metrics (Di2 data)."""

    def test_extracts_gear_shifts(self, aggregator, mock_api):
        """Test gear shift counting from streams."""
        mock_api.get_activity_streams.return_value = [
            {"type": "FrontGear", "data": [34, 34, 50, 50, 34]},
            {"type": "RearGear", "data": [28, 25, 25, 23, 23]},
            {"type": "GearRatio", "data": [1.21, 1.36, 2.0, 2.17, 1.48]},
        ]

        result = aggregator._extract_gear_metrics("i100")

        assert result is not None
        assert result["front_shifts"] == 2  # 34→50, 50→34
        assert result["rear_shifts"] == 2  # 28→25, 25→23
        assert result["shifts"] == 4
        assert result["avg_gear_ratio"] is not None

    def test_no_gear_data_returns_none(self, aggregator, mock_api):
        """Test returns None when no gear streams."""
        mock_api.get_activity_streams.return_value = [
            {"type": "Watts", "data": [150, 160, 170]},
        ]

        assert aggregator._extract_gear_metrics("i100") is None

    def test_api_error_returns_none(self, aggregator, mock_api):
        """Test returns None on API error."""
        mock_api.get_activity_streams.side_effect = Exception("No streams")

        assert aggregator._extract_gear_metrics("i100") is None

    def test_no_api_returns_none(self, aggregator_no_api):
        """Test returns None when no API."""
        assert aggregator_no_api._extract_gear_metrics("i100") is None


class TestCollectRawData:
    """Test collect_raw_data full pipeline."""

    def test_collects_all_sections(self, aggregator, mock_api, tmp_path):
        """Test all data sections are collected."""
        mock_api.get_activities.return_value = [
            {"id": "i100", "name": "A", "start_date_local": "2026-03-09"}
        ]
        mock_api.get_activity.return_value = {
            "id": "i100",
            "name": "A",
            "start_date_local": "2026-03-09",
            "icu_training_load": 55,
        }
        mock_api.get_wellness.return_value = [{"ctl": 60.0, "atl": 55.0, "tsb": 5.0}]
        mock_api.get_events.return_value = [{"category": "WORKOUT", "name": "Test"}]

        aggregator.data_dir = tmp_path

        raw = aggregator.collect_raw_data()

        assert "activities" in raw
        assert "metrics_daily" in raw
        assert "feedback" in raw
        assert "wellness" in raw
        assert "planned" in raw

    def test_handles_all_api_errors(self, aggregator, mock_api, tmp_path):
        """Test graceful degradation when all API calls fail."""
        mock_api.get_activities.side_effect = Exception("Fail")
        mock_api.get_wellness.side_effect = Exception("Fail")
        mock_api.get_events.side_effect = Exception("Fail")

        aggregator.data_dir = tmp_path

        raw = aggregator.collect_raw_data()

        assert raw["activities"] == []
        assert raw["metrics_daily"] == []
        assert raw["wellness"] == {}


class TestFormatOutput:
    """Test format_output."""

    def test_markdown_summary(self, aggregator):
        """Test markdown output generation."""
        processed = {
            "summary": {
                "total_sessions": 5,
                "total_tss": 300,
                "total_duration": 7200,
                "avg_tss": 60.0,
                "final_metrics": {"ctl": 65.0, "atl": 60.0, "tsb": 5.0},
            }
        }

        output = aggregator.format_output(processed)

        assert "S090" in output
        assert "300" in output
        assert "5" in output  # sessions
        assert "CTL" in output
        assert "65.0" in output

    def test_no_final_metrics(self, aggregator):
        """Test output without final metrics."""
        processed = {
            "summary": {"total_sessions": 0, "total_tss": 0, "total_duration": 0, "avg_tss": 0}
        }

        output = aggregator.format_output(processed)

        assert "S090" in output
        assert "CTL" not in output


class TestComputeCompliance:
    """Test _compute_compliance."""

    def test_full_compliance(self, aggregator):
        """Test 100% compliance."""
        activities = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        planned = [{"name": "1"}, {"name": "2"}, {"name": "3"}]

        result = aggregator._compute_compliance(activities, planned)

        assert result["rate"] == 100.0
        assert result["planned_count"] == 3
        assert result["executed_count"] == 3

    def test_partial_compliance(self, aggregator):
        """Test partial compliance."""
        activities = [{"name": "A"}, {"name": "B"}]
        planned = [{"name": "1"}, {"name": "2"}, {"name": "3"}, {"name": "4"}]

        result = aggregator._compute_compliance(activities, planned)

        assert result["rate"] == 50.0
        assert len(result["missed"]) == 2

    def test_empty_planned(self, aggregator):
        """Test with no planned workouts."""
        result = aggregator._compute_compliance([{"name": "A"}], [])

        assert result["rate"] == 0
        assert result["planned_count"] == 0


class TestPedalBalance:
    """Test pedal balance detection in learnings and summary."""

    def test_imbalance_detected_left(self, aggregator):
        """Test left-heavy pedal imbalance detection."""
        workouts = [
            {"tss": 50, "if": 0.7, "pedal_balance": 53.5},
            {"tss": 55, "if": 0.75, "pedal_balance": 54.0},
        ]

        learnings = aggregator._extract_training_learnings(workouts, {})

        assert any("Déséquilibre pédalage" in lrn for lrn in learnings)

    def test_no_imbalance(self, aggregator):
        """Test no imbalance when balanced."""
        workouts = [
            {"tss": 50, "if": 0.7, "pedal_balance": 50.2},
            {"tss": 55, "if": 0.75, "pedal_balance": 49.8},
        ]

        learnings = aggregator._extract_training_learnings(workouts, {})

        assert not any("Déséquilibre" in lrn for lrn in learnings)

    def test_summary_pedal_balance(self, aggregator):
        """Test pedal balance in weekly summary."""
        activities = [
            {
                "icu_training_load": 50,
                "moving_time": 3600,
                "icu_intensity": 70,
                "distance": 40,
                "avg_lr_balance": 53.5,
            },
        ]

        summary = aggregator._compute_weekly_summary(activities)

        assert summary["avg_pedal_balance"] == 53.5
        assert summary["pedal_balance_imbalance"] is True


class TestGearLearnings:
    """Test gear-related learnings extraction."""

    def test_frequent_shifts(self, aggregator):
        """Test frequent gear shift detection."""
        workouts = [
            {
                "tss": 50,
                "if": 0.7,
                "duration": 3600,
                "gear_metrics": {"shifts": 200, "avg_gear_ratio": 2.0},
            },
        ]

        learnings = aggregator._extract_training_learnings(workouts, {})

        assert any("fréquents" in lrn for lrn in learnings)

    def test_low_gear_ratio(self, aggregator):
        """Test low gear ratio detection."""
        workouts = [
            {
                "tss": 50,
                "if": 0.7,
                "duration": 7200,
                "gear_metrics": {"shifts": 100, "avg_gear_ratio": 1.2},
            },
        ]

        learnings = aggregator._extract_training_learnings(workouts, {})

        assert any("Développement faible" in lrn for lrn in learnings)
