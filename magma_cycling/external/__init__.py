"""External data sources integration for training workouts.

This package provides integrations with external workout databases:
- Zwift workout catalog (whatsonzwift.com)
"""

from magma_cycling.external.zwift_client import ZwiftWorkoutClient
from magma_cycling.external.zwift_converter import ZwiftWorkoutConverter
from magma_cycling.external.zwift_models import (
    WorkoutSearchCriteria,
    ZwiftWorkout,
    ZwiftWorkoutSegment,
)
from magma_cycling.external.zwift_scraper import ZwiftWorkoutScraper

__all__ = [
    "ZwiftWorkoutClient",
    "ZwiftWorkout",
    "ZwiftWorkoutSegment",
    "WorkoutSearchCriteria",
    "ZwiftWorkoutConverter",
    "ZwiftWorkoutScraper",
]
