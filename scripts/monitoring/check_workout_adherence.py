#!/usr/bin/env python3
"""Check workout adherence - detect skipped/missed workouts.

This script checks if planned workouts were completed by comparing
Intervals.icu planned events with actual activities.

Usage:
    # Check today's adherence
    python scripts/monitoring/check_workout_adherence.py

    # Check specific date
    python scripts/monitoring/check_workout_adherence.py --date 2026-01-05

    # Dry-run (no notifications)
    python scripts/monitoring/check_workout_adherence.py --dry-run

Sprint R6 Integration:
    - Detects skipped workouts for baseline data integrity
    - Logs adherence for PID calibration analysis
    - Sends notifications for immediate corrective action
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

from magma_cycling.api.intervals_client import IntervalsClient
from magma_cycling.config import get_intervals_config


class WorkoutAdherenceChecker:
    """Check if planned workouts were completed."""

    def __init__(self, dry_run: bool = False):
        """Initialize adherence checker.

        Args:
            dry_run: If True, don't send notifications (logging only)
        """
        self.config = get_intervals_config()
        self.client = IntervalsClient(
            athlete_id=self.config.athlete_id, api_key=self.config.api_key
        )
        self.dry_run = dry_run
        self.log_dir = Path.home() / "data" / "monitoring"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def check_date(self, date: datetime) -> dict:
        """Check adherence for a specific date.

        Args:
            date: Date to check

        Returns:
            Dict with adherence status:
            {
                "date": "2026-01-05",
                "planned_workouts": 1,
                "completed_activities": 1,
                "skipped_workouts": [],
                "adherence_rate": 1.0,
                "status": "COMPLETE"  # or "PARTIAL" or "MISSED"
            }
        """
        date_str = date.strftime("%Y-%m-%d")
        print(f"\n{'=' * 60}")
        print(f"🔍 Checking workout adherence for {date_str}")
        print(f"{'=' * 60}\n")

        # Fetch planned workouts (events)
        events = self.client.get_events(oldest=date_str, newest=date_str)

        # Filter WORKOUT events only, excluding rest/recovery days
        # Exclude:
        # - Events starting with "[" (cancelled/notes)
        # - Events containing "REC" or "Repos" (recovery/rest days)
        planned_workouts = [
            e
            for e in events
            if e.get("category") == "WORKOUT"
            and not e.get("name", "").startswith("[")
            and "REC" not in e.get("name", "").upper()
            and "REPOS" not in e.get("name", "").upper()
            and "RECOVERY" not in e.get("name", "").upper()
            and "REST" not in e.get("name", "").upper()
        ]

        # Fetch completed activities
        activities = self.client.get_activities(oldest=date_str, newest=date_str)

        # Match planned workouts with activities
        skipped = []
        for workout in planned_workouts:
            workout_name = workout.get("name", "")
            workout_id = workout.get("id")

            # Check if activity exists for this workout
            matched = False
            for activity in activities:
                # Match by name similarity or workout_id reference
                if (
                    workout_name.lower() in activity.get("name", "").lower()
                    or activity.get("workout_id") == workout_id
                ):
                    matched = True
                    break

            if not matched:
                skipped.append(
                    {
                        "id": workout_id,
                        "name": workout_name,
                        "start_time": workout.get("start_date_local", ""),
                    }
                )

        # Calculate adherence
        planned_count = len(planned_workouts)
        completed_count = planned_count - len(skipped)
        adherence_rate = completed_count / planned_count if planned_count > 0 else 1.0

        # Determine status
        if adherence_rate == 1.0:
            status = "COMPLETE"
        elif adherence_rate > 0:
            status = "PARTIAL"
        else:
            status = "MISSED"

        result = {
            "date": date_str,
            "planned_workouts": planned_count,
            "completed_activities": completed_count,
            "skipped_workouts": skipped,
            "adherence_rate": adherence_rate,
            "status": status,
            "timestamp": datetime.now().isoformat(),
        }

        # Display results
        self._display_results(result)

        # Log results
        self._log_results(result)

        # Send notification if needed
        if skipped and not self.dry_run:
            self._notify_skipped(result)

        return result

    def _display_results(self, result: dict) -> None:
        """Display adherence check results.

        Args:
            result: Adherence check result dict
        """
        status_emoji = {"COMPLETE": "✅", "PARTIAL": "⚠️", "MISSED": "🔴"}

        print("📊 Adherence Summary:")
        print(f"   Status: {status_emoji.get(result['status'], '❓')} {result['status']}")
        print(f"   Planned: {result['planned_workouts']} workouts")
        print(f"   Completed: {result['completed_activities']} activities")
        print(f"   Adherence Rate: {result['adherence_rate'] * 100:.0f}%")

        if result["skipped_workouts"]:
            print(f"\n🔴 Skipped Workouts ({len(result['skipped_workouts'])}):")
            for workout in result["skipped_workouts"]:
                print(f"   - {workout['name']} (at {workout['start_time']})")
        else:
            print("\n✅ All planned workouts completed!")

    def _log_results(self, result: dict) -> None:
        """Log adherence results to file.

        Args:
            result: Adherence check result dict
        """
        log_file = self.log_dir / "workout_adherence.jsonl"

        with open(log_file, "a") as f:
            f.write(json.dumps(result) + "\n")

        print(f"\n📝 Results logged to: {log_file}")

    def _notify_skipped(self, result: dict) -> None:
        """Send notification about skipped workouts.

        Args:
            result: Adherence check result dict
        """
        if not result["skipped_workouts"]:
            return

        print(f"\n{'=' * 60}")
        print("🚨 WORKOUT ADHERENCE ALERT")
        print(f"{'=' * 60}")
        print(f"\n⚠️  {len(result['skipped_workouts'])} workout(s) were skipped on {result['date']}")
        print("\nSkipped workouts:")
        for workout in result["skipped_workouts"]:
            print(f"  • {workout['name']}")

        print("\n💡 Recommended Actions:")
        print("   1. Review reason for skip (fatigue, schedule, etc.)")
        print("   2. Update session status if intentional:")
        print("      poetry run update-session --status skipped --reason 'Your reason'")
        print("   3. Consider rescheduling if needed")
        print("   4. Update baseline data for PID calibration")
        print(f"\n{'=' * 60}\n")

    def check_week(self, week_start: datetime) -> dict:
        """Check adherence for entire week.

        Args:
            week_start: Monday of the week to check

        Returns:
            Dict with weekly adherence summary
        """
        print(f"\n{'=' * 60}")
        print("📅 Weekly Adherence Check")
        print(f"{'=' * 60}\n")

        daily_results = []
        for i in range(7):
            date = week_start + timedelta(days=i)
            if date <= datetime.now():
                result = self.check_date(date)
                daily_results.append(result)

        # Aggregate weekly stats
        total_planned = sum(r["planned_workouts"] for r in daily_results)
        total_completed = sum(r["completed_activities"] for r in daily_results)
        total_skipped = sum(len(r["skipped_workouts"]) for r in daily_results)

        weekly_adherence = total_completed / total_planned if total_planned > 0 else 1.0

        weekly_result = {
            "week_start": week_start.strftime("%Y-%m-%d"),
            "daily_results": daily_results,
            "total_planned": total_planned,
            "total_completed": total_completed,
            "total_skipped": total_skipped,
            "weekly_adherence": weekly_adherence,
            "timestamp": datetime.now().isoformat(),
        }

        print(f"\n{'=' * 60}")
        print(f"📊 Weekly Summary ({week_start.strftime('%Y-W%U')})")
        print(f"{'=' * 60}")
        print(f"   Total Planned: {total_planned} workouts")
        print(f"   Total Completed: {total_completed} activities")
        print(f"   Total Skipped: {total_skipped} workouts")
        print(f"   Weekly Adherence: {weekly_adherence * 100:.0f}%")
        print(f"{'=' * 60}\n")

        return weekly_result

    def check_weekly_adherence_and_alert(self) -> dict:
        """
        Check current week's adherence and send alerts if below thresholds.

        Thresholds (Sprint R10):
        - ≥90%: INFO (excellent)
        - 85-90%: INFO (good, target met)
        - 70-85%: WARNING (at-risk, email alert)
        - <70%: CRITICAL (intervention required, email + PID gains reduction)

        Returns:
            Dict with adherence summary and alert status
        """
        print(f"\n{'=' * 60}")
        print("📊 Weekly Adherence Alert Check")
        print(f"{'=' * 60}\n")

        # Get current week Monday
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())

        # Check week adherence
        weekly_result = self.check_week(week_start)
        adherence_rate = weekly_result["weekly_adherence"]
        adherence_pct = adherence_rate * 100

        # Determine alert level
        if adherence_rate >= 0.90:
            alert_level = "INFO"
            alert_emoji = "✅"
            alert_message = f"Adherence excellente: {adherence_pct:.0f}%"
        elif adherence_rate >= 0.85:
            alert_level = "INFO"
            alert_emoji = "✅"
            alert_message = f"Adherence cible atteinte: {adherence_pct:.0f}%"
        elif adherence_rate >= 0.70:
            alert_level = "WARNING"
            alert_emoji = "⚠️"
            alert_message = f"Adherence sous-optimale: {adherence_pct:.0f}% < 85%"
        else:
            alert_level = "CRITICAL"
            alert_emoji = "🚨"
            alert_message = f"Adherence critique: {adherence_pct:.0f}% < 70%"

        print(f"{alert_emoji} Alert Level: {alert_level}")
        print(f"   {alert_message}")
        print()

        # Send email alert for WARNING and CRITICAL
        if alert_level in ["WARNING", "CRITICAL"] and not self.dry_run:
            self._send_adherence_alert(
                alert_level=alert_level,
                adherence_pct=adherence_pct,
                weekly_result=weekly_result,
            )

        return {
            "alert_level": alert_level,
            "adherence_rate": adherence_rate,
            "adherence_pct": adherence_pct,
            "alert_message": alert_message,
            "weekly_result": weekly_result,
        }

    def _send_adherence_alert(
        self, alert_level: str, adherence_pct: float, weekly_result: dict
    ) -> None:
        """
        Send adherence alert email via Brevo.

        Args:
            alert_level: "WARNING" or "CRITICAL"
            adherence_pct: Adherence percentage
            weekly_result: Weekly adherence result dict
        """
        try:
            import sib_api_v3_sdk
            from sib_api_v3_sdk.rest import ApiException

            from magma_cycling.config import get_email_config

            email_config = get_email_config()

            if not email_config.is_configured():
                print("⚠️  Email non configuré - alerte non envoyée")
                return

            print(f"\n📧 Envoi alerte {alert_level} via Brevo...")

            # Configure Brevo API
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key["api-key"] = email_config.api_key

            # Email content
            if alert_level == "CRITICAL":
                subject = "🚨 ALERTE CRITIQUE: Adherence <70%"
                emoji = "🚨"
                color = "#dc3545"  # Red
                actions = [
                    "🔧 Réduction automatique gains PID de -30%",
                    "📋 Révision planning semaine en cours",
                    "💬 Identifier obstacles à l'adherence",
                    "🎯 Ajuster objectifs si nécessaire",
                ]
            else:  # WARNING
                subject = "⚠️  Alerte: Adherence <85%"
                emoji = "⚠️"
                color = "#ffc107"  # Yellow
                actions = [
                    "📊 Surveiller progression cette semaine",
                    "🔍 Identifier séances à risque",
                    "💡 Considérer ajustements planning",
                ]

            total_planned = weekly_result["total_planned"]
            total_completed = weekly_result["total_completed"]
            total_skipped = weekly_result["total_skipped"]

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .alert-box {{
                        background-color: {color};
                        color: white;
                        padding: 20px;
                        border-radius: 8px;
                        margin: 20px 0;
                        text-align: center;
                    }}
                    .metric {{
                        background-color: #f8f9fa;
                        padding: 15px;
                        border-radius: 6px;
                        margin: 10px 0;
                    }}
                    .action-list {{
                        background-color: #e9ecef;
                        padding: 15px;
                        border-radius: 6px;
                        margin: 15px 0;
                    }}
                    ul {{
                        line-height: 2;
                    }}
                </style>
            </head>
            <body>
                <div class="alert-box">
                    <h1>{emoji} ALERTE ADHERENCE</h1>
                    <h2>{adherence_pct:.0f}%</h2>
                    <p>Semaine {weekly_result['week_start']}</p>
                </div>

                <div class="metric">
                    <h3>📊 Métriques Hebdomadaires</h3>
                    <p><strong>Séances planifiées:</strong> {total_planned}</p>
                    <p><strong>Séances complétées:</strong> {total_completed}</p>
                    <p><strong>Séances sautées:</strong> {total_skipped}</p>
                    <p><strong>Taux adherence:</strong> {adherence_pct:.0f}%</p>
                </div>

                <div class="action-list">
                    <h3>💡 Actions Recommandées</h3>
                    <ul>
                        {"".join(f"<li>{action}</li>" for action in actions)}
                    </ul>
                </div>

                <p style="color: #6c757d; font-size: 0.9em; margin-top: 30px;">
                    Sprint R10 - Architecture PID+Peaks<br>
                    Seuil cible: ≥85% pour optimisation PID active
                </p>
            </body>
            </html>
            """

            # Send email
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
                sib_api_v3_sdk.ApiClient(configuration)
            )

            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": email_config.email_to}],
                sender={
                    "name": email_config.email_from_name,
                    "email": email_config.email_from,
                },
                subject=subject,
                html_content=html_content,
            )

            api_response = api_instance.send_transac_email(send_smtp_email)
            print(f"  ✅ Email alerte envoyé (ID: {api_response.message_id})")

        except ApiException as e:
            print(f"  ❌ Erreur Brevo API: {e}")
        except Exception as e:
            print(f"  ❌ Erreur envoi alerte: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check workout adherence (detect skipped workouts)"
    )
    parser.add_argument("--date", type=str, help="Date to check (YYYY-MM-DD). Default: today")
    parser.add_argument(
        "--week", action="store_true", help="Check entire week instead of single day"
    )
    parser.add_argument(
        "--weekly-alert",
        action="store_true",
        help="Check weekly adherence and send alerts if <85%% (Sprint R10)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Dry-run mode (no notifications)")

    args = parser.parse_args()

    # Parse date
    if args.date:
        check_date = datetime.strptime(args.date, "%Y-%m-%d")
    else:
        check_date = datetime.now()

    # Initialize checker
    checker = WorkoutAdherenceChecker(dry_run=args.dry_run)

    # Check adherence
    if args.weekly_alert:
        # Sprint R10: Weekly adherence with automatic alerts
        checker.check_weekly_adherence_and_alert()
    elif args.week:
        # Get Monday of the week
        week_start = check_date - timedelta(days=check_date.weekday())
        checker.check_week(week_start)
    else:
        checker.check_date(check_date)


if __name__ == "__main__":
    main()
