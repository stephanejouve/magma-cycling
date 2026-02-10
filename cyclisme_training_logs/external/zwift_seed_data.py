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


def get_build_me_up_collection() -> list[ZwiftWorkout]:
    """Get Build Me Up workout collection - varied training formats.

    These 20 workouts provide diversity across all training zones:
    - FTP/Sweet Spot with varied formats (3x8, 4x6, 2x10, etc.)
    - VO2 Max intervals (2-3min repeats)
    - Tempo/Endurance (mixed cadence work)
    - Sprint/Neuromuscular (15-30sec bursts)
    - Recovery/Skills (pedaling drills)
    - Mixed formats for fun and variety

    Returns:
        List of ZwiftWorkout objects
    """
    workouts = []

    # 1. Halvfems - Sweet Spot + Cadence (Week 2)
    workouts.append(
        ZwiftWorkout(
            name="Halvfems",
            category=ZwiftCategory.FTP,
            duration_minutes=62,
            tss=68,
            url="https://whatsonzwift.com/workouts/build-me-up/week-2-halvfems",
            description="Sweet spot training centered around 90% FTP with cadence variations",
            segments=[
                # Warmup
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=420,  # 7min
                    power_low=25,
                    power_high=75,
                    cadence=90,
                ),
                # Cadence escalation (3x)
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=95,
                    cadence=95,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=30,
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=105,
                    cadence=105,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=30,
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=115,
                    cadence=115,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=30,
                    power_low=50,
                    cadence=85,
                ),
                # Recovery
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=120,  # 2min
                    power_low=50,
                    cadence=85,
                ),
                # Sweet spot block
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=720,  # 12min
                    power_low=90,
                    cadence=90,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=240,  # 4min
                    power_low=55,
                    cadence=85,
                ),
                # 6x alternating cadence
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=60,
                    power_low=90,
                    cadence=60,
                    repeat_count=6,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=60,
                    power_low=90,
                    cadence=90,
                    repeat_count=6,
                ),
                # Recovery
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=240,  # 4min
                    power_low=55,
                    cadence=85,
                ),
                # 4x final efforts
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=120,  # 2min
                    power_low=90,
                    cadence=100,
                    repeat_count=4,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=60,  # 1min
                    power_low=90,
                    cadence=65,
                    repeat_count=4,
                ),
                # Cooldown
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=360,  # 6min
                    power_low=55,
                    power_high=25,
                ),
            ],
        )
    )

    # 2. Novanta - Sweet Spot Alternations (Week 3)
    workouts.append(
        ZwiftWorkout(
            name="Novanta",
            category=ZwiftCategory.FTP,
            duration_minutes=60,
            tss=70,
            url="https://whatsonzwift.com/workouts/build-me-up/week-3-novanta",
            description="Sweet spot training with 4x4min/1min alternations",
            segments=[
                # Warmup
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=420,  # 7min
                    power_low=25,
                    power_high=75,
                ),
                # Cadence ladder
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=95,
                    cadence=95,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=30,
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=105,
                    cadence=105,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=30,
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=115,
                    cadence=115,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=30,
                    power_low=50,
                    cadence=85,
                ),
                # Recovery
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=120,  # 2min
                    power_low=50,
                    cadence=85,
                ),
                # Main intervals: 4x (4min + 1min)
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=240,  # 4min
                    power_low=90,
                    cadence=90,
                    repeat_count=4,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=60,  # 1min
                    power_low=90,
                    cadence=65,
                    repeat_count=4,
                ),
                # Recovery
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=180,  # 3min
                    power_low=55,
                    cadence=85,
                ),
                # Sustained effort
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=300,  # 5min
                    power_low=90,
                    cadence=90,
                ),
                # Final intervals: 5x (1min + 1min)
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=60,
                    power_low=90,
                    cadence=100,
                    repeat_count=5,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=60,
                    power_low=90,
                    cadence=70,
                    repeat_count=5,
                ),
                # Recovery
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=300,  # 5min
                    power_low=90,
                    cadence=90,
                ),
                # Cooldown
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=300,  # 5min
                    power_low=55,
                    power_high=25,
                ),
            ],
        )
    )

    # 3. #8 - VO2 Max Intervals (Week 5)
    workouts.append(
        ZwiftWorkout(
            name="#8",
            category=ZwiftCategory.VO2MAX,
            duration_minutes=60,
            tss=65,
            url="https://whatsonzwift.com/workouts/build-me-up/week-5-8",
            description="VO2 Max repeats: 3x2min @ 115% FTP",
            segments=[
                # Warmup
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=600,  # 10min
                    power_low=25,
                    power_high=75,
                ),
                # Progressive cadence intervals
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=95,
                    cadence=95,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=30,
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=105,
                    cadence=105,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=30,
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=115,
                    cadence=115,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=30,
                    power_low=50,
                    cadence=85,
                ),
                # Recovery
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=120,  # 2min
                    power_low=50,
                    cadence=85,
                ),
                # VO2 Max repeats: 3x (2min on + 3min off)
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=120,  # 2min
                    power_low=115,
                    cadence=105,
                    repeat_count=3,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=180,  # 3min
                    power_low=50,
                    cadence=85,
                    repeat_count=3,
                ),
                # Steady state
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=600,  # 10min
                    power_low=65,
                    cadence=90,
                ),
                # VO2 Max repeats: 3x (2min on + 3min off)
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=120,  # 2min
                    power_low=115,
                    cadence=105,
                    repeat_count=3,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=180,  # 3min
                    power_low=50,
                    cadence=85,
                    repeat_count=3,
                ),
                # Cooldown
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=300,  # 5min
                    power_low=50,
                    power_high=25,
                ),
            ],
        )
    )

    # 4. Pedaling Drills - Recovery/Skills (Week 1)
    workouts.append(
        ZwiftWorkout(
            name="Pedaling Drills",
            category=ZwiftCategory.RECOVERY,
            duration_minutes=30,
            tss=24,
            url="https://whatsonzwift.com/workouts/build-me-up/week-1-pedaling-drills",
            description="Cadence drills and skills work for recovery",
            segments=[
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=600,  # 10min
                    power_low=40,
                    power_high=75,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=85,
                    cadence=95,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=30,
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=95,
                    cadence=105,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=30,
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=105,
                    cadence=110,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=150,  # 2min30s
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.FREE_RIDE,
                    duration_seconds=600,  # 10min
                    power_low=50,
                    description="Free ride / recovery",
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=300,  # 5min
                    power_low=50,
                    power_high=25,
                ),
            ],
        )
    )

    # 5. Renewal - Active Recovery (Week 12)
    workouts.append(
        ZwiftWorkout(
            name="Renewal",
            category=ZwiftCategory.RECOVERY,
            duration_minutes=30,
            tss=13,
            url="https://whatsonzwift.com/workouts/build-me-up/week-12-renewal",
            description="Active recovery with easy cadence work",
            segments=[
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=300,  # 5min
                    power_low=25,
                    power_high=50,
                ),
                # 4 rounds of decreasing duration
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=300,  # 5min
                    power_low=50,
                    cadence=95,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=60,
                    power_low=60,
                    cadence=100,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=30,
                    power_low=60,
                    power_high=70,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=300,  # 5min
                    power_low=50,
                    cadence=95,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=60,
                    power_low=60,
                    cadence=100,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=30,
                    power_low=60,
                    power_high=70,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=240,  # 4min
                    power_low=50,
                    cadence=95,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=60,
                    power_low=60,
                    cadence=100,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=30,
                    power_low=60,
                    power_high=70,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=180,  # 3min
                    power_low=50,
                    cadence=95,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=60,
                    power_low=60,
                    cadence=100,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=30,
                    power_low=60,
                    power_high=70,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=120,  # 2min
                    power_low=50,
                    power_high=25,
                ),
            ],
        )
    )

    # 6. Attack! - Sprint Fun (Week 6)
    workouts.append(
        ZwiftWorkout(
            name="Attack!",
            category=ZwiftCategory.SPRINT,
            duration_minutes=60,
            tss=61,
            url="https://whatsonzwift.com/workouts/build-me-up/week-6-attack",
            description="30sec sprint attacks with tempo recovery blocks",
            segments=[
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=600,  # 10min
                    power_low=25,
                    power_high=75,
                    cadence=90,
                ),
                # Cadence prep
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=95,
                    cadence=95,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=30,
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=105,
                    cadence=105,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=30,
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=115,
                    cadence=115,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=30,
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=120,  # 2min
                    power_low=50,
                    cadence=85,
                ),
                # First sprint + tempo
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=150,
                    cadence=110,
                    description="SPRINT!",
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=570,  # 9min30s
                    power_low=80,
                    cadence=90,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=180,  # 3min
                    power_low=55,
                    cadence=85,
                ),
                # Second sprint + tempo
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=150,
                    cadence=110,
                    description="SPRINT!",
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=630,  # 10min30s
                    power_low=80,
                    cadence=90,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=180,  # 3min
                    power_low=55,
                    cadence=85,
                ),
                # Third sprint + tempo
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=150,
                    cadence=110,
                    description="SPRINT!",
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=750,  # 12min30s
                    power_low=80,
                    cadence=90,
                ),
                # Cooldown
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=300,  # 5min
                    power_low=80,
                    power_high=25,
                ),
            ],
        )
    )

    # 7. Exemplar - Over-Unders (Week 10)
    workouts.append(
        ZwiftWorkout(
            name="Exemplar",
            category=ZwiftCategory.FTP,
            duration_minutes=60,
            tss=72,
            url="https://whatsonzwift.com/workouts/build-me-up/week-10-exemplar",
            description="Over-unders: 2x8min/2min + 5x2min/2min at 93/88% FTP",
            segments=[
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=600, power_low=40, power_high=75
                ),
                # 2x (8min + 2min) over-unders
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=480,
                    power_low=93,
                    cadence=75,
                    repeat_count=2,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=120,
                    power_low=88,
                    cadence=100,
                    repeat_count=2,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=180,
                    power_low=65,
                    cadence=85,
                ),
                # 5x (2min + 2min)
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=120,
                    power_low=93,
                    cadence=90,
                    repeat_count=5,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=120,
                    power_low=88,
                    cadence=70,
                    repeat_count=5,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=120, power_low=45, power_high=25
                ),
            ],
        )
    )

    # 8. Devedeset - Sweet Spot Blocks (Week 1)
    workouts.append(
        ZwiftWorkout(
            name="Devedeset",
            category=ZwiftCategory.FTP,
            duration_minutes=60,
            tss=62,
            url="https://whatsonzwift.com/workouts/build-me-up/week-1-devedeset",
            description="Sweet spot: 2x10min at 90% FTP with cadence work",
            segments=[
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=600, power_low=25, power_high=75
                ),
                # Cadence ladder
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL, duration_seconds=30, power_low=95, cadence=95
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=30, power_low=50, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=105,
                    cadence=105,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=30, power_low=50, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=115,
                    cadence=115,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=150,
                    power_low=50,
                    cadence=85,
                ),
                # 10min block 1
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=600, power_low=90, cadence=90
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=240,
                    power_low=55,
                    cadence=85,
                ),
                # 10min block 2
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=600, power_low=90, cadence=80
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=240,
                    power_low=55,
                    cadence=85,
                ),
                # Final efforts
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=120,
                    power_low=90,
                    cadence=90,
                    repeat_count=2,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=60,
                    power_low=90,
                    cadence=70,
                    repeat_count=2,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=240, power_low=90, cadence=100
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=420, power_low=55, power_high=25
                ),
            ],
        )
    )

    # 9. Giza - Pyramid (Week 7)
    workouts.append(
        ZwiftWorkout(
            name="Giza",
            category=ZwiftCategory.INTERVALS,
            duration_minutes=60,
            tss=56,
            url="https://whatsonzwift.com/workouts/build-me-up/week-7-giza",
            description="Pyramid intervals: 8min blocks at 75-80-85-80-75% with cadence changes",
            segments=[
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=420,
                    power_low=25,
                    power_high=75,
                    cadence=85,
                ),
                # Cadence prep
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL, duration_seconds=30, power_low=95, cadence=95
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=30, power_low=50, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=105,
                    cadence=105,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=30, power_low=50, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=115,
                    cadence=115,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=150,
                    power_low=50,
                    cadence=85,
                ),
                # Pyramid: 8min blocks
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=480, power_low=75, cadence=75
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=60, power_low=55, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=480, power_low=80, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=60, power_low=55, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=480, power_low=85, cadence=100
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=60, power_low=55, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=480, power_low=80, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=60, power_low=55, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=480, power_low=75, cadence=75
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=240, power_low=75, power_high=25
                ),
            ],
        )
    )

    # 10. Hang Ten - Wave Intervals (Week 8)
    workouts.append(
        ZwiftWorkout(
            name="Hang Ten",
            category=ZwiftCategory.INTERVALS,
            duration_minutes=60,
            tss=65,
            url="https://whatsonzwift.com/workouts/build-me-up/week-8-hang-ten",
            description="Wave intervals: 1/2/1min pattern at 95-80-110% with cadence variations",
            segments=[
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=300, power_low=25, power_high=60
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=300, power_low=60
                ),
                # 5x wave pattern (simplified - actual workout has cadence variations)
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=60,
                    power_low=95,
                    cadence=90,
                    repeat_count=10,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=120,
                    power_low=80,
                    cadence=90,
                    repeat_count=5,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=60,
                    power_low=110,
                    cadence=90,
                    repeat_count=5,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=120,
                    power_low=60,
                    cadence=85,
                    repeat_count=5,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=300, power_low=60, power_high=25
                ),
            ],
        )
    )

    # 11. Tine - Ramps (Week 5)
    workouts.append(
        ZwiftWorkout(
            name="Tine",
            category=ZwiftCategory.FTP,
            duration_minutes=60,
            tss=56,
            url="https://whatsonzwift.com/workouts/build-me-up/week-5-tine",
            description="Ramp intervals: 3x (3min@80% + ramps 90-100%) with varying cadence",
            segments=[
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=600, power_low=40, power_high=75
                ),
                # Cadence prep
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL, duration_seconds=30, power_low=95, cadence=95
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=30, power_low=50, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=105,
                    cadence=105,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=30, power_low=50, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=115,
                    cadence=115,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=150,
                    power_low=50,
                    cadence=85,
                ),
                # 3x blocks with ramps
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=180,
                    power_low=80,
                    cadence=90,
                    repeat_count=3,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=90,
                    power_low=90,
                    power_high=100,
                    cadence=90,
                    repeat_count=3,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=90,
                    power_low=100,
                    power_high=90,
                    cadence=90,
                    repeat_count=3,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=180,
                    power_low=80,
                    cadence=90,
                    repeat_count=3,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=240,
                    power_low=50,
                    cadence=85,
                    repeat_count=3,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=360, power_low=50, power_high=25
                ),
            ],
        )
    )

    # 12. Ham Sandwich - Complex Over-Unders (Week 3)
    workouts.append(
        ZwiftWorkout(
            name="Ham Sandwich",
            category=ZwiftCategory.FTP,
            duration_minutes=62,
            tss=76,
            url="https://whatsonzwift.com/workouts/build-me-up/week-3-ham-sandwich",
            description="Over-unders + microbursts: 4x(2min@88%+30sec@110%) + 5x30sec@130%",
            segments=[
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=600, power_low=40, power_high=75
                ),
                # Sweet spot over/unders warmup
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=80,
                    cadence=95,
                    repeat_count=3,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=95,
                    cadence=95,
                    repeat_count=2,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=105,
                    cadence=105,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=110,
                    cadence=110,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=120,
                    power_low=50,
                    cadence=85,
                ),
                # 4x over-unders
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=120,
                    power_low=88,
                    cadence=90,
                    repeat_count=4,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=110,
                    cadence=110,
                    repeat_count=4,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=150,
                    power_low=50,
                    cadence=85,
                ),
                # 5x microbursts (3 sets)
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=130,
                    cadence=110,
                    repeat_count=15,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=30,
                    power_low=50,
                    cadence=85,
                    repeat_count=15,
                ),
                # Second over-under set
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=150,
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=120,
                    power_low=88,
                    cadence=90,
                    repeat_count=4,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=110,
                    cadence=110,
                    repeat_count=4,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=120, power_low=50, power_high=25
                ),
            ],
        )
    )

    # 13. Potpourri - Mixed Threshold (Week 10)
    workouts.append(
        ZwiftWorkout(
            name="Potpourri",
            category=ZwiftCategory.FTP,
            duration_minutes=60,
            tss=64,
            url="https://whatsonzwift.com/workouts/build-me-up/week-10-potpourri",
            description="Mixed work: 5x1min@88% + 3x(2min@94%+3min@86%)",
            segments=[
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=600, power_low=25, power_high=75
                ),
                # Cadence ladder
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL, duration_seconds=30, power_low=95, cadence=95
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=30, power_low=50, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=105,
                    cadence=105,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=30, power_low=50, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=115,
                    cadence=115,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=150,
                    power_low=50,
                    cadence=85,
                ),
                # 5x alternating cadence
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=60,
                    power_low=88,
                    cadence=100,
                    repeat_count=5,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=60,
                    power_low=88,
                    cadence=60,
                    repeat_count=5,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=180,
                    power_low=55,
                    cadence=85,
                ),
                # 3x over-unders
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=120,
                    power_low=94,
                    cadence=90,
                    repeat_count=3,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=180,
                    power_low=86,
                    cadence=90,
                    repeat_count=3,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=180,
                    power_low=55,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=720, power_low=75, power_high=25
                ),
            ],
        )
    )

    # 14. Uphill Battle - Climbing Focus (Week 6)
    workouts.append(
        ZwiftWorkout(
            name="Uphill Battle",
            category=ZwiftCategory.FTP,
            duration_minutes=60,
            tss=71,
            url="https://whatsonzwift.com/workouts/build-me-up/week-6-uphill-battle",
            description="Climbing: 3x(5min@95%+30sec ramp) + microbursts",
            segments=[
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=600, power_low=25, power_high=75
                ),
                # Cadence prep
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL, duration_seconds=30, power_low=80, cadence=95
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=60, power_low=65, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=90,
                    cadence=105,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=60, power_low=65, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=105,
                    cadence=115,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=120,
                    power_low=50,
                    cadence=85,
                ),
                # 3x climb efforts
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=300,
                    power_low=95,
                    cadence=95,
                    repeat_count=3,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=30,
                    power_low=100,
                    power_high=150,
                    repeat_count=3,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=150,
                    power_low=50,
                    cadence=85,
                    repeat_count=3,
                ),
                # Microbursts
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=180,
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=130,
                    cadence=100,
                    repeat_count=5,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=30,
                    power_low=70,
                    cadence=90,
                    repeat_count=5,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=180,
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=140,
                    cadence=100,
                    repeat_count=5,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=30,
                    power_low=60,
                    cadence=90,
                    repeat_count=5,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=420, power_low=50, power_high=25
                ),
            ],
        )
    )

    # 15. Ruckus - Standing/Sitting (Week 11)
    workouts.append(
        ZwiftWorkout(
            name="Ruckus",
            category=ZwiftCategory.FTP,
            duration_minutes=60,
            tss=74,
            url="https://whatsonzwift.com/workouts/build-me-up/week-11-ruckus",
            description="Standing/sitting intervals: 7x(2min@100%+1min@75%)",
            segments=[
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=300, power_low=40, power_high=65
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=300, power_low=65, cadence=95
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=180, power_low=80, cadence=100
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=120,
                    power_low=55,
                    cadence=85,
                ),
                # 7x standing/sitting
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=120,
                    power_low=100,
                    cadence=90,
                    repeat_count=7,
                    description="Standing",
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=60,
                    power_low=75,
                    cadence=70,
                    repeat_count=7,
                    description="Sitting",
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=180,
                    power_low=55,
                    cadence=85,
                ),
                # 6x standing/sitting
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=120,
                    power_low=100,
                    cadence=90,
                    repeat_count=6,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=60,
                    power_low=75,
                    cadence=70,
                    repeat_count=6,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=180, power_low=74, power_high=25
                ),
            ],
        )
    )

    # 16. Mishmash - Cadence Variety (Week 2)
    workouts.append(
        ZwiftWorkout(
            name="Mishmash",
            category=ZwiftCategory.TEMPO,
            duration_minutes=90,
            tss=90,
            url="https://whatsonzwift.com/workouts/build-me-up/week-2-mishmash",
            description="Mixed cadence intervals: 4x(3min+1min) with varied RPM",
            segments=[
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=600, power_low=40, power_high=70
                ),
                # 4x mixed cadence blocks
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=180, power_low=80, cadence=95
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=60,
                    power_low=105,
                    cadence=65,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=60, power_low=65, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=180, power_low=80, cadence=100
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=60,
                    power_low=105,
                    cadence=65,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=60, power_low=65, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=180, power_low=80, cadence=70
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=60,
                    power_low=105,
                    cadence=100,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=60, power_low=65, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=180, power_low=80, cadence=95
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=60,
                    power_low=105,
                    cadence=65,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=120,
                    power_low=65,
                    cadence=85,
                ),
                # 3x 4min blocks
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=240, power_low=90, cadence=95
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=240, power_low=80, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=240, power_low=70, cadence=75
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=240, power_low=90, cadence=75
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=240, power_low=80, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=240, power_low=70, cadence=95
                ),
                # Cooldown
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=720, power_low=90, power_high=60
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=180, power_low=50
                ),
            ],
        )
    )

    # 17. Circus - Sprint Madness (Week 9)
    workouts.append(
        ZwiftWorkout(
            name="Circus",
            category=ZwiftCategory.SPRINT,
            duration_minutes=60,
            tss=78,
            url="https://whatsonzwift.com/workouts/build-me-up/week-9-circus",
            description="Sprint circus: 18x15sec @ 150% + descending intensity patterns",
            segments=[
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=600,
                    power_low=25,
                    power_high=75,
                    cadence=85,
                ),
                # Cadence prep
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL, duration_seconds=30, power_low=95, cadence=95
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=30, power_low=50, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=105,
                    cadence=105,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=30, power_low=50, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=115,
                    cadence=115,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=150,
                    power_low=50,
                    cadence=85,
                ),
                # Block 1: 18x15/15
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=15,
                    power_low=200,
                    cadence=100,
                    description="MAX SPRINT",
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=15, power_low=50, cadence=90
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=15,
                    power_low=150,
                    cadence=100,
                    repeat_count=18,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=15,
                    power_low=50,
                    cadence=90,
                    repeat_count=18,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=15,
                    power_low=200,
                    cadence=100,
                    description="MAX SPRINT",
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=300,
                    power_low=50,
                    cadence=90,
                ),
                # Block 2: Descending intensity
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=15,
                    power_low=180,
                    cadence=100,
                    repeat_count=4,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=15,
                    power_low=50,
                    cadence=90,
                    repeat_count=4,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=15,
                    power_low=160,
                    cadence=100,
                    repeat_count=6,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=15,
                    power_low=50,
                    cadence=90,
                    repeat_count=6,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=15,
                    power_low=140,
                    cadence=100,
                    repeat_count=6,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=15,
                    power_low=50,
                    cadence=90,
                    repeat_count=6,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=15,
                    power_low=120,
                    cadence=100,
                    repeat_count=4,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=15,
                    power_low=50,
                    cadence=90,
                    repeat_count=4,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=300,
                    power_low=50,
                    cadence=90,
                ),
                # Block 3: Mixed
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=15,
                    power_low=200,
                    cadence=100,
                    repeat_count=2,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=15,
                    power_low=50,
                    cadence=90,
                    repeat_count=2,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=15,
                    power_low=120,
                    cadence=100,
                    repeat_count=2,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=15,
                    power_low=50,
                    cadence=90,
                    repeat_count=2,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=15,
                    power_low=150,
                    cadence=100,
                    repeat_count=12,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=15,
                    power_low=50,
                    cadence=90,
                    repeat_count=12,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=300, power_low=50, power_high=25
                ),
            ],
        )
    )

    # 18. Baffling Beau - Sprint Progressions (Week 10)
    workouts.append(
        ZwiftWorkout(
            name="Baffling Beau",
            category=ZwiftCategory.SPRINT,
            duration_minutes=60,
            tss=73,
            url="https://whatsonzwift.com/workouts/build-me-up/week-10-baffling-beau",
            description="Sprint progressions: 10x40/20 + 10x30/30 + 10x20/40",
            segments=[
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=600,
                    power_low=25,
                    power_high=75,
                    cadence=85,
                ),
                # Cadence prep
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL, duration_seconds=30, power_low=95, cadence=95
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=30, power_low=50, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=105,
                    cadence=105,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=30, power_low=50, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=115,
                    cadence=115,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=150,
                    power_low=50,
                    cadence=85,
                ),
                # 10x 40/20 @ 120%
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=40,
                    power_low=120,
                    cadence=110,
                    repeat_count=10,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=20,
                    power_low=55,
                    cadence=85,
                    repeat_count=10,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=300,
                    power_low=65,
                    cadence=85,
                ),
                # 10x 30/30 @ 130%
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=130,
                    cadence=110,
                    repeat_count=10,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=30,
                    power_low=55,
                    cadence=85,
                    repeat_count=10,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=300,
                    power_low=65,
                    cadence=85,
                ),
                # 10x 20/40 @ 140%
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=20,
                    power_low=140,
                    cadence=110,
                    repeat_count=10,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=40,
                    power_low=55,
                    cadence=85,
                    repeat_count=10,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=300, power_low=55, power_high=25
                ),
            ],
        )
    )

    # 19. Amalgam - Complete Package (Week 3)
    workouts.append(
        ZwiftWorkout(
            name="Amalgam",
            category=ZwiftCategory.MIXED,
            duration_minutes=85,
            tss=99,
            url="https://whatsonzwift.com/workouts/build-me-up/week-3-amalgam",
            description="Complete package: FTP blocks + sprints + force work + shark teeth",
            segments=[
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=600, power_low=40, power_high=75
                ),
                # Cadence prep
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL, duration_seconds=30, power_low=95, cadence=95
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=30, power_low=50, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=105,
                    cadence=105,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=30, power_low=50, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=115,
                    cadence=115,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=150,
                    power_low=50,
                    cadence=85,
                ),
                # Force work
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=120,
                    power_low=85,
                    cadence=75,
                    repeat_count=2,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=60,
                    power_low=85,
                    cadence=60,
                    repeat_count=2,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=60,
                    power_low=85,
                    cadence=55,
                    repeat_count=2,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=300,
                    power_low=65,
                    cadence=85,
                ),
                # First FTP block
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=600, power_low=100, cadence=90
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=150,
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=180,
                    power_low=65,
                    cadence=85,
                ),
                # Sharp efforts
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=15,
                    power_low=110,
                    cadence=110,
                    repeat_count=6,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=45,
                    power_low=45,
                    cadence=85,
                    repeat_count=6,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=300,
                    power_low=65,
                    cadence=85,
                ),
                # Shark teeth (3x ramps)
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=60,
                    power_low=105,
                    power_high=115,
                    repeat_count=3,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP,
                    duration_seconds=60,
                    power_low=115,
                    power_high=105,
                    repeat_count=3,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=60,
                    power_low=50,
                    cadence=85,
                    repeat_count=3,
                ),
                # Second FTP block
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=150,
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=180,
                    power_low=65,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=600, power_low=100, cadence=90
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=300, power_low=65, power_high=40
                ),
            ],
        )
    )

    # 20. Escalation - Progressive Build (Week 5)
    workouts.append(
        ZwiftWorkout(
            name="Escalation",
            category=ZwiftCategory.MIXED,
            duration_minutes=95,
            tss=114,
            url="https://whatsonzwift.com/workouts/build-me-up/week-5-escalation",
            description="Progressive build: 4min@95% + VO2 surges + threshold + 10x30sec@150%",
            segments=[
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=600, power_low=40, power_high=75
                ),
                # Cadence prep
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL, duration_seconds=30, power_low=95, cadence=95
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=30, power_low=50, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=105,
                    cadence=105,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY, duration_seconds=30, power_low=50, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=115,
                    cadence=115,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=150,
                    power_low=50,
                    cadence=85,
                ),
                # Build phase
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=240, power_low=95, cadence=100
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=480, power_low=80, cadence=90
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=180,
                    power_low=50,
                    cadence=85,
                ),
                # Threshold efforts
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=240, power_low=95, cadence=70
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=120, power_low=80, cadence=70
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=60,
                    power_low=80,
                    cadence=100,
                    repeat_count=2,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=120,
                    power_low=80,
                    cadence=70,
                    repeat_count=2,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=180,
                    power_low=50,
                    cadence=85,
                ),
                # VO2 surges (3x with increasing rest)
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=30, power_low=80, power_high=105
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=105,
                    cadence=100,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=30, power_low=105, power_high=80
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=60, power_low=80, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=30, power_low=80, power_high=105
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=105,
                    cadence=100,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=30, power_low=105, power_high=80
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=120, power_low=80, cadence=85
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=30, power_low=80, power_high=105
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=105,
                    cadence=100,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=30, power_low=105, power_high=80
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=180, power_low=80, cadence=85
                ),
                # Sprint work
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=180,
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=120, power_low=95, cadence=90
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=60,
                    power_low=80,
                    cadence=90,
                    repeat_count=4,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY,
                    duration_seconds=60,
                    power_low=80,
                    cadence=65,
                    repeat_count=4,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.STEADY, duration_seconds=120, power_low=95, cadence=90
                ),
                # Final sprints
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=300,
                    power_low=50,
                    cadence=85,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.INTERVAL,
                    duration_seconds=30,
                    power_low=150,
                    cadence=100,
                    repeat_count=10,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RECOVERY,
                    duration_seconds=30,
                    power_low=65,
                    cadence=85,
                    repeat_count=10,
                ),
                ZwiftWorkoutSegment(
                    segment_type=SegmentType.RAMP, duration_seconds=180, power_low=50, power_high=25
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
        "build-me-up": get_build_me_up_collection(),
    }
