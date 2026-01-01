"""
Training Metrics Utilities.

Centralized utilities for CTL/ATL/TSB metrics extraction, calculation,
and formatting. Eliminates duplicate code patterns across the codebase.

Examples:
    Extract wellness metrics safely::

        wellness = api.get_wellness(oldest="2025-12-01", newest="2025-12-01")
        metrics = get_metrics_safely(wellness, index=0)
        print(f"CTL: {metrics['ctl']}, ATL: {metrics['atl']}, TSB: {metrics['tsb']}")

    Format metrics for display::

        display = format_metrics_display(metrics)
        print(display)  # "CTL: 45.6 | ATL: 37.7 | TSB: +7.9"

    Check if metrics are complete::

        if is_metrics_complete(metrics):
            print("All metrics available")

Author: Claude Code
Created: 2026-01-01
"""

from typing import Dict, List, Optional, Any


def extract_wellness_metrics(
    wellness_data: Optional[Dict[str, Any]]
) -> Dict[str, float]:
    """
    Extract CTL/ATL/TSB metrics from wellness data with proper None handling.

    This function unifies the three common patterns found in the codebase:
    - Pattern A: `ctl = wellness.get('ctl', 0)`
    - Pattern B: `ctl = wellness.get('ctl')` then check None
    - Pattern C: Wellness data from list with fallback

    Args:
        wellness_data: Wellness dictionary from Intervals.icu API (or None)

    Returns:
        Dict with 'ctl', 'atl', 'tsb' keys (float values, 0.0 if missing)

    Examples:
        >>> wellness = {'ctl': 45.6, 'atl': 37.7, 'tsb': 7.9}
        >>> extract_wellness_metrics(wellness)
        {'ctl': 45.6, 'atl': 37.7, 'tsb': 7.9}

        >>> extract_wellness_metrics(None)
        {'ctl': 0.0, 'atl': 0.0, 'tsb': 0.0}

        >>> wellness = {'ctl': None, 'atl': 35.0}
        >>> extract_wellness_metrics(wellness)
        {'ctl': 0.0, 'atl': 35.0, 'tsb': -35.0}
    """
    if not wellness_data:
        return {'ctl': 0.0, 'atl': 0.0, 'tsb': 0.0}

    # Extract with None handling (Pattern B)
    ctl = wellness_data.get('ctl')
    atl = wellness_data.get('atl')
    tsb = wellness_data.get('tsb')

    # Convert None to 0.0
    ctl = ctl if ctl is not None else 0.0
    atl = atl if atl is not None else 0.0

    # Calculate TSB if not provided (TSB = CTL - ATL)
    if tsb is None:
        tsb = ctl - atl
    else:
        tsb = float(tsb)

    return {
        'ctl': float(ctl),
        'atl': float(atl),
        'tsb': float(tsb),
    }


def calculate_tsb(ctl: float, atl: float) -> float:
    """
    Calculate Training Stress Balance from CTL and ATL.

    TSB = CTL - ATL

    Args:
        ctl: Chronic Training Load (fitness)
        atl: Acute Training Load (fatigue)

    Returns:
        float: Training Stress Balance (form)

    Examples:
        >>> calculate_tsb(45.6, 37.7)
        7.9
        >>> calculate_tsb(40.0, 50.0)
        -10.0
    """
    return ctl - atl


def format_metrics_display(metrics: Dict[str, float]) -> str:
    """
    Format CTL/ATL/TSB metrics for display.

    Formats metrics as: "CTL: 45.6 | ATL: 37.7 | TSB: +7.9"
    TSB includes + sign for positive values.

    Args:
        metrics: Dictionary with 'ctl', 'atl', 'tsb' keys

    Returns:
        str: Formatted metrics string

    Examples:
        >>> metrics = {'ctl': 45.6, 'atl': 37.7, 'tsb': 7.9}
        >>> format_metrics_display(metrics)
        'CTL: 45.6 | ATL: 37.7 | TSB: +7.9'

        >>> metrics = {'ctl': 40.0, 'atl': 50.0, 'tsb': -10.0}
        >>> format_metrics_display(metrics)
        'CTL: 40.0 | ATL: 50.0 | TSB: -10.0'

        >>> metrics = {'ctl': 0, 'atl': 0, 'tsb': 0}
        >>> format_metrics_display(metrics)
        'CTL: 0.0 | ATL: 0.0 | TSB: +0.0'
    """
    ctl = metrics.get('ctl', 0)
    atl = metrics.get('atl', 0)
    tsb = metrics.get('tsb', 0)

    # Add + sign for positive TSB
    tsb_sign = '+' if tsb >= 0 else ''

    return f"CTL: {ctl:.1f} | ATL: {atl:.1f} | TSB: {tsb_sign}{tsb:.1f}"


def is_metrics_complete(metrics: Dict[str, Any]) -> bool:
    """
    Check if all CTL/ATL/TSB metrics are present and valid.

    A metric is considered complete if all three values (CTL, ATL, TSB)
    are present, not None, and can be converted to float.

    Args:
        metrics: Dictionary potentially containing 'ctl', 'atl', 'tsb'

    Returns:
        bool: True if all metrics are valid

    Examples:
        >>> metrics = {'ctl': 45.6, 'atl': 37.7, 'tsb': 7.9}
        >>> is_metrics_complete(metrics)
        True

        >>> metrics = {'ctl': None, 'atl': 37.7}
        >>> is_metrics_complete(metrics)
        False

        >>> metrics = {}
        >>> is_metrics_complete(metrics)
        False

        >>> metrics = {'ctl': 0, 'atl': 0, 'tsb': 0}
        >>> is_metrics_complete(metrics)
        True
    """
    if not metrics:
        return False

    required_keys = ['ctl', 'atl', 'tsb']

    for key in required_keys:
        value = metrics.get(key)
        if value is None:
            return False
        try:
            float(value)
        except (TypeError, ValueError):
            return False

    return True


def calculate_metrics_change(
    metrics_start: Dict[str, float], metrics_end: Dict[str, float]
) -> Dict[str, Optional[float]]:
    """
    Calculate change in metrics between two timepoints.

    Computes delta for CTL, ATL, and TSB. Returns None for any metric
    where either start or end value is None.

    Args:
        metrics_start: Metrics at start of period
        metrics_end: Metrics at end of period

    Returns:
        Dict with 'ctl_change', 'atl_change', 'tsb_change' keys
        (float values or None if data incomplete)

    Examples:
        >>> start = {'ctl': 40.0, 'atl': 35.0, 'tsb': 5.0}
        >>> end = {'ctl': 45.6, 'atl': 37.7, 'tsb': 7.9}
        >>> calculate_metrics_change(start, end)
        {'ctl_change': 5.6, 'atl_change': 2.7, 'tsb_change': 2.9}

        >>> start = {'ctl': None, 'atl': 35.0, 'tsb': None}
        >>> end = {'ctl': 45.6, 'atl': 37.7, 'tsb': 7.9}
        >>> calculate_metrics_change(start, end)
        {'ctl_change': None, 'atl_change': 2.7, 'tsb_change': None}
    """
    # Calculate CTL change
    ctl_start = metrics_start.get('ctl')
    ctl_end = metrics_end.get('ctl')
    ctl_change = (
        (ctl_end - ctl_start)
        if (ctl_start is not None and ctl_end is not None)
        else None
    )

    # Calculate ATL change
    atl_start = metrics_start.get('atl')
    atl_end = metrics_end.get('atl')
    atl_change = (
        (atl_end - atl_start)
        if (atl_start is not None and atl_end is not None)
        else None
    )

    # Calculate TSB change
    tsb_start = metrics_start.get('tsb')
    tsb_end = metrics_end.get('tsb')
    tsb_change = (
        (tsb_end - tsb_start)
        if (tsb_start is not None and tsb_end is not None)
        else None
    )

    return {
        'ctl_change': ctl_change,
        'atl_change': atl_change,
        'tsb_change': tsb_change,
    }


def get_metrics_safely(
    wellness_list: Optional[List[Dict[str, Any]]], index: int = 0
) -> Dict[str, float]:
    """
    Safely extract metrics from wellness list with fallback.

    This function handles the common pattern of getting wellness data from
    a list returned by API, with proper bounds checking and None handling.

    Args:
        wellness_list: List of wellness data from API (or None)
        index: Index to extract (default: 0 for most recent)

    Returns:
        Dict with 'ctl', 'atl', 'tsb' keys (0.0 if unavailable)

    Examples:
        >>> wellness_list = [
        ...     {'id': '2025-12-01', 'ctl': 45.6, 'atl': 37.7},
        ...     {'id': '2025-11-30', 'ctl': 44.0, 'atl': 36.0}
        ... ]
        >>> get_metrics_safely(wellness_list, index=0)
        {'ctl': 45.6, 'atl': 37.7, 'tsb': 7.9}

        >>> get_metrics_safely(None)
        {'ctl': 0.0, 'atl': 0.0, 'tsb': 0.0}

        >>> get_metrics_safely([], index=0)
        {'ctl': 0.0, 'atl': 0.0, 'tsb': 0.0}

        >>> wellness_list = [{'id': '2025-12-01'}]
        >>> get_metrics_safely(wellness_list, index=5)
        {'ctl': 0.0, 'atl': 0.0, 'tsb': 0.0}
    """
    # Handle None or empty list
    if not wellness_list:
        return {'ctl': 0.0, 'atl': 0.0, 'tsb': 0.0}

    # Handle out of bounds index
    if index < 0 or index >= len(wellness_list):
        return {'ctl': 0.0, 'atl': 0.0, 'tsb': 0.0}

    # Extract metrics from the specified index
    wellness_data = wellness_list[index]
    return extract_wellness_metrics(wellness_data)
