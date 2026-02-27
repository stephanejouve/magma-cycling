"""Tests for IntervalsFormatValidator duration and ramp rules."""

from cyclisme_training_logs.intervals_format_validator import IntervalsFormatValidator


class TestDurationValidation:
    """Tests for valid/invalid duration suffixes."""

    def test_valid_durations_accepted(self):
        """5m, 30s, 2h are valid Intervals.icu durations."""
        validator = IntervalsFormatValidator()
        workout = "Warmup\n- 5m 90%\n- 30s 80%\n- 2h 60%"
        is_valid, errors, warnings = validator.validate_workout(workout)
        assert is_valid
        assert errors == []

    def test_invalid_duration_min_rejected(self):
        """'5min' is not a valid duration — must use '5m'."""
        validator = IntervalsFormatValidator()
        workout = "Main set\n- 5min 90%"
        is_valid, errors, _warnings = validator.validate_workout(workout)
        assert not is_valid
        assert any("5min" in e for e in errors)

    def test_invalid_duration_sec_rejected(self):
        """'10sec' is not a valid duration — must use '10s'."""
        validator = IntervalsFormatValidator()
        workout = "Main set\n- 10sec 80%"
        is_valid, errors, _warnings = validator.validate_workout(workout)
        assert not is_valid
        assert any("10sec" in e for e in errors)

    def test_invalid_duration_hr_rejected(self):
        """'1hr' is not a valid duration — must use '1h'."""
        validator = IntervalsFormatValidator()
        workout = "Main set\n- 1hr 60%"
        is_valid, errors, _warnings = validator.validate_workout(workout)
        assert not is_valid
        assert any("1hr" in e for e in errors)


class TestRampValidation:
    """Tests for ramp format (dash required between bounds)."""

    def test_ramp_with_dash_accepted(self):
        """'ramp 50-65%' is valid ramp format."""
        validator = IntervalsFormatValidator()
        workout = "Warmup\n- 10m ramp 50-65%"
        is_valid, errors, _warnings = validator.validate_workout(workout)
        assert is_valid
        assert errors == []

    def test_ramp_without_dash_rejected(self):
        """'ramp 40 50%' is invalid — must be 'ramp 40-50%'."""
        validator = IntervalsFormatValidator()
        workout = "Warmup\n- 10m ramp 40 50%"
        is_valid, errors, _warnings = validator.validate_workout(workout)
        assert not is_valid
        assert any("ramp" in e.lower() for e in errors)

    def test_ramp_missing_percent_rejected(self):
        """'ramp 40-50' without % is invalid — must be 'ramp 40-50%'."""
        validator = IntervalsFormatValidator()
        workout = "Warmup\n- 10m ramp 40-50"
        is_valid, errors, _warnings = validator.validate_workout(workout)
        assert not is_valid
        assert any("ramp" in e.lower() for e in errors)
