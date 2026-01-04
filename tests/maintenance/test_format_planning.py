"""
Tests pour format_planning.py.

GARTNER_TIME: T
STATUS: Testing
LAST_REVIEW: 2026-01-04
PRIORITY: P1
DOCSTRING: v2

Tests unitaires pour le script format_planning.py qui reformate
les workouts générés par l'AI coach vers le format Intervals.icu.

Author: Claude Code
Created: 2026-01-04
Updated: 2026-01-04 (Sprint R5 - Initial test suite)
"""

import sys
from pathlib import Path

import pytest

# Add scripts/maintenance to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "maintenance"))

from format_planning import WorkoutFormatter


@pytest.fixture
def formatter():
    """Create a WorkoutFormatter instance."""
    return WorkoutFormatter("S075")


@pytest.fixture
def sample_workout_correct():
    """Sample workout with correct notation."""
    return {
        "id": "S075-01",
        "name": "S075-01-END-EnduranceBase-V001",
        "content": """Endurance Base

Structure:
Warmup
- 10min ramp 50%→65% (110W→143W) 85rpm

Main set: 5x
- 3min 60rpm 65% (143W)
- 3min 100rpm 65% (143W)
- 2min 85rpm 65% (143W)

Cooldown
- 10min ramp 65%→50% (143W→110W) 85rpm

TSS: 45 | Durée: 60min""",
    }


@pytest.fixture
def sample_workout_bad_repetition():
    """Sample workout with incorrect repetition notation."""
    return {
        "id": "S075-02",
        "name": "S075-02-INT-Test-V001",
        "content": """Test

Main set:
- 5x [3min @ 110% FTP + 3min @ 65% FTP]

TSS: 60""",
    }


@pytest.fixture
def sample_workout_bad_warmup():
    """Sample workout with descending warmup (incorrect)."""
    return {
        "id": "S075-03",
        "name": "S075-03-END-Test-V001",
        "content": """Test

Warmup
- 10min ramp 65%→50% (143W→110W) 85rpm

Main set
- 30min 70% FTP (154W) 90rpm

Cooldown
- 10min 50% FTP 85rpm""",
    }


@pytest.fixture
def sample_workout_bad_cooldown():
    """Sample workout with ascending cooldown (incorrect)."""
    return {
        "id": "S075-04",
        "name": "S075-04-END-Test-V001",
        "content": """Test

Warmup
- 10min 50% FTP 85rpm

Main set
- 30min 70% FTP (154W) 90rpm

Cooldown
- 10min ramp 50%→65% (110W→143W) 85rpm""",
    }


@pytest.fixture
def sample_workout_no_watts():
    """Sample workout with ramps missing watts."""
    return {
        "id": "S075-05",
        "name": "S075-05-END-Test-V001",
        "content": """Test

Warmup
- 10min ramp 50%→65% 85rpm

Main set
- 30min 70% FTP (154W) 90rpm

Cooldown
- 10min ramp 65%→50% 85rpm""",
    }


@pytest.fixture
def sample_markdown_input():
    """Sample markdown AI output."""
    return """## S075-01 - Lundi 05/01/2026
**Type**: END - Endurance Base
**Nom**: EnduranceBase-V001
**TSS cible**: 45
**Durée**: 60min

### Structure
- 10min échauffement 50% → 65% FTP
- 30min 70% FTP (154W) 90rpm
- 10min retour au calme 65% → 50% FTP

## S075-02 - Mardi 06/01/2026
**Type**: INT - Intervalles
**Nom**: SweetSpot-V001
**TSS cible**: 60
**Durée**: 60min

### Structure
- 10min échauffement
- Main set: 3x
  - 10min 90% FTP (198W)
  - 5min 65% FTP (143W)
- 10min retour au calme
"""


class TestWorkoutFormatter:
    """Tests pour WorkoutFormatter class."""

    def test_initialization(self, formatter):
        """Test formatter initialization."""
        assert formatter.week_id == "S075"
        assert formatter.workouts == []

    def test_parse_workouts_from_markdown(self, formatter, sample_markdown_input):
        """Test parsing workouts from markdown AI output."""
        workouts = formatter.parse_workouts(sample_markdown_input)

        assert len(workouts) == 2
        assert workouts[0]["id"] == "S075-01"
        assert workouts[1]["id"] == "S075-02"
        assert "END" in workouts[0]["name"]
        assert "INT" in workouts[1]["name"]

    def test_validate_correct_notation(self, formatter, sample_workout_correct):
        """Test validation passes for correct notation."""
        warnings = formatter.validate_notation(sample_workout_correct)
        assert len(warnings) == 0

    def test_validate_bad_repetition(self, formatter, sample_workout_bad_repetition):
        """Test validation detects incorrect repetition notation."""
        warnings = formatter.validate_notation(sample_workout_bad_repetition)

        assert len(warnings) > 0
        assert any("5x [...]" in w for w in warnings)

    def test_validate_bad_warmup(self, formatter, sample_workout_bad_warmup):
        """Test validation detects descending warmup (should be ascending)."""
        warnings = formatter.validate_notation(sample_workout_bad_warmup)

        assert len(warnings) > 0
        assert any("Warmup ramp devrait être ascendant" in w for w in warnings)

    def test_validate_bad_cooldown(self, formatter, sample_workout_bad_cooldown):
        """Test validation detects ascending cooldown (should be descending)."""
        warnings = formatter.validate_notation(sample_workout_bad_cooldown)

        assert len(warnings) > 0
        assert any("Cooldown ramp devrait être descendant" in w for w in warnings)

    def test_validate_ramps_no_watts(self, formatter, sample_workout_no_watts):
        """Test validation detects ramps without explicit watts."""
        warnings = formatter.validate_notation(sample_workout_no_watts)

        assert len(warnings) > 0
        assert any("sans watts explicites" in w for w in warnings)

    def test_format_for_upload(self, formatter, sample_workout_correct):
        """Test formatting workouts for upload."""
        workouts = [sample_workout_correct]
        formatted = formatter.format_for_upload(workouts)

        assert "=== WORKOUT S075-01-END-EnduranceBase-V001 ===" in formatted
        assert "=== FIN WORKOUT ===" in formatted
        assert "Endurance Base" in formatted

    def test_format_multiple_workouts(self, formatter):
        """Test formatting multiple workouts."""
        workouts = [
            {
                "name": "S075-01-END-Test1-V001",
                "content": "Test 1 content",
            },
            {
                "name": "S075-02-INT-Test2-V001",
                "content": "Test 2 content",
            },
        ]

        formatted = formatter.format_for_upload(workouts)

        assert formatted.count("=== WORKOUT") == 2
        assert formatted.count("=== FIN WORKOUT ===") == 2
        assert "S075-01" in formatted
        assert "S075-02" in formatted


class TestValidationRules:
    """Tests spécifiques pour les règles de validation."""

    def test_repetition_2x_detection(self, formatter):
        """Test detection of 2x repetition."""
        workout = {
            "id": "TEST",
            "content": "Main set: 2x [10min @ 90% + 5min @ 65%]",
        }
        warnings = formatter.validate_notation(workout)
        assert len(warnings) > 0
        assert "2x [...]" in warnings[0]

    def test_repetition_10x_detection(self, formatter):
        """Test detection of 10x repetition."""
        workout = {
            "id": "TEST",
            "content": "Main set: 10x [30s @ 150% + 30s @ 50%]",
        }
        warnings = formatter.validate_notation(workout)
        assert len(warnings) > 0
        assert "10x [...]" in warnings[0]

    def test_warmup_50_to_65_valid(self, formatter):
        """Test warmup 50%→65% is valid (ascending)."""
        workout = {
            "id": "TEST",
            "content": """Warmup
- 10min ramp 50%→65% (110W→143W) 85rpm""",
        }
        warnings = formatter.validate_notation(workout)
        # Should not have warmup direction warning
        assert not any("Warmup ramp devrait être" in w for w in warnings)

    def test_warmup_65_to_50_invalid(self, formatter):
        """Test warmup 65%→50% is invalid (descending)."""
        workout = {
            "id": "TEST",
            "content": """Warmup
- 10min ramp 65%→50% (143W→110W) 85rpm""",
        }
        warnings = formatter.validate_notation(workout)
        assert any("Warmup ramp devrait être ascendant" in w for w in warnings)

    def test_cooldown_65_to_50_valid(self, formatter):
        """Test cooldown 65%→50% is valid (descending)."""
        workout = {
            "id": "TEST",
            "content": """Cooldown
- 10min ramp 65%→50% (143W→110W) 85rpm""",
        }
        warnings = formatter.validate_notation(workout)
        # Should not have cooldown direction warning
        assert not any("Cooldown ramp devrait être" in w for w in warnings)

    def test_cooldown_50_to_65_invalid(self, formatter):
        """Test cooldown 50%→65% is invalid (ascending)."""
        workout = {
            "id": "TEST",
            "content": """Cooldown
- 10min ramp 50%→65% (110W→143W) 85rpm""",
        }
        warnings = formatter.validate_notation(workout)
        assert any("Cooldown ramp devrait être descendant" in w for w in warnings)

    def test_ramp_with_watts_valid(self, formatter):
        """Test ramp with watts (110W→143W) is valid."""
        workout = {
            "id": "TEST",
            "content": "- 10min ramp 50%→65% (110W→143W) 85rpm",
        }
        warnings = formatter.validate_notation(workout)
        # Should not have watts warning
        assert not any("sans watts explicites" in w for w in warnings)

    def test_ramp_without_watts_invalid(self, formatter):
        """Test ramp without watts is invalid."""
        workout = {
            "id": "TEST",
            "content": "- 10min ramp 50%→65% 85rpm",
        }
        warnings = formatter.validate_notation(workout)
        assert any("sans watts explicites" in w for w in warnings)


class TestEdgeCases:
    """Tests pour les cas limites."""

    def test_empty_content(self, formatter):
        """Test validation with empty content."""
        workout = {"id": "TEST", "content": ""}
        warnings = formatter.validate_notation(workout)
        assert isinstance(warnings, list)  # Should not crash

    def test_no_structure(self, formatter):
        """Test workout without structure section."""
        workout = {
            "id": "TEST",
            "content": "Simple workout\nNo structure here",
        }
        warnings = formatter.validate_notation(workout)
        assert isinstance(warnings, list)  # Should not crash

    def test_multiple_ramps_same_workout(self, formatter):
        """Test workout with multiple ramps."""
        workout = {
            "id": "TEST",
            "content": """Warmup
- 5min ramp 45%→55% (99W→121W) 85rpm
- 5min ramp 55%→65% (121W→143W) 85rpm

Main set
- 30min 70% FTP (154W) 90rpm

Cooldown
- 10min ramp 65%→50% (143W→110W) 85rpm""",
        }
        warnings = formatter.validate_notation(workout)
        # Should validate all ramps correctly
        assert not any("sans watts explicites" in w for w in warnings)


class TestFormatOutput:
    """Tests pour le format de sortie."""

    def test_delimiter_format(self, formatter):
        """Test delimiter format is correct."""
        workout = {
            "name": "S075-01-END-Test-V001",
            "content": "Test content",
        }
        formatted = formatter.format_for_upload([workout])

        lines = formatted.split("\n")
        assert lines[0] == "=== WORKOUT S075-01-END-Test-V001 ==="
        assert "=== FIN WORKOUT ===" in formatted

    def test_empty_line_between_workouts(self, formatter):
        """Test empty line separates workouts."""
        workouts = [
            {"name": "S075-01-Test", "content": "Content 1"},
            {"name": "S075-02-Test", "content": "Content 2"},
        ]
        formatted = formatter.format_for_upload(workouts)

        # Should have empty line between FIN WORKOUT and next WORKOUT
        assert "\n\n=== WORKOUT S075-02" in formatted
