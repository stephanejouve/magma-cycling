"""Data fetching mixin for IntervalsICUBackfiller."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DataFetchMixin:
    """Fetch activities and wellness data from Intervals.icu API."""

    def fetch_activities(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """
        Fetch activities from Intervals.icu API.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            List of activity dicts
        """
        print(f"📥 Fetching activities from {start_date} to {end_date}...")

        try:
            activities = self.client.get_activities(oldest=start_date, newest=end_date)
            print(f"   ✅ Fetched {len(activities)} activities")
            return activities
        except Exception as e:
            print(f"   ❌ Error fetching activities: {e}")
            return []

    def fetch_wellness(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """
        Fetch wellness data (sleep, HRV, etc.) from Intervals.icu.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            List of wellness dicts (one per day).
        """
        print(f"😴 Fetching wellness data from {start_date} to {end_date}...")

        try:
            wellness = self.client.get_wellness(oldest=start_date, newest=end_date)
            print(f"   ✅ Fetched {len(wellness)} wellness entries")
            return wellness
        except Exception as e:
            print(f"   ❌ Error fetching wellness: {e}")
            return []
