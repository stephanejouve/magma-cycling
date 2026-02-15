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
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import markdown2
import sib_api_v3_sdk
from pydantic import ValidationError
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
from cyclisme_training_logs.intelligence.discrete_pid_controller import DiscretePIDController
from cyclisme_training_logs.planning.calendar import TrainingCalendar, WorkoutType
from cyclisme_training_logs.planning.intervals_sync import IntervalsSync
from cyclisme_training_logs.planning.models import WeeklyPlan
from cyclisme_training_logs.planning.peaks_phases import (
    determine_training_phase,
    format_phase_recommendation,
)
from cyclisme_training_logs.prepare_analysis import PromptGenerator
from cyclisme_training_logs.workflows.pid_peaks_integration import (
    compute_integrated_correction,
    format_integrated_recommendation,
)
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
            with open(self.tracking_file, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self):
        """Save tracking data to file."""
        self.tracking_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.tracking_file, "w", encoding="utf-8") as f:
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
            "feel_threshold": 4,  # Feel ≥4/5 (Passable/Mauvais) - Intervals.icu scale
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

        try:
            # ✅ Chargement sécurisé avec validation Pydantic
            plan = WeeklyPlan.from_json(planning_file)
        except (ValidationError, json.JSONDecodeError) as e:
            print(f"  ⚠️  Erreur chargement planning {week_id}: {e}")
            return {"status": None, "diff": None}

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

        for session in plan.planned_sessions:
            session_date = session.session_date

            # Skip rest days
            if session_date.weekday() == 6:  # Sunday
                continue

            cal_session = calendar.add_session(
                session_date=session_date,
                workout_type=workout_type_map.get(session.session_type, WorkoutType.ENDURANCE),
                planned_tss=session.tss_planned,
                duration_min=session.duration_min,
            )

            # Add description hash for content change detection
            cal_session.description = session.description or ""
            cal_session.description_hash = session.description_hash

        # Check sync
        sync = IntervalsSync()
        status = sync.get_sync_status(calendar=calendar, start_date=start_date, end_date=end_date)

        if status.diff.has_changes():
            print(f"  ⚠️  {status.summary()}")
        else:
            print("  ✅ Aucune modification détectée")

        return {"status": status, "diff": status.diff}

    def _extract_existing_analysis(
        self, activity_name: str, activity_id: str, activity_date_str: str
    ) -> str | None:
        """
        Check if analysis already exists in workouts-history.md and extract it.

        Args:
            activity_name: Name of the activity
            activity_id: Activity ID (e.g., i122040268)
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

            # Pattern: ### ACTIVITY_NAME\nID : ACTIVITY_ID\nDate : DATE
            # This ensures we match the exact activity even if multiple activities
            # have the same name on the same day
            pattern = (
                rf"###\s*{re.escape(activity_name)}\s*\n"
                rf"ID\s*:\s*{re.escape(activity_id)}\s*\n"
                rf"Date\s*:\s*{re.escape(activity_date_str)}"
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
            existing_analysis = self._extract_existing_analysis(
                activity_name, activity_id, activity_date_str
            )

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

                # Feel (Intervals.icu 1-5 scale: 1=Excellent, 5=Poor)
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

    def _is_low_effort_social_ride(self, activity: dict, metrics: dict) -> bool:
        """
        Detect false positive scenarios for decoupling alerts.

        Identifies social/accompaniment rides with frequent stops that
        generate artificially high decoupling values.

        Detection criteria:
        - Very low TSS (<30)
        - Very low avg power vs normalized power ratio (<0.5)
        - Keywords in notes: accompagnement, arrêts, attendre, partage, échange

        Args:
            activity: Activity dict with power metrics and notes
            metrics: Extracted metrics dict

        Returns:
            True if this is likely a low-effort social ride (false positive)
        """
        # Criterion 1: Very low TSS
        tss = activity.get("icu_training_load", 0)
        if tss >= 30:
            return False

        # Criterion 2: Very low power ratio (indicates frequent stops)
        avg_power = activity.get("average_watts", 0)
        normalized_power = activity.get("np", 0)
        if normalized_power > 0:
            power_ratio = avg_power / normalized_power
            if power_ratio < 0.5:  # Avg power < 50% of NP = many stops
                return True

        # Criterion 3: Keywords in notes/description
        description = activity.get("description", "").lower()
        keywords = [
            "accompagnement",
            "accompagner",
            "arrêts",
            "arrêt",
            "attendre",
            "attente",
            "partage",
            "partagé",
            "échange",
            "échangé",
            "initiation",
            "découvrir",
            "pied à terre",
            "mise à terre",
        ]

        if any(keyword in description for keyword in keywords):
            return True

        return False

    def should_trigger_servo(
        self, metrics: dict, activity: dict | None = None
    ) -> tuple[bool, list[str]]:
        """
        Evaluate if servo mode should be triggered based on metrics.

        Uses same criteria as workflow_coach servo-mode:
        - Découplage >7.5% (with false positive detection for social rides)
        - Sommeil <7h
        - Feel ≥4/5 (Passable/Mauvais) - Intervals.icu scale
        - TSB <-10

        Args:
            metrics: Dict with extracted metrics
            activity: Activity dict (optional, for false positive detection)

        Returns:
            Tuple of (should_trigger, reasons)
        """
        reasons = []

        # Criterion 1: Decoupling (with false positive detection)
        if metrics.get("decoupling") is not None:
            if metrics["decoupling"] > self.servo_criteria["decoupling_threshold"]:
                # Check for false positive scenarios
                if activity and self._is_low_effort_social_ride(activity, metrics):
                    print(
                        f"     ℹ️  Découplage élevé ({metrics['decoupling']:.1f}%) ignoré "
                        "(sortie sociale/accompagnement avec arrêts détectée)"
                    )
                else:
                    reasons.append(
                        f"Découplage élevé ({metrics['decoupling']:.1f}% > {self.servo_criteria['decoupling_threshold']}%)"
                    )

        # Criterion 2: Sleep
        if metrics.get("sleep_hours") is not None:
            if metrics["sleep_hours"] < self.servo_criteria["sleep_threshold_hours"]:
                reasons.append(
                    f"Sommeil insuffisant ({metrics['sleep_hours']:.1f}h < {self.servo_criteria['sleep_threshold_hours']}h)"
                )

        # Criterion 3: Feel (subjective) - Intervals.icu 1-5 scale
        if metrics.get("feel") is not None:
            if metrics["feel"] >= self.servo_criteria["feel_threshold"]:
                feel_labels = {
                    1: "Excellent",
                    2: "Bien",
                    3: "Moyen",
                    4: "Passable",
                    5: "Mauvais",
                }
                feel_label = feel_labels.get(metrics["feel"], "Unknown")
                reasons.append(f"Ressenti négatif ({feel_label} - {metrics['feel']}/5)")

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

Contexte : Tu viens d'analyser la séance du jour (DÉJÀ RÉALISÉE).

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

Basé sur l'analyse de la séance du jour et les métriques réelles ci-dessus, **recommandes-tu des ajustements au planning FUTUR ?**

Critères de décision:
- RPE > 8/10 en zone endurance → Signal alarme
- Découplage > 7.5% → Fatigue cardiaque
- Sommeil < 7h → Vulnérabilité accrue
- TSB < -10 → Forme dégradée

**RÈGLES STRICTES:**
1. **NE MODIFIER QUE LES SÉANCES FUTURES** (listées dans "Planning Restant" ci-dessus)
2. **NE JAMAIS modifier une séance de type TEST (TST)** - Préserver comparabilité historique
3. **Semaine de tests:** NE RIEN MODIFIER sauf fatigue critique (TSB < -15, découplage > 15%, Feel < 1.5/4)
4. **Séance du jour:** DÉJÀ réalisée, impossible à modifier rétroactivement
5. Utilise UNIQUEMENT les valeurs de métriques fournies ci-dessus
6. Si une métrique est "Non disponible", ne PAS inventer de valeur
7. Justifier les recommandations avec les métriques RÉELLES

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

    def analyze_ctl_peaks(self) -> dict[str, Any] | None:
        """
        Analyze CTL/ATL/TSB metrics according to Peaks Coaching principles.

        Checks current CTL against recommended thresholds for Masters 50+ athletes
        and generates alerts if critical conditions detected.

        NEW: Integrates PID + Peaks hierarchical recommendation system.

        Returns:
            Dict with analysis results and alerts, or None if failed
            {
                "ctl_current": float,
                "atl_current": float,
                "tsb_current": float,
                "ftp_current": int,
                "ctl_minimum_for_ftp": float,
                "ctl_optimal_for_ftp": float,
                "alerts": list[str],
                "recommendations": list[str],
                "phase_recommendation": PhaseRecommendation,
                "pid_peaks_recommendation": IntegratedRecommendation (NEW)
            }
        """
        try:
            # Get athlete profile for FTP
            athlete = self.client.get_athlete()
            ftp_current = athlete.get("ftp", 220)  # Default 220W if missing

            # Get latest wellness for CTL/ATL/TSB
            from datetime import date, timedelta

            today = date.today()
            yesterday = today - timedelta(days=1)

            wellness_data = self.client.get_wellness(
                oldest=yesterday.isoformat(), newest=today.isoformat()
            )

            if not wellness_data:
                print("  ⚠️  Pas de données wellness récentes")
                return None

            # Get most recent wellness
            wellness = wellness_data[-1] if wellness_data else None
            if not wellness:
                return None

            ctl_current = wellness.get("ctl", 0)
            atl_current = wellness.get("atl", 0)
            tsb_current = wellness.get("tsb", 0)

            # Calculate thresholds according to Peaks Coaching
            # FTP 220W → CTL minimum 55-65
            # FTP 240W → CTL minimum 65-75
            # FTP 260W → CTL minimum 70-80
            ctl_minimum = (ftp_current / 220) * 55
            ctl_optimal = (ftp_current / 220) * 70

            alerts = []
            recommendations = []

            # Check 1: CTL too low for FTP target
            if ctl_current < ctl_minimum:
                deficit = ctl_minimum - ctl_current
                alerts.append(
                    f"CTL critique: {ctl_current:.1f} < {ctl_minimum:.0f} minimum pour FTP {ftp_current}W"
                )
                weeks_to_rebuild = deficit / 2.5  # +2.5 CTL/week sustainable
                recommendations.append(
                    f"Reconstruction base nécessaire: {weeks_to_rebuild:.0f} semaines minimum"
                )
                recommendations.append(
                    "Focus: Tempo (35% TSS) + Sweet-Spot (20% TSS), 350-400 TSS/semaine charge"
                )

            # Check 2: CTL drop >10 points (Masters 50+ critical)
            # TODO: Implement 30-day history check for CTL drops
            # For now, just check if CTL is significantly below optimal
            if ctl_current < (ctl_optimal * 0.85):
                alerts.append(
                    f"CTL sous-optimal: {ctl_current:.1f} < 85% de {ctl_optimal:.0f} optimal"
                )
                recommendations.append(
                    "Citation Hunter Allen: 'At 60 years young, CTL drops take months to rebuild'"
                )
                recommendations.append("Maintenir CTL à 90% du maximum en permanence (Masters 50+)")

            # Check 3: TSB critical (form)
            if tsb_current < -15:
                alerts.append(f"TSB critique: {tsb_current:+.1f} (fatigue excessive)")
                recommendations.append("Semaine récupération recommandée: 250-280 TSS")
            elif tsb_current > +15:
                alerts.append(f"TSB élevé: {tsb_current:+.1f} (déconditionnement possible)")
                recommendations.append("Augmenter volume progressivement: +2-3 CTL points/semaine")

            # Determine training phase (Peaks Coaching algorithm)
            # TODO: Get FTP target from athlete profile or config
            ftp_target = 230  # Conservative target (Sprint R10)
            phase_rec = determine_training_phase(
                ctl_current=ctl_current, ftp_current=ftp_current, ftp_target=ftp_target
            )

            # NEW: Initialize PID controller with calibrated gains (Sprint R10)
            print("\n🎛️  Initialisation PID Controller (Sprint R10 calibration)...")
            pid_controller = DiscretePIDController(
                kp=0.008,  # Proportional gain (Masters 50+ adjusted)
                ki=0.001,  # Integral gain (Masters 50+ adjusted)
                kd=0.12,  # Derivative gain (Masters 50+ adjusted)
                setpoint=ftp_target,
                dead_band=3.0,  # ±3W natural FTP variation
            )

            # Load PID state from previous runs (if available)
            state_file = Path("/tmp/sprint_r10_pid_initialization.json")
            if state_file.exists():
                try:
                    import json

                    with open(state_file) as f:
                        state_data = json.load(f)
                        pid_state = state_data.get("pid_state", {})

                        # Restore PID internal state
                        pid_controller.integral = pid_state.get("integral", 0.0)
                        pid_controller.prev_error = pid_state.get("prev_error", 0.0)
                        pid_controller.prev_ftp = pid_state.get("prev_ftp", 0)
                        pid_controller.cycle_count = pid_state.get("cycle_count", 0)

                        print(
                            f"  ✅ État PID restauré: integral={pid_controller.integral:.2f}, "
                            f"cycles={pid_controller.cycle_count}"
                        )
                except Exception as e:
                    print(f"  ⚠️  Erreur restauration état PID: {e}")

            # NEW: Compute integrated PID + Peaks recommendation
            print("🔄 Calcul recommandation intégrée PID + Peaks...")

            # Calculate recent adherence and quality metrics
            # TODO: Extract from recent week data (for now use defaults)
            adherence_rate = 0.85  # Target adherence
            avg_coupling = 0.065  # Target quality (découplage)
            tss_completion = 0.90  # Target completion

            try:
                pid_peaks_rec = compute_integrated_correction(
                    ctl_current=ctl_current,
                    ftp_current=ftp_current,
                    ftp_target=ftp_target,
                    athlete_age=54,  # Masters 50+
                    pid_controller=pid_controller,
                    adherence_rate=adherence_rate,
                    avg_cardiovascular_coupling=avg_coupling,
                    tss_completion_rate=tss_completion,
                )

                print(
                    f"  ✅ Recommandation: {pid_peaks_rec.tss_per_week} TSS/semaine "
                    f"(mode: {pid_peaks_rec.mode.value})"
                )

                if pid_peaks_rec.override_active:
                    print(f"  🚨 OVERRIDE ACTIF: {pid_peaks_rec.mode.value}")

            except Exception as e:
                print(f"  ⚠️  Erreur calcul PID+Peaks: {e}")
                import traceback

                traceback.print_exc()
                pid_peaks_rec = None

            return {
                "ctl_current": ctl_current,
                "atl_current": atl_current,
                "tsb_current": tsb_current,
                "ftp_current": ftp_current,
                "ctl_minimum_for_ftp": ctl_minimum,
                "ctl_optimal_for_ftp": ctl_optimal,
                "alerts": alerts,
                "recommendations": recommendations,
                "phase_recommendation": phase_rec,
                "pid_peaks_recommendation": pid_peaks_rec,  # NEW
            }

        except Exception as e:
            print(f"  ❌ Erreur analyse CTL Peaks: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _extract_session_id(self, activity_name: str) -> tuple[str, str] | None:
        """
        Extract week_id and session_id from activity name.

        Args:
            activity_name: Activity name (e.g., "S079-02-INT-SweetSpotModere-V001")

        Returns:
            Tuple of (week_id, session_id) or None if no match
            Example: ("S079", "S079-02")
        """
        import re

        # Pattern: S079-02-INT-SweetSpotModere-V001
        pattern = r"^(S\d{3})-(\d{2})"
        match = re.match(pattern, activity_name)

        if match:
            week_id = match.group(1)
            session_num = match.group(2)
            session_id = f"{week_id}-{session_num}"
            return week_id, session_id

        return None

    def update_completed_sessions(self, activities: list[dict]):
        """
        Automatically update session status to 'completed' in local planning JSON.

        For each completed activity with a paired_event_id:
        1. Extract session_id from activity name
        2. Load corresponding week planning JSON
        3. Update session status to 'completed'
        4. Save updated JSON

        Args:
            activities: List of completed activities from Intervals.icu
        """
        if not activities:
            return

        print("\n🔄 Mise à jour automatique des statuts de sessions...")

        updated_weeks = {}  # Track which weeks need saving

        for activity in activities:
            # Only process activities paired with planned events
            if not activity.get("paired_event_id"):
                continue

            activity_name = activity.get("name", "")

            # Extract session info from name
            session_info = self._extract_session_id(activity_name)
            if not session_info:
                print(f"  ⚠️  Impossible d'extraire session_id de: {activity_name}")
                continue

            week_id, session_id = session_info

            # Load planning JSON if not already loaded
            if week_id not in updated_weeks:
                planning_file = Path(
                    f"/Users/stephanejouve/training-logs/data/week_planning/week_planning_{week_id}.json"
                )

                if not planning_file.exists():
                    print(f"  ⚠️  Planning introuvable: {planning_file}")
                    continue

                try:
                    # ✅ Chargement sécurisé avec Pydantic
                    plan = WeeklyPlan.from_json(planning_file)
                    updated_weeks[week_id] = {
                        "file": planning_file,
                        "plan": plan,
                        "modified": False,
                    }
                except (ValidationError, json.JSONDecodeError) as e:
                    print(f"  ⚠️  Erreur chargement planning {week_id}: {e}")
                    continue

            # Find and update session
            plan = updated_weeks[week_id]["plan"]
            session_found = False

            for session in plan.planned_sessions:
                if session.session_id == session_id:
                    # Only update if not already completed
                    if session.status != "completed":
                        session.status = "completed"
                        updated_weeks[week_id]["modified"] = True
                        print(f"  ✅ {session_id} marqué comme 'completed'")
                        session_found = True
                    else:
                        print(f"  ℹ️  {session_id} déjà marqué 'completed'")
                        session_found = True
                    break

            if not session_found:
                print(f"  ⚠️  Session {session_id} introuvable dans {week_id}")

        # Save modified planning files
        for week_id, week_data in updated_weeks.items():
            if week_data["modified"]:
                plan = week_data["plan"]
                plan.last_updated = datetime.now(UTC)

                # ✅ Sauvegarde atomique avec Pydantic
                plan.to_json(week_data["file"])

                print(f"  💾 Planning {week_id} sauvegardé")

        print("  ✅ Mise à jour automatique terminée")

    def generate_report(
        self,
        check_date: date,
        new_activities: list[dict],
        planning_changes: dict,
        analyses: dict[int, str] | None = None,
        servo_result: dict | None = None,
        compensation_result: dict | None = None,
        ctl_analysis: dict | None = None,
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
            ctl_analysis: CTL analysis according to Peaks Coaching principles

        Returns:
            Path to generated report file
        """
        report_file = self.reports_dir / f"daily_report_{check_date.isoformat()}.md"

        with open(report_file, "w", encoding="utf-8") as f:
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

            # Section 5: CTL Analysis (Peaks Coaching)
            if ctl_analysis:
                f.write("---\n\n")
                f.write("## 📈 Analyse CTL (Peaks Coaching)\n\n")

                ctl = ctl_analysis["ctl_current"]
                atl = ctl_analysis["atl_current"]
                tsb = ctl_analysis["tsb_current"]
                ftp = ctl_analysis["ftp_current"]
                ctl_min = ctl_analysis["ctl_minimum_for_ftp"]
                ctl_opt = ctl_analysis["ctl_optimal_for_ftp"]

                f.write("**Métriques Actuelles:**\n")
                f.write(f"- CTL (Fitness): {ctl:.1f}\n")
                f.write(f"- ATL (Fatigue): {atl:.1f}\n")
                f.write(f"- TSB (Form): {tsb:+.1f}\n")
                f.write(f"- FTP: {ftp}W\n\n")

                f.write(f"**Seuils Peaks Coaching (FTP {ftp}W):**\n")
                f.write(f"- CTL minimum: {ctl_min:.0f}\n")
                f.write(f"- CTL optimal: {ctl_opt:.0f}\n\n")

                alerts = ctl_analysis.get("alerts", [])
                recommendations = ctl_analysis.get("recommendations", [])

                if alerts:
                    f.write(f"**⚠️  {len(alerts)} Alerte(s):**\n\n")
                    for alert in alerts:
                        f.write(f"- {alert}\n")
                    f.write("\n")

                if recommendations:
                    f.write("**💡 Recommandations:**\n\n")
                    for rec in recommendations:
                        f.write(f"- {rec}\n")
                    f.write("\n")

                if not alerts:
                    f.write(
                        "✅ **CTL dans les normes** pour FTP actuel et principes Masters 50+\n\n"
                    )

                # Phase recommendation
                phase_rec = ctl_analysis.get("phase_recommendation")
                if phase_rec:
                    f.write("---\n\n")
                    f.write(format_phase_recommendation(phase_rec))

                # PID + Peaks integrated recommendation (NEW)
                pid_peaks_rec = ctl_analysis.get("pid_peaks_recommendation")
                if pid_peaks_rec:
                    f.write("---\n\n")
                    f.write("## 🎛️ Recommandation Intégrée PID + Peaks (Sprint R10)\n\n")
                    f.write(
                        "*Architecture hiérarchique multi-niveaux: Peaks Coaching (stratégique) → "
                        "PID Discret (tactique) → Daily execution (opérationnel)*\n\n"
                    )
                    formatted_rec = format_integrated_recommendation(pid_peaks_rec)
                    f.write(formatted_rec)

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

        # 1b. Auto-update session statuses in local planning JSON
        if new_activities:
            self.update_completed_sessions(new_activities)

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
            ctl_analysis = self.analyze_ctl_peaks()

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
        week_id=week_id,
        start_date=start_date,
        send_email=args.send_email,
    )


if __name__ == "__main__":
    main()
