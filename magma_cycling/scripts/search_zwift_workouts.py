#!/usr/bin/env python3
"""Zwift Workout Search - Find diverse workouts from cached database.

Usage:
    poetry run search-zwift-workouts --type FTP --tss 56
    poetry run search-zwift-workouts --type INT --tss 80 --duration-min 45
    poetry run search-zwift-workouts --cache-stats
    poetry run search-zwift-workouts --sample
"""

import argparse
import sys
from pathlib import Path

from magma_cycling.external.zwift_models import WorkoutSearchCriteria
from magma_cycling.external.zwift_service import ZwiftService
from magma_cycling.utils.cli import cli_main

# ---------------------------------------------------------------------------
# Display helpers (pure formatting, no business logic)
# ---------------------------------------------------------------------------


def _print_search_results(matches, limit):
    """Format and print search results."""
    if not matches:
        print("❌ No matching workouts found.")
        print("\nTry:")
        print("  - Increasing TSS tolerance (--tss-tolerance)")
        print("  - Removing duration constraints")
        print("  - Using --show-all to include recently used workouts")
        return

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
            print(f"   Usage: {workout.usage_count}x | Last: {workout.last_used_date or 'Never'}")
        if match.recently_used:
            print("   ⚠️  Recently used (within 21-day diversity window)")
        print(f"   URL: {workout.url}")

        if workout.description:
            print(f"\n   {workout.description}")

        # Intervals.icu preview
        print("\n   Intervals.icu Format Preview:")
        text_lines = workout.to_intervals_description().split("\n")
        for line in text_lines[:8]:
            print(f"   {line}")
        if len(text_lines) > 8:
            print(f"   ... ({len(text_lines) - 8} more lines)")

        print("\n" + "-" * 80)

    if len(matches) > limit:
        print(f"\n... and {len(matches) - limit} more result(s)")
        print(f"Use --limit {len(matches)} to see all results")


def _print_cache_stats(stats):
    """Format and print cache statistics."""
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


def _print_sample_workout(service):
    """Generate and display a sample workout."""
    print("\n📋 Sample Workout (Flat Out Fast)\n")
    print("=" * 80)

    workout = service.create_sample_workout()
    print(f"Name: {workout.name}")
    print(f"Category: {workout.category.value}")
    print(f"Duration: {workout.duration_minutes} min")
    print(f"TSS: {workout.tss}")
    print(f"Segments: {len(workout.segments)}")
    print()

    text_desc = workout.to_intervals_description()
    print("Intervals.icu Format:")
    print("-" * 80)
    print(text_desc)
    print("-" * 80)

    is_valid, issues = service.validate_wahoo(text_desc)
    if is_valid:
        print("\n✅ Wahoo ELEMNT compatible")
    else:
        print("\n❌ Wahoo compatibility issues:")
        for issue in issues:
            print(f"   - {issue}")

    print("=" * 80)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


@cli_main
def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Search Zwift workouts from whatsonzwift.com",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --type FTP --tss 56
  %(prog)s --type INT --tss 80 --duration-min 45 --duration-max 60
  %(prog)s --type END --tss 100 --show-all
  %(prog)s --cache-stats

Valid session types:
  END  - Endurance       INT  - Intervals       FTP  - FTP Test
  SPR  - Sprint          CLM  - Climbing        REC  - Recovery
  FOR  - Force           CAD  - Cadence         TEC  - Technique
  MIX  - Mixed           PDC  - Pédales         TST  - Test
        """,
    )

    parser.add_argument("--type", dest="session_type", help="Session type (3-letter code)")
    parser.add_argument("--tss", dest="tss_target", type=int, help="Target TSS")
    parser.add_argument(
        "--tss-tolerance",
        dest="tss_tolerance",
        type=int,
        default=15,
        help="TSS tolerance %% (default: 15)",
    )
    parser.add_argument("--duration-min", dest="duration_min", type=int, help="Min duration (min)")
    parser.add_argument("--duration-max", dest="duration_max", type=int, help="Max duration (min)")
    parser.add_argument(
        "--show-all", dest="show_all", action="store_true", help="Include recently used"
    )
    parser.add_argument(
        "--limit", dest="limit", type=int, default=5, help="Max results (default: 5)"
    )
    parser.add_argument(
        "--cache-stats", dest="cache_stats", action="store_true", help="Show cache statistics"
    )
    parser.add_argument("--sample", dest="sample", action="store_true", help="Show sample workout")
    parser.add_argument("--cache-path", dest="cache_path", type=Path, help="Custom cache path")

    args = parser.parse_args()

    service = ZwiftService(cache_db_path=args.cache_path)

    if args.cache_stats:
        _print_cache_stats(service.get_cache_stats())
    elif args.sample:
        _print_sample_workout(service)
    elif args.session_type and args.tss_target:
        print("\n🔍 Searching Zwift workouts...")
        print(f"   Type: {args.session_type.upper()}")
        print(f"   TSS: {args.tss_target} ±{args.tss_tolerance}%")
        if args.duration_min or args.duration_max:
            print(f"   Duration: {args.duration_min or 0}-{args.duration_max or '∞'} min")
        print()

        criteria = WorkoutSearchCriteria(
            session_type=args.session_type.upper(),
            tss_target=args.tss_target,
            tss_tolerance=args.tss_tolerance,
            duration_min=args.duration_min,
            duration_max=args.duration_max,
            exclude_recent=not args.show_all,
        )
        matches = service.search_workouts(criteria)
        _print_search_results(matches, args.limit)
    else:
        parser.print_help()
        print("\n❌ Error: --type and --tss are required for search")
        print("   Or use --cache-stats or --sample for utility commands")
        sys.exit(1)


if __name__ == "__main__":
    main()
