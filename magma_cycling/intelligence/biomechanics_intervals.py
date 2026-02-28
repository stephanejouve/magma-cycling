"""
Biomechanics Integration with Intervals.icu API.

Extracts biomechanical metrics from Intervals.icu activities and provides
cadence recommendations based on Grappe research.

Metadata:
    Created: 2026-01-15
    Author: Claude Code
    Category: INTELLIGENCE
    Status: Development
    Priority: P1
    Version: 1.0.0
    Sprint: R9 (Consolidation - Grappe Integration)
"""

from datetime import datetime, timedelta
from typing import Any

from magma_cycling.intelligence.biomechanics import calculer_cadence_optimale


def extract_biomechanical_metrics(
    activities: list[dict[str, Any]],
) -> dict[str, float | int]:
    """
    Extract average biomechanical metrics from Intervals.icu activities.

    Calculates weighted averages of cadence, duration, and intensity from
    recent activities to feed into biomechanical analysis.

    Args:
        activities: List of activity dicts from Intervals.icu API
                   (from IntervalsClient.get_activities())

    Returns:
        Dict with keys:
            - avg_cadence: Weighted average cadence (rpm)
            - avg_duration_min: Average session duration (minutes)
            - avg_intensity: Weighted average intensity (% FTP, 0.0-1.0)
            - activity_count: Number of activities analyzed

    Notes:
        - Filters out activities with zero cadence (e.g., rest days)
        - Weights averages by TSS (training load)
        - Returns zeros if no valid activities found

    Example:
        >>> from magma_cycling.api.intervals_client import IntervalsClient
        >>> client = IntervalsClient("iXXXXXX", api_key)
        >>> activities = client.get_activities(oldest="2026-01-01", newest="2026-01-14")
        >>> metrics = extract_biomechanical_metrics(activities)
        >>> print(f"Avg cadence: {metrics['avg_cadence']} rpm")
    """
    if not activities:
        return {
            "avg_cadence": 0,
            "avg_duration_min": 0,
            "avg_intensity": 0.0,
            "activity_count": 0,
        }

    # Filter activities with valid cadence data (exclude rest days, non-bike activities)
    valid_activities = [
        a
        for a in activities
        if a.get("average_cadence", 0) > 0 and a.get("icu_training_load", 0) > 0
    ]

    if not valid_activities:
        return {
            "avg_cadence": 0,
            "avg_duration_min": 0,
            "avg_intensity": 0.0,
            "activity_count": 0,
        }

    # Calculate weighted averages by TSS
    total_tss = sum(a.get("icu_training_load", 0) for a in valid_activities)

    weighted_cadence = sum(
        a.get("average_cadence", 0) * a.get("icu_training_load", 0) for a in valid_activities
    )
    weighted_intensity = sum(
        (a.get("icu_intensity", 0) / 100.0) * a.get("icu_training_load", 0)
        for a in valid_activities
    )

    avg_cadence = round(weighted_cadence / total_tss) if total_tss > 0 else 0
    avg_intensity = round(weighted_intensity / total_tss, 2) if total_tss > 0 else 0.0

    # Average duration (not weighted, as longer sessions don't necessarily mean more important)
    avg_duration_min = round(
        sum(a.get("moving_time", 0) for a in valid_activities) / len(valid_activities) / 60
    )

    return {
        "avg_cadence": avg_cadence,
        "avg_duration_min": avg_duration_min,
        "avg_intensity": avg_intensity,
        "activity_count": len(valid_activities),
    }


def get_cadence_recommendation_from_activities(
    activities: list[dict[str, Any]],
    next_cycle_zone_ftp: float,
    next_cycle_duration_min: int,
    profil_fibres: str = "mixte",
) -> dict[str, Any]:
    """
    Get cadence recommendation for next cycle based on recent activities.

    Analyzes recent activity cadence patterns and compares against optimal
    cadence for the upcoming training cycle using Grappe research.

    Args:
        activities: List of activity dicts from Intervals.icu API
        next_cycle_zone_ftp: Planned FTP zone for next cycle (0.5-1.5)
        next_cycle_duration_min: Planned session duration for next cycle (minutes)
        profil_fibres: Athlete fiber profile ("explosif" | "mixte" | "endurant")

    Returns:
        Dict with keys:
            - cadence_optimale: Optimal cadence for next cycle (rpm)
            - cadence_actuelle: Recent average cadence (rpm)
            - ecart_rpm: Difference between optimal and actual (rpm)
            - correction_necessaire: Whether adjustment needed (bool)
            - recent_metrics: Raw metrics from extract_biomechanical_metrics()
            - recommendation: Detailed recommendation dict from calculer_cadence_optimale()

    Raises:
        ValueError: If next_cycle_zone_ftp out of range or invalid profil_fibres

    Example:
        >>> activities = client.get_activities(oldest="2026-01-01", newest="2026-01-14")
        >>> recommendation = get_cadence_recommendation_from_activities(
        ...     activities=activities,
        ...     next_cycle_zone_ftp=0.90,  # Sweet-Spot
        ...     next_cycle_duration_min=60,
        ...     profil_fibres="mixte"
        ... )
        >>> print(f"Target cadence: {recommendation['cadence_optimale']} rpm")
        >>> if recommendation['correction_necessaire']:
        ...     print(f"Adjust by {recommendation['ecart_rpm']} rpm")
    """
    # Extract recent metrics
    recent_metrics = extract_biomechanical_metrics(activities)

    # Calculate optimal cadence for next cycle
    cadence_opt = calculer_cadence_optimale(
        zone_ftp=next_cycle_zone_ftp,
        duree_minutes=next_cycle_duration_min,
        profil_fibres=profil_fibres,
    )

    cadence_optimale = cadence_opt["cadence_cible"]
    cadence_actuelle = recent_metrics["avg_cadence"]

    ecart_rpm = cadence_optimale - cadence_actuelle

    # Correction needed if deviation > 5 rpm (outside optimal range)
    correction_necessaire = abs(ecart_rpm) > 5

    return {
        "cadence_optimale": cadence_optimale,
        "cadence_actuelle": cadence_actuelle,
        "ecart_rpm": ecart_rpm,
        "correction_necessaire": correction_necessaire,
        "recent_metrics": recent_metrics,
        "recommendation": cadence_opt,
    }


def get_activities_last_n_weeks(
    client,
    n_weeks: int = 4,
) -> list[dict[str, Any]]:
    """
    Fetch activities from last N weeks using Intervals.icu client.

    Convenience helper to retrieve recent activities for biomechanical analysis.

    Args:
        client: IntervalsClient instance
        n_weeks: Number of weeks to look back (default: 4)

    Returns:
        List of activity dicts from Intervals.icu API

    Example:
        >>> from magma_cycling.api.intervals_client import IntervalsClient
        >>> client = IntervalsClient("iXXXXXX", api_key)
        >>> activities = get_activities_last_n_weeks(client, n_weeks=6)
        >>> print(f"Found {len(activities)} activities")
    """
    oldest = (datetime.now() - timedelta(weeks=n_weeks)).strftime("%Y-%m-%d")
    newest = datetime.now().strftime("%Y-%m-%d")

    return client.get_activities(oldest=oldest, newest=newest)
