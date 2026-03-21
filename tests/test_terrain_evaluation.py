"""Tests for terrain outdoor execution evaluation."""

import pytest

from magma_cycling.terrain.evaluation import (
    evaluate_outdoor_execution,
    evaluate_segment,
    extract_execution_per_km,
)
from magma_cycling.terrain.models import (
    AdaptedSegment,
    AdaptedWorkout,
    GearObservation,
    GradeCategory,
    SegmentExecution,
)

# ---------------------------------------------------------------------------
# Stream helpers
# ---------------------------------------------------------------------------

FTP_WATTS = 260


def _make_streams(
    n_km: int = 3,
    points_per_km: int = 100,
    watts: float = 200.0,
    cadence: float = 90.0,
    front_gear: int | None = None,
    rear_gear: int | None = None,
) -> list[dict]:
    """Generate synthetic activity streams for testing.

    Each data point represents 1 second. Distance increases linearly
    at ``points_per_km`` points per 1000 m.

    Args:
        n_km: Number of kilometres to simulate.
        points_per_km: Data points per km (controls resolution).
        watts: Constant power value.
        cadence: Constant cadence value.
        front_gear: If set, include FrontGear stream.
        rear_gear: If set, include RearGear stream.

    Returns:
        List of stream dicts with 'type' and 'data' keys.
    """
    n_points = n_km * points_per_km
    step_m = 1000.0 / points_per_km

    distance = [i * step_m for i in range(n_points)]
    watts_data = [watts] * n_points
    cadence_data = [cadence] * n_points

    streams = [
        {"type": "distance", "data": distance},
        {"type": "watts", "data": watts_data},
        {"type": "cadence", "data": cadence_data},
    ]

    if front_gear is not None and rear_gear is not None:
        streams.append({"type": "FrontGear", "data": [front_gear] * n_points})
        streams.append({"type": "RearGear", "data": [rear_gear] * n_points})

    return streams


def _make_adapted_segment(
    km_index: int = 0,
    grade_pct: float = 0.0,
    category: GradeCategory = GradeCategory.plat,
    adapted_power_pct: float = 88.0,
    target_cadence: int = 90,
    cadence_min: int = 85,
    cadence_max: int = 95,
    recommended_gear: GearObservation | None = None,
) -> AdaptedSegment:
    """Build an AdaptedSegment with sensible defaults."""
    return AdaptedSegment(
        km_index=km_index,
        terrain_grade_pct=grade_pct,
        terrain_category=category,
        original_power_pct=88.0,
        adapted_power_pct=adapted_power_pct,
        power_adjustment_pct=0.0,
        target_cadence_rpm=target_cadence,
        cadence_min_rpm=cadence_min,
        cadence_max_rpm=cadence_max,
        recommended_gear=recommended_gear,
    )


def _make_adapted_workout(
    segments: list[AdaptedSegment] | None = None,
    ftp: int = FTP_WATTS,
    name: str = "Test Workout",
    circuit_id: str = "TC_test",
) -> AdaptedWorkout:
    """Build an AdaptedWorkout with sensible defaults."""
    if segments is None:
        segments = [_make_adapted_segment(km_index=i) for i in range(3)]
    return AdaptedWorkout(
        workout_name=name,
        circuit_id=circuit_id,
        ftp_watts=ftp,
        segments=segments,
    )


def _make_gear(front: int = 50, rear: int = 17) -> GearObservation:
    """Build a GearObservation helper."""
    return GearObservation(
        front_teeth=front,
        rear_teeth=rear,
        ratio=round(front / rear, 3),
        usage_pct=100.0,
    )


# ---------------------------------------------------------------------------
# TestExtractExecutionPerKm
# ---------------------------------------------------------------------------


class TestExtractExecutionPerKm:
    """Tests for extract_execution_per_km."""

    def test_basic_3km_flat(self):
        """3 km flat streams produce 3 SegmentExecution objects."""
        streams = _make_streams(n_km=3, watts=200.0, cadence=90.0)
        result = extract_execution_per_km(streams, segment_count=3)

        assert len(result) == 3
        for i, seg in enumerate(result):
            assert seg.km_index == i
            assert seg.avg_power_watts == pytest.approx(200.0, abs=1)
            assert seg.avg_cadence_rpm == pytest.approx(90.0, abs=1)
            assert seg.time_seconds > 0
            assert seg.speed_kmh > 0

    def test_with_gear_data(self):
        """Streams with FrontGear/RearGear populate actual_gear."""
        streams = _make_streams(n_km=2, watts=200.0, cadence=88.0, front_gear=50, rear_gear=17)
        result = extract_execution_per_km(streams, segment_count=2)

        assert len(result) == 2
        for seg in result:
            assert seg.actual_gear is not None
            assert seg.actual_gear.front_teeth == 50
            assert seg.actual_gear.rear_teeth == 17
            assert seg.actual_gear.ratio == pytest.approx(50 / 17, abs=0.01)

    def test_without_gear_data(self):
        """Streams without gear data leave actual_gear as None."""
        streams = _make_streams(n_km=2, watts=200.0, cadence=88.0)
        result = extract_execution_per_km(streams, segment_count=2)

        for seg in result:
            assert seg.actual_gear is None

    def test_none_values_skipped(self):
        """None values in cadence/power are skipped in averages."""
        streams = _make_streams(n_km=1, points_per_km=200, watts=200.0, cadence=90.0)
        # Inject some None values into watts and cadence
        watts_data = streams[1]["data"]
        cadence_data = streams[2]["data"]
        for i in range(0, 50):
            watts_data[i] = None
            cadence_data[i] = None

        result = extract_execution_per_km(streams, segment_count=1)

        assert len(result) == 1
        # Averages should still be based on non-None values
        assert result[0].avg_power_watts == pytest.approx(200.0, abs=1)
        assert result[0].avg_cadence_rpm == pytest.approx(90.0, abs=1)

    def test_partial_last_segment(self):
        """Last segment < 1km but > 200m is included."""
        # 2.5 km of data, requesting 3 segments
        streams = _make_streams(n_km=3, points_per_km=100, watts=180.0, cadence=85.0)
        # Truncate to ~2500m (250 points)
        for s in streams:
            s["data"] = s["data"][:250]

        result = extract_execution_per_km(streams, segment_count=3)

        # Should get 2 full km + 1 partial (500m > 200m threshold)
        assert len(result) == 3
        assert result[0].km_index == 0
        assert result[1].km_index == 1
        assert result[2].km_index == 2

    def test_missing_distance_raises(self):
        """Missing distance stream raises ValueError."""
        streams = [{"type": "watts", "data": [200] * 100}]
        with pytest.raises(ValueError, match="distance"):
            extract_execution_per_km(streams, segment_count=1)


# ---------------------------------------------------------------------------
# TestEvaluateSegment
# ---------------------------------------------------------------------------


class TestEvaluateSegment:
    """Tests for evaluate_segment."""

    def test_cadence_in_range_excellent(self):
        """Cadence in range + gear match results in excellent."""
        gear = _make_gear(50, 17)
        execution = SegmentExecution(
            km_index=0,
            avg_power_watts=228.0,
            avg_cadence_rpm=90.0,
            actual_gear=gear,
            time_seconds=120.0,
            speed_kmh=30.0,
        )
        prescription = _make_adapted_segment(
            km_index=0,
            target_cadence=90,
            cadence_min=85,
            cadence_max=95,
            recommended_gear=gear,
        )

        result = evaluate_segment(execution, prescription, FTP_WATTS)

        assert result.cadence_in_range is True
        assert result.gear_match is True
        assert result.segment_compliance == "excellent"
        assert result.cadence_delta_rpm == pytest.approx(0.0)

    def test_cadence_in_range_no_gear(self):
        """Cadence in range, no gear data results in excellent."""
        execution = SegmentExecution(
            km_index=0,
            avg_power_watts=200.0,
            avg_cadence_rpm=92.0,
            actual_gear=None,
            time_seconds=120.0,
            speed_kmh=30.0,
        )
        prescription = _make_adapted_segment(
            km_index=0,
            target_cadence=90,
            cadence_min=85,
            cadence_max=95,
            recommended_gear=None,
        )

        result = evaluate_segment(execution, prescription, FTP_WATTS)

        assert result.cadence_in_range is True
        assert result.gear_match is None
        assert result.segment_compliance == "excellent"

    def test_cadence_in_range_gear_mismatch(self):
        """Cadence in range, wrong gear results in bon."""
        actual_gear = _make_gear(50, 17)
        recommended_gear = _make_gear(34, 28)

        execution = SegmentExecution(
            km_index=0,
            avg_power_watts=220.0,
            avg_cadence_rpm=90.0,
            actual_gear=actual_gear,
            time_seconds=120.0,
            speed_kmh=30.0,
        )
        prescription = _make_adapted_segment(
            km_index=0,
            target_cadence=90,
            cadence_min=85,
            cadence_max=95,
            recommended_gear=recommended_gear,
        )

        result = evaluate_segment(execution, prescription, FTP_WATTS)

        assert result.cadence_in_range is True
        assert result.gear_match is False
        assert result.segment_compliance == "bon"

    def test_cadence_near_range(self):
        """Cadence within +/-5 rpm of range results in acceptable."""
        execution = SegmentExecution(
            km_index=0,
            avg_power_watts=200.0,
            avg_cadence_rpm=80.0,  # 5 rpm below min of 85
            actual_gear=None,
            time_seconds=120.0,
            speed_kmh=30.0,
        )
        prescription = _make_adapted_segment(
            km_index=0,
            target_cadence=90,
            cadence_min=85,
            cadence_max=95,
        )

        result = evaluate_segment(execution, prescription, FTP_WATTS)

        assert result.cadence_in_range is False
        assert result.segment_compliance == "acceptable"

    def test_cadence_far_from_range(self):
        """Cadence >5 rpm outside range results in hors_cible."""
        execution = SegmentExecution(
            km_index=0,
            avg_power_watts=200.0,
            avg_cadence_rpm=70.0,  # 15 rpm below min of 85
            actual_gear=None,
            time_seconds=120.0,
            speed_kmh=30.0,
        )
        prescription = _make_adapted_segment(
            km_index=0,
            target_cadence=90,
            cadence_min=85,
            cadence_max=95,
        )

        result = evaluate_segment(execution, prescription, FTP_WATTS)

        assert result.cadence_in_range is False
        assert result.segment_compliance == "hors_cible"

    def test_power_informational(self):
        """Power delta is computed but does not affect compliance."""
        execution = SegmentExecution(
            km_index=0,
            avg_power_watts=130.0,  # 50% FTP -- very low
            avg_cadence_rpm=90.0,  # In range
            actual_gear=None,
            time_seconds=120.0,
            speed_kmh=30.0,
        )
        prescription = _make_adapted_segment(
            km_index=0,
            adapted_power_pct=88.0,
            target_cadence=90,
            cadence_min=85,
            cadence_max=95,
        )

        result = evaluate_segment(execution, prescription, FTP_WATTS)

        # Power is way off but cadence is fine -> still excellent
        assert result.segment_compliance == "excellent"
        assert result.actual_power_pct == pytest.approx(50.0, abs=0.5)
        assert result.power_delta_pct < 0  # Below target


# ---------------------------------------------------------------------------
# TestEvaluateOutdoorExecution
# ---------------------------------------------------------------------------


class TestEvaluateOutdoorExecution:
    """Tests for evaluate_outdoor_execution."""

    def test_all_segments_excellent(self):
        """All segments compliant results in overall excellent."""
        streams = _make_streams(n_km=3, watts=228.0, cadence=90.0, front_gear=50, rear_gear=17)
        gear = _make_gear(50, 17)
        segments = [
            _make_adapted_segment(
                km_index=i,
                target_cadence=90,
                cadence_min=85,
                cadence_max=95,
                recommended_gear=gear,
            )
            for i in range(3)
        ]
        workout = _make_adapted_workout(segments=segments)

        result = evaluate_outdoor_execution(streams, workout)

        assert result.segments_evaluated == 3
        assert result.cadence_compliance_pct == 100.0
        assert result.gear_compliance_pct == 100.0
        assert result.overall_compliance == "excellent"
        assert "Excellent" in result.summary

    def test_mixed_compliance(self):
        """Mix of compliant/non-compliant gives appropriate overall."""
        n_km = 4
        points_per_km = 100
        n_points = n_km * points_per_km
        step_m = 1000.0 / points_per_km

        distance = [i * step_m for i in range(n_points)]
        watts_data = [200.0] * n_points
        # First 2 km: cadence 90 (in range), last 2 km: cadence 70 (out)
        cadence_data = [90.0] * (2 * points_per_km) + [70.0] * (2 * points_per_km)

        streams = [
            {"type": "distance", "data": distance},
            {"type": "watts", "data": watts_data},
            {"type": "cadence", "data": cadence_data},
        ]

        segments = [
            _make_adapted_segment(
                km_index=i,
                target_cadence=90,
                cadence_min=85,
                cadence_max=95,
            )
            for i in range(4)
        ]
        workout = _make_adapted_workout(segments=segments)

        result = evaluate_outdoor_execution(streams, workout)

        assert result.segments_evaluated == 4
        assert result.cadence_compliance_pct == 50.0
        # 50% < 60% -> a_ameliorer
        assert result.overall_compliance == "a_ameliorer"

    def test_fewer_execution_segments(self):
        """Fewer execution km than prescription gives partial evaluation."""
        streams = _make_streams(n_km=2, watts=200.0, cadence=90.0)
        segments = [_make_adapted_segment(km_index=i) for i in range(4)]
        workout = _make_adapted_workout(segments=segments)

        result = evaluate_outdoor_execution(streams, workout)

        assert result.segments_evaluated == 2
        assert len(result.segment_evaluations) == 2

    def test_recommendations_generated(self):
        """Non-compliant segments generate specific recommendations."""
        streams = _make_streams(n_km=3, watts=200.0, cadence=70.0)
        segments = [
            _make_adapted_segment(
                km_index=i,
                grade_pct=5.0,
                category=GradeCategory.montee,
                target_cadence=90,
                cadence_min=85,
                cadence_max=95,
            )
            for i in range(3)
        ]
        workout = _make_adapted_workout(segments=segments)

        result = evaluate_outdoor_execution(streams, workout)

        assert len(result.recommendations) > 0
        recs_text = " ".join(result.recommendations)
        assert "montee" in recs_text.lower()
        assert "cadence" in recs_text.lower()

    def test_no_gear_data_100pct_compliance(self):
        """No gear data results in gear_compliance_pct = 100%."""
        streams = _make_streams(n_km=3, watts=200.0, cadence=90.0)
        segments = [_make_adapted_segment(km_index=i) for i in range(3)]
        workout = _make_adapted_workout(segments=segments)

        result = evaluate_outdoor_execution(streams, workout)

        assert result.gear_compliance_pct == 100.0

    def test_overall_thresholds_bon(self):
        """Test bon threshold: cadence >= 75% and gear >= 60%."""
        n_km = 4
        points_per_km = 100
        n_points = n_km * points_per_km
        step_m = 1000.0 / points_per_km

        distance = [i * step_m for i in range(n_points)]
        watts_data = [200.0] * n_points
        cadence_data = [90.0] * (3 * points_per_km) + [70.0] * points_per_km

        streams = [
            {"type": "distance", "data": distance},
            {"type": "watts", "data": watts_data},
            {"type": "cadence", "data": cadence_data},
        ]

        segments = [
            _make_adapted_segment(
                km_index=i,
                target_cadence=90,
                cadence_min=85,
                cadence_max=95,
            )
            for i in range(4)
        ]
        workout = _make_adapted_workout(segments=segments)

        result = evaluate_outdoor_execution(streams, workout)

        assert result.cadence_compliance_pct == 75.0
        assert result.overall_compliance == "bon"

    def test_overall_thresholds_acceptable(self):
        """Test acceptable threshold: cadence >= 60%."""
        n_km = 5
        points_per_km = 100
        n_points = n_km * points_per_km
        step_m = 1000.0 / points_per_km

        distance = [i * step_m for i in range(n_points)]
        watts_data = [200.0] * n_points
        cadence_data = [90.0] * (3 * points_per_km) + [70.0] * (2 * points_per_km)

        streams = [
            {"type": "distance", "data": distance},
            {"type": "watts", "data": watts_data},
            {"type": "cadence", "data": cadence_data},
        ]

        segments = [
            _make_adapted_segment(
                km_index=i,
                target_cadence=90,
                cadence_min=85,
                cadence_max=95,
            )
            for i in range(5)
        ]
        workout = _make_adapted_workout(segments=segments)

        result = evaluate_outdoor_execution(streams, workout)

        assert result.cadence_compliance_pct == 60.0
        assert result.overall_compliance == "acceptable"

    def test_overall_thresholds_a_ameliorer(self):
        """Test a_ameliorer threshold: cadence < 60%."""
        n_km = 5
        points_per_km = 100
        n_points = n_km * points_per_km
        step_m = 1000.0 / points_per_km

        distance = [i * step_m for i in range(n_points)]
        watts_data = [200.0] * n_points
        cadence_data = [90.0] * (2 * points_per_km) + [70.0] * (3 * points_per_km)

        streams = [
            {"type": "distance", "data": distance},
            {"type": "watts", "data": watts_data},
            {"type": "cadence", "data": cadence_data},
        ]

        segments = [
            _make_adapted_segment(
                km_index=i,
                target_cadence=90,
                cadence_min=85,
                cadence_max=95,
            )
            for i in range(5)
        ]
        workout = _make_adapted_workout(segments=segments)

        result = evaluate_outdoor_execution(streams, workout)

        assert result.cadence_compliance_pct == 40.0
        assert result.overall_compliance == "a_ameliorer"

    def test_summary_in_french(self):
        """Summary is generated in French."""
        streams = _make_streams(n_km=2, watts=200.0, cadence=90.0)
        segments = [_make_adapted_segment(km_index=i) for i in range(2)]
        workout = _make_adapted_workout(segments=segments)

        result = evaluate_outdoor_execution(streams, workout)

        assert "Evaluation terrain" in result.summary
        assert "Verdict global" in result.summary

    def test_gear_recommendations_generated(self):
        """Gear mismatches generate gear-specific recommendations."""
        recommended = _make_gear(34, 28)
        actual_gear_front = 50
        actual_gear_rear = 17

        streams = _make_streams(
            n_km=3,
            watts=200.0,
            cadence=90.0,
            front_gear=actual_gear_front,
            rear_gear=actual_gear_rear,
        )
        segments = [
            _make_adapted_segment(
                km_index=i,
                target_cadence=90,
                cadence_min=85,
                cadence_max=95,
                recommended_gear=recommended,
            )
            for i in range(3)
        ]
        workout = _make_adapted_workout(segments=segments)

        result = evaluate_outdoor_execution(streams, workout)

        recs_text = " ".join(result.recommendations)
        assert "braquet" in recs_text.lower()
