#!/usr/bin/env python3
"""Seed Zwift Workouts - Load curated workouts into cache.

Usage:
    poetry run seed-zwift-workouts
    poetry run seed-zwift-workouts --collection zwift-camp-baseline-2025
    poetry run seed-zwift-workouts --list
"""

import argparse
import sys
from pathlib import Path

from magma_cycling.external.zwift_service import ZwiftService
from magma_cycling.utils.cli import cli_main


@cli_main
def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Seed Zwift workout cache from curated collections",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --collection zwift-camp-baseline-2025
  %(prog)s --list
        """,
    )

    parser.add_argument(
        "--collection", dest="collection", help="Collection name to seed (default: all)"
    )
    parser.add_argument(
        "--list", dest="list_collections", action="store_true", help="List available collections"
    )
    parser.add_argument(
        "--cache-path", dest="cache_path", type=Path, help="Custom cache database path"
    )

    args = parser.parse_args()

    service = ZwiftService(cache_db_path=args.cache_path)

    # List mode
    if args.list_collections:
        collections = service.list_seed_collections()
        print("\n📚 Available Seed Collections:\n")
        for name, workouts in collections.items():
            print(f"  {name}")
            print(f"    Workouts: {len(workouts)}")
            for w in workouts:
                print(f"      - {w.name} ({w.duration_minutes}min, {w.tss} TSS)")
        print()
        return

    # Seed mode
    print("\n🌱 Seeding Zwift workout cache...\n")

    try:
        count = service.seed_collection(args.collection)
    except KeyError as exc:
        print(f"❌ Error: {exc}")
        sys.exit(1)

    print(f"\n{'=' * 80}")
    print(f"✅ Seeded {count} workouts")
    print("=" * 80)

    # Cache stats
    stats = service.get_cache_stats()
    print(f"\n📊 Cache: {stats['total_workouts']} workouts")
    if stats.get("by_category"):
        for category, cnt in sorted(stats["by_category"].items(), key=lambda x: x[1], reverse=True):
            print(f"  {category:20s}: {cnt:3d} workouts")
    print()


if __name__ == "__main__":
    main()
