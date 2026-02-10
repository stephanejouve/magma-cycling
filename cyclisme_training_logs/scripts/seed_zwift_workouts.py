#!/usr/bin/env python3
"""
Seed Zwift Workouts - Load curated workouts into cache.

This script loads manually curated Zwift workouts from seed data into the cache.
Unlike the web scraper, this uses verified workout definitions.

Usage:
    # Seed all collections
    poetry run seed-zwift-workouts

    # Seed specific collection
    poetry run seed-zwift-workouts --collection zwift-camp-baseline-2025

    # Show available collections without seeding
    poetry run seed-zwift-workouts --list

Metadata:
    Created: 2026-02-10
    Author: Claude Code + Stéphane Jouve
    Category: EXTERNAL DATA + CACHE
    Status: Development (Sprint 2)
    Priority: P1
    Version: 1.0.0
    Sprint: Zwift Integration S2
"""

import argparse
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cyclisme_training_logs.external.zwift_client import ZwiftWorkoutClient  # noqa: E402
from cyclisme_training_logs.external.zwift_seed_data import (  # noqa: E402
    get_all_seed_workouts,
)


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Seed Zwift workout cache from curated collections",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Seed all collections
  %(prog)s

  # Seed specific collection
  %(prog)s --collection zwift-camp-baseline-2025

  # List available collections
  %(prog)s --list
        """,
    )

    parser.add_argument(
        "--collection",
        dest="collection",
        help="Collection name to seed (default: all)",
    )
    parser.add_argument(
        "--list",
        dest="list_collections",
        action="store_true",
        help="List available seed collections",
    )
    parser.add_argument(
        "--cache-path",
        dest="cache_path",
        type=Path,
        help="Custom cache database path",
    )

    args = parser.parse_args()

    # Get all seed workouts
    all_collections = get_all_seed_workouts()

    # List collections if requested
    if args.list_collections:
        print("\n📚 Available Seed Collections:\n")
        for name, workouts in all_collections.items():
            print(f"  {name}")
            print(f"    Workouts: {len(workouts)}")
            for workout in workouts:
                print(f"      - {workout.name} ({workout.duration_minutes}min, {workout.tss} TSS)")
        print()
        return

    # Determine which collections to seed
    if args.collection:
        if args.collection not in all_collections:
            print(f"❌ Error: Collection '{args.collection}' not found")
            print(f"Available collections: {', '.join(all_collections.keys())}")
            sys.exit(1)
        collections_to_seed = {args.collection: all_collections[args.collection]}
    else:
        collections_to_seed = all_collections

    # Initialize client
    client = ZwiftWorkoutClient(cache_db_path=args.cache_path)

    # Seed workouts
    print("\n🌱 Seeding Zwift workout cache...\n")
    total_seeded = 0

    for collection_name, workouts in collections_to_seed.items():
        print(f"📦 Collection: {collection_name}")
        print(f"   Workouts: {len(workouts)}\n")

        for i, workout in enumerate(workouts, start=1):
            print(f"   [{i}/{len(workouts)}] {workout.name}")
            print(
                f"      Category: {workout.category.value} | TSS: {workout.tss} | Duration: {workout.duration_minutes}min"
            )
            print(f"      Segments: {len(workout.segments)}")

            # Save to cache
            client._save_workout_to_cache(workout)
            print("      ✅ Cached")

            total_seeded += 1

        print()

    print("=" * 80)
    print(f"✅ Seeded {total_seeded} workouts from {len(collections_to_seed)} collection(s)")
    print("=" * 80)

    # Show cache stats
    print("\n📊 Cache Statistics:")
    stats = client.get_cache_stats()
    print(f"Total workouts: {stats['total_workouts']}")
    if stats.get("by_category"):
        print("\nBy category:")
        for category, count in sorted(
            stats["by_category"].items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  {category:20s}: {count:3d} workouts")
    print()


if __name__ == "__main__":
    main()
