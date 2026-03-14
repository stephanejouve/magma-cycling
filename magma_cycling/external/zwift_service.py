"""Façade service for all Zwift workout operations.

Centralises populate, search, seed and utility operations behind a single
entry-point that never prints — all formatting is left to CLI scripts.
"""

import logging
import sqlite3
import time
from collections.abc import Callable
from pathlib import Path

import requests
from pydantic import BaseModel

from magma_cycling.external.zwift_client import ZwiftWorkoutClient
from magma_cycling.external.zwift_collections import KNOWN_COLLECTIONS
from magma_cycling.external.zwift_converter import ZwiftWorkoutConverter
from magma_cycling.external.zwift_models import (
    WorkoutMatch,
    WorkoutSearchCriteria,
    ZwiftWorkout,
)
from magma_cycling.external.zwift_scraper import ZwiftWorkoutScraper
from magma_cycling.external.zwift_seed_data import get_all_seed_workouts

logger = logging.getLogger(__name__)

# Rate limiting between HTTP requests (seconds)
REQUEST_DELAY_SECONDS = 1.5


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


class PopulateResult(BaseModel):
    """Result of populating a single collection."""

    collection: str
    total_found: int = 0
    cached_count: int = 0
    skipped_count: int = 0
    errors: list[str] = []


# ---------------------------------------------------------------------------
# Service façade
# ---------------------------------------------------------------------------


class ZwiftService:
    """Façade for all Zwift workout operations.

    Orchestrates client, scraper, converter and seed data without any
    print statements — callers handle presentation.
    """

    BASE_URL = "https://whatsonzwift.com"

    def __init__(
        self,
        cache_db_path: Path | None = None,
        cache_ttl_days: int = 60,
    ):
        self._client = ZwiftWorkoutClient(
            cache_db_path=cache_db_path,
            cache_ttl_days=cache_ttl_days,
        )
        self._scraper = ZwiftWorkoutScraper()
        self._converter = ZwiftWorkoutConverter()
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/91.0.4472.124 Safari/537.36"
                )
            }
        )
        self._seen_names: set[str] = set()
        self._load_existing_names()

    def _load_existing_names(self):
        """Load existing workout names from cache for deduplication."""
        try:
            conn = sqlite3.connect(self._client.cache_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM workouts")
            for row in cursor.fetchall():
                self._seen_names.add(row[0].lower())
            conn.close()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Populate
    # ------------------------------------------------------------------

    def populate_collection(
        self,
        slug: str,
        *,
        dry_run: bool = False,
        on_workout: Callable | None = None,
    ) -> PopulateResult:
        """Fetch and cache all workouts from a whatsonzwift.com collection.

        Args:
            slug: Collection URL slug (e.g. ``"zwift-camp-baseline"``).
            dry_run: Parse without saving to cache.
            on_workout: Optional callback ``(index, total, workout_or_none)``
                        for progress reporting.

        Returns:
            PopulateResult with counters and any errors.
        """
        result = PopulateResult(collection=slug)
        collection_url = f"{self.BASE_URL}/workouts/{slug}"

        try:
            response = self._session.get(collection_url, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            result.errors.append(f"Failed to fetch collection: {exc}")
            return result

        workout_metadata = self._scraper.parse_workout_metadata_from_listing(
            response.text, self.BASE_URL
        )
        result.total_found = len(workout_metadata)

        if not workout_metadata:
            return result

        for i, meta in enumerate(workout_metadata, start=1):
            name_lower = meta["name"].lower()

            # Deduplication
            if name_lower in self._seen_names:
                result.skipped_count += 1
                continue

            # Rate limiting
            time.sleep(REQUEST_DELAY_SECONDS)

            try:
                resp = self._session.get(meta["url"], timeout=15)
                resp.raise_for_status()
                workout = self._scraper.parse_workout_detail(resp.text, meta["url"])
            except requests.RequestException as exc:
                result.errors.append(f"{meta['name']}: {exc}")
                if on_workout:
                    on_workout(i, result.total_found, None)
                continue

            if workout:
                if not dry_run:
                    self._client._save_workout_to_cache(workout)
                self._seen_names.add(name_lower)
                result.cached_count += 1
            else:
                result.errors.append(f"{meta['name']}: failed to parse")

            if on_workout:
                on_workout(i, result.total_found, workout)

        return result

    def populate_collections(
        self,
        slugs: list[str],
        *,
        dry_run: bool = False,
        on_workout: Callable | None = None,
    ) -> dict[str, PopulateResult]:
        """Populate cache from multiple collections.

        Returns:
            Dict mapping slug → PopulateResult.
        """
        return {
            slug: self.populate_collection(slug, dry_run=dry_run, on_workout=on_workout)
            for slug in slugs
        }

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_workouts(self, criteria: WorkoutSearchCriteria) -> list[WorkoutMatch]:
        """Search cached workouts matching *criteria*."""
        return self._client.search_workouts(criteria)

    def search_catalog(
        self,
        session_type: str | None = None,
        duration_target: int | None = None,
        tss_target: int | None = None,
        pattern: str | None = None,
        limit: int = 5,
    ) -> list[ZwiftWorkout]:
        """Search the workout catalog with flexible filters.

        Delegates to client's search_catalog for pattern-aware queries.
        """
        return self._client.search_catalog(
            session_type=session_type,
            duration_target=duration_target,
            tss_target=tss_target,
            pattern=pattern,
            limit=limit,
        )

    def mark_workout_used(self, workout: ZwiftWorkout, date: str) -> None:
        """Mark a workout as used on *date* (ISO format)."""
        self._client.mark_workout_used(workout, date)

    # ------------------------------------------------------------------
    # Seed
    # ------------------------------------------------------------------

    def seed_collection(self, name: str | None = None) -> int:
        """Seed cache from curated offline data.

        Args:
            name: Specific collection name, or ``None`` for all.

        Returns:
            Number of workouts seeded.

        Raises:
            KeyError: If *name* is not a known seed collection.
        """
        all_collections = get_all_seed_workouts()

        if name is not None:
            if name not in all_collections:
                raise KeyError(
                    f"Collection '{name}' not found. " f"Available: {', '.join(all_collections)}"
                )
            collections = {name: all_collections[name]}
        else:
            collections = all_collections

        count = 0
        for workouts in collections.values():
            for workout in workouts:
                self._client._save_workout_to_cache(workout)
                count += 1
        return count

    def list_seed_collections(self) -> dict[str, list[ZwiftWorkout]]:
        """Return all available seed collections."""
        return get_all_seed_workouts()

    # ------------------------------------------------------------------
    # Stats & utilities
    # ------------------------------------------------------------------

    def get_cache_stats(self) -> dict:
        """Return cache statistics dict."""
        return self._client.get_cache_stats()

    def create_sample_workout(self) -> ZwiftWorkout:
        """Create the sample *Flat Out Fast* workout."""
        return self._converter.create_sample_workout()

    def to_intervals_format(self, workout: ZwiftWorkout) -> str:
        """Convert *workout* to Intervals.icu text format."""
        return self._converter.workout_to_intervals_text(workout)

    def validate_wahoo(self, text: str) -> tuple[bool, list[str]]:
        """Validate Wahoo ELEMNT compatibility of *text*."""
        return self._converter.validate_wahoo_compatibility(text)

    def get_known_collections(self) -> dict[str, str]:
        """Return the registry of known web collections."""
        return dict(KNOWN_COLLECTIONS)
