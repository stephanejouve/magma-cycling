"""Tests for terrain models."""

import json

import pytest

from magma_cycling.terrain.models import (
    AdaptedSegment,
    AdaptedWorkout,
    GearObservation,
    GearProfile,
    GradeCategory,
    TerrainCircuit,
    TerrainSegment,
)


class TestGradeCategory:
    """GradeCategory.from_grade() classification tests."""

    @pytest.mark.parametrize(
        "grade, expected",
        [
            (-10.0, GradeCategory.descente_raide),
            (-4.1, GradeCategory.descente_raide),
            (-4.0, GradeCategory.descente),
            (-2.0, GradeCategory.descente),
            (-1.5, GradeCategory.faux_plat_descendant),
            (-1.0, GradeCategory.faux_plat_descendant),
            (-0.5, GradeCategory.plat),
            (0.0, GradeCategory.plat),
            (0.5, GradeCategory.plat),
            (0.6, GradeCategory.faux_plat_montant),
            (1.5, GradeCategory.faux_plat_montant),
            (1.6, GradeCategory.montee),
            (4.0, GradeCategory.montee),
            (4.1, GradeCategory.montee_raide),
            (12.0, GradeCategory.montee_raide),
        ],
    )
    def test_from_grade(self, grade, expected):
        """Verify grade classification across all 7 categories and boundaries."""
        assert GradeCategory.from_grade(grade) == expected

    def test_all_categories_reachable(self):
        """Every category is reachable via from_grade."""
        grades = [-10, -3, -1, 0, 1, 3, 8]
        categories = {GradeCategory.from_grade(g) for g in grades}
        assert categories == set(GradeCategory)


class TestGearObservation:
    """GearObservation validation tests."""

    def test_valid_gear(self):
        """Valid gear observation with brand-agnostic fields only."""
        gear = GearObservation(front_teeth=34, rear_teeth=28, ratio=1.214, usage_pct=65.0)
        assert gear.front_teeth == 34
        assert gear.rear_teeth == 28
        assert gear.ratio == 1.214
        assert gear.usage_pct == 65.0

    def test_no_brand_fields(self):
        """GearObservation has no brand-specific fields."""
        fields = set(GearObservation.model_fields.keys())
        assert fields == {"front_teeth", "rear_teeth", "ratio", "usage_pct"}

    def test_invalid_teeth(self):
        """Reject zero or negative teeth count."""
        with pytest.raises(Exception):
            GearObservation(front_teeth=0, rear_teeth=28, ratio=1.0, usage_pct=50.0)

    def test_invalid_usage_pct(self):
        """Reject usage outside 0-100 range."""
        with pytest.raises(Exception):
            GearObservation(front_teeth=50, rear_teeth=11, ratio=4.5, usage_pct=101.0)


class TestTerrainCircuit:
    """TerrainCircuit roundtrip and validation."""

    @pytest.fixture
    def sample_circuit(self):
        """Build a minimal TerrainCircuit."""
        return TerrainCircuit(
            circuit_id="TC_i123456",
            name="Test Circuit",
            source_type="activity",
            source_activity_id="i123456",
            total_distance_km=5.0,
            total_elevation_gain_m=120.0,
            total_elevation_loss_m=110.0,
            segments=[
                TerrainSegment(
                    km_index=0,
                    distance_m=1000.0,
                    elevation_start_m=100.0,
                    elevation_end_m=130.0,
                    elevation_gain_m=30.0,
                    elevation_loss_m=0.0,
                    grade_pct=3.0,
                    grade_category=GradeCategory.montee,
                ),
                TerrainSegment(
                    km_index=1,
                    distance_m=1000.0,
                    elevation_start_m=130.0,
                    elevation_end_m=125.0,
                    elevation_gain_m=0.0,
                    elevation_loss_m=5.0,
                    grade_pct=-0.5,
                    grade_category=GradeCategory.plat,
                ),
            ],
            gear_profiles=[
                GearProfile(
                    grade_category=GradeCategory.montee,
                    primary_gear=GearObservation(
                        front_teeth=34, rear_teeth=28, ratio=1.214, usage_pct=70.0
                    ),
                    avg_cadence_rpm=78.0,
                    avg_power_watts=220.0,
                ),
            ],
        )

    def test_json_roundtrip(self, sample_circuit):
        """Serialize to JSON and back without data loss."""
        json_str = sample_circuit.model_dump_json()
        parsed = json.loads(json_str)
        restored = TerrainCircuit.model_validate(parsed)
        assert restored == sample_circuit

    def test_source_types(self):
        """Validate all three source types are accepted."""
        for src in ("activity", "gpx", "manual"):
            circuit = TerrainCircuit(
                circuit_id="TC_test",
                source_type=src,
                total_distance_km=1.0,
                total_elevation_gain_m=0,
                total_elevation_loss_m=0,
            )
            assert circuit.source_type == src

    def test_invalid_source_type(self):
        """Reject unknown source type."""
        with pytest.raises(Exception):
            TerrainCircuit(
                circuit_id="TC_test",
                source_type="unknown",
                total_distance_km=1.0,
                total_elevation_gain_m=0,
                total_elevation_loss_m=0,
            )


class TestAdaptedWorkout:
    """AdaptedWorkout validation tests."""

    def test_basic_adapted_workout(self):
        """Create a valid adapted workout with segments."""
        workout = AdaptedWorkout(
            workout_name="Sweet Spot Terrain",
            circuit_id="TC_i123456",
            ftp_watts=260,
            segments=[
                AdaptedSegment(
                    km_index=0,
                    terrain_grade_pct=3.0,
                    terrain_category=GradeCategory.montee,
                    original_power_pct=88.0,
                    adapted_power_pct=85.4,
                    power_adjustment_pct=-3.0,
                    target_cadence_rpm=88,
                    cadence_min_rpm=83,
                    cadence_max_rpm=93,
                    instruction="km 0-1 : Montee 3% — Sweet Spot adapte 85% FTP",
                ),
            ],
            estimated_tss=75.0,
            original_tss=80.0,
            delta_tss=-5.0,
            warnings=["Descente raide km 5: pedalage leger recommande"],
        )
        assert workout.ftp_watts == 260
        assert len(workout.segments) == 1
        assert workout.segments[0].power_adjustment_pct == -3.0
        assert workout.delta_tss == -5.0

    def test_adapted_segment_with_gear(self):
        """AdaptedSegment can include a gear recommendation."""
        gear = GearObservation(front_teeth=34, rear_teeth=28, ratio=1.214, usage_pct=70.0)
        seg = AdaptedSegment(
            km_index=2,
            terrain_grade_pct=5.5,
            terrain_category=GradeCategory.montee_raide,
            original_power_pct=88.0,
            adapted_power_pct=83.6,
            power_adjustment_pct=-5.0,
            target_cadence_rpm=85,
            cadence_min_rpm=80,
            cadence_max_rpm=90,
            recommended_gear=gear,
        )
        assert seg.recommended_gear is not None
        assert seg.recommended_gear.front_teeth == 34

    def test_adapted_segment_without_gear(self):
        """AdaptedSegment works without gear recommendation."""
        seg = AdaptedSegment(
            km_index=0,
            terrain_grade_pct=0.0,
            terrain_category=GradeCategory.plat,
            original_power_pct=88.0,
            adapted_power_pct=88.0,
            power_adjustment_pct=0.0,
            target_cadence_rpm=92,
            cadence_min_rpm=87,
            cadence_max_rpm=97,
        )
        assert seg.recommended_gear is None
