#!/usr/bin/env python3
"""Populate Zwift Workout Cache - Seed database from whatsonzwift.com collections.

Usage:
    poetry run populate-zwift-cache --collection zwift-camp-baseline
    poetry run populate-zwift-cache --all
    poetry run populate-zwift-cache --collection zwift-camp-baseline --dry-run
"""

import argparse
import sys
from pathlib import Path

from magma_cycling.external.zwift_collections import KNOWN_COLLECTIONS
from magma_cycling.external.zwift_service import ZwiftService
from magma_cycling.utils.cli import cli_main


@cli_main
def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Populate Zwift workout cache from whatsonzwift.com",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Known Collections:
{chr(10).join(f'  {slug:25s} - {desc}' for slug, desc in KNOWN_COLLECTIONS.items())}

Examples:
  %(prog)s --collection zwift-camp-baseline
  %(prog)s --collection zwift-camp-baseline --collection ftp-builder
  %(prog)s --all
  %(prog)s --collection zwift-camp-baseline --dry-run
        """,
    )

    parser.add_argument(
        "--collection",
        dest="collections",
        action="append",
        help="Collection slug to populate (can be specified multiple times)",
    )
    parser.add_argument(
        "--all",
        dest="all_collections",
        action="store_true",
        help="Populate from all known collections",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Parse workouts but don't save to cache",
    )
    parser.add_argument(
        "--cache-path",
        dest="cache_path",
        type=Path,
        help="Custom cache database path",
    )

    args = parser.parse_args()

    # Determine which collections to populate
    if args.all_collections:
        collections = list(KNOWN_COLLECTIONS.keys())
    elif args.collections:
        collections = args.collections
    else:
        parser.print_help()
        print("\n❌ Error: Specify --collection or --all")
        sys.exit(1)

    if args.dry_run:
        print("\n⚠️  DRY-RUN MODE - No workouts will be cached\n")

    service = ZwiftService(cache_db_path=args.cache_path)

    def _on_workout(index, total, workout):
        if workout:
            pattern_str = f" [{workout.pattern}]" if workout.pattern else ""
            print(
                f"   [{index}/{total}] ✅ {workout.name} "
                f"({workout.tss} TSS, {len(workout.segments)} seg{pattern_str})"
            )
        else:
            print(f"   [{index}/{total}] ⚠️  Failed to parse")

    results = service.populate_collections(
        collections, dry_run=args.dry_run, on_workout=_on_workout
    )

    # Summary
    total_cached = sum(r.cached_count for r in results.values())
    print(f"\n{'=' * 80}")
    print(f"🎯 Total: {total_cached} workouts cached from {len(collections)} collections")

    for slug, result in results.items():
        status = f"{result.cached_count}/{result.total_found}"
        extras = []
        if result.skipped_count > 0:
            extras.append(f"{result.skipped_count} dupes")
        if result.errors:
            extras.append(f"{len(result.errors)} errors")
        suffix = f" ({', '.join(extras)})" if extras else ""
        print(f"   {slug:25s}: {status}{suffix}")

    print("=" * 80)

    # Cache stats
    if not args.dry_run:
        stats = service.get_cache_stats()
        print(f"\n📊 Cache: {stats['total_workouts']} workouts")
        if stats.get("by_category"):
            for category, count in sorted(
                stats["by_category"].items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  {category:20s}: {count:3d} workouts")


if __name__ == "__main__":
    main()
