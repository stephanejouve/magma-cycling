"""Advanced metrics utilities for training analysis.

This module provides advanced analytical functions for cycling training metrics,
including trend analysis, peak detection, recovery recommendations, and overtraining
risk assessment.

Functions:
    calculate_ramp_rate: Calculate CTL progression rate (points/week)
    get_weekly_metrics_trend: Analyze weekly metric trends (rising/stable/declining)
    detect_training_peaks: Detect significant training load peaks
    get_recovery_recommendation: Generate recovery recommendations based on metrics
    format_metrics_comparison: Format comparison between two time periods
    detect_overtraining_risk: Detect overtraining risk for master athletes (CRITICAL).
"""

from statistics import mean, stdev
from typing import Any, cast


def calculate_ramp_rate(ctl_current: float, ctl_previous: float, days: int = 7) -> float:
    """Calculate CTL (Chronic Training Load) progression rate.

    Calculates the rate of fitness progression in CTL points per week.
    Useful for monitoring training load increases and preventing overtraining.

    Args:
        ctl_current: Current CTL value
        ctl_previous: Previous CTL value (from 'days' ago)
        days: Number of days between measurements (default: 7 for weekly)

    Returns:
        float: CTL change rate in points per week. Positive = increasing fitness,
               negative = decreasing fitness.

    Examples:
        >>> calculate_ramp_rate(65.0, 60.0, days=7)
        5.0
        >>> calculate_ramp_rate(65.0, 60.0, days=14)
        2.5
        >>> calculate_ramp_rate(60.0, 65.0, days=7)
        -5.0

    Notes:
        - Recommended max ramp rate for master athletes: 5-7 points/week
        - Rates >10 points/week indicate high injury/overtraining risk
        - Negative rates indicate detraining or recovery phase.
    """
    if days <= 0:
        raise ValueError("days must be positive")

    delta = ctl_current - ctl_previous
    weeks = days / 7.0
    return delta / weeks if weeks > 0 else delta


def get_weekly_metrics_trend(
    weekly_data: list[dict[str, float]], metric: str = "ctl"
) -> dict[str, Any]:
    """Analyze trend in weekly metrics.

    Determines if a metric is rising, stable, or declining over multiple weeks
    using statistical analysis.

    Args:
        weekly_data: List of dicts with weekly metrics. Each dict should contain
                     the metric key (e.g., 'ctl', 'atl', 'tsb')
        metric: Metric name to analyze (default: 'ctl')

    Returns:
        Dict with keys:
            - trend: 'rising' | 'stable' | 'declining'
            - slope: Average change per week
            - volatility: Standard deviation of changes
            - weeks_analyzed: Number of weeks in analysis

    Examples:
        >>> data = [
        ...     {'ctl': 60.0, 'week': 1},
        ...     {'ctl': 62.0, 'week': 2},
        ...     {'ctl': 65.0, 'week': 3},
        ...     {'ctl': 67.0, 'week': 4}
        ... ]
        >>> result = get_weekly_metrics_trend(data, 'ctl')
        >>> result['trend']
        'rising'
        >>> result['slope'] > 0
        True

    Notes:
        - 'rising': slope > 1.0 points/week
        - 'stable': slope between -1.0 and +1.0 points/week
        - 'declining': slope < -1.0 points/week.
    """
    if not weekly_data:
        return {"trend": "unknown", "slope": 0.0, "volatility": 0.0, "weeks_analyzed": 0}

    if len(weekly_data) < 2:
        return {
            "trend": "insufficient_data",
            "slope": 0.0,
            "volatility": 0.0,
            "weeks_analyzed": len(weekly_data),
        }

    # Extract metric values
    values = [week.get(metric, 0.0) for week in weekly_data]

    # Calculate week-to-week changes
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]

    # Calculate statistics
    avg_change = mean(changes)
    volatility = stdev(changes) if len(changes) > 1 else 0.0

    # Determine trend
    if avg_change > 1.0:
        trend = "rising"
    elif avg_change < -1.0:
        trend = "declining"
    else:
        trend = "stable"

    return {
        "trend": trend,
        "slope": round(avg_change, 2),
        "volatility": round(volatility, 2),
        "weeks_analyzed": len(weekly_data),
    }


def detect_training_peaks(
    ctl_history: list[float], threshold_percent: float = 10.0
) -> list[dict[str, Any]]:
    """Detect significant training load peaks in CTL history.

    Identifies periods where CTL increases significantly above recent baseline,
    which may indicate high training stress periods.

    Args:
        ctl_history: List of CTL values in chronological order
        threshold_percent: Minimum % increase to qualify as peak (default: 10.0)

    Returns:
        List of dicts, each representing a peak with keys:
            - index: Position in ctl_history
            - value: CTL value at peak
            - increase_percent: % increase from previous period
            - baseline: Recent baseline CTL before peak

    Examples:
        >>> history = [50, 52, 51, 58, 60, 55, 53]
        >>> peaks = detect_training_peaks(history, threshold_percent=10.0)
        >>> len(peaks) >= 1
        True
        >>> peaks[0]['value'] >= 58
        True

    Notes:
        - Uses 3-week rolling average as baseline
        - Master athletes: Consider threshold_percent=8-10% (more sensitive)
        - Senior athletes: Can use threshold_percent=12-15%.
    """
    if len(ctl_history) < 4:
        return []

    peaks = []

    for i in range(3, len(ctl_history)):
        # Calculate 3-week baseline (excluding current)
        baseline = mean(ctl_history[i - 3 : i])
        current = ctl_history[i]

        # Calculate increase percentage
        increase_pct = ((current - baseline) / baseline * 100) if baseline > 0 else 0

        # Detect peak if above threshold
        if increase_pct >= threshold_percent:
            peaks.append(
                {
                    "index": i,
                    "value": round(current, 1),
                    "increase_percent": round(increase_pct, 1),
                    "baseline": round(baseline, 1),
                }
            )

    return peaks


def get_recovery_recommendation(
    tsb: float, atl_ctl_ratio: float, profile: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Generate recovery recommendation based on training metrics.

    Provides actionable recovery advice based on TSB, fatigue ratio, and
    athlete profile (age, recovery capacity).

    Args:
        tsb: Training Stress Balance (Form)
        atl_ctl_ratio: Ratio of ATL/CTL (Fatigue/Fitness)
        profile: Optional athlete profile dict with keys:
                 - age: int
                 - recovery_capacity: 'normal' | 'good' | 'exceptional'
                 - category: 'junior' | 'senior' | 'master'

    Returns:
        Dict with keys:
            - recommendation: Main recovery advice
            - intensity_limit: Max % FTP recommended
            - duration_limit: Max session duration (minutes)
            - rest_days: Suggested rest days
            - priority: 'low' | 'medium' | 'high' | 'critical'

    Examples:
        >>> rec = get_recovery_recommendation(
        ...     tsb=-18.0,
        ...     atl_ctl_ratio=1.45,
        ...     profile={'age': 54, 'category': 'master'}
        ... )
        >>> rec['priority']
        'high'
        >>> rec['intensity_limit'] <= 75
        True

    Notes:
        - TSB <-20 → Critical recovery needed
        - ATL/CTL >1.5 → High fatigue
        - Master athletes: More conservative limits.
    """
    # Default profile
    if profile is None:
        profile = {"age": 35, "recovery_capacity": "normal", "category": "senior"}

    is_master = profile.get("category") == "master" or profile.get("age", 35) >= 50
    recovery_capacity = profile.get("recovery_capacity", "normal")

    # Determine priority level
    if tsb < -20 or atl_ctl_ratio > 1.6:
        priority = "critical"
    elif tsb < -15 or atl_ctl_ratio > 1.4:
        priority = "high"
    elif tsb < -10 or atl_ctl_ratio > 1.2:
        priority = "medium"
    else:
        priority = "low"

    # Base recommendations
    recommendations = {
        "critical": {
            "recommendation": "Immediate rest or Z1 only. Cancel all intensity.",
            "intensity_limit": 55,  # Z1 only
            "duration_limit": 45,
            "rest_days": 2 if is_master else 1,
        },
        "high": {
            "recommendation": "Cancel >85% FTP. Z2 endurance only, max 60min.",
            "intensity_limit": 75,  # Z2 max
            "duration_limit": 60,
            "rest_days": 1,
        },
        "medium": {
            "recommendation": "Reduce intensity -10% OR duration -15%. Monitor closely.",
            "intensity_limit": 90,
            "duration_limit": 90,
            "rest_days": 0,
        },
        "low": {
            "recommendation": "Normal training. Follow planned sessions.",
            "intensity_limit": 100,
            "duration_limit": 120,
            "rest_days": 0,
        },
    }

    result = recommendations[priority].copy()
    result["priority"] = priority

    # Adjust for master athletes
    if is_master and priority in ["high", "critical"]:
        result["duration_limit"] = min(cast(int, result["duration_limit"]), 45)
        result["rest_days"] = cast(int, result["rest_days"]) + 1

    # Adjust for exceptional recovery
    if recovery_capacity == "exceptional" and priority == "medium":
        result["intensity_limit"] = min(95, cast(int, result["intensity_limit"]))

    return result


def format_metrics_comparison(
    period1: dict[str, float], period2: dict[str, float], labels: dict[str, str] | None = None
) -> str:
    """Format comparison between two time periods.

    Creates a human-readable comparison of metrics between two periods,
    showing changes and trends.

    Args:
        period1: First period metrics (e.g., {'ctl': 60, 'atl': 55, 'tsb': 5})
        period2: Second period metrics (same keys as period1)
        labels: Optional labels for periods (e.g., {'period1': 'Last week', 'period2': 'This week'})

    Returns:
        Formatted string showing metric comparisons with change indicators

    Examples:
        >>> p1 = {'ctl': 60.0, 'atl': 55.0, 'tsb': 5.0}
        >>> p2 = {'ctl': 65.0, 'atl': 58.0, 'tsb': 7.0}
        >>> result = format_metrics_comparison(p1, p2)
        >>> 'CTL' in result and '↑' in result
        True

    Notes:
        - ↑ indicates increase
        - ↓ indicates decrease
        - → indicates no change (<0.5 difference).
    """
    if labels is None:
        labels = {"period1": "Period 1", "period2": "Period 2"}

    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(
        f"Metrics Comparison: {labels.get('period1', 'Period 1')} → {labels.get('period2', 'Period 2')}"
    )
    lines.append(f"{'='*60}\n")

    # Common metrics to compare
    metrics = ["ctl", "atl", "tsb"]

    for metric in metrics:
        if metric in period1 and metric in period2:
            val1 = period1[metric]
            val2 = period2[metric]
            delta = val2 - val1

            # Determine direction
            if abs(delta) < 0.5:
                direction = "→"
                change_desc = "stable"
            elif delta > 0:
                direction = "↑"
                change_desc = f"+{delta:.1f}"
            else:
                direction = "↓"
                change_desc = f"{delta:.1f}"

            metric_name = metric.upper()
            lines.append(f"{metric_name:6} {direction} {val1:6.1f} → {val2:6.1f}  ({change_desc})")

    lines.append(f"{'='*60}\n")

    return "\n".join(lines)


def detect_overtraining_risk(
    ctl: float,
    atl: float,
    tsb: float,
    sleep_hours: float | None = None,
    profile: dict[str, Any] | None = None,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Detect overtraining risk for master athletes (CRITICAL FUNCTION).

    Combines TSB, ATL/CTL ratio, sleep quality, and athlete profile to assess
    overtraining risk and provide VETO recommendations for safety.

    This is a CRITICAL safety function for master athletes (50+ years) who are
    more susceptible to overtraining and require longer recovery.

    Args:
        ctl: Current Chronic Training Load (Fitness)
        atl: Current Acute Training Load (Fatigue)
        tsb: Current Training Stress Balance (Form)
        sleep_hours: Sleep duration from previous night (optional but recommended)
        profile: Athlete profile dict with keys:
                 - age: int
                 - category: 'junior' | 'senior' | 'master'
                 - sleep_dependent: bool
        thresholds: Optional custom thresholds dict:
                    - tsb_critical: float (default: -25)
                    - tsb_fatigued: float (default: -15)
                    - ratio_critical: float (default: 1.8)
                    - ratio_warning: float (default: 1.3)
                    - sleep_critical: float (default: 6.0)
                    - ramp_critical: float (default: 10.0)

    Returns:
        Dict with keys:
            - risk_level: 'critical' | 'high' | 'medium' | 'low'
            - veto: bool - If True, cancel ALL intensity training
            - recommendation: Specific action to take
            - factors: List of contributing risk factors
            - sleep_veto: bool - Specific sleep-based veto

    Examples:
        >>> # Critical overtraining risk
        >>> result = detect_overtraining_risk(
        ...     ctl=65.0, atl=120.0, tsb=-27.0,
        ...     sleep_hours=5.5,
        ...     profile={'age': 54, 'category': 'master', 'sleep_dependent': True}
        ... )
        >>> result['risk_level']
        'critical'
        >>> result['veto']
        True

        >>> # Low risk
        >>> result = detect_overtraining_risk(
        ...     ctl=65.0, atl=60.0, tsb=5.0,
        ...     sleep_hours=7.5,
        ...     profile={'age': 54, 'category': 'master'}
        ... )
        >>> result['risk_level']
        'low'
        >>> result['veto']
        False

    Notes:
        CRITICAL THRESHOLDS (Master Athlete):
        - TSB <-25 + sleep <6h → VETO (rest or Z1 max 45min)
        - ATL >CTL×1.8 → VETO
        - Sleep <5.5h → HIGH risk (cancel >85% FTP)
        - Sleep <6h + TSB <-15 → CRITICAL

        VETO means: Cancel ALL intensity, rest day or Z1 only (max 45min).
    """
    # Default thresholds (master athlete calibrated)
    if thresholds is None:
        thresholds = {
            "tsb_critical": -25.0,
            "tsb_fatigued": -15.0,
            "tsb_optimal_min": -5.0,
            "ratio_critical": 1.8,
            "ratio_warning": 1.5,
            "ratio_optimal": 1.3,
            "sleep_critical": 6.0,
            "sleep_veto": 5.5,
        }

    # Default profile
    if profile is None:
        profile = {"age": 35, "category": "senior", "sleep_dependent": False}

    is_master = profile.get("category") == "master" or profile.get("age", 35) >= 50
    sleep_dependent = profile.get("sleep_dependent", False)

    # Calculate ATL/CTL ratio
    atl_ctl_ratio = atl / ctl if ctl > 0 else 0

    # Initialize result
    factors = []
    veto = False
    sleep_veto = False
    risk_level = "low"

    # CRITICAL CHECKS (VETO triggers)

    # 1. TSB Critical
    if tsb < thresholds["tsb_critical"]:
        factors.append(f"TSB critically low ({tsb:.1f} < {thresholds['tsb_critical']})")
        risk_level = "critical"
        veto = True

    # 2. ATL/CTL Ratio Critical
    if atl_ctl_ratio > thresholds["ratio_critical"]:
        factors.append(
            f"ATL/CTL ratio critical ({atl_ctl_ratio:.2f} > {thresholds['ratio_critical']})"
        )
        risk_level = "critical"
        veto = True

    # 3. Sleep Veto (if data available)
    if sleep_hours is not None:
        if sleep_hours < thresholds["sleep_veto"]:
            factors.append(
                f"Sleep critically low ({sleep_hours:.1f}h < {thresholds['sleep_veto']}h)"
            )
            risk_level = "high" if risk_level == "low" else "critical"
            sleep_veto = True
            veto = True

        # Combined TSB + Sleep Critical
        if sleep_hours < thresholds["sleep_critical"] and tsb < thresholds["tsb_fatigued"]:
            factors.append(f"Combined: Low sleep ({sleep_hours:.1f}h) + Fatigued (TSB {tsb:.1f})")
            risk_level = "critical"
            veto = True

    # HIGH RISK CHECKS

    if not veto:
        # TSB Fatigued
        if tsb < -20:
            factors.append(f"TSB very low ({tsb:.1f})")
            risk_level = "high"

        # Ratio Warning
        if atl_ctl_ratio > thresholds["ratio_warning"]:
            factors.append(f"ATL/CTL ratio elevated ({atl_ctl_ratio:.2f})")
            risk_level = "high" if risk_level == "low" else risk_level

        # Sleep Warning (for sleep-dependent athletes)
        if sleep_hours is not None and sleep_dependent:
            if sleep_hours < 7.0:
                factors.append(f"Sleep below optimal ({sleep_hours:.1f}h < 7h)")
                risk_level = "medium" if risk_level == "low" else risk_level

    # MEDIUM RISK CHECKS

    if risk_level == "low":
        if thresholds["tsb_fatigued"] <= tsb < thresholds["tsb_optimal_min"]:
            factors.append(f"TSB fatigued range ({tsb:.1f})")
            risk_level = "medium"

        if thresholds["ratio_optimal"] < atl_ctl_ratio <= thresholds["ratio_warning"]:
            factors.append(f"ATL/CTL ratio moderate ({atl_ctl_ratio:.2f})")
            risk_level = "medium" if risk_level == "low" else risk_level

    # Generate recommendations
    if veto:
        if is_master:
            recommendation = "VETO: Immediate rest required. Cancel ALL training OR Z1 only (max 45min, <55% FTP)."
        else:
            recommendation = "VETO: Rest day recommended or very light Z1 only (max 60min)."
    elif risk_level == "high":
        recommendation = (
            "Cancel all sessions >85% FTP. Z2 endurance only, max 60min. Monitor sleep closely."
        )
    elif risk_level == "medium":
        recommendation = "Reduce intensity -10% OR duration -15%. Prioritize recovery quality."
    else:
        recommendation = "Normal training. Follow planned sessions. Monitor recovery markers."

    return {
        "risk_level": risk_level,
        "veto": veto,
        "sleep_veto": sleep_veto,
        "recommendation": recommendation,
        "factors": factors,
        "atl_ctl_ratio": round(atl_ctl_ratio, 2),
        "is_master_athlete": is_master,
    }
