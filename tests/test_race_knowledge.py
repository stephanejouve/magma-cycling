"""Tests for magma_cycling/race_knowledge.py — circuit KB loading and matching."""

import json

import pytest

from magma_cycling.race_knowledge import RaceKnowledge


@pytest.fixture
def circuits_data():
    """Minimal circuits KB for testing."""
    return {
        "the-classic": {
            "name": "The Classic",
            "aliases": ["the classic", "jarvis ccw"],
            "world": "Watopia",
            "region": "Jarvis Island",
            "distance_km": 4.87,
            "elevation_m": 46,
            "profile": "flat",
            "segments": ["Jarvis KOM", "Jarvis Sprint"],
            "tactical_notes": "Drafting crucial.",
        },
        "croissant": {
            "name": "Croissant",
            "aliases": ["croissant", "paris croissant"],
            "world": "France",
            "region": "Paris",
            "distance_km": 10.1,
            "elevation_m": 55,
            "profile": "flat",
        },
    }


@pytest.fixture
def kb_path(tmp_path, circuits_data):
    """Write circuits.json to a temp path and return it."""
    path = tmp_path / "circuits.json"
    path.write_text(json.dumps(circuits_data), encoding="utf-8")
    return path


@pytest.fixture
def kb(kb_path):
    """Create a RaceKnowledge instance."""
    return RaceKnowledge(kb_path)


class TestLoadCircuits:
    """Test circuit KB loading."""

    def test_load_circuits(self, kb, circuits_data):
        """Loads a minimal circuits.json and verifies structure."""
        assert len(kb.circuits) == 2
        assert "the-classic" in kb.circuits
        assert kb.circuits["the-classic"]["world"] == "Watopia"

    def test_load_missing_file(self, tmp_path):
        """Missing file results in empty circuits, no crash."""
        kb = RaceKnowledge(tmp_path / "missing.json")
        assert kb.circuits == {}

    def test_load_invalid_json(self, tmp_path):
        """Invalid JSON results in empty circuits, no crash."""
        bad = tmp_path / "bad.json"
        bad.write_text("{invalid", encoding="utf-8")
        kb = RaceKnowledge(bad)
        assert kb.circuits == {}


class TestFindCircuit:
    """Test circuit matching logic."""

    def test_find_circuit_exact_name(self, kb):
        """Match by exact canonical name."""
        result = kb.find_circuit("The Classic")
        assert result is not None
        assert result["name"] == "The Classic"

    def test_find_circuit_alias(self, kb):
        """Match by alias."""
        result = kb.find_circuit("jarvis ccw")
        assert result is not None
        assert result["name"] == "The Classic"

    def test_find_circuit_case_insensitive(self, kb):
        """Case-insensitive matching."""
        result = kb.find_circuit("THE CLASSIC")
        assert result is not None
        assert result["name"] == "The Classic"

    def test_find_circuit_substring(self, kb):
        """Match when circuit name is a substring of event name."""
        result = kb.find_circuit("ZRL - The Classic (Points Race)")
        assert result is not None
        assert result["name"] == "The Classic"

    def test_find_circuit_not_found(self, kb):
        """Unknown name returns None."""
        result = kb.find_circuit("Unknown Circuit XYZ")
        assert result is None

    def test_find_circuit_empty_name(self, kb):
        """Empty event name returns None."""
        assert kb.find_circuit("") is None
        assert kb.find_circuit(None) is None


class TestEnrichEvent:
    """Test event enrichment with circuit metadata."""

    def test_enrich_event_with_match(self, kb):
        """Event with known circuit gets enriched."""
        event = {"name": "ZRL - The Classic", "category": "RACE"}
        enriched = kb.enrich_event(event)

        assert "circuit" in enriched
        assert enriched["circuit"]["world"] == "Watopia"
        assert enriched["circuit"]["distance_km"] == 4.87
        # Original fields preserved
        assert enriched["category"] == "RACE"

    def test_enrich_event_no_match(self, kb):
        """Event without matching circuit keeps original dict."""
        event = {"name": "Unknown Race", "category": "RACE"}
        enriched = kb.enrich_event(event)

        assert "circuit" not in enriched
        assert enriched["name"] == "Unknown Race"
