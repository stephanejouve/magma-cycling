"""ActivityTracker — track analyzed activities to avoid re-processing."""

import json
from datetime import date, datetime
from pathlib import Path


class ActivityTracker:
    """Track analyzed activities to avoid re-processing."""

    def __init__(self, tracking_file: Path):
        """
        Initialize activity tracker.

        Args:
            tracking_file: Path to JSON file storing analyzed activity IDs
        """
        self.tracking_file = tracking_file
        self.data = self._load()

    def _load(self) -> dict:
        """Load tracking data from file."""
        if self.tracking_file.exists():
            with open(self.tracking_file, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self):
        """Save tracking data to file."""
        from magma_cycling.planning.backup import safe_write

        self.tracking_file.parent.mkdir(parents=True, exist_ok=True)
        safe_write(self.tracking_file, json.dumps(self.data, indent=2))

    def is_analyzed(self, activity_id: int, activity_date: date) -> bool:
        """
        Check if activity has been analyzed.

        Args:
            activity_id: Intervals.icu activity ID
            activity_date: Activity date

        Returns:
            True if already analyzed
        """
        date_key = activity_date.isoformat()
        if date_key not in self.data:
            return False

        return any(a["id"] == activity_id for a in self.data[date_key].get("activities", []))

    def mark_analyzed(self, activity: dict, analyzed_at: datetime):
        """
        Mark activity as analyzed.

        Args:
            activity: Activity dict from Intervals.icu API
            analyzed_at: Timestamp of analysis
        """
        activity_date = datetime.fromisoformat(activity["start_date_local"]).date()
        date_key = activity_date.isoformat()

        if date_key not in self.data:
            self.data[date_key] = {"activities": []}

        # Use paired_event_id if available (planned activity), otherwise activity ID (unplanned)
        tracking_id = activity.get("paired_event_id") or activity["id"]

        self.data[date_key]["activities"].append(
            {
                "id": tracking_id,
                "activity_id": activity["id"],  # Store actual activity ID for reference
                "paired_event_id": activity.get("paired_event_id"),
                "name": activity.get("name"),
                "type": activity.get("type"),
                "icu_training_load": activity.get("icu_training_load"),
                "analyzed": True,
                "analyzed_at": analyzed_at.isoformat(),
            }
        )

        self._save()
