#!/usr/bin/env python3
"""
Daily synchronization checker for training activities and planning.

Facade module — delegates to mixin modules in magma_cycling/workflows/sync/.

Runs as a cron job to:
1. Detect new completed activities uploaded to Intervals.icu
2. Detect planning modifications made by external coach
3. Generate daily report with all changes
4. Optional: Send report via email (Brevo API)

Usage:
    poetry run daily-sync
    poetry run daily-sync --date 2026-01-15
    poetry run daily-sync --week-id S077 --start-date 2026-01-19
    poetry run daily-sync --date 2026-01-15 --week-id S077 --start-date 2026-01-19 --send-email

Email configuration (in .env):
    BREVO_API_KEY=xkeysib-...
    EMAIL_TO=your-email@example.com
    EMAIL_FROM=training@yourdomain.com
    EMAIL_FROM_NAME="Training Logs"

See project-docs/BREVO_SETUP.md for complete setup guide.

Author: Stéphane Jouve
Created: 2026-01-18

Metadata:
    Status: Production
    Priority: P2
    Version: v2.1
"""

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from magma_cycling.ai_providers import AIProviderFactory
from magma_cycling.config import (
    create_intervals_client,
    get_ai_config,
    get_data_config,
    get_week_config,
)
from magma_cycling.insert_analysis import WorkoutHistoryManager
from magma_cycling.prepare_analysis import PromptGenerator
from magma_cycling.utils.cli import cli_main
from magma_cycling.utils.hot_reload import (
    hot_reload_if_needed,
    mark_modules_loaded,
)
from magma_cycling.workflows.proactive_compensation import (
    evaluate_weekly_deficit,
    generate_compensation_prompt,
    parse_ai_compensation_response,
)

# Mixin modules
from magma_cycling.workflows.sync.activity_detection import ActivityDetectionMixin
from magma_cycling.workflows.sync.activity_tracker import ActivityTracker
from magma_cycling.workflows.sync.ai_analysis import AIAnalysisMixin
from magma_cycling.workflows.sync.ctl_peaks import CTLPeaksMixin
from magma_cycling.workflows.sync.reporting import ReportingMixin
from magma_cycling.workflows.sync.servo_evaluation import ServoEvaluationMixin
from magma_cycling.workflows.sync.session_updates import SessionUpdatesMixin


def calculate_current_week_info(target_date: date | None = None) -> tuple[str, date]:
    """Calculate current week-id and start date based on WeekReferenceConfig.

    Args:
        target_date: Date to calculate week for (default: today)

    Returns:
        Tuple of (week_id, start_date)
        - week_id: Week identifier (e.g., "S077")
        - start_date: Monday start date for the week

    Examples:
        >>> week_id, start_date = calculate_current_week_info()
        >>> print(week_id, start_date)
        S077 2026-01-19
    """
    if target_date is None:
        target_date = date.today()

    # Get S001 reference date from config
    week_config = get_week_config()
    s001_date = week_config.get_s001_date_obj("S001")

    # Calculate weeks difference from S001
    delta = target_date - s001_date
    weeks_offset = delta.days // 7

    # Calculate week-id
    week_id = f"S{weeks_offset + 1:03d}"

    # Calculate Monday start date for this week
    start_date = s001_date + timedelta(weeks=weeks_offset)

    return week_id, start_date


class DailySync(
    ActivityDetectionMixin,
    AIAnalysisMixin,
    ServoEvaluationMixin,
    CTLPeaksMixin,
    SessionUpdatesMixin,
    ReportingMixin,
):
    """Daily synchronization checker."""

    def __init__(
        self,
        tracking_file: Path,
        reports_dir: Path,
        enable_ai_analysis: bool = False,
        enable_auto_servo: bool = False,
        verbose: bool = True,
    ):
        """
        Initialize daily sync.

        Args:
            tracking_file: Path to activity tracking JSON
            reports_dir: Directory for daily reports
            enable_ai_analysis: Enable automatic AI analysis of activities
            enable_auto_servo: Enable automatic servo mode for planning adjustments
            verbose: Enable console output (disable for MCP/API usage)
        """
        self.client = create_intervals_client()
        self.tracker = ActivityTracker(tracking_file)
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.enable_ai_analysis = enable_ai_analysis
        self.enable_auto_servo = enable_auto_servo
        self.verbose = verbose

        # Initialize AI analyzer if enabled
        self.ai_analyzer = None
        self.prompt_generator = None
        self.history_manager = None
        if enable_ai_analysis:
            ai_config = get_ai_config()
            available = ai_config.get_available_providers()
            if available:
                default = ai_config.default_provider
                provider = default if default in available else available[0]
                provider_config = ai_config.get_provider_config(provider)
                self.ai_analyzer = AIProviderFactory.create(provider, provider_config)
                self.prompt_generator = PromptGenerator()
                self.history_manager = WorkoutHistoryManager(
                    yes_confirm=True
                )  # Auto-confirm for automation
                print(f"🤖 AI Analysis activé (provider: {provider})")
            else:
                print("⚠️  Aucun provider AI configuré - analysis désactivée")
                self.enable_ai_analysis = False

        # Servo detection criteria (same as workflow_coach)
        self.servo_criteria = {
            "decoupling_threshold": 7.5,  # Découplage >7.5%
            "sleep_threshold_hours": 7.0,  # Sommeil <7h
            "feel_threshold": 4,  # Feel ≥4/5 (Passable/Mauvais) - Intervals.icu scale
            "tsb_threshold": -10,  # TSB <-10
        }

    def run(
        self,
        check_date: date,
        week_id: str | None = None,
        start_date: date | None = None,
        send_email: bool = False,
    ):
        """
        Run daily sync check.

        Args:
            check_date: Date to check activities
            week_id: Optional week ID for planning check
            start_date: Optional week start date
            send_email: Send report via email (requires Brevo config in .env)
        """
        print("=" * 80)
        print("DAILY SYNC - Vérification Quotidienne")
        print("=" * 80)

        # 1. Check activities - returns (new_activities, completed_activities)
        new_activities, completed_activities = self.check_activities(check_date)

        # Mark new activities as analyzed
        for activity in new_activities:
            self.tracker.mark_analyzed(activity, datetime.now())

        # 1b. Auto-update session statuses in local planning JSON
        # Use ALL completed activities (not just new ones) to ensure status updates
        if completed_activities:
            self.update_completed_sessions(completed_activities)

        # 2. Generate AI analyses (if enabled)
        analyses = {}
        if self.enable_ai_analysis and new_activities:
            print(f"\n🤖 Génération analyses AI pour {len(new_activities)} activité(s)...")
            for activity in new_activities:
                analysis = self.analyze_activity(activity)
                if analysis:
                    analyses[activity["id"]] = analysis

        # 2b. Auto-servo mode evaluation (if enabled and AI analysis active)
        servo_result = None
        if self.enable_auto_servo and self.enable_ai_analysis and new_activities and week_id:
            print("\n🔍 Évaluation conditions auto-servo...")

            # Evaluate only the most recent activity (last one analyzed)
            latest_activity = new_activities[-1]
            latest_analysis = analyses.get(latest_activity["id"])

            # Get wellness data for metrics extraction
            try:
                activity_date_str = latest_activity["start_date_local"].split("T")[0]
                wellness_data = self.client.get_wellness(
                    oldest=activity_date_str, newest=activity_date_str
                )
                wellness_pre = wellness_data[0] if wellness_data else None
            except Exception:
                wellness_pre = None

            # Extract metrics
            metrics = self.extract_metrics_from_activity(
                latest_activity, latest_analysis, wellness_pre
            )

            # Check if servo should trigger
            should_trigger, reasons = self.should_trigger_servo(metrics, latest_activity)

            if should_trigger:
                print("\n⚠️  Conditions détectées pour ajustement planning:")
                for reason in reasons:
                    print(f"   • {reason}")
                print()

                # Run servo adjustment
                servo_result = self.run_servo_adjustment(
                    week_id=week_id,
                    activity=latest_activity,
                    metrics=metrics,
                    analysis=latest_analysis,
                )
            else:
                print("  ✅ Aucun signal d'alerte - planning maintenu")

        # 2c. TSS Proactive Compensation (if week specified and AI analysis enabled)
        compensation_result = None
        if week_id and self.enable_ai_analysis:
            print("\n🔍 Évaluation déficit TSS hebdomadaire...")

            # Evaluate weekly deficit
            deficit_context = evaluate_weekly_deficit(
                week_id=week_id, check_date=check_date, client=self.client, threshold_tss=50
            )

            if deficit_context:
                deficit = deficit_context["deficit"]
                print(f"\n⚠️  Déficit TSS détecté: -{deficit:.0f} TSS")
                print(f"   Semaine {week_id}, {deficit_context['days_remaining']} jours restants")

                # Generate compensation prompt
                prompt = generate_compensation_prompt(deficit_context)

                # Call AI analyzer
                try:
                    print("🤖 Demande recommandations compensation au coach AI...")
                    ai_response = self.ai_analyzer.analyze_session(prompt)

                    if ai_response:
                        print(f"  ✅ Réponse reçue ({len(ai_response)} caractères)")

                        # Parse AI response
                        recommendations = parse_ai_compensation_response(ai_response)

                        if recommendations:
                            print(f"✅ Recommandations générées: {recommendations['strategy']}")
                            print(
                                f"   Compensation totale: +{recommendations['total_compensated']} TSS"
                            )

                            compensation_result = {
                                "context": deficit_context,
                                "recommendations": recommendations,
                                "ai_response": ai_response,
                            }
                        else:
                            print("  ⚠️  Échec parsing recommandations AI")
                    else:
                        print("  ⚠️  Pas de réponse du coach AI")

                except Exception as e:
                    print(f"  ❌ Erreur génération recommandations: {e}")
            else:
                print("  ✅ Déficit < seuil (50 TSS) - Pas d'intervention")

        # 2d. CTL Analysis (Peaks Coaching principles)
        ctl_analysis = None
        if self.enable_ai_analysis:
            print("\n🔍 Analyse CTL selon principes Peaks Coaching...")
            ctl_analysis = self.analyze_ctl_peaks(check_date=check_date)

            if ctl_analysis and ctl_analysis.get("alerts"):
                print(f"\n⚠️  {len(ctl_analysis['alerts'])} alerte(s) CTL détectée(s)")
                for alert in ctl_analysis["alerts"]:
                    print(f"   • {alert}")
            else:
                print("  ✅ CTL dans les normes Peaks Coaching")

        # 3. Check planning changes (if week specified)
        planning_changes = {"status": None, "diff": None}
        if week_id and start_date:
            end_date = start_date + timedelta(days=6)
            planning_changes = self.check_planning_changes(week_id, start_date, end_date)

        # 4. Generate report
        report_file = self.generate_report(
            check_date,
            new_activities,
            planning_changes,
            analyses,
            servo_result,
            compensation_result,
            ctl_analysis,
        )

        print(f"\n📝 Rapport généré: {report_file}")

        # 4. Send email if requested
        if send_email:
            email_sent = self.send_email(report_file, check_date)
            if not email_sent:
                print("\n⚠️  Email non envoyé - vérifiez configuration .env")

        print("\n" + "=" * 80)
        print("✅ Daily sync terminé")
        print("=" * 80)


@cli_main
def main():
    """CLI entry point."""
    # Establish baseline for hot-reload detection (first run only)
    mark_modules_loaded()

    # Hot-reload modules if source files changed (prevents cache issues in daemons)
    reloaded = hot_reload_if_needed(verbose=False)
    if reloaded:
        print(f"♻️  Hot-reloaded {len(reloaded)} modified module(s)")

    parser = argparse.ArgumentParser(description="Daily sync checker for training activities")

    parser.add_argument(
        "--date",
        type=str,
        help="Date to check (YYYY-MM-DD). Default: today",
    )
    parser.add_argument(
        "--week-id",
        type=str,
        help="Week ID for planning check (e.g., S077)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="Week start date (YYYY-MM-DD). Required if --week-id specified",
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Send report via email (requires BREVO_API_KEY in .env)",
    )
    parser.add_argument(
        "--ai-analysis",
        action="store_true",
        help="Enable automatic AI analysis of activities",
    )
    parser.add_argument(
        "--auto-servo",
        action="store_true",
        help="Enable automatic servo mode for planning adjustments (requires --ai-analysis and --week-id)",
    )

    args = parser.parse_args()

    # Parse check date
    if args.date:
        check_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        check_date = date.today()

    # Determine week-id and start-date
    week_id = args.week_id
    start_date = None

    # Parse start-date if provided
    if args.start_date:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()

    # Auto-calculate if needed (auto-servo enabled or week-id provided without start-date)
    needs_week_info = args.auto_servo or (week_id and not start_date)

    if needs_week_info and not (week_id and start_date):
        calculated_week_id, calculated_start_date = calculate_current_week_info(check_date)

        if not week_id:
            week_id = calculated_week_id
            start_date = calculated_start_date
            print(f"ℹ️  Week-id auto-calculé: {week_id} (début: {start_date})")
        elif not start_date:
            start_date = calculated_start_date
            print(f"ℹ️  Start-date auto-calculé pour {week_id}: {start_date}")

    # Validate auto-servo requirements
    if args.auto_servo:
        if not args.ai_analysis:
            print("❌ Erreur: --auto-servo nécessite --ai-analysis")
            sys.exit(1)

    # Setup paths from config (uses TRAINING_DATA_REPO env var or ~/training-logs fallback)
    data_config = get_data_config()
    tracking_file = data_config.data_dir / "activities_tracking.json"
    reports_dir = data_config.data_repo_path / "daily-reports"

    # Run sync
    sync = DailySync(
        tracking_file=tracking_file,
        reports_dir=reports_dir,
        enable_ai_analysis=args.ai_analysis,
        enable_auto_servo=args.auto_servo,
    )
    sync.run(
        check_date=check_date,
        week_id=week_id,
        start_date=start_date,
        send_email=args.send_email,
    )


if __name__ == "__main__":
    main()
