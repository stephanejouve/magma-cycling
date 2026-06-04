"""Fallback to last known weight in a recent wellness window (BT-015 follow-up).

When Intervals.icu wellness for day J has no weight (e.g. no real weighing and
FitnessSyncer J+1 lag), look back up to ``max_days_back`` days and return the
most recent ``weight > 0`` found in the wellness range.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def get_last_known_weight(
    client: Any, target_date: date, max_days_back: int = 14
) -> tuple[float | None, date | None]:
    """Return (weight_kg, measurement_date) — last weight > 0 in [target-N, target]."""
    start = target_date - timedelta(days=max_days_back)
    try:
        entries = client.get_wellness(oldest=start.isoformat(), newest=target_date.isoformat())
    except Exception as exc:
        logger.warning("weight fallback: wellness range fetch failed: %s", exc)
        return None, None
    if not entries:
        return None, None
    for entry in sorted(entries, key=lambda e: e.get("id", ""), reverse=True):
        raw = entry.get("weight")
        if not raw:
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if value <= 0:
            continue
        day_str = entry.get("id")
        try:
            day = date.fromisoformat(day_str) if day_str else None
        except (TypeError, ValueError):
            day = None
        return value, day
    return None, None


def apply_weight_fallback(
    client: Any,
    target_date: date,
    wellness: dict | None,
    max_days_back: int = 14,
) -> dict | None:
    """Return a copy of ``wellness`` with ``weight`` filled from fallback if missing.

    If ``wellness`` is None or already has ``weight > 0``, return it unchanged.
    Otherwise look back up to ``max_days_back`` days for the last known weight.
    Logs an info-level message when fallback fires, with the age of the picked value.
    """
    if wellness is None:
        return None
    raw = wellness.get("weight")
    if raw:
        try:
            if float(raw) > 0:
                return wellness
        except (TypeError, ValueError):
            pass
    fallback_weight, fallback_date = get_last_known_weight(client, target_date, max_days_back)
    if fallback_weight is None:
        return wellness
    patched = dict(wellness)
    patched["weight"] = fallback_weight
    if fallback_date is not None:
        age = (target_date - fallback_date).days
        logger.info(
            "BT-015 weight fallback: using %.1fkg from %s (%d days ago)",
            fallback_weight,
            fallback_date.isoformat(),
            age,
        )
    else:
        logger.info("BT-015 weight fallback: using %.1fkg (unknown date)", fallback_weight)
    return patched
