"""Pydantic models for Withings health data.

This module defines type-safe data structures for Withings API responses
including sleep data, weight measurements, training readiness evaluations,
and health trend analysis.
"""

from datetime import date as DateType
from datetime import datetime as DateTimeType
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SleepData(BaseModel):
    """Sleep session data from Withings.

    Represents a complete sleep session with detailed sleep stage breakdowns,
    quality metrics, and disturbance indicators.

    Attributes:
        date: Sleep date (night ending, i.e., morning date)
        start_datetime: Sleep start time (ISO format)
        end_datetime: Sleep end time (ISO format)
        total_sleep_hours: Total sleep duration in hours
        deep_sleep_minutes: Deep sleep duration in minutes (optional)
        light_sleep_minutes: Light sleep duration in minutes (optional)
        rem_sleep_minutes: REM sleep duration in minutes (optional)
        sleep_score: Sleep quality score 0-100 (optional)
        wakeup_count: Number of awakenings during sleep
        wakeup_minutes: Total time awake during sleep period (optional)
        breathing_disturbances: Breathing quality indicator (optional)
    """

    date: DateType = Field(description="Sleep date (night ending)")
    start_datetime: DateTimeType = Field(description="Sleep start time")
    end_datetime: DateTimeType = Field(description="Sleep end time")
    total_sleep_hours: float = Field(ge=0, le=24, description="Total sleep duration in hours")
    deep_sleep_minutes: float | None = Field(
        default=None, ge=0, description="Deep sleep duration in minutes"
    )
    light_sleep_minutes: float | None = Field(
        default=None, ge=0, description="Light sleep duration in minutes"
    )
    rem_sleep_minutes: float | None = Field(
        default=None, ge=0, description="REM sleep duration in minutes"
    )
    sleep_score: int | None = Field(
        default=None, ge=0, le=100, description="Sleep quality score (0-100)"
    )
    wakeup_count: int = Field(ge=0, description="Number of awakenings")
    wakeup_minutes: float | None = Field(default=None, ge=0, description="Time awake during sleep")
    breathing_disturbances: int | None = Field(
        default=None, ge=0, description="Breathing disturbance count"
    )

    @field_validator("total_sleep_hours")
    @classmethod
    def validate_sleep_hours(cls, v: float) -> float:
        """Validate total sleep hours is reasonable."""
        if v > 16:
            # Log warning but don't fail - some people do sleep very long
            import logging

            logging.warning(f"Unusually long sleep duration detected: {v} hours")
        return v


class WeightMeasurement(BaseModel):
    """Weight measurement from Withings scale.

    Represents a single weight measurement with optional body composition metrics.

    Attributes:
        date: Measurement date
        datetime: Measurement timestamp (ISO format)
        weight_kg: Weight in kilograms
        fat_mass_kg: Fat mass in kg (optional, requires compatible scale)
        bone_mass_kg: Bone mass in kg (optional, requires compatible scale)
        muscle_mass_kg: Muscle mass in kg (optional, requires compatible scale)
    """

    date: DateType = Field(description="Measurement date")
    datetime: DateTimeType = Field(description="Measurement timestamp")
    weight_kg: float = Field(gt=0, description="Weight in kilograms")
    fat_mass_kg: float | None = Field(default=None, ge=0, description="Fat mass in kg")
    bone_mass_kg: float | None = Field(default=None, ge=0, description="Bone mass in kg")
    muscle_mass_kg: float | None = Field(default=None, ge=0, description="Muscle mass in kg")


class TrainingReadiness(BaseModel):
    """Training readiness evaluation based on health metrics.

    Evaluates readiness for training based on sleep quality, duration,
    and other health metrics. Provides intensity recommendations and
    veto reasons if high-intensity training should be avoided.

    Attributes:
        date: Evaluation date
        sleep_hours: Last night's sleep duration in hours
        sleep_score: Sleep quality score 0-100 (optional)
        deep_sleep_minutes: Deep sleep duration in minutes (optional)
        ready_for_intense: Boolean flag for high-intensity readiness
        recommended_intensity: Recommended training intensity level
        veto_reasons: List of reasons to avoid high intensity
        recommendations: List of training recommendations
        weight_kg: Current weight in kg (optional)
        resting_hr: Resting heart rate in bpm (optional)
    """

    date: DateType = Field(description="Evaluation date")
    sleep_hours: float = Field(ge=0, description="Last night sleep duration")
    sleep_score: int | None = Field(default=None, ge=0, le=100, description="Sleep quality score")
    deep_sleep_minutes: float | None = Field(default=None, ge=0, description="Deep sleep duration")

    ready_for_intense: bool = Field(description="Ready for high-intensity training")
    recommended_intensity: Literal[
        "recovery_only", "endurance_max", "moderate", "all_systems_go"
    ] = Field(description="Recommended training intensity")

    veto_reasons: list[str] = Field(default_factory=list, description="Reasons to avoid intensity")
    recommendations: list[str] = Field(default_factory=list, description="Training recommendations")

    weight_kg: float | None = Field(default=None, gt=0, description="Current weight")
    resting_hr: int | None = Field(default=None, gt=0, description="Resting heart rate")


class HealthTrend(BaseModel):
    """Health trend analysis over a time period.

    Aggregates health metrics over a period to identify trends, sleep debt,
    weight changes, and overall health status.

    Attributes:
        start_date: Period start date
        end_date: Period end date
        avg_sleep_hours: Average sleep per night
        avg_sleep_score: Average sleep quality score (optional)
        nights_above_7h: Count of nights with >=7h sleep
        total_nights: Total nights tracked in period
        sleep_debt_hours: Cumulative sleep debt (negative = surplus)
        weight_start_kg: Weight at period start (optional)
        weight_end_kg: Weight at period end (optional)
        weight_delta_kg: Weight change over period (optional)
        avg_resting_hr: Average resting heart rate (optional)
        status: Overall health status classification
        alerts: List of health alerts or concerns
    """

    start_date: DateType = Field(description="Period start date")
    end_date: DateType = Field(description="Period end date")

    avg_sleep_hours: float = Field(ge=0, description="Average sleep per night")
    avg_sleep_score: float | None = Field(
        default=None, ge=0, le=100, description="Average sleep score"
    )
    nights_above_7h: int = Field(ge=0, description="Nights with ≥7h sleep")
    total_nights: int = Field(gt=0, description="Total nights tracked")

    sleep_debt_hours: float = Field(description="Sleep debt (negative = surplus)")

    weight_start_kg: float | None = Field(default=None, gt=0, description="Weight at start")
    weight_end_kg: float | None = Field(default=None, gt=0, description="Weight at end")
    weight_delta_kg: float | None = Field(default=None, description="Weight change")

    avg_resting_hr: int | None = Field(default=None, gt=0, description="Average resting HR")

    status: Literal["optimal", "adequate", "debt", "critical"] = Field(
        description="Overall health status"
    )
    alerts: list[str] = Field(default_factory=list, description="Health alerts")

    @field_validator("sleep_debt_hours")
    @classmethod
    def validate_sleep_debt(cls, v: float) -> float:
        """Validate sleep debt is within reasonable bounds."""
        if abs(v) > 100:
            import logging

            logging.warning(f"Extreme sleep debt detected: {v} hours")
        return v


class HeartRateData(BaseModel):
    """Heart rate measurement from Withings.

    Represents resting heart rate and heart rate variability measurements.

    Attributes:
        date: Measurement date
        datetime: Measurement timestamp
        resting_hr: Resting heart rate in bpm
        hr_variability: Heart rate variability in ms (optional)
    """

    date: DateType = Field(description="Measurement date")
    datetime: DateTimeType = Field(description="Measurement timestamp")
    resting_hr: int = Field(gt=0, le=300, description="Resting heart rate in bpm")
    hr_variability: float | None = Field(
        default=None, ge=0, description="Heart rate variability in ms"
    )
