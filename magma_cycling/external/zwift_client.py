"""Client for fetching and caching Zwift workout data from whatsonzwift.com."""

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import requests

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
        self._init_cache_db()

    def _init_cache_db(self):
        """Initialize SQLite cache database with schema."""
        self.cache_db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        # Create workouts table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                tss INTEGER NOT NULL,
                url TEXT UNIQUE NOT NULL,
                description TEXT,
                segments_json TEXT,
                cached_at TEXT NOT NULL,
                last_used_date TEXT,
                usage_count INTEGER DEFAULT 0
            )
        """
        )

        # Create index on category and TSS for faster searches
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_category_tss
            ON workouts(category, tss)
        """
        )

        # Create index on cached_at for TTL cleanup
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cached_at
            ON workouts(cached_at)
        """
        )

        # Migrate: add pattern column if missing
        cursor.execute("PRAGMA table_info(workouts)")
        columns = {row[1] for row in cursor.fetchall()}
        if "pattern" not in columns:
            cursor.execute("ALTER TABLE workouts ADD COLUMN pattern TEXT")

        conn.commit()
        conn.close()

        logger.info(f"Initialized Zwift workout cache at {self.cache_db_path}")

    def _cleanup_expired_cache(self):
        """Remove cached workouts older than TTL."""
        expiry_date = datetime.now() - timedelta(days=self.cache_ttl_days)
        expiry_str = expiry_date.isoformat()

        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM workouts WHERE cached_at < ?", (expiry_str,))
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired workout(s) from cache")

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

    def _save_workout_to_cache(self, workout: ZwiftWorkout):
        """Save workout to SQLite cache.

        Args:
            workout: ZwiftWorkout to cache
        """
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        # Convert segments to JSON for storage
        segments_json = workout.model_dump_json()

        cursor.execute(
            """
            INSERT OR REPLACE INTO workouts
            (name, category, duration_minutes, tss, url, description,
             segments_json, cached_at, last_used_date, usage_count, pattern)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                workout.name,
                workout.category.value,
                workout.duration_minutes,
                workout.tss,
                workout.url,
                workout.description,
                segments_json,
                datetime.now().isoformat(),
                workout.last_used_date,
                workout.usage_count,
                workout.pattern,
            ),
        )

        conn.commit()
        conn.close()

        logger.debug(f"Cached workout: {workout.name}")

    def _load_workouts_from_cache(
        self,
        category: ZwiftCategory | None = None,
        tss_min: int | None = None,
        tss_max: int | None = None,
    ) -> list[ZwiftWorkout]:
        """Load workouts from cache with optional filters.

        Args:
            category: Filter by Zwift category
            tss_min: Minimum TSS
            tss_max: Maximum TSS

        Returns:
            List of cached ZwiftWorkout objects
        """
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        # Build query with filters
        query = "SELECT segments_json FROM workouts WHERE 1=1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category.value)

        if tss_min is not None:
            query += " AND tss >= ?"
            params.append(tss_min)

        if tss_max is not None:
            query += " AND tss <= ?"
            params.append(tss_max)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        workouts = []
        for row in rows:
            try:
                workout = ZwiftWorkout.model_validate_json(row[0])
                workouts.append(workout)
            except Exception as e:
                logger.warning(f"Failed to deserialize cached workout: {e}")

        return workouts

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
        self._cleanup_expired_cache()

        # Determine which Zwift categories map to the requested session type
        target_categories = self._get_categories_for_session_type(criteria.session_type)

        # Calculate TSS range from target and tolerance
        tss_tolerance_abs = int(criteria.tss_target * criteria.tss_tolerance / 100)
        tss_min = max(0, criteria.tss_target - tss_tolerance_abs)
        tss_max = min(500, criteria.tss_target + tss_tolerance_abs)

        # Load workouts from cache
        all_workouts = []
        for category in target_categories:
            workouts = self._load_workouts_from_cache(
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
            score = self._calculate_match_score(workout, criteria)

            # Check if recently used (for diversity)
            recently_used = self._is_recently_used(workout, criteria.diversity_window_days)

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

    def _get_categories_for_session_type(self, session_type: str) -> list[ZwiftCategory]:
        """Map session type to relevant Zwift categories.

        Args:
            session_type: 3-letter session type code

        Returns:
            List of relevant ZwiftCategory values
        """
        # Reverse mapping from session types to Zwift categories
        mapping = {
            "END": [ZwiftCategory.ENDURANCE, ZwiftCategory.TEMPO],
            "INT": [ZwiftCategory.INTERVALS, ZwiftCategory.VO2MAX],
            "FTP": [ZwiftCategory.FTP, ZwiftCategory.THRESHOLD],
            "SPR": [ZwiftCategory.SPRINT],
            "CLM": [ZwiftCategory.CLIMBING],
            "REC": [ZwiftCategory.RECOVERY],
            "MIX": [ZwiftCategory.MIXED],
        }

        # Default to mixed if not found
        return mapping.get(session_type, [ZwiftCategory.MIXED])

    def _calculate_match_score(
        self,
        workout: ZwiftWorkout,
        criteria: WorkoutSearchCriteria,
    ) -> float:
        """Calculate match quality score (0-100) for a workout.

        Scoring factors:
        - TSS accuracy (40 points): Closer to target = higher score
        - Type match (30 points): Exact category match = full points
        - Duration fit (20 points): Within constraints = full points
        - Novelty (10 points): Less used = higher score

        Args:
            workout: Workout to score
            criteria: Search criteria

        Returns:
            Score from 0.0 to 100.0
        """
        score = 0.0

        # TSS accuracy (40 points)
        tss_diff = abs(workout.tss - criteria.tss_target)
        tss_tolerance = criteria.tss_target * criteria.tss_tolerance / 100
        if tss_diff == 0:
            score += 40.0
        elif tss_diff <= tss_tolerance:
            # Linear decay within tolerance
            score += 40.0 * (1.0 - tss_diff / tss_tolerance)

        # Type match (30 points)
        if ZwiftCategory.to_session_type(workout.category) == criteria.session_type:
            score += 30.0

        # Duration fit (20 points)
        duration_ok = True
        if criteria.duration_min and workout.duration_minutes < criteria.duration_min:
            duration_ok = False
        if criteria.duration_max and workout.duration_minutes > criteria.duration_max:
            duration_ok = False
        if duration_ok:
            score += 20.0

        # Novelty bonus (10 points) - less used = higher score
        # Max usage_count of 10 gives 0 points, 0 gives 10 points
        novelty = max(0, 10 - workout.usage_count)
        score += novelty

        return min(100.0, score)

    def _is_recently_used(self, workout: ZwiftWorkout, window_days: int) -> bool:
        """Check if workout was used within the diversity window.

        Args:
            workout: Workout to check
            window_days: Diversity window in days

        Returns:
            True if used within window, False otherwise
        """
        if not workout.last_used_date:
            return False

        try:
            last_used = datetime.fromisoformat(workout.last_used_date)
            cutoff = datetime.now() - timedelta(days=window_days)
            return last_used > cutoff
        except ValueError:
            logger.warning(f"Invalid last_used_date format: {workout.last_used_date}")
            return False

    def mark_workout_used(self, workout: ZwiftWorkout, used_date: str):
        """Mark workout as used on a specific date.

        Updates usage statistics in cache for diversity tracking.

        Args:
            workout: Workout that was used
            used_date: ISO date string (YYYY-MM-DD)
        """
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE workouts
            SET last_used_date = ?,
                usage_count = usage_count + 1
            WHERE url = ?
        """,
            (used_date, workout.url),
        )

        conn.commit()
        conn.close()

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
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        query = "SELECT segments_json FROM workouts WHERE 1=1"
        params: list = []

        if session_type:
            categories = self._get_categories_for_session_type(session_type)
            placeholders = ",".join("?" for _ in categories)
            query += f" AND category IN ({placeholders})"
            params.extend(c.value for c in categories)

        if duration_target is not None:
            query += " AND duration_minutes BETWEEN ? AND ?"
            params.extend([duration_target - 15, duration_target + 15])

        if tss_target is not None:
            query += " AND tss BETWEEN ? AND ?"
            params.extend([tss_target - 10, tss_target + 10])

        if pattern:
            query += " AND pattern = ?"
            params.append(pattern)

        query += " ORDER BY usage_count ASC, tss DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        workouts = []
        for row in rows:
            try:
                workouts.append(ZwiftWorkout.model_validate_json(row[0]))
            except Exception as e:
                logger.warning(f"Failed to deserialize workout: {e}")

        return workouts

    def get_cache_stats(self) -> dict:
        """Get statistics about the workout cache.

        Returns:
            Dictionary with cache statistics (total workouts, by category, etc.)
        """
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        # Total workouts
        cursor.execute("SELECT COUNT(*) FROM workouts")
        total = cursor.fetchone()[0]

        # By category
        cursor.execute(
            """
            SELECT category, COUNT(*) as count
            FROM workouts
            GROUP BY category
            ORDER BY count DESC
        """
        )
        by_category = {row[0]: row[1] for row in cursor.fetchall()}

        # Cache age
        cursor.execute("SELECT MIN(cached_at), MAX(cached_at) FROM workouts")
        oldest, newest = cursor.fetchone()

        conn.close()

        return {
            "total_workouts": total,
            "by_category": by_category,
            "oldest_cached": oldest,
            "newest_cached": newest,
            "cache_path": str(self.cache_db_path),
        }
