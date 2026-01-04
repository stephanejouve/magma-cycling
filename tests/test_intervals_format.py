#!/usr/bin/env python3
"""
test_intervals_format.py - Tests validation format Intervals.icu.
"""
import pytest

from cyclisme_training_logs.intervals_format_validator import IntervalsFormatValidator


@pytest.fixture
def validator():
    """Fixture validateur."""
    return IntervalsFormatValidator()


def test_valid_simple_workout(validator):
    """Test workout simple valide."""
    workout = """Warmup

- 10m ramp 50-65% 85rpm

Main set
- 20m 75% 88rpm

Cooldown
- 10m ramp 65-50% 85rpm"""
    is_valid, errors, warnings = validator.validate_workout(workout)

    assert is_valid is True
    assert len(errors) == 0


def test_valid_repeated_block(validator):
    """Test bloc répété valide."""
    workout = """Warmup

- 10m ramp 50-75% 85rpm

Main set 3x
- 10m 90% 92rpm
- 4m 62% 85rpm

Cooldown
- 10m ramp 75-50% 85rpm"""
    is_valid, errors, warnings = validator.validate_workout(workout)

    assert is_valid is True
    assert len(errors) == 0


def test_invalid_repetition_in_interval(validator):
    """Test répétition dans intervalle (INVALIDE)."""
    workout = """Warmup

- 10m ramp 50-65%

Main set
- 3x 10m 90%
- 2m 60%

Cooldown
- 10m ramp 65-50%"""
    is_valid, errors, warnings = validator.validate_workout(workout)

    assert is_valid is False
    assert len(errors) > 0
    assert any("Répétition dans intervalle" in error for error in errors)


def test_invalid_repetition_alone(validator):
    """Test répétition seule sur ligne (INVALIDE)."""
    workout = """Warmup

- 10m ramp 50-65%

3x
- 10m 90%
- 2m 60%

Cooldown
- 10m ramp 65-50%"""
    is_valid, errors, warnings = validator.validate_workout(workout)

    assert is_valid is False
    assert len(errors) > 0
    assert any("Répétition" in error and "seule" in error for error in errors)


def test_warning_non_standard_section(validator):
    """Test section non standard avec répétition (WARNING)."""
    workout = """Warmup

- 10m ramp 50-65%

Test capacité 3x
- 5m 70-75%
- 3m 60%

Cooldown
- 10m ramp 65-50%"""
    is_valid, errors, warnings = validator.validate_workout(workout)

    # Valide techniquement, mais warning
    assert is_valid is True
    assert len(warnings) > 0
    assert any("non standard" in warning for warning in warnings)


def test_invalid_markdown(validator):
    """Test contenu markdown (INVALIDE)."""
    workout = """Warmup

- 10m ramp 50-65%

**Main set**
- 10m 90%

Cooldown
- 10m ramp 65-50%"""
    is_valid, errors, warnings = validator.validate_workout(workout)

    assert is_valid is False
    assert any("markdown" in error.lower() for error in errors)


def test_fix_non_standard_section(validator):
    """Test correction automatique section non standard."""
    workout = """Warmup

- 10m ramp 50-65%

Test capacité 3x
- 5m 70-75%
- 3m 60%

Cooldown
- 10m ramp 65-50%"""
    corrected = validator.fix_repetition_format(workout)

    assert "Main set 3x" in corrected
    assert "Test capacité 3x" not in corrected


def test_multiple_repeated_blocks(validator):
    """Test plusieurs blocs répétés valides."""
    workout = """Warmup

- 15m ramp 50-75% 85-90rpm

Main set 2x
- 5m 110% 95rpm
- 3m 55% 85rpm

Block 3x
- 1m 120% 100rpm
- 2m 60% 85rpm

Cooldown
- 12m ramp 75-50% 85rpm"""
    is_valid, errors, warnings = validator.validate_workout(workout)

    assert is_valid is True
    assert len(errors) == 0


def test_generate_examples(validator):
    """Test génération exemples."""
    examples = validator.generate_example_workouts()

    assert "simple" in examples
    assert "repeated_block" in examples
    assert "multiple_blocks" in examples

    # Vérifier que les exemples sont valides
    for name, workout in examples.items():
        is_valid, errors, warnings = validator.validate_workout(workout)
        assert is_valid is True, f"Example '{name}' devrait être valide"


def test_empty_workout(validator):
    """Test workout vide."""
    workout = ""

    is_valid, errors, warnings = validator.validate_workout(workout)
    # Workout vide techniquement valide (pas d'erreurs)
    assert is_valid is True


def test_workout_without_sections(validator):
    """Test workout sans sections (juste intervalles)."""
    workout = """- 10m 50%

- 20m 70%
- 10m 50%"""
    is_valid, errors, warnings = validator.validate_workout(workout)

    # Valide mais peut avoir warnings sur durées
    assert is_valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
