"""Withings implementation of HealthProvider."""

from __future__ import annotations

from datetime import date
from typing import Any

from magma_cycling.api.withings_client import WithingsClient
from magma_cycling.health.base import HealthProvider
from magma_cycling.models.withings_models import (
    SleepData,
    TrainingReadiness,
    WeightMeasurement,
)


class WithingsProvider(HealthProvider):
    """Wraps WithingsClient and converts raw dicts to Pydantic models."""

    def __init__(self, client: WithingsClient) -> None:
        """Initialize with a configured WithingsClient."""
        self._client = client

    # -- sleep ---------------------------------------------------------------

    @staticmethod
    def _normalize_sleep_data(data: dict) -> dict:
        """Normalize Withings sleep data before Pydantic validation.

        Withings API returns sleep_efficiency as a 0-1 ratio (e.g. 0.96),
        but SleepData model expects an integer percentage (0-100).
        """
        eff = data.get("sleep_efficiency")
        if eff is not None and eff <= 1.0:
            data["sleep_efficiency"] = round(eff * 100)
        elif eff is not None:
            data["sleep_efficiency"] = round(eff)
        return data

    def get_sleep_summary(self, target_date: date) -> SleepData | None:
        """Get last night's sleep from Withings."""
        data = self._client.get_last_night_sleep()
        if not data:
            return None
        return SleepData(**self._normalize_sleep_data(data))

    def get_sleep_range(self, start_date: date, end_date: date) -> list[SleepData]:
        """Get sleep sessions over a date range from Withings."""
        return [
            SleepData(**self._normalize_sleep_data(s))
            for s in self._client.get_sleep(start_date, end_date)
        ]

    # -- body composition ----------------------------------------------------

    def get_body_composition(self) -> WeightMeasurement | None:
        """Get latest weight measurement from Withings."""
        data = self._client.get_latest_weight()
        return WeightMeasurement(**data) if data else None

    def get_body_composition_range(
        self, start_date: date, end_date: date
    ) -> list[WeightMeasurement]:
        """Get weight measurements over a date range from Withings."""
        return [
            WeightMeasurement(**m)
            for m in self._client.get_measurements(
                start_date, end_date, measure_types=[1, 6, 8, 76, 88]
            )
        ]

    # -- readiness -----------------------------------------------------------

    def get_readiness(self, target_date: date | None = None) -> TrainingReadiness | None:
        """Evaluate training readiness from sleep + weight data."""
        sleep = self.get_sleep_summary(target_date or date.today())
        if not sleep:
            return None
        readiness_dict = self._client.evaluate_training_readiness(sleep.model_dump())
        weight = self.get_body_composition()
        if weight:
            readiness_dict["weight_kg"] = weight.weight_kg
        return TrainingReadiness(**readiness_dict)

    # -- auth ----------------------------------------------------------------

    def auth_status(self) -> dict[str, Any]:
        """Return Withings authentication status."""
        return {
            "configured": True,
            "has_credentials": self._client.is_authenticated(),
            "provider": "withings",
        }

    def get_provider_info(self) -> dict[str, str]:
        """Return WithingsProvider metadata."""
        return {"provider": "WithingsProvider", "status": "ready"}

    # -- direct client access (OAuth flows, etc.) ----------------------------

    @property
    def client(self) -> WithingsClient:
        """Access underlying WithingsClient for Withings-specific operations."""
        return self._client
