"""Data discovery, loading and API fetch mixin for MonthlyAnalyzer."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class DataMixin:
    """Monthly data discovery, loading and API fetch."""

    def find_weeks_in_month(self) -> list[Path]:
        """
        Find all weekly planning files that overlap with the target month.

        Returns:
            List of paths to weekly planning JSON files.
        """
        if not self.planning_dir.exists():
            return []

        # Get month boundaries
        month_start = self.month_date
        # Last day of month
        if month_start.month == 12:
            month_end = datetime(month_start.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = datetime(month_start.year, month_start.month + 1, 1) - timedelta(days=1)

        matching_weeks = []

        for planning_file in sorted(self.planning_dir.glob("week_planning_S*.json")):
            try:
                with open(planning_file, encoding="utf-8") as f:
                    planning = json.load(f)

                week_start = datetime.strptime(planning["start_date"], "%Y-%m-%d")
                week_end = datetime.strptime(planning["end_date"], "%Y-%m-%d")

                # Check if week overlaps with month
                if week_start <= month_end and week_end >= month_start.replace(day=1):
                    matching_weeks.append(planning_file)

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"\u26a0\ufe0f  Skip {planning_file.name}: {e}")
                continue

        return matching_weeks

    def load_weekly_data(self, week_files: list[Path]) -> list[dict]:
        """Load and parse weekly planning data."""
        weekly_data = []

        for week_file in week_files:
            try:
                with open(week_file, encoding="utf-8") as f:
                    data = json.load(f)
                    weekly_data.append(data)
            except Exception as e:
                print(f"\u274c Error loading {week_file.name}: {e}")

        return weekly_data

    def _fetch_actual_tss(self, weekly_data: list[dict]) -> dict[str, int]:
        """Fetch actual TSS from Intervals.icu for completed activities.

        Returns:
            Mapping {intervals_id: actual_tss} for all activities in the month.
            Empty dict on failure (graceful degradation -> fallback to tss_planned).
        """
        try:
            from magma_cycling.config import create_intervals_client

            start = min(w["start_date"] for w in weekly_data)
            end = max(w["end_date"] for w in weekly_data)
            client = create_intervals_client()
            activities = client.get_activities(oldest=start, newest=end)

            return {a["id"]: a.get("icu_training_load", 0) or 0 for a in activities}
        except Exception:
            logger.warning("Could not fetch activities from Intervals.icu, using planned TSS")
            return {}
