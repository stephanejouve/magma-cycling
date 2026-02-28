"""Tests for DataCollector module.

Sprint R10 MVP Day 4 - Tests for data collection from WeeklyAggregator.

Author: Claude Code
Created: 2026-01-18
"""

from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from magma_cycling.reports.data_collector import (
    DataCollectionError,
    DataCollector,
)


class TestDataCollectorInit:
    """Tests for DataCollector initialization."""

    def test_init_with_default_data_dir(self):
        """Test initialization with default data directory."""
        # When: Creating collector without data_dir
        collector = DataCollector()

        # Then: Should use default ~/data directory
        assert collector.data_dir == Path.home() / "data"

    def test_init_with_custom_data_dir(self):
        """Test initialization with custom data directory."""
        # Given: Custom data directory
        custom_dir = Path("/tmp/custom_data")

        # When: Creating collector with custom directory
        collector = DataCollector(data_dir=custom_dir)

        # Then: Should use custom directory
        assert collector.data_dir == custom_dir


class TestCollectWeekData:
    """Tests for collect_week_data method."""

    @patch("magma_cycling.reports.data_collector.WeeklyAggregator")
    def test_collect_week_data_success(self, mock_aggregator_class):
        """Test successful week data collection."""
        # Given: Mocked WeeklyAggregator with successful result
        mock_aggregator = Mock()
        mock_aggregator_class.return_value = mock_aggregator

        # Mock successful aggregation result
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = {
            "processed": {
                "workouts": [
                    {
                        "intervals_activity": {
                            "id": "12345",
                            "name": "Test Workout",
                            "start_date_local": "2026-01-13T09:00:00",
                            "type": "Ride",
                            "moving_time": 3600,
                            "icu_training_load": 85,
                            "icu_intensity": 0.72,
                            "icu_np": 180,
                            "average_hr": 135,
                            "trainer": True,
                        }
                    }
                ],
                "summary": {
                    "planned_tss": 450,
                    "total_tss": 423,
                },
                "metrics_evolution": {
                    "daily_metrics": [
                        {
                            "ctl": 100,
                            "atl": 50,
                            "tsb": 50,
                            "hrv": 58,
                            "sleep_quality": 7.2,
                            "fatigue": 3.5,
                            "readiness": 8.1,
                        },
                        {
                            "ctl": 105,
                            "atl": 55,
                            "tsb": 50,
                            "hrv": 58,
                            "sleep_quality": 7.5,
                            "fatigue": 3.2,
                            "readiness": 8.3,
                        },
                    ]
                },
                "learnings": [
                    {
                        "type": "protocol_validation",
                        "title": "Z2 Protocol Validated",
                        "description": "90min Z2 indoor @ 72% IF maintained",
                        "session_id": "12345",
                        "confidence": "high",
                    }
                ],
            }
        }
        mock_aggregator.aggregate.return_value = mock_result

        collector = DataCollector()

        # When: Collecting week data
        week_data = collector.collect_week_data("S076", date(2026, 1, 13))

        # Then: Should return complete week data structure
        assert week_data["week_number"] == "S076"
        assert week_data["start_date"] == "2026-01-13"
        assert week_data["end_date"] == "2026-01-19"
        assert week_data["tss_planned"] == 450
        assert week_data["tss_realized"] == 423
        assert len(week_data["activities"]) == 1
        assert week_data["activities"][0]["name"] == "Test Workout"
        assert week_data["wellness_data"]["hrv_avg"] == 58
        assert len(week_data["learnings"]) == 1
        assert week_data["metrics_evolution"]["start"]["ctl"] == 100
        assert week_data["metrics_evolution"]["end"]["ctl"] == 105

        # Verify WeeklyAggregator was called correctly
        mock_aggregator_class.assert_called_once_with(week="S076", start_date=date(2026, 1, 13))
        mock_aggregator.aggregate.assert_called_once()

    @patch("magma_cycling.reports.data_collector.WeeklyAggregator")
    def test_collect_week_data_aggregator_failure(self, mock_aggregator_class):
        """Test data collection fails when aggregator fails."""
        # Given: Mocked WeeklyAggregator with failed result
        mock_aggregator = Mock()
        mock_aggregator_class.return_value = mock_aggregator

        mock_result = Mock()
        mock_result.success = False
        mock_result.error = "Aggregation failed"
        mock_aggregator.aggregate.return_value = mock_result

        collector = DataCollector()

        # When/Then: Should raise DataCollectionError
        with pytest.raises(DataCollectionError, match="Failed to aggregate week data"):
            collector.collect_week_data("S076", date(2026, 1, 13))

    @patch("magma_cycling.reports.data_collector.WeeklyAggregator")
    def test_collect_week_data_exception_handling(self, mock_aggregator_class):
        """Test data collection handles exceptions properly."""
        # Given: WeeklyAggregator that raises exception
        mock_aggregator_class.side_effect = Exception("Unexpected error")

        collector = DataCollector()

        # When/Then: Should raise DataCollectionError with context
        with pytest.raises(DataCollectionError, match="Failed to collect week data"):
            collector.collect_week_data("S076", date(2026, 1, 13))


class TestFormatActivities:
    """Tests for _format_activities helper method."""

    def test_format_activities_with_data(self):
        """Test formatting activities from workouts."""
        # Given: Workouts with intervals_activity data
        workouts = [
            {
                "intervals_activity": {
                    "id": "12345",
                    "name": "Z2 Base Indoor",
                    "start_date_local": "2026-01-13T09:00:00",
                    "type": "Ride",
                    "moving_time": 5400,
                    "icu_training_load": 85,
                    "icu_intensity": 0.72,
                    "icu_np": 180,
                    "average_hr": 135,
                    "trainer": True,
                }
            },
            {
                "intervals_activity": {
                    "id": "12346",
                    "name": "SST Intervals",
                    "start_date_local": "2026-01-15T14:00:00",
                    "type": "Ride",
                    "moving_time": 4200,
                    "icu_training_load": 95,
                    "icu_intensity": 0.88,
                    "icu_np": 220,
                    "average_hr": 155,
                    "trainer": False,
                }
            },
        ]

        collector = DataCollector()

        # When: Formatting activities
        activities = collector._format_activities(workouts)

        # Then: Should return properly formatted activities list
        assert len(activities) == 2
        assert activities[0]["name"] == "Z2 Base Indoor"
        assert activities[0]["tss"] == 85
        assert activities[0]["if_"] == 0.72
        assert activities[0]["indoor"] is True
        assert activities[1]["name"] == "SST Intervals"
        assert activities[1]["indoor"] is False

        # Activities should be sorted by start_date
        assert activities[0]["start_date"] < activities[1]["start_date"]

    def test_format_activities_empty_list(self):
        """Test formatting empty workouts list."""
        # Given: Empty workouts list
        workouts = []

        collector = DataCollector()

        # When: Formatting activities
        activities = collector._format_activities(workouts)

        # Then: Should return empty list
        assert activities == []

    def test_format_activities_missing_intervals_activity(self):
        """Test formatting handles missing intervals_activity."""
        # Given: Workout without intervals_activity
        workouts = [{"some_other_data": "value"}]

        collector = DataCollector()

        # When: Formatting activities (logs warning)
        activities = collector._format_activities(workouts)

        # Then: Should skip invalid workout and return empty list
        assert activities == []


class TestExtractWellnessData:
    """Tests for _extract_wellness_data helper method."""

    def test_extract_wellness_data_with_metrics(self):
        """Test extracting wellness data from processed data."""
        # Given: Processed data with metrics evolution
        processed_data = {
            "metrics_evolution": {
                "daily_metrics": [
                    {
                        "hrv": 55,
                        "sleep_quality": 7.0,
                        "fatigue": 4.0,
                        "readiness": 7.5,
                    },
                    {
                        "hrv": 58,
                        "sleep_quality": 7.2,
                        "fatigue": 3.5,
                        "readiness": 8.1,
                    },
                    {
                        "hrv": 60,
                        "sleep_quality": 7.5,
                        "fatigue": 3.0,
                        "readiness": 8.5,
                    },
                ]
            }
        }

        collector = DataCollector()

        # When: Extracting wellness data
        wellness = collector._extract_wellness_data(processed_data)

        # Then: Should calculate averages correctly
        assert wellness["hrv_avg"] == 57.7  # (55 + 58 + 60) / 3
        assert wellness["hrv_trend"] == "increasing"
        assert wellness["sleep_quality_avg"] == 7.2  # (7.0 + 7.2 + 7.5) / 3
        assert wellness["fatigue_score_avg"] == 3.5  # (4.0 + 3.5 + 3.0) / 3
        assert wellness["readiness_avg"] == 8.0  # (7.5 + 8.1 + 8.5) / 3

    def test_extract_wellness_data_no_metrics(self):
        """Test extracting wellness data when no metrics available."""
        # Given: Processed data without metrics
        processed_data = {}

        collector = DataCollector()

        # When: Extracting wellness data
        wellness = collector._extract_wellness_data(processed_data)

        # Then: Should return N/A for all metrics
        assert wellness["hrv_avg"] == "N/A"
        assert wellness["hrv_trend"] == "stable"
        assert wellness["sleep_quality_avg"] == "N/A"
        assert wellness["fatigue_score_avg"] == "N/A"
        assert wellness["readiness_avg"] == "N/A"


class TestExtractLearnings:
    """Tests for _extract_learnings helper method."""

    def test_extract_learnings_with_data(self):
        """Test extracting learnings from processed data."""
        # Given: Processed data with learnings
        processed_data = {
            "learnings": [
                {
                    "type": "protocol_validation",
                    "title": "Z2 Protocol Validated",
                    "description": "90min Z2 indoor @ 72% IF maintained",
                    "session_id": "12345",
                    "confidence": "high",
                },
                {
                    "type": "performance_discovery",
                    "title": "SST Capacity Confirmed",
                    "description": "3x8min SST @ 88% IF",
                    "session_id": "12346",
                    "confidence": "high",
                },
            ]
        }

        collector = DataCollector()

        # When: Extracting learnings
        learnings = collector._extract_learnings(processed_data)

        # Then: Should return formatted learnings
        assert len(learnings) == 2
        assert learnings[0]["type"] == "protocol_validation"
        assert learnings[0]["title"] == "Z2 Protocol Validated"
        assert learnings[1]["type"] == "performance_discovery"

    def test_extract_learnings_empty_list(self):
        """Test extracting learnings when none available."""
        # Given: Processed data without learnings
        processed_data = {"learnings": []}

        collector = DataCollector()

        # When: Extracting learnings
        learnings = collector._extract_learnings(processed_data)

        # Then: Should return empty list
        assert learnings == []


class TestExtractMetricsEvolution:
    """Tests for _extract_metrics_evolution helper method."""

    def test_extract_metrics_evolution_with_data(self):
        """Test extracting metrics evolution (start vs end)."""
        # Given: Processed data with daily metrics
        processed_data = {
            "metrics_evolution": {
                "daily_metrics": [
                    {"ctl": 100, "atl": 50, "tsb": 50, "hrv": 58},
                    {"ctl": 102, "atl": 52, "tsb": 50, "hrv": 57},
                    {"ctl": 105, "atl": 55, "tsb": 50, "hrv": 58},
                ]
            }
        }

        collector = DataCollector()

        # When: Extracting metrics evolution
        metrics = collector._extract_metrics_evolution(processed_data)

        # Then: Should return start and end metrics
        assert metrics["start"]["ctl"] == 100
        assert metrics["start"]["atl"] == 50
        assert metrics["start"]["tsb"] == 50
        assert metrics["start"]["hrv"] == 58
        assert metrics["end"]["ctl"] == 105
        assert metrics["end"]["atl"] == 55
        assert metrics["end"]["tsb"] == 50
        assert metrics["end"]["hrv"] == 58

    def test_extract_metrics_evolution_no_data(self):
        """Test extracting metrics evolution when no data available."""
        # Given: Processed data without metrics
        processed_data = {}

        collector = DataCollector()

        # When: Extracting metrics evolution
        metrics = collector._extract_metrics_evolution(processed_data)

        # Then: Should return empty start and end dicts
        assert metrics == {"start": {}, "end": {}}


class TestCalculateTrend:
    """Tests for _calculate_trend helper method."""

    def test_calculate_trend_increasing(self):
        """Test trend calculation for increasing values."""
        # Given: Increasing values
        values = [50, 52, 55, 58, 60]

        collector = DataCollector()

        # When: Calculating trend
        trend = collector._calculate_trend(values)

        # Then: Should detect increasing trend
        assert trend == "increasing"

    def test_calculate_trend_decreasing(self):
        """Test trend calculation for decreasing values."""
        # Given: Decreasing values
        values = [60, 58, 55, 52, 50]

        collector = DataCollector()

        # When: Calculating trend
        trend = collector._calculate_trend(values)

        # Then: Should detect decreasing trend
        assert trend == "decreasing"

    def test_calculate_trend_stable(self):
        """Test trend calculation for stable values."""
        # Given: Stable values (small variations)
        values = [58, 57, 58, 59, 58]

        collector = DataCollector()

        # When: Calculating trend
        trend = collector._calculate_trend(values)

        # Then: Should detect stable trend
        assert trend == "stable"

    def test_calculate_trend_empty_list(self):
        """Test trend calculation with empty list."""
        # Given: Empty values
        values = []

        collector = DataCollector()

        # When: Calculating trend
        trend = collector._calculate_trend(values)

        # Then: Should return stable for empty list
        assert trend == "stable"

    def test_calculate_trend_single_value(self):
        """Test trend calculation with single value."""
        # Given: Single value
        values = [58]

        collector = DataCollector()

        # When: Calculating trend
        trend = collector._calculate_trend(values)

        # Then: Should return stable for single value
        assert trend == "stable"
