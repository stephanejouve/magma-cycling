"""Tests for report generator.

Sprint R10 MVP - Tests for ReportGenerator orchestration.

Author: Claude Code
Created: 2026-01-18
"""

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

    # Note: Full integration tests removed - generate_report now fully implemented
    # Integration testing will be done with proper mocking of DataCollector and AIClient
    # in dedicated integration test files (Day 3)
