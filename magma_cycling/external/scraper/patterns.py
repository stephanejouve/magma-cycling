"""Détection de patterns structurels dans les segments workout."""

import logging

from magma_cycling.external.zwift_models import SegmentType, ZwiftWorkoutSegment

logger = logging.getLogger(__name__)


def _extract_work_segments(
    segments: list[ZwiftWorkoutSegment],
) -> list[ZwiftWorkoutSegment]:
    """Extract main-set work segments, excluding warmup/cooldown/recovery.

    Filters out:
    - First ascending ramp (warmup)
    - Last descending ramp (cooldown)
    - WARMUP, COOLDOWN, FREE_RIDE, RECOVERY segments
    """
    if not segments:
        return []

    filtered = list(segments)

    # Remove first segment if it's a warmup ramp (ascending power)
    if filtered and filtered[0].segment_type in (
        SegmentType.WARMUP,
        SegmentType.RAMP,
    ):
        if filtered[0].power_high and filtered[0].power_low:
            if filtered[0].power_high > filtered[0].power_low:
                filtered = filtered[1:]

    # Remove last segment if it's a cooldown ramp (descending power)
    if filtered and filtered[-1].segment_type in (
        SegmentType.COOLDOWN,
        SegmentType.RAMP,
    ):
        if filtered[-1].power_high and filtered[-1].power_low:
            if filtered[-1].power_high < filtered[-1].power_low:
                filtered = filtered[:-1]

    # Keep only work segments (exclude recovery and free ride)
    work = [
        s
        for s in filtered
        if s.segment_type
        not in (
            SegmentType.WARMUP,
            SegmentType.COOLDOWN,
            SegmentType.FREE_RIDE,
            SegmentType.RECOVERY,
        )
    ]

    # Filter out leading short opener/primer segments (< 2min)
    # Only remove consecutive short segments at the START of the work set
    if len(work) >= 4:
        first_long_idx = next(
            (i for i, s in enumerate(work) if s.duration_seconds >= 120),
            len(work),
        )
        if first_long_idx > 0 and len(work) - first_long_idx >= 3:
            work = work[first_long_idx:]
    return work


def _find_repeating_block(
    powers: list[int],
    min_block_len: int = 3,
    min_repeats: int = 3,
) -> list[int] | None:
    """Find shortest repeating block in a power sequence.

    Args:
        powers: List of power values
        min_block_len: Minimum block length to consider
        min_repeats: Minimum number of consecutive repetitions

    Returns:
        The repeating block if found, None otherwise
    """
    n = len(powers)
    if n < min_block_len * min_repeats:
        return None

    for block_len in range(min_block_len, n // min_repeats + 1):
        block = powers[:block_len]
        repeats = 0
        for i in range(0, n, block_len):
            chunk = powers[i : i + block_len]
            if len(chunk) == block_len and chunk == block:
                repeats += 1
            else:
                break
        if repeats >= min_repeats:
            return block
    return None


def detect_pattern(segments: list[ZwiftWorkoutSegment]) -> str:
    """Detect structural pattern from workout segments.

    Patterns:
    - over-under: alternating above/below threshold (~95-100% FTP)
    - pyramide: ascending then descending power in main set
    - progressif: ascending power through the workout
    - blocs-repetes: identical interval blocks repeated
    - libre: no clear pattern

    Args:
        segments: List of workout segments

    Returns:
        Pattern name string
    """
    if not segments:
        return "libre"

    # Extract all non-warmup/cooldown segments (including recovery)
    all_main = [
        s
        for s in segments
        if s.segment_type
        not in (SegmentType.WARMUP, SegmentType.COOLDOWN, SegmentType.FREE_RIDE)
    ]

    # Also strip leading/trailing ramps used as warmup/cooldown
    if all_main and all_main[0].segment_type == SegmentType.RAMP:
        if (
            all_main[0].power_high
            and all_main[0].power_low
            and all_main[0].power_high > all_main[0].power_low
        ):
            all_main = all_main[1:]
    if all_main and all_main[-1].segment_type == SegmentType.RAMP:
        if (
            all_main[-1].power_high
            and all_main[-1].power_low
            and all_main[-1].power_high < all_main[-1].power_low
        ):
            all_main = all_main[:-1]

    if len(all_main) < 2:
        return "libre"

    # Check for over-under FIRST (before blocs-repetes)
    # Pattern 1: repeated interval+recovery with over/under powers
    repeated = [s for s in all_main if s.repeat_count and s.repeat_count > 1]
    if len(repeated) >= 2:
        interval_segs = [s for s in repeated if s.segment_type == SegmentType.INTERVAL]
        recovery_segs = [
            s for s in repeated if s.segment_type in (SegmentType.RECOVERY, SegmentType.STEADY)
        ]
        if interval_segs and recovery_segs:
            hi = max(s.power_low for s in interval_segs if s.power_low)
            near_threshold = [
                s.power_low for s in recovery_segs if s.power_low and s.power_low >= 80
            ]
            if hi >= 100 and near_threshold and 85 <= min(near_threshold) <= 97:
                return "over-under"

    # Pattern 2: alternating steady segments above/below threshold
    work = _extract_work_segments(segments)
    work_powers = [s.power_low for s in work if s.power_low]
    if len(work_powers) >= 4:
        has_over = any(p >= 100 for p in work_powers)
        has_under = any(85 <= p <= 97 for p in work_powers)
        if has_over and has_under:
            alternating = all(
                (work_powers[i] >= 98) != (work_powers[i + 1] >= 98)
                for i in range(len(work_powers) - 1)
            )
            if alternating:
                return "over-under"

    # Pattern 3: repeating block with over-under within each repetition
    # Handles workouts listed as individual segments without repeat_count
    repeating_block = _find_repeating_block(work_powers)
    if repeating_block:
        has_over = any(p >= 100 for p in repeating_block)
        has_under = any(85 <= p <= 97 for p in repeating_block)
        if has_over and has_under:
            return "over-under"

    # Check for blocs-repetes: repeat_count > 1 or repeating power block
    if repeated or repeating_block:
        return "blocs-repetes"

    # Use work segments (no recovery) for shape analysis
    if len(work_powers) >= 3:
        # Check for pyramid: ascending then descending power
        mid = len(work_powers) // 2
        ascending = all(work_powers[i] <= work_powers[i + 1] for i in range(mid))
        descending = all(
            work_powers[i] >= work_powers[i + 1] for i in range(mid, len(work_powers) - 1)
        )
        if ascending and descending and work_powers[0] < work_powers[mid]:
            return "pyramide"

        # Check for progressive: strictly ascending power
        strictly_ascending = all(
            work_powers[i] < work_powers[i + 1] for i in range(len(work_powers) - 1)
        )
        if strictly_ascending:
            return "progressif"

    return "libre"
