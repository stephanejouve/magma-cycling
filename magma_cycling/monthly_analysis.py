#!/usr/bin/env python3
"""
Monthly Training Analysis - Macro view of training cycle.

Aggregates weekly planning data to provide monthly insights on:
- Training load (TSS) distribution
- Session type balance (END/INT/REC/TEC)
- Plan adherence (completed vs skipped)
- Weekly progression patterns
- AI-powered periodization assessment

Examples:
    Analyze December 2025::

        poetry run monthly-analysis --month 2025-12 --provider mistral_api

    Generate report without AI analysis::

        poetry run monthly-analysis --month 2025-12 --no-ai

    Output to file::

        poetry run monthly-analysis --month 2025-12 --output reports/dec-2025.md

Author: Claude Code
Created: 2026-01-01.
"""
import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from magma_cycling.ai_providers.factory import AIProviderFactory
from magma_cycling.config import get_ai_config, get_data_config
from magma_cycling.prompts import build_prompt

logger = logging.getLogger(__name__)


class MonthlyAnalyzer:
    """Analyze training data at monthly granularity."""

    def __init__(self, month: str, provider: str = "mistral_api", no_ai: bool = False):
        """
        Initialize monthly analyzer.

        Args:
            month: Month in YYYY-MM format (e.g., "2025-12")
            provider: AI provider for analysis
            no_ai: Skip AI analysis, only generate statistics
        """
        self.month = month

        self.provider = provider
        self.no_ai = no_ai

        # Parse month
        try:
            self.month_date = datetime.strptime(month, "%Y-%m")
        except ValueError as e:
            raise ValueError(f"Invalid month format: {month}. Use YYYY-MM (e.g., 2025-12)") from e

        # Get data repo config
        self.data_config = get_data_config()
        self.planning_dir = self.data_config.data_repo_path / "data" / "week_planning"

        # Initialize AI if needed
        self.ai_analyzer = None
        if not no_ai:
            ai_config = get_ai_config()
            provider_config = ai_config.get_provider_config(provider)
            self.ai_analyzer = AIProviderFactory.create(provider, provider_config)

    def find_weeks_in_month(self) -> list[Path]:
        """
        Find all weekly planning files that overlap with the target month.

        Returns:
            List of paths to weekly planning JSON files.
        """
        if not self.planning_dir.exists():
            return []

        # Get month boundaries
        month_start = self.month_date
        # Last day of month
        if month_start.month == 12:
            month_end = datetime(month_start.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = datetime(month_start.year, month_start.month + 1, 1) - timedelta(days=1)

        matching_weeks = []

        for planning_file in sorted(self.planning_dir.glob("week_planning_S*.json")):
            try:
                with open(planning_file, encoding="utf-8") as f:
                    planning = json.load(f)

                week_start = datetime.strptime(planning["start_date"], "%Y-%m-%d")
                week_end = datetime.strptime(planning["end_date"], "%Y-%m-%d")

                # Check if week overlaps with month
                if week_start <= month_end and week_end >= month_start.replace(day=1):
                    matching_weeks.append(planning_file)

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"⚠️  Skip {planning_file.name}: {e}")
                continue

        return matching_weeks

    def load_weekly_data(self, week_files: list[Path]) -> list[dict]:
        """Load and parse weekly planning data."""
        weekly_data = []

        for week_file in week_files:
            try:
                with open(week_file, encoding="utf-8") as f:
                    data = json.load(f)
                    weekly_data.append(data)
            except Exception as e:
                print(f"❌ Error loading {week_file.name}: {e}")

        return weekly_data

    def aggregate_statistics(self, weekly_data: list[dict]) -> dict:
        """
        Aggregate monthly statistics from weekly data.

        Returns:
            Dictionary with monthly metrics.
        """
        stats: dict[str, Any] = {
            "total_weeks": len(weekly_data),
            "total_sessions": 0,
            "completed": 0,
            "skipped": 0,
            "cancelled": 0,
            "modified": 0,
            "rest_days": 0,
            "tss_planned": 0,
            "tss_target_total": 0,
            "sessions_by_type": defaultdict(int),
            "sessions_by_status": defaultdict(int),
            "tss_by_week": [],
            "weekly_details": [],
        }

        for week in sorted(weekly_data, key=lambda w: w["start_date"]):
            week_stats = {
                "week_id": week["week_id"],
                "start_date": week["start_date"],
                "end_date": week["end_date"],
                "tss_target": week.get("tss_target", 0),
                "tss_actual": 0,
                "sessions": len(week.get("planned_sessions", [])),
            }

            stats["tss_target_total"] += week.get("tss_target", 0)

            for session in week.get("planned_sessions", []):
                stats["total_sessions"] += 1
                status = session.get("status", "unknown")
                session_type = session.get("type", "unknown")
                tss = session.get("tss_planned", 0)

                # Count by status
                stats["sessions_by_status"][status] += 1

                if status == "completed":
                    stats["completed"] += 1
                    stats["tss_planned"] += tss
                    week_stats["tss_actual"] += tss
                elif status == "skipped":
                    stats["skipped"] += 1
                elif status == "cancelled":
                    stats["cancelled"] += 1
                elif status == "modified":
                    stats["modified"] += 1
                    stats["tss_planned"] += tss
                    week_stats["tss_actual"] += tss
                elif status == "rest_day":
                    stats["rest_days"] += 1

                # Count by type (exclude rest days)
                if status != "rest_day":
                    stats["sessions_by_type"][session_type] += 1

            stats["tss_by_week"].append(week_stats)
            stats["weekly_details"].append(week_stats)

        # Calculate adherence rate
        total_planned = (
            stats["completed"] + stats["skipped"] + stats["cancelled"] + stats["modified"]
        )
        if total_planned > 0:
            stats["adherence_rate"] = (stats["completed"] + stats["modified"]) / total_planned * 100
        else:
            stats["adherence_rate"] = 0

        # Calculate TSS achievement rate
        if stats["tss_target_total"] > 0:
            stats["tss_achievement_rate"] = stats["tss_planned"] / stats["tss_target_total"] * 100
        else:
            stats["tss_achievement_rate"] = 0

        return stats

    def generate_report(self, stats: dict, ai_analysis: str | None = None) -> str:
        """Generate markdown report."""
        month_name = self.month_date.strftime("%B %Y")

        report = f"""# 📊 Analyse Mensuelle - {month_name}.

## Résumé Exécutif

**Période :** {stats['tss_by_week'][0]['start_date']} → {stats['tss_by_week'][-1]['end_date']}
**Semaines analysées :** {stats['total_weeks']}

### Charge d'Entraînement (TSS)
- **TSS Cible :** {stats['tss_target_total']}
- **TSS Réalisé :** {stats['tss_planned']}
- **Taux de réalisation :** {stats['tss_achievement_rate']:.1f}%

### Sessions
- **Total planifié :** {stats['total_sessions']} sessions
- **Complétées :** {stats['completed']} ({stats['completed'] / stats['total_sessions'] * 100:.1f}%)
- **Modifiées :** {stats['modified']}
- **Sautées :** {stats['skipped']}
- **Annulées :** {stats['cancelled']}
- **Repos :** {stats['rest_days']}
- **Taux d'adhérence :** {stats['adherence_rate']:.1f}%

## 📈 Progression Hebdomadaire

| Semaine | Dates | TSS Cible | TSS Réalisé | % Réalisation |
|---------|-------|-----------|-------------|---------------|.
"""
        for week in stats["tss_by_week"]:
            achievement = (
                (week["tss_actual"] / week["tss_target"] * 100) if week["tss_target"] > 0 else 0
            )
            report += f"| {week['week_id']} | {week['start_date']} → {week['end_date']} | {week['tss_target']} | {week['tss_actual']} | {achievement:.1f}% |\n"

        report += "\n## 🎯 Répartition par Type de Séance\n\n"

        type_labels = {
            "END": "Endurance",
            "INT": "Intensité",
            "REC": "Récupération",
            "TEC": "Technique",
            "FOR": "Force",
            "CAD": "Cadence",
            "MIX": "Mixte",
        }

        for session_type, count in sorted(
            stats["sessions_by_type"].items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (
                count / (stats["total_sessions"] - stats["rest_days"]) * 100
                if stats["total_sessions"] > stats["rest_days"]
                else 0
            )
            type_name = type_labels.get(session_type, session_type)
            report += f"- **{type_name} ({session_type})** : {count} sessions ({percentage:.1f}%)\n"

        report += "\n## 📊 Statut des Sessions\n\n"
        for status, count in sorted(
            stats["sessions_by_status"].items(), key=lambda x: x[1], reverse=True
        ):
            percentage = count / stats["total_sessions"] * 100
            report += f"- **{status.title()}** : {count} ({percentage:.1f}%)\n"

        # Add AI analysis if available
        if ai_analysis:
            report += f"\n## 🤖 Analyse IA - Insights & Recommandations\n\n{ai_analysis}\n"

        report += f"\n---\n*Généré le {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n"

        return report

    def generate_ai_prompt(self, stats: dict) -> str:
        """Generate prompt for AI analysis."""
        month_name = self.month_date.strftime("%B %Y")

        prompt = f"""Analyse ce mois d'entraînement cyclisme ({month_name}) et fournis des insights :

📊 DONNÉES MENSUELLES :
- {stats['total_weeks']} semaines analysées
- TSS Cible : {stats['tss_target_total']}
- TSS Réalisé : {stats['tss_planned']} ({stats['tss_achievement_rate']:.1f}%)
- Taux d'adhérence : {stats['adherence_rate']:.1f}%
- Sessions complétées : {stats['completed']}/{stats['total_sessions']}
- Sessions sautées : {stats['skipped']}
- Repos : {stats['rest_days']}

📈 PROGRESSION HEBDOMADAIRE :
"""
        for week in stats["tss_by_week"]:
            prompt += f"\n- {week['week_id']} : {week['tss_actual']}/{week['tss_target']} TSS"

        prompt += "\n\n🎯 RÉPARTITION TYPES :\n"
        for session_type, count in sorted(
            stats["sessions_by_type"].items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (
                count / (stats["total_sessions"] - stats["rest_days"]) * 100
                if stats["total_sessions"] > stats["rest_days"]
                else 0
            )
            prompt += f"- {session_type} : {count} sessions ({percentage:.0f}%)\n"

        prompt += """
ANALYSE DEMANDÉE (format markdown) :

1. **Évaluation Globale** (2-3 phrases)
   - Qualité du mois (excellent/bon/moyen/insuffisant)
   - Respect de la planification

2. **Points Forts** (3-4 bullets)
   - Ce qui a bien fonctionné

3. **Points d'Amélioration** (3-4 bullets)
   - Ce qui pourrait être optimisé

4. **Analyse de Périodisation** (2-3 phrases)
   - Cohérence de la charge (progression/plateau/taper)
   - Équilibre intensité/volume/récupération

5. **Recommandations pour le Mois Suivant** (3-5 bullets)
   - Ajustements suggérés
   - Focus prioritaires

Sois concret, direct et orienté action. Utilise des emojis pour la lisibilité.
"""
        return prompt

    def _load_current_metrics(self) -> dict:
        """Load current athlete metrics for prompt enrichment.

        Returns:
            Dict with ftp, weight, ctl, atl, ramp_rate keys.
            Empty dict on failure (graceful degradation).
        """
        metrics: dict = {}
        # Load FTP/weight from AthleteProfile
        try:
            from magma_cycling.config import AthleteProfile

            profile = AthleteProfile.from_env()
            metrics["ftp"] = profile.ftp
            metrics["weight"] = profile.weight
        except Exception:
            logger.debug("Could not load AthleteProfile, skipping FTP/weight")

        # Load CTL/ATL from Intervals.icu
        try:
            from magma_cycling.config import create_intervals_client

            today = datetime.now().strftime("%Y-%m-%d")
            client = create_intervals_client()
            wellness = client.get_wellness(oldest=today, newest=today)
            if wellness:
                day = wellness[0]
                metrics["ctl"] = day.get("ctl")
                metrics["atl"] = day.get("atl")
                metrics["ramp_rate"] = day.get("rampRate")
        except Exception:
            logger.debug("Could not load Intervals.icu metrics, skipping CTL/ATL")

        return metrics

    def run(self) -> str:
        """Execute monthly analysis and return report."""
        print(f"\n{'=' * 70}")

        print(f"  📊 ANALYSE MENSUELLE - {self.month_date.strftime('%B %Y')}")
        print(f"{'=' * 70}\n")

        # Find weeks
        print(f"🔍 Recherche des semaines pour {self.month}...")
        week_files = self.find_weeks_in_month()

        if not week_files:
            print(f"❌ Aucun planning trouvé pour {self.month}")
            print(f"   Vérifier : {self.planning_dir}")
            return ""

        print(f"✅ {len(week_files)} semaine(s) trouvée(s)")
        for wf in week_files:
            print(f"   - {wf.name}")

        # Load data
        print("\n📥 Chargement des données...")
        weekly_data = self.load_weekly_data(week_files)
        print(f"✅ {len(weekly_data)} semaine(s) chargée(s)")

        # Aggregate statistics
        print("\n📊 Calcul des statistiques...")
        stats = self.aggregate_statistics(weekly_data)
        print("✅ Statistiques calculées")
        print(
            f"   - TSS : {stats['tss_planned']}/{stats['tss_target_total']} ({stats['tss_achievement_rate']:.1f}%)"
        )
        print(
            f"   - Sessions : {stats['completed']}/{stats['total_sessions']} ({stats['adherence_rate']:.1f}%)"
        )

        # AI Analysis
        ai_analysis = None
        if not self.no_ai and self.ai_analyzer:
            print(f"\n🤖 Génération analyse IA ({self.provider})...")
            try:
                workflow_data = self.generate_ai_prompt(stats)
                current_metrics = self._load_current_metrics()
                system_prompt, user_prompt = build_prompt(
                    mission="mesocycle_analysis",
                    current_metrics=current_metrics,
                    workflow_data=workflow_data,
                )
                ai_analysis = self.ai_analyzer.analyze_session(
                    user_prompt, system_prompt=system_prompt
                )
                print("✅ Analyse IA générée")
            except Exception as e:
                print(f"⚠️  Erreur analyse IA : {e}")
                print("   Rapport généré sans analyse IA")

        # Generate report
        print("\n📝 Génération du rapport...")
        report = self.generate_report(stats, ai_analysis)
        print(f"✅ Rapport généré ({len(report)} caractères)")

        return report


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Monthly training analysis - macro view of training cycle"
    )

    parser.add_argument(
        "--month", required=True, help="Month to analyze in YYYY-MM format (e.g., 2025-12)"
    )

    parser.add_argument(
        "--provider",
        default="mistral_api",
        choices=["mistral_api", "claude_api", "openai", "ollama", "clipboard"],
        help="AI provider for analysis (default: mistral_api)",
    )

    parser.add_argument(
        "--no-ai", action="store_true", help="Skip AI analysis, only generate statistics"
    )

    parser.add_argument("--output", type=Path, help="Output file path (default: print to stdout)")

    args = parser.parse_args()

    try:
        analyzer = MonthlyAnalyzer(month=args.month, provider=args.provider, no_ai=args.no_ai)

        report = analyzer.run()

        if not report:
            sys.exit(1)

        # Output
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(report, encoding="utf-8")
            print(f"\n✅ Rapport sauvegardé : {args.output}")
        else:
            print(f"\n{'=' * 70}")
            print(report)
            print(f"{'=' * 70}")

    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
