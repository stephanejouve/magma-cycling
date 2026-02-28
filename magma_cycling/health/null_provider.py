"""Null health provider — silent fallback when no device is configured."""

from __future__ import annotations

from datetime import date
from typing import Any

from magma_cycling.health.base import HealthProvider
from magma_cycling.models.withings_models import (
    SleepData,
    TrainingReadiness,
    WeightMeasurement,
)


class NullProvider(HealthProvider):
    """Returns None / empty lists for every method. Never raises."""

    def get_sleep_summary(self, target_date: date) -> SleepData | None:
        """Return None — no sleep data available."""
        return None

    def get_sleep_range(self, start_date: date, end_date: date) -> list[SleepData]:
        """Return empty list — no sleep data available."""
        return []

    def get_body_composition(self) -> WeightMeasurement | None:
        """Return None — no body composition data available."""
        return None

    def get_body_composition_range(
        self, start_date: date, end_date: date
    ) -> list[WeightMeasurement]:
        """Return empty list — no body composition data available."""
        return []

    def get_readiness(self, target_date: date | None = None) -> TrainingReadiness | None:
        """Return None — no readiness evaluation available."""
        return None

    def auth_status(self) -> dict[str, Any]:
        """Return not-configured status."""
        return {
            "configured": False,
            "has_credentials": False,
            "message": "No health provider configured",
        }

    def get_provider_info(self) -> dict[str, str]:
        """Return NullProvider metadata."""
        return {"provider": "NullProvider", "status": "not_configured"}
