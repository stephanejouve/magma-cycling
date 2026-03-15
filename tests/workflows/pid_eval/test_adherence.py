"""Tests for AdherenceMixin."""

import json
from datetime import date
from pathlib import Path

from magma_cycling.workflows.pid_eval.adherence import AdherenceMixin


class StubAdherence(AdherenceMixin):
    """Stub class to test AdherenceMixin in isolation."""

    def __init__(self, adherence_file):
        """Initialize stub with adherence file path."""
        self.adherence_file = Path(adherence_file)


def _write_jsonl(path, records):
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


class TestLoadAdherenceData:
    """Tests for load_adherence_data."""

    def test_loads_records_in_range(self, tmp_path):
        """Records within date range are returned."""
        path = tmp_path / "adherence.jsonl"
        _write_jsonl(
            path,
            [
                {"date": "2026-01-10", "planned_workouts": 1, "completed_activities": 1},
                {"date": "2026-01-15", "planned_workouts": 2, "completed_activities": 1},
                {"date": "2026-01-20", "planned_workouts": 1, "completed_activities": 0},
            ],
        )
        stub = StubAdherence(path)
        result = stub.load_adherence_data(date(2026, 1, 10), date(2026, 1, 15))
        assert len(result) == 2

    def test_excludes_records_outside_range(self, tmp_path):
        """Records outside date range are excluded."""
        path = tmp_path / "adherence.jsonl"
        _write_jsonl(
            path,
            [
                {"date": "2026-01-01", "planned_workouts": 1, "completed_activities": 1},
                {"date": "2026-02-01", "planned_workouts": 1, "completed_activities": 1},
            ],
        )
        stub = StubAdherence(path)
        result = stub.load_adherence_data(date(2026, 1, 10), date(2026, 1, 20))
        assert len(result) == 0

    def test_empty_file_returns_empty(self, tmp_path):
        """Empty file returns empty list."""
        path = tmp_path / "adherence.jsonl"
        path.write_text("")
        stub = StubAdherence(path)
        result = stub.load_adherence_data(date(2026, 1, 1), date(2026, 12, 31))
        assert result == []

    def test_missing_file_returns_empty(self, tmp_path):
        """Missing file returns empty list without crash."""
        path = tmp_path / "nonexistent.jsonl"
        stub = StubAdherence(path)
        result = stub.load_adherence_data(date(2026, 1, 1), date(2026, 12, 31))
        assert result == []

    def test_malformed_json_skipped(self, tmp_path):
        """Malformed JSON lines are silently skipped."""
        path = tmp_path / "adherence.jsonl"
        path.write_text(
            '{"date": "2026-01-10", "planned_workouts": 1, "completed_activities": 1}\n'
            "NOT_JSON\n"
            '{"date": "2026-01-11", "planned_workouts": 2, "completed_activities": 2}\n'
        )
        stub = StubAdherence(path)
        result = stub.load_adherence_data(date(2026, 1, 1), date(2026, 12, 31))
        assert len(result) == 2
