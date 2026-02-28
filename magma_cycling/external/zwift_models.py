"""Pydantic models for Zwift workout data structures."""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ZwiftCategory(str, Enum):
    """Zwift workout categories (maps to our session types)."""

    FTP = "FTP"
    INTERVALS = "Intervals"
    VO2MAX = "VO2 Max"
    THRESHOLD = "Threshold"
    ENDURANCE = "Endurance"
    RECOVERY = "Recovery"
    SPRINT = "Sprint"
    CLIMBING = "Climbing"
    MIXED = "Mixed"
    TEMPO = "Tempo"

    @staticmethod
    def to_session_type(category: "ZwiftCategory") -> str:
        """Map Zwift category to our 3-letter session type codes."""
        mapping = {
            ZwiftCategory.FTP: "FTP",
            ZwiftCategory.INTERVALS: "INT",
            ZwiftCategory.VO2MAX: "INT",  # High-intensity intervals
            ZwiftCategory.THRESHOLD: "FTP",
            ZwiftCategory.ENDURANCE: "END",
            ZwiftCategory.RECOVERY: "REC",
            ZwiftCategory.SPRINT: "SPR",
            ZwiftCategory.CLIMBING: "CLM",
            ZwiftCategory.MIXED: "MIX",
            ZwiftCategory.TEMPO: "END",  # Tempo often maps to endurance
        }
        return mapping.get(category, "MIX")


class SegmentType(str, Enum):
    """Types of workout segments."""

    WARMUP = "warmup"
    COOLDOWN = "cooldown"
    STEADY = "steady"
    INTERVAL = "interval"
    RECOVERY = "recovery"
    RAMP = "ramp"
    FREE_RIDE = "free_ride"  # ALL-OUT segments


class ZwiftWorkoutSegment(BaseModel):
    """Individual segment within a Zwift workout."""

    segment_type: SegmentType
    duration_seconds: int = Field(gt=0, description="Segment duration in seconds")
    power_low: int | None = Field(None, ge=0, le=500, description="Lower power % FTP")
    power_high: int | None = Field(None, ge=0, le=500, description="Upper power % FTP (for ramps)")
    cadence: int | None = Field(None, ge=0, le=200, description="Target cadence RPM")
    description: str | None = Field(None, description="Segment description")
    repeat_count: int = Field(1, ge=1, description="Number of repetitions")

    # Note: power_high can be < power_low for cooldown ramps (descending power)
    # No validation needed - both ascending and descending ramps are valid

    def to_duration_str(self) -> str:
        """Convert duration to human-readable string (e.g., '10m', '30s')."""
        if self.duration_seconds >= 60:
            minutes = self.duration_seconds // 60
            seconds = self.duration_seconds % 60
            if seconds > 0:
                return f"{minutes}m{seconds}s"
            return f"{minutes}m"
        return f"{self.duration_seconds}s"

    def to_intervals_format(self) -> str:
        """Convert segment to Intervals.icu text format with explicit power."""
        duration = self.to_duration_str()

        # Handle ramps
        if self.segment_type == SegmentType.RAMP and self.power_low and self.power_high:
            cadence_str = f" {self.cadence}rpm" if self.cadence else ""
            return f"- {duration} ramp {self.power_low}-{self.power_high}%{cadence_str}"

        # Handle free ride (ALL-OUT) segments - use power_low as target
        if self.segment_type == SegmentType.FREE_RIDE:
            power = self.power_low or 100
            cadence_str = f" {self.cadence}rpm" if self.cadence else ""
            desc = f" {self.description}" if self.description else ""
            return f"- {duration} {power}% ALL-OUT{cadence_str}{desc}"

        # Standard segments with explicit power
        power = self.power_low or 100
        cadence_str = f" {self.cadence}rpm" if self.cadence else ""
        desc = f" {self.description}" if self.description else ""
        return f"- {duration} {power}%{cadence_str}{desc}"


class ZwiftWorkout(BaseModel):
    """Complete Zwift workout with metadata and segments."""

    name: str = Field(..., min_length=1, description="Workout name")
    category: ZwiftCategory
    duration_minutes: int = Field(gt=0, description="Total duration in minutes")
    tss: int = Field(ge=0, le=500, description="Training Stress Score")
    url: str = Field(..., description="Source URL from whatsonzwift.com")
    description: str | None = Field(None, description="Workout overview")
    segments: list[ZwiftWorkoutSegment] = Field(default_factory=list)

    # Metadata for matching and diversity tracking
    source: str = Field("whatsonzwift.com", description="Data source")
    last_used_date: str | None = Field(None, description="ISO date when last used (YYYY-MM-DD)")
    usage_count: int = Field(0, ge=0, description="Number of times used in planning")

    def calculate_total_duration(self) -> int:
        """Calculate total workout duration from segments in seconds."""
        return sum(seg.duration_seconds * seg.repeat_count for seg in self.segments)

    def to_intervals_description(self) -> str:
        """Convert entire workout to Intervals.icu text description format."""
        lines = []

        # Header
        lines.append(f"{self.name} ({self.duration_minutes}min, {self.tss} TSS)")
        lines.append("")

        # Group segments by type for cleaner output
        current_group = None
        for seg in self.segments:
            # Add group headers for clarity
            if seg.segment_type != current_group:
                group_name = seg.segment_type.value.replace("_", " ").title()
                if seg.segment_type in (SegmentType.WARMUP, SegmentType.COOLDOWN):
                    lines.append(f"\n{group_name}")
                elif seg.repeat_count > 1:
                    lines.append(f"\n{group_name} {seg.repeat_count}x")
                current_group = seg.segment_type

            lines.append(seg.to_intervals_format())

        return "\n".join(lines)

    def matches_criteria(self, criteria: "WorkoutSearchCriteria") -> bool:
        """Check if workout matches search criteria."""
        # TSS match (with tolerance)
        if criteria.tss_target:
            tss_tolerance = criteria.tss_tolerance or 15
            if abs(self.tss - criteria.tss_target) > tss_tolerance:
                return False

        # Duration match (if specified)
        if criteria.duration_min and self.duration_minutes < criteria.duration_min:
            return False
        if criteria.duration_max and self.duration_minutes > criteria.duration_max:
            return False

        # Category match
        if criteria.session_type:
            if ZwiftCategory.to_session_type(self.category) != criteria.session_type:
                return False

        return True


class WorkoutSearchCriteria(BaseModel):
    """Search criteria for finding Zwift workouts."""

    session_type: str = Field(..., description="3-letter session type (END, INT, FTP, etc.)")
    tss_target: int = Field(..., ge=0, le=500, description="Target TSS")
    tss_tolerance: int = Field(15, ge=0, le=100, description="TSS tolerance ±%")
    duration_min: int | None = Field(None, ge=0, description="Minimum duration in minutes")
    duration_max: int | None = Field(None, ge=0, description="Maximum duration in minutes")
    exclude_recent: bool = Field(True, description="Exclude workouts used in last 21 days")
    diversity_window_days: int = Field(21, ge=0, description="Days to check for workout diversity")

    @field_validator("session_type")
    @classmethod
    def validate_session_type(cls, v):
        """Validate session type is one of the 12 valid codes."""
        valid_types = {
            "END",
            "INT",
            "FTP",
            "SPR",
            "CLM",
            "REC",
            "FOR",
            "CAD",
            "TEC",
            "MIX",
            "PDC",
            "TST",
        }
        if v not in valid_types:
            raise ValueError(f"Invalid session type: {v}. Must be one of {valid_types}")
        return v

    @field_validator("duration_max")
    @classmethod
    def validate_duration_max(cls, v, info):
        """Ensure duration_max >= duration_min."""
        if v is not None and info.data.get("duration_min") is not None:
            if v < info.data["duration_min"]:
                raise ValueError("duration_max must be >= duration_min")
        return v


class WorkoutMatch(BaseModel):
    """A matched workout with relevance score."""

    workout: ZwiftWorkout
    score: float = Field(ge=0.0, le=100.0, description="Match quality score (0-100)")
    tss_delta: int = Field(description="Difference from target TSS")
    type_match: bool = Field(description="Exact session type match")
    recently_used: bool = Field(description="Used within diversity window")

    class Config:
        """Pydantic config."""

        frozen = False  # Allow modifications
