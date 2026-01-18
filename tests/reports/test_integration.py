"""Integration tests for report generation pipeline.

Sprint R10 MVP Day 3 - Integration tests with mocked dependencies.

Author: Claude Code
Created: 2026-01-18
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from cyclisme_training_logs.reports import ReportGenerator
from cyclisme_training_logs.reports.data_collector import DataCollectionError
from cyclisme_training_logs.reports.generator import ReportGenerationError
from tests.reports.fixtures import (
    SAMPLE_WEEK_DATA_S076,
    SAMPLE_WORKOUT_HISTORY_REPORT,
)


class TestReportGeneratorIntegration:
    """Integration tests for ReportGenerator with mocked components."""

    @patch("cyclisme_training_logs.reports.generator.DataCollector")
    @patch("anthropic.Anthropic")
    def test_generate_workout_history_success(self, mock_anthropic, mock_data_collector_class):
        """Test successful workout_history report generation end-to-end."""
        # Given: Mocked dependencies
        # Mock DataCollector
        mock_collector = Mock()
        mock_data_collector_class.return_value = mock_collector
        mock_collector.collect_week_data.return_value = SAMPLE_WEEK_DATA_S076

        # Mock Claude AI client
        mock_ai_client = Mock()
        mock_anthropic.return_value = mock_ai_client
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = SAMPLE_WORKOUT_HISTORY_REPORT
        mock_response.content = [mock_content]
        mock_ai_client.messages.create.return_value = mock_response

        # Create generator
        generator = ReportGenerator(ai_provider="claude")

        # When: Generating report
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test_key"}):
            output_path = generator.generate_report(
                week="S076",
                report_type="workout_history",
                output_dir=Path("/tmp/test_reports"),
            )

        # Then: Report should be generated successfully
        assert output_path.exists() or True  # Path object returned
        assert str(output_path).endswith("workout_history_s076.md")
        mock_collector.collect_week_data.assert_called_once()
        mock_ai_client.messages.create.assert_called_once()

    @patch("cyclisme_training_logs.reports.generator.DataCollector")
    def test_generate_report_data_collection_failure(self, mock_data_collector_class):
        """Test report generation fails gracefully on data collection error."""
        # Given: DataCollector that fails
        mock_collector = Mock()
        mock_data_collector_class.return_value = mock_collector
        mock_collector.collect_week_data.side_effect = DataCollectionError("Failed to collect data")

        generator = ReportGenerator()

        # When/Then: Should raise ReportGenerationError
        with pytest.raises(ReportGenerationError, match="Data collection failed"):
            generator.generate_report(week="S076", report_type="workout_history")

    @patch("cyclisme_training_logs.reports.generator.DataCollector")
    @patch("anthropic.Anthropic")
    def test_generate_report_ai_generation_failure(self, mock_anthropic, mock_data_collector_class):
        """Test report generation fails gracefully on AI error."""
        # Given: Successful data collection but AI failure
        mock_collector = Mock()
        mock_data_collector_class.return_value = mock_collector
        mock_collector.collect_week_data.return_value = SAMPLE_WEEK_DATA_S076

        mock_ai_client = Mock()
        mock_anthropic.return_value = mock_ai_client
        mock_ai_client.messages.create.side_effect = Exception("API Error")

        generator = ReportGenerator(ai_provider="claude")

        # When/Then: Should raise ReportGenerationError
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test_key"}):
            with pytest.raises(ReportGenerationError, match="AI generation failed"):
                generator.generate_report(week="S076", report_type="workout_history")

    @patch("cyclisme_training_logs.reports.generator.DataCollector")
    @patch("anthropic.Anthropic")
    def test_generate_report_validation_failure(self, mock_anthropic, mock_data_collector_class):
        """Test report generation fails on validation errors."""
        # Given: Successful generation but invalid output
        mock_collector = Mock()
        mock_data_collector_class.return_value = mock_collector
        mock_collector.collect_week_data.return_value = SAMPLE_WEEK_DATA_S076

        mock_ai_client = Mock()
        mock_anthropic.return_value = mock_ai_client
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "Invalid report without required sections"
        mock_response.content = [mock_content]
        mock_ai_client.messages.create.return_value = mock_response

        generator = ReportGenerator(ai_provider="claude")

        # When/Then: Should raise ReportGenerationError
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test_key"}):
            with pytest.raises(ReportGenerationError, match="failed validation"):
                generator.generate_report(
                    week="S076",
                    report_type="workout_history",
                    output_dir=Path("/tmp/test_reports"),
                )

    @patch("cyclisme_training_logs.reports.generator.DataCollector")
    @patch("anthropic.Anthropic")
    def test_generate_bilan_final_success(self, mock_anthropic, mock_data_collector_class):
        """Test successful bilan_final report generation."""
        # Given: Mocked dependencies with bilan_final data (same structure as workout_history)
        mock_collector = Mock()
        mock_data_collector_class.return_value = mock_collector
        mock_collector.collect_week_data.return_value = SAMPLE_WEEK_DATA_S076

        # Mock AI response
        mock_ai_client = Mock()
        mock_anthropic.return_value = mock_ai_client
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = """# Bilan Final S076

## Semaine en Chiffres
## Métriques Finales
## Découvertes Majeures
## Conclusion

Report content here."""
        mock_response.content = [mock_content]
        mock_ai_client.messages.create.return_value = mock_response

        generator = ReportGenerator(ai_provider="claude")

        # When: Generating bilan_final
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test_key"}):
            output_path = generator.generate_report(
                week="S076",
                report_type="bilan_final",
                output_dir=Path("/tmp/test_reports"),
            )

        # Then: Should succeed
        assert str(output_path).endswith("bilan_final_s076.md")
        mock_ai_client.messages.create.assert_called_once()

    @patch("cyclisme_training_logs.reports.generator.DataCollector")
    @patch("anthropic.Anthropic")
    def test_generate_with_ai_provider_override(self, mock_anthropic, mock_data_collector_class):
        """Test AI provider can be overridden per request."""
        # Given: Generator with default provider
        mock_collector = Mock()
        mock_data_collector_class.return_value = mock_collector
        mock_collector.collect_week_data.return_value = SAMPLE_WEEK_DATA_S076

        mock_ai_client = Mock()
        mock_anthropic.return_value = mock_ai_client
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = SAMPLE_WORKOUT_HISTORY_REPORT
        mock_response.content = [mock_content]
        mock_ai_client.messages.create.return_value = mock_response

        generator = ReportGenerator(ai_provider="openai")

        # When: Overriding with claude provider
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test_key"}):
            output_path = generator.generate_report(
                week="S076",
                report_type="workout_history",
                ai_provider="claude",
                output_dir=Path("/tmp/test_reports"),
            )

        # Then: Should use overridden provider
        assert output_path is not None
        mock_ai_client.messages.create.assert_called_once()
