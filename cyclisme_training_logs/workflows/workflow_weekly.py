"""
Weekly analysis workflow CLI and orchestration.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Workflow complet analyse hebdomadaire automatisée. Orchestre :
WeeklyAggregator → WeeklyAnalyzer → 6 reports markdown.
Remplace weekly_analysis.py legacy.

Examples:
    Command-line usage::

        # Analyse semaine courante
        poetry run weekly-analysis --week current

        # Analyse semaine spécifique
        poetry run weekly-analysis --week S073 --start-date 2025-01-06

        # Avec AI analysis (clipboard)
        poetry run weekly-analysis --week S073 --ai-analysis

    Programmatic usage::

        from cyclisme_training_logs.workflows.workflow_weekly import run_weekly_analysis
        from datetime import date

        # Exécution programmatique
        reports = run_weekly_analysis(
            week="S073",
            start_date=date(2025, 1, 6),
            save_reports=True
        )

        print(f"Generated {len(reports)} reports")

    Integration with existing::

        # Compatible avec workflow actuel
        from cyclisme_training_logs.workflows.workflow_weekly import WeeklyWorkflow

        workflow = WeeklyWorkflow(week="S073", start_date=date(2025, 1, 6))
        workflow.run()

Author: Claude Code
Created: 2025-12-26 (Phase 2 - Weekly Analysis System)
"""

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import sys

from cyclisme_training_logs.analyzers.weekly_aggregator import WeeklyAggregator
from cyclisme_training_logs.analyzers.weekly_analyzer import WeeklyAnalyzer

logger = logging.getLogger(__name__)


class WeeklyWorkflow:
    """
    Workflow complet analyse hebdomadaire.

    Pipeline :
    1. WeeklyAggregator - Collecte et agrégation données
    2. WeeklyAnalyzer - Génération 6 reports
    3. Save reports - Sauvegarde markdown
    4. Optional: AI analysis via clipboard
    """

    def __init__(
        self,
        week: str,
        start_date: date,
        data_dir: Optional[Path] = None,
        ai_analysis: bool = False
    ):
        """
        Initialiser workflow.

        Args:
            week: Numéro semaine (S073)
            start_date: Date début (lundi)
            data_dir: Répertoire données (None = auto-detect)
            ai_analysis: Activer AI analysis via clipboard
        """
        self.week = week
        self.start_date = start_date
        self.ai_analysis = ai_analysis

        # Determine data directory
        if data_dir is None:
            try:
                from cyclisme_training_logs.config import get_data_config
                config = get_data_config()
                self.data_dir = config.data_repo_path
            except Exception:
                self.data_dir = Path.home() / 'training-logs'
        else:
            self.data_dir = Path(data_dir)

    def run(self) -> Dict[str, str]:
        """
        Exécuter workflow complet.

        Returns:
            Dict avec 6 reports générés
        """
        logger.info(f"Starting weekly workflow for {self.week}")

        # 1. Aggregation
        logger.info("Step 1/3: Aggregating weekly data")
        aggregator = WeeklyAggregator(
            week=self.week,
            start_date=self.start_date,
            data_dir=self.data_dir
        )

        aggregation = aggregator.aggregate()

        if not aggregation.success:
            logger.error(f"Aggregation failed: {aggregation.errors}")
            raise RuntimeError("Weekly aggregation failed")

        # 2. Analysis
        logger.info("Step 2/3: Generating reports")
        analyzer = WeeklyAnalyzer(
            week=self.week,
            weekly_data=aggregation.data['processed']
        )

        reports = analyzer.generate_all_reports()

        # 3. Save
        logger.info("Step 3/3: Saving reports")
        output_dir = self.data_dir / 'weekly-reports' / self.week
        analyzer.save_reports(reports, output_dir)

        logger.info(f"Weekly workflow completed: {len(reports)} reports saved")

        # 4. Optional: AI analysis
        if self.ai_analysis:
            self._trigger_ai_analysis(reports)

        return reports

    def _trigger_ai_analysis(self, reports: Dict[str, str]) -> None:
        """Trigger AI analysis via clipboard (optionnel)."""
        try:
            import subprocess

            # Combiner prompts pour AI
            combined = "\n\n---\n\n".join([
                f"# {name.upper()}\n{content}"
                for name, content in reports.items()
            ])

            # Copy to clipboard (macOS)
            subprocess.run(['pbcopy'], input=combined.encode('utf-8'), check=True)
            logger.info("Reports copied to clipboard for AI analysis")
            print("\n✅ Reports copied to clipboard - paste into Claude.ai for AI analysis")
        except Exception as e:
            logger.warning(f"AI analysis clipboard failed: {e}")


def run_weekly_analysis(
    week: str,
    start_date: date,
    data_dir: Optional[Path] = None,
    ai_analysis: bool = False
) -> Dict[str, str]:
    """
    Fonction utilitaire pour workflow weekly.

    Args:
        week: Numéro semaine (S073)
        start_date: Date début
        data_dir: Répertoire données (None = auto)
        ai_analysis: Activer AI analysis

    Returns:
        Dict avec 6 reports générés
    """
    workflow = WeeklyWorkflow(
        week=week,
        start_date=start_date,
        data_dir=data_dir,
        ai_analysis=ai_analysis
    )

    return workflow.run()


def get_current_week_info() -> tuple:
    """
    Calculer numéro semaine courante et date début.

    Returns:
        (week, start_date) tuple
    """
    today = date.today()

    # Trouver lundi de la semaine
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)

    # Calculer numéro semaine
    week_number = monday.isocalendar()[1]
    week = f"S{week_number:03d}"

    return week, monday


def main():
    """Entry point CLI."""
    parser = argparse.ArgumentParser(
        description="Weekly analysis workflow - Generate 6 automated reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze current week
  %(prog)s --week current

  # Analyze specific week
  %(prog)s --week S073 --start-date 2025-01-06

  # With AI analysis
  %(prog)s --week S073 --start-date 2025-01-06 --ai-analysis
        """
    )

    parser.add_argument(
        '--week',
        type=str,
        help='Week number (S073) or "current"',
        default='current'
    )

    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date YYYY-MM-DD (Monday)',
        default=None
    )

    parser.add_argument(
        '--data-dir',
        type=str,
        help='Data directory (default: auto-detect)',
        default=None
    )

    parser.add_argument(
        '--ai-analysis',
        action='store_true',
        help='Enable AI analysis via clipboard'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose logging'
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    # Déterminer semaine et date
    if args.week == 'current':
        week, start_date = get_current_week_info()
        logger.info(f"Current week detected: {week} (starting {start_date})")
    else:
        week = args.week

        if args.start_date:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        else:
            logger.error("--start-date required when using custom week")
            return 1

    # Data directory
    data_dir = Path(args.data_dir) if args.data_dir else None

    # Exécuter workflow
    try:
        print(f"\n🏃 Starting weekly analysis for {week}...\n")

        reports = run_weekly_analysis(
            week=week,
            start_date=start_date,
            data_dir=data_dir,
            ai_analysis=args.ai_analysis
        )

        print(f"\n✅ Weekly analysis completed for {week}")
        print(f"📊 Generated {len(reports)} reports:")
        for name in reports.keys():
            print(f"   - {name}")

        # Show output location
        if data_dir:
            output_dir = data_dir / 'weekly-reports' / week
        else:
            try:
                from cyclisme_training_logs.config import get_data_config
                config = get_data_config()
                output_dir = config.data_repo_path / 'weekly-reports' / week
            except Exception:
                output_dir = Path.home() / 'training-logs' / 'weekly-reports' / week

        print(f"\n📁 Reports saved to: {output_dir}")

        return 0

    except Exception as e:
        logger.error(f"Weekly analysis failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
