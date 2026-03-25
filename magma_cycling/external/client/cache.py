"""SQLite cache operations for Zwift workout data."""

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from magma_cycling.external.zwift_models import ZwiftCategory, ZwiftWorkout

logger = logging.getLogger(__name__)


def init_cache_db(cache_db_path: Path) -> None:
    """Initialize SQLite cache database with schema.

    Args:
        cache_db_path: Path to SQLite cache database file.
    """
    cache_db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(cache_db_path)
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

    logger.info(f"Initialized Zwift workout cache at {cache_db_path}")


def cleanup_expired_cache(cache_db_path: Path, ttl_days: int) -> None:
    """Remove cached workouts older than TTL.

    Args:
        cache_db_path: Path to SQLite cache database file.
        ttl_days: Number of days after which cache entries expire.
    """
    expiry_date = datetime.now() - timedelta(days=ttl_days)
    expiry_str = expiry_date.isoformat()

    conn = sqlite3.connect(cache_db_path)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM workouts WHERE cached_at < ?", (expiry_str,))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()

    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} expired workout(s) from cache")


def save_workout_to_cache(cache_db_path: Path, workout: ZwiftWorkout) -> None:
    """Save workout to SQLite cache.

    Args:
        cache_db_path: Path to SQLite cache database file.
        workout: ZwiftWorkout to cache.
    """
    conn = sqlite3.connect(cache_db_path)
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


def load_workouts_from_cache(
    cache_db_path: Path,
    category: ZwiftCategory | None = None,
    tss_min: int | None = None,
    tss_max: int | None = None,
) -> list[ZwiftWorkout]:
    """Load workouts from cache with optional filters.

    Args:
        cache_db_path: Path to SQLite cache database file.
        category: Filter by Zwift category.
        tss_min: Minimum TSS.
        tss_max: Maximum TSS.

    Returns:
        List of cached ZwiftWorkout objects.
    """
    conn = sqlite3.connect(cache_db_path)
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


def mark_workout_used(cache_db_path: Path, workout_url: str, used_date: str) -> None:
    """Mark workout as used on a specific date.

    Updates usage statistics in cache for diversity tracking.

    Args:
        cache_db_path: Path to SQLite cache database file.
        workout_url: URL of the workout to mark.
        used_date: ISO date string (YYYY-MM-DD).
    """
    conn = sqlite3.connect(cache_db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE workouts
        SET last_used_date = ?,
            usage_count = usage_count + 1
        WHERE url = ?
    """,
        (used_date, workout_url),
    )

    conn.commit()
    conn.close()


def get_cache_stats(cache_db_path: Path) -> dict:
    """Get statistics about the workout cache.

    Args:
        cache_db_path: Path to SQLite cache database file.

    Returns:
        Dictionary with cache statistics (total workouts, by category, etc.).
    """
    conn = sqlite3.connect(cache_db_path)
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
        "cache_path": str(cache_db_path),
    }


def search_catalog_db(
    cache_db_path: Path,
    categories: list[ZwiftCategory] | None = None,
    duration_target: int | None = None,
    tss_target: int | None = None,
    pattern: str | None = None,
    limit: int = 5,
) -> list[ZwiftWorkout]:
    """Search the workout catalog in the database with flexible filters.

    Args:
        cache_db_path: Path to SQLite cache database file.
        categories: List of Zwift categories to filter by.
        duration_target: Target duration in minutes (±15 tolerance).
        tss_target: Target TSS (±10 tolerance).
        pattern: Structural pattern filter.
        limit: Maximum results to return.

    Returns:
        List of matching ZwiftWorkout objects.
    """
    conn = sqlite3.connect(cache_db_path)
    cursor = conn.cursor()

    query = "SELECT segments_json FROM workouts WHERE 1=1"
    params: list = []

    if categories:
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
