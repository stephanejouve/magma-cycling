"""Tests for metrics utilities (Sprint R2)."""

import pytest

from cyclisme_training_logs.utils.metrics import (
    calculate_metrics_change,
    calculate_tsb,
    extract_wellness_metrics,
    format_metrics_display,
    get_metrics_safely,
    is_metrics_complete,
)


class TestExtractWellnessMetrics:
    """Tests for extract_wellness_metrics function."""

    def test_extract_complete_wellness(self):
        """Test extracting metrics from complete wellness data."""
        wellness = {"ctl": 45.6, "atl": 37.7, "tsb": 7.9}

        result = extract_wellness_metrics(wellness)

        assert result["ctl"] == 45.6
        assert result["atl"] == 37.7
        assert result["tsb"] == 7.9

    def test_extract_none_wellness(self):
        """Test extracting metrics from None wellness data."""
        result = extract_wellness_metrics(None)

        assert result["ctl"] == 0.0
        assert result["atl"] == 0.0
        assert result["tsb"] == 0.0

    def test_extract_with_none_values(self):
        """Test extracting metrics with None values in wellness data."""
        wellness = {"ctl": None, "atl": 35.0, "tsb": None}

        result = extract_wellness_metrics(wellness)

        assert result["ctl"] == 0.0
        assert result["atl"] == 35.0
        assert result["tsb"] == -35.0  # Calculated from ctl - atl

    def test_extract_without_tsb(self):
        """Test extracting metrics when TSB not provided (needs calculation)."""
        wellness = {"ctl": 45.6, "atl": 37.7}

        result = extract_wellness_metrics(wellness)

        assert result["ctl"] == 45.6
        assert result["atl"] == 37.7
        assert result["tsb"] == pytest.approx(7.9, abs=0.1)

    def test_extract_empty_dict(self):
        """Test extracting metrics from empty dict."""
        wellness = {}

        result = extract_wellness_metrics(wellness)

        assert result["ctl"] == 0.0
        assert result["atl"] == 0.0
        assert result["tsb"] == 0.0


class TestCalculateTSB:
    """Tests for calculate_tsb function."""

    def test_calculate_positive_tsb(self):
        """Test calculating positive TSB (fit > fatigued)."""
        tsb = calculate_tsb(45.6, 37.7)

        assert tsb == pytest.approx(7.9, abs=0.1)

    def test_calculate_negative_tsb(self):
        """Test calculating negative TSB (fatigued > fit)."""
        tsb = calculate_tsb(40.0, 50.0)

        assert tsb == -10.0

    def test_calculate_zero_tsb(self):
        """Test calculating zero TSB (balanced)."""
        tsb = calculate_tsb(45.0, 45.0)

        assert tsb == 0.0


class TestFormatMetricsDisplay:
    """Tests for format_metrics_display function."""

    def test_format_positive_tsb(self):
        """Test formatting metrics with positive TSB."""
        metrics = {"ctl": 45.6, "atl": 37.7, "tsb": 7.9}

        result = format_metrics_display(metrics)

        assert result == "CTL: 45.6 | ATL: 37.7 | TSB: +7.9"

    def test_format_negative_tsb(self):
        """Test formatting metrics with negative TSB."""
        metrics = {"ctl": 40.0, "atl": 50.0, "tsb": -10.0}

        result = format_metrics_display(metrics)

        assert result == "CTL: 40.0 | ATL: 50.0 | TSB: -10.0"

    def test_format_zero_tsb(self):
        """Test formatting metrics with zero TSB."""
        metrics = {"ctl": 45.0, "atl": 45.0, "tsb": 0.0}

        result = format_metrics_display(metrics)

        assert result == "CTL: 45.0 | ATL: 45.0 | TSB: +0.0"

    def test_format_missing_values(self):
        """Test formatting with missing values (should default to 0)."""
        metrics = {}

        result = format_metrics_display(metrics)

        assert result == "CTL: 0.0 | ATL: 0.0 | TSB: +0.0"


class TestIsMetricsComplete:
    """Tests for is_metrics_complete function."""

    def test_complete_metrics(self):
        """Test with complete metrics."""
        metrics = {"ctl": 45.6, "atl": 37.7, "tsb": 7.9}

        assert is_metrics_complete(metrics) is True

    def test_zero_values_are_complete(self):
        """Test that zero values are still considered complete."""
        metrics = {"ctl": 0, "atl": 0, "tsb": 0}

        assert is_metrics_complete(metrics) is True

    def test_none_value(self):
        """Test with None value."""
        metrics = {"ctl": None, "atl": 37.7, "tsb": 7.9}

        assert is_metrics_complete(metrics) is False

    def test_missing_key(self):
        """Test with missing key."""
        metrics = {"ctl": 45.6, "atl": 37.7}  # Missing tsb

        assert is_metrics_complete(metrics) is False

    def test_empty_dict(self):
        """Test with empty dict."""
        assert is_metrics_complete({}) is False

    def test_none_dict(self):
        """Test with None dict."""
        assert is_metrics_complete(None) is False

    def test_invalid_type(self):
        """Test with invalid value type."""
        metrics = {"ctl": "invalid", "atl": 37.7, "tsb": 7.9}

        assert is_metrics_complete(metrics) is False


class TestCalculateMetricsChange:
    """Tests for calculate_metrics_change function."""

    def test_calculate_positive_change(self):
        """Test calculating positive change in metrics."""
        start = {"ctl": 40.0, "atl": 35.0, "tsb": 5.0}

        end = {"ctl": 45.6, "atl": 37.7, "tsb": 7.9}
        result = calculate_metrics_change(start, end)

        assert result["ctl_change"] == pytest.approx(5.6, abs=0.1)
        assert result["atl_change"] == pytest.approx(2.7, abs=0.1)
        assert result["tsb_change"] == pytest.approx(2.9, abs=0.1)

    def test_calculate_negative_change(self):
        """Test calculating negative change (decrease)."""
        start = {"ctl": 50.0, "atl": 40.0, "tsb": 10.0}

        end = {"ctl": 45.0, "atl": 37.0, "tsb": 8.0}
        result = calculate_metrics_change(start, end)

        assert result["ctl_change"] == -5.0
        assert result["atl_change"] == -3.0
        assert result["tsb_change"] == -2.0

    def test_calculate_with_none_values(self):
        """Test calculating change with None values."""
        start = {"ctl": None, "atl": 35.0, "tsb": None}

        end = {"ctl": 45.6, "atl": 37.7, "tsb": 7.9}
        result = calculate_metrics_change(start, end)

        assert result["ctl_change"] is None  # Can't calculate with None start
        assert result["atl_change"] == pytest.approx(2.7, abs=0.1)
        assert result["tsb_change"] is None  # Can't calculate with None start

    def test_calculate_no_change(self):
        """Test calculating with no change."""
        start = {"ctl": 45.0, "atl": 37.0, "tsb": 8.0}

        end = {"ctl": 45.0, "atl": 37.0, "tsb": 8.0}
        result = calculate_metrics_change(start, end)

        assert result["ctl_change"] == 0.0
        assert result["atl_change"] == 0.0
        assert result["tsb_change"] == 0.0


class TestGetMetricsSafely:
    """Tests for get_metrics_safely function."""

    def test_get_from_valid_list(self):
        """Test getting metrics from valid wellness list."""
        wellness_list = [
            {"id": "2025-12-01", "ctl": 45.6, "atl": 37.7},
            {"id": "2025-11-30", "ctl": 44.0, "atl": 36.0},
        ]
        result = get_metrics_safely(wellness_list, index=0)

        assert result["ctl"] == 45.6
        assert result["atl"] == 37.7
        assert result["tsb"] == pytest.approx(7.9, abs=0.1)

    def test_get_from_second_index(self):
        """Test getting metrics from second index."""
        wellness_list = [
            {"id": "2025-12-01", "ctl": 45.6, "atl": 37.7},
            {"id": "2025-11-30", "ctl": 44.0, "atl": 36.0},
        ]
        result = get_metrics_safely(wellness_list, index=1)

        assert result["ctl"] == 44.0
        assert result["atl"] == 36.0

    def test_get_from_none_list(self):
        """Test getting metrics from None list."""
        result = get_metrics_safely(None)

        assert result["ctl"] == 0.0
        assert result["atl"] == 0.0
        assert result["tsb"] == 0.0

    def test_get_from_empty_list(self):
        """Test getting metrics from empty list."""
        result = get_metrics_safely([])

        assert result["ctl"] == 0.0
        assert result["atl"] == 0.0
        assert result["tsb"] == 0.0

    def test_get_out_of_bounds_index(self):
        """Test getting metrics with out of bounds index."""
        wellness_list = [{"id": "2025-12-01", "ctl": 45.6, "atl": 37.7}]

        result = get_metrics_safely(wellness_list, index=5)

        assert result["ctl"] == 0.0
        assert result["atl"] == 0.0
        assert result["tsb"] == 0.0

    def test_get_negative_index(self):
        """Test getting metrics with negative index."""
        wellness_list = [{"id": "2025-12-01", "ctl": 45.6, "atl": 37.7}]

        result = get_metrics_safely(wellness_list, index=-1)

        assert result["ctl"] == 0.0
        assert result["atl"] == 0.0
        assert result["tsb"] == 0.0

    def test_get_with_incomplete_data(self):
        """Test getting metrics when wellness entry has incomplete data."""
        wellness_list = [{"id": "2025-12-01"}]  # No CTL/ATL

        result = get_metrics_safely(wellness_list, index=0)

        assert result["ctl"] == 0.0
        assert result["atl"] == 0.0
        assert result["tsb"] == 0.0
