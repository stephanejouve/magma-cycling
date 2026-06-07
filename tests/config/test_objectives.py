"""Tests for the priority_objective schema + read/write helpers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from magma_cycling.config.objectives import (
    PriorityObjective,
    clear_priority_objective,
    load_priority_objective,
    save_priority_objective,
)


class TestPriorityObjective:
    def test_minimal_valid(self):
        obj = PriorityObjective(
            name="Les Copains 81km",
            type="granfondo",
            target_date=date(2026, 7, 4),
        )
        assert obj.name == "Les Copains 81km"
        assert obj.type == "granfondo"
        assert obj.target_date == date(2026, 7, 4)
        assert obj.priority == "A"
        assert obj.distance_km is None
        assert obj.notes is None

    def test_all_fields(self):
        obj = PriorityObjective(
            name="Race",
            type="race",
            target_date=date(2026, 7, 4),
            priority="B",
            distance_km=81.0,
            notes="Build + taper",
        )
        assert obj.priority == "B"
        assert obj.distance_km == 81.0
        assert obj.notes == "Build + taper"

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            PriorityObjective(name="", type="granfondo", target_date=date(2026, 7, 4))

    def test_zero_distance_rejected(self):
        with pytest.raises(ValidationError):
            PriorityObjective(
                name="x", type="granfondo", target_date=date(2026, 7, 4), distance_km=0
            )

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            PriorityObjective(
                name="x",
                type="granfondo",
                target_date=date(2026, 7, 4),
                unknown="oops",  # type: ignore[call-arg]
            )

    def test_frozen_cannot_mutate(self):
        obj = PriorityObjective(name="x", type="granfondo", target_date=date(2026, 7, 4))
        with pytest.raises(ValidationError):
            obj.priority = "C"  # type: ignore[misc]


class TestLoadPriorityObjective:
    def test_returns_none_when_yaml_absent(self, tmp_path: Path):
        assert load_priority_objective(tmp_path / "absent.yaml") is None

    def test_returns_none_when_key_absent(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        yaml_path.write_text("athlete:\n  name: Test\n", encoding="utf-8")
        assert load_priority_objective(yaml_path) is None

    def test_returns_none_when_athlete_section_missing(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        yaml_path.write_text("not_athlete: {}\n", encoding="utf-8")
        assert load_priority_objective(yaml_path) is None

    def test_loads_valid_objective(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        yaml_path.write_text(
            "athlete:\n"
            "  priority_objective:\n"
            "    name: Les Copains 81km\n"
            "    type: granfondo\n"
            "    target_date: 2026-07-04\n"
            "    priority: A\n"
            "    distance_km: 81\n"
            "    notes: Build + taper\n",
            encoding="utf-8",
        )
        obj = load_priority_objective(yaml_path)
        assert obj is not None
        assert obj.name == "Les Copains 81km"
        assert obj.target_date == date(2026, 7, 4)
        assert obj.distance_km == 81.0

    def test_invalid_objective_returns_none(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        yaml_path.write_text(
            "athlete:\n  priority_objective:\n    name: x\n",  # missing required
            encoding="utf-8",
        )
        assert load_priority_objective(yaml_path) is None

    def test_malformed_yaml_returns_none(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        yaml_path.write_text("not: valid: yaml: [", encoding="utf-8")
        assert load_priority_objective(yaml_path) is None


class TestSavePriorityObjective:
    def test_creates_yaml_when_absent(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        obj = PriorityObjective(
            name="Les Copains 81km",
            type="granfondo",
            target_date=date(2026, 7, 4),
            distance_km=81.0,
        )
        result = save_priority_objective(obj, yaml_path)
        assert result == yaml_path
        assert yaml_path.is_file()
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        po = data["athlete"]["priority_objective"]
        assert po["name"] == "Les Copains 81km"
        assert po["target_date"] == "2026-07-04"
        assert po["distance_km"] == 81.0

    def test_preserves_other_athlete_fields(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        yaml_path.write_text(
            "athlete:\n  name: Test\n  age: 54\n  home_location:\n    lat: 1.0\n    lon: 2.0\n",
            encoding="utf-8",
        )
        obj = PriorityObjective(name="x", type="granfondo", target_date=date(2026, 7, 4))
        save_priority_objective(obj, yaml_path)
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert data["athlete"]["name"] == "Test"
        assert data["athlete"]["age"] == 54
        assert data["athlete"]["home_location"]["lat"] == 1.0
        assert data["athlete"]["priority_objective"]["name"] == "x"

    def test_overwrites_existing(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        save_priority_objective(
            PriorityObjective(name="old", type="granfondo", target_date=date(2026, 1, 1)),
            yaml_path,
        )
        save_priority_objective(
            PriorityObjective(name="new", type="granfondo", target_date=date(2026, 7, 4)),
            yaml_path,
        )
        loaded = load_priority_objective(yaml_path)
        assert loaded is not None
        assert loaded.name == "new"
        assert loaded.target_date == date(2026, 7, 4)

    def test_omits_none_fields(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        save_priority_objective(
            PriorityObjective(name="x", type="granfondo", target_date=date(2026, 7, 4)),
            yaml_path,
        )
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        po = data["athlete"]["priority_objective"]
        assert "distance_km" not in po
        assert "notes" not in po


class TestClearPriorityObjective:
    def test_returns_none_when_yaml_absent(self, tmp_path: Path):
        assert clear_priority_objective(tmp_path / "absent.yaml") is None

    def test_returns_none_when_key_absent(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        yaml_path.write_text("athlete:\n  name: Test\n", encoding="utf-8")
        assert clear_priority_objective(yaml_path) is None

    def test_removes_existing(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        save_priority_objective(
            PriorityObjective(name="x", type="granfondo", target_date=date(2026, 7, 4)),
            yaml_path,
        )
        result = clear_priority_objective(yaml_path)
        assert result == yaml_path
        assert load_priority_objective(yaml_path) is None
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert "priority_objective" not in data["athlete"]


class TestRoundTrip:
    def test_save_then_load(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        original = PriorityObjective(
            name="Les Copains 81km",
            type="granfondo",
            target_date=date(2026, 7, 4),
            priority="A",
            distance_km=81.0,
            notes="Build + taper",
        )
        save_priority_objective(original, yaml_path)
        loaded = load_priority_objective(yaml_path)
        assert loaded == original
