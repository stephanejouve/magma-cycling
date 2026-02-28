"""Factory for creating the appropriate HealthProvider."""

from __future__ import annotations

from magma_cycling.health.base import HealthProvider


def create_health_provider() -> HealthProvider:
    """Create a HealthProvider based on available configuration.

    Returns WithingsProvider if Withings is configured, NullProvider otherwise.
    Never raises — falls back silently to NullProvider on any error.
    """
    try:
        from magma_cycling.config import create_withings_client, get_withings_config
        from magma_cycling.health.withings_provider import WithingsProvider

        config = get_withings_config()
        if not config.is_configured():
            from magma_cycling.health.null_provider import NullProvider

            return NullProvider()
        client = create_withings_client()
        return WithingsProvider(client)
    except Exception:
        from magma_cycling.health.null_provider import NullProvider

        return NullProvider()
