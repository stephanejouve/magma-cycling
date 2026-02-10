"""Workout diversity tracking and recommendation system.

Manages workout history to ensure variety in training sessions by tracking
usage of external workouts (e.g., Zwift) and enforcing rotation windows.

Metadata:
    Created: 2026-02-10
    Author: Claude Code + Stéphane Jouve
    Category: INTELLIGENCE + EXTERNAL
    Status: Development (Sprint 2 Phase 2)
    Priority: P1
    Version: 1.0.0
    Sprint: Zwift Integration S2
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class WorkoutUsage:
    """Record of a workout being used in training.

    Attributes:
        workout_url: URL or identifier of the workout
        workout_name: Human-readable workout name
        date_used: ISO date string (YYYY-MM-DD)
        session_id: Session ID where used (e.g., "S080-02")
        source: Source of workout (e.g., "whatsonzwift.com")
        category: Workout category (e.g., "FTP", "VO2Max")
        tss: Training Stress Score
    """

    workout_url: str
    workout_name: str
    date_used: str  # ISO date YYYY-MM-DD
    session_id: str
    source: str = "whatsonzwift.com"
    category: str | None = None
    tss: int | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class WorkoutDiversityTracker:
    """Track and enforce workout diversity across training sessions.

    Maintains workout_history in intelligence.json to ensure variety
    through rotation windows and usage statistics.

    Attributes:
        intelligence_file: Path to intelligence.json
        rotation_window_days: Days to enforce diversity (default: 21)
        max_repetition_rate: Maximum allowed repetition rate (default: 0.4 = 40%)
    """

    DEFAULT_ROTATION_WINDOW = 21  # days
    DEFAULT_MAX_REPETITION_RATE = 0.40  # 40%

    def __init__(
        self,
        intelligence_file: Path | None = None,
        rotation_window_days: int = DEFAULT_ROTATION_WINDOW,
        max_repetition_rate: float = DEFAULT_MAX_REPETITION_RATE,
    ):
        """Initialize workout diversity tracker.

        Args:
            intelligence_file: Path to intelligence.json (default: ~/data/intelligence.json)
            rotation_window_days: Days to check for workout diversity
            max_repetition_rate: Maximum allowed repetition rate (0.0-1.0)
        """
        if intelligence_file is None:
            intelligence_file = Path.home() / "data" / "intelligence.json"

        self.intelligence_file = intelligence_file
        self.rotation_window_days = rotation_window_days
        self.max_repetition_rate = max_repetition_rate

        # Load existing intelligence data
        self._load_intelligence()

    def _load_intelligence(self):
        """Load intelligence.json and initialize workout_history if needed."""
        if not self.intelligence_file.exists():
            logger.warning(f"Intelligence file not found: {self.intelligence_file}")
            self.intelligence_data = {
                "learnings": {},
                "patterns": {},
                "adaptations": {},
                "workout_history": [],
            }
            return

        with open(self.intelligence_file, encoding="utf-8") as f:
            self.intelligence_data = json.load(f)

        # Initialize workout_history if not present
        if "workout_history" not in self.intelligence_data:
            self.intelligence_data["workout_history"] = []
            logger.info("Initialized workout_history in intelligence.json")

    def _save_intelligence(self):
        """Save intelligence data back to JSON file."""
        self.intelligence_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.intelligence_file, "w", encoding="utf-8") as f:
            json.dump(self.intelligence_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved intelligence data to {self.intelligence_file}")

    def record_workout_usage(self, usage: WorkoutUsage) -> None:
        """Record a workout being used in training.

        Args:
            usage: WorkoutUsage record to add
        """
        # Add to history
        self.intelligence_data["workout_history"].append(usage.to_dict())

        # Save immediately
        self._save_intelligence()

        logger.info(
            f"Recorded workout usage: {usage.workout_name} on {usage.date_used} "
            f"(session: {usage.session_id})"
        )

    def get_recent_usage(
        self, workout_url: str, window_days: int | None = None
    ) -> list[WorkoutUsage]:
        """Get recent usage of a specific workout within rotation window.

        Args:
            workout_url: URL of the workout to check
            window_days: Days to look back (default: use tracker's rotation_window_days)

        Returns:
            List of WorkoutUsage records within window
        """
        if window_days is None:
            window_days = self.rotation_window_days

        cutoff_date = date.today() - timedelta(days=window_days)
        recent_usages = []

        for usage_dict in self.intelligence_data["workout_history"]:
            if usage_dict["workout_url"] != workout_url:
                continue

            usage_date = date.fromisoformat(usage_dict["date_used"])
            if usage_date >= cutoff_date:
                recent_usages.append(WorkoutUsage(**usage_dict))

        return recent_usages

    def is_recently_used(self, workout_url: str, window_days: int | None = None) -> bool:
        """Check if a workout was used within rotation window.

        Args:
            workout_url: URL of the workout to check
            window_days: Days to look back (default: use tracker's rotation_window_days)

        Returns:
            True if used within window, False otherwise
        """
        recent = self.get_recent_usage(workout_url, window_days)
        return len(recent) > 0

    def get_workout_stats(self, workout_url: str) -> dict:
        """Get usage statistics for a workout.

        Args:
            workout_url: URL of the workout

        Returns:
            Dict with usage statistics (total_uses, last_used, first_used, recent_uses)
        """
        all_uses = [
            usage_dict
            for usage_dict in self.intelligence_data["workout_history"]
            if usage_dict["workout_url"] == workout_url
        ]

        if not all_uses:
            return {
                "total_uses": 0,
                "last_used": None,
                "first_used": None,
                "recent_uses": 0,
            }

        # Sort by date
        all_uses.sort(key=lambda u: u["date_used"])

        recent = self.get_recent_usage(workout_url)

        return {
            "total_uses": len(all_uses),
            "last_used": all_uses[-1]["date_used"],
            "first_used": all_uses[0]["date_used"],
            "recent_uses": len(recent),
        }

    def get_diversity_report(self, days: int = 30) -> dict:
        """Generate diversity report for recent training period.

        Args:
            days: Number of days to analyze

        Returns:
            Dict with diversity metrics
        """
        cutoff_date = date.today() - timedelta(days=days)

        # Get recent workouts
        recent_workouts = [
            usage_dict
            for usage_dict in self.intelligence_data["workout_history"]
            if date.fromisoformat(usage_dict["date_used"]) >= cutoff_date
        ]

        if not recent_workouts:
            return {
                "period_days": days,
                "total_sessions": 0,
                "unique_workouts": 0,
                "repetition_rate": 0.0,
                "most_used": [],
            }

        # Count by workout URL
        workout_counts = {}
        for usage_dict in recent_workouts:
            url = usage_dict["workout_url"]
            if url not in workout_counts:
                workout_counts[url] = {
                    "name": usage_dict["workout_name"],
                    "count": 0,
                }
            workout_counts[url]["count"] += 1

        # Calculate metrics
        total_sessions = len(recent_workouts)
        unique_workouts = len(workout_counts)
        repetition_rate = 1.0 - (unique_workouts / total_sessions) if total_sessions > 0 else 0.0

        # Get most used workouts
        most_used = sorted(
            [
                {"url": url, "name": data["name"], "count": data["count"]}
                for url, data in workout_counts.items()
            ],
            key=lambda x: x["count"],
            reverse=True,
        )[:5]

        return {
            "period_days": days,
            "total_sessions": total_sessions,
            "unique_workouts": unique_workouts,
            "repetition_rate": repetition_rate,
            "most_used": most_used,
            "diversity_ok": repetition_rate <= self.max_repetition_rate,
        }

    def get_available_workouts_for_diversity(self, all_workout_urls: list[str]) -> list[str]:
        """Filter workouts to only those respecting diversity constraints.

        Args:
            all_workout_urls: List of all available workout URLs

        Returns:
            List of workout URLs that can be used (not recently used)
        """
        available = []

        for url in all_workout_urls:
            if not self.is_recently_used(url):
                available.append(url)

        logger.info(
            f"Diversity filter: {len(available)}/{len(all_workout_urls)} workouts available "
            f"(excluding recently used within {self.rotation_window_days} days)"
        )

        return available
