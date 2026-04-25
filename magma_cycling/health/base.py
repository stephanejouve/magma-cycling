"""Abstract base class for health data providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any

from magma_cycling.models.hrv_models import HrvReading
from magma_cycling.models.withings_models import (
    BloodPressureMeasurement,
    SleepData,
    TrainingReadiness,
    WeightMeasurement,
)


class HealthProvider(ABC):
    """Semantic interface for health data consumed by the training system.

    Each method returns typed Pydantic models. Providers translate their
    native API responses into these shared structures.
    """

    @abstractmethod
    def get_sleep_summary(self, target_date: date) -> SleepData | None:
        """Sleep data for the night ending on target_date."""

    @abstractmethod
    def get_sleep_range(self, start_date: date, end_date: date) -> list[SleepData]:
        """Sleep sessions over a date range."""

    @abstractmethod
    def get_body_composition(self) -> WeightMeasurement | None:
        """Latest body composition measurement."""

    @abstractmethod
    def get_body_composition_range(
        self, start_date: date, end_date: date
    ) -> list[WeightMeasurement]:
        """Body composition measurements over a date range."""

    @abstractmethod
    def get_blood_pressure_range(
        self, start_date: date, end_date: date
    ) -> list[BloodPressureMeasurement]:
        """Blood pressure measurements over a date range."""

    @abstractmethod
    def get_readiness(self, target_date: date | None = None) -> TrainingReadiness | None:
        """Training readiness evaluation (encapsulates sleep -> readiness -> weight)."""

    @abstractmethod
    def auth_status(self) -> dict[str, Any]:
        """Authentication / configuration status."""

    def get_hrv_nocturnal(self, target_date: date) -> HrvReading | None:
        """HRV reading captured at the end of the night ending on target_date.

        Default: return None (provider does not expose HRV). Subclasses override
        when they have access to such data (e.g. Withings Sleep Analyzer or
        Intervals.icu wellness).
        """
        return None

    def get_hrv_range(self, start_date: date, end_date: date) -> list[HrvReading]:
        """HRV readings over a date range.

        Default implementation iterates day-by-day calling get_hrv_nocturnal.
        Providers with batch-capable APIs (single wellness fetch covering the
        whole window) should override for efficiency.
        """
        from datetime import timedelta

        readings: list[HrvReading] = []
        current = start_date
        while current <= end_date:
            reading = self.get_hrv_nocturnal(current)
            if reading is not None:
                readings.append(reading)
            current = current + timedelta(days=1)
        return readings

    def get_provider_info(self) -> dict[str, str]:
        """Provider metadata (concrete — not abstract)."""
        return {"provider": self.__class__.__name__, "status": "ready"}
