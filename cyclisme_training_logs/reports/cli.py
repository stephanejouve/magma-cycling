"""CLI interface for AI-powered report generation.

Sprint R10 MVP Day 4 - Command-line interface for weekly reports.

Author: Claude Code
Created: 2026-01-18

Usage:
    generate-report --week S076 --type workout_history
    generate-report --week S076 --type bilan_final --output ~/reports
    generate-report --week S076 --type workout_history --provider claude
"""

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

from cyclisme_training_logs.reports import ReportGenerator
from cyclisme_training_logs.reports.generator import ReportGenerationError

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Generate AI-powered weekly training reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate workout_history report for week S076
  generate-report --week S076 --type workout_history

  # Generate bilan_final report with custom output directory
  generate-report --week S076 --type bilan_final --output ~/custom/reports

  # Use specific AI provider
  generate-report --week S076 --type workout_history --provider claude

Report Types:
  workout_history  Detailed session-by-session chronology (factual, 2000 words)
  bilan_final      Strategic synthesis and learnings (strategic, 1500 words)

AI Providers:
  claude           Claude Sonnet 4.5 (requires ANTHROPIC_API_KEY)
  openai           OpenAI GPT-4 (requires OPENAI_API_KEY)
  clipboard        Copy prompt to clipboard (no API required)
        """,
    )

    parser.add_argument(
        "--week",
        "-w",
        required=True,
        help="Week identifier (e.g., S076)",
        metavar="WEEK",
    )

    parser.add_argument(
        "--type",
        "-t",
        required=True,
        choices=["workout_history", "bilan_final"],
        help="Report type to generate",
        metavar="TYPE",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output directory (default: ~/data/reports)",
        metavar="DIR",
    )

    parser.add_argument(
        "--provider",
        "-p",
        default="claude",
        choices=["claude", "openai", "clipboard"],
        help="AI provider to use (default: claude)",
        metavar="PROVIDER",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args()


def calculate_week_start_date(week: str) -> date:
    """Calculate start date for a week identifier.

    Args:
        week: Week identifier (e.g., "S076")

    Returns:
        Start date (Monday) for the week

    Raises:
        ValueError: If week format invalid

    Examples:
        >>> calculate_week_start_date("S076")
        date(2026, 1, 13)  # Assuming 2026 calendar
    """
    try:
        week_num = int(week[1:])  # Remove 'S' prefix
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid week format: {week}. Expected format: SXXX") from e

    # Calculate start date (assuming week 1 starts on first Monday of year)
    year = date.today().year
    first_day = date(year, 1, 1)

    # Find first Monday
    days_until_monday = (7 - first_day.weekday()) % 7
    first_monday = first_day + timedelta(days=days_until_monday)

    # Calculate week start date
    start_date = first_monday + timedelta(weeks=week_num - 1)

    return start_date


def main():
    """Main CLI entry point for report generation.

    Exit codes:
        0: Success
        1: Report generation error
        2: Configuration error (missing API keys, etc.)
        3: Invalid arguments
    """
    args = parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")

    logger.info("=" * 60)
    logger.info("AI-Powered Weekly Report Generation")
    logger.info("Sprint R10 MVP - Claude Code")
    logger.info("=" * 60)
    logger.info(f"Week: {args.week}")
    logger.info(f"Report Type: {args.type}")
    logger.info(f"AI Provider: {args.provider}")
    if args.output:
        logger.info(f"Output Directory: {args.output}")
    logger.info("=" * 60)

    try:
        # Initialize report generator
        logger.info("Initializing report generator...")
        generator = ReportGenerator(ai_provider=args.provider)

        # Generate report
        logger.info(f"Generating {args.type} report for {args.week}...")
        output_path = generator.generate_report(
            week=args.week,
            report_type=args.type,
            output_dir=args.output,
        )

        # Success
        logger.info("=" * 60)
        logger.info("✅ Report generation successful!")
        logger.info(f"📄 Output file: {output_path}")
        logger.info("=" * 60)

        # Print file content if it's a clipboard provider
        if args.provider == "clipboard":
            logger.info("\n📋 Prompt copied to clipboard. Paste in Claude.ai.")
            logger.info("💡 Tip: Review and edit the prompt before submitting.")

        return 0

    except ReportGenerationError as e:
        logger.error("=" * 60)
        logger.error("❌ Report generation failed!")
        logger.error(f"Error: {str(e)}")
        logger.error("=" * 60)
        return 1

    except ValueError as e:
        logger.error("=" * 60)
        logger.error("❌ Invalid arguments!")
        logger.error(f"Error: {str(e)}")
        logger.error("=" * 60)
        return 3

    except Exception as e:
        logger.error("=" * 60)
        logger.error("❌ Unexpected error!")
        logger.error(f"Error: {str(e)}")
        logger.error("=" * 60)
        logger.exception("Full traceback:")
        return 2


if __name__ == "__main__":
    sys.exit(main())
