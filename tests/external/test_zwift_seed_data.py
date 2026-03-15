"""Tests for zwift_seed_data JSON loader."""

import json

from magma_cycling.external.zwift_seed_data import _SEED_DATA_DIR, get_all_seed_workouts


class TestZwiftSeedData:
    """Tests for get_all_seed_workouts and JSON data integrity."""

    def test_get_all_returns_dict(self):
        """get_all_seed_workouts returns a dict."""
        result = get_all_seed_workouts()
        assert isinstance(result, dict)

    def test_get_all_not_empty(self):
        """Seed data contains at least one collection."""
        result = get_all_seed_workouts()
        assert len(result) > 0

    def test_each_workout_has_name(self):
        """Every workout has a non-empty name."""
        for collection, workouts in get_all_seed_workouts().items():
            for w in workouts:
                assert w.name, f"Workout without name in {collection}"

    def test_json_file_exists(self):
        """The JSON seed data file exists on disk."""
        json_file = _SEED_DATA_DIR / "zwift_workouts.json"
        assert json_file.exists()

    def test_json_file_valid(self):
        """The JSON file parses without errors."""
        json_file = _SEED_DATA_DIR / "zwift_workouts.json"
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_roundtrip_count(self):
        """Workout count from function matches raw JSON count."""
        json_file = _SEED_DATA_DIR / "zwift_workouts.json"
        with open(json_file, encoding="utf-8") as f:
            raw = json.load(f)
        raw_count = sum(len(v) for v in raw.values())

        result = get_all_seed_workouts()
        func_count = sum(len(v) for v in result.values())

        assert func_count == raw_count
