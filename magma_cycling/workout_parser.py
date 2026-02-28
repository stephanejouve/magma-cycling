"""Parser for workout text descriptions into structured interval blocks.

Converts the human-readable workout format used in {week_id}_workouts.txt files
into structured data suitable for applying custom intervals to Intervals.icu activities.

Author: Stephane Jouve
"""

import re
from dataclasses import dataclass
from enum import Enum
from statistics import median


class Phase(Enum):
    """Workout phase classification."""

    WARMUP = "WARMUP"
    MAIN_SET = "MAIN_SET"
    COOLDOWN = "COOLDOWN"


@dataclass
class WorkoutBlock:
    """A single block within a workout prescription.

    Attributes:
        phase: Workout phase (WARMUP, MAIN_SET, COOLDOWN)
        duration_seconds: Block duration in seconds
        intensity_low: Lower bound intensity as % FTP
        intensity_high: Upper bound intensity as % FTP (None if constant)
        cadence: Target cadence in rpm
        is_ramp: Whether this is a ramp (progressive) block
    """

    phase: Phase
    duration_seconds: int
    intensity_low: int
    intensity_high: int | None
    cadence: int
    is_ramp: bool


@dataclass
class ComputedInterval:
    """An interval ready to be sent to Intervals.icu PUT API.

    Attributes:
        type: Interval type ("WORK" or "RECOVERY")
        label: Human-readable label (e.g. "Set1 95rpm", "Warmup")
        start_index: Start index in the activity stream
        end_index: End index in the activity stream
    """

    type: str
    label: str
    start_index: int
    end_index: int


def parse_workout_text(text: str) -> list[WorkoutBlock]:
    """Parse workout text into structured blocks.

    Handles the workout format used in {week_id}_workouts.txt files:
    - Phase headers: Warmup, Main set [Nx], Cooldown
    - Blocks: - {num}m [ramp] {int}[-{int}]% {cad}rpm
    - Repetition expansion (e.g. Main set 3x)
    - Multiple Main set sections (pattern S082-04)
    - REST/REPOS → empty list

    Args:
        text: Raw workout text content.

    Returns:
        List of WorkoutBlock, empty for rest days.
    """
    # Rest day detection
    lines = text.strip().splitlines()
    for line in lines[:5]:
        stripped = line.strip().upper()
        if stripped in ("REPOS", "REST", "REPOS COMPLET"):
            return []

    blocks: list[WorkoutBlock] = []
    current_phase: Phase | None = None
    current_repeat = 1
    repeat_buffer: list[WorkoutBlock] = []

    # Block pattern: - 10m ramp 50-65% 85rpm  OR  - 45m 68-72% 88rpm  OR  - 3m 65% 90rpm
    block_re = re.compile(
        r"^-\s+(\d+)m\s+"  # duration
        r"(ramp\s+)?"  # optional ramp
        r"(\d+)(?:-(\d+))?%\s+"  # intensity (single or range)
        r"(\d+)rpm"  # cadence
    )
    # Phase header pattern
    warmup_re = re.compile(r"^Warmup\b", re.IGNORECASE)
    main_re = re.compile(r"^Main\s+set(?:\s+(\d+)x)?", re.IGNORECASE)
    cooldown_re = re.compile(r"^Cooldown\b", re.IGNORECASE)

    def _flush_repeat():
        """Expand repeat buffer and append to blocks."""
        for _ in range(current_repeat):
            blocks.extend(repeat_buffer)

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check phase headers
        m = warmup_re.match(line)
        if m:
            if current_phase == Phase.MAIN_SET and repeat_buffer:
                _flush_repeat()
                repeat_buffer = []
            current_phase = Phase.WARMUP
            current_repeat = 1
            continue

        m = main_re.match(line)
        if m:
            # Flush previous main set section if any
            if current_phase == Phase.MAIN_SET and repeat_buffer:
                _flush_repeat()
                repeat_buffer = []
            current_phase = Phase.MAIN_SET
            current_repeat = int(m.group(1)) if m.group(1) else 1
            repeat_buffer = []
            continue

        m = cooldown_re.match(line)
        if m:
            if current_phase == Phase.MAIN_SET and repeat_buffer:
                _flush_repeat()
                repeat_buffer = []
            current_phase = Phase.COOLDOWN
            current_repeat = 1
            continue

        # Parse block
        m = block_re.match(line)
        if m and current_phase is not None:
            duration_min = int(m.group(1))
            is_ramp = m.group(2) is not None
            intensity_low = int(m.group(3))
            intensity_high = int(m.group(4)) if m.group(4) else None
            cadence = int(m.group(5))

            block = WorkoutBlock(
                phase=current_phase,
                duration_seconds=duration_min * 60,
                intensity_low=intensity_low,
                intensity_high=intensity_high,
                cadence=cadence,
                is_ramp=is_ramp,
            )

            if current_phase == Phase.MAIN_SET:
                repeat_buffer.append(block)
            else:
                blocks.append(block)

    # Flush final main set if file ends without cooldown
    if current_phase == Phase.MAIN_SET and repeat_buffer:
        _flush_repeat()

    return blocks


def classify_interval_type(block: WorkoutBlock, main_blocks: list[WorkoutBlock]) -> str:
    """Classify a block as WORK or RECOVERY.

    Rules:
    - Warmup/Cooldown → always RECOVERY
    - Main set with varying intensities (spread > 5%) → high intensity = WORK
    - Main set with uniform intensity (CadenceVariations) → above median cadence = WORK

    Args:
        block: The block to classify.
        main_blocks: All main set blocks (for context).

    Returns:
        "WORK" or "RECOVERY"
    """
    if block.phase in (Phase.WARMUP, Phase.COOLDOWN):
        return "RECOVERY"

    # Compute intensity spread across main set blocks
    intensities = [b.intensity_low for b in main_blocks]
    if main_blocks:
        intensity_spread = max(intensities) - min(intensities)
    else:
        intensity_spread = 0

    if intensity_spread > 5:
        # Intensity-based classification: high intensity = WORK
        threshold = min(intensities) + intensity_spread / 2
        return "WORK" if block.intensity_low >= threshold else "RECOVERY"
    else:
        # Cadence-based classification (e.g. CadenceVariations)
        cadences = [b.cadence for b in main_blocks]
        if cadences:
            med = median(cadences)
            return "WORK" if block.cadence > med else "RECOVERY"
        return "RECOVERY"


def compute_intervals(
    blocks: list[WorkoutBlock], total_stream_points: int
) -> list[ComputedInterval]:
    """Convert parsed workout blocks into stream-aligned intervals.

    Heuristic (proven in live testing, error < 20 indices):
    - warmup_end = total_points - main_set_seconds - cooldown_seconds
    - Warmup absorbs excess time (longer warmup, pauses, etc.)
    - Main set blocks placed sequentially from warmup_end
    - Cooldown fills remaining points after main set

    Args:
        blocks: Parsed workout blocks.
        total_stream_points: Total number of data points in the activity stream.

    Returns:
        List of ComputedInterval with stream indices.

    Raises:
        ValueError: If stream is too short (warmup_end < 0).
    """
    if not blocks:
        return []

    main_blocks = [b for b in blocks if b.phase == Phase.MAIN_SET]
    cooldown_blocks = [b for b in blocks if b.phase == Phase.COOLDOWN]

    main_seconds = sum(b.duration_seconds for b in main_blocks)
    cooldown_seconds = sum(b.duration_seconds for b in cooldown_blocks)

    warmup_end = total_stream_points - main_seconds - cooldown_seconds

    if warmup_end < 0:
        raise ValueError(
            f"Stream too short: {total_stream_points} points < "
            f"{main_seconds}s main + {cooldown_seconds}s cooldown = "
            f"{main_seconds + cooldown_seconds}s minimum"
        )

    intervals: list[ComputedInterval] = []

    # Warmup: absorbs everything from 0 to warmup_end
    warmup_blocks = [b for b in blocks if b.phase == Phase.WARMUP]
    if warmup_blocks:
        intervals.append(
            ComputedInterval(
                type="RECOVERY",
                label="Warmup",
                start_index=0,
                end_index=warmup_end - 1,
            )
        )

    # Main set: sequential from warmup_end
    cursor = warmup_end
    set_counter = 0
    for block in main_blocks:
        set_counter += 1
        interval_type = classify_interval_type(block, main_blocks)
        label = f"Set{set_counter} {block.cadence}rpm"
        end = cursor + block.duration_seconds - 1
        intervals.append(
            ComputedInterval(
                type=interval_type,
                label=label,
                start_index=cursor,
                end_index=end,
            )
        )
        cursor = end + 1

    # Cooldown: fills remaining points
    if cooldown_blocks:
        intervals.append(
            ComputedInterval(
                type="RECOVERY",
                label="Cooldown",
                start_index=cursor,
                end_index=total_stream_points - 1,
            )
        )

    return intervals


def load_workout_descriptions(week_id: str) -> dict[str, str]:
    """Load full workout descriptions from {week_id}_workouts.txt.

    Parses the === WORKOUT ... === / === FIN WORKOUT === delimited file
    and returns a dict mapping intervals_name → full description.

    Args:
        week_id: Week ID (e.g., "S081").

    Returns:
        Dict {intervals_name: full_description}. Empty dict if file not found.
    """
    from magma_cycling.planning.control_tower import planning_tower

    workouts_file = planning_tower.planning_dir / f"{week_id}_workouts.txt"
    if not workouts_file.exists():
        return {}

    content = workouts_file.read_text(encoding="utf-8")
    pattern = r"=== WORKOUT (.*?) ===\n(.*?)\n=== FIN WORKOUT ==="
    matches = re.findall(pattern, content, re.DOTALL)

    descriptions: dict[str, str] = {}
    for workout_name, workout_content in matches:
        name = workout_name.strip()
        descriptions[name] = workout_content.strip()

    return descriptions
