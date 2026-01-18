"""Tests for report generator.

Sprint R10 MVP - Tests for ReportGenerator orchestration.

Author: Claude Code
Created: 2026-01-18
"""

from pathlib import Path

import pytest

from cyclisme_training_logs.reports import ReportGenerator


class TestReportGenerator:
    """Tests for ReportGenerator class."""

    def test_init_default_provider(self):
        """Test generator initialization with default provider."""
        generator = ReportGenerator()

        assert generator.ai_provider == "claude"
        assert generator.ai_client is None

    def test_init_custom_provider(self):
        """Test generator initialization with custom provider."""
        generator = ReportGenerator(ai_provider="openai")

        assert generator.ai_provider == "openai"

    def test_generate_report_invalid_week_format(self):
        """Test generate_report rejects invalid week format."""
        generator = ReportGenerator()

        with pytest.raises(ValueError, match="Invalid week format"):
            generator.generate_report(week="076", report_type="workout_history")

        with pytest.raises(ValueError, match="Invalid week format"):
            generator.generate_report(week="", report_type="workout_history")

    def test_generate_report_invalid_report_type(self):
        """Test generate_report rejects invalid report type."""
        generator = ReportGenerator()

        with pytest.raises(ValueError, match="Invalid report type"):
            generator.generate_report(week="S076", report_type="invalid_report")

    def test_generate_report_not_implemented(self):
        """Test generate_report raises NotImplementedError (MVP skeleton)."""
        generator = ReportGenerator()

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            generator.generate_report(week="S076", report_type="workout_history")

    def test_generate_report_with_output_dir(self):
        """Test generate_report accepts custom output directory."""
        generator = ReportGenerator()
        output_dir = Path("/tmp/test_reports")

        with pytest.raises(NotImplementedError):
            # Should not raise ValueError for output_dir
            generator.generate_report(
                week="S076",
                report_type="workout_history",
                output_dir=output_dir,
            )

    def test_generate_report_with_ai_provider_override(self):
        """Test generate_report accepts AI provider override."""
        generator = ReportGenerator(ai_provider="claude")

        with pytest.raises(NotImplementedError):
            # Should not raise ValueError for ai_provider override
            generator.generate_report(
                week="S076",
                report_type="workout_history",
                ai_provider="openai",
            )
