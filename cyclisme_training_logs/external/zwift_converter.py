"""Converter for Zwift workout formats to Intervals.icu text format."""

import logging
import re

from cyclisme_training_logs.external.zwift_models import (
    SegmentType,
    ZwiftWorkout,
    ZwiftWorkoutSegment,
)

logger = logging.getLogger(__name__)


class ZwiftWorkoutConverter:
    """Converts Zwift workouts to Intervals.icu text format.

    Ensures Wahoo ELEMNT compatibility by:
    - Adding explicit power percentages to every line
    - Converting Zwift terminology to standard format
    - Handling FreeRide/ALL-OUT segments appropriately
    """

    # Power defaults for different segment types (% FTP)
    DEFAULT_WARMUP_POWER = 55
    DEFAULT_COOLDOWN_POWER = 50
    DEFAULT_RECOVERY_POWER = 55
    DEFAULT_STEADY_POWER = 90
    DEFAULT_ALLOUT_POWER = 100
    DEFAULT_CADENCE = 85

    @staticmethod
    def workout_to_intervals_text(workout: ZwiftWorkout) -> str:
        """Convert ZwiftWorkout to Intervals.icu text description.

        This is the main conversion method that ensures Wahoo compatibility.

        Args:
            workout: ZwiftWorkout object to convert

        Returns:
            Formatted text description ready for Intervals.icu

        Example output:
            ```
            Flat Out Fast (41min, 56 TSS)

            Warmup
            - 7m ramp 50-75% 85rpm

            Openers 3x
            - 30s 100% 95rpm
            - 30s 55% 85rpm

            Main - FTP Test
            - 20m 100% ALL-OUT

            Cooldown
            - 6m ramp 65-40% 85rpm
            ```
        """
        return workout.to_intervals_description()

    @staticmethod
    def parse_zwift_html_workout(html_content: str) -> ZwiftWorkout | None:
        """Parse Zwift workout from HTML page content.

        NOTE: This is a placeholder implementation. Full implementation requires
        analyzing the HTML structure of whatsonzwift.com workout pages.

        Args:
            html_content: Raw HTML content from workout page

        Returns:
            ZwiftWorkout object if parsing successful, None otherwise
        """
        # TODO: Implement HTML parsing logic
        # This would involve:
        # 1. Parse workout metadata (name, TSS, duration, category)
        # 2. Parse workout structure table/segments
        # 3. Convert to ZwiftWorkoutSegment objects
        # 4. Return ZwiftWorkout object

        logger.warning("HTML parsing not yet implemented")
        return None

    @staticmethod
    def validate_wahoo_compatibility(description: str) -> tuple[bool, list[str]]:
        """Validate that workout description is Wahoo ELEMNT compatible.

        Checks for common issues that break Wahoo export:
        - Missing power percentages
        - Incomplete transition specifications
        - Invalid segment formats

        Args:
            description: Workout description text

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        lines = description.split("\n")

        for line_num, line in enumerate(lines, start=1):
            # Skip empty lines and headers
            if not line.strip() or not line.strip().startswith("-"):
                continue

            # Check for explicit power percentage or "ramp" keyword
            has_power = bool(re.search(r"\d+%", line))
            has_ramp = "ramp" in line.lower()
            is_allout = "ALL-OUT" in line

            if not (has_power or has_ramp):
                issues.append(f"Line {line_num}: Missing explicit power percentage: {line.strip()}")

            # ALL-OUT segments should still have target power
            if is_allout and not has_power:
                issues.append(
                    f"Line {line_num}: ALL-OUT segment needs target power: {line.strip()}"
                )

        is_valid = len(issues) == 0
        return is_valid, issues

    @staticmethod
    def ensure_explicit_power(segment: ZwiftWorkoutSegment) -> ZwiftWorkoutSegment:
        """Ensure segment has explicit power values for Wahoo compatibility.

        If segment is missing power values, adds sensible defaults based on type.

        Args:
            segment: Workout segment to validate

        Returns:
            Segment with guaranteed power values
        """
        if segment.power_low is not None:
            return segment  # Already has power

        # Assign defaults based on segment type
        defaults = {
            SegmentType.WARMUP: ZwiftWorkoutConverter.DEFAULT_WARMUP_POWER,
            SegmentType.COOLDOWN: ZwiftWorkoutConverter.DEFAULT_COOLDOWN_POWER,
            SegmentType.RECOVERY: ZwiftWorkoutConverter.DEFAULT_RECOVERY_POWER,
            SegmentType.STEADY: ZwiftWorkoutConverter.DEFAULT_STEADY_POWER,
            SegmentType.FREE_RIDE: ZwiftWorkoutConverter.DEFAULT_ALLOUT_POWER,
        }

        power = defaults.get(segment.segment_type, ZwiftWorkoutConverter.DEFAULT_STEADY_POWER)

        # Create copy with power set
        return ZwiftWorkoutSegment(
            segment_type=segment.segment_type,
            duration_seconds=segment.duration_seconds,
            power_low=power,
            power_high=segment.power_high,
            cadence=segment.cadence or ZwiftWorkoutConverter.DEFAULT_CADENCE,
            description=segment.description,
            repeat_count=segment.repeat_count,
        )

    @staticmethod
    def create_sample_workout() -> ZwiftWorkout:
        """Create a sample workout for testing and demonstration.

        Returns:
            A complete ZwiftWorkout with all segments properly formatted
        """
        from cyclisme_training_logs.external.zwift_models import ZwiftCategory

        segments = [
            # Warmup ramp
            ZwiftWorkoutSegment(
                segment_type=SegmentType.RAMP,
                duration_seconds=420,  # 7min
                power_low=50,
                power_high=75,
                cadence=85,
            ),
            # Openers (repeated 3x)
            ZwiftWorkoutSegment(
                segment_type=SegmentType.INTERVAL,
                duration_seconds=30,
                power_low=100,
                cadence=95,
                repeat_count=3,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.RECOVERY,
                duration_seconds=30,
                power_low=55,
                cadence=85,
                repeat_count=3,
            ),
            # Recovery block
            ZwiftWorkoutSegment(
                segment_type=SegmentType.RECOVERY,
                duration_seconds=240,  # 4min
                power_low=50,
                cadence=85,
            ),
            # Gear selection
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=30,
                power_low=50,
                cadence=85,
                description="sélection braquet",
            ),
            # Main FTP test
            ZwiftWorkoutSegment(
                segment_type=SegmentType.FREE_RIDE,
                duration_seconds=1200,  # 20min
                power_low=100,  # Target power for ALL-OUT
                description="FTP Test",
            ),
            # Cooldown ramp
            ZwiftWorkoutSegment(
                segment_type=SegmentType.RAMP,
                duration_seconds=360,  # 6min
                power_low=65,
                power_high=40,
                cadence=85,
            ),
        ]

        workout = ZwiftWorkout(
            name="Flat Out Fast",
            category=ZwiftCategory.FTP,
            duration_minutes=41,
            tss=56,
            url="https://whatsonzwift.com/workouts/zwift-camp-baseline/2025-4-flat-out-fast",
            description="Zwift - Flat Out Fast (Test FTP 20min)",
            segments=segments,
        )

        return workout

    @staticmethod
    def format_for_wahoo_export(workout: ZwiftWorkout) -> str:
        """Format workout specifically for Wahoo ELEMNT export.

        Ensures all segments have explicit power and validates format.

        Args:
            workout: Workout to format

        Returns:
            Wahoo-compatible text description

        Raises:
            ValueError: If workout cannot be made Wahoo-compatible
        """
        # Ensure all segments have explicit power
        validated_segments = []
        for seg in workout.segments:
            validated_seg = ZwiftWorkoutConverter.ensure_explicit_power(seg)
            validated_segments.append(validated_seg)

        # Create copy with validated segments
        validated_workout = ZwiftWorkout(
            name=workout.name,
            category=workout.category,
            duration_minutes=workout.duration_minutes,
            tss=workout.tss,
            url=workout.url,
            description=workout.description,
            segments=validated_segments,
        )

        # Generate text description
        text_description = validated_workout.to_intervals_description()

        # Validate compatibility
        is_valid, issues = ZwiftWorkoutConverter.validate_wahoo_compatibility(text_description)

        if not is_valid:
            error_msg = "Workout not Wahoo-compatible:\n" + "\n".join(issues)
            logger.error(error_msg)
            raise ValueError(error_msg)

        return text_description
