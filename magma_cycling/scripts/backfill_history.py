#!/usr/bin/env python3
"""
Backfill automatise de l'historique d'entrainement.

Analyse en masse des activites historiques depuis Intervals.icu avec generation
automatisee d'analyses IA. Utilise TimelineInjector via insert-analysis pour
injection chronologique dans workouts-history.md.

Examples:
    CLI usage::

        # Backfill par defaut (2024-01-01 → aujourd'hui)
        poetry run backfill-history --yes

        # Backfill periode specifique
        poetry run backfill-history --start-date 2024-08-01 --end-date 2024-08-31 --yes

        # Test dry-run avec limite
        poetry run backfill-history --dry-run --limit 5

        # Provider specifique et batch size
        poetry run backfill-history --provider claude_api --batch-size 5 --yes

        # Skip activites avec workouts planifies
        poetry run backfill-history --skip-planned --yes

    Programmatic usage::

        from backfill_history import HistoryBackfiller

        # Initialisation backfiller
        backfiller = HistoryBackfiller(
            provider="mistral_api",
            batch_size=10,
            yes_confirm=True
        )

        # Execution backfill (utilise TimelineInjector via insert-analysis)
        backfiller.run(
            start_date="2024-08-01",
            end_date="2024-08-31"
        )

Author: Claude Code
Created: 2025-12-26
Updated: 2025-12-26 (Integrated TimelineInjector via insert-analysis)

Metadata:
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: I
    Status: Production
    Priority: P2
    Version: v2
"""
import argparse
import sys
import time
from datetime import datetime

from magma_cycling.config import create_intervals_client, get_data_config
from magma_cycling.scripts.backfill.fetching import DataFetchMixin
from magma_cycling.scripts.backfill.persistence import PersistenceMixin
from magma_cycling.scripts.backfill.processing import ProcessingMixin
from magma_cycling.utils.cli import cli_main
from magma_cycling.workflow_state import WorkflowState


class HistoryBackfiller(DataFetchMixin, ProcessingMixin, PersistenceMixin):
    """Backfill training history with AI analysis."""

    def __init__(
        self,
        provider: str = "mistral_api",
        batch_size: int = 10,
        dry_run: bool = False,
        yes_confirm: bool = False,
        force_reanalyze: bool = False,
    ):
        """Initialize history backfiller.

        Args:
            provider: AI provider name (default: mistral_api)
            batch_size: Number of activities per batch (default: 10)
            dry_run: If True, simulate without writing (default: False)
            yes_confirm: If True, skip confirmation prompts (default: False)
            force_reanalyze: If True, reanalyze existing entries (default: False).
        """
        self.provider = provider

        self.batch_size = batch_size
        self.dry_run = dry_run
        self.yes_confirm = yes_confirm
        self.force_reanalyze = force_reanalyze

        self.api = create_intervals_client()
        self.state = WorkflowState()

        # Get data repo configuration
        self.data_config = get_data_config()

        # Statistics tracking
        self.total_activities = 0
        self.already_analyzed = 0
        self.to_analyze = 0
        self.analyzed_success = 0
        self.analyzed_failed = 0
        self.start_time: float | None = None

    def run(
        self, start_date: str, end_date: str, skip_planned: bool = False, limit: int | None = None
    ):
        """
        Run complete backfill process.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            skip_planned: Skip activities with planned workouts
            limit: Max activities to analyze (for testing).
        """
        self.start_time = time.time()

        # Print header
        print("\n" + "=" * 70)
        print("  🚀 BACKFILL HISTORIQUE COMPLET")
        print("=" * 70)
        print(f"\n📅 Periode: {start_date} → {end_date}")
        print(f"🤖 Provider: {self.provider}")
        print(f"📦 Batch size: {self.batch_size}")
        print(f"🔍 Dry run: {self.dry_run}")
        if limit:
            print(f"⚠️  Limit: {limit} activites max")
        print()

        # Fetch all activities
        activities = self.fetch_activities(start_date, end_date)
        self.total_activities = len(activities)

        # Filter unanalyzed
        to_analyze = self.filter_unanalyzed(activities, skip_planned)
        self.to_analyze = len(to_analyze)

        # Print summary
        print("\n📊 RESUME:")
        print(f"   Total activites: {self.total_activities}")
        print(f"   Deja analysees: {self.already_analyzed}")
        print(f"   A analyser: {self.to_analyze}")

        # Apply limit if specified
        if limit and self.to_analyze > limit:
            print(f"\n⚠️  Limite activee: {limit} activites max")
            to_analyze = to_analyze[:limit]
            self.to_analyze = limit

        # Nothing to do?
        if self.to_analyze == 0:
            print("\n✅ Rien a faire!")
            print("   Toutes les activites sont deja analysees.")
            return

        # Estimate resources
        estimates = self.estimate_resources(self.to_analyze)

        print("\n⏱️  ESTIMATIONS:")
        print(
            f"   Temps: ~{estimates['time_hours']:.1f}h " f"({estimates['time_minutes']:.0f} min)"
        )
        print(f"   Cout: ${estimates['cost_usd']:.2f} " f"({self.provider})")

        # Confirm if not dry run
        if not self.dry_run:
            if self.yes_confirm:
                print("\n✅ CONFIRMATION AUTOMATIQUE (--yes)")
                print(f"   Analyse de {self.to_analyze} activites avec '{self.provider}'")
            else:
                print("\n⚠️  CONFIRMATION REQUISE")
                print(f"   Cela va analyser {self.to_analyze} activites")
                print(f"   avec le provider '{self.provider}'")
                print()

                response = input("   Continuer? (yes/no): ").strip().lower()
                if response not in ["yes", "y"]:
                    print("\n❌ Annule par l'utilisateur")
                    return

        # Process activities in batches
        batch = []
        batch_num = 1

        for i, activity in enumerate(to_analyze, 1):
            # Progress header
            progress_pct = int(i * 100 / self.to_analyze)
            print(f"\n{'=' * 70}")
            print(f"📈 Progression: {i}/{self.to_analyze} ({progress_pct}%)")

            # Estimate remaining time
            if self.start_time and i > 1:
                elapsed = time.time() - self.start_time
                avg_time_per_activity = elapsed / (i - 1)
                remaining_activities = self.to_analyze - i + 1
                eta_seconds = avg_time_per_activity * remaining_activities
                eta_minutes = eta_seconds / 60
                print(f"⏱️  ETA: ~{eta_minutes:.1f} min")

            print(f"{'=' * 70}")

            # Analyze activity
            success = self.analyze_activity(activity)

            # Add to batch if successful
            if success:
                batch.append(activity)

            # Commit batch if full
            if len(batch) >= self.batch_size:
                self.commit_batch(batch_num, batch)
                batch = []
                batch_num += 1

                # Rate limiting (avoid API throttling)
                if not self.dry_run and i < self.to_analyze:
                    print("\n⏸️  Pause 5s (rate limiting)...")
                    time.sleep(5)

        # Commit remaining activities
        if batch:
            self.commit_batch(batch_num, batch)

        # Final report
        self.print_final_report()


@cli_main
def main():
    """Run entry point."""
    parser = argparse.ArgumentParser(
        description="Backfill complete training history from Intervals.icu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  # Dry run to see what would be analyzed
  poetry run backfill-history --dry-run --limit 10

  # Test with 10 activities
  poetry run backfill-history --limit 10 --provider mistral_api

  # Backfill complete 2024
  poetry run backfill-history --start-date 2024-01-01 --end-date 2024-12-31

  # Backfill all with Claude API
  poetry run backfill-history --start-date 2024-01-01 --provider claude_api

  # Backfill with Ollama (free but slow)
  poetry run backfill-history --start-date 2024-01-01 --provider ollama.
        """,
    )

    parser.add_argument(
        "--start-date",
        default="2024-01-01",
        help="Start date in YYYY-MM-DD format (default: 2024-01-01)",
    )

    parser.add_argument(
        "--end-date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="End date in YYYY-MM-DD format (default: today)",
    )

    parser.add_argument(
        "--provider",
        default="mistral_api",
        choices=["mistral_api", "claude_api", "openai", "ollama", "clipboard"],
        help="AI provider to use (default: mistral_api)",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of activities per git commit (default: 10)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be analyzed without actually doing it",
    )

    parser.add_argument(
        "--skip-planned", action="store_true", help="Skip activities that have planned workouts"
    )

    parser.add_argument(
        "--limit", type=int, help="Maximum number of activities to analyze (for testing)"
    )

    parser.add_argument(
        "--yes", action="store_true", help="Auto-confirm analysis (no interactive prompt)"
    )

    parser.add_argument(
        "--force-reanalyze",
        action="store_true",
        help="Force re-analyze activities even if already in workflow state (useful after fixing bugs)",
    )

    args = parser.parse_args()

    # Validate dates
    try:
        datetime.strptime(args.start_date, "%Y-%m-%d")
        datetime.strptime(args.end_date, "%Y-%m-%d")
    except ValueError as e:
        print(f"❌ Invalid date format: {e}")
        print("   Use YYYY-MM-DD format")
        sys.exit(1)

    # Create and run backfiller
    backfiller = HistoryBackfiller(
        provider=args.provider,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        yes_confirm=args.yes,
        force_reanalyze=args.force_reanalyze,
    )

    try:
        backfiller.run(
            start_date=args.start_date,
            end_date=args.end_date,
            skip_planned=args.skip_planned,
            limit=args.limit,
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompu par l'utilisateur (Ctrl+C)")
        print("\n📊 Progression avant interruption:")
        print(f"   Analysees: {backfiller.analyzed_success}")
        print(f"   Echecs: {backfiller.analyzed_failed}")
        sys.exit(130)


if __name__ == "__main__":
    main()
