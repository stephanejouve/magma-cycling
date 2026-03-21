"""Extract terrain circuits from activity streams."""

from collections import defaultdict

from magma_cycling.terrain.models import (
    GearObservation,
    GearProfile,
    GradeCategory,
    TerrainCircuit,
    TerrainSegment,
)

# Segment length in meters
SEGMENT_LENGTH_M = 1000.0


def classify_grade(grade_pct: float) -> GradeCategory:
    """Classify a grade percentage into a terrain category.

    Args:
        grade_pct: Grade in percent.

    Returns:
        Matching GradeCategory.
    """
    return GradeCategory.from_grade(grade_pct)


def _get_stream_data(streams: list[dict], stream_type: str) -> list | None:
    """Extract data array for a given stream type.

    Args:
        streams: List of stream dicts with 'type' and 'data' keys.
        stream_type: Stream type name (e.g. 'altitude', 'distance').

    Returns:
        Data list or None if not found.
    """
    for s in streams:
        if s.get("type") == stream_type:
            return s.get("data")
    return None


def extract_terrain_from_streams(
    activity_id: str,
    streams: list[dict],
    *,
    activity_name: str = "",
) -> TerrainCircuit:
    """Build a TerrainCircuit from activity streams (pure logic, no API).

    Aggregates per-second streams into per-km segments. Extracts gear
    profiles if FrontGear/RearGear streams are present.

    Args:
        activity_id: Source activity ID.
        streams: List of stream dicts with 'type' and 'data' fields.
        activity_name: Optional display name for the circuit.

    Returns:
        TerrainCircuit with per-km segments and gear profiles.

    Raises:
        ValueError: If required streams (altitude, distance) are missing.
    """
    altitude_data = _get_stream_data(streams, "altitude")
    distance_data = _get_stream_data(streams, "distance")

    if not altitude_data or not distance_data:
        raise ValueError(
            "Streams must contain 'altitude' and 'distance' data. "
            f"Available: {[s.get('type') for s in streams]}"
        )

    if len(altitude_data) != len(distance_data):
        raise ValueError(
            f"altitude ({len(altitude_data)}) and distance ({len(distance_data)}) "
            "streams must have the same length"
        )

    # Optional gear streams
    front_gear_data = _get_stream_data(streams, "FrontGear")
    rear_gear_data = _get_stream_data(streams, "RearGear")
    has_gear = (
        front_gear_data is not None
        and rear_gear_data is not None
        and len(front_gear_data) == len(altitude_data)
        and len(rear_gear_data) == len(altitude_data)
    )

    # Optional cadence/power for gear profiles
    cadence_data = _get_stream_data(streams, "cadence")
    watts_data = _get_stream_data(streams, "watts")

    # Build per-km segments
    segments: list[TerrainSegment] = []
    total_gain = 0.0
    total_loss = 0.0

    # Per-category gear accumulator: category -> list of (front, rear, cadence, watts)
    gear_by_category: dict[GradeCategory, list[tuple]] = defaultdict(list)

    km_index = 0
    seg_start_idx = 0
    seg_start_dist = distance_data[0] if distance_data[0] is not None else 0.0

    for i in range(1, len(distance_data)):
        if distance_data[i] is None or altitude_data[i] is None:
            continue

        current_dist = distance_data[i]
        seg_distance = current_dist - seg_start_dist

        if seg_distance >= SEGMENT_LENGTH_M:
            # Finalize this km segment
            seg = _build_segment(
                km_index=km_index,
                altitude_data=altitude_data,
                distance_data=distance_data,
                start_idx=seg_start_idx,
                end_idx=i,
                seg_start_dist=seg_start_dist,
            )
            segments.append(seg)
            total_gain += seg.elevation_gain_m
            total_loss += seg.elevation_loss_m

            # Collect gear data for this segment's category
            if has_gear:
                _collect_gear_data(
                    gear_by_category,
                    seg.grade_category,
                    front_gear_data,
                    rear_gear_data,
                    cadence_data,
                    watts_data,
                    seg_start_idx,
                    i,
                )

            km_index += 1
            seg_start_idx = i
            seg_start_dist = current_dist

    # Handle last partial segment (if > 200m remaining)
    if seg_start_idx < len(distance_data) - 1:
        last_dist = distance_data[-1]
        if last_dist is not None:
            remaining = last_dist - seg_start_dist
            if remaining > 200:
                seg = _build_segment(
                    km_index=km_index,
                    altitude_data=altitude_data,
                    distance_data=distance_data,
                    start_idx=seg_start_idx,
                    end_idx=len(distance_data) - 1,
                    seg_start_dist=seg_start_dist,
                )
                segments.append(seg)
                total_gain += seg.elevation_gain_m
                total_loss += seg.elevation_loss_m

                if has_gear:
                    _collect_gear_data(
                        gear_by_category,
                        seg.grade_category,
                        front_gear_data,
                        rear_gear_data,
                        cadence_data,
                        watts_data,
                        seg_start_idx,
                        len(distance_data) - 1,
                    )

    # Build gear profiles
    gear_profiles = _build_gear_profiles(gear_by_category)

    total_distance = 0.0
    if distance_data[-1] is not None and distance_data[0] is not None:
        total_distance = (distance_data[-1] - distance_data[0]) / 1000.0

    return TerrainCircuit(
        circuit_id=f"TC_{activity_id}",
        name=activity_name or f"Circuit {activity_id}",
        source_type="activity",
        source_activity_id=activity_id,
        total_distance_km=round(total_distance, 2),
        total_elevation_gain_m=round(total_gain, 1),
        total_elevation_loss_m=round(total_loss, 1),
        segments=segments,
        gear_profiles=gear_profiles,
    )


def _build_segment(
    km_index: int,
    altitude_data: list,
    distance_data: list,
    start_idx: int,
    end_idx: int,
    seg_start_dist: float,
) -> TerrainSegment:
    """Build a TerrainSegment from stream slice."""
    elev_start = altitude_data[start_idx]
    elev_end = altitude_data[end_idx]
    dist = distance_data[end_idx] - seg_start_dist

    # Calculate gain/loss by walking through each point
    gain = 0.0
    loss = 0.0
    for j in range(start_idx + 1, end_idx + 1):
        if altitude_data[j] is not None and altitude_data[j - 1] is not None:
            delta = altitude_data[j] - altitude_data[j - 1]
            if delta > 0:
                gain += delta
            else:
                loss += abs(delta)

    grade = ((elev_end - elev_start) / dist * 100) if dist > 0 else 0.0

    return TerrainSegment(
        km_index=km_index,
        distance_m=round(dist, 1),
        elevation_start_m=round(elev_start, 1),
        elevation_end_m=round(elev_end, 1),
        elevation_gain_m=round(gain, 1),
        elevation_loss_m=round(loss, 1),
        grade_pct=round(grade, 2),
        grade_category=classify_grade(grade),
    )


def _collect_gear_data(
    gear_by_category: dict,
    category: GradeCategory,
    front_gear_data: list,
    rear_gear_data: list,
    cadence_data: list | None,
    watts_data: list | None,
    start_idx: int,
    end_idx: int,
) -> None:
    """Collect gear observations for a segment into the category accumulator."""
    for j in range(start_idx, end_idx + 1):
        front = front_gear_data[j]
        rear = rear_gear_data[j]
        if front is not None and rear is not None and front > 0 and rear > 0:
            cad = (
                cadence_data[j] if cadence_data and j < len(cadence_data) and cadence_data[j] else 0
            )
            pwr = watts_data[j] if watts_data and j < len(watts_data) and watts_data[j] else 0
            gear_by_category[category].append((int(front), int(rear), cad, pwr))


def _build_gear_profiles(
    gear_by_category: dict[GradeCategory, list[tuple]],
) -> list[GearProfile]:
    """Aggregate raw gear data into GearProfile objects per category."""
    profiles = []

    for category, observations in gear_by_category.items():
        if not observations:
            continue

        # Count gear combos
        combo_counts: dict[tuple[int, int], int] = defaultdict(int)
        combo_cadence: dict[tuple[int, int], list[float]] = defaultdict(list)
        combo_power: dict[tuple[int, int], list[float]] = defaultdict(list)

        for front, rear, cad, pwr in observations:
            combo_counts[(front, rear)] += 1
            if cad > 0:
                combo_cadence[(front, rear)].append(cad)
            if pwr > 0:
                combo_power[(front, rear)].append(pwr)

        total = sum(combo_counts.values())
        sorted_combos = sorted(combo_counts.items(), key=lambda x: -x[1])

        # Primary gear = most used
        primary_combo = sorted_combos[0]
        primary_front, primary_rear = primary_combo[0]
        primary_usage = primary_combo[1] / total * 100

        # Average cadence/power across all observations for this category
        all_cadences = [c for _, _, c, _ in observations if c > 0]
        all_powers = [p for _, _, _, p in observations if p > 0]
        avg_cad = sum(all_cadences) / len(all_cadences) if all_cadences else 0
        avg_pwr = sum(all_powers) / len(all_powers) if all_powers else 0

        primary_gear = GearObservation(
            front_teeth=primary_front,
            rear_teeth=primary_rear,
            ratio=round(primary_front / primary_rear, 3),
            usage_pct=round(primary_usage, 1),
        )

        alternatives = []
        for combo, count in sorted_combos[1:4]:  # Up to 3 alternatives
            front, rear = combo
            usage = count / total * 100
            if usage >= 5.0:  # Only include if >= 5% usage
                alternatives.append(
                    GearObservation(
                        front_teeth=front,
                        rear_teeth=rear,
                        ratio=round(front / rear, 3),
                        usage_pct=round(usage, 1),
                    )
                )

        profiles.append(
            GearProfile(
                grade_category=category,
                primary_gear=primary_gear,
                alternatives=alternatives,
                avg_cadence_rpm=round(avg_cad, 1),
                avg_power_watts=round(avg_pwr, 1),
            )
        )

    return profiles


def extract_terrain_from_activity(
    client,
    activity_id: str,
) -> TerrainCircuit:
    """Extract terrain circuit from an Intervals.icu activity.

    High-level wrapper: fetches activity details and streams,
    then delegates to extract_terrain_from_streams().

    Args:
        client: IntervalsClient instance.
        activity_id: Activity ID (e.g. 'i131572602').

    Returns:
        TerrainCircuit built from the activity's streams.
    """
    activity = client.get_activity(activity_id)
    streams = client.get_activity_streams(activity_id)

    activity_name = activity.get("name", "")

    return extract_terrain_from_streams(
        activity_id=activity_id,
        streams=streams,
        activity_name=activity_name,
    )
