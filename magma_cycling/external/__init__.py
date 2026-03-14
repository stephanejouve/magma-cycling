"""External data sources integration for training workouts.

This package provides integrations with external workout databases:
- Zwift workout catalog (whatsonzwift.com)
"""

from magma_cycling.external.zwift_client import ZwiftWorkoutClient
from magma_cycling.external.zwift_collections import KNOWN_COLLECTIONS
from magma_cycling.external.zwift_converter import ZwiftWorkoutConverter
from magma_cycling.external.zwift_models import (
    WorkoutSearchCriteria,
    ZwiftWorkout,
    ZwiftWorkoutSegment,
)
from magma_cycling.external.zwift_scraper import ZwiftWorkoutScraper
from magma_cycling.external.zwift_service import PopulateResult, ZwiftService

__all__ = [
    "KNOWN_COLLECTIONS",
    "PopulateResult",
    "WorkoutSearchCriteria",
    "ZwiftService",
    "ZwiftWorkout",
    "ZwiftWorkoutClient",
    "ZwiftWorkoutConverter",
    "ZwiftWorkoutSegment",
    "ZwiftWorkoutScraper",
]
