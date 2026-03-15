#!/usr/bin/env python3
r"""
End-of-Week Workflow Orchestrator.

Workflow automatisé complet pour transition hebdomadaire :
1. Analyse semaine écoulée (weekly-analysis)
1b. Évaluation PID & Training Intelligence (pid-daily-evaluation)
1c. Analyse mensuelle automatique (si transition de mois)
2. Génération planning semaine suivante (weekly-planner)
3. Appel AI provider pour génération workouts
4. Validation notation (format-planning intégré)
5. Upload workouts vers Intervals.icu
6. Archivage et commit (optionnel)

Examples:
    Mode clipboard (défaut) - copier-coller manuel::

        poetry run end-of-week --week-completed S075 --week-next S076

    Mode automatique avec Claude API::

        poetry run end-of-week --week-completed S075 --week-next S076 \\
            --provider claude_api --auto

    Dry-run (simulation)::

        poetry run end-of-week --week-completed S075 --week-next S076 --dry-run

    Avec archivage automatique::

        poetry run end-of-week --week-completed S075 --week-next S076 \\
            --provider clipboard --archive

Author: Claude Code
Created: 2026-01-10
Version: 1.0.0

Metadata:
    Category: I (Integration)
    Status: Production
    Priority: P1
"""

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from magma_cycling.config import get_data_config, get_week_config
from magma_cycling.planning.models import WeeklyPlan
from magma_cycling.utils.cli import cli_main
from magma_cycling.workflows.eow.ai_workouts import AIWorkoutsMixin
from magma_cycling.workflows.eow.analysis import AnalysisMixin
from magma_cycling.workflows.eow.archive import ArchiveMixin
from magma_cycling.workflows.eow.evaluation import EvaluationMixin
from magma_cycling.workflows.eow.upload import UploadMixin


def calculate_week_start_date(week_id: str) -> date:
    """
    Calculate Monday start date from project week ID.

    The project uses sequential week numbering with multi-season support.
    Reference dates are read from .config.json (no hardcoded dates).

    Args:
        week_id: Week identifier (e.g., "S075")

    Returns:
        Date of Monday for that week

    Raises:
        FileNotFoundError: If .config.json doesn't exist
        ValueError: If .config.json is invalid or date is not a Monday

    Examples:
        >>> calculate_week_start_date("S001")
        date(2024, 8, 5)  # Season 2024-2025: Monday Aug 5, 2024
        >>> calculate_week_start_date("S075")
        date(2026, 1, 5)  # Season 2026: Monday Jan 5, 2026
        >>> calculate_week_start_date("S076")
        date(2026, 1, 12)  # Season 2026: Monday Jan 12, 2026
    """
    # Load reference date and offset from config (multi-season aware)
    week_config = get_week_config()
    reference_date, weeks_offset = week_config.get_reference_for_week(week_id)

    # Calculate target Monday
    target_monday = reference_date + timedelta(weeks=weeks_offset)

    # Validation: must be a Monday
    if target_monday.weekday() != 0:
        raise ValueError(f"Calculated date {target_monday} is not a Monday (got {target_monday})")

    return target_monday


def calculate_weekly_transition(reference_date: date | None = None) -> tuple[str, str, date, date]:
    """
    Calculate week IDs for weekly transition (completed → next).

    Logic:
    - Determines the most recently completed week and the next week to plan
    - On Monday (first day of new week), the previous week is completed
    - On Sunday (last day of current week), the current week is completed
    - Both Sunday evening and Monday morning yield the same transition

    Args:
        reference_date: Reference date for calculation (default: today)

    Returns:
        Tuple of (week_completed, week_next, completed_start_date, next_start_date)

    Examples:
        >>> # Running on Sunday 2026-01-25 or Monday 2026-01-26
        >>> calculate_weekly_transition(date(2026, 1, 25))
        ('S077', 'S078', date(2026, 1, 19), date(2026, 1, 26))
        >>> calculate_weekly_transition(date(2026, 1, 26))
        ('S077', 'S078', date(2026, 1, 19), date(2026, 1, 26))
    """
    if reference_date is None:
        reference_date = date.today()

    # Get week config
    week_config = get_week_config()
    s001_date = week_config.get_s001_date_obj("S001")

    # Use yesterday to determine completed week: on Monday (first day of
    # new week), yesterday=Sunday falls in the previous week, giving the
    # correct "just completed" week. On Sunday, yesterday=Saturday stays
    # in the same week. Both yield the same transition.
    adjusted_date = reference_date - timedelta(days=1)
    delta = adjusted_date - s001_date
    weeks_offset = delta.days // 7

    # Completed week is the one containing yesterday
    current_week_num = weeks_offset + 1
    week_completed = f"S{current_week_num:03d}"
    week_next = f"S{current_week_num + 1:03d}"

    # Calculate start dates
    completed_start_date = s001_date + timedelta(weeks=weeks_offset)
    next_start_date = s001_date + timedelta(weeks=weeks_offset + 1)

    return week_completed, week_next, completed_start_date, next_start_date


class EndOfWeekWorkflow(
    AnalysisMixin,
    EvaluationMixin,
    AIWorkoutsMixin,
    UploadMixin,
    ArchiveMixin,
):
    """Orchestrateur workflow fin de semaine."""

    def __init__(
        self,
        week_completed: str,
        week_next: str,
        provider: str = "clipboard",
        dry_run: bool = False,
        auto: bool = False,
        archive: bool = False,
    ):
        """
        Initialize workflow.

        Args:
            week_completed: Semaine terminée (e.g., "S075")
            week_next: Semaine à planifier (e.g., "S076")
            provider: AI provider (clipboard, claude_api, mistral_api)
            dry_run: Mode simulation
            auto: Mode automatique (pas de confirmation)
            archive: Archiver et commiter automatiquement
        """
        self.week_completed = week_completed
        self.week_next = week_next
        self.provider = provider
        self.dry_run = dry_run
        self.auto = auto
        self.archive = archive

        # Calculate dates automatically
        self.completed_start_date = calculate_week_start_date(week_completed)
        self.completed_end_date = self.completed_start_date + timedelta(days=6)
        self.next_start_date = calculate_week_start_date(week_next)
        self.next_end_date = self.next_start_date + timedelta(days=6)

        # Configuration
        try:
            config = get_data_config()
            self.data_dir = config.data_repo_path
            self.reports_dir = config.data_repo_path / "weekly-reports"
            self.planning_dir = config.week_planning_dir
        except Exception as e:
            print(f"❌ Erreur configuration : {e}")
            sys.exit(1)

        # État du workflow
        self.reports: dict[str, str] = {}
        self.planning_prompt: str = ""
        self.workouts_content: str = ""
        self.workouts_file: Path | None = None
        self.validation_warnings: list[str] = []

    def _check_next_week_already_planned(self) -> bool:
        """Check if next week planning already exists and is non-trivial."""
        planning_file = self.planning_dir / f"week_planning_{self.week_next}.json"
        if not planning_file.exists():
            return False

        try:
            plan = WeeklyPlan.from_json(planning_file)
        except Exception:
            return False

        # Explicit source check — non-EOW plannings are always respected
        if plan.source and plan.source != "eow":
            return True

        # Heuristic fallback for legacy files without source field
        for session in plan.planned_sessions:
            if session.intervals_id is not None:
                return True
            if session.status not in ("planned", "pending"):
                return True

        return False

    def run(self) -> bool:
        """
        Execute workflow complet.

        Returns:
            True si succès, False sinon
        """
        # Idempotence: skip if already completed for this week
        marker = self.planning_dir / f".eow_done_{self.week_completed}"
        if marker.exists():
            print(f"⚠️  End-of-week déjà exécuté pour {self.week_completed} — skip")
            return True

        # Précondition: next week not already planned
        if self._check_next_week_already_planned():
            print(
                f"⚠️  Planning {self.week_next} déjà existant avec sessions "
                f"actives — skip end-of-week pour éviter écrasement"
            )
            return True

        print("=" * 80)
        print(f"🏁 END-OF-WEEK WORKFLOW: {self.week_completed} → {self.week_next}")
        print("=" * 80)
        print()
        print("📅 Dates calculées automatiquement:")
        print(
            f"   {self.week_completed}: {self.completed_start_date.strftime('%d/%m/%Y')} → "
            f"{self.completed_end_date.strftime('%d/%m/%Y')}"
        )
        print(
            f"   {self.week_next}: {self.next_start_date.strftime('%d/%m/%Y')} → "
            f"{self.next_end_date.strftime('%d/%m/%Y')}"
        )
        print()

        try:
            # Step 1: Analyze completed week
            if not self._step1_analyze_completed_week():
                return False

            # Step 1b: PID evaluation and intelligence learning
            if not self._step1b_pid_evaluation():
                return False

            # Step 1c: Monthly analysis if month transition
            if not self._step1c_monthly_analysis_if_month_end():
                return False

            # Step 2: Generate planning prompt for next week
            if not self._step2_generate_planning_prompt():
                return False

            # Step 3: Get workouts from AI provider
            if not self._step3_get_ai_workouts():
                return False

            # Step 4: Validate workouts notation
            if not self._step4_validate_workouts():
                return False

            # Step 5: Upload workouts to Intervals.icu
            if not self._step5_upload_workouts():
                return False

            # Step 5b: Save planning JSON with uploaded workouts data
            if not self.dry_run:
                self._step5b_save_planning_json()

            # Step 6: Archive and commit (optional)
            if self.archive and not self.dry_run:
                self._step6_archive_and_commit()

            # Success summary
            self._print_success_summary()

            # Write idempotence marker (skip in dry-run — no real work done)
            if not self.dry_run:
                marker.write_text(datetime.now().isoformat())

            return True

        except KeyboardInterrupt:
            print("\n\n⚠️  Workflow interrompu par l'utilisateur")
            return False
        except Exception as e:
            print(f"\n❌ Erreur workflow : {e}")
            if "--verbose" in sys.argv:
                import traceback

                traceback.print_exc()
            return False


def parse_args(args=None):
    """Parse command line arguments.

    Args:
        args: Optional list of arguments (for testing). If None, uses sys.argv.
    """
    parser = argparse.ArgumentParser(
        description="End-of-Week Workflow - Automatisation transition hebdomadaire",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:

  # Mode clipboard (défaut) - copier-coller manuel
  %(prog)s --week-completed S075 --week-next S076

  # Mode automatique avec Claude API (en développement)
  %(prog)s --week-completed S075 --week-next S076 --provider claude_api --auto

  # Dry-run (simulation)
  %(prog)s --week-completed S075 --week-next S076 --dry-run

  # Avec archivage automatique
  %(prog)s --week-completed S075 --week-next S076 --archive

Workflow complet:
  1. Analyse semaine écoulée (weekly-analysis)
  1b. Évaluation PID & Training Intelligence (pid-daily-evaluation)
  1c. Analyse mensuelle automatique (si transition de mois)
  2. Génération planning semaine suivante (weekly-planner)
  3. Appel AI provider pour génération workouts
  4. Validation notation (format-planning intégré)
  5. Upload workouts vers Intervals.icu
  6. Archivage et commit (optionnel)
        """,
    )

    parser.add_argument(
        "--week-completed",
        type=str,
        required=False,
        help="Semaine terminée (format SXXX, ex: S075). Optionnel si --auto-calculate",
    )

    parser.add_argument(
        "--week-next",
        type=str,
        required=False,
        help="Semaine à planifier (format SXXX, ex: S076). Optionnel si --auto-calculate",
    )

    parser.add_argument(
        "--auto-calculate",
        action="store_true",
        help="Auto-calculer les week-ids à partir de la date du jour (pas de hard-coding)",
    )

    parser.add_argument(
        "--provider",
        type=str,
        choices=["clipboard", "claude_api", "mistral_api"],
        default="clipboard",
        help="AI provider pour génération workouts (défaut: clipboard)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mode simulation (pas d'actions réelles)",
    )

    parser.add_argument(
        "--auto",
        action="store_true",
        help="Mode automatique (pas de confirmations interactives)",
    )

    parser.add_argument(
        "--archive",
        action="store_true",
        help="Archiver et commiter automatiquement",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mode verbose (affiche détails erreurs)",
    )

    return parser.parse_args(args)


@cli_main
def main():
    """Point d'entrée du script."""
    args = parse_args()

    # Auto-calculate week-ids if requested
    if args.auto_calculate:
        if args.week_completed or args.week_next:
            print("⚠️  --auto-calculate ignore les --week-completed et --week-next fournis")

        week_completed, week_next, completed_start, next_start = calculate_weekly_transition()
        print("ℹ️  Transition auto-calculée:")
        print(f"   • Semaine complétée: {week_completed} (début: {completed_start})")
        print(f"   • Semaine suivante:  {week_next} (début: {next_start})")
        print()
    else:
        # Manual mode - validate required args
        if not args.week_completed or not args.week_next:
            print("❌ Erreur: --week-completed et --week-next sont requis")
            print("   Ou utilisez --auto-calculate pour calcul automatique")
            return 1

        week_completed = args.week_completed
        week_next = args.week_next

        # Validate week formats
        if not week_completed.startswith("S") or len(week_completed) != 4:
            print(f"❌ Format semaine invalide : {week_completed}")
            print("   Utiliser le format SXXX (ex: S075)")
            return 1

        if not week_next.startswith("S") or len(week_next) != 4:
            print(f"❌ Format semaine invalide : {week_next}")
            print("   Utiliser le format SXXX (ex: S076)")
            return 1

        # Check week sequence
        completed_num = int(week_completed[1:])
        next_num = int(week_next[1:])

        if next_num != completed_num + 1:
            print(f"⚠️  Attention : {week_next} ne suit pas {week_completed}")
            if not args.auto:
                response = input("Continuer quand même ? (o/n) : ")
                if response.lower() != "o":
                    return 1

    # Execute workflow
    workflow = EndOfWeekWorkflow(
        week_completed=week_completed,
        week_next=week_next,
        provider=args.provider,
        dry_run=args.dry_run,
        auto=args.auto,
        archive=args.archive,
    )

    success = workflow.run()

    return 0 if success else 1


if __name__ == "__main__":
    main()  # @cli_main handles exit codes
