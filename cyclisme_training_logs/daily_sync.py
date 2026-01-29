#!/usr/bin/env python3
"""
Daily synchronization checker for training activities and planning.

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
    Version: v2.0
"""

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import markdown2
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from cyclisme_training_logs.ai_providers import AIProviderFactory
from cyclisme_training_logs.config import (
    create_intervals_client,
    get_ai_config,
    get_email_config,
    get_week_config,
)
from cyclisme_training_logs.config.athlete_profile import AthleteProfile
from cyclisme_training_logs.insert_analysis import WorkoutHistoryManager
from cyclisme_training_logs.planning.calendar import TrainingCalendar, WorkoutType
from cyclisme_training_logs.planning.intervals_sync import IntervalsSync
from cyclisme_training_logs.prepare_analysis import PromptGenerator
from cyclisme_training_logs.workflows.proactive_compensation import (
    evaluate_weekly_deficit,
    format_compensation_section,
    generate_compensation_prompt,
    parse_ai_compensation_response,
)


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


class ActivityTracker:
    """Track analyzed activities to avoid re-processing."""

    def __init__(self, tracking_file: Path):
        """
        Initialize activity tracker.

        Args:
            tracking_file: Path to JSON file storing analyzed activity IDs
        """
        self.tracking_file = tracking_file
        self.data = self._load()

    def _load(self) -> dict:
        """Load tracking data from file."""
        if self.tracking_file.exists():
            with open(self.tracking_file) as f:
                return json.load(f)
        return {}

    def _save(self):
        """Save tracking data to file."""
        self.tracking_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.tracking_file, "w") as f:
            json.dump(self.data, f, indent=2)

    def is_analyzed(self, activity_id: int, activity_date: date) -> bool:
        """
        Check if activity has been analyzed.

        Args:
            activity_id: Intervals.icu activity ID
            activity_date: Activity date

        Returns:
            True if already analyzed
        """
        date_key = activity_date.isoformat()
        if date_key not in self.data:
            return False

        return any(a["id"] == activity_id for a in self.data[date_key].get("activities", []))

    def mark_analyzed(self, activity: dict, analyzed_at: datetime):
        """
        Mark activity as analyzed.

        Args:
            activity: Activity dict from Intervals.icu API
            analyzed_at: Timestamp of analysis
        """
        activity_date = datetime.fromisoformat(activity["start_date_local"]).date()
        date_key = activity_date.isoformat()

        if date_key not in self.data:
            self.data[date_key] = {"activities": []}

        # Use paired_event_id if available (planned activity), otherwise activity ID (unplanned)
        tracking_id = activity.get("paired_event_id") or activity["id"]

        self.data[date_key]["activities"].append(
            {
                "id": tracking_id,
                "activity_id": activity["id"],  # Store actual activity ID for reference
                "paired_event_id": activity.get("paired_event_id"),
                "name": activity.get("name"),
                "type": activity.get("type"),
                "icu_training_load": activity.get("icu_training_load"),
                "analyzed": True,
                "analyzed_at": analyzed_at.isoformat(),
            }
        )

        self._save()


class DailySync:
    """Daily synchronization checker."""

    def __init__(
        self,
        tracking_file: Path,
        reports_dir: Path,
        enable_ai_analysis: bool = False,
        enable_auto_servo: bool = False,
    ):
        """
        Initialize daily sync.

        Args:
            tracking_file: Path to activity tracking JSON
            reports_dir: Directory for daily reports
            enable_ai_analysis: Enable automatic AI analysis of activities
            enable_auto_servo: Enable automatic servo mode for planning adjustments
        """
        self.client = create_intervals_client()
        self.tracker = ActivityTracker(tracking_file)
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.enable_ai_analysis = enable_ai_analysis
        self.enable_auto_servo = enable_auto_servo

        # Initialize AI analyzer if enabled
        self.ai_analyzer = None
        self.prompt_generator = None
        self.history_manager = None
        if enable_ai_analysis:
            ai_config = get_ai_config()
            available = ai_config.get_available_providers()
            if available:
                provider = available[0]
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
            "feel_threshold": 2,  # Feel ≤2/4 (Difficile/Moyen)
            "tsb_threshold": -10,  # TSB <-10
        }

    def check_activities(self, check_date: date) -> list[dict]:
        """
        Check for new completed activities on given date.

        Retrieves both:
        - Planned activities (paired with WORKOUT events)
        - Unplanned activities (no event association)

        Args:
            check_date: Date to check

        Returns:
            List of new completed activities (from activities API, not events)
        """
        print(f"\n🔍 Vérification activités du {check_date.strftime('%d/%m/%Y')}...")

        # Get all activities for the date (includes both planned and unplanned)
        all_activities = self.client.get_activities(
            oldest=check_date.isoformat(), newest=check_date.isoformat()
        )

        # Filter out activities that are ignored or incomplete
        completed_activities = [
            act
            for act in all_activities
            if not act.get("icu_ignore_time", False)  # Not ignored
            and act.get("type") in ["Ride", "VirtualRide"]  # Cycling activities only
        ]

        # Filter new activities (not yet analyzed)
        # Use activity ID (not event ID) for tracking
        new_activities = []
        planned_count = 0
        unplanned_count = 0

        for activity in completed_activities:
            # Convert activity ID to comparable format (tracker uses event IDs from old format)
            # For new format, we use the event ID if available, otherwise the activity ID
            tracking_id = activity.get("paired_event_id") or activity["id"]

            # Check if already analyzed
            if self.tracker.is_analyzed(tracking_id, check_date):
                continue

            new_activities.append(activity)

            # Count planned vs unplanned
            if activity.get("paired_event_id"):
                planned_count += 1
            else:
                unplanned_count += 1

        print(f"  ✅ {len(completed_activities)} activité(s) complétée(s)")
        print(f"  📋 {planned_count} planifiée(s), {unplanned_count} non planifiée(s)")
        print(f"  🆕 {len(new_activities)} nouvelle(s) activité(s) à analyser")

        return new_activities

    def check_planning_changes(self, week_id: str, start_date: date, end_date: date) -> dict:
        """
        Check for planning modifications by external coach.

        Args:
            week_id: Week identifier (e.g., "S077")
            start_date: Week start date
            end_date: Week end date

        Returns:
            Dict with sync status and diff
        """
        print(f"\n🔍 Vérification modifications planning {week_id}...")

        # Load week planning
        planning_file = Path(
            f"/Users/stephanejouve/training-logs/data/week_planning/week_planning_{week_id}.json"
        )

        if not planning_file.exists():
            print(f"  ⚠️  Planning {week_id} introuvable")
            return {"status": None, "diff": None}

        with open(planning_file) as f:
            planning_data = json.load(f)

        # Create minimal calendar for sync check
        profile = AthleteProfile.from_env()
        calendar = TrainingCalendar(year=start_date.year, athlete_profile=profile)

        # Add planned sessions (simplified, no full description loading)
        workout_type_map = {
            "END": WorkoutType.ENDURANCE,
            "INT": WorkoutType.TEMPO,
            "PDC": WorkoutType.RECOVERY,
            "REC": WorkoutType.RECOVERY,
        }

        for session_data in planning_data["planned_sessions"]:
            session_date = date.fromisoformat(session_data["date"])

            # Skip rest days
            if session_date.weekday() == 6:  # Sunday
                continue

            session = calendar.add_session(
                session_date=session_date,
                workout_type=workout_type_map.get(session_data["type"], WorkoutType.ENDURANCE),
                planned_tss=session_data["tss_planned"],
                duration_min=session_data["duration_min"],
            )

            # Add description hash for content change detection
            session.description = session_data.get("description", "")
            session.description_hash = session_data.get("description_hash")

        # Check sync
        sync = IntervalsSync()
        status = sync.get_sync_status(calendar=calendar, start_date=start_date, end_date=end_date)

        if status.diff.has_changes():
            print(f"  ⚠️  {status.summary()}")
        else:
            print("  ✅ Aucune modification détectée")

        return {"status": status, "diff": status.diff}

    def _extract_existing_analysis(self, activity_name: str, activity_date_str: str) -> str | None:
        """
        Check if analysis already exists in workouts-history.md and extract it.

        Args:
            activity_name: Name of the activity
            activity_date_str: Date in format DD/MM/YYYY

        Returns:
            Existing analysis text or None if not found
        """
        if not self.history_manager:
            return None

        try:
            history_content = self.history_manager.read_history()
            if not history_content:
                return None

            # Look for the activity entry
            import re

            # Pattern: ### ACTIVITY_NAME\nDate : DATE
            pattern = (
                rf"###\s*{re.escape(activity_name)}\s*\nDate\s*:\s*{re.escape(activity_date_str)}"
            )
            match = re.search(pattern, history_content)

            if not match:
                return None

            # Extract the full entry (from ### to next ### or end)
            start_pos = match.start()
            next_entry = re.search(r"\n###\s+", history_content[start_pos + 1 :])

            if next_entry:
                end_pos = start_pos + 1 + next_entry.start()
                analysis = history_content[start_pos:end_pos].strip()
            else:
                analysis = history_content[start_pos:].strip()

            return analysis

        except Exception as e:
            print(f"     ⚠️  Erreur extraction analyse existante: {e}")
            return None

    def analyze_activity(self, activity: dict) -> str | None:
        """
        Generate or retrieve AI analysis for an activity.

        Checks if analysis already exists in workouts-history.md:
        - If yes: extracts and returns existing analysis
        - If no: generates new analysis, inserts into history, and returns it

        Args:
            activity: Activity dict with id and other metadata

        Returns:
            Analysis text or None if failed
        """
        if not self.enable_ai_analysis or not self.ai_analyzer:
            return None

        try:
            # Use activity ID directly (activity dict, not event dict)
            activity_id = activity.get("id")
            if not activity_id:
                print(f"  ⚠️  Pas d'ID activité pour {activity.get('name', 'Unknown')}")
                return None

            activity_name = activity.get("name", "")
            print(f"  🔍 Vérification analyse existante pour {activity_name}...")

            # Extract date from activity
            activity_date = date.fromisoformat(activity["start_date_local"].split("T")[0])
            activity_date_str = activity_date.strftime("%d/%m/%Y")

            # Check if analysis already exists
            existing_analysis = self._extract_existing_analysis(activity_name, activity_date_str)

            if existing_analysis:
                print("     ✅ Analyse existante trouvée dans workouts-history.md")
                return existing_analysis

            print(f"  🤖 Génération nouvelle analyse AI pour {activity_name}...")

            # Add is_strava flag (required by PromptGenerator)
            activity["is_strava"] = activity.get("source") == "STRAVA"

            # Get wellness data (pre and post)
            activity_date_str = activity["start_date_local"].split("T")[0]

            # Get pre-workout wellness
            try:
                wellness_data = self.client.get_wellness(
                    oldest=activity_date_str, newest=activity_date_str
                )
                wellness_pre = wellness_data[0] if wellness_data else None
            except Exception:
                wellness_pre = None

            # Get post-workout wellness (may not exist yet for today's workout)
            try:
                activity_date = date.fromisoformat(activity_date_str)
                next_day = activity_date + timedelta(days=1)
                next_day_str = next_day.isoformat()
                wellness_data = self.client.get_wellness(oldest=next_day_str, newest=next_day_str)
                wellness_post = wellness_data[0] if wellness_data else None
            except Exception:
                wellness_post = None

            # Load athlete context and recent workouts
            athlete_context = self.prompt_generator.load_athlete_context()
            recent_workouts = self.prompt_generator.load_recent_workouts(limit=5)

            # Format activity data for prompt generation
            activity_data = self.prompt_generator.format_activity_data(activity)

            # Generate complete prompt
            prompt = self.prompt_generator.generate_prompt(
                activity_data=activity_data,
                wellness_pre=wellness_pre,
                wellness_post=wellness_post,
                athlete_context=athlete_context,
                recent_workouts=recent_workouts,
                athlete_feedback=None,  # No feedback in automated mode
                planned_workout=None,  # Could be added later
                cycling_concepts=None,
            )

            # Get AI analysis
            analysis = self.ai_analyzer.analyze_session(prompt)

            if analysis:
                print(f"     ✅ Analyse générée ({len(analysis)} caractères)")

                # Insert analysis into workouts-history.md
                print("     📝 Insertion dans workouts-history.md...")
                try:
                    if self.history_manager.insert_analysis(analysis):
                        print("     ✅ Analyse insérée dans workouts-history.md")
                    else:
                        print("     ⚠️  Échec insertion (analyse utilisée quand même)")
                except Exception as e:
                    print(f"     ⚠️  Erreur insertion workouts-history.md: {e}")
                    # Continue anyway - we still have the analysis for email

                return analysis
            else:
                print("     ⚠️  Échec génération analyse")
                return None

        except Exception as e:
            print(f"     ❌ Erreur analyse AI: {e}")
            return None

    def extract_metrics_from_activity(
        self, activity: dict, analysis: str | None, wellness_pre: dict | None
    ) -> dict:
        """
        Extract key metrics from activity data and analysis.

        Args:
            activity: Activity dict from Intervals.icu
            analysis: AI analysis text (if available)
            wellness_pre: Pre-workout wellness data

        Returns:
            Dict with extracted metrics for servo evaluation
        """
        metrics = {
            "tsb": None,
            "sleep_hours": None,
            "decoupling": None,
            "feel": None,
            "tss_planned": None,
            "tss_actual": None,
            "duration_planned_min": None,
            "duration_actual_min": None,
        }

        # Extract from wellness
        if wellness_pre:
            try:
                from cyclisme_training_logs.utils.metrics import (
                    extract_wellness_metrics,
                )

                wellness_metrics = extract_wellness_metrics(wellness_pre)
                metrics["tsb"] = wellness_metrics.get("tsb")

                # Sleep in hours
                sleep_secs = wellness_pre.get("sleepSecs", 0)
                if sleep_secs:
                    metrics["sleep_hours"] = sleep_secs / 3600.0

                # Feel (1-4 scale)
                metrics["feel"] = activity.get("feel")
            except Exception as e:
                print(f"     ⚠️  Erreur extraction wellness: {e}")

        # Extract from activity
        metrics["tss_actual"] = activity.get("icu_training_load")
        metrics["duration_actual_min"] = activity.get("moving_time", 0) // 60
        metrics["decoupling"] = activity.get("decoupling")

        # Try to get planned values from session name (if it follows naming convention)
        # This would require looking up the planning JSON, but for now we'll skip
        # The servo will work without TSS comparison if not available

        return metrics

    def should_trigger_servo(self, metrics: dict) -> tuple[bool, list[str]]:
        """
        Evaluate if servo mode should be triggered based on metrics.

        Uses same criteria as workflow_coach servo-mode:
        - Découplage >7.5%
        - Sommeil <7h
        - Feel ≤2/4 (Difficile/Moyen)
        - TSB <-10

        Args:
            metrics: Dict with extracted metrics

        Returns:
            Tuple of (should_trigger, reasons)
        """
        reasons = []

        # Criterion 1: Decoupling
        if metrics.get("decoupling") is not None:
            if metrics["decoupling"] > self.servo_criteria["decoupling_threshold"]:
                reasons.append(
                    f"Découplage élevé ({metrics['decoupling']:.1f}% > {self.servo_criteria['decoupling_threshold']}%)"
                )

        # Criterion 2: Sleep
        if metrics.get("sleep_hours") is not None:
            if metrics["sleep_hours"] < self.servo_criteria["sleep_threshold_hours"]:
                reasons.append(
                    f"Sommeil insuffisant ({metrics['sleep_hours']:.1f}h < {self.servo_criteria['sleep_threshold_hours']}h)"
                )

        # Criterion 3: Feel (subjective)
        if metrics.get("feel") is not None:
            if metrics["feel"] <= self.servo_criteria["feel_threshold"]:
                feel_labels = {1: "Difficile", 2: "Moyen", 3: "Bon", 4: "Excellent"}
                feel_label = feel_labels.get(metrics["feel"], "Unknown")
                reasons.append(f"Ressenti négatif ({feel_label} - {metrics['feel']}/4)")

        # Criterion 4: TSB
        if metrics.get("tsb") is not None:
            if metrics["tsb"] < self.servo_criteria["tsb_threshold"]:
                reasons.append(
                    f"Forme dégradée (TSB {metrics['tsb']:+.0f} < {self.servo_criteria['tsb_threshold']})"
                )

        # Trigger if at least one strong signal
        should_trigger = len(reasons) > 0

        return should_trigger, reasons

    def run_servo_adjustment(
        self, week_id: str, activity: dict, metrics: dict, analysis: str | None
    ) -> dict | None:
        """
        Run servo mode to get AI recommendations for planning adjustments.

        Args:
            week_id: Week identifier (e.g., "S077")
            activity: Activity dict
            metrics: Extracted metrics
            analysis: AI analysis of the session

        Returns:
            Dict with servo recommendations or None if failed
        """
        try:
            print("\n" + "=" * 80)
            print("🔄 SERVO MODE AUTOMATIQUE - Ajustement Planning")
            print("=" * 80)
            print()

            # Load remaining sessions from planning
            from cyclisme_training_logs.workflow_coach import WorkflowCoach

            coach = WorkflowCoach(servo_mode=True)
            remaining_sessions = coach.load_remaining_sessions(week_id)

            if not remaining_sessions:
                print("  ⚠️  Aucune séance future dans le planning")
                return None

            print(f"📋 {len(remaining_sessions)} séance(s) restante(s) dans le planning")
            print()

            # Format metrics for prompt
            tsb_str = f"{metrics['tsb']:+.0f}" if metrics.get("tsb") is not None else "N/A"
            sleep_str = (
                f"{metrics['sleep_hours']:.1f}h"
                if metrics.get("sleep_hours") is not None
                else "Non disponible"
            )
            decoupling_str = (
                f"{metrics['decoupling']:.1f}%"
                if metrics.get("decoupling") is not None
                else "Non disponible"
            )
            feel_str = f"{metrics['feel']}/4" if metrics.get("feel") is not None else "Non fourni"

            # Generate servo prompt (same as workflow_coach)
            planning_context = coach.format_remaining_sessions_compact(remaining_sessions)

            servo_prompt = f"""# ASSERVISSEMENT PLANNING - Demande Coach AI.

Contexte : Tu viens d'analyser la séance du jour.

## Métriques de la séance analysée
- TSB pré-séance : {tsb_str}
- Sommeil : {sleep_str}
- Ressenti (Feel) : {feel_str}
- Découplage cardiovasculaire : {decoupling_str}

{planning_context}

## Catalogue Workouts Remplacement

Si modification planning nécessaire, utilise ces templates prédéfinis :

**RÉCUPÉRATION** (remplacement END/INT léger) :
- `recovery_active_30tss` : 45min Z1-Z2 (30 TSS)
- `recovery_active_25tss` : 40min Z1-Z2 (25 TSS)
- `recovery_short_20tss` : 30min Z1 (20 TSS)

**ENDURANCE ALLÉGÉE** (remplacement END normal) :
- `endurance_light_35tss` : 50min Z2 (35 TSS)
- `endurance_short_40tss` : 55min Z2 (40 TSS)

**INTENSITÉ RÉDUITE** (remplacement Sweet-Spot/VO2) :
- `sweetspot_short_50tss` : 2x10min 88% (50 TSS)

## Instructions

Basé sur l'analyse de la séance du jour et les métriques réelles ci-dessus, **recommandes-tu des ajustements au planning restant ?**

Critères de décision:
- RPE > 8/10 en zone endurance → Signal alarme
- Découplage > 7.5% → Fatigue cardiaque
- Sommeil < 7h → Vulnérabilité accrue
- TSB < -10 → Forme dégradée

**IMPORTANT:**
- Utilise UNIQUEMENT les valeurs de métriques fournies ci-dessus
- Si une métrique est "Non disponible", ne PAS inventer de valeur
- Justifier les recommandations avec les métriques RÉELLES

**Format JSON si modification recommandée** :
```json
{{"modifications": [{{
  "action": "lighten",
  "target_date": "YYYY-MM-DD",
  "current_workout": "CODE",
  "template_id": "recovery_active_30tss",
  "reason": "Découplage 11.2%, prioriser récupération"
}}]}}
```

**Si aucune modification nécessaire** : Ne rien ajouter (pas de JSON).

Réponds maintenant."""

            # Call AI analyzer
            print("🤖 Demande recommandations au coach AI...")
            ai_response = self.ai_analyzer.analyze_session(servo_prompt)

            if not ai_response:
                print("  ⚠️  Pas de réponse du coach AI")
                return None

            print(f"  ✅ Réponse reçue ({len(ai_response)} caractères)")
            print()

            # Parse modifications
            modifications = coach.parse_ai_modifications(ai_response)

            result = {
                "ai_response": ai_response,
                "modifications": modifications,
                "remaining_sessions": remaining_sessions,
            }

            if modifications:
                print(f"📋 {len(modifications)} modification(s) recommandée(s)")
                for mod in modifications:
                    action = mod.get("action", "unknown")
                    target_date = mod.get("target_date", "N/A")
                    reason = mod.get("reason", "N/A")
                    print(f"  • {target_date}: {action} - {reason}")
            else:
                print("✅ Aucune modification recommandée - planning maintenu")

            print()
            print("=" * 80)

            return result

        except Exception as e:
            print(f"  ❌ Erreur servo mode: {e}")
            import traceback

            traceback.print_exc()
            return None

    def generate_report(
        self,
        check_date: date,
        new_activities: list[dict],
        planning_changes: dict,
        analyses: dict[int, str] | None = None,
        servo_result: dict | None = None,
        compensation_result: dict | None = None,
    ) -> Path:
        """
        Generate markdown daily report.

        Args:
            check_date: Date of check
            new_activities: List of new completed activities
            planning_changes: Dict with planning changes
            analyses: Dict of AI analyses by activity ID
            servo_result: Servo mode recommendations (if triggered)
            compensation_result: TSS proactive compensation (if deficit detected)

        Returns:
            Path to generated report file
        """
        report_file = self.reports_dir / f"daily_report_{check_date.isoformat()}.md"

        with open(report_file, "w") as f:
            f.write(f"# Rapport Quotidien - {check_date.strftime('%d/%m/%Y')}\n\n")
            f.write(f"**Généré le**: {datetime.now().strftime('%d/%m/%Y à %H:%M')}\n\n")
            f.write("---\n\n")

            # Section 1: Activities
            f.write("## 📊 Activités Complétées\n\n")
            if new_activities:
                f.write(f"**{len(new_activities)} nouvelle(s) activité(s) détectée(s)**\n\n")
                for activity in new_activities:
                    f.write(f"### {activity['name']}\n\n")
                    f.write(f"- **ID**: {activity['id']}\n")
                    f.write(f"- **Type**: {activity.get('type', 'N/A')}\n")
                    f.write(f"- **TSS**: {activity.get('icu_training_load', 'N/A')} (réalisé)\n")
                    f.write(f"- **Durée**: {activity.get('moving_time', 0) // 60} min\n")
                    f.write(f"- **Activité liée**: {activity.get('paired_activity_id', 'N/A')}\n")
                    f.write("\n")

                    # Add AI analysis if available
                    if analyses and activity["id"] in analyses:
                        f.write("#### 🤖 Analyse AI\n\n")
                        f.write(analyses[activity["id"]])
                        f.write("\n\n")
            else:
                f.write("*Aucune nouvelle activité détectée*\n\n")

            # Section 2: Planning changes
            f.write("---\n\n")
            f.write("## 📅 Modifications Planning\n\n")

            if planning_changes.get("diff") and planning_changes["diff"].has_changes():
                diff = planning_changes["diff"]

                if diff.removed_remote:
                    f.write(f"### 🗑️ Supprimés ({len(diff.removed_remote)})\n\n")
                    for workout in diff.removed_remote:
                        f.write(f"- **{workout['date']}**: {workout['name']}\n")
                    f.write("\n")

                if diff.added_remote:
                    f.write(f"### ➕ Ajoutés ({len(diff.added_remote)})\n\n")
                    for workout in diff.added_remote:
                        f.write(
                            f"- **{workout['date']}**: {workout['name']} (ID: {workout['id']})\n"
                        )
                    f.write("\n")

                if diff.modified_remote:
                    f.write(f"### ✏️ Modifiés ({len(diff.modified_remote)})\n\n")
                    for mod in diff.modified_remote:
                        f.write(f"#### {mod['date']}\n\n")
                        f.write(f"- **Local**: {mod['local']['name']}\n")
                        f.write(
                            f"- **Remote**: {mod['remote']['name']} (ID: {mod['remote']['id']})\n"
                        )
                        if "diff" in mod:
                            f.write("\n**Changements**:\n```diff\n")
                            f.write(mod["diff"])
                            f.write("\n```\n\n")
            else:
                f.write("*Aucune modification détectée dans le planning*\n\n")

            # Section 3: Servo recommendations (if triggered)
            if servo_result:
                f.write("---\n\n")
                f.write("## 🔄 Ajustements Planning (Auto-Servo)\n\n")

                modifications = servo_result.get("modifications", [])
                ai_response = servo_result.get("ai_response", "")

                if modifications:
                    f.write(
                        f"**⚠️  {len(modifications)} modification(s) recommandée(s) par le coach AI**\n\n"
                    )

                    for mod in modifications:
                        action = mod.get("action", "unknown")
                        target_date = mod.get("target_date", "N/A")
                        current_workout = mod.get("current_workout", "N/A")
                        template_id = mod.get("template_id", "N/A")
                        reason = mod.get("reason", "N/A")

                        f.write(f"### 📅 {target_date}\n\n")
                        f.write(f"- **Action**: {action}\n")
                        f.write(f"- **Séance actuelle**: {current_workout}\n")
                        f.write(f"- **Remplacement**: {template_id}\n")
                        f.write(f"- **Raison**: {reason}\n\n")

                    f.write("#### 🤖 Analyse complète du coach AI\n\n")
                    f.write("```\n")
                    f.write(ai_response[:500] + "..." if len(ai_response) > 500 else ai_response)
                    f.write("\n```\n\n")

                    f.write(
                        "**⚠️  Action requise**: Utiliser `poetry run update-session` pour appliquer les modifications\n\n"
                    )
                else:
                    f.write(
                        "✅ **Aucune modification recommandée** - Planning maintenu tel quel\n\n"
                    )

            # Section 4: TSS Proactive Compensation (if deficit detected)
            if compensation_result:
                context = compensation_result.get("context")
                recommendations = compensation_result.get("recommendations")

                if context and recommendations:
                    f.write("---\n\n")
                    compensation_section = format_compensation_section(context, recommendations)
                    f.write(compensation_section)

            f.write("---\n\n")
            f.write(
                "*Rapport généré automatiquement par daily-sync - "
                "[cyclisme-training-logs](https://github.com/stephanejouve/cyclisme-training-logs)*\n"
            )

        return report_file

    def send_email(self, report_file: Path, check_date: date) -> bool:
        """
        Send daily report via email using Brevo API.

        Args:
            report_file: Path to markdown report file
            check_date: Date of report

        Returns:
            True if email sent successfully

        Configuration (via config.py):
            Uses get_email_config() which reads from .env:
            - BREVO_API_KEY: Brevo API key
            - EMAIL_TO: Recipient email address
            - EMAIL_FROM: Sender email address (verified in Brevo)
            - EMAIL_FROM_NAME: Sender name (optional, default: "Training Logs")
        """
        # Get email configuration
        email_config = get_email_config()

        if not email_config.is_configured():
            print("\n⚠️  Configuration email manquante dans .env:")
            for var in email_config.get_missing_vars():
                print(f"  - {var} manquant")
            return False

        print("\n📧 Envoi email via Brevo...")

        try:
            # Configure Brevo API
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key["api-key"] = email_config.api_key

            # Read markdown report
            markdown_content = report_file.read_text(encoding="utf-8")

            # Convert markdown to HTML with CSS styling
            html_content = markdown2.markdown(
                markdown_content,
                extras=["fenced-code-blocks", "tables", "code-friendly"],
            )

            # Add CSS styling for better email rendering
            styled_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    h1 {{
                        color: #2c3e50;
                        border-bottom: 3px solid #3498db;
                        padding-bottom: 10px;
                    }}
                    h2 {{
                        color: #34495e;
                        margin-top: 30px;
                        border-bottom: 2px solid #ecf0f1;
                        padding-bottom: 5px;
                    }}
                    h3 {{
                        color: #7f8c8d;
                        margin-top: 20px;
                    }}
                    code {{
                        background-color: #f8f9fa;
                        padding: 2px 6px;
                        border-radius: 3px;
                        font-family: 'Monaco', 'Courier New', monospace;
                        font-size: 0.9em;
                    }}
                    pre {{
                        background-color: #f8f9fa;
                        border: 1px solid #e1e4e8;
                        border-radius: 6px;
                        padding: 16px;
                        overflow-x: auto;
                    }}
                    pre code {{
                        background-color: transparent;
                        padding: 0;
                    }}
                    ul {{
                        line-height: 1.8;
                    }}
                    hr {{
                        border: none;
                        border-top: 2px solid #ecf0f1;
                        margin: 30px 0;
                    }}
                    .emoji {{
                        font-size: 1.2em;
                    }}
                    a {{
                        color: #3498db;
                        text-decoration: none;
                    }}
                    a:hover {{
                        text-decoration: underline;
                    }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """

            # Create email object
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
                sib_api_v3_sdk.ApiClient(configuration)
            )

            subject = f"📊 Rapport Quotidien Training - {check_date.strftime('%d/%m/%Y')}"

            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": email_config.email_to}],
                sender={"name": email_config.email_from_name, "email": email_config.email_from},
                subject=subject,
                html_content=styled_html,
                text_content=markdown_content,  # Fallback for text-only clients
            )

            # Send email
            api_response = api_instance.send_transac_email(send_smtp_email)

            print(f"  ✅ Email envoyé avec succès (ID: {api_response.message_id})")
            print(f"  📬 Destinataire: {email_config.email_to}")
            return True

        except ApiException as e:
            print(f"  ❌ Erreur Brevo API: {e}")
            return False
        except Exception as e:
            print(f"  ❌ Erreur envoi email: {e}")
            return False

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

        # 1. Check activities
        new_activities = self.check_activities(check_date)

        # Mark as analyzed
        for activity in new_activities:
            self.tracker.mark_analyzed(activity, datetime.now())

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
            should_trigger, reasons = self.should_trigger_servo(metrics)

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


def main():
    """CLI entry point."""
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

    # Setup paths
    tracking_file = Path("/Users/stephanejouve/training-logs/data/activities_tracking.json")
    reports_dir = Path("/Users/stephanejouve/training-logs/daily-reports")

    # Run sync
    sync = DailySync(
        tracking_file=tracking_file,
        reports_dir=reports_dir,
        enable_ai_analysis=args.ai_analysis,
        enable_auto_servo=args.auto_servo,
    )
    sync.run(
        check_date=check_date,
        week_id=args.week_id,
        start_date=start_date,
        send_email=args.send_email,
    )


if __name__ == "__main__":
    main()
