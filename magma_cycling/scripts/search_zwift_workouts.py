#!/usr/bin/env python3
"""
Zwift Workout Search - Find diverse workouts from whatsonzwift.com database.

This script searches the Zwift workout catalog for workouts matching specific
criteria (TSS, session type, duration) while maintaining diversity through
usage tracking.

Features:
- SQLite-cached workout database (60-day TTL)
- Multi-factor matching: TSS accuracy, type fit, duration constraints
- Diversity enforcement: 21-day rotation window
- Wahoo ELEMNT compatibility validation
- Intervals.icu text format export

Usage:
    # Search for FTP workout ~56 TSS
    poetry run search-zwift-workouts --type FTP --tss 56

    # Search with duration constraints
    poetry run search-zwift-workouts --type INT --tss 80 --duration-min 45 --duration-max 60

    # Show all matches (no diversity filter)
    poetry run search-zwift-workouts --type END --tss 100 --show-all

    # Show cache statistics
    poetry run search-zwift-workouts --cache-stats

    # Generate sample workout for testing
    poetry run search-zwift-workouts --sample

Metadata:
    Created: 2026-02-10
    Author: Claude Code + Stéphane Jouve
    Category: EXTERNAL DATA + PLANNING
    Status: Development (Sprint 1)
    Priority: P1
    Version: 1.0.0
    Sprint: Zwift Integration S1
"""

import argparse
import sys
from pathlib import Path

from magma_cycling.external.zwift_client import ZwiftWorkoutClient
from magma_cycling.external.zwift_converter import ZwiftWorkoutConverter
from magma_cycling.external.zwift_models import (
    WorkoutSearchCriteria,
)


class ZwiftWorkoutSearchCLI:
    """CLI interface for Zwift workout search.

    Attributes:
        client: ZwiftWorkoutClient instance
        converter: ZwiftWorkoutConverter instance
    """

    def __init__(self, cache_db_path: Path | None = None):
        """Initialize the CLI with Zwift client.

        Args:
            cache_db_path: Optional custom cache database path
        """
        self.client = ZwiftWorkoutClient(cache_db_path=cache_db_path)
        self.converter = ZwiftWorkoutConverter()

    def search_workouts(
        self,
        session_type: str,
        tss_target: int,
        tss_tolerance: int = 15,
        duration_min: int | None = None,
        duration_max: int | None = None,
        show_all: bool = False,
        limit: int = 5,
    ) -> None:
        """Search for workouts and display results.

        Args:
            session_type: 3-letter session type code
            tss_target: Target TSS
            tss_tolerance: TSS tolerance percentage
            duration_min: Minimum duration in minutes
            duration_max: Maximum duration in minutes
            show_all: Show all matches including recently used
            limit: Maximum number of results to display
        """
        print("\n🔍 Searching Zwift workouts...")
        print(f"   Type: {session_type}")
        print(f"   TSS: {tss_target} ±{tss_tolerance}%")
        if duration_min or duration_max:
            print(f"   Duration: {duration_min or 0}-{duration_max or '∞'} min")
        print()

        # Create search criteria
        criteria = WorkoutSearchCriteria(
            session_type=session_type,
            tss_target=tss_target,
            tss_tolerance=tss_tolerance,
            duration_min=duration_min,
            duration_max=duration_max,
            exclude_recent=not show_all,
        )

        # Search workouts
        matches = self.client.search_workouts(criteria)

        if not matches:
            print("❌ No matching workouts found.")
            print("\nTry:")
            print("  - Increasing TSS tolerance (--tss-tolerance)")
            print("  - Removing duration constraints")
            print("  - Using --show-all to include recently used workouts")
            return

        # Display results
        print(f"✅ Found {len(matches)} matching workout(s)\n")
        print("=" * 80)

        for i, match in enumerate(matches[:limit], start=1):
            workout = match.workout
            print(f"\n{i}. {workout.name}")
            print(
                f"   Score: {match.score:.1f}/100 | TSS: {workout.tss} (Δ{match.tss_delta}) | "
                f"Duration: {workout.duration_minutes}min"
            )
            print(f"   Category: {workout.category.value} | Type Match: {match.type_match}")
            if workout.usage_count > 0:
                print(
                    f"   Usage: {workout.usage_count}x | Last: {workout.last_used_date or 'Never'}"
                )
            if match.recently_used:
                print("   ⚠️  Recently used (within 21-day diversity window)")
            print(f"   URL: {workout.url}")

            # Show workout description
            if workout.description:
                print(f"\n   {workout.description}")

            # Show Intervals.icu format preview
            print("\n   Intervals.icu Format Preview:")
            text_desc = workout.to_intervals_description()
            text_lines = text_desc.split("\n")
            for line in text_lines[:8]:  # Show first 8 lines
                print(f"   {line}")
            if len(text_lines) > 8:
                print(f"   ... ({len(text_lines) - 8} more lines)")

            print("\n" + "-" * 80)

        if len(matches) > limit:
            print(f"\n... and {len(matches) - limit} more result(s)")
            print(f"Use --limit {len(matches)} to see all results")

    def show_cache_stats(self) -> None:
        """Display cache statistics."""
        stats = self.client.get_cache_stats()

        print("\n📊 Zwift Workout Cache Statistics\n")
        print("=" * 80)
        print(f"Total workouts: {stats['total_workouts']}")
        print(f"Cache location: {stats['cache_path']}")
        print(f"Oldest cached: {stats.get('oldest_cached', 'N/A')}")
        print(f"Newest cached: {stats.get('newest_cached', 'N/A')}")

        if stats.get("by_category"):
            print("\nWorkouts by category:")
            for category, count in sorted(
                stats["by_category"].items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  {category:20s}: {count:3d} workouts")

        print("=" * 80)

    def show_sample_workout(self) -> None:
        """Generate and display a sample workout."""
        print("\n📋 Sample Workout (Flat Out Fast)\n")
        print("=" * 80)

        workout = self.converter.create_sample_workout()

        print(f"Name: {workout.name}")
        print(f"Category: {workout.category.value}")
        print(f"Duration: {workout.duration_minutes} min")
        print(f"TSS: {workout.tss}")
        print(f"Segments: {len(workout.segments)}")
        print()

        # Show Intervals.icu format
        text_desc = workout.to_intervals_description()
        print("Intervals.icu Format:")
        print("-" * 80)
        print(text_desc)
        print("-" * 80)

        # Validate Wahoo compatibility
        is_valid, issues = self.converter.validate_wahoo_compatibility(text_desc)
        if is_valid:
            print("\n✅ Wahoo ELEMNT compatible")
        else:
            print("\n❌ Wahoo compatibility issues:")
            for issue in issues:
                print(f"   - {issue}")

        print("=" * 80)


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Search Zwift workouts from whatsonzwift.com",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for FTP workout
  %(prog)s --type FTP --tss 56

  # Search with duration constraints
  %(prog)s --type INT --tss 80 --duration-min 45 --duration-max 60

  # Show all matches including recently used
  %(prog)s --type END --tss 100 --show-all

  # Cache statistics
  %(prog)s --cache-stats

Valid session types:
  END  - Endurance       INT  - Intervals       FTP  - FTP Test
  SPR  - Sprint          CLM  - Climbing        REC  - Recovery
  FOR  - Force           CAD  - Cadence         TEC  - Technique
  MIX  - Mixed           PDC  - Pédales         TST  - Test
        """,
    )

    # Search parameters
    parser.add_argument(
        "--type",
        dest="session_type",
        help="Session type (3-letter code: END, INT, FTP, etc.)",
    )
    parser.add_argument(
        "--tss",
        dest="tss_target",
        type=int,
        help="Target TSS",
    )
    parser.add_argument(
        "--tss-tolerance",
        dest="tss_tolerance",
        type=int,
        default=15,
        help="TSS tolerance percentage (default: 15)",
    )
    parser.add_argument(
        "--duration-min",
        dest="duration_min",
        type=int,
        help="Minimum duration in minutes",
    )
    parser.add_argument(
        "--duration-max",
        dest="duration_max",
        type=int,
        help="Maximum duration in minutes",
    )
    parser.add_argument(
        "--show-all",
        dest="show_all",
        action="store_true",
        help="Show all matches including recently used workouts",
    )
    parser.add_argument(
        "--limit",
        dest="limit",
        type=int,
        default=5,
        help="Maximum number of results to display (default: 5)",
    )

    # Utility commands
    parser.add_argument(
        "--cache-stats",
        dest="cache_stats",
        action="store_true",
        help="Show cache statistics",
    )
    parser.add_argument(
        "--sample",
        dest="sample",
        action="store_true",
        help="Generate and display sample workout",
    )

    # Options
    parser.add_argument(
        "--cache-path",
        dest="cache_path",
        type=Path,
        help="Custom cache database path",
    )

    args = parser.parse_args()

    # Initialize CLI
    cli = ZwiftWorkoutSearchCLI(cache_db_path=args.cache_path)

    # Execute command
    if args.cache_stats:
        cli.show_cache_stats()
    elif args.sample:
        cli.show_sample_workout()
    elif args.session_type and args.tss_target:
        cli.search_workouts(
            session_type=args.session_type.upper(),
            tss_target=args.tss_target,
            tss_tolerance=args.tss_tolerance,
            duration_min=args.duration_min,
            duration_max=args.duration_max,
            show_all=args.show_all,
            limit=args.limit,
        )
    else:
        parser.print_help()
        print("\n❌ Error: --type and --tss are required for search")
        print("   Or use --cache-stats or --sample for utility commands")
        sys.exit(1)


if __name__ == "__main__":
    main()
