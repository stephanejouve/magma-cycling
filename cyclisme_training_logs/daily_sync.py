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
)
from cyclisme_training_logs.config.athlete_profile import AthleteProfile
from cyclisme_training_logs.planning.calendar import TrainingCalendar, WorkoutType
from cyclisme_training_logs.planning.intervals_sync import IntervalsSync


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

        self.data[date_key]["activities"].append(
            {
                "id": activity["id"],
                "paired_activity_id": activity.get("paired_activity_id"),
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

    def __init__(self, tracking_file: Path, reports_dir: Path, enable_ai_analysis: bool = False):
        """
        Initialize daily sync.

        Args:
            tracking_file: Path to activity tracking JSON
            reports_dir: Directory for daily reports
            enable_ai_analysis: Enable automatic AI analysis of activities
        """
        self.client = create_intervals_client()
        self.tracker = ActivityTracker(tracking_file)
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.enable_ai_analysis = enable_ai_analysis

        # Initialize AI analyzer if enabled
        self.ai_analyzer = None
        if enable_ai_analysis:
            ai_config = get_ai_config()
            available = ai_config.get_available_providers()
            if available:
                provider = available[0]
                provider_config = ai_config.get_provider_config(provider)
                self.ai_analyzer = AIProviderFactory.create(provider, provider_config)
                print(f"🤖 AI Analysis activé (provider: {provider})")
            else:
                print("⚠️  Aucun provider AI configuré - analysis désactivée")
                self.enable_ai_analysis = False

    def check_activities(self, check_date: date) -> list[dict]:
        """
        Check for new completed activities on given date.

        Args:
            check_date: Date to check

        Returns:
            List of new completed activities
        """
        print(f"\n🔍 Vérification activités du {check_date.strftime('%d/%m/%Y')}...")

        # Get all events for the date
        events = self.client.get_events(
            oldest=check_date.isoformat(), newest=check_date.isoformat()
        )

        # Filter completed activities (have paired_activity_id)
        completed = [
            e for e in events if e.get("paired_activity_id") and e.get("category") == "WORKOUT"
        ]

        # Filter new activities (not yet analyzed)
        new_activities = [
            activity
            for activity in completed
            if not self.tracker.is_analyzed(activity["id"], check_date)
        ]

        print(f"  ✅ {len(completed)} activité(s) complétée(s)")
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

    def analyze_activity(self, activity: dict) -> str | None:
        """
        Generate AI analysis for an activity.

        Args:
            activity: Activity dict with id and other metadata

        Returns:
            Analysis text or None if failed
        """
        if not self.enable_ai_analysis or not self.ai_analyzer:
            return None

        try:
            # Use Intervals.icu ID (paired_activity_id) instead of Strava ID
            intervals_id = activity.get("paired_activity_id")
            if not intervals_id:
                print(f"  ⚠️  Pas d'ID Intervals.icu pour {activity.get('name', activity['id'])}")
                return None

            print(f"  🤖 Génération analyse AI pour {activity.get('name', intervals_id)}...")

            # Get full activity data from Intervals.icu
            full_activity = self.client.get_activity(intervals_id)

            # Create simplified prompt for daily analysis
            prompt = self._create_simple_prompt(full_activity)

            # Get AI analysis
            analysis = self.ai_analyzer.analyze_session(prompt)

            if analysis:
                print(f"     ✅ Analyse générée ({len(analysis)} caractères)")
                return analysis
            else:
                print("     ⚠️  Échec génération analyse")
                return None

        except Exception as e:
            print(f"     ❌ Erreur analyse AI: {e}")
            return None

    def _create_simple_prompt(self, activity: dict) -> str:
        """
        Create a simplified analysis prompt from activity data.

        Args:
            activity: Full activity data from Intervals.icu

        Returns:
            Prompt text for AI analysis
        """
        # Extract key metrics
        name = activity.get("name", "Activité")
        workout_type = activity.get("type", "N/A")
        duration_min = activity.get("moving_time", 0) // 60
        tss = activity.get("icu_training_load", "N/A")
        avg_power = activity.get("average_watts", "N/A")
        np = activity.get("np", "N/A")
        avg_hr = activity.get("average_hr", "N/A")
        max_hr = activity.get("max_hr", "N/A")
        avg_cadence = activity.get("average_cadence", "N/A")

        prompt = f"""Analyse cette séance de cyclisme et fournis un résumé concis.

## Données de la séance

**Nom**: {name}
**Type**: {workout_type}
**Durée**: {duration_min} min
**TSS**: {tss}
**Puissance moyenne**: {avg_power} W
**NP**: {np} W
**FC moyenne**: {avg_hr} bpm
**FC max**: {max_hr} bpm
**Cadence moyenne**: {avg_cadence} rpm

## Instructions

Fournis une analyse concise (3-4 paragraphes) qui inclut:

1. **Observation générale**: Type de séance, durée, intensité
2. **Points clés**: Métriques importantes et observations
3. **Qualité d'exécution**: Comment la séance s'est déroulée
4. **Recommandations**: Points d'attention pour les prochaines séances

Format: Texte markdown simple, pas de titres de section, style conversationnel et direct.
"""
        return prompt

    def generate_report(
        self,
        check_date: date,
        new_activities: list[dict],
        planning_changes: dict,
        analyses: dict[int, str] | None = None,
    ) -> Path:
        """
        Generate markdown daily report.

        Args:
            check_date: Date of check
            new_activities: List of new completed activities
            planning_changes: Dict with planning changes

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

        # 3. Check planning changes (if week specified)
        planning_changes = {"status": None, "diff": None}
        if week_id and start_date:
            end_date = start_date + timedelta(days=6)
            planning_changes = self.check_planning_changes(week_id, start_date, end_date)

        # 4. Generate report
        report_file = self.generate_report(check_date, new_activities, planning_changes, analyses)

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

    args = parser.parse_args()

    # Parse check date
    if args.date:
        check_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        check_date = date.today()

    # Parse week start date if provided
    start_date = None
    if args.start_date:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()

    # Validate week-id requires start-date
    if args.week_id and not start_date:
        print("❌ Erreur: --week-id nécessite --start-date")
        sys.exit(1)

    # Setup paths
    tracking_file = Path("/Users/stephanejouve/training-logs/data/activities_tracking.json")
    reports_dir = Path("/Users/stephanejouve/training-logs/daily-reports")

    # Run sync
    sync = DailySync(
        tracking_file=tracking_file,
        reports_dir=reports_dir,
        enable_ai_analysis=args.ai_analysis,
    )
    sync.run(
        check_date=check_date,
        week_id=args.week_id,
        start_date=start_date,
        send_email=args.send_email,
    )


if __name__ == "__main__":
    main()
