"""Search logic, scoring, and category mapping for Zwift workouts."""

import logging
from datetime import datetime, timedelta

from magma_cycling.external.zwift_models import (
    WorkoutSearchCriteria,
    ZwiftCategory,
    ZwiftWorkout,
)

logger = logging.getLogger(__name__)


def get_categories_for_session_type(session_type: str) -> list[ZwiftCategory]:
    """Map session type to relevant Zwift categories.

    Args:
        session_type: 3-letter session type code.

    Returns:
        List of relevant ZwiftCategory values.
    """
    # Reverse mapping from session types to Zwift categories
    mapping = {
        "END": [ZwiftCategory.ENDURANCE, ZwiftCategory.TEMPO],
        "INT": [ZwiftCategory.INTERVALS, ZwiftCategory.VO2MAX],
        "FTP": [ZwiftCategory.FTP, ZwiftCategory.THRESHOLD],
        "SPR": [ZwiftCategory.SPRINT],
        "CLM": [ZwiftCategory.CLIMBING],
        "REC": [ZwiftCategory.RECOVERY],
        "MIX": [ZwiftCategory.MIXED],
    }

    # Default to mixed if not found
    return mapping.get(session_type, [ZwiftCategory.MIXED])


def calculate_match_score(
    workout: ZwiftWorkout,
    criteria: WorkoutSearchCriteria,
) -> float:
    """Calculate match quality score (0-100) for a workout.

    Scoring factors:
    - TSS accuracy (40 points): Closer to target = higher score
    - Type match (30 points): Exact category match = full points
    - Duration fit (20 points): Within constraints = full points
    - Novelty (10 points): Less used = higher score

    Args:
        workout: Workout to score.
        criteria: Search criteria.

    Returns:
        Score from 0.0 to 100.0.
    """
    score = 0.0

    # TSS accuracy (40 points)
    tss_diff = abs(workout.tss - criteria.tss_target)
    tss_tolerance = criteria.tss_target * criteria.tss_tolerance / 100
    if tss_diff == 0:
        score += 40.0
    elif tss_diff <= tss_tolerance:
        # Linear decay within tolerance
        score += 40.0 * (1.0 - tss_diff / tss_tolerance)

    # Type match (30 points)
    if ZwiftCategory.to_session_type(workout.category) == criteria.session_type:
        score += 30.0

    # Duration fit (20 points)
    duration_ok = True
    if criteria.duration_min and workout.duration_minutes < criteria.duration_min:
        duration_ok = False
    if criteria.duration_max and workout.duration_minutes > criteria.duration_max:
        duration_ok = False
    if duration_ok:
        score += 20.0

    # Novelty bonus (10 points) - less used = higher score
    # Max usage_count of 10 gives 0 points, 0 gives 10 points
    novelty = max(0, 10 - workout.usage_count)
    score += novelty

    return min(100.0, score)


def is_recently_used(workout: ZwiftWorkout, window_days: int) -> bool:
    """Check if workout was used within the diversity window.

    Args:
        workout: Workout to check.
        window_days: Diversity window in days.

    Returns:
        True if used within window, False otherwise.
    """
    if not workout.last_used_date:
        return False

    try:
        last_used = datetime.fromisoformat(workout.last_used_date)
        cutoff = datetime.now() - timedelta(days=window_days)
        return last_used > cutoff
    except ValueError:
        logger.warning(f"Invalid last_used_date format: {workout.last_used_date}")
        return False
