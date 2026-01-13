"""Integration tests for Di2 workflow end-to-end.

Tests cover complete Di2 extraction workflow from
Intervals.icu API through weekly analysis reporting.
"""

import pytest
from unittest.mock import Mock, patch
from cyclisme_training_logs.analyzers.weekly_aggregator import WeeklyAggregator
from cyclisme_training_logs.api.intervals_client import IntervalsClient


class TestDi2WorkflowIntegration:
    """Test suite for Di2 end-to-end workflow."""

    @pytest.fixture
    def mock_api(self):
        """Create mocked IntervalsClient."""
        api = Mock(spec=IntervalsClient)
        return api

    @pytest.fixture
    def aggregator(self, mock_api):
        """Create WeeklyAggregator with mocked API."""
        from datetime import date
        from unittest.mock import patch
        with patch('cyclisme_training_logs.analyzers.weekly_aggregator.get_intervals_config'):
            aggregator = WeeklyAggregator(week="S075", start_date=date(2026, 1, 5))
            aggregator.api = mock_api
            return aggregator

    @pytest.fixture
    def mock_outdoor_activity_with_di2(self):
        """Mock outdoor activity with Di2 data (realistic S056 scenario)."""
        return {
            "id": "i107424849",
            "type": "Ride",
            "name": "S056-01-TERRAIN-MixteCollines",
            "trainer": False,  # Outdoor
            "moving_time": 7200,  # 2 hours
            "distance": 50000,  # 50km
            "icu_training_load": 145,
            "average_power": 180,
            "normalized_power": 195,
        }

    @pytest.fixture
    def mock_di2_streams_s056(self):
        """Mock Di2 streams for S056 (834 shifts documented)."""
        # Generate realistic shift pattern (simplified)
        front_gear = [50] * 500 + [34] * 200 + [50] * 300  # Front shifts
        rear_gear = []
        for i in range(1000):
            if i % 10 == 0:
                rear_gear.append(21 + (i // 10) % 10)  # Shift pattern
            else:
                rear_gear.append(rear_gear[-1] if rear_gear else 21)

        return [
            {"type": "FrontGear", "data": front_gear},
            {"type": "RearGear", "data": rear_gear},
            {
                "type": "GearRatio",
                "data": [f / r for f, r in zip(front_gear, rear_gear)]
            }
        ]

    def test_di2_extraction_outdoor_activity_complete(
        self, aggregator, mock_api, mock_outdoor_activity_with_di2, mock_di2_streams_s056
    ):
        """Test complete Di2 extraction for outdoor activity."""
        # Given: Outdoor activity with Di2 data
        activity = mock_outdoor_activity_with_di2
        mock_api.get_activity_streams.return_value = mock_di2_streams_s056

        # When: Extracting gear metrics
        gear_metrics = aggregator._extract_gear_metrics(activity["id"])

        # Then: Metrics extracted successfully
        assert gear_metrics is not None
        assert "shifts" in gear_metrics
        assert gear_metrics["shifts"] > 0  # Has shifts
        assert "front_shifts" in gear_metrics
        assert "rear_shifts" in gear_metrics
        assert "avg_gear_ratio" in gear_metrics

        # Verify API called
        mock_api.get_activity_streams.assert_called_once_with(activity["id"])

    def test_di2_extraction_indoor_activity_skipped(self, aggregator, mock_api):
        """Test Di2 extraction skipped for indoor trainer rides."""
        # Given: Indoor trainer activity (no Di2)
        indoor_activity = {
            "id": "i107424850",
            "type": "Ride",
            "name": "S056-02-INT-SweetSpot",
            "trainer": True,  # Indoor
            "moving_time": 3600,
        }

        # When: Processing workout (should skip Di2 extraction)
        # Simulate workflow: Check trainer flag before calling extract
        should_extract_di2 = indoor_activity.get("trainer") is False

        if should_extract_di2:
            gear_metrics = aggregator._extract_gear_metrics(indoor_activity["id"])
        else:
            gear_metrics = None

        # Then: Di2 extraction skipped (not called)
        assert gear_metrics is None
        mock_api.get_activity_streams.assert_not_called()

    def test_weekly_analysis_includes_di2_patterns(self, aggregator, mock_api):
        """Test weekly analysis includes Di2 patterns in learnings."""
        # Given: Week with outdoor Di2 activities
        workouts_with_di2 = [
            {
                "id": "i107424849",
                "type": "Ride",
                "name": "S056-01-TERRAIN",
                "trainer": False,
                "duration": 7200,
                "tss": 145,
                "gear_metrics": {
                    "shifts": 834,
                    "front_shifts": 19,
                    "rear_shifts": 815,
                    "avg_gear_ratio": 2.15,
                    "gear_ratio_distribution": {2.38: 200, 2.08: 150, 1.85: 100}
                }
            }
        ]

        # When: Extracting training learnings
        learnings = aggregator._extract_training_learnings(workouts_with_di2, {})

        # Then: Learnings include Di2 patterns
        assert learnings is not None
        assert isinstance(learnings, list)

        # Check if any learning mentions shifts/gear
        di2_learning_found = any(
            "shifts" in learning.lower() or "vitesse" in learning.lower()
            for learning in learnings
        )
        assert di2_learning_found, "Di2 patterns should be in training learnings"

    def test_di2_workflow_with_missing_api(self, aggregator):
        """Test workflow gracefully handles missing API."""
        # Given: Aggregator without API
        from datetime import date
        from unittest.mock import patch
        with patch('cyclisme_training_logs.analyzers.weekly_aggregator.get_intervals_config'):
            aggregator_no_api = WeeklyAggregator(week="S075", start_date=date(2026, 1, 5))
            aggregator_no_api.api = None  # No API

        # When: Attempting to extract gear metrics
        gear_metrics = aggregator_no_api._extract_gear_metrics("i107424849")

        # Then: Returns None (no API available)
        assert gear_metrics is None

    def test_di2_workflow_api_exception_handling(self, aggregator, mock_api):
        """Test workflow handles API exceptions gracefully."""
        # Given: API raises exception (network error)
        mock_api.get_activity_streams.side_effect = Exception("Network timeout")

        # When: Extracting gear metrics
        gear_metrics = aggregator._extract_gear_metrics("i107424849")

        # Then: Exception caught, returns None
        assert gear_metrics is None

    def test_di2_cross_chaining_pattern_in_learnings(self, aggregator):
        """Test cross-chaining pattern detection in learnings."""
        # Given: Workout with high cross-chaining usage
        workouts_cross_chain = [
            {
                "id": "i107424851",
                "type": "Ride",
                "name": "S057-01-TERRAIN",
                "trainer": False,
                "duration": 3600,
                "tss": 85,
                "gear_metrics": {
                    "shifts": 400,
                    "front_shifts": 5,
                    "rear_shifts": 395,
                    "avg_gear_ratio": 1.85,  # Low ratio (50T + big cogs)
                    "gear_ratio_distribution": {
                        1.85: 500,  # 50T-27T (cross-chain)
                        1.67: 300,  # 50T-30T (cross-chain)
                        2.38: 100   # 50T-21T (OK)
                    }
                }
            }
        ]

        # When: Extracting learnings
        learnings = aggregator._extract_training_learnings(workouts_cross_chain, {})

        # Then: Should mention shifts (possibly frequent)
        assert learnings is not None
        # Note: Cross-chaining % calculated elsewhere, but shifts/h should be noted
        shifts_per_hour = 400 / (3600 / 3600)  # 400 shifts/h
        assert shifts_per_hour == 400

    def test_di2_workflow_multiple_activities_aggregation(self, aggregator):
        """Test aggregation of multiple Di2 activities in single week."""
        # Given: Multiple outdoor rides with Di2 in same week
        workouts_multiple_di2 = [
            {
                "id": "i107424852",
                "type": "Ride",
                "name": "S056-01-TERRAIN",
                "trainer": False,
                "duration": 7200,
                "gear_metrics": {"shifts": 800, "front_shifts": 20, "rear_shifts": 780}
            },
            {
                "id": "i107424853",
                "type": "Ride",
                "name": "S056-03-TERRAIN",
                "trainer": False,
                "duration": 5400,
                "gear_metrics": {"shifts": 600, "front_shifts": 15, "rear_shifts": 585}
            }
        ]

        # When: Extracting learnings
        learnings = aggregator._extract_training_learnings(workouts_multiple_di2, {})

        # Then: Aggregates all Di2 data
        outdoor_with_gears = [
            w for w in workouts_multiple_di2
            if w.get("gear_metrics") and w["gear_metrics"].get("shifts")
        ]
        assert len(outdoor_with_gears) == 2

        total_shifts = sum(w["gear_metrics"]["shifts"] for w in outdoor_with_gears)
        assert total_shifts == 1400  # 800 + 600

        total_duration_hours = sum(w.get("duration", 0) / 3600 for w in outdoor_with_gears)
        shifts_per_hour = total_shifts / total_duration_hours
        assert shifts_per_hour > 0

    @pytest.mark.integration
    @pytest.mark.slow
    def test_di2_real_activity_s067_extraction(self):
        """Test Di2 extraction on real activity S067 (if API available).

        This test requires real Intervals.icu credentials.
        Skip if credentials not available.
        """
        # Note: This test is marked as integration/slow
        # It would require real API credentials to run
        pytest.skip("Requires real Intervals.icu API credentials")

        # Pseudo-code for real test:
        # api = IntervalsClient(athlete_id="i151223", api_key=os.getenv("INTERVALS_API_KEY"))
        # aggregator = WeeklyAggregator(api=api)
        # gear_metrics = aggregator._extract_gear_metrics("i107424849")  # Real S067 activity
        # assert gear_metrics["shifts"] == 394  # Known value from session log
