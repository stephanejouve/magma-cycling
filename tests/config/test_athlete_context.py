"""Tests for athlete context YAML loader."""

import pytest
import yaml

from magma_cycling.config.athlete_context import load_athlete_context


@pytest.fixture
def sample_yaml(tmp_path):
    """Create a sample athlete context YAML file."""
    data = {
        "athlete": {
            "name": "Test Athlete",
            "age": 40,
            "training_since": "2024-01",
            "platform": "Home trainer",
            "objectives": "General fitness",
            "constraints": ["Constraint A", "Constraint B"],
            "system_context": "Test system context.",
        }
    }
    path = tmp_path / "athlete_context.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


def test_load_athlete_context_returns_profile(sample_yaml):
    """The loader returns athlete profile from YAML."""
    context = load_athlete_context(sample_yaml)
    assert context["name"] == "Test Athlete"
    assert context["age"] == 40
    assert len(context["constraints"]) == 2


def test_load_athlete_context_missing_file_returns_empty(tmp_path):
    """If YAML is missing, returns empty dict without crash."""
    missing = tmp_path / "nonexistent.yaml"
    context = load_athlete_context(missing)
    assert context == {}


def test_load_athlete_context_custom_path(tmp_path):
    """The loader accepts a custom path."""
    data = {"athlete": {"name": "Custom", "age": 30}}
    path = tmp_path / "custom.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")

    context = load_athlete_context(path)
    assert context["name"] == "Custom"
    assert context["age"] == 30


def test_load_athlete_context_default_path():
    """The default path loads the real athlete_context.yaml."""
    context = load_athlete_context()
    assert isinstance(context, dict)
    # The real file should have a name
    assert "name" in context


def test_load_athlete_context_malformed_yaml(tmp_path):
    """Malformed YAML returns empty dict (graceful degradation)."""
    path = tmp_path / "bad.yaml"
    path.write_text("{{invalid yaml: [", encoding="utf-8")
    context = load_athlete_context(path)
    assert context == {}
