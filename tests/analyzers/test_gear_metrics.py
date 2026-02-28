"""Tests for Di2 gear metrics extraction and analysis.

Tests cover _extract_gear_metrics() in WeeklyAggregator
for calculating shifts, cross-chaining, and patterns.
"""

from datetime import date
from unittest.mock import Mock, patch

import pytest

from magma_cycling.analyzers.weekly_aggregator import WeeklyAggregator


class TestExtractGearMetrics:
    """Test suite for gear metrics extraction."""

    @pytest.fixture
    def aggregator(self):
        """Create WeeklyAggregator with mocked API (Sprint R9.B Phase 2)."""

        # Create aggregator (API initialization will be mocked below)
        with patch("magma_cycling.analyzers.weekly_aggregator.create_intervals_client"):
            aggregator = WeeklyAggregator(week="S075", start_date=date(2026, 1, 5))
            # Mock the API
            aggregator.api = Mock()
            return aggregator

    @pytest.fixture
    def complete_di2_streams(self):
        """Complete Di2 streams (23 shifts scenario)."""
        return [
            {
                "type": "FrontGear",
                "data": [50, 50, 50, 50, 34, 34, 34, 34, 50, 50],  # 2 front shifts
            },
            {"type": "RearGear", "data": [21, 24, 27, 30, 30, 27, 24, 21, 21, 18]},  # 8 rear shifts
            {
                "type": "GearRatio",
                "data": [2.38, 2.08, 1.85, 1.67, 1.13, 1.26, 1.42, 1.62, 2.38, 2.78],
            },
        ]

    @pytest.fixture
    def cross_chaining_streams(self):
        """Di2 streams with cross-chaining (50T + 27T)."""
        return [
            {"type": "FrontGear", "data": [50] * 100},  # Always 50T
            {"type": "RearGear", "data": [27] * 50 + [21] * 50},  # 50% on 27T (cross-chain)
            {"type": "GearRatio", "data": [1.85] * 50 + [2.38] * 50},
        ]

    def test_extract_gear_metrics_complete_data(self, aggregator, complete_di2_streams):
        """Test complete metrics extraction with all Di2 streams."""
        # Given: Activity with complete Di2 data
        activity_id = "i107424849"
        aggregator.api.get_activity_streams.return_value = complete_di2_streams

        # When: Extracting gear metrics
        metrics = aggregator._extract_gear_metrics(activity_id)

        # Then: All metrics calculated
        assert metrics is not None
        assert "shifts" in metrics
        assert "front_shifts" in metrics
        assert "rear_shifts" in metrics
        assert "avg_gear_ratio" in metrics
        assert "gear_ratio_distribution" in metrics

        # Verify shift counts
        assert metrics["shifts"] == 9  # 2 front + 7 rear
        assert metrics["front_shifts"] == 2
        assert metrics["rear_shifts"] == 7

        # Verify avg ratio (approximate)
        assert metrics["avg_gear_ratio"] > 1.5
        assert metrics["avg_gear_ratio"] < 2.5

        # Verify distribution is dict
        assert isinstance(metrics["gear_ratio_distribution"], dict)
        assert len(metrics["gear_ratio_distribution"]) > 0

    def test_extract_gear_metrics_cross_chaining_detection(
        self, aggregator, cross_chaining_streams
    ):
        """Test cross-chaining pattern detection in metrics."""
        # Given: Streams with known cross-chaining (50T + 27T)
        activity_id = "i107424850"
        aggregator.api.get_activity_streams.return_value = cross_chaining_streams

        # When: Extracting metrics
        metrics = aggregator._extract_gear_metrics(activity_id)

        # Then: Metrics extracted (cross-chain % calculated separately)
        assert metrics is not None
        assert metrics["shifts"] == 1  # One shift 27T → 21T
        assert metrics["front_shifts"] == 0  # Always 50T
        assert metrics["rear_shifts"] == 1

        # Verify distribution contains 1.85 ratio (50T-27T cross-chain)
        distribution = metrics["gear_ratio_distribution"]
        assert any(abs(ratio - 1.85) < 0.1 for ratio in distribution.keys())

    def test_extract_gear_metrics_empty_streams(self, aggregator):
        """Test handling of empty streams (no Di2 data)."""
        # Given: Activity without Di2 (empty streams)
        activity_id = "i107424851"
        aggregator.api.get_activity_streams.return_value = []

        # When: Extracting metrics
        metrics = aggregator._extract_gear_metrics(activity_id)

        # Then: Returns None (no Di2 data available)
        assert metrics is None

    def test_extract_gear_metrics_missing_front_gear(self, aggregator):
        """Test handling of missing FrontGear stream."""
        # Given: Only RearGear (FrontGear sensor failure)
        activity_id = "i107424852"
        streams_missing_front = [
            {"type": "RearGear", "data": [21, 24, 27]},
            {"type": "GearRatio", "data": [2.38, 2.08, 1.85]},
        ]
        aggregator.api.get_activity_streams.return_value = streams_missing_front

        # When: Extracting metrics
        metrics = aggregator._extract_gear_metrics(activity_id)

        # Then: Returns None (incomplete Di2 data)
        assert metrics is None

    def test_extract_gear_metrics_missing_rear_gear(self, aggregator):
        """Test handling of missing RearGear stream."""
        # Given: Only FrontGear (RearGear sensor failure)
        activity_id = "i107424853"
        streams_missing_rear = [
            {"type": "FrontGear", "data": [50, 50, 34]},
            {"type": "GearRatio", "data": [2.38, 2.08, 1.26]},
        ]
        aggregator.api.get_activity_streams.return_value = streams_missing_rear

        # When: Extracting metrics
        metrics = aggregator._extract_gear_metrics(activity_id)

        # Then: Returns None (incomplete Di2 data)
        assert metrics is None

    def test_extract_gear_metrics_with_none_values(self, aggregator):
        """Test filtering of None values in streams."""
        # Given: Streams with None (signal dropout)
        activity_id = "i107424854"
        streams_with_none = [
            {"type": "FrontGear", "data": [50, 50, None, 34, None, 50]},
            {"type": "RearGear", "data": [21, None, 24, 27, 27, None]},
            {"type": "GearRatio", "data": [2.38, None, 2.08, 1.26, 1.26, None]},
        ]
        aggregator.api.get_activity_streams.return_value = streams_with_none

        # When: Extracting metrics
        metrics = aggregator._extract_gear_metrics(activity_id)

        # Then: Metrics calculated from valid data only
        assert metrics is not None
        # Valid data points: [50,50,34,50] and [21,24,27,27] after filtering None
        assert metrics["shifts"] >= 3  # At least 3 shifts after filtering

    def test_gear_ratio_distribution_top_5(self, aggregator, complete_di2_streams):
        """Test that distribution contains top 5 ratios only."""
        # Given: Streams with multiple ratios
        activity_id = "i107424855"

        # Create streams with 10 different ratios (but top 5 should be returned)
        streams_many_ratios = [
            {"type": "FrontGear", "data": [50] * 100},
            {
                "type": "RearGear",
                "data": [11] * 20
                + [13] * 18
                + [15] * 16
                + [17] * 14
                + [19] * 12
                + [21] * 10
                + [24] * 5
                + [27] * 3
                + [30] * 1
                + [34] * 1,
            },
            {
                "type": "GearRatio",
                "data": [4.55] * 20
                + [3.85] * 18
                + [3.33] * 16
                + [2.94] * 14
                + [2.63] * 12
                + [2.38] * 10
                + [2.08] * 5
                + [1.85] * 3
                + [1.67] * 1
                + [1.47] * 1,
            },
        ]
        aggregator.api.get_activity_streams.return_value = streams_many_ratios

        # When: Extracting metrics
        metrics = aggregator._extract_gear_metrics(activity_id)

        # Then: Distribution has max 5 entries (top 5)
        assert metrics is not None
        distribution = metrics["gear_ratio_distribution"]
        assert len(distribution) <= 5

    def test_extract_gear_metrics_api_exception(self, aggregator):
        """Test graceful handling of API exceptions."""
        # Given: API raises exception
        activity_id = "i107424856"
        aggregator.api.get_activity_streams.side_effect = Exception("API Error")

        # When: Extracting metrics
        metrics = aggregator._extract_gear_metrics(activity_id)

        # Then: Returns None (exception caught)
        assert metrics is None

    def test_extract_gear_metrics_no_shifts(self, aggregator):
        """Test activity with single gear (0 shifts)."""
        # Given: Constant gear throughout (e.g., indoor trainer with Di2 bike)
        activity_id = "i107424857"
        streams_no_shifts = [
            {"type": "FrontGear", "data": [50] * 100},
            {"type": "RearGear", "data": [21] * 100},
            {"type": "GearRatio", "data": [2.38] * 100},
        ]
        aggregator.api.get_activity_streams.return_value = streams_no_shifts

        # When: Extracting metrics
        metrics = aggregator._extract_gear_metrics(activity_id)

        # Then: 0 shifts recorded
        assert metrics is not None
        assert metrics["shifts"] == 0
        assert metrics["front_shifts"] == 0
        assert metrics["rear_shifts"] == 0
        assert metrics["avg_gear_ratio"] == 2.38

        # Distribution should have single entry
        distribution = metrics["gear_ratio_distribution"]
        assert len(distribution) == 1
        assert 2.38 in distribution
