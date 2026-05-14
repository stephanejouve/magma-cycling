"""Tests for the home_location schema + read/write helpers (MCT-XXX-0)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from magma_cycling.config.geo import (
    GeoPoint,
    load_home_location,
    save_home_location,
)


class TestGeoPoint:
    def test_valid_geopoint(self):
        p = GeoPoint(lat=45.69, lon=3.34, label="Chas")
        assert p.lat == 45.69
        assert p.lon == 3.34
        assert p.label == "Chas"

    def test_label_optional(self):
        p = GeoPoint(lat=0.0, lon=0.0)
        assert p.label is None

    def test_lat_out_of_range(self):
        with pytest.raises(ValidationError):
            GeoPoint(lat=91.0, lon=0.0)
        with pytest.raises(ValidationError):
            GeoPoint(lat=-91.0, lon=0.0)

    def test_lon_out_of_range(self):
        with pytest.raises(ValidationError):
            GeoPoint(lat=0.0, lon=181.0)
        with pytest.raises(ValidationError):
            GeoPoint(lat=0.0, lon=-181.0)

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            GeoPoint(lat=0.0, lon=0.0, country="FR")  # type: ignore[call-arg]

    def test_frozen_cannot_mutate(self):
        p = GeoPoint(lat=0.0, lon=0.0)
        with pytest.raises(ValidationError):
            p.lat = 1.0  # type: ignore[misc]


class TestLoadHomeLocation:
    def test_returns_none_when_yaml_absent(self, tmp_path: Path):
        missing = tmp_path / "absent.yaml"
        assert load_home_location(missing) is None

    def test_returns_none_when_key_absent(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        yaml_path.write_text("athlete:\n  name: Test\n", encoding="utf-8")
        assert load_home_location(yaml_path) is None

    def test_returns_none_when_athlete_section_missing(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        yaml_path.write_text("not_athlete: {}\n", encoding="utf-8")
        assert load_home_location(yaml_path) is None

    def test_loads_valid_geopoint(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        yaml_path.write_text(
            "athlete:\n  home_location:\n    lat: 45.69\n    lon: 3.34\n    label: Chas\n",
            encoding="utf-8",
        )
        p = load_home_location(yaml_path)
        assert p is not None
        assert p.lat == 45.69
        assert p.lon == 3.34
        assert p.label == "Chas"

    def test_invalid_geopoint_returns_none(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        yaml_path.write_text(
            "athlete:\n  home_location:\n    lat: 200\n    lon: 3.34\n",
            encoding="utf-8",
        )
        assert load_home_location(yaml_path) is None

    def test_malformed_yaml_returns_none(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        yaml_path.write_text("not: valid: yaml: [", encoding="utf-8")
        assert load_home_location(yaml_path) is None


class TestSaveHomeLocation:
    def test_creates_yaml_when_absent(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        location = GeoPoint(lat=45.69, lon=3.34, label="Chas")
        result_path = save_home_location(location, yaml_path)
        assert result_path == yaml_path
        assert yaml_path.is_file()
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert data["athlete"]["home_location"] == {
            "lat": 45.69,
            "lon": 3.34,
            "label": "Chas",
        }

    def test_preserves_other_athlete_fields(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        yaml_path.write_text(
            "athlete:\n  name: Test\n  age: 54\n  bike: cube\n",
            encoding="utf-8",
        )
        location = GeoPoint(lat=45.69, lon=3.34)
        save_home_location(location, yaml_path)
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert data["athlete"]["name"] == "Test"
        assert data["athlete"]["age"] == 54
        assert data["athlete"]["bike"] == "cube"
        assert data["athlete"]["home_location"]["lat"] == 45.69

    def test_overwrites_existing_home_location(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        save_home_location(GeoPoint(lat=10.0, lon=20.0, label="A"), yaml_path)
        save_home_location(GeoPoint(lat=30.0, lon=40.0, label="B"), yaml_path)
        loaded = load_home_location(yaml_path)
        assert loaded is not None
        assert loaded.lat == 30.0
        assert loaded.label == "B"

    def test_omits_label_when_absent(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        save_home_location(GeoPoint(lat=10.0, lon=20.0), yaml_path)
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert "label" not in data["athlete"]["home_location"]


class TestRoundTrip:
    def test_save_then_load(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        original = GeoPoint(lat=45.690123, lon=3.34, label="Chas")
        save_home_location(original, yaml_path)
        loaded = load_home_location(yaml_path)
        assert loaded == original
