"""Tests for IntervalsFormatValidator duration and ramp rules."""

from magma_cycling.intervals_format_validator import IntervalsFormatValidator


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


class TestWarmupCooldownMonoBloc:
    """Tests for mono-bloc warmup/cooldown detection."""

    def test_warmup_mono_bloc_warns(self):
        """Single warmup block without justification triggers warning."""
        v = IntervalsFormatValidator()
        workout = "Warmup\n- 15m 65% 85rpm\n\nMain set\n- 20m 90% 92rpm\n\nCooldown\n- 5m 50% 85rpm\n- 5m 45% 80rpm"
        is_valid, _errors, warnings = v.validate_workout(workout)
        assert is_valid
        assert any("Warmup mono-bloc" in w for w in warnings)

    def test_cooldown_mono_bloc_warns(self):
        """Single cooldown block without justification triggers warning."""
        v = IntervalsFormatValidator()
        workout = "Warmup\n- 5m 50% 85rpm\n- 5m 58% 85rpm\n- 5m 65% 85rpm\n\nMain set\n- 20m 90% 92rpm\n\nCooldown\n- 13m 55% 85rpm"
        is_valid, _errors, warnings = v.validate_workout(workout)
        assert is_valid
        assert any("Cooldown mono-bloc" in w for w in warnings)

    def test_warmup_ramp_no_warning(self):
        """Multi-step warmup does not trigger warning."""
        v = IntervalsFormatValidator()
        workout = "Warmup\n- 5m 50% 85rpm\n- 5m 58% 85rpm\n- 5m 65% 85rpm\n\nMain set\n- 20m 90%\n\nCooldown\n- 5m 60%\n- 5m 50%"
        _valid, _errors, warnings = v.validate_workout(workout)
        assert not any("mono-bloc" in w for w in warnings)

    def test_warmup_mono_bloc_with_justification_no_warning(self):
        """Mono-bloc warmup with gear justification does not warn."""
        v = IntervalsFormatValidator()
        workout = (
            "Warmup\n- 15m 65% 85rpm\n"
            "\u2699\ufe0f Bloc plat intentionnel \u2014 pr\u00e9servation fra\u00eecheur\n"
            "\nMain set\n- 20m 90%\n\nCooldown\n- 5m 60%\n- 5m 50%"
        )
        _valid, _errors, warnings = v.validate_workout(workout)
        assert not any("Warmup mono-bloc" in w for w in warnings)

    def test_cooldown_mono_bloc_with_justification_no_warning(self):
        """Mono-bloc cooldown with gear justification does not warn."""
        v = IntervalsFormatValidator()
        workout = (
            "Warmup\n- 5m 50%\n- 5m 60%\n\nMain set\n- 20m 90%\n"
            "\nCooldown\n- 10m 55% 85rpm\n"
            "\u2699\ufe0f Cooldown court intentionnel"
        )
        _valid, _errors, warnings = v.validate_workout(workout)
        assert not any("Cooldown mono-bloc" in w for w in warnings)

    def test_mono_bloc_is_warning_not_error(self):
        """Mono-bloc detection is a warning, not an error (non-blocking)."""
        v = IntervalsFormatValidator()
        workout = "Warmup\n- 15m 65% 85rpm\n\nMain set\n- 20m 90%\n\nCooldown\n- 10m 55%"
        is_valid, errors, warnings = v.validate_workout(workout)
        assert is_valid
        assert len(errors) == 0
        assert len(warnings) == 2  # both warmup and cooldown

    def test_auto_fix_warmup_mono_bloc(self):
        """Auto-fix replaces mono-bloc warmup with 3-step ramp."""
        v = IntervalsFormatValidator()
        workout = "Warmup\n- 15m 65% 85rpm\n\nMain set\n- 20m 90%\n\nCooldown\n- 5m 60%\n- 5m 50%"
        fixed = v.fix_warmup_cooldown(workout)
        warmup_lines = []
        in_warmup = False
        for line in fixed.split("\n"):
            s = line.strip()
            if s.lower().startswith("warmup"):
                in_warmup = True
                continue
            if in_warmup and s.lower().startswith(("main", "cooldown", "block")):
                break
            if in_warmup and s.startswith("- "):
                warmup_lines.append(s)
        assert len(warmup_lines) == 3
        assert "50%" in warmup_lines[0]
        assert "65%" in warmup_lines[2]

    def test_auto_fix_no_change_with_justification(self):
        """Auto-fix does not modify mono-bloc with justification."""
        v = IntervalsFormatValidator()
        workout = (
            "Warmup\n- 15m 65% 85rpm\n"
            "\u2699\ufe0f Intentionnel\n"
            "\nMain set\n- 20m 90%\n\nCooldown\n- 5m 60%\n- 5m 50%"
        )
        fixed = v.fix_warmup_cooldown(workout)
        assert "- 15m 65% 85rpm" in fixed


class TestNotesSectionFiltering:
    """Section M regression: skip validation in non-workout sections.

    Before fix: any line starting with "-" was validated for duration
    suffix, even if it lived in a "Notes execution", "Plan B",
    "Hydratation" etc. section — producing false-positive errors like
    "Ligne 16: Durée invalide '90min'" when "1L+ pour 90min" was a
    legitimate coaching note. After fix: only lines under
    Warmup/Main set/Cooldown/Block are validated; lines under other
    section titles are ignored.
    """

    def test_s094_02_intro_30min_in_notes_no_error(self):
        """S094-02 regression: '30min' mentioned in notes section under non-workout title."""
        validator = IntervalsFormatValidator()
        workout = (
            "Warmup\n- 10m ramp 50-75% 85rpm\n"
            "\nMain set\n- 30m 75%\n"
            "\nCooldown\n- 10m ramp 75-50% 85rpm\n"
            "\nNotes execution\n- Tempo progressif sur 30min puis relax\n"
        )
        is_valid, errors, _warnings = validator.validate_workout(workout)
        assert is_valid, f"unexpected errors: {errors}"

    def test_s094_04_plan_b_45min_in_notes_no_error(self):
        """S094-04 regression: 'Plan B 45min' in notes must not fail validation."""
        validator = IntervalsFormatValidator()
        workout = (
            "Warmup\n- 10m ramp 50-75% 85rpm\n"
            "\nMain set\n- 75m 70%\n"
            "\nCooldown\n- 10m ramp 75-50% 85rpm\n"
            "\nPlan B\n- Si pluie: indoor 45min Z2\n"
        )
        is_valid, errors, _warnings = validator.validate_workout(workout)
        assert is_valid, f"unexpected errors: {errors}"

    def test_s094_06_hydration_90min_in_notes_no_error(self):
        """S094-06 regression: '90min' in hydration note must not fail."""
        validator = IntervalsFormatValidator()
        workout = (
            "Warmup\n- 10m ramp 50-75% 85rpm\n"
            "\nMain set\n- 70m 70%\n"
            "\nCooldown\n- 10m ramp 75-50% 85rpm\n"
            "\nHydratation\n- 1L+ pour 90min effort\n"
        )
        is_valid, errors, _warnings = validator.validate_workout(workout)
        assert is_valid, f"unexpected errors: {errors}"

    def test_invalid_duration_in_workout_section_still_rejected(self):
        """Anti-false-negative: '30min' in Main set MUST still be flagged."""
        validator = IntervalsFormatValidator()
        workout = (
            "Warmup\n- 10m ramp 50-75% 85rpm\n"
            "\nMain set\n- 30min 75%\n"
            "\nCooldown\n- 10m ramp 75-50% 85rpm\n"
        )
        is_valid, errors, _warnings = validator.validate_workout(workout)
        assert not is_valid
        assert any("30min" in e for e in errors)

    def test_invalid_duration_in_block_section_still_rejected(self):
        """Block section also counts as workout section — must validate."""
        validator = IntervalsFormatValidator()
        workout = (
            "Warmup\n- 10m ramp 50-75% 85rpm\n"
            "\nBlock 3x\n- 5min 95%\n- 3m 60%\n"
            "\nCooldown\n- 10m ramp 75-50% 85rpm\n"
        )
        is_valid, errors, _warnings = validator.validate_workout(workout)
        assert not is_valid
        assert any("5min" in e for e in errors)

    def test_multiple_invalid_durations_in_notes_no_error(self):
        """Multiple bogus 'Xmin' across several non-workout sections all skipped."""
        validator = IntervalsFormatValidator()
        workout = (
            "Warmup\n- 10m ramp 50-75% 85rpm\n"
            "\nMain set\n- 60m 75%\n"
            "\nCooldown\n- 10m ramp 75-50% 85rpm\n"
            "\nNotes execution\n- Intro 30min easy\n"
            "\nPlan B\n- Si météo défavorable, indoor 45min Z2\n"
            "\nHydratation\n- 1L+ pour 90min effort\n"
            "\nItinéraire\n- Boucle 75min via Z3\n"
        )
        is_valid, errors, _warnings = validator.validate_workout(workout)
        assert is_valid, f"unexpected errors: {errors}"

    def test_switch_back_to_workout_section_after_notes(self):
        """Notes → return to Cooldown: validation must resume."""
        validator = IntervalsFormatValidator()
        workout = (
            "Warmup\n- 10m ramp 50-75% 85rpm\n"
            "\nMain set\n- 60m 75%\n"
            "\nNotes\n- Garder cadence 90rpm sur 30min\n"
            "\nCooldown\n- 10min ramp 75-50%\n"
        )
        is_valid, errors, _warnings = validator.validate_workout(workout)
        assert not is_valid
        assert any("10min" in e for e in errors), f"expected 10min flag, got: {errors}"
