"""Health provider abstraction layer.

Provides a semantic interface for health data (sleep, weight, readiness)
that decouples the training system from any specific health device API.
"""

from magma_cycling.health.base import HealthProvider
from magma_cycling.health.factory import create_health_provider
from magma_cycling.health.null_provider import NullProvider
from magma_cycling.health.withings_provider import WithingsProvider

__all__ = [
    "HealthProvider",
    "NullProvider",
    "WithingsProvider",
    "create_health_provider",
]
