"""Tests for terrain workout adaptation."""

import pytest

from magma_cycling.terrain.adaptation import (
    POWER_ADJUSTMENTS,
    _estimate_speed_kmh,
    _parse_workout_phases,
    adapt_workout_to_terrain,
)
from magma_cycling.terrain.models import (
    GearObservation,
    GearProfile,
    GradeCategory,
    TerrainCircuit,
    TerrainSegment,
)


def _make_circuit(
    n_km: int = 5,
    grade_pct: float = 0.0,
    gear_profiles: list | None = None,
) -> TerrainCircuit:
    """Helper: build a uniform-grade circuit."""
    category = GradeCategory.from_grade(grade_pct)
    segments = [
        TerrainSegment(
            km_index=i,
            distance_m=1000.0,
            elevation_start_m=100.0 + i * grade_pct * 10,
            elevation_end_m=100.0 + (i + 1) * grade_pct * 10,
            elevation_gain_m=max(0, grade_pct * 10),
            elevation_loss_m=max(0, -grade_pct * 10),
            grade_pct=grade_pct,
            grade_category=category,
        )
        for i in range(n_km)
    ]
    return TerrainCircuit(
        circuit_id="TC_test",
        name="Test Circuit",
        total_distance_km=float(n_km),
        total_elevation_gain_m=max(0, grade_pct * 10 * n_km),
        total_elevation_loss_m=max(0, -grade_pct * 10 * n_km),
        segments=segments,
        gear_profiles=gear_profiles or [],
    )


class TestParseWorkoutPhases:
    """_parse_workout_phases tests."""

    def test_dict_with_phases(self):
        workout = {
            "phases": [
                {"duration_min": 10, "power_pct": 65},
                {"duration_min": 20, "power_pct": 88},
            ]
        }
        phases = _parse_workout_phases(workout)
        assert len(phases) == 2
        assert phases[0]["power_pct"] == 65
        assert phases[1]["duration_min"] == 20

    def test_string_notation(self):
        phases = _parse_workout_phases("10min@65% + 3x10min@88% + 10min@55%")
        assert len(phases) == 5  # 1 + 3 + 1
        assert phases[0]["power_pct"] == 65
        assert phases[1]["power_pct"] == 88
        assert phases[4]["power_pct"] == 55

    def test_string_without_reps(self):
        phases = _parse_workout_phases("15min@70%")
        assert len(phases) == 1
        assert phases[0]["duration_min"] == 15
        assert phases[0]["power_pct"] == 70


class TestEstimateSpeed:
    """Speed estimation tests."""

    def test_flat_reasonable_speed(self):
        speed = _estimate_speed_kmh(200, 0.0, 70)
        assert 25 < speed < 40  # Reasonable flat speed at 200W

    def test_uphill_slower(self):
        speed_flat = _estimate_speed_kmh(200, 0.0, 70)
        speed_climb = _estimate_speed_kmh(200, 5.0, 70)
        assert speed_climb < speed_flat

    def test_downhill_faster(self):
        speed_flat = _estimate_speed_kmh(200, 0.0, 70)
        speed_down = _estimate_speed_kmh(200, -5.0, 70)
        assert speed_down > speed_flat

    def test_zero_power(self):
        speed = _estimate_speed_kmh(0, 0.0, 70)
        assert speed >= 5.0  # Minimum floor


class TestAdaptWorkoutToTerrain:
    """adapt_workout_to_terrain tests."""

    def test_flat_terrain_no_adjustment(self):
        """Flat terrain should not adjust power."""
        circuit = _make_circuit(5, grade_pct=0.0)
        workout = {"phases": [{"duration_min": 30, "power_pct": 88}]}

        result = adapt_workout_to_terrain(
            workout, circuit, ftp_watts=260, original_workout_name="SS Test"
        )

        assert result.workout_name == "SS Test"
        assert result.circuit_id == "TC_test"
        for seg in result.segments:
            assert seg.power_adjustment_pct == 0.0
            assert seg.adapted_power_pct == 88.0

    def test_climb_reduces_power(self):
        """Climbing terrain should reduce power."""
        circuit = _make_circuit(3, grade_pct=3.0)
        workout = {"phases": [{"duration_min": 30, "power_pct": 88}]}

        result = adapt_workout_to_terrain(workout, circuit, ftp_watts=260)

        for seg in result.segments:
            assert seg.power_adjustment_pct == POWER_ADJUSTMENTS[GradeCategory.montee]
            assert seg.adapted_power_pct < 88.0

    def test_steep_climb_adjustment(self):
        """Steep climb applies -5% adjustment."""
        circuit = _make_circuit(2, grade_pct=6.0)
        workout = {"phases": [{"duration_min": 20, "power_pct": 90}]}

        result = adapt_workout_to_terrain(workout, circuit, ftp_watts=260)

        for seg in result.segments:
            assert seg.power_adjustment_pct == -5.0
            assert seg.adapted_power_pct == 85.0

    def test_descent_reduces_power(self):
        """Descent applies -10% adjustment."""
        circuit = _make_circuit(2, grade_pct=-3.0)
        workout = {"phases": [{"duration_min": 20, "power_pct": 88}]}

        result = adapt_workout_to_terrain(workout, circuit, ftp_watts=260)

        for seg in result.segments:
            assert seg.power_adjustment_pct == -10.0
            assert seg.adapted_power_pct == 78.0

    def test_cadence_positive(self):
        """Cadence values should be positive for all segments."""
        circuit = _make_circuit(3, grade_pct=2.0)
        workout = {"phases": [{"duration_min": 30, "power_pct": 88}]}

        result = adapt_workout_to_terrain(workout, circuit, ftp_watts=260)

        for seg in result.segments:
            assert seg.target_cadence_rpm > 0
            assert seg.cadence_min_rpm <= seg.target_cadence_rpm
            assert seg.target_cadence_rpm <= seg.cadence_max_rpm

    def test_cadence_range_valid(self):
        """Cadence min <= target <= max for all segments."""
        circuit = _make_circuit(5, grade_pct=0.0)
        workout = {"phases": [{"duration_min": 60, "power_pct": 75}]}

        result = adapt_workout_to_terrain(workout, circuit, ftp_watts=260)

        for seg in result.segments:
            assert seg.cadence_min_rpm <= seg.target_cadence_rpm <= seg.cadence_max_rpm

    def test_tss_delta_tracked(self):
        """Delta TSS is computed when original_tss provided."""
        circuit = _make_circuit(5, grade_pct=0.0)
        workout = {"phases": [{"duration_min": 60, "power_pct": 88}]}

        result = adapt_workout_to_terrain(workout, circuit, ftp_watts=260, original_tss=80)

        # delta_tss should be estimated_tss - original_tss
        assert result.delta_tss == pytest.approx(result.estimated_tss - 80, abs=0.2)

    def test_gear_recommendations_from_profiles(self):
        """Gear recommendations come from circuit gear_profiles."""
        gear = GearObservation(front_teeth=34, rear_teeth=28, ratio=1.214, usage_pct=80.0)
        profile = GearProfile(
            grade_category=GradeCategory.montee,
            primary_gear=gear,
            avg_cadence_rpm=78.0,
            avg_power_watts=220.0,
        )
        circuit = _make_circuit(3, grade_pct=3.0, gear_profiles=[profile])
        workout = {"phases": [{"duration_min": 30, "power_pct": 88}]}

        result = adapt_workout_to_terrain(workout, circuit, ftp_watts=260)

        for seg in result.segments:
            assert seg.recommended_gear is not None
            assert seg.recommended_gear.front_teeth == 34
            assert seg.recommended_gear.rear_teeth == 28

    def test_no_gear_profiles(self):
        """Without gear profiles, recommended_gear is None."""
        circuit = _make_circuit(3, grade_pct=0.0)
        workout = {"phases": [{"duration_min": 30, "power_pct": 88}]}

        result = adapt_workout_to_terrain(workout, circuit, ftp_watts=260)

        for seg in result.segments:
            assert seg.recommended_gear is None

    def test_instructions_present(self):
        """Each segment has a non-empty instruction."""
        circuit = _make_circuit(3, grade_pct=2.0)
        workout = {"phases": [{"duration_min": 30, "power_pct": 88}]}

        result = adapt_workout_to_terrain(workout, circuit, ftp_watts=260)

        for seg in result.segments:
            assert seg.instruction
            assert "FTP" in seg.instruction
            assert "rpm" in seg.instruction

    def test_empty_workout(self):
        """Empty workout produces warning."""
        circuit = _make_circuit(3)
        result = adapt_workout_to_terrain({"phases": []}, circuit, ftp_watts=260)
        assert len(result.warnings) > 0
