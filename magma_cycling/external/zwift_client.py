"""Client for fetching and caching Zwift workout data from whatsonzwift.com."""

import logging
from pathlib import Path

import requests

from magma_cycling.external.client.cache import (
    cleanup_expired_cache,
)
from magma_cycling.external.client.cache import get_cache_stats as _get_cache_stats
from magma_cycling.external.client.cache import (
    init_cache_db,
    load_workouts_from_cache,
)
from magma_cycling.external.client.cache import mark_workout_used as _mark_workout_used
from magma_cycling.external.client.cache import (
    save_workout_to_cache,
    search_catalog_db,
)
from magma_cycling.external.client.search import (
    calculate_match_score,
    get_categories_for_session_type,
    is_recently_used,
)
from magma_cycling.external.zwift_models import (
    WorkoutMatch,
    WorkoutSearchCriteria,
    ZwiftCategory,
    ZwiftWorkout,
)
from magma_cycling.external.zwift_scraper import ZwiftWorkoutScraper

logger = logging.getLogger(__name__)


class ZwiftWorkoutClient:
    """Client for fetching and caching Zwift workouts from whatsonzwift.com.

    This client scrapes workout data from whatsonzwift.com and caches results
    in a local SQLite database with a 60-day TTL to minimize web requests.

    Attributes:
        cache_db_path: Path to SQLite cache database
        cache_ttl_days: Cache TTL in days (default: 60)
        base_url: Base URL for whatsonzwift.com
    """

    BASE_URL = "https://whatsonzwift.com"
    WORKOUTS_PATH = "/workouts"
    DEFAULT_CACHE_TTL_DAYS = 60

    def __init__(
        self,
        cache_db_path: Path | None = None,
        cache_ttl_days: int = DEFAULT_CACHE_TTL_DAYS,
    ):
        """Initialize the Zwift workout client.

        Args:
            cache_db_path: Path to SQLite cache database. If None, uses default location
                          in project data directory.
            cache_ttl_days: Number of days to cache workout data (default: 60)
        """
        if cache_db_path is None:
            # Default to data directory in project
            cache_db_path = Path.home() / "data" / "cache" / "zwift_workouts.db"

        self.cache_db_path = cache_db_path
        self.cache_ttl_days = cache_ttl_days
        self.base_url = self.BASE_URL
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            }
        )

        # Initialize cache database
        init_cache_db(self.cache_db_path)

    def _fetch_workout_from_web(self, url: str) -> ZwiftWorkout | None:
        """Fetch a single workout from whatsonzwift.com and parse it.

        Args:
            url: Full URL to workout page

        Returns:
            ZwiftWorkout object if successful, None otherwise
        """
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            workout = ZwiftWorkoutScraper.parse_workout_detail(response.text, url)
            if workout:
                logger.info(f"Fetched workout from web: {workout.name}")
            else:
                logger.warning(f"Could not parse workout from {url}")
            return workout

        except requests.RequestException as e:
            logger.error(f"Failed to fetch workout from {url}: {e}")
            return None

    def _save_workout_to_cache(self, workout: ZwiftWorkout) -> None:
        """Save workout to SQLite cache.

        Args:
            workout: ZwiftWorkout to cache.
        """
        save_workout_to_cache(self.cache_db_path, workout)

    def search_workouts(
        self,
        criteria: WorkoutSearchCriteria,
        force_refresh: bool = False,
    ) -> list[WorkoutMatch]:
        """Search for workouts matching criteria.

        Args:
            criteria: Search criteria (TSS, type, duration, etc.)
            force_refresh: If True, bypass cache and fetch from web

        Returns:
            List of WorkoutMatch objects sorted by relevance score
        """
        # Clean up expired cache entries
        cleanup_expired_cache(self.cache_db_path, self.cache_ttl_days)

        # Determine which Zwift categories map to the requested session type
        target_categories = get_categories_for_session_type(criteria.session_type)

        # Calculate TSS range from target and tolerance
        tss_tolerance_abs = int(criteria.tss_target * criteria.tss_tolerance / 100)
        tss_min = max(0, criteria.tss_target - tss_tolerance_abs)
        tss_max = min(500, criteria.tss_target + tss_tolerance_abs)

        # Load workouts from cache
        all_workouts = []
        for category in target_categories:
            workouts = load_workouts_from_cache(
                self.cache_db_path,
                category=category,
                tss_min=tss_min,
                tss_max=tss_max,
            )
            all_workouts.extend(workouts)

        logger.info(
            f"Found {len(all_workouts)} cached workouts for {criteria.session_type} "
            f"with TSS {tss_min}-{tss_max}"
        )

        # Score and rank workouts
        matches = []
        for workout in all_workouts:
            if not workout.matches_criteria(criteria):
                continue

            # Calculate match score (0-100)
            score = calculate_match_score(workout, criteria)

            # Check if recently used (for diversity)
            recently_used = is_recently_used(workout, criteria.diversity_window_days)

            # Skip if recently used and exclusion requested
            if recently_used and criteria.exclude_recent:
                logger.debug(f"Skipping recently used workout: {workout.name}")
                continue

            matches.append(
                WorkoutMatch(
                    workout=workout,
                    score=score,
                    tss_delta=abs(workout.tss - criteria.tss_target),
                    type_match=ZwiftCategory.to_session_type(workout.category)
                    == criteria.session_type,
                    recently_used=recently_used,
                )
            )

        # Sort by score (highest first)
        matches.sort(key=lambda m: m.score, reverse=True)

        logger.info(f"Matched {len(matches)} workouts after filtering and scoring")
        return matches

    def mark_workout_used(self, workout: ZwiftWorkout, used_date: str):
        """Mark workout as used on a specific date.

        Updates usage statistics in cache for diversity tracking.

        Args:
            workout: Workout that was used
            used_date: ISO date string (YYYY-MM-DD)
        """
        _mark_workout_used(self.cache_db_path, workout.url, used_date)
        logger.info(f"Marked workout '{workout.name}' as used on {used_date}")

    def search_catalog(
        self,
        session_type: str | None = None,
        duration_target: int | None = None,
        tss_target: int | None = None,
        pattern: str | None = None,
        limit: int = 5,
    ) -> list[ZwiftWorkout]:
        """Search the workout catalog with flexible filters.

        Args:
            session_type: 3-letter session type (END, INT, FTP, REC)
            duration_target: Target duration in minutes (±15 tolerance)
            tss_target: Target TSS (±10 tolerance)
            pattern: Structural pattern filter
            limit: Maximum results to return

        Returns:
            List of matching ZwiftWorkout objects
        """
        categories = None
        if session_type:
            categories = get_categories_for_session_type(session_type)

        return search_catalog_db(
            self.cache_db_path,
            categories=categories,
            duration_target=duration_target,
            tss_target=tss_target,
            pattern=pattern,
            limit=limit,
        )

    def get_cache_stats(self) -> dict:
        """Get statistics about the workout cache.

        Returns:
            Dictionary with cache statistics (total workouts, by category, etc.)
        """
        return _get_cache_stats(self.cache_db_path)
