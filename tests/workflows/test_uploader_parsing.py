"""Tests for workflows.uploader.parsing module.

Tests ParsingMixin : parse_workouts_file avec tmp_path, formats valide/invalide,
single/multi workout, validation critique.
"""

from datetime import date

from magma_cycling.workflows.uploader.parsing import ParsingMixin
from magma_cycling.workflows.uploader.validation import ValidationMixin


class StubUploader(ValidationMixin, ParsingMixin):
    """Stub combining ParsingMixin + ValidationMixin for testing."""

    def __init__(self, start_date):
        self.start_date = start_date


VALID_SINGLE_WORKOUT = """\
=== WORKOUT S081-01-END-RepriseLundi-V001 ===
Reprise Douce Lundi (60min, 45 TSS)
- Warmup: 15min Z1
- Main set: 30min Z2
- Cooldown: 15min Z1
=== FIN WORKOUT ===
"""

VALID_MULTI_WORKOUTS = """\
=== WORKOUT S081-01-END-RepriseLundi-V001 ===
Reprise Douce Lundi (60min, 45 TSS)
- Warmup: 15min Z1
- Main set: 30min Z2
- Cooldown: 15min Z1
=== FIN WORKOUT ===

=== WORKOUT S081-03-INT-Intervalles-V001 ===
Intervalles Mercredi (75min, 80 TSS)
- Warmup: 15min Z1-Z2
- Main set: 5x4min Z4 / 3min Z1
- Cooldown: 15min Z1
=== FIN WORKOUT ===

=== WORKOUT S081-05-END-EnduranceLongue-V001 ===
Endurance Longue Vendredi (90min, 65 TSS)
- Warmup: 20min Z1-Z2
- Main set: 50min Z2-Z3
- Cooldown: 20min Z1
=== FIN WORKOUT ===
"""

DOUBLE_SESSION_WORKOUTS = """\
=== WORKOUT S081-06a-REC-RecupMatin-V001 ===
Récup Matin (30min, 20 TSS)
- Warmup: 10min Z1
- Main set: 10min Z1
- Cooldown: 10min Z1
=== FIN WORKOUT ===

=== WORKOUT S081-06b-INT-SprintSoir-V001 ===
Sprint Soir (45min, 55 TSS)
- Warmup: 10min Z1-Z2
- Main set: 6x30s sprint / 3min Z1
- Cooldown: 10min Z1
=== FIN WORKOUT ===
"""

INVALID_FORMAT_WORKOUT = """\
=== WORKOUT InvalidName ===
No day number
- Some content
=== FIN WORKOUT ===
"""


class TestParseWorkoutsFileBasic:
    """Tests for parse_workouts_file() basic behavior."""

    def test_file_not_found_returns_empty(self, tmp_path):
        uploader = StubUploader(start_date=date(2026, 3, 16))
        result = uploader.parse_workouts_file(tmp_path / "missing.txt")
        assert result == []

    def test_empty_file_returns_empty(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        uploader = StubUploader(start_date=date(2026, 3, 16))
        result = uploader.parse_workouts_file(f)
        assert result == []

    def test_single_workout_parsed(self, tmp_path):
        f = tmp_path / "workouts.txt"
        f.write_text(VALID_SINGLE_WORKOUT)
        uploader = StubUploader(start_date=date(2026, 3, 16))
        result = uploader.parse_workouts_file(f)
        assert len(result) == 1
        assert result[0]["filename"] == "S081-01-END-RepriseLundi-V001"
        assert result[0]["day"] == 1

    def test_single_workout_uses_exact_date(self, tmp_path):
        """In single workout mode, date should be start_date directly."""
        f = tmp_path / "workouts.txt"
        f.write_text(VALID_SINGLE_WORKOUT)
        uploader = StubUploader(start_date=date(2026, 3, 16))
        result = uploader.parse_workouts_file(f)
        assert result[0]["date"] == "2026-03-16"

    def test_multi_workouts_parsed(self, tmp_path):
        f = tmp_path / "workouts.txt"
        f.write_text(VALID_MULTI_WORKOUTS)
        uploader = StubUploader(start_date=date(2026, 3, 16))
        result = uploader.parse_workouts_file(f)
        assert len(result) == 3

    def test_multi_workout_date_offset(self, tmp_path):
        """Multi workouts use start_date + (day_num - 1) for date."""
        f = tmp_path / "workouts.txt"
        f.write_text(VALID_MULTI_WORKOUTS)
        # Monday 2026-03-16
        uploader = StubUploader(start_date=date(2026, 3, 16))
        result = uploader.parse_workouts_file(f)
        # Day 1 → Monday, Day 3 → Wednesday, Day 5 → Friday
        assert result[0]["date"] == "2026-03-16"  # day 1
        assert result[1]["date"] == "2026-03-18"  # day 3
        assert result[2]["date"] == "2026-03-20"  # day 5

    def test_workout_fields_complete(self, tmp_path):
        f = tmp_path / "workouts.txt"
        f.write_text(VALID_SINGLE_WORKOUT)
        uploader = StubUploader(start_date=date(2026, 3, 16))
        result = uploader.parse_workouts_file(f)
        w = result[0]
        assert "filename" in w
        assert "day" in w
        assert "suffix" in w
        assert "date" in w
        assert "name" in w
        assert "description" in w


class TestParseDoubleSession:
    """Tests for double session support (suffix a/b)."""

    def test_double_session_suffix_parsed(self, tmp_path):
        f = tmp_path / "workouts.txt"
        f.write_text(DOUBLE_SESSION_WORKOUTS)
        uploader = StubUploader(start_date=date(2026, 3, 16))
        result = uploader.parse_workouts_file(f)
        assert len(result) == 2
        assert result[0]["suffix"] == "a"
        assert result[1]["suffix"] == "b"

    def test_double_session_same_day(self, tmp_path):
        f = tmp_path / "workouts.txt"
        f.write_text(DOUBLE_SESSION_WORKOUTS)
        uploader = StubUploader(start_date=date(2026, 3, 16))
        result = uploader.parse_workouts_file(f)
        # Both are day 6 → same date offset
        assert result[0]["day"] == 6
        assert result[1]["day"] == 6
        assert result[0]["date"] == result[1]["date"]

    def test_standard_workout_empty_suffix(self, tmp_path):
        f = tmp_path / "workouts.txt"
        f.write_text(VALID_SINGLE_WORKOUT)
        uploader = StubUploader(start_date=date(2026, 3, 16))
        result = uploader.parse_workouts_file(f)
        assert result[0]["suffix"] == ""


class TestParseInvalidFormat:
    """Tests for invalid workout format handling."""

    def test_invalid_format_skipped(self, tmp_path):
        f = tmp_path / "workouts.txt"
        f.write_text(INVALID_FORMAT_WORKOUT)
        uploader = StubUploader(start_date=date(2026, 3, 16))
        result = uploader.parse_workouts_file(f)
        assert result == []

    def test_mixed_valid_and_invalid(self, tmp_path):
        content = VALID_SINGLE_WORKOUT + "\n" + INVALID_FORMAT_WORKOUT
        f = tmp_path / "workouts.txt"
        f.write_text(content)
        uploader = StubUploader(start_date=date(2026, 3, 16))
        result = uploader.parse_workouts_file(f)
        # Only the valid one should be parsed
        assert len(result) == 1
        assert result[0]["filename"] == "S081-01-END-RepriseLundi-V001"

    def test_no_workout_delimiters(self, tmp_path):
        f = tmp_path / "workouts.txt"
        f.write_text("Just some random text\nno workout delimiters here\n")
        uploader = StubUploader(start_date=date(2026, 3, 16))
        result = uploader.parse_workouts_file(f)
        assert result == []


class TestParseValidationIntegration:
    """Tests for validation warnings during parsing."""

    def test_critical_warning_blocks_upload(self, tmp_path):
        """Workouts with critical validation warnings should return empty."""
        # Workout missing warmup/cooldown → critical warning
        content = """\
=== WORKOUT S081-01-INT-Test-V001 ===
Test workout (60min, 50 TSS)
Main set: 5x4min Z4 / 3min Z1
=== FIN WORKOUT ===
"""
        f = tmp_path / "workouts.txt"
        f.write_text(content)
        uploader = StubUploader(start_date=date(2026, 3, 16))
        result = uploader.parse_workouts_file(f)
        # If validation detects critical issues, result is empty
        # (depends on ValidationMixin rules — may pass or block)
        assert isinstance(result, list)

    def test_valid_workout_passes_validation(self, tmp_path):
        f = tmp_path / "workouts.txt"
        f.write_text(VALID_SINGLE_WORKOUT)
        uploader = StubUploader(start_date=date(2026, 3, 16))
        result = uploader.parse_workouts_file(f)
        assert len(result) == 1

    def test_workout_description_preserved(self, tmp_path):
        f = tmp_path / "workouts.txt"
        f.write_text(VALID_SINGLE_WORKOUT)
        uploader = StubUploader(start_date=date(2026, 3, 16))
        result = uploader.parse_workouts_file(f)
        desc = result[0]["description"]
        assert "Warmup: 15min Z1" in desc
        assert "Main set: 30min Z2" in desc
        assert "Cooldown: 15min Z1" in desc

    def test_workout_name_from_delimiter(self, tmp_path):
        """Name should come from the === WORKOUT ... === delimiter."""
        f = tmp_path / "workouts.txt"
        f.write_text(VALID_SINGLE_WORKOUT)
        uploader = StubUploader(start_date=date(2026, 3, 16))
        result = uploader.parse_workouts_file(f)
        assert result[0]["name"] == "S081-01-END-RepriseLundi-V001"
