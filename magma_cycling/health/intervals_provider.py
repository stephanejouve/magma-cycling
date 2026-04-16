"""Intervals.icu wellness-based health provider (Garmin/other watch sources)."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from magma_cycling.health.base import HealthProvider
from magma_cycling.models.withings_models import (
    BloodPressureMeasurement,
    SleepData,
    TrainingReadiness,
    WeightMeasurement,
)

logger = logging.getLogger(__name__)


class IntervalsHealthProvider(HealthProvider):
    """Read health data from Intervals.icu wellness (Garmin/other sources)."""

    def __init__(self, client: Any) -> None:
        """Initialize with an IntervalsClient instance."""
        self._client = client

    def _get_wellness_day(self, target_date: date) -> dict | None:
        """Fetch a single day's wellness data."""
        date_str = str(target_date)
        wellness = self._client.get_wellness(oldest=date_str, newest=date_str)
        if not wellness:
            return None
        return wellness[0]

    # -- sleep ---------------------------------------------------------------

    def get_sleep_summary(self, target_date: date) -> SleepData | None:
        """Get sleep data from Intervals.icu wellness (Garmin push)."""
        w = self._get_wellness_day(target_date)
        if not w:
            return None
        sleep_secs = w.get("sleepTime")
        if not sleep_secs:
            return None
        # Build a SleepData from available wellness fields
        sleep_hours = round(sleep_secs / 3600, 2)
        # Estimate start/end from sleep duration ending at 07:00
        end_dt = datetime.combine(target_date, datetime.min.time()).replace(hour=7)
        start_dt = end_dt - timedelta(seconds=sleep_secs)
        return SleepData(
            date=target_date,
            start_datetime=start_dt,
            end_datetime=end_dt,
            total_sleep_hours=sleep_hours,
            sleep_score=w.get("sleepScore"),
            sleep_efficiency=None,
            wakeup_count=w.get("wakeupCount", 0),
        )

    def get_sleep_range(self, start_date: date, end_date: date) -> list[SleepData]:
        """Get sleep sessions over a date range from wellness data."""
        results = []
        current = start_date
        while current <= end_date:
            summary = self.get_sleep_summary(current)
            if summary:
                results.append(summary)
            current += timedelta(days=1)
        return results

    # -- body composition (not available from Intervals.icu wellness) --------

    def get_body_composition(self) -> WeightMeasurement | None:
        """Return None — not available from Intervals.icu wellness."""
        return None

    def get_body_composition_range(
        self, start_date: date, end_date: date
    ) -> list[WeightMeasurement]:
        """Return empty list — not available from Intervals.icu wellness."""
        return []

    # -- blood pressure (not available) --------------------------------------

    def get_blood_pressure_range(
        self, start_date: date, end_date: date
    ) -> list[BloodPressureMeasurement]:
        """Return empty list — not available from Intervals.icu wellness."""
        return []

    # -- readiness -----------------------------------------------------------

    def get_readiness(self, target_date: date | None = None) -> TrainingReadiness | None:
        """Evaluate readiness from Intervals.icu sleep data."""
        sleep = self.get_sleep_summary(target_date or date.today())
        if not sleep:
            return None
        ready = sleep.total_sleep_hours >= 6.5
        if sleep.total_sleep_hours >= 7:
            intensity = "all_systems_go"
        elif sleep.total_sleep_hours >= 6:
            intensity = "moderate"
        elif sleep.total_sleep_hours >= 5:
            intensity = "endurance_max"
        else:
            intensity = "recovery_only"
        veto = []
        if sleep.total_sleep_hours < 5.5:
            veto.append(f"Insufficient sleep: {sleep.total_sleep_hours}h")
        return TrainingReadiness(
            date=target_date or date.today(),
            sleep_hours=sleep.total_sleep_hours,
            sleep_score=sleep.sleep_score,
            ready_for_intense=ready,
            recommended_intensity=intensity,
            veto_reasons=veto,
        )

    # -- auth ----------------------------------------------------------------

    def auth_status(self) -> dict[str, Any]:
        """Return provider status."""
        return {
            "configured": True,
            "has_credentials": True,
            "provider": "intervals_icu_wellness",
        }

    def get_provider_info(self) -> dict[str, str]:
        """Return IntervalsHealthProvider metadata."""
        return {"provider": "IntervalsHealthProvider", "status": "ready"}
