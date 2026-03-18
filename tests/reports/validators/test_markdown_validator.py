"""Tests for reports.validators.markdown_validator module.

Tests MarkdownValidator: validate_report, structure validation, required sections,
metrics consistency (hallucination detection), word counting, section extraction.
"""

import pytest

from magma_cycling.reports.validators.markdown_validator import (
    MarkdownValidator,
    ValidationResult,
)


@pytest.fixture
def validator():
    return MarkdownValidator()


# ─── ValidationResult dataclass ─────────────────────────────────────


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_valid_result(self):
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        assert result.is_valid is True
        assert result.metrics is None

    def test_invalid_result(self):
        result = ValidationResult(
            is_valid=False,
            errors=["Missing section"],
            warnings=["Too short"],
            metrics={"word_count": 50},
        )
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.metrics["word_count"] == 50


# ─── validate_report ────────────────────────────────────────────────


class TestValidateReport:
    """Tests for validate_report()."""

    def test_invalid_report_type_raises(self, validator):
        with pytest.raises(ValueError, match="Invalid report type"):
            validator.validate_report("# Title", "unknown_type", {})

    def test_valid_workout_history(self, validator):
        content = (
            "# Workout History S076\n\n"
            "## Contexte Semaine\nSemaine productive.\n\n"
            "## Chronologie Complète\nLundi : repos.\n\n"
            "## Métriques Évolution\nTSS en hausse.\n\n"
            "## Enseignements Majeurs\nBonne progression.\n\n"
            + ("Lorem ipsum dolor sit amet. " * 50)
        )
        result = validator.validate_report(content, "workout_history", {"week_number": "S076"})
        assert result.is_valid is True

    def test_valid_bilan_final(self, validator):
        content = (
            "# Bilan Final S076\n\n"
            "## Semaine en Chiffres\n5 séances.\n\n"
            "## Métriques Finales\nTSS : 450\n\n"
            "## Découvertes Majeures\nProgression notable.\n\n"
            "## Conclusion\nBonne semaine.\n\n" + ("Mot " * 400)
        )
        result = validator.validate_report(content, "bilan_final", {"week_number": "S076"})
        assert result.is_valid is True

    def test_missing_sections_invalid(self, validator):
        content = "# Workout History S076\n\n## Random Section\nNothing relevant.\n"
        result = validator.validate_report(content, "workout_history", {"week_number": "S076"})
        assert result.is_valid is False
        assert any("Missing required section" in e for e in result.errors)

    def test_metrics_in_result(self, validator):
        content = (
            "# Bilan Final S076\n\n"
            "## Semaine en Chiffres\nDonnées.\n\n"
            "## Métriques Finales\nStats.\n\n"
            "## Découvertes Majeures\nInsights.\n\n"
            "## Conclusion\nFin.\n"
        )
        result = validator.validate_report(content, "bilan_final", {"week_number": "S076"})
        assert "word_count" in result.metrics
        assert "section_count" in result.metrics
        assert result.metrics["section_count"] == 4


# ─── _validate_markdown_structure ────────────────────────────────────


class TestValidateMarkdownStructure:
    """Tests for _validate_markdown_structure()."""

    def test_valid_structure(self, validator):
        content = "# Title\n\n## Section 1\nContent.\n\n## Section 2\nMore content.\n"
        errors = validator._validate_markdown_structure(content)
        assert errors == []

    def test_missing_main_title(self, validator):
        content = "## Section 1\nContent.\n"
        errors = validator._validate_markdown_structure(content)
        assert any("Missing main title" in e for e in errors)

    def test_missing_sections(self, validator):
        content = "# Title\nJust a title with no sections.\n"
        errors = validator._validate_markdown_structure(content)
        assert any("Missing sections" in e for e in errors)

    def test_title_with_hash_in_content(self, validator):
        content = "# Main Title\n\n## Section\nSome content with #hashtag.\n"
        errors = validator._validate_markdown_structure(content)
        assert errors == []


# ─── _validate_required_sections ─────────────────────────────────────


class TestValidateRequiredSections:
    """Tests for _validate_required_sections()."""

    def test_all_workout_history_sections(self, validator):
        content = (
            "## Contexte Semaine\n"
            "## Chronologie Complète\n"
            "## Métriques Évolution\n"
            "## Enseignements Majeurs\n"
        )
        errors = validator._validate_required_sections(content, "workout_history")
        assert errors == []

    def test_all_bilan_final_sections(self, validator):
        content = (
            "## Semaine en Chiffres\n"
            "## Métriques Finales\n"
            "## Découvertes Majeures\n"
            "## Conclusion\n"
        )
        errors = validator._validate_required_sections(content, "bilan_final")
        assert errors == []

    def test_missing_one_section(self, validator):
        content = "## Contexte Semaine\n" "## Chronologie Complète\n" "## Métriques Évolution\n"
        errors = validator._validate_required_sections(content, "workout_history")
        assert len(errors) == 1
        assert "Enseignements Majeurs" in errors[0]

    def test_case_insensitive_matching(self, validator):
        content = (
            "## contexte semaine\n"
            "## chronologie complète\n"
            "## métriques évolution\n"
            "## enseignements majeurs\n"
        )
        errors = validator._validate_required_sections(content, "workout_history")
        assert errors == []

    def test_flexible_spacing(self, validator):
        content = (
            "## Contexte  Semaine\n"
            "## Chronologie  Complète\n"
            "## Métriques  Évolution\n"
            "## Enseignements  Majeurs\n"
        )
        errors = validator._validate_required_sections(content, "workout_history")
        assert errors == []

    def test_unknown_report_type_no_required(self, validator):
        errors = validator._validate_required_sections("## Random", "unknown_type")
        assert errors == []


# ─── _validate_metrics_consistency ───────────────────────────────────


class TestValidateMetricsConsistency:
    """Tests for _validate_metrics_consistency() — hallucination detection."""

    def test_matching_week_number(self, validator):
        content = "# Report S076\nSome content."
        errors = validator._validate_metrics_consistency(
            content, {"week_number": "S076"}, "bilan_final"
        )
        assert errors == []

    def test_mismatched_week_number(self, validator):
        content = "# Report S077\nWrong week."
        errors = validator._validate_metrics_consistency(
            content, {"week_number": "S076"}, "bilan_final"
        )
        assert any("Week number mismatch" in e for e in errors)

    def test_no_week_in_content(self, validator):
        content = "# Weekly Report\nNo week number mentioned."
        errors = validator._validate_metrics_consistency(
            content, {"week_number": "S076"}, "bilan_final"
        )
        assert errors == []

    def test_no_week_in_source_data(self, validator):
        content = "# Report S076\nContent."
        errors = validator._validate_metrics_consistency(content, {}, "bilan_final")
        assert errors == []

    def test_activity_count_match(self, validator):
        content = "# Report S076\nComplété 5 séances cette semaine."
        activities = [{"id": i} for i in range(5)]
        errors = validator._validate_metrics_consistency(
            content, {"week_number": "S076", "activities": activities}, "bilan_final"
        )
        assert errors == []

    def test_activity_count_mismatch(self, validator):
        content = "# Report S076\nComplété 10 séances cette semaine."
        activities = [{"id": i} for i in range(5)]
        errors = validator._validate_metrics_consistency(
            content, {"week_number": "S076", "activities": activities}, "bilan_final"
        )
        assert any("Activity count mismatch" in e for e in errors)

    def test_activity_count_within_tolerance(self, validator):
        content = "# Report S076\nComplété 6 séances cette semaine."
        activities = [{"id": i} for i in range(5)]
        errors = validator._validate_metrics_consistency(
            content, {"week_number": "S076", "activities": activities}, "bilan_final"
        )
        # 6 vs 5 → diff = 1 → within tolerance
        assert errors == []

    def test_tss_values_present_no_crash(self, validator):
        content = "# Report S076\nTSS : 450\nTSS planifié : 500"
        errors = validator._validate_metrics_consistency(
            content,
            {"week_number": "S076", "tss_planned": 500, "tss_realized": 450},
            "bilan_final",
        )
        assert errors == []


# ─── _count_words ────────────────────────────────────────────────────


class TestCountWords:
    """Tests for _count_words()."""

    def test_plain_text(self, validator):
        assert validator._count_words("Hello world foo bar") == 4

    def test_strips_headers(self, validator):
        content = "# Title\n## Section\nTwo words"
        count = validator._count_words(content)
        # "Title", "Section", "Two", "words" = 4
        assert count == 4

    def test_strips_bold(self, validator):
        content = "This is **bold text** here"
        count = validator._count_words(content)
        assert count == 5

    def test_strips_italic(self, validator):
        content = "This is *italic text* here"
        count = validator._count_words(content)
        assert count == 5

    def test_strips_code_blocks(self, validator):
        content = "Before\n```python\ncode here\n```\nAfter"
        count = validator._count_words(content)
        # "Before", "After" = 2
        assert count == 2

    def test_strips_inline_code(self, validator):
        content = "Use `command` to run"
        count = validator._count_words(content)
        # "Use", "to", "run" = 3
        assert count == 3

    def test_strips_urls(self, validator):
        content = "Visit https://example.com for info"
        count = validator._count_words(content)
        # "Visit", "for", "info" = 3
        assert count == 3

    def test_empty_content(self, validator):
        assert validator._count_words("") == 0


# ─── _extract_sections ──────────────────────────────────────────────


class TestExtractSections:
    """Tests for _extract_sections()."""

    def test_extracts_h2_sections(self, validator):
        content = "# Title\n## Section A\nText\n## Section B\nMore text\n"
        sections = validator._extract_sections(content)
        assert sections == ["Section A", "Section B"]

    def test_ignores_h1_and_h3(self, validator):
        content = "# Title\n## Section\n### Subsection\nText\n"
        sections = validator._extract_sections(content)
        assert sections == ["Section"]

    def test_strips_whitespace(self, validator):
        content = "##  Spaced Section  \n"
        sections = validator._extract_sections(content)
        assert sections == ["Spaced Section"]

    def test_no_sections(self, validator):
        content = "# Just a Title\nNo sections here.\n"
        sections = validator._extract_sections(content)
        assert sections == []

    def test_multiple_sections(self, validator):
        content = "## A\n## B\n## C\n## D\n"
        sections = validator._extract_sections(content)
        assert len(sections) == 4


# ─── Word count warnings ────────────────────────────────────────────


class TestWordCountWarnings:
    """Tests for word count limit warnings in validate_report."""

    def test_exceeds_word_limit(self, validator):
        # workout_history max = 2000 words
        content = (
            "# Workout History S076\n\n"
            "## Contexte Semaine\nContent.\n"
            "## Chronologie Complète\nContent.\n"
            "## Métriques Évolution\nContent.\n"
            "## Enseignements Majeurs\nContent.\n" + ("mot " * 2100)
        )
        result = validator.validate_report(content, "workout_history", {"week_number": "S076"})
        assert any("exceeds limit" in w for w in result.warnings)

    def test_suspiciously_low_word_count(self, validator):
        content = (
            "# Bilan Final S076\n\n"
            "## Semaine en Chiffres\nA.\n"
            "## Métriques Finales\nB.\n"
            "## Découvertes Majeures\nC.\n"
            "## Conclusion\nD.\n"
        )
        result = validator.validate_report(content, "bilan_final", {"week_number": "S076"})
        # Very few words → suspicious
        assert any("suspiciously low" in w for w in result.warnings)
