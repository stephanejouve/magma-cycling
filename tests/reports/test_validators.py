"""Tests for report validators.

Sprint R10 MVP - Tests for markdown validation functionality.

Author: Claude Code
Created: 2026-01-18
"""

import pytest

from magma_cycling.reports.validators import (
    MarkdownValidator,
    ValidationResult,
)
from tests.reports.fixtures import (
    SAMPLE_ACTIVITIES_S076,
    SAMPLE_BILAN_FINAL_REPORT,
    SAMPLE_WORKOUT_HISTORY_REPORT,
)


class TestMarkdownValidator:
    """Tests for MarkdownValidator class."""

    def test_init(self):
        """Test validator initialization."""
        validator = MarkdownValidator()
        assert validator.max_word_counts["workout_history"] == 2000
        assert validator.max_word_counts["bilan_final"] == 1500

    def test_validate_valid_workout_history(self):
        """Test validation of valid workout_history report."""
        validator = MarkdownValidator()

        source_data = {
            "week_number": "S076",
            "tss_planned": 450,
            "tss_realized": 423,
            "activities": SAMPLE_ACTIVITIES_S076,
        }

        result = validator.validate_report(
            report_content=SAMPLE_WORKOUT_HISTORY_REPORT,
            report_type="workout_history",
            source_data=source_data,
        )

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.metrics is not None
        assert result.metrics["word_count"] > 0

    def test_validate_valid_bilan_final(self):
        """Test validation of valid bilan_final report."""
        validator = MarkdownValidator()

        source_data = {
            "week_number": "S076",
            "tss_planned": 450,
            "tss_realized": 423,
        }

        result = validator.validate_report(
            report_content=SAMPLE_BILAN_FINAL_REPORT,
            report_type="bilan_final",
            source_data=source_data,
        )

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.metrics is not None

    def test_validate_invalid_report_type(self):
        """Test validation with invalid report type."""
        validator = MarkdownValidator()

        with pytest.raises(ValueError, match="Invalid report type"):
            validator.validate_report(
                report_content="# Test",
                report_type="invalid_type",
                source_data={},
            )

    def test_validate_missing_title(self):
        """Test validation detects missing main title."""
        validator = MarkdownValidator()

        content = """## Section 1

Some content here.
"""

        result = validator.validate_report(
            report_content=content,
            report_type="workout_history",
            source_data={"week_number": "S076"},
        )

        assert result.is_valid is False
        assert any("Missing main title" in error for error in result.errors)

    def test_validate_missing_sections(self):
        """Test validation detects missing required sections."""
        validator = MarkdownValidator()

        content = """# Workout History S076

## Only One Section

Some content.
"""

        result = validator.validate_report(
            report_content=content,
            report_type="workout_history",
            source_data={"week_number": "S076"},
        )

        assert result.is_valid is False
        # Should report missing sections like "Contexte Semaine", "Chronologie Complète", etc.
        assert len(result.errors) > 0

    def test_validate_week_number_mismatch(self):
        """Test validation detects week number mismatch."""
        validator = MarkdownValidator()

        content = """# Workout History S076

## Contexte Semaine
## Chronologie Complète
## Métriques Évolution
## Enseignements Majeurs

Content here.
"""

        result = validator.validate_report(
            report_content=content,
            report_type="workout_history",
            source_data={"week_number": "S075"},  # Mismatch!
        )

        assert result.is_valid is False
        assert any("Week number mismatch" in error for error in result.errors)

    def test_word_count_warning(self):
        """Test validation generates warning for excessive word count."""
        validator = MarkdownValidator()

        # Create content with excessive words (> 2000 for workout_history)
        long_content = """# Workout History S076

## Contexte Semaine
## Chronologie Complète
## Métriques Évolution
## Enseignements Majeurs

""" + (
            " ".join(["word"] * 2500)
        )

        result = validator.validate_report(
            report_content=long_content,
            report_type="workout_history",
            source_data={"week_number": "S076"},
        )

        # Should have warning about word count
        assert any("Word count exceeds limit" in warning for warning in result.warnings)

    def test_word_count_calculation(self):
        """Test word counting excludes markdown syntax."""
        validator = MarkdownValidator()

        content = """# Title **bold** _italic_

## Section

`code` and [link](http://example.com)

Regular words here.
"""

        word_count = validator._count_words(content)

        # Should count: Title, bold, italic, Section, code, and, link, Regular, words, here
        # (Markdown syntax removed)
        assert word_count > 0
        assert word_count < 50  # Reasonable bound

    def test_extract_sections(self):
        """Test section extraction from markdown."""
        validator = MarkdownValidator()

        content = """# Main Title

## Section One
Content

## Section Two
More content

### Subsection (should not be extracted)
"""

        sections = validator._extract_sections(content)

        assert len(sections) == 2
        assert "Section One" in sections
        assert "Section Two" in sections
        assert "Subsection (should not be extracted)" not in sections


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test creating ValidationResult."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Minor warning"],
            metrics={"word_count": 1500},
        )

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 1
        assert result.metrics["word_count"] == 1500

    def test_validation_result_invalid(self):
        """Test ValidationResult for invalid report."""
        result = ValidationResult(
            is_valid=False,
            errors=["Missing section: Contexte Semaine"],
            warnings=[],
        )

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0] == "Missing section: Contexte Semaine"
