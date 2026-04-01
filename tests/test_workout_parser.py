"""Tests for workout_parser module."""

import pytest

from magma_cycling.workout_parser import (
    Phase,
    WorkoutBlock,
    calculate_workout_duration,
    classify_interval_type,
    compute_intervals,
    parse_workout_text,
)


class TestParseWorkoutText:
    """Tests for parse_workout_text()."""

    def test_simple_three_phase(self):
        """Warmup + Main + Cooldown basique."""
        text = """\
Endurance Base (68min, 48 TSS)

Warmup
- 10m ramp 50-65% 85rpm
- 3m 65% 90rpm

Main set
- 45m 68-72% 88rpm

Cooldown
- 10m ramp 65-50% 85rpm
"""
        blocks = parse_workout_text(text)
        assert len(blocks) == 4

        # Warmup blocks
        assert blocks[0].phase == Phase.WARMUP
        assert blocks[0].duration_seconds == 600
        assert blocks[0].is_ramp is True
        assert blocks[0].intensity_low == 50
        assert blocks[0].intensity_high == 65

        assert blocks[1].phase == Phase.WARMUP
        assert blocks[1].duration_seconds == 180
        assert blocks[1].cadence == 90

        # Main set
        assert blocks[2].phase == Phase.MAIN_SET
        assert blocks[2].duration_seconds == 2700
        assert blocks[2].intensity_low == 68
        assert blocks[2].intensity_high == 72
        assert blocks[2].cadence == 88

        # Cooldown
        assert blocks[3].phase == Phase.COOLDOWN
        assert blocks[3].duration_seconds == 600
        assert blocks[3].is_ramp is True

    def test_repeated_main_set(self):
        """Main set 3x → 12 blocs main (4 blocs * 3 repetitions)."""
        text = """\
Variations Cadence (40min, 32 TSS)

Warmup
- 5m ramp 50-65% 85rpm

Main set 3x
- 3m 70% 95rpm
- 2m 70% 80rpm
- 3m 70% 105rpm
- 2m 65% 85rpm

Cooldown
- 5m ramp 65-50% 85rpm
"""
        blocks = parse_workout_text(text)

        warmup = [b for b in blocks if b.phase == Phase.WARMUP]
        main = [b for b in blocks if b.phase == Phase.MAIN_SET]
        cooldown = [b for b in blocks if b.phase == Phase.COOLDOWN]

        assert len(warmup) == 1
        assert len(main) == 12  # 4 * 3
        assert len(cooldown) == 1

        # Check repetition pattern
        assert main[0].cadence == 95
        assert main[1].cadence == 80
        assert main[2].cadence == 105
        assert main[3].cadence == 85
        # Second repetition
        assert main[4].cadence == 95
        assert main[5].cadence == 80

    def test_multiple_main_sections(self):
        """Main set 2x followed by Main set (pattern S082-04)."""
        text = """\
Tempo Progression (78min, 68 TSS)

Warmup
- 12m ramp 50-65% 85rpm
- 3m 65% 90rpm

Main set 2x
- 15m 78-82% 90rpm
- 5m 62% 85rpm

Main set
- 12m 84-86% 92rpm

Cooldown
- 10m ramp 65-50% 85rpm
"""
        blocks = parse_workout_text(text)

        main = [b for b in blocks if b.phase == Phase.MAIN_SET]
        assert len(main) == 5  # 2*2 + 1

        # First main set section: 2x(15m + 5m)
        assert main[0].intensity_low == 78
        assert main[1].intensity_low == 62
        assert main[2].intensity_low == 78  # second repeat
        assert main[3].intensity_low == 62

        # Second main set section: 1x(12m)
        assert main[4].intensity_low == 84

    def test_rest_day_empty(self):
        """REPOS → empty list."""
        text = """\
REPOS

Séance reportée à samedi matin (S081-06a)
"""
        blocks = parse_workout_text(text)
        assert blocks == []

    def test_rest_day_rest(self):
        """REST → empty list."""
        text = "REST"
        blocks = parse_workout_text(text)
        assert blocks == []


class TestClassifyIntervalType:
    """Tests for classify_interval_type()."""

    def test_warmup_always_recovery(self):
        """Warmup blocks are always RECOVERY."""
        block = WorkoutBlock(Phase.WARMUP, 600, 50, 65, 85, True)
        assert classify_interval_type(block, []) == "RECOVERY"

    def test_cooldown_always_recovery(self):
        """Cooldown blocks are always RECOVERY."""
        block = WorkoutBlock(Phase.COOLDOWN, 600, 65, 50, 85, True)
        assert classify_interval_type(block, []) == "RECOVERY"

    def test_classify_sweetspot(self):
        """High intensity = WORK, low intensity = RECOVERY when spread > 5%."""
        work_block = WorkoutBlock(Phase.MAIN_SET, 600, 90, None, 92, False)
        recovery_block = WorkoutBlock(Phase.MAIN_SET, 240, 62, None, 85, False)
        main_blocks = [work_block, recovery_block]

        assert classify_interval_type(work_block, main_blocks) == "WORK"
        assert classify_interval_type(recovery_block, main_blocks) == "RECOVERY"

    def test_classify_cadence_variations(self):
        """Same intensity → cadence above median = WORK."""
        high_cad = WorkoutBlock(Phase.MAIN_SET, 180, 70, None, 105, False)
        low_cad = WorkoutBlock(Phase.MAIN_SET, 120, 70, None, 80, False)
        med_cad = WorkoutBlock(Phase.MAIN_SET, 180, 70, None, 95, False)
        rest_cad = WorkoutBlock(Phase.MAIN_SET, 120, 65, None, 85, False)
        main_blocks = [high_cad, low_cad, med_cad, rest_cad]

        # median cadence of [105, 80, 95, 85] = 90
        assert classify_interval_type(high_cad, main_blocks) == "WORK"  # 105 > 90
        assert classify_interval_type(med_cad, main_blocks) == "WORK"  # 95 > 90
        assert classify_interval_type(low_cad, main_blocks) == "RECOVERY"  # 80 < 90
        assert classify_interval_type(rest_cad, main_blocks) == "RECOVERY"  # 85 < 90


class TestComputeIntervals:
    """Tests for compute_intervals()."""

    def test_compute_intervals_alignment(self):
        """Warmup absorbs excess time, main set aligns correctly."""
        blocks = [
            WorkoutBlock(Phase.WARMUP, 600, 50, 65, 85, True),
            WorkoutBlock(Phase.MAIN_SET, 600, 90, None, 92, False),
            WorkoutBlock(Phase.MAIN_SET, 240, 62, None, 85, False),
            WorkoutBlock(Phase.COOLDOWN, 300, 65, 50, 85, True),
        ]

        # Stream is longer than prescription (real world: pauses, longer warmup)
        total_points = 2000
        intervals = compute_intervals(blocks, total_points)

        assert len(intervals) == 4  # warmup + 2 main + cooldown

        # Warmup absorbs extra time
        warmup = intervals[0]
        assert warmup.label == "Warmup"
        assert warmup.type == "RECOVERY"
        assert warmup.start_index == 0
        # warmup_end = 2000 - 600 - 240 - 300 = 860
        assert warmup.end_index == 859

        # Main set 1
        main1 = intervals[1]
        assert main1.start_index == 860
        assert main1.end_index == 860 + 600 - 1  # 1459

        # Main set 2
        main2 = intervals[2]
        assert main2.start_index == 1460
        assert main2.end_index == 1460 + 240 - 1  # 1699

        # Cooldown fills remaining
        cooldown = intervals[3]
        assert cooldown.start_index == 1700
        assert cooldown.end_index == 1999

    def test_stream_too_short_raises(self):
        """Stream < main+cooldown → ValueError."""
        blocks = [
            WorkoutBlock(Phase.WARMUP, 600, 50, 65, 85, True),
            WorkoutBlock(Phase.MAIN_SET, 1800, 90, None, 92, False),
            WorkoutBlock(Phase.COOLDOWN, 600, 65, 50, 85, True),
        ]
        with pytest.raises(ValueError, match="Stream too short"):
            compute_intervals(blocks, 2000)  # 1800 + 600 = 2400 > 2000

    def test_empty_blocks(self):
        """Empty blocks → empty intervals."""
        assert compute_intervals([], 5000) == []

    def test_labels_and_types(self):
        """Labels include set number and cadence; types are classified correctly."""
        blocks = [
            WorkoutBlock(Phase.WARMUP, 300, 50, 65, 85, True),
            WorkoutBlock(Phase.MAIN_SET, 600, 90, None, 92, False),
            WorkoutBlock(Phase.MAIN_SET, 240, 62, None, 85, False),
            WorkoutBlock(Phase.MAIN_SET, 600, 90, None, 92, False),
            WorkoutBlock(Phase.COOLDOWN, 300, 65, 50, 85, True),
        ]
        intervals = compute_intervals(blocks, 3000)

        assert intervals[0].label == "Warmup"
        assert intervals[1].label == "Set1 92rpm"
        assert intervals[2].label == "Set2 85rpm"
        assert intervals[3].label == "Set3 92rpm"
        assert intervals[4].label == "Cooldown"

        # Intensity spread: 90 vs 62 = 28 > 5 → intensity-based
        assert intervals[1].type == "WORK"
        assert intervals[2].type == "RECOVERY"
        assert intervals[3].type == "WORK"


class TestCalculateWorkoutDuration:
    """Tests for calculate_workout_duration()."""

    def test_simple_workout(self):
        """Blocs 10+3+45+10=68 → retourne 68."""
        text = """\
Endurance Base (68min, 48 TSS)

Warmup
- 10m ramp 50-65% 85rpm
- 3m 65% 90rpm

Main set
- 45m 68-72% 88rpm

Cooldown
- 10m ramp 65-50% 85rpm
"""
        assert calculate_workout_duration(text) == 68

    def test_repeated_blocks(self):
        """Main set 3x → expansion correcte."""
        text = """\
Variations Cadence (40min, 32 TSS)

Warmup
- 5m ramp 50-65% 85rpm

Main set 3x
- 3m 70% 95rpm
- 2m 70% 80rpm
- 3m 70% 105rpm
- 2m 65% 85rpm

Cooldown
- 5m ramp 65-50% 85rpm
"""
        # 5 + 3*(3+2+3+2) + 5 = 5 + 30 + 5 = 40
        assert calculate_workout_duration(text) == 40

    def test_rest_day_returns_none(self):
        """Texte REPOS → None."""
        text = "REPOS\n\nSéance reportée à samedi."
        assert calculate_workout_duration(text) is None

    def test_unparseable_returns_none(self):
        """Texte libre sans blocs structurés → None."""
        text = "Sortie libre en endurance, rouler au feeling."
        assert calculate_workout_duration(text) is None

    def test_header_ignored_blocks_used(self):
        """Header dit 90min, blocs totalisent 75min → retourne 75."""
        text = """\
SweetSpot Progressif (90min, 72 TSS)

Warmup
- 10m ramp 50-65% 85rpm
- 5m 65% 90rpm

Main set
- 40m 88-92% 90rpm
- 5m 62% 85rpm

Cooldown
- 10m ramp 65-50% 85rpm
- 5m 50% 80rpm
"""
        # 10+5+40+5+10+5 = 75 (header says 90)
        assert calculate_workout_duration(text) == 75
