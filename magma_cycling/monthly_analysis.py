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
import sys
from datetime import datetime
from pathlib import Path

from magma_cycling.ai_providers.factory import AIProviderFactory
from magma_cycling.analyzers.monthly.data import DataMixin
from magma_cycling.analyzers.monthly.reporting import ReportingMixin
from magma_cycling.analyzers.monthly.stats import StatsMixin
from magma_cycling.config import get_ai_config, get_data_config
from magma_cycling.prompts import build_prompt
from magma_cycling.utils.cli import cli_main


class MonthlyAnalyzer(DataMixin, StatsMixin, ReportingMixin):
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

    def run(self) -> str:
        """Execute monthly analysis and return report."""
        print(f"\n{'=' * 70}")

        print(f"  \U0001f4ca ANALYSE MENSUELLE - {self.month_date.strftime('%B %Y')}")
        print(f"{'=' * 70}\n")

        # Find weeks
        print(f"\U0001f50d Recherche des semaines pour {self.month}...")
        week_files = self.find_weeks_in_month()

        if not week_files:
            print(f"\u274c Aucun planning trouv\u00e9 pour {self.month}")
            print(f"   V\u00e9rifier : {self.planning_dir}")
            return ""

        print(f"\u2705 {len(week_files)} semaine(s) trouv\u00e9e(s)")
        for wf in week_files:
            print(f"   - {wf.name}")

        # Load data
        print("\n\U0001f4e5 Chargement des donn\u00e9es...")
        weekly_data = self.load_weekly_data(week_files)
        print(f"\u2705 {len(weekly_data)} semaine(s) charg\u00e9e(s)")

        # Fetch actual TSS from Intervals.icu
        print("\n\U0001f4e1 R\u00e9cup\u00e9ration TSS r\u00e9els (Intervals.icu)...")
        actual_tss_map = self._fetch_actual_tss(weekly_data)
        if actual_tss_map:
            print(f"\u2705 {len(actual_tss_map)} activit\u00e9s trouv\u00e9es")
        else:
            print("\u26a0\ufe0f  Fallback sur TSS planifi\u00e9s")

        # Aggregate statistics
        print("\n\U0001f4ca Calcul des statistiques...")
        stats = self.aggregate_statistics(weekly_data, actual_tss_map)
        print("\u2705 Statistiques calcul\u00e9es")
        print(
            f"   - TSS : {stats['tss_realized']}/{stats['tss_target_total']} ({stats['tss_achievement_rate']:.1f}%)"
        )
        print(
            f"   - Sessions : {stats['completed']}/{stats['total_sessions']} ({stats['adherence_rate']:.1f}%)"
        )

        # AI Analysis
        ai_analysis = None
        if not self.no_ai and self.ai_analyzer:
            print(f"\n\U0001f916 G\u00e9n\u00e9ration analyse IA ({self.provider})...")
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
                print("\u2705 Analyse IA g\u00e9n\u00e9r\u00e9e")
            except Exception as e:
                print(f"\u26a0\ufe0f  Erreur analyse IA : {e}")
                print("   Rapport g\u00e9n\u00e9r\u00e9 sans analyse IA")

        # Generate report
        print("\n\U0001f4dd G\u00e9n\u00e9ration du rapport...")
        report = self.generate_report(stats, ai_analysis)
        print(f"\u2705 Rapport g\u00e9n\u00e9r\u00e9 ({len(report)} caract\u00e8res)")

        return report


@cli_main
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

    analyzer = MonthlyAnalyzer(month=args.month, provider=args.provider, no_ai=args.no_ai)

    report = analyzer.run()

    if not report:
        sys.exit(1)

    # Output
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"\n\u2705 Rapport sauvegard\u00e9 : {args.output}")
    else:
        print(f"\n{'=' * 70}")
        print(report)
        print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
