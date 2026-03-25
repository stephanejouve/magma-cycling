"""Statistical aggregation mixin for MonthlyAnalyzer."""

from collections import defaultdict
from typing import Any


class StatsMixin:
    """Monthly statistical aggregation."""

    def aggregate_statistics(
        self, weekly_data: list[dict], actual_tss_map: dict | None = None
    ) -> dict:
        """Aggregate monthly statistics from weekly data.

        Args:
            weekly_data: List of weekly planning dicts.
            actual_tss_map: Optional mapping {intervals_id: actual_tss} from
                Intervals.icu. When provided, completed/modified sessions with
                an intervals_id use real TSS instead of tss_planned.

        Returns:
            Dictionary with monthly metrics.
        """
        stats: dict[str, Any] = {
            "total_weeks": len(weekly_data),
            "total_sessions": 0,
            "completed": 0,
            "skipped": 0,
            "cancelled": 0,
            "modified": 0,
            "rest_days": 0,
            "tss_realized": 0,
            "tss_target_total": 0,
            "sessions_by_type": defaultdict(int),
            "sessions_by_status": defaultdict(int),
            "tss_by_week": [],
            "weekly_details": [],
        }

        for week in sorted(weekly_data, key=lambda w: w["start_date"]):
            week_stats = {
                "week_id": week["week_id"],
                "start_date": week["start_date"],
                "end_date": week["end_date"],
                "tss_target": week.get("tss_target", 0),
                "tss_actual": 0,
                "sessions": len(week.get("planned_sessions", [])),
            }

            stats["tss_target_total"] += week.get("tss_target", 0)

            for session in week.get("planned_sessions", []):
                stats["total_sessions"] += 1
                status = session.get("status", "unknown")
                session_type = session.get("type", "unknown")

                tss_planned = session.get("tss_planned", 0)
                intervals_id = session.get("intervals_id")
                # Use actual TSS for completed/modified sessions when available
                if intervals_id and actual_tss_map and f"i{intervals_id}" in actual_tss_map:
                    tss = actual_tss_map[f"i{intervals_id}"]
                else:
                    tss = tss_planned

                # Count by status
                stats["sessions_by_status"][status] += 1

                if status == "completed":
                    stats["completed"] += 1
                    stats["tss_realized"] += tss
                    week_stats["tss_actual"] += tss
                elif status == "skipped":
                    stats["skipped"] += 1
                elif status == "cancelled":
                    stats["cancelled"] += 1
                elif status == "modified":
                    stats["modified"] += 1
                    stats["tss_realized"] += tss
                    week_stats["tss_actual"] += tss
                elif status == "rest_day":
                    stats["rest_days"] += 1

                # Count by type (exclude rest days)
                if status != "rest_day":
                    stats["sessions_by_type"][session_type] += 1

            stats["tss_by_week"].append(week_stats)
            stats["weekly_details"].append(week_stats)

        # Calculate adherence rate
        total_planned = (
            stats["completed"] + stats["skipped"] + stats["cancelled"] + stats["modified"]
        )
        if total_planned > 0:
            stats["adherence_rate"] = (stats["completed"] + stats["modified"]) / total_planned * 100
        else:
            stats["adherence_rate"] = 0

        # Calculate TSS achievement rate
        if stats["tss_target_total"] > 0:
            stats["tss_achievement_rate"] = stats["tss_realized"] / stats["tss_target_total"] * 100
        else:
            stats["tss_achievement_rate"] = 0

        return stats
