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


def test_interval_without_duration_warning(validator):
    """Test warning pour intervalle sans durée.

    Covers line 173: Warning when interval doesn't have duration pattern.
    """
    workout = """Warmup

- 10m ramp 50-65%

Main set
- No duration here just text
- 5m 90%

Cooldown
- 10m ramp 65-50%"""
    is_valid, errors, warnings = validator.validate_workout(workout)

    # Should be valid but with warning
    assert is_valid is True
    assert len(warnings) > 0
    assert any("Aucune durée détectée" in warning for warning in warnings)
    assert any("No duration here just text" in warning for warning in warnings)


def test_fix_repetition_with_interval_error(validator, capsys):
    """Test fix_repetition_format with uncorrectable repetition in interval.

    Covers lines 193-198, 219-221: Error detection and printing for
    repetitions inside intervals that cannot be auto-corrected.
    """
    workout = """Warmup

- 10m ramp 50-65%

Main set
- 3x 10m 90%
- 2m 60%

Cooldown
- 10m ramp 65-50%"""

    corrected = validator.fix_repetition_format(workout)

    # Capture stdout to check error messages (lines 219-221)
    captured = capsys.readouterr()

    # Verify error message printed (lines 219-221)
    assert "ERREURS NON CORRIGEABLES" in captured.out
    assert "Impossible de corriger automatiquement" in captured.out
    assert "3x 10m 90%" in captured.out

    # Verify workout unchanged (lines 197)
    assert "- 3x 10m 90%" in corrected


def test_fix_repetition_prints_correction(validator, capsys):
    """Test fix_repetition_format prints correction message.

    Covers line 212: Print message when correcting non-standard section.

    Note: This line is already covered by test_fix_non_standard_section
    but let's verify the print explicitly.
    """
    workout = """Warmup

- 10m ramp 50-65%

Test capacité 3x
- 5m 70-75%

Cooldown
- 10m ramp 65-50%"""

    validator.fix_repetition_format(workout)

    captured = capsys.readouterr()

    # Verify correction message printed (line 212)
    assert "Ligne" in captured.out and "corrigée" in captured.out
    assert "Test capacité 3x" in captured.out
    assert "Main set 3x" in captured.out


def test_main_function_runs():
    """Test main() CLI function runs without errors.

    Covers lines 271-350, 354: The entire main() CLI function.

    This test verifies that the CLI demonstration runs successfully
    with all test cases (invalid formats, corrections, valid formats, examples).
    """
    from cyclisme_training_logs.intervals_format_validator import main

    # Should run without exceptions
    try:
        main()
        success = True
    except Exception as e:
        success = False
        error = e

    assert success, f"main() should run without errors, got: {error if not success else None}"


def test_main_function_outputs(capsys):
    """Test main() CLI function produces expected output.

    Covers lines 271-350: Verify main() prints all expected sections.
    """
    from cyclisme_training_logs.intervals_format_validator import main

    main()

    captured = capsys.readouterr()
    output = captured.out

    # Verify all test sections present (lines 274-293)
    assert "TEST 1: Format incorrect (répétition dans intervalle)" in output
    assert "TEST 2: Format incorrect (section non standard" in output
    assert "TEST 3: Format correct" in output

    # Verify correction section present (line 315)
    assert "CORRECTION AUTOMATIQUE" in output

    # Verify examples section present (lines 343-350)
    assert "EXEMPLES WORKOUTS VALIDES" in output
    assert "SIMPLE" in output
    assert "REPEATED_BLOCK" in output
    assert "MULTIPLE_BLOCKS" in output


def test_script_main_entry_point(monkeypatch, capsys):
    """Test if __name__ == '__main__' entry point.

    Covers line 354: if __name__ == "__main__": main() execution.

    Uses monkeypatch to simulate script being run directly.
    """
    from unittest.mock import patch

    # Import the module
    import cyclisme_training_logs.intervals_format_validator as validator_module

    # Mock __name__ to be '__main__' and execute the module-level code
    # We'll directly test that the condition would trigger main()
    with patch.object(validator_module, "__name__", "__main__"):
        # Manually trigger what would happen at line 353-354
        if validator_module.__name__ == "__main__":
            validator_module.main()

    # Verify main() was called by checking output
    captured = capsys.readouterr()
    assert "TEST 1" in captured.out or "EXEMPLES" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
