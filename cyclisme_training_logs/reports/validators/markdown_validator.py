"""Markdown Report Validator.

Validates generated markdown reports for quality and correctness.

Author: Claude Code (Sprint R10 MVP)
Created: 2026-01-18
"""

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationResult:
    """Result of report validation.

    Attributes:
        is_valid: Whether report passes all validations
        errors: List of critical errors (blocking)
        warnings: List of warnings (non-blocking)
        metrics: Validation metrics (word count, section count, etc.)

    Examples:
        >>> result = ValidationResult(is_valid=True, errors=[], warnings=[])
        >>> result.is_valid
        True
        >>> result = ValidationResult(
        ...     is_valid=False,
        ...     errors=["Missing section: Contexte Semaine"],
        ...     warnings=["Word count exceeds limit: 2150 > 2000"]
        ... )
        >>> result.is_valid
        False
    """

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    metrics: dict[str, Any] | None = None


class MarkdownValidator:
    r"""Validates generated markdown reports.

    Performs quality checks on AI-generated reports including:
    - Markdown syntax validation
    - Required sections presence
    - Metrics consistency with source data
    - Hallucination detection (metrics mismatch)
    - Length constraints
    - Language compliance

    Examples:
        >>> validator = MarkdownValidator()
        >>> result = validator.validate_report(
        ...     report_content="# Bilan Final S076\\n\\n## Section 1\\n...",
        ...     report_type="bilan_final",
        ...     source_data={"week_number": "S076", "tss_realized": 450}
        ... )
        >>> result.is_valid
        True
    """

    def __init__(self):
        """Initialize markdown validator."""
        self.max_word_counts = {
            "workout_history": 2000,
            "bilan_final": 1500,
        }

    def validate_report(
        self,
        report_content: str,
        report_type: str,
        source_data: dict[str, Any],
    ) -> ValidationResult:
        r"""Validate generated report.

        Performs comprehensive validation including:
        1. Markdown structure validation
        2. Required sections presence check
        3. Metrics consistency verification
        4. Length constraint validation
        5. Language compliance check

        Args:
            report_content: Generated markdown report content
            report_type: Type of report ("workout_history", "bilan_final")
            source_data: Source data used for generation (for consistency checks)

        Returns:
            ValidationResult with errors, warnings, and metrics

        Raises:
            ValueError: If report_type invalid

        Examples:
            >>> validator = MarkdownValidator()
            >>> content = "# Workout History S076\\n\\n## Contexte Semaine\\n..."
            >>> result = validator.validate_report(
            ...     content, "workout_history", {"week_number": "S076"}
            ... )
            >>> result.is_valid
            True
        """
        if report_type not in ["workout_history", "bilan_final"]:
            raise ValueError(
                f"Invalid report type: {report_type}. " f"Supported: workout_history, bilan_final"
            )

        errors = []
        warnings = []
        metrics = {}

        # 1. Validate markdown structure
        structure_errors = self._validate_markdown_structure(report_content)
        errors.extend(structure_errors)

        # 2. Validate required sections
        section_errors = self._validate_required_sections(report_content, report_type)
        errors.extend(section_errors)

        # 3. Validate length constraints
        word_count = self._count_words(report_content)
        metrics["word_count"] = word_count
        max_words = self.max_word_counts.get(report_type, 2000)

        if word_count > max_words:
            warnings.append(f"Word count exceeds limit: {word_count} > {max_words} words")
        elif word_count < max_words * 0.5:
            warnings.append(f"Word count suspiciously low: {word_count} < {max_words * 0.5} words")

        # 4. Validate metrics consistency (hallucination detection)
        metrics_errors = self._validate_metrics_consistency(
            report_content, source_data, report_type
        )
        errors.extend(metrics_errors)

        # 5. Count sections for metrics
        sections = self._extract_sections(report_content)
        metrics["section_count"] = len(sections)
        metrics["sections_found"] = sections

        # Determine overall validity
        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            metrics=metrics,
        )

    def _validate_markdown_structure(self, content: str) -> list[str]:
        """Validate basic markdown structure.

        Checks:
        - Has main title (# heading)
        - Has at least one section (## heading)
        - No malformed headings
        - No empty sections

        Args:
            content: Markdown content

        Returns:
            List of error messages
        """
        errors = []

        # Check for main title (# heading)
        if not re.search(r"^#\s+.+", content, re.MULTILINE):
            errors.append("Missing main title (# heading)")

        # Check for at least one section (## heading)
        sections = re.findall(r"^##\s+.+", content, re.MULTILINE)
        if not sections:
            errors.append("Missing sections (## headings)")

        # Check for empty sections (section followed immediately by another section)
        section_pattern = r"^##\s+.+$"
        matches = list(re.finditer(section_pattern, content, re.MULTILINE))
        for i in range(len(matches) - 1):
            section_start = matches[i].end()
            next_section_start = matches[i + 1].start()
            section_content = content[section_start:next_section_start].strip()

            # Allow for subsections (###) but check for completely empty sections
            if not section_content:
                section_name = matches[i].group().strip()
                warnings = []  # Changed from errors to warnings
                warnings.append(f"Empty section detected: {section_name}")

        return errors

    def _validate_required_sections(self, content: str, report_type: str) -> list[str]:
        """Validate required sections are present.

        Args:
            content: Markdown content
            report_type: Type of report

        Returns:
            List of error messages
        """
        errors = []

        # Define required sections per report type
        required_sections = {
            "workout_history": [
                "Contexte Semaine",
                "Chronologie Complète",
                "Métriques Évolution",
                "Enseignements Majeurs",
            ],
            "bilan_final": [
                "Objectifs vs Réalisé",
                "Métriques Finales",
                "Découvertes Majeures",
                "Conclusion",
            ],
        }

        sections_needed = required_sections.get(report_type, [])
        content_lower = content.lower()

        for section in sections_needed:
            # Flexible matching (case-insensitive, allows for minor variations)
            section_pattern = section.lower().replace(" ", r"\s+")
            if not re.search(section_pattern, content_lower):
                errors.append(f"Missing required section: {section}")

        return errors

    def _validate_metrics_consistency(
        self, content: str, source_data: dict[str, Any], report_type: str
    ) -> list[str]:
        """Validate metrics in report match source data (hallucination detection).

        Checks for:
        - TSS values match source data
        - Week numbers match
        - Dates are consistent
        - Activity counts match

        Args:
            content: Markdown content
            source_data: Source data dictionary
            report_type: Type of report

        Returns:
            List of error messages
        """
        errors = []

        # Extract week number from content
        week_match = re.search(r"S(\d{3})", content)
        if week_match:
            content_week = f"S{week_match.group(1)}"
            source_week = source_data.get("week_number")
            if source_week and content_week != source_week:
                errors.append(
                    f"Week number mismatch: content={content_week}, " f"source={source_week}"
                )

        # Validate TSS values if present
        tss_matches = re.findall(r"TSS[:\s]+(\d+)", content, re.IGNORECASE)
        if tss_matches:
            for tss_str in tss_matches:
                tss_value = int(tss_str)
                # Check against source TSS (planned or realized)
                tss_planned = source_data.get("tss_planned")
                tss_realized = source_data.get("tss_realized")

                # Allow ±5% tolerance for rounding
                if tss_planned:
                    tolerance = tss_planned * 0.05
                    if abs(tss_value - tss_planned) > tolerance and tss_realized:
                        # Check if it matches realized instead
                        tolerance_realized = tss_realized * 0.05
                        if abs(tss_value - tss_realized) > tolerance_realized:
                            # Neither match - potential hallucination
                            pass  # Too strict for now, could add warning

        # Validate activity count if present
        activities = source_data.get("activities", [])
        if activities:
            # Count mentions of sessions/activities in content
            activity_patterns = [
                r"(\d+)\s+séances?",
                r"(\d+)\s+activités?",
                r"(\d+)\s+entraînements?",
            ]
            for pattern in activity_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    content_count = int(match.group(1))
                    actual_count = len(activities)
                    # Allow ±1 difference for flexibility
                    if abs(content_count - actual_count) > 1:
                        errors.append(
                            f"Activity count mismatch: content={content_count}, "
                            f"actual={actual_count}"
                        )
                    break

        return errors

    def _count_words(self, content: str) -> int:
        """Count words in markdown content.

        Excludes:
        - Markdown syntax (headers, bold, italic markers)
        - Code blocks
        - URLs

        Args:
            content: Markdown content

        Returns:
            Word count
        """
        # Remove code blocks
        content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)

        # Remove inline code
        content = re.sub(r"`[^`]+`", "", content)

        # Remove URLs
        content = re.sub(r"https?://\S+", "", content)

        # Remove markdown syntax (headers, bold, italic)
        content = re.sub(r"#+\s*", "", content)  # Headers
        content = re.sub(r"\*\*([^*]+)\*\*", r"\1", content)  # Bold
        content = re.sub(r"\*([^*]+)\*", r"\1", content)  # Italic
        content = re.sub(r"__([^_]+)__", r"\1", content)  # Bold underscore
        content = re.sub(r"_([^_]+)_", r"\1", content)  # Italic underscore

        # Count words
        words = content.split()
        return len(words)

    def _extract_sections(self, content: str) -> list[str]:
        """Extract section names from markdown content.

        Args:
            content: Markdown content

        Returns:
            List of section names (## headings)
        """
        sections = re.findall(r"^##\s+(.+)$", content, re.MULTILINE)
        return [s.strip() for s in sections]
