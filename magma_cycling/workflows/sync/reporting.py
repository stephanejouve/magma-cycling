"""ReportingMixin — report generation, backup, and email sending."""

import re
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

import markdown2
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from magma_cycling.config import get_email_config
from magma_cycling.planning.peaks_phases import format_phase_recommendation
from magma_cycling.workflows.pid_peaks_integration import format_integrated_recommendation
from magma_cycling.workflows.proactive_compensation import format_compensation_section


def _normalize_analysis_for_report(analysis: str) -> str:
    """Strip duplicate header and adjust heading levels for report insertion.

    Analysis from workouts-history.md starts with::

        ### SessionName
        ID : xxx
        Date : dd/mm/yyyy

        #### Section...

    The session name/ID/date are already shown in the activity section,
    so we strip them and downgrade ``####`` → ``#####`` to sit properly
    under the ``#### 🤖 Analyse AI`` heading.
    """
    # Strip leading ### header + ID + Date lines
    cleaned = re.sub(
        r"^###\s+.+\nID\s*:.+\nDate\s*:.+\n*",
        "",
        analysis.strip(),
    )
    # Downgrade #### to ##### (exactly 4 # followed by space)
    cleaned = re.sub(r"^#### ", "##### ", cleaned, flags=re.MULTILINE)
    return cleaned.strip()


class ReportingMixin:
    """Mixin for report generation, backup, and email sending."""

    def _backup_existing_report(self, report_file: Path) -> Path | None:
        """
        Backup existing report before overwriting.

        Creates timestamped backup in backups/ subdirectory.
        Automatically cleans backups older than 30 days.

        Args:
            report_file: Path to report file

        Returns:
            Path to backup file if created, None if no existing report
        """
        if not report_file.exists():
            return None

        # Create backups directory
        backups_dir = report_file.parent / "backups"
        backups_dir.mkdir(exist_ok=True)

        # Generate timestamped backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{report_file.stem}.{timestamp}{report_file.suffix}"
        backup_file = backups_dir / backup_name

        # Copy existing report to backup
        shutil.copy2(report_file, backup_file)

        print(f"  💾 Backup créé: {backup_file.name}")

        # Cleanup old backups (>30 days)
        cutoff_date = datetime.now() - timedelta(days=30)
        for old_backup in backups_dir.glob("daily_report_*.md"):
            if old_backup.stat().st_mtime < cutoff_date.timestamp():
                old_backup.unlink()
                print(f"  🗑️  Backup nettoyé: {old_backup.name}")

        return backup_file

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

        # Backup existing report before overwriting
        self._backup_existing_report(report_file)

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
                        f.write(_normalize_analysis_for_report(analyses[activity["id"]]))
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
                ftp_target = ctl_analysis["ftp_target"]
                ctl_min = ctl_analysis["ctl_minimum_for_ftp"]
                ctl_opt = ctl_analysis["ctl_optimal_for_ftp"]

                f.write("**Métriques Actuelles:**\n")
                f.write(f"- CTL (Fitness): {ctl:.1f}\n")
                f.write(f"- ATL (Fatigue): {atl:.1f}\n")
                f.write(f"- TSB (Form): {tsb:+.1f}\n")
                f.write(f"- FTP actuel: {ftp}W\n")
                f.write(f"- FTP cible: {ftp_target}W\n\n")

                f.write("**Seuils Peaks Coaching:**\n")
                f.write(f"- CTL minimum (FTP {ftp}W): {ctl_min:.0f}\n")
                f.write(f"- CTL optimal (FTP {ftp_target}W): {ctl_opt:.0f}\n\n")

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
                "[magma-cycling](https://github.com/stephanejouve/magma-cycling)*\n"
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
