"""Rich athlete profile fields stored in the athlete YAML (BT-017).

Hosts the pydantic models and read/write helpers for six structured
fields that extend the bundled athlete profile beyond Intervals.icu
training metrics:

* :class:`HrvBaseline` — HRV rMSSD range, fatigue alert threshold and
  athlete-specific anomalies (each documented with context — kept
  visible even when excluded from stats so the AI prompts see *why*).
* :class:`InjuryHistory` — active injuries with status + standing watch
  points (volume ramp limits, recurring weak areas).
* :class:`MacroPlan` — weekly TSS targets, CTL target and the peak event
  with a TSB target range (min/max).
* :class:`NutritionStrategy` — carbs/h range and known issues (cramps,
  GI limits) consumed by long-event briefings.
* :class:`SleepBaseline` — average sleep duration, nightly deficit and
  bedtime target.
* :class:`AvailabilityPattern` — recurring weekly slots (commute,
  cross-training, long rides) used by planning.

Each field follows the same convention as
:mod:`magma_cycling.config.objectives` : dispatched from the
``update-athlete-profile`` MCP handler, persisted under
``athlete.<field>`` of the user YAML resolved by
:func:`magma_cycling.config.data_repo.resolve_athlete_yaml_path`. The
bundled ``athlete_context.yaml`` is never touched.

Migration noop: a missing field returns ``None`` from its loader.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from magma_cycling.config._yaml_io import atomic_write_yaml, read_yaml
from magma_cycling.config.data_repo import resolve_athlete_yaml_path

__all__ = [
    "HrvAnomaly",
    "HrvBaseline",
    "Injury",
    "InjuryHistory",
    "WeeklyTssTarget",
    "PeakEvent",
    "MacroPlan",
    "NutritionStrategy",
    "SleepBaseline",
    "AvailabilitySlot",
    "AvailabilityPattern",
    "load_hrv_baseline",
    "save_hrv_baseline",
    "clear_hrv_baseline",
    "load_injury_history",
    "save_injury_history",
    "clear_injury_history",
    "load_macro_plan",
    "save_macro_plan",
    "clear_macro_plan",
    "load_nutrition_strategy",
    "save_nutrition_strategy",
    "clear_nutrition_strategy",
    "load_sleep_baseline",
    "save_sleep_baseline",
    "clear_sleep_baseline",
    "load_availability_pattern",
    "save_availability_pattern",
    "clear_availability_pattern",
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HRV baseline
# ---------------------------------------------------------------------------


class HrvAnomaly(BaseModel):
    """A documented HRV outlier with the athlete-specific context."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    date: date
    value: float = Field(gt=0, description="rMSSD value (ms)")
    context: str = Field(min_length=1, description="Why this point is an outlier")
    # Per-anomaly opt-in: the sensor works in general — exclusion is a
    # context-driven decision, not a default policy.
    exclude_from_stats: bool = Field(default=False)


class HrvBaseline(BaseModel):
    """HRV rMSSD baseline + fatigue alert threshold."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rmssd_min: float = Field(gt=0, description="Baseline minimum (ms)")
    rmssd_max: float = Field(gt=0, description="Baseline maximum (ms)")
    rmssd_peak: float | None = Field(default=None, gt=0, description="Recovery peak ceiling (ms)")
    alert_threshold: float = Field(gt=0, description="Fatigue alert threshold (ms)")
    anomalies: list[HrvAnomaly] = Field(default_factory=list)
    recovery_pattern: str | None = Field(default=None, description="Free-form pattern description")

    @model_validator(mode="after")
    def _check_range(self) -> "HrvBaseline":
        if self.rmssd_max < self.rmssd_min:
            raise ValueError("rmssd_max must be >= rmssd_min")
        if self.rmssd_peak is not None and self.rmssd_peak < self.rmssd_max:
            raise ValueError("rmssd_peak must be >= rmssd_max")
        if self.alert_threshold >= self.rmssd_min:
            raise ValueError("alert_threshold must be < rmssd_min")
        return self


# ---------------------------------------------------------------------------
# Injury history
# ---------------------------------------------------------------------------


class Injury(BaseModel):
    """A single injury entry."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    area: str = Field(min_length=1, description="Body area / structure")
    status: Literal["active", "monitoring", "healed"]
    onset_date: date | None = None
    last_followup: date | None = None
    notes: str | None = None


class InjuryHistory(BaseModel):
    """Active injuries + recurring watch points."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    active: list[Injury] = Field(default_factory=list)
    watch_points: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Macro plan
# ---------------------------------------------------------------------------


class WeeklyTssTarget(BaseModel):
    """TSS target for one week of the macro plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    week_label: str = Field(min_length=1, description="e.g. 'S003' or '2026-W25'")
    tss_target: int = Field(gt=0)
    notes: str | None = None


class PeakEvent(BaseModel):
    """The macro plan's peak event with its readiness window targets."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    date: date
    ctl_target: float | None = Field(default=None, gt=0)
    tsb_target_min: float | None = None
    tsb_target_max: float | None = None
    strategy: str | None = Field(default=None, description="Free-form race / event strategy notes")

    @model_validator(mode="after")
    def _check_tsb_range(self) -> "PeakEvent":
        if (
            self.tsb_target_min is not None
            and self.tsb_target_max is not None
            and self.tsb_target_max < self.tsb_target_min
        ):
            raise ValueError("tsb_target_max must be >= tsb_target_min")
        return self


class MacroPlan(BaseModel):
    """Macro training plan: weekly TSS + CTL target + peak event."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    weekly_tss: list[WeeklyTssTarget] = Field(default_factory=list)
    ctl_target: float | None = Field(default=None, gt=0)
    peak_event: PeakEvent | None = None


# ---------------------------------------------------------------------------
# Nutrition strategy
# ---------------------------------------------------------------------------


class NutritionStrategy(BaseModel):
    """In-event nutrition strategy and known limits."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    carbs_per_hour_min: int = Field(gt=0, description="Lower bound (g/h)")
    carbs_per_hour_max: int = Field(gt=0, description="Upper bound (g/h)")
    known_issues: list[str] = Field(default_factory=list, description="e.g. 'cramps on 4h+ rides'")

    @model_validator(mode="after")
    def _check_range(self) -> "NutritionStrategy":
        if self.carbs_per_hour_max < self.carbs_per_hour_min:
            raise ValueError("carbs_per_hour_max must be >= carbs_per_hour_min")
        return self


# ---------------------------------------------------------------------------
# Sleep baseline
# ---------------------------------------------------------------------------


class SleepBaseline(BaseModel):
    """Sleep duration baseline + nightly deficit + bedtime target."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    avg_duration_minutes: int = Field(gt=0, description="Average nightly sleep (min)")
    deficit_per_night_minutes: int = Field(ge=0, description="Nightly deficit (min)")
    bedtime_target: str | None = Field(
        default=None,
        pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
        description="HH:MM 24h",
    )


# ---------------------------------------------------------------------------
# Availability pattern
# ---------------------------------------------------------------------------


class AvailabilitySlot(BaseModel):
    """One recurring weekly slot (commute, cross-training, long ride...)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    day_of_week: Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    time_window: str = Field(
        pattern=r"^([01]\d|2[0-3]):[0-5]\d-([01]\d|2[0-3]):[0-5]\d$",
        description="HH:MM-HH:MM 24h",
    )
    activity: str = Field(min_length=1, description="e.g. 'velocommute', 'aviron'")
    typical_tss: int | None = Field(default=None, ge=0)


class AvailabilityPattern(BaseModel):
    """Recurring weekly availability — informs planning's slot allocation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    weekly_slots: list[AvailabilitySlot] = Field(default_factory=list)
    notes: str | None = None


# ---------------------------------------------------------------------------
# YAML I/O — generic helpers + per-field public wrappers
# ---------------------------------------------------------------------------


_FIELDS: dict[str, type[BaseModel]] = {
    "hrv_baseline": HrvBaseline,
    "injury_history": InjuryHistory,
    "macro_plan": MacroPlan,
    "nutrition_strategy": NutritionStrategy,
    "sleep_baseline": SleepBaseline,
    "availability_pattern": AvailabilityPattern,
}


def _load(field: str, path: Path | None) -> BaseModel | None:
    yaml_path = path or resolve_athlete_yaml_path()
    data = read_yaml(yaml_path)
    raw = (data.get("athlete") or {}).get(field)
    if not raw:
        return None
    try:
        return _FIELDS[field].model_validate(raw)
    except Exception:
        logger.warning("%s in %s failed pydantic validation; ignoring", field, yaml_path)
        return None


def _save(field: str, obj: BaseModel, path: Path | None) -> Path:
    yaml_path = path or resolve_athlete_yaml_path()
    data = read_yaml(yaml_path)
    athlete = data.get("athlete")
    if not isinstance(athlete, dict):
        athlete = {}
        data["athlete"] = athlete
    athlete[field] = obj.model_dump(mode="json", exclude_none=True)
    atomic_write_yaml(yaml_path, data)
    return yaml_path


def _clear(field: str, path: Path | None) -> Path | None:
    yaml_path = path or resolve_athlete_yaml_path()
    if not yaml_path.exists():
        return None
    data = read_yaml(yaml_path)
    athlete = data.get("athlete")
    if not isinstance(athlete, dict) or field not in athlete:
        return None
    athlete.pop(field, None)
    atomic_write_yaml(yaml_path, data)
    return yaml_path


def load_hrv_baseline(path: Path | None = None) -> HrvBaseline | None:
    """Read ``athlete.hrv_baseline`` from the user YAML."""
    return _load("hrv_baseline", path)  # type: ignore[return-value]


def save_hrv_baseline(obj: HrvBaseline, path: Path | None = None) -> Path:
    """Persist ``obj`` under ``athlete.hrv_baseline``."""
    return _save("hrv_baseline", obj, path)


def clear_hrv_baseline(path: Path | None = None) -> Path | None:
    """Remove ``athlete.hrv_baseline`` if present."""
    return _clear("hrv_baseline", path)


def load_injury_history(path: Path | None = None) -> InjuryHistory | None:
    """Read ``athlete.injury_history`` from the user YAML."""
    return _load("injury_history", path)  # type: ignore[return-value]


def save_injury_history(obj: InjuryHistory, path: Path | None = None) -> Path:
    """Persist ``obj`` under ``athlete.injury_history``."""
    return _save("injury_history", obj, path)


def clear_injury_history(path: Path | None = None) -> Path | None:
    """Remove ``athlete.injury_history`` if present."""
    return _clear("injury_history", path)


def load_macro_plan(path: Path | None = None) -> MacroPlan | None:
    """Read ``athlete.macro_plan`` from the user YAML."""
    return _load("macro_plan", path)  # type: ignore[return-value]


def save_macro_plan(obj: MacroPlan, path: Path | None = None) -> Path:
    """Persist ``obj`` under ``athlete.macro_plan``."""
    return _save("macro_plan", obj, path)


def clear_macro_plan(path: Path | None = None) -> Path | None:
    """Remove ``athlete.macro_plan`` if present."""
    return _clear("macro_plan", path)


def load_nutrition_strategy(path: Path | None = None) -> NutritionStrategy | None:
    """Read ``athlete.nutrition_strategy`` from the user YAML."""
    return _load("nutrition_strategy", path)  # type: ignore[return-value]


def save_nutrition_strategy(obj: NutritionStrategy, path: Path | None = None) -> Path:
    """Persist ``obj`` under ``athlete.nutrition_strategy``."""
    return _save("nutrition_strategy", obj, path)


def clear_nutrition_strategy(path: Path | None = None) -> Path | None:
    """Remove ``athlete.nutrition_strategy`` if present."""
    return _clear("nutrition_strategy", path)


def load_sleep_baseline(path: Path | None = None) -> SleepBaseline | None:
    """Read ``athlete.sleep_baseline`` from the user YAML."""
    return _load("sleep_baseline", path)  # type: ignore[return-value]


def save_sleep_baseline(obj: SleepBaseline, path: Path | None = None) -> Path:
    """Persist ``obj`` under ``athlete.sleep_baseline``."""
    return _save("sleep_baseline", obj, path)


def clear_sleep_baseline(path: Path | None = None) -> Path | None:
    """Remove ``athlete.sleep_baseline`` if present."""
    return _clear("sleep_baseline", path)


def load_availability_pattern(
    path: Path | None = None,
) -> AvailabilityPattern | None:
    """Read ``athlete.availability_pattern`` from the user YAML."""
    return _load("availability_pattern", path)  # type: ignore[return-value]


def save_availability_pattern(obj: AvailabilityPattern, path: Path | None = None) -> Path:
    """Persist ``obj`` under ``athlete.availability_pattern``."""
    return _save("availability_pattern", obj, path)


def clear_availability_pattern(path: Path | None = None) -> Path | None:
    """Remove ``athlete.availability_pattern`` if present."""
    return _clear("availability_pattern", path)
