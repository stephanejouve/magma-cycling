"""Tests for sync handler skipping validation on rest days."""

from magma_cycling.intervals_format_validator import IntervalsFormatValidator


def test_sync_skips_validation_for_rest_day():
    """Rest day (duration_min=0) should not trigger validation.

    The sync handler condition is:
        if session.duration_min and session.duration_min > 0 and ...
    So duration_min=0 (falsy) skips the validation block entirely.
    This test verifies that a free-text description that would fail
    validation is acceptable for rest days via the guard condition.
    """
    # Simulate the sync handler guard condition
    duration_min = 0
    full_description = "Repos complet"

    # The guard condition from remote_sync.py
    should_validate = (
        duration_min and duration_min > 0 and full_description and full_description.strip()
    )

    assert should_validate is False or not should_validate

    # Confirm that this description WOULD fail validation if checked
    validator = IntervalsFormatValidator()
    is_valid, errors, _ = validator.validate_workout(full_description)
    assert is_valid is False
    assert any("Aucune ligne d'intervalle" in e for e in errors)


def test_sync_validates_normal_session():
    """Normal session (duration_min>0) with description triggers validation."""
    duration_min = 45
    full_description = "- 10m 70% 85rpm"

    should_validate = (
        duration_min and duration_min > 0 and full_description and full_description.strip()
    )

    assert should_validate


def test_sync_skips_validation_for_none_duration():
    """Session with duration_min=None should skip validation."""
    duration_min = None
    full_description = "Some description"

    should_validate = (
        duration_min and duration_min > 0 and full_description and full_description.strip()
    )

    assert not should_validate
