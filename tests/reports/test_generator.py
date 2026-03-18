"""Tests for reports/generator.py — ReportGenerator pipeline.

Covers:
- Input validation (week format, report_type)
- _build_prompt() dispatch to correct builder
- _save_report() file creation
- _validate_report() delegation
- _initialize_ai_analyzer() provider setup
- _collect_week_data() week parsing
- generate_report() full pipeline success + error chains
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.reports.generator import (
    ReportGenerationError,
    ReportGenerator,
)
from magma_cycling.reports.validators import ValidationResult


@pytest.fixture
def generator():
    """Create ReportGenerator instance."""
    return ReportGenerator(ai_provider="claude_api")


@pytest.fixture
def valid_week_data():
    """Sample collected week data."""
    return {
        "week": "S090",
        "activities": [
            {"name": "Endurance Z2", "tss": 65},
            {"name": "Sweet Spot", "tss": 85},
        ],
        "wellness": {"ctl": 65, "atl": 58},
    }


class TestReportGeneratorInit:
    """Test ReportGenerator initialization."""

    def test_init_default_provider(self):
        """Test default provider is claude_api."""
        gen = ReportGenerator()
        assert gen.ai_provider == "claude_api"
        assert gen.ai_analyzer is None

    def test_init_custom_provider(self):
        """Test custom provider assignment."""
        gen = ReportGenerator(ai_provider="mistral_api")
        assert gen.ai_provider == "mistral_api"


class TestInputValidation:
    """Test generate_report input validation."""

    def test_invalid_week_format_none(self, generator):
        """Test ValueError for None week."""
        with pytest.raises(ValueError, match="Invalid week format"):
            generator.generate_report(week=None, report_type="workout_history")

    def test_invalid_week_format_no_prefix(self, generator):
        """Test ValueError for week without S prefix."""
        with pytest.raises(ValueError, match="Invalid week format"):
            generator.generate_report(week="090", report_type="workout_history")

    def test_invalid_week_format_empty(self, generator):
        """Test ValueError for empty week string."""
        with pytest.raises(ValueError, match="Invalid week format"):
            generator.generate_report(week="", report_type="workout_history")

    def test_invalid_report_type(self, generator):
        """Test ValueError for unsupported report type."""
        with pytest.raises(ValueError, match="Invalid report type"):
            generator.generate_report(week="S090", report_type="weekly_summary")

    def test_valid_report_types_accepted(self, generator):
        """Test both valid report types pass validation (fail later)."""
        for rtype in ["workout_history", "bilan_final"]:
            with pytest.raises(ReportGenerationError):
                # Will fail at data collection, not validation
                generator.generate_report(week="S090", report_type=rtype)


class TestBuildPrompt:
    """Test _build_prompt() dispatch."""

    def test_workout_history_dispatch(self, generator, valid_week_data):
        """Test workout_history dispatches to correct builder."""
        with patch(
            "magma_cycling.reports.generator.build_workout_history_prompt",
            return_value="prompt-wh",
        ) as mock_build:
            result = generator._build_prompt(valid_week_data, "workout_history")

        mock_build.assert_called_once_with(valid_week_data)
        assert result == "prompt-wh"

    def test_bilan_final_dispatch(self, generator, valid_week_data):
        """Test bilan_final dispatches to correct builder."""
        with patch(
            "magma_cycling.reports.generator.build_bilan_final_prompt",
            return_value="prompt-bf",
        ) as mock_build:
            result = generator._build_prompt(valid_week_data, "bilan_final")

        mock_build.assert_called_once_with(valid_week_data)
        assert result == "prompt-bf"

    def test_unknown_type_raises(self, generator, valid_week_data):
        """Test unknown report type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown report type"):
            generator._build_prompt(valid_week_data, "invalid_type")


class TestSaveReport:
    """Test _save_report() file creation."""

    def test_save_creates_file(self, generator, tmp_path):
        """Test report saved to correct path."""
        content = "# Weekly Report\nContent here."
        result = generator._save_report(content, "S090", "workout_history", tmp_path)

        assert result == tmp_path / "workout_history_s090.md"
        assert result.exists()
        assert result.read_text() == content

    def test_save_filename_format(self, generator, tmp_path):
        """Test filename uses lowercase week."""
        generator._save_report("content", "S076", "bilan_final", tmp_path)

        assert (tmp_path / "bilan_final_s076.md").exists()

    def test_save_error_raises(self, generator):
        """Test save to invalid path raises ReportGenerationError."""
        with pytest.raises(ReportGenerationError, match="Failed to save"):
            generator._save_report(
                "content",
                "S090",
                "workout_history",
                Path("/nonexistent/path/that/cannot/exist"),
            )


class TestValidateReport:
    """Test _validate_report() delegation."""

    def test_validates_via_markdown_validator(self, generator, valid_week_data):
        """Test _validate_report delegates to MarkdownValidator."""
        mock_result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            metrics={"word_count": 500},
        )

        with patch("magma_cycling.reports.generator.MarkdownValidator") as MockValidator:
            MockValidator.return_value.validate_report.return_value = mock_result
            result = generator._validate_report("# Report", "workout_history", valid_week_data)

        assert result.is_valid is True
        MockValidator.return_value.validate_report.assert_called_once_with(
            "# Report", "workout_history", valid_week_data
        )


class TestInitializeAiAnalyzer:
    """Test _initialize_ai_analyzer() provider setup."""

    def test_initializes_provider(self, generator):
        """Test AI analyzer is created via factory."""
        mock_analyzer = MagicMock()

        with (
            patch("magma_cycling.reports.generator.get_ai_config") as mock_config,
            patch("magma_cycling.reports.generator.AIProviderFactory") as mock_factory,
        ):
            mock_config.return_value.get_provider_config.return_value = {"api_key": "k"}
            mock_factory.create.return_value = mock_analyzer

            generator._initialize_ai_analyzer("claude_api")

        assert generator.ai_analyzer == mock_analyzer
        mock_factory.create.assert_called_once()

    def test_config_error_raises(self, generator):
        """Test ConfigError during init is re-raised."""
        from magma_cycling.ai_providers.factory import ConfigError

        with (
            patch("magma_cycling.reports.generator.get_ai_config") as mock_config,
            patch("magma_cycling.reports.generator.AIProviderFactory") as mock_factory,
        ):
            mock_config.return_value.get_provider_config.return_value = {}
            mock_factory.create.side_effect = ConfigError("No API key")

            with pytest.raises(ConfigError, match="No API key"):
                generator._initialize_ai_analyzer("claude_api")


class TestCollectWeekData:
    """Test _collect_week_data() week parsing."""

    def test_invalid_week_number(self, generator):
        """Test non-numeric week number raises error."""
        with pytest.raises(ReportGenerationError, match="Invalid week format"):
            generator._collect_week_data("SABC")

    def test_delegates_to_data_collector(self, generator):
        """Test data collection delegates to DataCollector."""
        mock_data = {"activities": [], "wellness": {}}

        with patch("magma_cycling.reports.generator.DataCollector") as MockCollector:
            MockCollector.return_value.collect_week_data.return_value = mock_data
            result = generator._collect_week_data("S090")

        assert result == mock_data
        MockCollector.return_value.collect_week_data.assert_called_once()


class TestGenerateReportPipeline:
    """Test generate_report() full pipeline."""

    def test_full_pipeline_success(self, generator, tmp_path):
        """Test successful end-to-end report generation."""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_session.return_value = "# Generated Report\nContent."

        valid_result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            metrics={"word_count": 100, "section_count": 3},
        )

        with (
            patch.object(
                generator,
                "_collect_week_data",
                return_value={"activities": []},
            ),
            patch.object(
                generator,
                "_build_prompt",
                return_value="Build this report",
            ),
            patch.object(generator, "_validate_report", return_value=valid_result),
        ):
            generator.ai_analyzer = mock_analyzer
            result = generator.generate_report(
                week="S090",
                report_type="workout_history",
                output_dir=tmp_path,
            )

        assert result == tmp_path / "workout_history_s090.md"
        assert result.exists()
        mock_analyzer.analyze_session.assert_called_once()

    def test_pipeline_validation_failure(self, generator, tmp_path):
        """Test pipeline raises when validation fails."""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_session.return_value = "Bad content"

        invalid_result = ValidationResult(
            is_valid=False,
            errors=["Missing required section"],
            warnings=[],
        )

        with (
            patch.object(
                generator,
                "_collect_week_data",
                return_value={"activities": []},
            ),
            patch.object(generator, "_build_prompt", return_value="prompt"),
            patch.object(generator, "_validate_report", return_value=invalid_result),
        ):
            generator.ai_analyzer = mock_analyzer

            with pytest.raises(ReportGenerationError, match="failed validation"):
                generator.generate_report(
                    week="S090",
                    report_type="workout_history",
                    output_dir=tmp_path,
                )

    def test_pipeline_data_collection_error(self, generator, tmp_path):
        """Test DataCollectionError is wrapped in ReportGenerationError."""
        from magma_cycling.reports.data_collector import DataCollectionError

        with patch.object(
            generator,
            "_collect_week_data",
            side_effect=DataCollectionError("No data found"),
        ):
            with pytest.raises(ReportGenerationError, match="Data collection failed"):
                generator.generate_report(
                    week="S090",
                    report_type="workout_history",
                    output_dir=tmp_path,
                )

    def test_pipeline_ai_error(self, generator, tmp_path):
        """Test AI error is wrapped in ReportGenerationError."""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_session.side_effect = Exception("API timeout")

        with (
            patch.object(
                generator,
                "_collect_week_data",
                return_value={"activities": []},
            ),
            patch.object(generator, "_build_prompt", return_value="prompt"),
        ):
            generator.ai_analyzer = mock_analyzer

            with pytest.raises(ReportGenerationError, match="Unexpected error"):
                generator.generate_report(
                    week="S090",
                    report_type="workout_history",
                    output_dir=tmp_path,
                )

    def test_provider_override(self, generator, tmp_path):
        """Test ai_provider parameter overrides default."""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_session.return_value = "# Report"

        valid_result = ValidationResult(is_valid=True, errors=[], warnings=[], metrics={})

        with (
            patch.object(
                generator,
                "_collect_week_data",
                return_value={"activities": []},
            ),
            patch.object(generator, "_build_prompt", return_value="prompt"),
            patch.object(generator, "_validate_report", return_value=valid_result),
            patch.object(generator, "_initialize_ai_analyzer") as mock_init,
        ):
            generator.ai_analyzer = mock_analyzer
            generator.generate_report(
                week="S090",
                report_type="workout_history",
                ai_provider="mistral_api",
                output_dir=tmp_path,
            )

        # ai_analyzer was already set, so _initialize_ai_analyzer not called
        mock_init.assert_not_called()

    def test_default_output_dir(self, generator):
        """Test default output dir is ~/data/reports/."""
        with (
            patch.object(
                generator,
                "_collect_week_data",
                return_value={"activities": []},
            ),
            patch.object(generator, "_build_prompt", return_value="prompt"),
            patch.object(
                generator,
                "_validate_report",
                return_value=ValidationResult(is_valid=True, errors=[], warnings=[], metrics={}),
            ),
            patch.object(
                generator, "_save_report", return_value=Path("/tmp/report.md")
            ) as mock_save,
        ):
            generator.ai_analyzer = MagicMock()
            generator.ai_analyzer.analyze_session.return_value = "report"

            generator.generate_report(week="S090", report_type="workout_history")

        # Verify default output_dir was used
        call_args = mock_save.call_args
        assert call_args[0][3] == Path.home() / "data" / "reports"

    def test_validation_warnings_logged(self, generator, tmp_path, caplog):
        """Test validation warnings are logged."""
        import logging

        mock_analyzer = MagicMock()
        mock_analyzer.analyze_session.return_value = "# Report"

        result_with_warnings = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Word count low: 50"],
            metrics={"word_count": 50},
        )

        with (
            patch.object(
                generator,
                "_collect_week_data",
                return_value={"activities": []},
            ),
            patch.object(generator, "_build_prompt", return_value="prompt"),
            patch.object(generator, "_validate_report", return_value=result_with_warnings),
            caplog.at_level(logging.WARNING, logger="magma_cycling.reports.generator"),
        ):
            generator.ai_analyzer = mock_analyzer
            generator.generate_report(
                week="S090",
                report_type="workout_history",
                output_dir=tmp_path,
            )

        assert "Word count low" in caplog.text
