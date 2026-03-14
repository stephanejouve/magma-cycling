#!/usr/bin/env python3
"""
Populate Zwift Workout Cache - Seed database from whatsonzwift.com collections.

This script fetches workouts from specific Zwift collections and populates the
local SQLite cache for offline searching and matching.

Usage:
    # Populate from Zwift Camp Baseline collection
    poetry run populate-zwift-cache --collection zwift-camp-baseline

    # Populate from multiple collections
    poetry run populate-zwift-cache --collection zwift-camp-baseline --collection ftp-builder

    # Populate from all known collections
    poetry run populate-zwift-cache --all

    # Dry-run (don't save to cache)
    poetry run populate-zwift-cache --collection zwift-camp-baseline --dry-run

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
import time
from pathlib import Path

import requests

from magma_cycling.external.zwift_client import ZwiftWorkoutClient
from magma_cycling.external.zwift_scraper import ZwiftWorkoutScraper

# Rate limiting
REQUEST_DELAY_SECONDS = 1.5  # Delay between HTTP requests

# Known workout collections on whatsonzwift.com
KNOWN_COLLECTIONS = {
    # Workout categories (direct listings)
    "endurance": "Endurance (Z2 base building)",
    "sweet-spot": "Sweet Spot (88-93% FTP)",
    "threshold": "Threshold (FTP/seuil)",
    "vo2-max": "VO2 Max (high-intensity intervals)",
    "recovery": "Recovery (active recovery)",
    "sprinting": "Sprinting (sprint-specific)",
    "climbing": "Climbing (hill-specific training)",
    "ftp-tests": "FTP Tests (testing protocols)",
    # Duration-based collections
    "30-minutes-to-burn": "30 minutes to burn (short workouts)",
    "30-60-minutes-to-burn": "30-60 minutes to burn",
    "60-90-minutes-to-burn": "60-90 minutes to burn",
    "90plus-minutes-to-burn": "90+ minutes to burn (long workouts)",
    # Training plans
    "build-me-up": "Build Me Up (progressive loading)",
    "ftp-builder": "FTP Builder (structured training)",
    "active-offseason": "Active Offseason (recovery phase)",
    "gravel-grinder": "Gravel Grinder (endurance focus)",
    "gran-fondo": "Gran Fondo (endurance/distance)",
    "crit-crusher": "Crit Crusher (race prep)",
    "back-to-fitness": "Back To Fitness (return to form)",
    "zwift-camp-baseline": "Zwift Camp: Baseline (test workouts)",
}


class ZwiftCachePopulator:
    """Populate Zwift workout cache from web scraping.

    Attributes:
        client: ZwiftWorkoutClient instance
        scraper: ZwiftWorkoutScraper instance
        dry_run: If True, don't save to cache
        base_url: Base URL for whatsonzwift.com
    """

    BASE_URL = "https://whatsonzwift.com"

    def __init__(self, cache_db_path: Path | None = None, dry_run: bool = False):
        """Initialize the cache populator.

        Args:
            cache_db_path: Optional custom cache database path
            dry_run: If True, don't save to cache
        """
        self.client = ZwiftWorkoutClient(cache_db_path=cache_db_path)
        self.scraper = ZwiftWorkoutScraper()
        self.dry_run = dry_run
        self.seen_names: set[str] = set()  # Deduplication
        self._load_existing_names()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            }
        )

    def _load_existing_names(self):
        """Load existing workout names from cache for deduplication."""
        try:
            import sqlite3

            conn = sqlite3.connect(self.client.cache_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM workouts")
            for row in cursor.fetchall():
                self.seen_names.add(row[0].lower())
            conn.close()
        except Exception:
            pass

    def populate_from_collection(self, collection_slug: str) -> int:
        """Fetch and cache all workouts from a collection.

        Args:
            collection_slug: Collection URL slug (e.g., "zwift-camp-baseline")

        Returns:
            Number of workouts successfully cached
        """
        collection_url = f"{self.BASE_URL}/workouts/{collection_slug}"
        print(f"\n🔍 Fetching collection: {collection_slug}")
        print(f"   URL: {collection_url}")

        try:
            # Fetch collection listing page
            response = self.session.get(collection_url, timeout=15)
            response.raise_for_status()

            # Parse workout list from collection
            workout_metadata = self.scraper.parse_workout_metadata_from_listing(
                response.text, self.BASE_URL
            )

            if not workout_metadata:
                print("   ❌ No workouts found in collection")
                return 0

            print(f"   ✅ Found {len(workout_metadata)} workouts")

            # Fetch and cache each workout
            cached_count = 0
            skipped_count = 0
            failed_names = []
            for i, meta in enumerate(workout_metadata, start=1):
                name_lower = meta["name"].lower()

                # Deduplication check
                if name_lower in self.seen_names:
                    skipped_count += 1
                    continue

                print(f"\n   [{i}/{len(workout_metadata)}] {meta['name']}")

                # Rate limiting
                time.sleep(REQUEST_DELAY_SECONDS)

                # Fetch individual workout page
                try:
                    workout_response = self.session.get(meta["url"], timeout=15)
                    workout_response.raise_for_status()

                    # Parse workout details
                    workout = self.scraper.parse_workout_detail(workout_response.text, meta["url"])

                    if workout:
                        if not self.dry_run:
                            self.client._save_workout_to_cache(workout)
                        self.seen_names.add(name_lower)
                        cached_count += 1
                        pattern_str = f" [{workout.pattern}]" if workout.pattern else ""
                        segs = len(workout.segments)
                        print(
                            f"      ✅ {workout.tss} TSS | "
                            f"{workout.duration_minutes}min | "
                            f"{segs} segments{pattern_str}"
                        )
                    else:
                        failed_names.append(meta["name"])
                        print("      ⚠️  Failed to parse")

                except requests.RequestException as e:
                    failed_names.append(meta["name"])
                    print(f"      ❌ Failed to fetch: {e}")
                    continue

            print(f"\n📊 Summary: {cached_count} cached, {skipped_count} duplicates skipped")
            if failed_names:
                print(f"   ⚠️  Failed ({len(failed_names)}): {', '.join(failed_names[:5])}")
            return cached_count

        except requests.RequestException as e:
            print(f"   ❌ Failed to fetch collection: {e}")
            return 0

    def populate_from_collections(self, collection_slugs: list[str]) -> dict[str, int]:
        """Populate cache from multiple collections.

        Args:
            collection_slugs: List of collection URL slugs

        Returns:
            Dict mapping collection slug to number of workouts cached
        """
        results = {}
        total_cached = 0

        for collection_slug in collection_slugs:
            count = self.populate_from_collection(collection_slug)
            results[collection_slug] = count
            total_cached += count

        print("\n" + "=" * 80)
        print(f"🎯 Total: {total_cached} workouts cached from {len(collection_slugs)} collections")
        print("=" * 80)

        return results


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Populate Zwift workout cache from whatsonzwift.com",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Known Collections:
{chr(10).join(f'  {slug:25s} - {desc}' for slug, desc in KNOWN_COLLECTIONS.items())}

Examples:
  # Single collection
  %(prog)s --collection zwift-camp-baseline

  # Multiple collections
  %(prog)s --collection zwift-camp-baseline --collection ftp-builder

  # All known collections
  %(prog)s --all

  # Dry-run (no caching)
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

    # Initialize populator and run
    populator = ZwiftCachePopulator(cache_db_path=args.cache_path, dry_run=args.dry_run)

    populator.populate_from_collections(collections)

    # Show cache stats after population
    if not args.dry_run:
        print("\n" + "=" * 80)
        print("📊 Cache Statistics After Population:")
        print("=" * 80)
        stats = populator.client.get_cache_stats()
        print(f"Total workouts: {stats['total_workouts']}")
        if stats.get("by_category"):
            print("\nBy category:")
            for category, count in sorted(
                stats["by_category"].items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  {category:20s}: {count:3d} workouts")


if __name__ == "__main__":
    main()
