"""Pydantic v2 models for terrain circuits and adapted workouts."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class GradeCategory(str, Enum):
    """Terrain grade categories with thresholds from validated POC."""

    descente_raide = "descente_raide"
    descente = "descente"
    faux_plat_descendant = "faux_plat_descendant"
    plat = "plat"
    faux_plat_montant = "faux_plat_montant"
    montee = "montee"
    montee_raide = "montee_raide"

    @classmethod
    def from_grade(cls, grade_pct: float) -> "GradeCategory":
        """Classify a grade percentage into a category.

        Args:
            grade_pct: Grade in percent (e.g. 5.0 for 5%).

        Returns:
            Matching GradeCategory.
        """
        if grade_pct < -4.0:
            return cls.descente_raide
        if grade_pct < -1.5:
            return cls.descente
        if grade_pct < -0.5:
            return cls.faux_plat_descendant
        if grade_pct <= 0.5:
            return cls.plat
        if grade_pct <= 1.5:
            return cls.faux_plat_montant
        if grade_pct <= 4.0:
            return cls.montee
        return cls.montee_raide


class GearObservation(BaseModel):
    """Observed gear combination on a terrain segment (brand-agnostic)."""

    front_teeth: int = Field(..., ge=1, description="Front chainring teeth count")
    rear_teeth: int = Field(..., ge=1, description="Rear cog teeth count")
    ratio: float = Field(..., gt=0, description="Gear ratio (front/rear)")
    usage_pct: float = Field(..., ge=0, le=100, description="Usage percentage in segment")


class GearProfile(BaseModel):
    """Aggregated gear usage for a terrain grade category."""

    grade_category: GradeCategory
    primary_gear: GearObservation
    alternatives: list[GearObservation] = Field(default_factory=list)
    avg_cadence_rpm: float = Field(..., ge=0)
    avg_power_watts: float = Field(..., ge=0)


class TerrainSegment(BaseModel):
    """Per-km terrain segment with elevation data."""

    km_index: int = Field(..., ge=0, description="Kilometer index (0-based)")
    distance_m: float = Field(..., gt=0, description="Segment distance in meters")
    elevation_start_m: float = Field(..., description="Elevation at segment start")
    elevation_end_m: float = Field(..., description="Elevation at segment end")
    elevation_gain_m: float = Field(..., ge=0, description="Elevation gain in segment")
    elevation_loss_m: float = Field(..., ge=0, description="Elevation loss in segment")
    grade_pct: float = Field(..., description="Average grade in percent")
    grade_category: GradeCategory


class TerrainCircuit(BaseModel):
    """Complete terrain circuit extracted from activity or other source."""

    circuit_id: str = Field(..., description="Unique circuit ID (e.g. TC_i131572602)")
    name: str = Field(default="", description="Circuit display name")
    source_type: Literal["activity", "gpx", "manual"] = Field(
        default="activity", description="Data source type"
    )
    source_activity_id: str = Field(default="", description="Source activity ID if from activity")
    total_distance_km: float = Field(..., ge=0)
    total_elevation_gain_m: float = Field(..., ge=0)
    total_elevation_loss_m: float = Field(..., ge=0)
    segments: list[TerrainSegment] = Field(default_factory=list)
    gear_profiles: list[GearProfile] = Field(default_factory=list)


class AdaptedSegment(BaseModel):
    """Workout segment adapted to terrain."""

    km_index: int = Field(..., ge=0)
    terrain_grade_pct: float
    terrain_category: GradeCategory
    original_power_pct: float = Field(..., description="Original target power as %% FTP")
    adapted_power_pct: float = Field(..., description="Adapted target power as %% FTP")
    power_adjustment_pct: float = Field(
        ..., description="Power adjustment applied (negative = reduction)"
    )
    target_cadence_rpm: int = Field(..., ge=0)
    cadence_min_rpm: int = Field(..., ge=0)
    cadence_max_rpm: int = Field(..., ge=0)
    recommended_gear: GearObservation | None = Field(
        default=None, description="Recommended gear from circuit gear profiles"
    )
    instruction: str = Field(default="", description="Human-readable instruction for this segment")


class AdaptedWorkout(BaseModel):
    """Complete workout adapted to a terrain circuit."""

    workout_name: str
    circuit_id: str
    circuit_name: str = ""
    ftp_watts: int = Field(..., gt=0)
    athlete_weight_kg: float = Field(default=70.0, gt=0)
    segments: list[AdaptedSegment] = Field(default_factory=list)
    estimated_tss: float = Field(default=0, ge=0)
    original_tss: float = Field(default=0, ge=0)
    delta_tss: float = Field(default=0, description="TSS difference (estimated - original)")
    warnings: list[str] = Field(default_factory=list)
