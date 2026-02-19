#!/usr/bin/env python3
"""
Adherence Storage - Persistent storage for adherence tracking data.

Stores planned vs realized metrics for each session to enable
long-term adherence analysis and PID correction.

Examples:
    Save session adherence::

        from cyclisme_training_logs.analyzers.adherence_storage import AdherenceStorage

        storage = AdherenceStorage()
        storage.save_session_adherence(
            activity_id="i123456",
            week_id="S082",
            adherence_data={...}
        )

    Query mesocycle adherence::

        adherence_data = storage.get_mesocycle_adherence(
            weeks=["S077", "S078", "S079", "S080", "S081", "S082"]
        )

Author: Claude Code
Created: 2026-02-19
Version: 1.0.0
"""

import json
from datetime import datetime
from pathlib import Path


class AdherenceStorage:
    """
    Persistent storage for adherence tracking data.

    Stores session-by-session adherence metrics for long-term analysis.
    """

    def __init__(self, storage_file: Path | None = None):
        """
        Initialize adherence storage.

        Args:
            storage_file: Path to storage file (default: ~/.adherence_history.json)
        """
        self.storage_file = storage_file or (Path.home() / ".adherence_history.json")
        self.data = self._load_data()

    def _load_data(self) -> dict:
        """Load adherence data from file."""
        if self.storage_file.exists():
            try:
                return json.loads(self.storage_file.read_text(encoding="utf-8"))
            except Exception:
                return {"sessions": {}, "last_updated": None}
        return {"sessions": {}, "last_updated": None}

    def _save_data(self):
        """Save adherence data to file."""
        try:
            self.data["last_updated"] = datetime.now().isoformat()
            self.storage_file.write_text(
                json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            print(f"⚠️  Failed to save adherence data: {e}")

    def save_session_adherence(
        self, activity_id: str, week_id: str, date: str, adherence_data: dict
    ):
        """
        Save adherence data for a session.

        Args:
            activity_id: Activity ID (e.g., "i123456")
            week_id: Week identifier (e.g., "S082")
            date: Session date (ISO format YYYY-MM-DD)
            adherence_data: Adherence metrics dict from AdherenceTracker

        Examples:
            >>> storage = AdherenceStorage()
            >>> storage.save_session_adherence(
            ...     "i123456",
            ...     "S082",
            ...     "2026-02-19",
            ...     {"tss_adherence": 0.95, "if_adherence": 0.98}
            ... )
        """
        session_key = f"{week_id}_{activity_id}"

        self.data["sessions"][session_key] = {
            "activity_id": activity_id,
            "week_id": week_id,
            "date": date,
            "adherence": adherence_data,
            "timestamp": datetime.now().isoformat(),
        }

        self._save_data()

    def get_session_adherence(self, activity_id: str, week_id: str) -> dict | None:
        """
        Get adherence data for a specific session.

        Args:
            activity_id: Activity ID
            week_id: Week identifier

        Returns:
            Adherence data dict or None if not found
        """
        session_key = f"{week_id}_{activity_id}"
        return self.data["sessions"].get(session_key)

    def get_mesocycle_adherence(self, weeks: list[str]) -> list[dict]:
        """
        Get all adherence data for a mesocycle.

        Args:
            weeks: List of week IDs (e.g., ["S077", "S078", ...])

        Returns:
            List of adherence data dicts

        Examples:
            >>> storage = AdherenceStorage()
            >>> data = storage.get_mesocycle_adherence(["S077", "S078", "S079"])
            >>> len(data)
            15  # 15 sessions over 3 weeks
        """
        mesocycle_data = []

        for session_key, session_data in self.data["sessions"].items():
            if session_data["week_id"] in weeks:
                mesocycle_data.append(session_data)

        # Sort by date
        mesocycle_data.sort(key=lambda x: x["date"])

        return mesocycle_data

    def calculate_mesocycle_stats(self, weeks: list[str]) -> dict:
        """
        Calculate aggregated statistics for a mesocycle.

        Args:
            weeks: List of week IDs

        Returns:
            Dict with aggregated adherence statistics

        Examples:
            >>> storage = AdherenceStorage()
            >>> stats = storage.calculate_mesocycle_stats(["S077", "S078", "S079"])
            >>> stats['tss_adherence_avg']
            0.87
        """
        sessions = self.get_mesocycle_adherence(weeks)

        if not sessions:
            return {
                "tss_adherence_avg": 0,
                "if_adherence_avg": 0,
                "sessions_count": 0,
                "sessions_with_plan": 0,
            }

        # Filter sessions with plan
        sessions_with_plan = [s for s in sessions if s["adherence"].get("has_plan", False)]

        if not sessions_with_plan:
            return {
                "tss_adherence_avg": 0,
                "if_adherence_avg": 0,
                "sessions_count": len(sessions),
                "sessions_with_plan": 0,
            }

        # Calculate averages
        tss_values = [
            s["adherence"]["tss_adherence"]
            for s in sessions_with_plan
            if s["adherence"].get("tss_adherence") is not None
        ]

        if_values = [
            s["adherence"]["if_adherence"]
            for s in sessions_with_plan
            if s["adherence"].get("if_adherence") is not None
        ]

        return {
            "tss_adherence_avg": sum(tss_values) / len(tss_values) if tss_values else 0,
            "if_adherence_avg": sum(if_values) / len(if_values) if if_values else 0,
            "sessions_count": len(sessions),
            "sessions_with_plan": len(sessions_with_plan),
            "tss_adherence_values": tss_values,
            "if_adherence_values": if_values,
        }

    def get_adherence_trend(self, weeks: list[str], metric: str = "tss") -> str:
        """
        Calculate trend for adherence metric over mesocycle.

        Args:
            weeks: List of week IDs
            metric: Metric to analyze ("tss" or "if")

        Returns:
            Trend description: "improving", "stable", "declining"
        """
        sessions = self.get_mesocycle_adherence(weeks)
        sessions_with_plan = [s for s in sessions if s["adherence"].get("has_plan", False)]

        if len(sessions_with_plan) < 3:
            return "insufficient_data"

        # Extract values
        if metric == "tss":
            values = [
                s["adherence"]["tss_adherence"]
                for s in sessions_with_plan
                if s["adherence"].get("tss_adherence") is not None
            ]
        else:  # if
            values = [
                s["adherence"]["if_adherence"]
                for s in sessions_with_plan
                if s["adherence"].get("if_adherence") is not None
            ]

        if len(values) < 3:
            return "insufficient_data"

        # Simple linear regression slope
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable"

        slope = numerator / denominator

        if slope > 0.01:
            return "improving"
        elif slope < -0.01:
            return "declining"
        else:
            return "stable"
