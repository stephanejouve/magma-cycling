"""Data Collector for report generation.

Collects and prepares data from multiple sources for AI report generation.

Author: Claude Code (Sprint R10 MVP - Day 2)
Created: 2026-01-18
"""

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from magma_cycling.analyzers.weekly_aggregator import WeeklyAggregator

logger = logging.getLogger(__name__)


class DataCollectionError(Exception):
    """Exception raised for data collection errors."""

    pass


class DataCollector:
    """Collects data from multiple sources for report generation.

    Aggregates data from:
    - Intervals.icu (activities, wellness, metrics)
    - Training intelligence (learnings, patterns)
    - Local files (objectives, feedback)

    Examples:
        >>> collector = DataCollector()
        >>> data = collector.collect_week_data("S076", date(2026, 1, 13))
        >>> data["week_number"]
        'S076'
        >>> len(data["activities"]) > 0
        True
    """

    def __init__(self, data_dir: Path | None = None):
        """Initialize data collector.

        Args:
            data_dir: Optional data directory (defaults to ~/data)
        """
        self.data_dir = data_dir or Path.home() / "data"
        logger.info(f"DataCollector initialized with data_dir: {self.data_dir}")

    def collect_week_data(self, week_number: str, start_date: date) -> dict[str, Any]:
        """Collect all data for a week.

        Args:
            week_number: Week identifier (e.g., "S076")
            start_date: Week start date (Monday)

        Returns:
            Dictionary with all week data:
                - week_number: str
                - start_date: str (ISO format)
                - end_date: str (ISO format)
                - tss_planned: int
                - tss_realized: int
                - activities: list[dict]
                - wellness_data: dict
                - learnings: list[dict]
                - metrics_evolution: dict

        Raises:
            DataCollectionError: If collection fails

        Examples:
            >>> collector = DataCollector()
            >>> data = collector.collect_week_data("S076", date(2026, 1, 13))
            >>> "activities" in data
            True
        """
        try:
            logger.info(f"Collecting data for week {week_number} ({start_date})")

            # Use WeeklyAggregator to collect data
            aggregator = WeeklyAggregator(
                week=week_number,
                start_date=start_date,
            )

            result = aggregator.aggregate()

            if not result.success:
                raise DataCollectionError(f"Failed to aggregate week data: {result.error}")

            # Extract and format data
            processed_data = result.data.get("processed", {})

            # Calculate end date (start_date + 6 days)
            end_date = start_date + timedelta(days=6)

            # Extract activities
            activities = self._format_activities(processed_data.get("workouts", []))

            # Extract wellness data
            wellness_data = self._extract_wellness_data(processed_data)

            # Extract learnings
            learnings = self._extract_learnings(processed_data)

            # Extract metrics evolution
            metrics_evolution = self._extract_metrics_evolution(processed_data)

            # Calculate TSS
            tss_planned = processed_data.get("summary", {}).get("planned_tss", 0)
            tss_realized = processed_data.get("summary", {}).get("total_tss", 0)

            # Compile final data structure
            week_data = {
                "week_number": week_number,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "tss_planned": tss_planned,
                "tss_realized": tss_realized,
                "activities": activities,
                "wellness_data": wellness_data,
                "learnings": learnings,
                "metrics_evolution": metrics_evolution,
            }

            logger.info(
                f"Successfully collected data for {week_number}: "
                f"{len(activities)} activities, "
                f"{len(learnings)} learnings"
            )

            return week_data

        except Exception as e:
            error_msg = f"Failed to collect week data for {week_number}: {str(e)}"
            logger.error(error_msg)
            raise DataCollectionError(error_msg) from e

    def _format_activities(self, workouts: list[dict]) -> list[dict[str, Any]]:
        """Format workouts from WeeklyAggregator into activities format.

        Args:
            workouts: List of workout dicts from WeeklyAggregator

        Returns:
            List of formatted activity dictionaries
        """
        activities = []

        for workout in workouts:
            # Extract activity data (WorkoutAggregator format)
            activity_data = workout.get("intervals_activity", {})

            if not activity_data:
                logger.warning(f"Workout missing intervals_activity: {workout}")
                continue

            activity = {
                "id": activity_data.get("id", ""),
                "name": activity_data.get("name", "Session sans nom"),
                "start_date": activity_data.get("start_date_local", ""),
                "type": activity_data.get("type", "Ride"),
                "moving_time": activity_data.get("moving_time", 0),
                "tss": activity_data.get("icu_training_load", 0),
                "if_": activity_data.get("icu_intensity", 0.0),
                "np": activity_data.get("icu_np", 0),
                "avg_hr": activity_data.get("average_hr", 0),
                "indoor": activity_data.get("trainer", False),
            }

            activities.append(activity)

        # Sort by start date
        activities.sort(key=lambda x: x["start_date"])

        return activities

    def _extract_wellness_data(self, processed_data: dict) -> dict[str, Any]:
        """Extract wellness metrics from processed data.

        Args:
            processed_data: Processed data from WeeklyAggregator

        Returns:
            Dictionary with wellness metrics
        """
        metrics = processed_data.get("metrics_evolution", {})

        # Calculate averages from daily data
        hrv_values = []
        sleep_values = []
        fatigue_values = []
        readiness_values = []

        # Extract from metrics evolution if available
        if metrics and "daily_metrics" in metrics:
            for day_data in metrics["daily_metrics"]:
                if "hrv" in day_data and day_data["hrv"] is not None:
                    hrv_values.append(day_data["hrv"])
                if "sleep_quality" in day_data and day_data["sleep_quality"] is not None:
                    sleep_values.append(day_data["sleep_quality"])
                if "fatigue" in day_data and day_data["fatigue"] is not None:
                    fatigue_values.append(day_data["fatigue"])
                if "readiness" in day_data and day_data["readiness"] is not None:
                    readiness_values.append(day_data["readiness"])

        # Calculate averages
        wellness_data = {
            "hrv_avg": round(sum(hrv_values) / len(hrv_values), 1) if hrv_values else "N/A",
            "hrv_trend": self._calculate_trend(hrv_values),
            "sleep_quality_avg": (
                round(sum(sleep_values) / len(sleep_values), 1) if sleep_values else "N/A"
            ),
            "fatigue_score_avg": (
                round(sum(fatigue_values) / len(fatigue_values), 1) if fatigue_values else "N/A"
            ),
            "readiness_avg": (
                round(sum(readiness_values) / len(readiness_values), 1)
                if readiness_values
                else "N/A"
            ),
        }

        return wellness_data

    def _extract_learnings(self, processed_data: dict) -> list[dict[str, Any]]:
        """Extract training intelligence learnings.

        Args:
            processed_data: Processed data from WeeklyAggregator

        Returns:
            List of learning dictionaries
        """
        learnings_data = processed_data.get("learnings", [])

        learnings = []
        for learning in learnings_data:
            learnings.append(
                {
                    "type": learning.get("type", "general"),
                    "title": learning.get("title", "Apprentissage"),
                    "description": learning.get("description", ""),
                    "session_id": learning.get("session_id", ""),
                    "confidence": learning.get("confidence", "medium"),
                }
            )

        return learnings

    def _extract_metrics_evolution(self, processed_data: dict) -> dict[str, Any]:
        """Extract metrics evolution (start vs end).

        Args:
            processed_data: Processed data from WeeklyAggregator

        Returns:
            Dictionary with start and end metrics
        """
        metrics = processed_data.get("metrics_evolution", {})

        if not metrics or "daily_metrics" not in metrics:
            return {"start": {}, "end": {}}

        daily_metrics = metrics["daily_metrics"]

        if not daily_metrics:
            return {"start": {}, "end": {}}

        # Get first and last day metrics
        start_metrics = daily_metrics[0] if len(daily_metrics) > 0 else {}
        end_metrics = daily_metrics[-1] if len(daily_metrics) > 0 else {}

        return {
            "start": {
                "ctl": start_metrics.get("ctl", "N/A"),
                "atl": start_metrics.get("atl", "N/A"),
                "tsb": start_metrics.get("tsb", "N/A"),
                "hrv": start_metrics.get("hrv", "N/A"),
            },
            "end": {
                "ctl": end_metrics.get("ctl", "N/A"),
                "atl": end_metrics.get("atl", "N/A"),
                "tsb": end_metrics.get("tsb", "N/A"),
                "hrv": end_metrics.get("hrv", "N/A"),
            },
        }

    def _calculate_trend(self, values: list[float]) -> str:
        """Calculate trend from list of values.

        Args:
            values: List of numeric values

        Returns:
            Trend description ("increasing", "decreasing", "stable")
        """
        if not values or len(values) < 2:
            return "stable"

        # Compare first half vs second half
        mid_point = len(values) // 2
        first_half_avg = sum(values[:mid_point]) / len(values[:mid_point])
        second_half_avg = sum(values[mid_point:]) / len(values[mid_point:])

        diff_pct = ((second_half_avg - first_half_avg) / first_half_avg) * 100

        if diff_pct > 5:
            return "increasing"
        elif diff_pct < -5:
            return "decreasing"
        else:
            return "stable"
