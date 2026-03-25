#!/usr/bin/env python3
"""
Backfill Training Intelligence depuis historique Intervals.icu.

Extrait learnings et patterns depuis 2 ans de donnees (2024-2025) pour
pre-remplir TrainingIntelligence avec knowledge accumulee.

Usage:
    poetry run backfill-intelligence --start-date 2024-01-01 --end-date 2025-12-31

Examples:
    # Backfill complet 2024-2025
    poetry run backfill-intelligence --start-date 2024-01-01 --end-date 2025-12-31 --output ~/data/intelligence.json

    # Analyse specifique
    python backfill_intelligence.py --athlete-id iXXXXXX --start 2024-01-01 --end 2024-12-31

Metadata:
    Created: 2026-01-02
    Author: Claude Code
    Category: INTELLIGENCE
    Status: Production
    Priority: P1
    Version: 1.0.0.
"""
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from magma_cycling.api.intervals_client import IntervalsClient
from magma_cycling.intelligence.training_intelligence import TrainingIntelligence
from magma_cycling.scripts.intelligence.analysis import AnalysisMixin
from magma_cycling.scripts.intelligence.fetching import DataFetchMixin
from magma_cycling.utils.cli import cli_main

# Load environment
env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)


class IntervalsICUBackfiller(DataFetchMixin, AnalysisMixin):
    """
    Backfill TrainingIntelligence depuis historique Intervals.icu.

    Analyse activites historiques pour extraire:
    - Learnings (sweet-spot optimal, FTP progression)
    - Patterns (VO2/sommeil, outdoor discipline)
    - Protocol adaptations

    Attributes:
        client: IntervalsClient API instance
        intelligence: TrainingIntelligence instance
        athlete_id: Intervals.icu athlete ID.
    """

    def __init__(self, athlete_id: str, api_key: str):
        """
        Initialize backfiller.

        Args:
            athlete_id: Intervals.icu athlete ID (e.g., "iXXXXXX")
            api_key: Intervals.icu API key
        """
        self.athlete_id = athlete_id

        self.client = IntervalsClient(athlete_id=athlete_id, api_key=api_key)
        self.intelligence = TrainingIntelligence()

    def run(self, start_date: str, end_date: str, output_path: Path) -> None:
        """
        Execute backfill analysis.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            output_path: Path to save intelligence JSON.
        """
        print(f"\n🚀 Starting backfill: {start_date} → {end_date}")

        print(f"📁 Output: {output_path}")
        print("=" * 60)

        # Fetch data
        activities = self.fetch_activities(start_date, end_date)
        wellness_data = self.fetch_wellness(start_date, end_date)

        if not activities:
            print("\n❌ No activities found. Aborting.")
            return

        # Run analyses
        self.analyze_sweet_spot_sessions(activities)
        self.analyze_vo2_sleep_correlation(activities, wellness_data)
        self.analyze_outdoor_discipline(activities)
        self.analyze_ftp_progression(start_date, end_date, activities, wellness_data)

        # Save intelligence
        print(f"\n💾 Saving intelligence to {output_path}...")
        self.intelligence.save_to_file(output_path)

        # Print summary
        print("\n" + "=" * 60)
        print("✨ Backfill complete!")
        print(f"   Learnings: {len(self.intelligence.learnings)}")
        print(f"   Patterns: {len(self.intelligence.patterns)}")
        print(f"   Saved to: {output_path}")


@cli_main
def main():
    """Run entry point."""
    parser = argparse.ArgumentParser(
        description="Backfill Training Intelligence from Intervals.icu history"
    )

    parser.add_argument("--start-date", type=str, required=True, help="Start date (YYYY-MM-DD)")

    parser.add_argument("--end-date", type=str, required=True, help="End date (YYYY-MM-DD)")

    parser.add_argument(
        "--output",
        type=str,
        default="~/data/intelligence_backfilled.json",
        help="Output path for intelligence JSON",
    )

    parser.add_argument("--athlete-id", type=str, help="Intervals.icu athlete ID (overrides env)")

    parser.add_argument("--api-key", type=str, help="Intervals.icu API key (overrides env)")

    args = parser.parse_args()

    # Get credentials (support both standard and VITE_ prefixed)
    athlete_id = (
        args.athlete_id
        or os.getenv("INTERVALS_ATHLETE_ID")
        or os.getenv("VITE_INTERVALS_ATHLETE_ID")
    )
    api_key = args.api_key or os.getenv("INTERVALS_API_KEY") or os.getenv("VITE_INTERVALS_API_KEY")

    if not athlete_id or not api_key:
        print("❌ Missing Intervals.icu credentials")
        print("   Set INTERVALS_ATHLETE_ID and INTERVALS_API_KEY environment variables")
        print("   Or VITE_INTERVALS_ATHLETE_ID and VITE_INTERVALS_API_KEY")
        print("   Or pass --athlete-id and --api-key arguments")
        sys.exit(1)

    # Expand output path
    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Run backfill
    backfiller = IntervalsICUBackfiller(athlete_id=athlete_id, api_key=api_key)
    backfiller.run(args.start_date, args.end_date, output_path)


if __name__ == "__main__":
    main()
