"""Zwift seed workout data loader.

Loads manually curated Zwift workout collections from JSON.
Data originally based on actual Zwift Camp: Baseline 2025 workouts.
"""

import json
from pathlib import Path

from magma_cycling.external.zwift_models import ZwiftWorkout

_SEED_DATA_DIR = Path(__file__).parent / "seed_data"


def get_all_seed_workouts() -> dict[str, list[ZwiftWorkout]]:
    """Load all seed workout collections from JSON.

    Returns:
        Dict mapping collection name to list of ZwiftWorkout objects
    """
    data_file = _SEED_DATA_DIR / "zwift_workouts.json"
    if not data_file.exists():
        return {}
    with open(data_file, encoding="utf-8") as f:
        raw = json.load(f)
    return {
        collection: [ZwiftWorkout(**w) for w in workouts] for collection, workouts in raw.items()
    }
