"""Tests for advanced metrics utilities.

Test coverage for Sprint R2.1 advanced functions:
- calculate_ramp_rate
- get_weekly_metrics_trend
- detect_training_peaks
- get_recovery_recommendation
- format_metrics_comparison
- detect_overtraining_risk (CRITICAL)
"""
import pytest

from cyclisme_training_logs.utils.metrics_advanced import (
    calculate_ramp_rate,
    detect_overtraining_risk,
    detect_training_peaks,
    format_metrics_comparison,
    get_recovery_recommendation,
    get_weekly_metrics_trend,
)

# ============================================================================
# Test calculate_ramp_rate
# ============================================================================


def test_calculate_ramp_rate_weekly_increase():
    """Test CTL increasing 5 points over 1 week."""
    result = calculate_ramp_rate(65.0, 60.0, days=7)
    assert result == 5.0


def test_calculate_ramp_rate_biweekly():
    """Test CTL increasing 5 points over 2 weeks = 2.5 points/week."""
    result = calculate_ramp_rate(65.0, 60.0, days=14)
    assert result == 2.5


def test_calculate_ramp_rate_declining():
    """Test CTL declining (negative ramp rate)."""
    result = calculate_ramp_rate(60.0, 65.0, days=7)
    assert result == -5.0


def test_calculate_ramp_rate_zero_days_raises():
    """Test that zero days raises ValueError."""
    with pytest.raises(ValueError, match="days must be positive"):
        calculate_ramp_rate(65.0, 60.0, days=0)


def test_calculate_ramp_rate_negative_days_raises():
    """Test that negative days raises ValueError."""
    with pytest.raises(ValueError, match="days must be positive"):
        calculate_ramp_rate(65.0, 60.0, days=-7)


# ============================================================================
# Test get_weekly_metrics_trend
# ============================================================================


def test_weekly_trend_rising():
    """Test detecting rising trend in CTL."""
    data = [
        {"ctl": 60.0, "week": 1},
        {"ctl": 62.0, "week": 2},
        {"ctl": 65.0, "week": 3},
        {"ctl": 67.0, "week": 4},
    ]
    result = get_weekly_metrics_trend(data, "ctl")

    assert result["trend"] == "rising"
    assert result["slope"] > 1.0
    assert result["weeks_analyzed"] == 4


def test_weekly_trend_declining():
    """Test detecting declining trend in CTL."""
    data = [
        {"ctl": 67.0, "week": 1},
        {"ctl": 65.0, "week": 2},
        {"ctl": 62.0, "week": 3},
        {"ctl": 59.0, "week": 4},
    ]
    result = get_weekly_metrics_trend(data, "ctl")

    assert result["trend"] == "declining"
    assert result["slope"] < -1.0
    assert result["weeks_analyzed"] == 4


def test_weekly_trend_stable():
    """Test detecting stable trend in CTL."""
    data = [
        {"ctl": 60.0, "week": 1},
        {"ctl": 60.5, "week": 2},
        {"ctl": 59.5, "week": 3},
        {"ctl": 60.0, "week": 4},
    ]
    result = get_weekly_metrics_trend(data, "ctl")

    assert result["trend"] == "stable"
    assert -1.0 <= result["slope"] <= 1.0
    assert result["weeks_analyzed"] == 4


def test_weekly_trend_empty_data():
    """Test handling empty data."""
    result = get_weekly_metrics_trend([], "ctl")

    assert result["trend"] == "unknown"
    assert result["slope"] == 0.0
    assert result["weeks_analyzed"] == 0


def test_weekly_trend_insufficient_data():
    """Test handling single week data."""
    data = [{"ctl": 60.0, "week": 1}]
    result = get_weekly_metrics_trend(data, "ctl")

    assert result["trend"] == "insufficient_data"
    assert result["weeks_analyzed"] == 1


# ============================================================================
# Test detect_training_peaks
# ============================================================================


def test_detect_peaks_single_peak():
    """Test detecting single significant peak."""
    history = [50, 52, 51, 58, 60, 55, 53]
    peaks = detect_training_peaks(history, threshold_percent=10.0)

    assert len(peaks) >= 1
    assert any(p["value"] >= 58 for p in peaks)
    assert all("increase_percent" in p for p in peaks)


def test_detect_peaks_no_peaks():
    """Test no peaks detected in stable progression."""
    history = [50, 51, 52, 53, 54, 55]
    peaks = detect_training_peaks(history, threshold_percent=10.0)

    # Small gradual increases shouldn't trigger peaks
    assert len(peaks) == 0


def test_detect_peaks_multiple_peaks():
    """Test detecting multiple peaks."""
    history = [50, 52, 58, 55, 52, 62, 60, 55]
    peaks = detect_training_peaks(history, threshold_percent=10.0)

    # Should detect at least one peak (index 5: 62, with 12.7% increase from baseline 55)
    # Note: Index 2 cannot be detected as needs 3 previous values for baseline calculation
    assert len(peaks) >= 1
    assert peaks[0]["index"] == 5
    assert peaks[0]["value"] == 62


def test_detect_peaks_insufficient_history():
    """Test handling insufficient history."""
    history = [50, 52, 51]
    peaks = detect_training_peaks(history, threshold_percent=10.0)

    assert len(peaks) == 0


# ============================================================================
# Test get_recovery_recommendation
# ============================================================================


def test_recovery_recommendation_critical():
    """Test critical recovery recommendation."""
    result = get_recovery_recommendation(
        tsb=-22.0, atl_ctl_ratio=1.7, profile={"age": 54, "category": "master"}
    )

    assert result["priority"] == "critical"
    assert result["intensity_limit"] <= 60
    assert result["rest_days"] >= 2


def test_recovery_recommendation_high():
    """Test high priority recovery recommendation."""
    result = get_recovery_recommendation(
        tsb=-18.0, atl_ctl_ratio=1.45, profile={"age": 54, "category": "master"}
    )

    assert result["priority"] == "high"
    assert result["intensity_limit"] <= 75
    assert "Z2" in result["recommendation"]


def test_recovery_recommendation_medium():
    """Test medium priority recovery recommendation."""
    result = get_recovery_recommendation(
        tsb=-12.0, atl_ctl_ratio=1.25, profile={"age": 35, "category": "senior"}
    )

    assert result["priority"] == "medium"
    assert result["intensity_limit"] <= 90


def test_recovery_recommendation_low():
    """Test low priority (normal training)."""
    result = get_recovery_recommendation(
        tsb=5.0, atl_ctl_ratio=1.0, profile={"age": 35, "category": "senior"}
    )

    assert result["priority"] == "low"
    assert result["intensity_limit"] == 100
    assert "Normal" in result["recommendation"]


def test_recovery_recommendation_master_adjustments():
    """Test that master athletes get more conservative recommendations."""
    result_master = get_recovery_recommendation(
        tsb=-18.0, atl_ctl_ratio=1.45, profile={"age": 54, "category": "master"}
    )

    result_senior = get_recovery_recommendation(
        tsb=-18.0, atl_ctl_ratio=1.45, profile={"age": 35, "category": "senior"}
    )

    # Master should have more rest days
    assert result_master["rest_days"] >= result_senior["rest_days"]
    # Master should have shorter duration limits
    assert result_master["duration_limit"] <= result_senior["duration_limit"]


# ============================================================================
# Test format_metrics_comparison
# ============================================================================


def test_format_comparison_basic():
    """Test basic metrics comparison formatting."""
    p1 = {"ctl": 60.0, "atl": 55.0, "tsb": 5.0}
    p2 = {"ctl": 65.0, "atl": 58.0, "tsb": 7.0}

    result = format_metrics_comparison(p1, p2)

    assert "CTL" in result
    assert "ATL" in result
    assert "TSB" in result
    assert "↑" in result  # At least one metric increased


def test_format_comparison_with_labels():
    """Test comparison with custom labels."""
    p1 = {"ctl": 60.0}
    p2 = {"ctl": 65.0}
    labels = {"period1": "Last Week", "period2": "This Week"}

    result = format_metrics_comparison(p1, p2, labels=labels)

    assert "Last Week" in result
    assert "This Week" in result


def test_format_comparison_declining():
    """Test comparison with declining metrics."""
    p1 = {"ctl": 65.0, "atl": 60.0}
    p2 = {"ctl": 60.0, "atl": 55.0}

    result = format_metrics_comparison(p1, p2)

    assert "↓" in result  # Metrics declined


def test_format_comparison_stable():
    """Test comparison with stable metrics."""
    p1 = {"ctl": 60.0, "atl": 55.0}
    p2 = {"ctl": 60.2, "atl": 55.1}  # Within 0.5 threshold

    result = format_metrics_comparison(p1, p2)

    assert "→" in result  # Stable indicator


# ============================================================================
# Test detect_overtraining_risk (CRITICAL)
# ============================================================================


def test_overtraining_risk_critical_tsb():
    """Test critical overtraining risk from TSB alone."""
    result = detect_overtraining_risk(
        ctl=65.0, atl=95.0, tsb=-30.0, profile={"age": 54, "category": "master"}
    )

    assert result["risk_level"] == "critical"
    assert result["veto"] is True
    assert "VETO" in result["recommendation"]


def test_overtraining_risk_critical_ratio():
    """Test critical overtraining risk from ATL/CTL ratio."""
    result = detect_overtraining_risk(
        ctl=60.0, atl=115.0, tsb=-10.0, profile={"age": 54, "category": "master"}  # Ratio = 1.92
    )

    assert result["risk_level"] == "critical"
    assert result["veto"] is True
    assert result["atl_ctl_ratio"] > 1.8


def test_overtraining_risk_sleep_veto():
    """Test sleep-based veto for master athlete."""
    result = detect_overtraining_risk(
        ctl=65.0,
        atl=70.0,
        tsb=0.0,
        sleep_hours=5.0,  # Below 5.5h threshold
        profile={"age": 54, "category": "master", "sleep_dependent": True},
    )

    assert result["sleep_veto"] is True
    assert result["veto"] is True
    assert result["risk_level"] in ["high", "critical"]


def test_overtraining_risk_combined_sleep_tsb():
    """Test combined sleep + TSB critical condition."""
    result = detect_overtraining_risk(
        ctl=65.0,
        atl=82.0,
        tsb=-17.0,
        sleep_hours=5.8,  # Below 6h
        profile={"age": 54, "category": "master", "sleep_dependent": True},
    )

    assert result["risk_level"] == "critical"
    assert result["veto"] is True
    assert len(result["factors"]) >= 1


def test_overtraining_risk_high():
    """Test high overtraining risk."""
    result = detect_overtraining_risk(
        ctl=65.0, atl=100.0, tsb=-22.0, sleep_hours=7.0, profile={"age": 54, "category": "master"}
    )

    assert result["risk_level"] == "high"
    assert "85% FTP" in result["recommendation"]


def test_overtraining_risk_medium():
    """Test medium overtraining risk."""
    result = detect_overtraining_risk(
        ctl=65.0,
        atl=88.0,
        tsb=-12.0,
        sleep_hours=6.5,
        profile={"age": 54, "category": "master", "sleep_dependent": True},
    )

    assert result["risk_level"] == "medium"
    assert result["veto"] is False


def test_overtraining_risk_low():
    """Test low overtraining risk (normal training)."""
    result = detect_overtraining_risk(
        ctl=65.0, atl=60.0, tsb=5.0, sleep_hours=7.5, profile={"age": 54, "category": "master"}
    )

    assert result["risk_level"] == "low"
    assert result["veto"] is False
    assert "Normal" in result["recommendation"]


def test_overtraining_risk_master_vs_senior():
    """Test that master athletes get more conservative veto recommendations."""
    # Same conditions, different age categories
    result_master = detect_overtraining_risk(
        ctl=65.0, atl=95.0, tsb=-27.0, profile={"age": 54, "category": "master"}
    )

    result_senior = detect_overtraining_risk(
        ctl=65.0, atl=95.0, tsb=-27.0, profile={"age": 35, "category": "senior"}
    )

    # Both should VETO, but master gets 45min limit vs 60min
    assert result_master["veto"] is True
    assert result_senior["veto"] is True
    assert "45min" in result_master["recommendation"]
    assert "60min" in result_senior["recommendation"]


def test_overtraining_risk_custom_thresholds():
    """Test custom threshold override."""
    custom = {
        "tsb_critical": -20.0,  # More conservative
        "ratio_critical": 1.6,
        "sleep_critical": 6.5,
        "sleep_veto": 6.0,
        "tsb_fatigued": -12.0,
        "tsb_optimal_min": -5.0,
        "ratio_warning": 1.4,
        "ratio_optimal": 1.2,
    }

    result = detect_overtraining_risk(ctl=65.0, atl=90.0, tsb=-21.0, thresholds=custom)

    # Should be critical with custom threshold of -20
    assert result["risk_level"] == "critical"
    assert result["veto"] is True
