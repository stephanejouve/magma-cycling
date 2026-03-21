"""Adapt structured workouts to terrain circuits."""

import math

from magma_cycling.intelligence.biomechanics import calculer_cadence_optimale
from magma_cycling.terrain.models import (
    AdaptedSegment,
    AdaptedWorkout,
    GearObservation,
    GradeCategory,
    TerrainCircuit,
)

# Power adjustment by grade category (negative = reduction)
POWER_ADJUSTMENTS: dict[GradeCategory, float] = {
    GradeCategory.descente_raide: -15.0,
    GradeCategory.descente: -10.0,
    GradeCategory.faux_plat_descendant: -3.0,
    GradeCategory.plat: 0.0,
    GradeCategory.faux_plat_montant: 0.0,
    GradeCategory.montee: -3.0,
    GradeCategory.montee_raide: -5.0,
}

# Cadence overlay by grade category (applied on top of biomechanics)
CADENCE_OVERLAY: dict[GradeCategory, int] = {
    GradeCategory.descente_raide: 0,
    GradeCategory.descente: 0,
    GradeCategory.faux_plat_descendant: 0,
    GradeCategory.plat: 0,
    GradeCategory.faux_plat_montant: 0,
    GradeCategory.montee: -3,
    GradeCategory.montee_raide: -5,
}


def _estimate_speed_kmh(
    power_watts: float,
    grade_pct: float,
    weight_kg: float,
) -> float:
    """Estimate cycling speed from power, grade, and weight.

    Simplified model: P = (CdA * 0.5 * rho * v^3) + (m * g * sin(theta) * v) + (Crr * m * g * cos(theta) * v)

    For simplicity we use an iterative approach with reasonable defaults.

    Args:
        power_watts: Power output in watts.
        grade_pct: Road grade in percent.
        weight_kg: Total weight (rider + bike) in kg.

    Returns:
        Estimated speed in km/h (minimum 5 km/h).
    """
    if power_watts <= 0:
        return 5.0

    # Constants
    cda = 0.32  # Drag coefficient * frontal area (m^2)
    rho = 1.225  # Air density (kg/m^3)
    crr = 0.005  # Rolling resistance
    g = 9.81
    total_mass = weight_kg + 8.0  # Bike weight

    grade_rad = math.atan(grade_pct / 100.0)

    # Iterative solve: find v where P_required(v) == power_watts
    # Start with a rough estimate and refine
    v = 8.0  # m/s initial guess
    for _ in range(20):
        p_aero = 0.5 * cda * rho * v**3
        p_gravity = total_mass * g * math.sin(grade_rad) * v
        p_rolling = crr * total_mass * g * math.cos(grade_rad) * v
        p_total = p_aero + p_gravity + p_rolling

        if abs(p_total) < 1e-6:
            break

        # Newton-like step
        dp_dv = (
            1.5 * cda * rho * v**2
            + total_mass * g * math.sin(grade_rad)
            + crr * total_mass * g * math.cos(grade_rad)
        )
        if abs(dp_dv) < 1e-6:
            break

        v = v - (p_total - power_watts) / dp_dv
        v = max(v, 1.0)  # Floor at 1 m/s

    speed_kmh = v * 3.6
    return max(speed_kmh, 5.0)


def _parse_workout_phases(workout: dict | str) -> list[dict]:
    """Parse a workout into sequential phases with duration and power.

    Supports:
    - Dict with 'phases' key (list of {duration_min, power_pct})
    - String with simple notation like '10min@65% + 3x10min@88% + 10min@55%'
    - Dict with 'intervals_description' from catalog

    Args:
        workout: Workout definition.

    Returns:
        List of dicts with 'duration_min' and 'power_pct' keys.
    """
    if isinstance(workout, dict):
        if "phases" in workout:
            return workout["phases"]
        if "intervals_description" in workout:
            return _parse_intervals_description(workout["intervals_description"])
        if "segments" in workout:
            return [
                {
                    "duration_min": s.get("duration_min", 5),
                    "power_pct": s.get("power_pct", 75),
                }
                for s in workout["segments"]
            ]
        return [{"duration_min": 60, "power_pct": 75}]

    if isinstance(workout, str):
        return _parse_simple_notation(workout)

    return [{"duration_min": 60, "power_pct": 75}]


def _parse_simple_notation(notation: str) -> list[dict]:
    """Parse simple workout notation like '10min@65% + 3x10min@88%'.

    Args:
        notation: Workout notation string.

    Returns:
        List of phase dicts.
    """
    phases = []
    parts = [p.strip() for p in notation.split("+")]

    for part in parts:
        if not part:
            continue

        # Handle repetitions: 3x10min@88%
        if "x" in part.split("@")[0]:
            rep_part, rest = part.split("x", 1)
            reps = int(rep_part.strip())
        else:
            reps = 1
            rest = part

        # Parse duration and power
        if "@" in rest:
            dur_str, pwr_str = rest.split("@")
        else:
            dur_str = rest
            pwr_str = "75%"

        duration = int(dur_str.replace("min", "").strip())
        power = float(pwr_str.replace("%", "").strip())

        for _ in range(reps):
            phases.append({"duration_min": duration, "power_pct": power})

    return phases


def _parse_intervals_description(description: str) -> list[dict]:
    r"""Parse Intervals.icu workout description to phases.

    Handles format like: '- 10m 65% FTP\n- 3x 10m 88% FTP...'

    Args:
        description: Intervals description text.

    Returns:
        List of phase dicts.
    """
    phases = []
    for line in description.strip().split("\n"):
        line = line.strip().lstrip("-").strip()
        if not line:
            continue

        # Handle repetitions
        reps = 1
        if line[0].isdigit() and "x" in line.split()[0]:
            rep_str = line.split("x")[0].strip()
            if rep_str.isdigit():
                reps = int(rep_str)
                line = line.split("x", 1)[1].strip()

        # Extract duration (e.g. '10m', '5m')
        duration = 5  # default
        power = 75.0  # default
        parts = line.split()
        for i, p in enumerate(parts):
            if p.endswith("m") and p[:-1].replace(".", "").isdigit():
                duration = int(float(p[:-1]))
            if p.endswith("%"):
                try:
                    power = float(p[:-1])
                except ValueError:
                    pass

        for _ in range(reps):
            phases.append({"duration_min": duration, "power_pct": power})

    return phases if phases else [{"duration_min": 60, "power_pct": 75}]


def _find_gear_for_category(
    circuit: TerrainCircuit,
    category: GradeCategory,
) -> GearObservation | None:
    """Find the primary gear observation for a terrain category.

    Args:
        circuit: TerrainCircuit with gear profiles.
        category: Grade category to look up.

    Returns:
        Primary GearObservation or None.
    """
    for profile in circuit.gear_profiles:
        if profile.grade_category == category:
            return profile.primary_gear
    return None


def adapt_workout_to_terrain(
    workout: dict | str,
    circuit: TerrainCircuit,
    ftp_watts: int,
    *,
    athlete_weight_kg: float = 70.0,
    profil_fibres: str = "mixte",
    original_workout_name: str = "Workout",
    original_tss: int = 0,
) -> AdaptedWorkout:
    """Adapt a structured workout to a terrain circuit.

    Maps workout phases to terrain km segments based on estimated speed,
    then adjusts power, cadence, and gear recommendations per segment.

    Args:
        workout: Workout definition (dict with phases or string notation).
        circuit: TerrainCircuit to adapt to.
        ftp_watts: Athlete FTP in watts.
        athlete_weight_kg: Athlete weight in kg.
        profil_fibres: Fiber profile for cadence calculation.
        original_workout_name: Display name for the workout.
        original_tss: Original TSS estimate for delta tracking.

    Returns:
        AdaptedWorkout with per-km adapted segments.
    """
    phases = _parse_workout_phases(workout)
    if not phases:
        return AdaptedWorkout(
            workout_name=original_workout_name,
            circuit_id=circuit.circuit_id,
            circuit_name=circuit.name,
            ftp_watts=ftp_watts,
            athlete_weight_kg=athlete_weight_kg,
            warnings=["No workout phases found"],
        )

    # Build timeline: for each phase, compute total seconds
    phase_timeline = []
    for phase in phases:
        phase_timeline.append(
            {
                "duration_s": phase["duration_min"] * 60,
                "power_pct": phase["power_pct"],
                "power_watts": phase["power_pct"] / 100.0 * ftp_watts,
                "remaining_s": phase["duration_min"] * 60,
            }
        )

    # Map phases onto terrain segments
    adapted_segments = []
    warnings = []
    phase_idx = 0

    for seg in circuit.segments:
        if phase_idx >= len(phase_timeline):
            warnings.append(
                f"km {seg.km_index}: workout phases exhausted, " "remaining terrain not covered"
            )
            break

        current_phase = phase_timeline[phase_idx]
        original_power_pct = current_phase["power_pct"]
        power_watts = current_phase["power_watts"]

        # Estimate time to traverse this km segment
        speed_kmh = _estimate_speed_kmh(power_watts, seg.grade_pct, athlete_weight_kg)
        time_s = (seg.distance_m / 1000.0) / speed_kmh * 3600

        # Consume phase time
        current_phase["remaining_s"] -= time_s
        if current_phase["remaining_s"] <= 0:
            phase_idx += 1

        # Power adjustment
        adjustment = POWER_ADJUSTMENTS.get(seg.grade_category, 0.0)
        adapted_power_pct = original_power_pct + adjustment

        # Cadence from biomechanics
        zone_ftp = max(0.5, min(1.5, original_power_pct / 100.0))
        total_workout_min = sum(p["duration_min"] for p in phases)
        cadence_result = calculer_cadence_optimale(
            zone_ftp=zone_ftp,
            duree_minutes=total_workout_min,
            profil_fibres=profil_fibres,
            objectif="terrain",
        )

        # Apply terrain cadence overlay
        overlay = CADENCE_OVERLAY.get(seg.grade_category, 0)
        target_cadence = cadence_result["cadence_cible"] + overlay
        cadence_min = cadence_result["cadence_min"] + overlay
        cadence_max = cadence_result["cadence_max"] + overlay

        # Gear recommendation from circuit profiles
        recommended_gear = _find_gear_for_category(circuit, seg.grade_category)

        # Build instruction
        instruction = _build_instruction(
            seg.km_index,
            seg.grade_pct,
            seg.grade_category,
            adapted_power_pct,
            target_cadence,
            recommended_gear,
        )

        adapted_segments.append(
            AdaptedSegment(
                km_index=seg.km_index,
                terrain_grade_pct=seg.grade_pct,
                terrain_category=seg.grade_category,
                original_power_pct=original_power_pct,
                adapted_power_pct=round(adapted_power_pct, 1),
                power_adjustment_pct=adjustment,
                target_cadence_rpm=max(0, target_cadence),
                cadence_min_rpm=max(0, cadence_min),
                cadence_max_rpm=max(0, cadence_max),
                recommended_gear=recommended_gear,
                instruction=instruction,
            )
        )

    # TSS from workout phase durations — terrain changes power distribution,
    # not total effort volume. TSS = sum(duration_h * IF^2 * 100) per phase.
    estimated_tss = 0.0
    if phases:
        for phase in phases:
            duration_h = phase["duration_min"] / 60.0
            intensity_factor = phase["power_pct"] / 100.0
            estimated_tss += duration_h * intensity_factor**2 * 100
        estimated_tss = round(estimated_tss, 1)

    delta_tss = estimated_tss - original_tss if original_tss > 0 else 0

    return AdaptedWorkout(
        workout_name=original_workout_name,
        circuit_id=circuit.circuit_id,
        circuit_name=circuit.name,
        ftp_watts=ftp_watts,
        athlete_weight_kg=athlete_weight_kg,
        segments=adapted_segments,
        estimated_tss=round(estimated_tss, 1),
        original_tss=float(original_tss),
        delta_tss=round(delta_tss, 1),
        warnings=warnings,
    )


def _build_instruction(
    km_index: int,
    grade_pct: float,
    category: GradeCategory,
    adapted_power_pct: float,
    target_cadence: int,
    gear: GearObservation | None,
) -> str:
    """Build a human-readable instruction for a terrain segment.

    Args:
        km_index: Kilometer index.
        grade_pct: Grade percentage.
        category: Grade category.
        adapted_power_pct: Adapted power target.
        target_cadence: Target cadence.
        gear: Optional gear recommendation.

    Returns:
        Instruction string.
    """
    cat_labels = {
        GradeCategory.descente_raide: "Descente raide",
        GradeCategory.descente: "Descente",
        GradeCategory.faux_plat_descendant: "Faux-plat descendant",
        GradeCategory.plat: "Plat",
        GradeCategory.faux_plat_montant: "Faux-plat montant",
        GradeCategory.montee: "Montee",
        GradeCategory.montee_raide: "Montee raide",
    }

    label = cat_labels.get(category, category.value)
    parts = [
        f"km {km_index}-{km_index + 1}",
        f"{label} {grade_pct:+.1f}%",
        f"{adapted_power_pct:.0f}% FTP",
        f"{target_cadence} rpm",
    ]

    if gear:
        parts.append(f"braquet {gear.front_teeth}/{gear.rear_teeth}")

    return " | ".join(parts)
