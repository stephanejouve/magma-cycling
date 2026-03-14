"""Tests for Zwift scraper segment parsing and pattern detection."""

import pytest

from magma_cycling.external.zwift_models import SegmentType, ZwiftWorkoutSegment
from magma_cycling.external.zwift_scraper import ZwiftWorkoutScraper

# ---------------------------------------------------------------------------
# Segment parsing tests
# ---------------------------------------------------------------------------


class TestParseSegmentsFromText:
    """Tests for _parse_segments_from_text."""

    def test_ramp_warmup(self):
        """Parse ascending ramp as warmup."""
        text = "7min from 25 to 75% FTP"
        segs = ZwiftWorkoutScraper._parse_segments_from_text(text)
        assert len(segs) == 1
        assert segs[0].segment_type == SegmentType.WARMUP
        assert segs[0].duration_seconds == 420
        assert segs[0].power_low == 25
        assert segs[0].power_high == 75

    def test_ramp_cooldown(self):
        """Parse descending ramp as cooldown."""
        text = "7min from 25 to 75% FTP\n" "10min @ 85rpm, 90% FTP\n" "6min from 55 to 25% FTP"
        segs = ZwiftWorkoutScraper._parse_segments_from_text(text)
        assert len(segs) == 3
        assert segs[2].segment_type == SegmentType.COOLDOWN
        assert segs[2].power_low == 55
        assert segs[2].power_high == 25

    def test_steady_with_cadence(self):
        """Parse steady segment with cadence."""
        text = "12min @ 90rpm, 90% FTP"
        segs = ZwiftWorkoutScraper._parse_segments_from_text(text)
        assert len(segs) == 1
        assert segs[0].segment_type == SegmentType.STEADY
        assert segs[0].duration_seconds == 720
        assert segs[0].power_low == 90
        assert segs[0].cadence == 90

    def test_steady_without_cadence(self):
        """Parse steady segment without cadence."""
        text = "2min @ 55% FTP"
        segs = ZwiftWorkoutScraper._parse_segments_from_text(text)
        assert len(segs) == 1
        assert segs[0].segment_type == SegmentType.RECOVERY
        assert segs[0].power_low == 55
        assert segs[0].cadence is None

    def test_interval_with_repeats(self):
        """Parse interval pattern with repeats (Nx)."""
        text = "6x 1min @ 60rpm, 90% FTP, 1min @ 90rpm, 90% FTP"
        segs = ZwiftWorkoutScraper._parse_segments_from_text(text)
        assert len(segs) == 2
        assert segs[0].segment_type == SegmentType.INTERVAL
        assert segs[0].repeat_count == 6
        assert segs[0].power_low == 90
        assert segs[0].cadence == 60
        assert segs[1].segment_type == SegmentType.RECOVERY
        assert segs[1].repeat_count == 6

    def test_seconds_duration(self):
        """Parse 30sec duration."""
        text = "30sec @ 95rpm, 95% FTP"
        segs = ZwiftWorkoutScraper._parse_segments_from_text(text)
        assert len(segs) == 1
        assert segs[0].duration_seconds == 30

    def test_free_ride(self):
        """Parse free ride segment."""
        text = "20min free ride"
        segs = ZwiftWorkoutScraper._parse_segments_from_text(text)
        assert len(segs) == 1
        assert segs[0].segment_type == SegmentType.FREE_RIDE
        assert segs[0].duration_seconds == 1200

    def test_complete_halvfems_structure(self):
        """Parse a realistic Halvfems-like workout."""
        text = """
7min from 25 to 75% FTP
1x 30sec @ 95rpm, 95% FTP, 30sec @ 85rpm, 50% FTP
2min @ 85rpm, 50% FTP
12min @ 90rpm, 90% FTP
4min @ 85rpm, 55% FTP
6x 1min @ 60rpm, 90% FTP, 1min @ 90rpm, 90% FTP
4min @ 85rpm, 55% FTP
6min from 55 to 25% FTP
"""
        segs = ZwiftWorkoutScraper._parse_segments_from_text(text)
        # Should parse: ramp + interval + recovery + steady + recovery +
        # interval pair + recovery + cooldown
        assert len(segs) >= 6
        assert segs[0].segment_type == SegmentType.WARMUP
        assert segs[-1].segment_type == SegmentType.COOLDOWN

    def test_empty_text_returns_empty(self):
        """Empty text returns empty list."""
        assert ZwiftWorkoutScraper._parse_segments_from_text("") == []

    def test_non_matching_text_returns_empty(self):
        """Text with no workout patterns returns empty list."""
        text = "This is just a regular description with no workout data."
        assert ZwiftWorkoutScraper._parse_segments_from_text(text) == []

    def test_ramp_with_rpm(self):
        """Parse ramp with RPM prefix."""
        text = "10min @ 85rpm, from 50 to 80% FTP"
        segs = ZwiftWorkoutScraper._parse_segments_from_text(text)
        assert len(segs) == 1
        assert segs[0].segment_type == SegmentType.WARMUP
        assert segs[0].duration_seconds == 600
        assert segs[0].power_low == 50
        assert segs[0].power_high == 80

    def test_multiline_sweet_spot_pyramid(self):
        """Parse full Sweet Spot Pyramid with newlines."""
        text = (
            "10min @ 85rpm, from 50 to 80% FTP\n"
            "2min @ 85rpm, 55% FTP\n"
            "10min @ 90rpm, 88% FTP\n"
            "2min @ 85rpm, 55% FTP\n"
            "10min @ 90rpm, 90% FTP\n"
            "2min @ 85rpm, 55% FTP\n"
            "10min @ 90rpm, 93% FTP\n"
            "2min @ 85rpm, 55% FTP\n"
            "10min @ 90rpm, 90% FTP\n"
            "2min @ 85rpm, 55% FTP\n"
            "10min @ 90rpm, 88% FTP\n"
            "2min from 50 to 30% FTP"
        )
        segs = ZwiftWorkoutScraper._parse_segments_from_text(text)
        assert len(segs) == 12
        assert segs[0].segment_type == SegmentType.WARMUP
        assert segs[-1].segment_type == SegmentType.COOLDOWN
        steady = [s for s in segs if s.segment_type == SegmentType.STEADY]
        assert len(steady) == 5
        assert [s.power_low for s in steady] == [88, 90, 93, 90, 88]


# ---------------------------------------------------------------------------
# Pattern detection tests
# ---------------------------------------------------------------------------


class TestDetectPattern:
    """Tests for detect_pattern."""

    def test_blocs_repetes(self):
        """Intervals with repeat_count > 1 are blocs-repetes."""
        segments = [
            ZwiftWorkoutSegment(
                segment_type=SegmentType.WARMUP,
                duration_seconds=420,
                power_low=50,
                power_high=75,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.INTERVAL,
                duration_seconds=600,
                power_low=90,
                repeat_count=3,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.RECOVERY,
                duration_seconds=240,
                power_low=55,
                repeat_count=3,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.COOLDOWN,
                duration_seconds=360,
                power_low=65,
                power_high=40,
            ),
        ]
        assert ZwiftWorkoutScraper.detect_pattern(segments) == "blocs-repetes"

    def test_progressif(self):
        """Strictly ascending power is progressif."""
        segments = [
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=600,
                power_low=70,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=600,
                power_low=80,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=600,
                power_low=90,
            ),
        ]
        assert ZwiftWorkoutScraper.detect_pattern(segments) == "progressif"

    def test_pyramide(self):
        """Ascending then descending power is pyramide."""
        segments = [
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=300,
                power_low=70,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=300,
                power_low=80,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=300,
                power_low=90,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=300,
                power_low=80,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=300,
                power_low=70,
            ),
        ]
        assert ZwiftWorkoutScraper.detect_pattern(segments) == "pyramide"

    def test_over_under(self):
        """Alternating above/below threshold is over-under."""
        segments = [
            ZwiftWorkoutSegment(
                segment_type=SegmentType.INTERVAL,
                duration_seconds=300,
                power_low=105,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=300,
                power_low=90,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.INTERVAL,
                duration_seconds=300,
                power_low=105,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=300,
                power_low=90,
            ),
        ]
        assert ZwiftWorkoutScraper.detect_pattern(segments) == "over-under"

    def test_libre_default(self):
        """Mixed segments with no clear pattern return libre."""
        segments = [
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=600,
                power_low=70,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=600,
                power_low=90,
            ),
        ]
        assert ZwiftWorkoutScraper.detect_pattern(segments) == "libre"

    def test_empty_segments_returns_libre(self):
        """Empty segments returns libre."""
        assert ZwiftWorkoutScraper.detect_pattern([]) == "libre"

    def test_warmup_cooldown_skipped(self):
        """Warmup and cooldown are excluded from pattern detection."""
        segments = [
            ZwiftWorkoutSegment(
                segment_type=SegmentType.WARMUP,
                duration_seconds=420,
                power_low=50,
                power_high=75,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.COOLDOWN,
                duration_seconds=360,
                power_low=65,
                power_high=40,
            ),
        ]
        assert ZwiftWorkoutScraper.detect_pattern(segments) == "libre"

    def test_over_under_repeated(self):
        """Repeated interval+recovery near threshold is over-under."""
        segments = [
            ZwiftWorkoutSegment(
                segment_type=SegmentType.INTERVAL,
                duration_seconds=120,
                power_low=105,
                repeat_count=3,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.RECOVERY,
                duration_seconds=60,
                power_low=90,
                repeat_count=3,
            ),
        ]
        assert ZwiftWorkoutScraper.detect_pattern(segments) == "over-under"

    def test_over_under_alternating_steady(self):
        """Alternating steady above/below threshold is over-under."""
        segments = [
            ZwiftWorkoutSegment(
                segment_type=SegmentType.RAMP,
                duration_seconds=180,
                power_low=35,
                power_high=55,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=120,
                power_low=96,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=60,
                power_low=104,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=120,
                power_low=96,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=60,
                power_low=104,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.RAMP,
                duration_seconds=180,
                power_low=55,
                power_high=35,
            ),
        ]
        assert ZwiftWorkoutScraper.detect_pattern(segments) == "over-under"

    def test_pyramide_with_ramp_warmup_cooldown(self):
        """Pyramid detection excludes RAMP warmup/cooldown."""
        segments = [
            ZwiftWorkoutSegment(
                segment_type=SegmentType.RAMP,
                duration_seconds=600,
                power_low=50,
                power_high=80,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=600,
                power_low=88,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.RECOVERY,
                duration_seconds=120,
                power_low=55,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=600,
                power_low=93,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.RECOVERY,
                duration_seconds=120,
                power_low=55,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=600,
                power_low=88,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.RAMP,
                duration_seconds=120,
                power_low=50,
                power_high=30,
            ),
        ]
        assert ZwiftWorkoutScraper.detect_pattern(segments) == "pyramide"

    def test_pyramide_giza_with_openers(self):
        """Giza-style pyramid with leading short openers is pyramide."""
        segments = [
            ZwiftWorkoutSegment(
                segment_type=SegmentType.RAMP,
                duration_seconds=420,
                power_low=25,
                power_high=75,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.INTERVAL,
                duration_seconds=30,
                power_low=95,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.RECOVERY,
                duration_seconds=30,
                power_low=50,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.INTERVAL,
                duration_seconds=30,
                power_low=115,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.RECOVERY,
                duration_seconds=150,
                power_low=50,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=480,
                power_low=75,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.RECOVERY,
                duration_seconds=60,
                power_low=55,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=480,
                power_low=85,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.RECOVERY,
                duration_seconds=60,
                power_low=55,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=480,
                power_low=75,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.RAMP,
                duration_seconds=240,
                power_low=75,
                power_high=25,
            ),
        ]
        assert ZwiftWorkoutScraper.detect_pattern(segments) == "pyramide"

    def test_over_under_intra_bloc_hang_ten(self):
        """Hang Ten: repeating block with over/under within is over-under."""
        segs = [
            ZwiftWorkoutSegment(
                segment_type=SegmentType.WARMUP,
                duration_seconds=300,
                power_low=25,
                power_high=60,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.RECOVERY,
                duration_seconds=300,
                power_low=60,
            ),
        ]
        block = [
            ZwiftWorkoutSegment(segment_type=SegmentType.STEADY, duration_seconds=60, power_low=95),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY, duration_seconds=120, power_low=80
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY, duration_seconds=60, power_low=110
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY, duration_seconds=120, power_low=80
            ),
            ZwiftWorkoutSegment(segment_type=SegmentType.STEADY, duration_seconds=60, power_low=95),
        ]
        for _ in range(6):
            segs.extend(block)
            segs.append(
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=120,
                    power_low=60,
                )
            )
        segs.append(
            ZwiftWorkoutSegment(
                segment_type=SegmentType.COOLDOWN,
                duration_seconds=300,
                power_low=60,
                power_high=25,
            )
        )
        assert ZwiftWorkoutScraper.detect_pattern(segs) == "over-under"

    def test_repeating_block_blocs_repetes(self):
        """Repeating block without over/under is blocs-repetes."""
        segs = []
        block = [
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY, duration_seconds=300, power_low=80
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY, duration_seconds=180, power_low=70
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY, duration_seconds=300, power_low=80
            ),
        ]
        for _ in range(4):
            segs.extend(block)
        assert ZwiftWorkoutScraper.detect_pattern(segs) == "blocs-repetes"


# ---------------------------------------------------------------------------
# Duration parsing tests
# ---------------------------------------------------------------------------


class TestParseDurationSeconds:
    """Tests for _parse_duration_seconds."""

    @pytest.mark.parametrize(
        "input_str,expected",
        [
            ("7min", 420),
            ("30sec", 30),
            ("1min", 60),
            ("2:00", 120),
            ("0:30", 30),
        ],
    )
    def test_valid_durations(self, input_str, expected):
        """Valid duration strings are parsed correctly."""
        assert ZwiftWorkoutScraper._parse_duration_seconds(input_str) == expected

    def test_invalid_returns_none(self):
        """Invalid duration string returns None."""
        assert ZwiftWorkoutScraper._parse_duration_seconds("invalid") is None
