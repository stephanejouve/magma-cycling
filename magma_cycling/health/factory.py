"""Factory for creating the appropriate HealthProvider."""

from __future__ import annotations

import logging

from magma_cycling.health.base import HealthProvider

logger = logging.getLogger(__name__)


def create_health_provider() -> HealthProvider:
    """Create a HealthProvider based on available configuration.

    Priority chain:
        1. WithingsProvider if Withings is configured
        2. IntervalsHealthProvider if Intervals.icu has sleep data
        3. NullProvider (silent fallback)

    Never raises — falls back silently to NullProvider on any error.
    """
    # 1. Try Withings
    try:
        from magma_cycling.config import create_withings_client, get_withings_config
        from magma_cycling.health.withings_provider import WithingsProvider

        config = get_withings_config()
        if config.is_configured():
            client = create_withings_client()
            return WithingsProvider(client)
    except Exception:
        pass

    # 2. Try Intervals.icu wellness (Garmin/other watch).
    # Probe a 7-day window (not just yesterday) so that a single missing day
    # — late Garmin sync, day off without watch, weekend retreat, etc. — does
    # not silently disable the provider for the whole session.
    try:
        from datetime import date, timedelta

        from magma_cycling.config import create_intervals_client

        client = create_intervals_client()
        seven_days_ago = str(date.today() - timedelta(days=7))
        yesterday = str(date.today() - timedelta(days=1))
        wellness = client.get_wellness(oldest=seven_days_ago, newest=yesterday)
        if wellness and any(w.get("sleepTime") for w in wellness):
            from magma_cycling.health.intervals_provider import IntervalsHealthProvider

            logger.info("Using IntervalsHealthProvider (sleep data found in last 7 days)")
            return IntervalsHealthProvider(client)
    except Exception:
        pass

    # 3. Fallback
    from magma_cycling.health.null_provider import NullProvider

    return NullProvider()
