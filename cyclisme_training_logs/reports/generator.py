"""Core report generation engine.

Orchestrates AI-powered weekly report generation using various data sources.

Author: Claude Code (Sprint R10 MVP)
Created: 2026-01-18

Metadata:
    Created: 2026-01-18
    Author: Cyclisme Training Logs Team
    Category: REPORTS
    Status: Production
    Priority: P0
    Version: 1.0.0
"""

import logging
from pathlib import Path
from typing import Any

from cyclisme_training_logs.ai_providers.factory import (
    AIProviderFactory,
    ConfigError,
)
from cyclisme_training_logs.config import get_ai_config
from cyclisme_training_logs.reports.data_collector import (
    DataCollectionError,
    DataCollector,
)
from cyclisme_training_logs.reports.prompts.bilan_final_prompt import (
    build_bilan_final_prompt,
)
from cyclisme_training_logs.reports.prompts.workout_history_prompt import (
    build_workout_history_prompt,
)
from cyclisme_training_logs.reports.validators import (
    MarkdownValidator,
    ValidationResult,
)

logger = logging.getLogger(__name__)


# Alias ConfigError as AIClientError for backward compatibility
AIClientError = ConfigError


class ReportGenerationError(Exception):
    """Exception raised when report generation fails."""

    pass


class ReportGenerator:
    """AI-powered weekly report generator.

    Orchestrates data collection from multiple sources and uses AI to generate
    comprehensive weekly training reports in markdown format.

    Uses existing ai_providers infrastructure (AIProviderFactory) for all AI operations.

    Examples:
        Basic usage::

            generator = ReportGenerator(ai_provider="claude_api")
            report_path = generator.generate_report(
                week="S076",
                report_type="workout_history"
            )

        With custom output directory::

            generator = ReportGenerator(ai_provider="mistral_api")
            report_path = generator.generate_report(
                week="S076",
                report_type="bilan_final",
                output_dir=Path("/custom/path")
            )

    Attributes:
        ai_provider: AI provider name ("claude_api", "mistral_api", "openai", "ollama", "clipboard")
        ai_analyzer: Initialized AI analyzer for generation
    """

    def __init__(self, ai_provider: str = "claude_api"):
        """Initialize report generator with AI provider.

        Args:
            ai_provider: AI provider to use ("claude_api", "mistral_api", "openai", "ollama", "clipboard")
                        Defaults to "claude_api"

        Raises:
            ValueError: If AI provider not supported
        """
        self.ai_provider = ai_provider
        self.ai_analyzer = None

        # Initialize AI analyzer (lazy - done in generate_report)
        logger.info(f"ReportGenerator initialized with provider: {ai_provider}")

    def generate_report(
        self,
        week: str,
        report_type: str,
        ai_provider: str | None = None,
        output_dir: Path | None = None,
    ) -> Path:
        """Generate weekly report using AI.

        Orchestrates full report generation pipeline:
        1. Validate inputs
        2. Collect data from sources (Intervals.icu, Intelligence)
        3. Build AI prompt with context
        4. Generate report via AI
        5. Validate output format
        6. Save to file

        Args:
            week: Week identifier (e.g., "S076")
            report_type: Type of report ("workout_history", "bilan_final")
            ai_provider: Override AI provider (optional)
            output_dir: Output directory (default: ~/data/reports/)

        Returns:
            Path to generated markdown file

        Raises:
            ReportGenerationError: If generation fails
            ValueError: If inputs invalid

        Examples:
            >>> generator = ReportGenerator()
            >>> path = generator.generate_report("S076", "workout_history")
            >>> print(path)
            /Users/user/data/reports/workout_history_s076.md
        """
        # Validate inputs
        if not week or not week.startswith("S"):
            raise ValueError(f"Invalid week format: {week}. Expected format: SXXX")

        if report_type not in ["workout_history", "bilan_final"]:
            raise ValueError(
                f"Invalid report type: {report_type}. " f"Supported: workout_history, bilan_final"
            )

        # Use override provider if specified
        provider = ai_provider or self.ai_provider

        # Set default output directory
        if output_dir is None:
            output_dir = Path.home() / "data" / "reports"

        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generating {report_type} report for week {week}")
        logger.info(f"AI provider: {provider}")
        logger.info(f"Output directory: {output_dir}")

        try:
            # Step 1: Collect data from all sources
            logger.info("Step 1/5: Collecting week data...")
            week_data = self._collect_week_data(week)

            # Step 2: Build AI prompt with context
            logger.info("Step 2/5: Building AI prompt...")
            prompt = self._build_prompt(week_data, report_type)

            # Step 3: Initialize AI analyzer
            logger.info("Step 3/5: Generating report via AI...")
            if not self.ai_analyzer:
                self._initialize_ai_analyzer(provider)

            # Generate report using analyze_session interface
            generated_text = self.ai_analyzer.analyze_session(prompt, dataset=week_data)

            # Step 4: Validate output
            logger.info("Step 4/5: Validating report...")
            validation_result = self._validate_report(generated_text, report_type, week_data)

            if not validation_result.is_valid:
                error_summary = "\n".join(validation_result.errors)
                logger.error(f"Validation failed:\n{error_summary}")
                raise ReportGenerationError(f"Generated report failed validation: {error_summary}")

            # Log warnings if any
            if validation_result.warnings:
                for warning in validation_result.warnings:
                    logger.warning(f"Validation warning: {warning}")

            # Step 5: Save to file
            logger.info("Step 5/5: Saving report to file...")
            output_path = self._save_report(generated_text, week, report_type, output_dir)

            logger.info(f"✅ Report generated successfully: {output_path}")
            logger.info(f"   Word count: {validation_result.metrics.get('word_count', 'N/A')}")
            logger.info(f"   Sections: {validation_result.metrics.get('section_count', 'N/A')}")

            return output_path

        except DataCollectionError as e:
            raise ReportGenerationError(f"Data collection failed: {str(e)}") from e
        except AIClientError as e:
            raise ReportGenerationError(f"AI generation failed: {str(e)}") from e
        except Exception as e:
            raise ReportGenerationError(f"Unexpected error: {str(e)}") from e

    def _collect_week_data(self, week: str) -> dict[str, Any]:
        """Collect all data for a week from various sources.

        Args:
            week: Week identifier (e.g., "S076")

        Returns:
            Dictionary with all week data (activities, wellness, intelligence)

        Raises:
            ReportGenerationError: If data collection fails
        """
        # Parse week number to get start date
        # Format: SXXX (e.g., S076)
        try:
            week_num = int(week[1:])  # Remove 'S' prefix
        except (ValueError, IndexError) as e:
            raise ReportGenerationError(f"Invalid week format: {week}") from e

        # Calculate start date (assuming week 1 starts on first Monday of year)
        # This is a simplified calculation - adjust based on actual week numbering
        from datetime import date, timedelta

        year = date.today().year
        first_day = date(year, 1, 1)

        # Find first Monday
        days_until_monday = (7 - first_day.weekday()) % 7
        first_monday = first_day + timedelta(days=days_until_monday)

        # Calculate week start date
        start_date = first_monday + timedelta(weeks=week_num - 1)

        # Use DataCollector to gather all data
        collector = DataCollector()
        return collector.collect_week_data(week, start_date)

    def _build_prompt(self, week_data: dict[str, Any], report_type: str) -> str:
        """Build AI prompt for report generation.

        Args:
            week_data: Collected week data
            report_type: Type of report to generate

        Returns:
            Complete AI prompt string

        Raises:
            ValueError: If report type not supported
        """
        if report_type == "workout_history":
            return build_workout_history_prompt(week_data)
        elif report_type == "bilan_final":
            return build_bilan_final_prompt(week_data)
        else:
            raise ValueError(f"Unknown report type: {report_type}")

    def _initialize_ai_analyzer(self, provider: str):
        """Initialize AI analyzer for specified provider.

        Uses existing AIProviderFactory to create analyzer instance
        with configuration from config_base.py.

        Args:
            provider: AI provider name ("claude_api", "mistral_api", etc.)

        Raises:
            ValueError: If provider not supported
            AIClientError: If analyzer initialization fails
        """
        logger.info(f"Initializing AI analyzer: {provider}")

        # Get AI config from centralized config
        ai_config = get_ai_config()

        # Get provider-specific config dict
        provider_config = ai_config.get_provider_config(provider)

        # Create analyzer using factory
        try:
            self.ai_analyzer = AIProviderFactory.create(provider, provider_config)
            logger.info(f"AI analyzer initialized: {provider}")
        except ConfigError as e:
            raise AIClientError(f"Failed to initialize AI provider '{provider}': {str(e)}") from e

    def _validate_report(
        self,
        report_content: str,
        report_type: str,
        source_data: dict[str, Any],
    ) -> ValidationResult:
        """Validate generated report.

        Args:
            report_content: Generated markdown report
            report_type: Type of report
            source_data: Source data used for generation

        Returns:
            ValidationResult with errors, warnings, and metrics
        """
        validator = MarkdownValidator()
        return validator.validate_report(report_content, report_type, source_data)

    def _save_report(
        self,
        report_content: str,
        week: str,
        report_type: str,
        output_dir: Path,
    ) -> Path:
        """Save generated report to file.

        Args:
            report_content: Generated markdown content
            week: Week identifier
            report_type: Type of report
            output_dir: Output directory

        Returns:
            Path to saved file

        Raises:
            ReportGenerationError: If save fails
        """
        # Generate filename: report_type_week.md (e.g., workout_history_s076.md)
        week_lower = week.lower()
        filename = f"{report_type}_{week_lower}.md"
        output_path = output_dir / filename

        try:
            output_path.write_text(report_content, encoding="utf-8")
            logger.info(f"Report saved to: {output_path}")
            return output_path
        except Exception as e:
            raise ReportGenerationError(f"Failed to save report to {output_path}: {str(e)}") from e
