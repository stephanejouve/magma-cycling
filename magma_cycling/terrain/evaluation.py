"""Evaluate outdoor execution against terrain-adapted workout prescription."""

from collections import Counter, defaultdict

from magma_cycling.terrain.extraction import SEGMENT_LENGTH_M, _get_stream_data
from magma_cycling.terrain.models import (
    AdaptedSegment,
    AdaptedWorkout,
    ExecutionEvaluation,
    GearObservation,
    GradeCategory,
    SegmentEvaluation,
    SegmentExecution,
)

# Descent categories excluded from compliance calculations.
# Rationale: terrain forces coasting or free-spinning on descents;
# cadence/gear discipline is not meaningful there.
_DESCENT_CATEGORIES: frozenset[GradeCategory] = frozenset(
    {GradeCategory.descente_raide, GradeCategory.descente}
)

# Grade category labels for French recommendations
_CATEGORY_LABELS: dict[GradeCategory, str] = {
    GradeCategory.descente_raide: "descente raide",
    GradeCategory.descente: "descente",
    GradeCategory.faux_plat_descendant: "faux-plat descendant",
    GradeCategory.plat: "plat",
    GradeCategory.faux_plat_montant: "faux-plat montant",
    GradeCategory.montee: "montee",
    GradeCategory.montee_raide: "montee raide",
}


def extract_execution_per_km(
    streams: list[dict],
    segment_count: int,
) -> list[SegmentExecution]:
    """Aggregate per-second activity streams into per-km execution data.

    Uses the same 1000m segment logic as terrain extraction. Computes
    average power, cadence, most-used gear, time and speed per km.

    Args:
        streams: Activity streams (list of dicts with 'type' and 'data').
        segment_count: Expected number of km segments from the prescription.

    Returns:
        List of SegmentExecution, one per km traversed.

    Raises:
        ValueError: If required distance stream is missing.
    """
    distance_data = _get_stream_data(streams, "distance")
    if not distance_data:
        raise ValueError("Streams must contain 'distance' data.")

    watts_data = _get_stream_data(streams, "watts")
    cadence_data = _get_stream_data(streams, "cadence")
    front_gear_data = _get_stream_data(streams, "FrontGear")
    rear_gear_data = _get_stream_data(streams, "RearGear")

    n_points = len(distance_data)
    has_gear = (
        front_gear_data is not None
        and rear_gear_data is not None
        and len(front_gear_data) == n_points
        and len(rear_gear_data) == n_points
    )

    # Walk through distance data, accumulating per-km buckets
    segments: list[SegmentExecution] = []
    km_index = 0
    seg_start_idx = 0
    seg_start_dist = _find_first_valid(distance_data)

    for i in range(1, n_points):
        if distance_data[i] is None:
            continue

        current_dist = distance_data[i]
        seg_distance = current_dist - seg_start_dist

        if seg_distance >= SEGMENT_LENGTH_M:
            seg = _build_execution_segment(
                km_index=km_index,
                start_idx=seg_start_idx,
                end_idx=i,
                distance_data=distance_data,
                watts_data=watts_data,
                cadence_data=cadence_data,
                front_gear_data=front_gear_data if has_gear else None,
                rear_gear_data=rear_gear_data if has_gear else None,
                seg_start_dist=seg_start_dist,
            )
            segments.append(seg)
            km_index += 1
            seg_start_idx = i
            seg_start_dist = current_dist

            if km_index >= segment_count:
                break

    # Handle last partial segment (only if we haven't reached segment_count)
    if km_index < segment_count and seg_start_idx < n_points - 1:
        last_valid_dist = _find_last_valid(distance_data)
        remaining = last_valid_dist - seg_start_dist
        if remaining > 200:
            seg = _build_execution_segment(
                km_index=km_index,
                start_idx=seg_start_idx,
                end_idx=n_points - 1,
                distance_data=distance_data,
                watts_data=watts_data,
                cadence_data=cadence_data,
                front_gear_data=front_gear_data if has_gear else None,
                rear_gear_data=rear_gear_data if has_gear else None,
                seg_start_dist=seg_start_dist,
            )
            segments.append(seg)

    return segments


def evaluate_segment(
    execution: SegmentExecution,
    prescription: AdaptedSegment,
    ftp_watts: int,
) -> SegmentEvaluation:
    """Compare one segment's execution against its prescription.

    Cadence and gear are the primary compliance criteria for outdoor
    riding. Power is computed for information but does not affect
    compliance since terrain forces power mechanically.

    Args:
        execution: Actual performance data for this km.
        prescription: Adapted prescription for this km.
        ftp_watts: Athlete FTP in watts.

    Returns:
        SegmentEvaluation with compliance verdict.
    """
    # Cadence evaluation
    cadence_delta = execution.avg_cadence_rpm - prescription.target_cadence_rpm
    cadence_in_range = (
        prescription.cadence_min_rpm <= execution.avg_cadence_rpm <= prescription.cadence_max_rpm
    )

    # Gear evaluation
    gear_match: bool | None = None
    if prescription.recommended_gear is not None and execution.actual_gear is not None:
        gear_match = (
            execution.actual_gear.front_teeth == prescription.recommended_gear.front_teeth
            and execution.actual_gear.rear_teeth == prescription.recommended_gear.rear_teeth
        )
    elif prescription.recommended_gear is None:
        gear_match = None
    else:
        # Recommendation exists but no actual gear data
        gear_match = None

    # Power (informational)
    actual_power_pct = (execution.avg_power_watts / ftp_watts * 100) if ftp_watts > 0 else 0.0
    power_delta = actual_power_pct - prescription.adapted_power_pct

    # Compliance logic
    segment_compliance = _compute_segment_compliance(
        cadence_in_range=cadence_in_range,
        cadence_min=prescription.cadence_min_rpm,
        cadence_max=prescription.cadence_max_rpm,
        actual_cadence=execution.avg_cadence_rpm,
        gear_match=gear_match,
    )

    return SegmentEvaluation(
        km_index=execution.km_index,
        terrain_category=prescription.terrain_category,
        terrain_grade_pct=prescription.terrain_grade_pct,
        target_cadence_rpm=prescription.target_cadence_rpm,
        cadence_min_rpm=prescription.cadence_min_rpm,
        cadence_max_rpm=prescription.cadence_max_rpm,
        actual_cadence_rpm=execution.avg_cadence_rpm,
        cadence_delta_rpm=round(cadence_delta, 1),
        cadence_in_range=cadence_in_range,
        recommended_gear=prescription.recommended_gear,
        actual_gear=execution.actual_gear,
        gear_match=gear_match,
        target_power_pct=prescription.adapted_power_pct,
        actual_power_pct=round(actual_power_pct, 1),
        power_delta_pct=round(power_delta, 1),
        segment_compliance=segment_compliance,
    )


def evaluate_outdoor_execution(
    streams: list[dict],
    adapted_workout: AdaptedWorkout,
    *,
    activity_id: str = "",
) -> ExecutionEvaluation:
    """Evaluate an outdoor activity against its terrain-adapted prescription.

    Orchestrates extraction, per-segment evaluation, and summary generation.

    Args:
        streams: Activity streams from the ride.
        adapted_workout: The terrain-adapted workout that was prescribed.
        activity_id: Activity ID of the realized ride.

    Returns:
        ExecutionEvaluation with per-segment details and overall verdict.
    """
    prescription_segments = adapted_workout.segments
    segment_count = len(prescription_segments)
    ftp_watts = adapted_workout.ftp_watts

    # Step 1: Extract per-km execution data
    executions = extract_execution_per_km(streams, segment_count)

    # Build lookup by km_index for prescriptions
    prescription_by_km = {seg.km_index: seg for seg in prescription_segments}

    # Step 2: Evaluate each matching segment
    evaluations: list[SegmentEvaluation] = []
    for exec_seg in executions:
        if exec_seg.km_index in prescription_by_km:
            evaluation = evaluate_segment(
                exec_seg,
                prescription_by_km[exec_seg.km_index],
                ftp_watts,
            )
            evaluations.append(evaluation)

    # Step 3: Compute summary metrics — exclude descent segments
    total = len(evaluations)
    counted = [e for e in evaluations if e.terrain_category not in _DESCENT_CATEGORIES]
    excluded = total - len(counted)

    cadence_ok = sum(1 for e in counted if e.cadence_in_range) if counted else 0
    cadence_compliance_pct = round(cadence_ok / len(counted) * 100, 1) if counted else 100.0

    gear_evaluated = [e for e in counted if e.gear_match is not None]
    gear_ok = sum(1 for e in gear_evaluated if e.gear_match)
    gear_compliance_pct = round(gear_ok / len(gear_evaluated) * 100, 1) if gear_evaluated else 100.0

    overall_compliance = _compute_overall_compliance(cadence_compliance_pct, gear_compliance_pct)

    # Step 4: Generate summary
    summary = _generate_summary(
        len(counted), cadence_ok, len(gear_evaluated), gear_ok, overall_compliance, excluded
    )

    # Step 5: Generate recommendations (only from counted segments)
    recommendations = _generate_recommendations(counted)

    return ExecutionEvaluation(
        activity_id=activity_id or adapted_workout.workout_name,
        workout_name=adapted_workout.workout_name,
        circuit_id=adapted_workout.circuit_id,
        ftp_watts=ftp_watts,
        segment_evaluations=evaluations,
        segments_evaluated=total,
        segments_excluded=excluded,
        cadence_compliance_pct=cadence_compliance_pct,
        gear_compliance_pct=gear_compliance_pct,
        overall_compliance=overall_compliance,
        summary=summary,
        recommendations=recommendations,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _find_first_valid(data: list) -> float:
    """Find the first non-None value in a list."""
    for v in data:
        if v is not None:
            return v
    return 0.0


def _find_last_valid(data: list) -> float:
    """Find the last non-None value in a list."""
    for v in reversed(data):
        if v is not None:
            return v
    return 0.0


def _build_execution_segment(
    km_index: int,
    start_idx: int,
    end_idx: int,
    distance_data: list,
    watts_data: list | None,
    cadence_data: list | None,
    front_gear_data: list | None,
    rear_gear_data: list | None,
    seg_start_dist: float,
) -> SegmentExecution:
    """Build a SegmentExecution from a slice of stream data."""
    # Distance for this segment
    end_dist = distance_data[end_idx] if distance_data[end_idx] is not None else seg_start_dist
    distance_m = end_dist - seg_start_dist

    # Time: number of seconds (1 data point per second in streams)
    time_seconds = float(end_idx - start_idx)
    if time_seconds <= 0:
        time_seconds = 1.0

    # Speed
    speed_kmh = (distance_m / time_seconds) * 3.6 if time_seconds > 0 else 1.0
    if speed_kmh <= 0:
        speed_kmh = 1.0

    # Average power (skip None and 0)
    avg_power = _compute_avg(watts_data, start_idx, end_idx)

    # Average cadence (skip None and 0)
    avg_cadence = _compute_avg(cadence_data, start_idx, end_idx)

    # Most-used gear combo
    actual_gear = _find_most_used_gear(front_gear_data, rear_gear_data, start_idx, end_idx)

    return SegmentExecution(
        km_index=km_index,
        avg_power_watts=round(avg_power, 1),
        avg_cadence_rpm=round(avg_cadence, 1),
        actual_gear=actual_gear,
        time_seconds=round(time_seconds, 1),
        speed_kmh=round(speed_kmh, 1),
    )


def _compute_avg(data: list | None, start_idx: int, end_idx: int) -> float:
    """Compute average of non-None, non-zero values in a slice."""
    if data is None:
        return 0.0
    values = []
    for i in range(start_idx, end_idx + 1):
        if i < len(data) and data[i] is not None and data[i] > 0:
            values.append(data[i])
    return sum(values) / len(values) if values else 0.0


def _find_most_used_gear(
    front_gear_data: list | None,
    rear_gear_data: list | None,
    start_idx: int,
    end_idx: int,
) -> GearObservation | None:
    """Find the most frequently used gear combo in a segment slice."""
    if front_gear_data is None or rear_gear_data is None:
        return None

    combos: Counter = Counter()
    total = 0
    for i in range(start_idx, end_idx + 1):
        if (
            i < len(front_gear_data)
            and i < len(rear_gear_data)
            and front_gear_data[i] is not None
            and rear_gear_data[i] is not None
            and front_gear_data[i] > 0
            and rear_gear_data[i] > 0
        ):
            combos[(int(front_gear_data[i]), int(rear_gear_data[i]))] += 1
            total += 1

    if not combos:
        return None

    (front, rear), count = combos.most_common(1)[0]
    usage_pct = count / total * 100 if total > 0 else 0.0

    return GearObservation(
        front_teeth=front,
        rear_teeth=rear,
        ratio=round(front / rear, 3),
        usage_pct=round(usage_pct, 1),
    )


def _compute_segment_compliance(
    cadence_in_range: bool,
    cadence_min: int,
    cadence_max: int,
    actual_cadence: float,
    gear_match: bool | None,
) -> str:
    """Determine segment compliance level.

    Args:
        cadence_in_range: Whether cadence is within prescribed min/max.
        cadence_min: Prescribed minimum cadence.
        cadence_max: Prescribed maximum cadence.
        actual_cadence: Actual cadence observed.
        gear_match: True/False/None for gear compliance.

    Returns:
        Compliance string: excellent / bon / acceptable / hors_cible.
    """
    if cadence_in_range:
        # Gear match or no gear data -> excellent
        if gear_match is True or gear_match is None:
            return "excellent"
        # Gear mismatch -> bon
        return "bon"

    # Cadence outside range: check if within +/- 5 rpm of the range bounds
    distance_below = cadence_min - actual_cadence if actual_cadence < cadence_min else 0
    distance_above = actual_cadence - cadence_max if actual_cadence > cadence_max else 0
    distance_from_range = max(distance_below, distance_above)

    if distance_from_range <= 5:
        return "acceptable"

    return "hors_cible"


def _compute_overall_compliance(
    cadence_compliance_pct: float,
    gear_compliance_pct: float,
) -> str:
    """Determine overall compliance from summary percentages.

    Args:
        cadence_compliance_pct: Percentage of segments with cadence in range.
        gear_compliance_pct: Percentage of segments with correct gear.

    Returns:
        Overall compliance: excellent / bon / acceptable / a_ameliorer.
    """
    if cadence_compliance_pct >= 90 and gear_compliance_pct >= 80:
        return "excellent"
    if cadence_compliance_pct >= 75 and gear_compliance_pct >= 60:
        return "bon"
    if cadence_compliance_pct >= 60:
        return "acceptable"
    return "a_ameliorer"


def _generate_summary(
    total: int,
    cadence_ok: int,
    gear_evaluated: int,
    gear_ok: int,
    overall: str,
    excluded: int = 0,
) -> str:
    """Generate a French summary of the evaluation.

    Args:
        total: Total counted segments (excluding descents).
        cadence_ok: Segments with cadence in range.
        gear_evaluated: Segments where gear was evaluated.
        gear_ok: Segments with correct gear.
        overall: Overall compliance level.
        excluded: Number of descent segments excluded from compliance.

    Returns:
        Human-readable summary in French.
    """
    overall_labels = {
        "excellent": "Excellent",
        "bon": "Bon",
        "acceptable": "Acceptable",
        "a_ameliorer": "A ameliorer",
    }
    label = overall_labels.get(overall, overall)

    parts = [
        f"Evaluation terrain: {cadence_ok}/{total} segments conformes en cadence",
    ]
    if excluded > 0:
        parts.append(f"{excluded} segment(s) de descente exclus")
    if gear_evaluated > 0:
        parts.append(f"{gear_ok}/{gear_evaluated} conformes en braquet")
    else:
        parts.append("pas de donnees de braquet")

    parts.append(f"Verdict global: {label}")
    return ". ".join(parts) + "."


def _generate_recommendations(
    evaluations: list[SegmentEvaluation],
) -> list[str]:
    """Generate improvement recommendations based on non-compliant segments.

    Groups failures by terrain category and generates specific advice.

    Args:
        evaluations: List of segment evaluations.

    Returns:
        List of recommendation strings in French.
    """
    if not evaluations:
        return []

    recommendations: list[str] = []

    # Group cadence failures by category
    cadence_failures_by_cat: dict[GradeCategory, list[float]] = defaultdict(list)
    gear_failures_by_cat: dict[GradeCategory, int] = defaultdict(int)

    for ev in evaluations:
        if not ev.cadence_in_range:
            cadence_failures_by_cat[ev.terrain_category].append(ev.cadence_delta_rpm)
        if ev.gear_match is False:
            gear_failures_by_cat[ev.terrain_category] += 1

    # Cadence recommendations
    for cat, deltas in cadence_failures_by_cat.items():
        label = _CATEGORY_LABELS.get(cat, cat.value)
        avg_delta = sum(deltas) / len(deltas)
        direction = "trop haute" if avg_delta > 0 else "trop basse"
        abs_delta = abs(round(avg_delta))

        if "montee" in cat.value:
            advice = "travailler la velocite en cote"
        elif "descente" in cat.value:
            advice = "maintenir le pedalage en descente"
        else:
            advice = "ajuster le rythme de pedalage"

        count = len(deltas)
        recommendations.append(
            f"Segments {label}: cadence {direction} "
            f"({int(abs_delta):+d} rpm, {count} segment(s)), {advice}"
        )

    # Gear recommendations
    for cat, count in gear_failures_by_cat.items():
        label = _CATEGORY_LABELS.get(cat, cat.value)
        recommendations.append(
            f"Segments {label}: braquet incorrect "
            f"({count} segment(s)), "
            f"revoir le choix de developpement"
        )

    return recommendations
