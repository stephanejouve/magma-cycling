"""Seed data for Zwift workouts - manually curated collections.

This module provides manually defined Zwift workouts for seeding the cache.
Data is based on actual Zwift Camp: Baseline 2025 workouts used in training.
"""

from cyclisme_training_logs.external.zwift_models import (
    SegmentType,
    ZwiftCategory,
    ZwiftWorkout,
    ZwiftWorkoutSegment,
)


def get_zwift_camp_baseline_2025() -> list[ZwiftWorkout]:
    """Get Zwift Camp: Baseline 2025 workout collection.

    These are the 4 official baseline test workouts from Zwift Camp 2025.
    Data based on actual workouts used in training week S080.

    Returns:
        List of ZwiftWorkout objects
    """
    workouts = []

    # 1. Flat Out Fast - FTP 20min test
    workouts.append(
        ZwiftWorkout(
            name="Flat Out Fast",
            category=ZwiftCategory.FTP,
            duration_minutes=41,
            tss=56,
            url="https://whatsonzwift.com/workouts/zwift-camp-baseline/2025-4-flat-out-fast",
            description="Zwift - Flat Out Fast (Test FTP 20min)",
            segments=[
                # Warmup ramp
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=420,  # 7min
                    power_low=50,
                    power_high=75,
                    cadence=85,
                ),
                # Openers (3x)
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
                # Recovery
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
                # Main FTP test (20min ALL-OUT)
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.FREE_RIDE,
                    duration_seconds=1200,  # 20min
                    power_low=100,
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
            ],
        )
    )

    # 2. Climb Control - VO2Max 5min test
    workouts.append(
        ZwiftWorkout(
            name="Climb Control",
            category=ZwiftCategory.VO2MAX,
            duration_minutes=43,
            tss=54,
            url="https://whatsonzwift.com/workouts/zwift-camp-baseline/2025-3-climb-control",
            description="Zwift - Climb Control (Test VO2Max 5min)",
            segments=[
                # Warmup ramp
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=420,  # 7min
                    power_low=50,
                    power_high=75,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=120,  # 2min
                    power_low=50,
                    cadence=85,
                ),
                # Openers (2x)
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=90,  # 1min30
                    power_low=90,
                    cadence=90,
                    repeat_count=2,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=90,  # 1min30
                    power_low=55,
                    cadence=85,
                    repeat_count=2,
                ),
                # Recovery before test
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=300,  # 5min
                    power_low=55,
                    cadence=85,
                ),
                # Test Climb #1
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=30,
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.FREE_RIDE,
                    duration_seconds=300,  # 5min
                    power_low=110,
                    description="VO2Max Test #1",
                ),
                # Recovery between tests
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=300,  # 5min
                    power_low=50,
                    cadence=85,
                ),
                # Test Climb #2
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=30,
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.FREE_RIDE,
                    duration_seconds=300,  # 5min
                    power_low=110,
                    description="VO2Max Test #2",
                ),
                # Cooldown
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=300,  # 5min
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=30,
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=300,  # 5min
                    power_low=60,
                    power_high=40,
                    cadence=85,
                ),
            ],
        )
    )

    # 3. Red Zone Repeats - Sprint 5sec test
    workouts.append(
        ZwiftWorkout(
            name="Red Zone Repeats",
            category=ZwiftCategory.SPRINT,
            duration_minutes=40,
            tss=41,
            url="https://whatsonzwift.com/workouts/zwift-camp-baseline/2025-1-red-zone-repeats",
            description="Zwift - Red Zone Repeats (Test Sprint 5sec)",
            segments=[
                # Warmup ramp
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=600,  # 10min
                    power_low=50,
                    power_high=75,
                    cadence=85,
                ),
                # Sprint openers (5x)
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=10,
                    power_low=150,
                    cadence=110,
                    repeat_count=5,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=50,
                    power_low=55,
                    cadence=85,
                    repeat_count=5,
                ),
                # Main sprint tests (3x 5-10sec ALL-OUT)
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=180,  # 3min recovery
                    power_low=50,
                    cadence=85,
                    repeat_count=3,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.FREE_RIDE,
                    duration_seconds=10,
                    power_low=200,
                    description="Sprint Test",
                    repeat_count=3,
                ),
                # Cooldown
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=420,  # 7min
                    power_low=65,
                    power_high=40,
                    cadence=85,
                ),
            ],
        )
    )

    # 4. Power Punches - Anaerobic 1min test
    workouts.append(
        ZwiftWorkout(
            name="Power Punches",
            category=ZwiftCategory.INTERVALS,
            duration_minutes=44,
            tss=54,
            url="https://whatsonzwift.com/workouts/zwift-camp-baseline/2025-2-power-punches",
            description="Zwift - Power Punches (Test Capacité Anaérobique 1min)",
            segments=[
                # Warmup ramp
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=480,  # 8min
                    power_low=50,
                    power_high=75,
                    cadence=85,
                ),
                # Openers (3x)
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
                # Primer
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=300,  # 5min
                    power_low=95,
                    cadence=90,
                ),
                # Main anaerobic tests (3x 1min ALL-OUT)
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=300,  # 5min recovery
                    power_low=50,
                    cadence=85,
                    repeat_count=3,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.FREE_RIDE,
                    duration_seconds=60,  # 1min
                    power_low=120,
                    description="Anaerobic Test",
                    repeat_count=3,
                ),
                # Cooldown
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=300,  # 5min
                    power_low=65,
                    power_high=40,
                    cadence=85,
                ),
            ],
        )
    )

    return workouts


def get_all_seed_workouts() -> dict[str, list[ZwiftWorkout]]:
    """Get all available seed workout collections.

    Returns:
        Dict mapping collection name to list of workouts
    """
    return {
        "zwift-camp-baseline-2025": get_zwift_camp_baseline_2025(),
    }
