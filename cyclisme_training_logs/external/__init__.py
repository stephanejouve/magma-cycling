"""External data sources integration for training workouts.

This package provides integrations with external workout databases:
- Zwift workout catalog (whatsonzwift.com)
"""

from cyclisme_training_logs.external.zwift_client import ZwiftWorkoutClient
from cyclisme_training_logs.external.zwift_converter import ZwiftWorkoutConverter
from cyclisme_training_logs.external.zwift_models import (
    WorkoutSearchCriteria,
    ZwiftWorkout,
    ZwiftWorkoutSegment,
)

__all__ = [
    "ZwiftWorkoutClient",
    "ZwiftWorkout",
    "ZwiftWorkoutSegment",
    "WorkoutSearchCriteria",
    "ZwiftWorkoutConverter",
]
