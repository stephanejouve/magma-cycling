#!/usr/bin/env python3
"""
Baseline Preliminary Analysis - Monitoring Data Validation.

Analyzes monitoring data (adherence, TSS, TSB) for baseline period
to validate infrastructure and identify patterns before PID calibration.

Usage:
    poetry run analyze-baseline --start 2026 - 01 - 04 --end 2026 - 01 - 25
    poetry run analyze-baseline --start 2026 - 01 - 04 --end 2026 - 01 - 25 --output ~/data/pid

Author: Claude Code + Stéphane Jouve
Created: 2026 - 01 - 25
Sprint: R9.E - Baseline Preliminary Analysis

Metadata:
    Status: Production
    Priority: P1
    Version: 1.0.0
"""

import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from cyclisme_training_logs.config import create_intervals_client


class BaselineAnalyzer:
    """Analyze monitoring data for baseline period validation.

    Validates infrastructure monitoring and extracts patterns from:
    - Adherence data (workout_adherence.jsonl)
    - Intervals.icu wellness (TSB, CTL, ATL)
    - Intervals.icu activities (TSS, IF, NP)
    - Cardiovascular coupling (workout_history)

    Args:
        start_date: Analysis start date (YYYY-MM-DD)
        end_date: Analysis end date (YYYY-MM-DD)
        adherence_file: Path to workout_adherence.jsonl
        workout_history_dir: Path to logs/weekly_reports/
        output_dir: Path to output directory
    """

    def __init__(
        self,
        start_date: str,
        end_date: str,
        adherence_file: Path | None = None,
        workout_history_dir: Path | None = None,
        output_dir: Path | None = None,
    ):
        """Initialize baseline analyzer."""
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        self.duration_days = (self.end_date - self.start_date).days + 1

        # Paths
        self.adherence_file = (
            adherence_file or Path.home() / "data" / "monitoring" / "workout_adherence.jsonl"
        )
        self.workout_history_dir = (
            workout_history_dir or Path(__file__).parent.parent.parent / "logs" / "weekly_reports"
        )
        self.output_dir = output_dir or Path.home() / "data" / "pid"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Data storage
        self.adherence_data = []
        self.wellness_data = []
        self.activities_data = []
        self.events_data = []
        self.cv_coupling_values = []
        self.skipped_sessions = []  # NOTE events with [SAUTÉE] tag
        self.replaced_sessions = []  # NOTE events with [REMPLACÉE] tag
        self.cancelled_sessions = []  # NOTE events with [ANNULÉE] tag
        self.unsolicited_activities = []  # Activities without paired workout event

        # Intervals.icu client
        self.client = create_intervals_client()

        print("📊 Baseline Analyzer Initialized")
        print(f"   Period: {self.start_date} → {self.end_date} ({self.duration_days} days)")
        print()

    def load_adherence_data(self) -> None:
        """Load adherence data from workout_adherence.jsonl."""
        print("📥 Loading adherence data...")

        if not self.adherence_file.exists():
            print(f"   ⚠️  File not found: {self.adherence_file}")
            return

        seen_dates = {}
        with open(self.adherence_file, encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)
                record_date = datetime.strptime(record["date"], "%Y-%m-%d").date()

                if self.start_date <= record_date <= self.end_date:
                    # Deduplicate: keep only most recent record per date
                    date_key = record["date"]
                    if date_key not in seen_dates:
                        seen_dates[date_key] = record
                    else:
                        # Keep record with most recent timestamp
                        existing_ts = seen_dates[date_key].get("timestamp", "")
                        current_ts = record.get("timestamp", "")
                        if current_ts > existing_ts:
                            seen_dates[date_key] = record

        self.adherence_data = list(seen_dates.values())
        self.adherence_data.sort(key=lambda x: x["date"])
        print(f"   ✅ Loaded {len(self.adherence_data)} records")

    def load_intervals_data(self) -> None:
        """Load data from Intervals.icu API."""
        print("\n📥 Loading Intervals.icu data...")

        start_str = self.start_date.isoformat()
        end_str = self.end_date.isoformat()

        # Wellness (TSB, CTL, ATL)
        try:
            self.wellness_data = self.client.get_wellness(start_str, end_str)
            print(f"   ✅ Wellness: {len(self.wellness_data)} days")
        except Exception as e:
            print(f"   ⚠️  Wellness error: {e}")

        # Activities
        try:
            self.activities_data = self.client.get_activities(start_str, end_str)
            print(f"   ✅ Activities: {len(self.activities_data)} records")
        except Exception as e:
            print(f"   ⚠️  Activities error: {e}")

        # Events (planned workouts)
        try:
            self.events_data = self.client.get_events(start_str, end_str)
            print(f"   ✅ Events: {len(self.events_data)} planned workouts")
        except Exception as e:
            print(f"   ⚠️  Events error: {e}")

    def parse_skipped_replaced_sessions(self) -> None:
        """Parse NOTE events for skipped/replaced/cancelled sessions.

        Intervals.icu creates NOTE events with special tags when sessions are
        cancelled/skipped/replaced via update-session script:
        - [SAUTÉE] = Skipped session
        - [REMPLACÉE] = Replaced session
        - [ANNULÉE] = Cancelled session
        """
        print("\n📥 Parsing skipped/replaced sessions...")

        if not self.events_data:
            print("   ⚠️  No events data loaded")
            return

        # Find NOTE events with status tags
        for event in self.events_data:
            if event.get("category") != "NOTE":
                continue

            name = event.get("name", "")
            description = event.get("description", "")
            date = event.get("start_date_local", "").split("T")[0]

            # Extract session info
            session_data = {
                "date": date,
                "name": name,
                "description": description,
                "reason": self._extract_reason(description),
            }

            # Categorize by tag
            if "[SAUTÉE]" in name:
                self.skipped_sessions.append(session_data)
            elif "[REMPLACÉE]" in name:
                self.replaced_sessions.append(session_data)
            elif "[ANNULÉE]" in name:
                self.cancelled_sessions.append(session_data)

        total_not_completed = (
            len(self.skipped_sessions) + len(self.replaced_sessions) + len(self.cancelled_sessions)
        )

        print(f"   ✅ Skipped: {len(self.skipped_sessions)}")
        print(f"   ✅ Replaced: {len(self.replaced_sessions)}")
        print(f"   ✅ Cancelled: {len(self.cancelled_sessions)}")
        print(f"   ✅ Total not-completed: {total_not_completed}")

    def _extract_reason(self, description: str) -> str:
        """Extract reason from NOTE description.

        Args:
            description: NOTE description text

        Returns:
            Reason string or "Non spécifiée"
        """
        if not description:
            return "Non spécifiée"

        # Look for "Raison: ..." pattern
        lines = description.split("\n")
        for line in lines:
            if line.startswith("Raison:"):
                return line.replace("Raison:", "").strip()

        return "Non spécifiée"

    def detect_unsolicited_activities(self) -> list[dict[str, Any]]:
        """Detect activities without paired workout event (unsolicited/spontaneous).

        Unsolicited activities are activities completed that don't match any
        planned workout in the calendar. These can be:
        - Spontaneous bonus workouts
        - Outdoor rides replacing planned indoor sessions (not marked as replaced)
        - Extra activities added on rest days

        Returns:
            List of unsolicited activity dicts with metadata
        """
        print("\n📥 Detecting unsolicited activities...")

        if not self.activities_data:
            print("   ⚠️  No activities data loaded")
            return []

        # Get all paired activity IDs from WORKOUT events
        # Empty events_data is valid - means no paired workouts exist
        workout_events = (
            [e for e in self.events_data if e.get("category") == "WORKOUT"]
            if self.events_data
            else []
        )
        paired_activity_ids = {
            e.get("paired_activity_id") for e in workout_events if e.get("paired_activity_id")
        }

        # Find activities NOT in paired set
        unsolicited = []
        for activity in self.activities_data:
            activity_id = activity.get("id")
            if activity_id and activity_id not in paired_activity_ids:
                date = activity.get("start_date_local", "").split("T")[0]
                unsolicited.append(
                    {
                        "date": date,
                        "activity_id": activity_id,
                        "name": activity.get("name", "Unnamed"),
                        "type": activity.get("type", "Unknown"),
                        "tss": activity.get("icu_training_load") or 0,
                        "duration_seconds": activity.get("moving_time") or 0,
                        "distance_meters": activity.get("distance") or 0,
                        "avg_power": activity.get("average_watts"),
                        "normalized_power": activity.get("normalized_power"),
                    }
                )

        # Sort by date
        unsolicited.sort(key=lambda x: x["date"])

        print(f"   ✅ Found {len(unsolicited)} unsolicited activities")
        if unsolicited:
            total_tss = sum(a["tss"] for a in unsolicited)
            print(f"   ✅ Total unsolicited TSS: {total_tss:.0f}")

        return unsolicited

    def analyze_skip_reasons(self, sessions: list[dict[str, Any]]) -> dict[str, Any]:
        """Cluster skip/replace/cancel reasons into categories.

        Categories:
        - work_schedule: Late from work, work tasks, schedule conflicts
        - mechanics: Bike/trainer issues, equipment problems
        - health: Fatigue, illness, injury, recovery
        - weather: Outdoor conditions, too hot/cold
        - personal: Family, personal commitments
        - other: Uncategorized reasons

        Args:
            sessions: List of session dicts with 'reason' field

        Returns:
            Dict with clustering stats and category details
        """
        print("\n📊 Analyzing skip reasons...")

        if not sessions:
            print("   ℹ️  No sessions to analyze")
            return {
                "total": 0,
                "categories": {},
                "distribution": {},
            }

        # Define category patterns (case-insensitive)
        category_patterns = {
            "work_schedule": [
                r"\btoo\s+late\b",
                r"\blate\s+from\s+work\b",
                r"\breturn.*late\b",
                r"\bwork\b",
                r"\bschedule\b",
                r"\bmeeting\b",
                r"\boffice\b",
                r"\bproject\b",
                r"\bdeadline\b",
            ],
            "mechanics": [
                r"\bmechanic",
                r"\bbike\s+issue",
                r"\btrainer\s+issue",
                r"\bequipment",
                r"\bbroken",
                r"\brepair",
                r"\bmaintenance",
                r"\bgear\s+problem",
            ],
            "health": [
                r"\bfatigue",
                r"\btired",
                r"\bill",
                r"\bsick",
                r"\binjur",
                r"\brecovery",
                r"\bpain",
                r"\bsoreness",
                r"\bhealthy",
            ],
            "weather": [
                r"\bweather",
                r"\brain",
                r"\bstorm",
                r"\bhot",
                r"\bcold",
                r"\bwind",
                r"\bsnow",
            ],
            "personal": [
                r"\bfamily",
                r"\bpersonal",
                r"\bemergency",
                r"\bappointment",
                r"\bvisit",
                r"\bevent",
            ],
        }

        # Categorize each session
        categorized = {cat: [] for cat in category_patterns}
        categorized["other"] = []

        for session in sessions:
            reason = session.get("reason", "").lower()
            categorized_flag = False

            for category, patterns in category_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, reason, re.IGNORECASE):
                        categorized[category].append(
                            {
                                "date": session.get("date"),
                                "name": session.get("name"),
                                "reason": session.get("reason"),
                                "matched_pattern": pattern,
                            }
                        )
                        categorized_flag = True
                        break
                if categorized_flag:
                    break

            if not categorized_flag:
                categorized["other"].append(
                    {
                        "date": session.get("date"),
                        "name": session.get("name"),
                        "reason": session.get("reason"),
                    }
                )

        # Calculate distribution
        total = len(sessions)
        distribution = {}
        for category, items in categorized.items():
            count = len(items)
            if count > 0:
                distribution[category] = {
                    "count": count,
                    "percentage": round(count / total * 100, 1),
                }

        # Print summary
        print(f"   ✅ Analyzed {total} sessions")
        for category, stats in distribution.items():
            print(f"   📋 {category}: {stats['count']} ({stats['percentage']}%)")

        return {
            "total": total,
            "categories": categorized,
            "distribution": distribution,
        }

    def analyze_day_of_week_patterns(
        self, day_patterns: dict[str, dict[str, int]]
    ) -> dict[str, Any]:
        """Analyze day-of-week adherence patterns with risk scoring.

        Args:
            day_patterns: Dict with day names as keys, each containing
                         {"planned": int, "completed": int}

        Returns:
            Dict with enhanced day patterns including adherence rates,
            risk scores, and recommendations
        """
        print("\n📅 Analyzing day-of-week patterns...")

        if not day_patterns:
            print("   ℹ️  No day patterns to analyze")
            return {
                "days": {},
                "high_risk_days": [],
                "recommendations": [],
            }

        # Calculate adherence rate and risk for each day
        enriched_days = {}
        for day, counts in day_patterns.items():
            planned = counts["planned"]
            completed = counts["completed"]
            adherence_rate = completed / planned if planned > 0 else 0

            # Risk scoring (0-100, higher = more risky)
            # Risk = 100 * (1 - adherence_rate)
            risk_score = round(100 * (1 - adherence_rate), 1)

            # Risk level classification
            if risk_score < 20:
                risk_level = "LOW"
            elif risk_score < 40:
                risk_level = "MODERATE"
            elif risk_score < 60:
                risk_level = "HIGH"
            else:
                risk_level = "CRITICAL"

            enriched_days[day] = {
                "planned": planned,
                "completed": completed,
                "adherence_rate": round(adherence_rate, 3),
                "risk_score": risk_score,
                "risk_level": risk_level,
            }

        # Identify high-risk days (risk_score >= 40)
        high_risk_days = [
            {"day": day, "risk_score": data["risk_score"], "adherence_rate": data["adherence_rate"]}
            for day, data in enriched_days.items()
            if data["risk_score"] >= 40
        ]
        # Sort by risk score descending
        high_risk_days.sort(key=lambda x: x["risk_score"], reverse=True)

        # Generate recommendations
        recommendations = []
        for risk_day in high_risk_days:
            day = risk_day["day"]
            risk_score = risk_day["risk_score"]
            adherence = risk_day["adherence_rate"]

            if risk_score >= 60:
                recommendations.append(
                    f"⚠️ {day}: CRITICAL risk ({adherence * 100:.0f}% adherence). "
                    f"Consider moving workouts to more reliable days or reducing session difficulty."
                )
            elif risk_score >= 40:
                recommendations.append(
                    f"⚠️ {day}: HIGH risk ({adherence * 100:.0f}% adherence). "
                    f"Plan lighter sessions or build flexibility into schedule."
                )

        print(f"   ✅ Analyzed {len(enriched_days)} days")
        print(f"   ⚠️  High-risk days: {len(high_risk_days)}")
        for risk_day in high_risk_days:
            print(f"      - {risk_day['day']}: {risk_day['adherence_rate'] * 100:.0f}% adherence")

        return {
            "days": enriched_days,
            "high_risk_days": high_risk_days,
            "recommendations": recommendations,
        }

    def analyze_workout_type_patterns(
        self, completed_workouts: list[dict[str, Any]], all_sessions: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Analyze adherence patterns by workout type.

        Extracts workout type from session names (e.g., CAD, INT, END, REC)
        and calculates adherence rates per type.

        Args:
            completed_workouts: List of completed workout events
            all_sessions: List of all sessions (completed + skipped + replaced + cancelled)

        Returns:
            Dict with workout type patterns, risk scores, and recommendations
        """
        print("\n🏋️ Analyzing workout type patterns...")

        if not all_sessions:
            print("   ℹ️  No sessions to analyze")
            return {
                "types": {},
                "high_risk_types": [],
                "recommendations": [],
            }

        # Extract workout type from session name
        # Format: SXXX-XX-TYPE-Name-VXXX
        type_pattern = re.compile(r"S\d+-\d+-([A-Z]+)-")

        # Count planned and completed per type
        type_stats = {}

        # Process all sessions (planned)
        for session in all_sessions:
            name = session.get("name", "")
            # Remove status tags
            name = (
                name.replace("[SAUTÉE] ", "").replace("[REMPLACÉE] ", "").replace("[ANNULÉE] ", "")
            )

            match = type_pattern.search(name)
            if match:
                workout_type = match.group(1)
                if workout_type not in type_stats:
                    type_stats[workout_type] = {"planned": 0, "completed": 0}
                type_stats[workout_type]["planned"] += 1

        # Process completed workouts
        for workout in completed_workouts:
            name = workout.get("name", "")
            match = type_pattern.search(name)
            if match:
                workout_type = match.group(1)
                if workout_type in type_stats:
                    type_stats[workout_type]["completed"] += 1

        # Calculate adherence and risk per type
        enriched_types = {}
        for workout_type, counts in type_stats.items():
            planned = counts["planned"]
            completed = counts["completed"]
            adherence_rate = completed / planned if planned > 0 else 0

            # Risk scoring (0-100, higher = more risky)
            risk_score = round(100 * (1 - adherence_rate), 1)

            # Risk level classification
            if risk_score < 20:
                risk_level = "LOW"
            elif risk_score < 40:
                risk_level = "MODERATE"
            elif risk_score < 60:
                risk_level = "HIGH"
            else:
                risk_level = "CRITICAL"

            enriched_types[workout_type] = {
                "planned": planned,
                "completed": completed,
                "adherence_rate": round(adherence_rate, 3),
                "risk_score": risk_score,
                "risk_level": risk_level,
            }

        # Identify high-risk types (risk_score >= 40)
        high_risk_types = [
            {
                "type": workout_type,
                "risk_score": data["risk_score"],
                "adherence_rate": data["adherence_rate"],
            }
            for workout_type, data in enriched_types.items()
            if data["risk_score"] >= 40
        ]
        # Sort by risk score descending
        high_risk_types.sort(key=lambda x: x["risk_score"], reverse=True)

        # Generate recommendations
        recommendations = []
        for risk_type in high_risk_types:
            workout_type = risk_type["type"]
            risk_score = risk_type["risk_score"]
            adherence = risk_type["adherence_rate"]

            if risk_score >= 60:
                recommendations.append(
                    f"⚠️ {workout_type} workouts: CRITICAL risk ({adherence * 100:.0f}% adherence). "
                    f"Consider reducing frequency or intensity for this type."
                )
            elif risk_score >= 40:
                recommendations.append(
                    f"⚠️ {workout_type} workouts: HIGH risk ({adherence * 100:.0f}% adherence). "
                    f"Review session difficulty or timing for this type."
                )

        print(f"   ✅ Analyzed {len(enriched_types)} workout types")
        print(f"   ⚠️  High-risk types: {len(high_risk_types)}")
        for risk_type in high_risk_types:
            print(
                f"      - {risk_type['type']}: {risk_type['adherence_rate'] * 100:.0f}% adherence"
            )

        return {
            "types": enriched_types,
            "high_risk_types": high_risk_types,
            "recommendations": recommendations,
        }

    def load_cardiovascular_coupling(self) -> None:
        """Extract cardiovascular coupling from workout_history files."""
        print("\n📥 Extracting cardiovascular coupling...")

        if not self.workout_history_dir.exists():
            print(f"   ⚠️  Directory not found: {self.workout_history_dir}")
            return

        patterns = [
            r"découplage\s+cardiovasculaire\s+\w+\s*\((\d+\.?\d*)\s*%\)",
            r"découplage\s+(\d+\.?\d*)\s*%",
        ]

        workout_files = sorted(self.workout_history_dir.glob("*/workout_history_*.md"))
        print(f"   📁 Found {len(workout_files)} weekly files")

        for workout_file in workout_files:
            with open(workout_file, encoding="utf-8") as f:
                content = f.read()

            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    coupling_pct = float(match.group(1))
                    self.cv_coupling_values.append(abs(coupling_pct) / 100.0)

        print(f"   ✅ Extracted {len(self.cv_coupling_values)} values")

    def validate_data_quality(self) -> dict[str, Any]:
        """Check data completeness, gaps, and anomalies.

        Returns:
            Dict with quality metrics and score
        """
        print("\n🔍 Validating data quality...")

        quality = {
            "completeness": {},
            "gaps": [],
            "anomalies": [],
            "score": 0,
            "grade": "",
        }

        # Check adherence completeness
        expected_days = self.duration_days
        actual_days = len(self.adherence_data)
        adherence_completeness = actual_days / expected_days if expected_days > 0 else 0

        quality["completeness"]["adherence"] = adherence_completeness
        quality["completeness"]["wellness"] = (
            len(self.wellness_data) / expected_days if expected_days > 0 else 0
        )
        quality["completeness"]["activities"] = len(self.activities_data)  # No expected count

        # Detect gaps in adherence
        if self.adherence_data:
            adherence_dates = {
                datetime.strptime(r["date"], "%Y-%m-%d").date() for r in self.adherence_data
            }
            current = self.start_date
            while current <= self.end_date:
                if current not in adherence_dates:
                    quality["gaps"].append({"date": current.isoformat(), "type": "adherence"})
                current += timedelta(days=1)

        # Detect anomalies
        for record in self.adherence_data:
            # Anomaly: negative adherence rate
            if record["adherence_rate"] < 0:
                quality["anomalies"].append(
                    {
                        "date": record["date"],
                        "type": "negative_adherence",
                        "value": record["adherence_rate"],
                    }
                )

        # Calculate quality score (0 - 100)
        completeness_score = adherence_completeness * 40
        consistency_score = 30 if len(quality["anomalies"]) == 0 else 20
        richness_score = (
            20 if len(self.cv_coupling_values) > 0 and len(self.wellness_data) > 0 else 10
        )
        timeliness_score = 10  # Assume timestamps are correct if data exists

        quality["score"] = int(
            completeness_score + consistency_score + richness_score + timeliness_score
        )

        # Grade
        if quality["score"] >= 90:
            quality["grade"] = "A"
        elif quality["score"] >= 80:
            quality["grade"] = "B"
        elif quality["score"] >= 70:
            quality["grade"] = "C"
        else:
            quality["grade"] = "D"

        print(f"   📊 Quality Score: {quality['score']}/100 (Grade: {quality['grade']})")
        print(f"   ✅ Completeness: {adherence_completeness * 100:.1f}%")
        print(f"   ⚠️  Gaps: {len(quality['gaps'])}")
        print(f"   ⚠️  Anomalies: {len(quality['anomalies'])}")

        return quality

    def calculate_adherence_metrics(self) -> dict[str, Any]:
        """Calculate adherence metrics from Intervals.icu events.

        Source of truth: Intervals.icu events
        - WORKOUT events with paired_activity_id = completed sessions
        - NOTE events with [SAUTÉE] = skipped sessions
        - NOTE events with [REMPLACÉE] = replaced sessions
        - NOTE events with [ANNULÉE] = cancelled sessions

        Returns:
            Dict with adherence rate, completed, skipped, replaced, cancelled details
        """
        print("\n📊 Calculating adherence metrics...")

        if not self.events_data:
            print("   ⚠️  No events data")
            return {}

        # Count completed workouts (WORKOUT events with paired activity)
        completed_workouts = [
            e
            for e in self.events_data
            if e.get("category") == "WORKOUT" and e.get("paired_activity_id")
        ]

        # Total planned = completed + skipped + replaced + cancelled
        total_planned = (
            len(completed_workouts)
            + len(self.skipped_sessions)
            + len(self.replaced_sessions)
            + len(self.cancelled_sessions)
        )

        total_completed = len(completed_workouts)
        total_skipped = len(self.skipped_sessions)
        total_replaced = len(self.replaced_sessions)
        total_cancelled = len(self.cancelled_sessions)

        # Calculate adherence rate (strict: only completed count as success)
        adherence_rate = total_completed / total_planned if total_planned > 0 else 0

        # Extract skipped/replaced dates and details
        skipped_details = [
            {
                "date": s["date"],
                "name": s["name"].replace("[SAUTÉE] ", ""),
                "reason": s["reason"],
            }
            for s in self.skipped_sessions
        ]

        replaced_details = [
            {
                "date": r["date"],
                "name": r["name"].replace("[REMPLACÉE] ", ""),
                "reason": r["reason"],
            }
            for r in self.replaced_sessions
        ]

        cancelled_details = [
            {
                "date": c["date"],
                "name": c["name"].replace("[ANNULÉE] ", ""),
                "reason": c["reason"],
            }
            for c in self.cancelled_sessions
        ]

        # Pattern by day of week (only for completed workouts)
        day_patterns = {}
        for workout in completed_workouts:
            date_str = workout.get("start_date_local", "").split("T")[0]
            if not date_str:
                continue
            date = datetime.strptime(date_str, "%Y-%m-%d")
            day_name = date.strftime("%A")
            if day_name not in day_patterns:
                day_patterns[day_name] = {"planned": 0, "completed": 0}
            day_patterns[day_name]["completed"] += 1

        # Add skipped/replaced/cancelled to planned counts
        for session in self.skipped_sessions + self.replaced_sessions + self.cancelled_sessions:
            date = datetime.strptime(session["date"], "%Y-%m-%d")
            day_name = date.strftime("%A")
            if day_name not in day_patterns:
                day_patterns[day_name] = {"planned": 0, "completed": 0}
            day_patterns[day_name]["planned"] += 1

        # Also count completed in planned
        for day_name in day_patterns:
            day_patterns[day_name]["planned"] += day_patterns[day_name]["completed"]

        # Analyze skip reasons (cluster into categories)
        skip_reasons_analysis = self.analyze_skip_reasons(self.skipped_sessions)

        # Analyze day-of-week patterns with risk scoring
        day_patterns_analysis = self.analyze_day_of_week_patterns(day_patterns)

        # Analyze workout type patterns
        # Build all_sessions list (completed + skipped + replaced + cancelled)
        all_sessions = []
        # Add completed workouts
        for workout in completed_workouts:
            all_sessions.append({"name": workout.get("name", "")})
        # Add skipped/replaced/cancelled
        for session in self.skipped_sessions + self.replaced_sessions + self.cancelled_sessions:
            all_sessions.append({"name": session.get("name", "")})

        workout_type_patterns_analysis = self.analyze_workout_type_patterns(
            completed_workouts, all_sessions
        )

        metrics = {
            "rate": adherence_rate,
            "completed": total_completed,
            "planned": total_planned,
            "skipped": total_skipped,
            "replaced": total_replaced,
            "cancelled": total_cancelled,
            "skipped_details": skipped_details,
            "replaced_details": replaced_details,
            "cancelled_details": cancelled_details,
            "day_patterns": day_patterns,
            "skip_reasons_analysis": skip_reasons_analysis,
            "day_patterns_analysis": day_patterns_analysis,
            "workout_type_patterns_analysis": workout_type_patterns_analysis,
        }

        print(f"   ✅ Adherence Rate: {adherence_rate * 100:.1f}%")
        print(f"   ✅ Completed: {total_completed}/{total_planned}")
        print(f"   ⚠️  Skipped: {total_skipped}")
        print(f"   ⚠️  Replaced: {total_replaced}")
        print(f"   ⚠️  Cancelled: {total_cancelled}")

        return metrics

    def calculate_tss_metrics(self) -> dict[str, Any]:
        """Calculate TSS metrics (planned vs actual).

        Returns:
            Dict with TSS planned, actual, completion rate
        """
        print("\n📊 Calculating TSS metrics...")

        # TSS planned from events (handle None values)
        tss_planned = sum(e.get("icu_training_load") or 0 for e in self.events_data)

        # TSS actual from activities (handle None values)
        tss_actual = sum(a.get("icu_training_load") or 0 for a in self.activities_data)

        completion_rate = tss_actual / tss_planned if tss_planned > 0 else 0

        avg_daily_planned = tss_planned / self.duration_days if self.duration_days > 0 else 0
        avg_daily_actual = tss_actual / self.duration_days if self.duration_days > 0 else 0

        metrics = {
            "planned_total": tss_planned,
            "actual_total": tss_actual,
            "completion_rate": completion_rate,
            "avg_daily_planned": avg_daily_planned,
            "avg_daily_actual": avg_daily_actual,
        }

        print(f"   ✅ TSS Planned: {tss_planned:.0f}")
        print(f"   ✅ TSS Actual: {tss_actual:.0f}")
        print(f"   ✅ Completion Rate: {completion_rate * 100:.1f}%")

        return metrics

    def analyze_tsb_trajectory(self) -> dict[str, Any]:
        """Analyze TSB evolution over period.

        Returns:
            Dict with TSB start, end, trajectory, average
        """
        print("\n📊 Analyzing TSB trajectory...")

        if not self.wellness_data:
            print("   ⚠️  No wellness data")
            return {}

        # Sort by date
        wellness_sorted = sorted(self.wellness_data, key=lambda x: x.get("id", ""))

        tsb_values = [w.get("tsb", 0) for w in wellness_sorted]
        ctl_values = [w.get("ctl", 0) for w in wellness_sorted]
        atl_values = [w.get("atl", 0) for w in wellness_sorted]

        trajectory = [
            {
                "date": w.get("id"),
                "tsb": w.get("tsb", 0),
                "ctl": w.get("ctl", 0),
                "atl": w.get("atl", 0),
            }
            for w in wellness_sorted
        ]

        metrics = {
            "start_tsb": tsb_values[0] if tsb_values else 0,
            "end_tsb": tsb_values[-1] if tsb_values else 0,
            "avg_tsb": sum(tsb_values) / len(tsb_values) if tsb_values else 0,
            "trajectory": trajectory,
            "start_ctl": ctl_values[0] if ctl_values else 0,
            "end_ctl": ctl_values[-1] if ctl_values else 0,
            "start_atl": atl_values[0] if atl_values else 0,
            "end_atl": atl_values[-1] if atl_values else 0,
        }

        print(f"   ✅ TSB: {metrics['start_tsb']:.1f} → {metrics['end_tsb']:.1f}")
        print(f"   ✅ CTL: {metrics['start_ctl']:.1f} → {metrics['end_ctl']:.1f}")
        print(f"   ✅ ATL: {metrics['start_atl']:.1f} → {metrics['end_atl']:.1f}")

        return metrics

    def calculate_cv_coupling_metrics(self) -> dict[str, Any]:
        """Calculate cardiovascular coupling metrics.

        Returns:
            Dict with average coupling, count, quality assessment
        """
        print("\n📊 Calculating cardiovascular coupling metrics...")

        if not self.cv_coupling_values:
            print("   ⚠️  No CV coupling data")
            return {"avg": 0, "count": 0, "quality": "NO_DATA"}

        avg_coupling = sum(self.cv_coupling_values) / len(self.cv_coupling_values)

        # Quality assessment (< 7.5% = good aerobic quality)
        if avg_coupling < 0.025:  # <2.5%
            quality = "EXCELLENT"
        elif avg_coupling < 0.05:  # <5%
            quality = "GOOD"
        elif avg_coupling < 0.075:  # <7.5%
            quality = "ACCEPTABLE"
        else:
            quality = "POOR"

        metrics = {
            "avg": avg_coupling,
            "count": len(self.cv_coupling_values),
            "quality": quality,
        }

        print(f"   ✅ Avg CV Coupling: {avg_coupling * 100:.1f}% ({quality})")
        print(f"   ✅ Samples: {len(self.cv_coupling_values)}")

        return metrics

    def run_analysis(self) -> dict[str, Any]:
        """Run complete baseline analysis.

        Returns:
            Complete analysis results dict
        """
        print("=" * 70)
        print("🔬 BASELINE PRELIMINARY ANALYSIS")
        print("=" * 70)
        print()

        # Load all data
        self.load_adherence_data()
        self.load_intervals_data()
        self.parse_skipped_replaced_sessions()  # Parse NOTE events for skipped/replaced
        self.unsolicited_activities = self.detect_unsolicited_activities()
        self.load_cardiovascular_coupling()

        # Validate quality
        quality = self.validate_data_quality()

        # Calculate metrics
        adherence = self.calculate_adherence_metrics()
        tss = self.calculate_tss_metrics()
        cv_coupling = self.calculate_cv_coupling_metrics()
        tsb = self.analyze_tsb_trajectory()

        # Calculate unsolicited metrics
        total_unsolicited_tss = sum(a["tss"] for a in self.unsolicited_activities)
        actual_tss = tss.get("actual_total", 0)
        unsolicited_percentage = (total_unsolicited_tss / actual_tss * 100) if actual_tss > 0 else 0

        # Assemble results
        results = {
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "period_start": self.start_date.isoformat(),
                "period_end": self.end_date.isoformat(),
                "duration_days": self.duration_days,
                "version": "2.0.0",  # Updated for Sprint R9.F
            },
            "quality": quality,
            "adherence": adherence,
            "tss": tss,
            "tsb": tsb,
            "cardiovascular_coupling": cv_coupling,
            "unsolicited_activities": {
                "total_count": len(self.unsolicited_activities),
                "total_tss": total_unsolicited_tss,
                "percentage_of_total": unsolicited_percentage,
                "details": self.unsolicited_activities,
            },
        }

        print()
        print("=" * 70)
        print("✅ ANALYSIS COMPLETE")
        print("=" * 70)

        return results

    def generate_json_output(self, results: dict[str, Any]) -> Path:
        """Generate JSON dataset output.

        Args:
            results: Analysis results dict

        Returns:
            Path to generated JSON file
        """
        output_file = self.output_dir / "baseline_preliminary.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n📄 JSON dataset: {output_file}")
        return output_file

    def generate_markdown_report(self, results: dict[str, Any]) -> Path:
        """Generate Markdown report.

        Args:
            results: Analysis results dict

        Returns:
            Path to generated markdown file
        """
        output_file = self.output_dir / "baseline_report_s076_s077.md"

        report = self._format_markdown_report(results)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"📄 Markdown report: {output_file}")
        return output_file

    def _format_markdown_report(self, results: dict[str, Any]) -> str:
        """Format analysis results as markdown report."""
        metadata = results["metadata"]
        quality = results["quality"]
        adherence = results.get("adherence", {})
        tss = results.get("tss", {})
        tsb = results.get("tsb", {})
        cv_coupling = results.get("cardiovascular_coupling", {})

        report = f"""# Rapport Baseline S076 - S077

**Analyse Préliminaire - Infrastructure Monitoring**

Généré le: {datetime.now().strftime("%d/%m/%Y %H:%M")}

---

## 📅 Période Analysée

- **Dates**: {metadata['period_start']} → {metadata['period_end']}
- **Durée**: {metadata['duration_days']} jours
- **Semaines**: S076 (complète), S077 (partielle)
- **Version**: {metadata['version']}

---

## 1. 📊 Synthèse Adhérence

### Taux Global
- **Adherence Rate**: {adherence.get('rate', 0) * 100:.1f}%
- **Séances complétées**: {adherence.get('completed', 0)}/{adherence.get('planned', 0)}
- **Séances sautées**: {adherence.get('skipped', 0)}
- **Séances remplacées**: {adherence.get('replaced', 0)}
- **Séances annulées**: {adherence.get('cancelled', 0)}

### Détail Séances Non Complétées
"""

        # Skipped sessions
        if adherence.get("skipped_details"):
            report += "\n#### ⏭️ Séances Sautées\n"
            for detail in adherence["skipped_details"]:
                report += f"- **{detail['date']}**: {detail['name']}\n"
                report += f"  - Raison: {detail['reason']}\n"

        # Replaced sessions
        if adherence.get("replaced_details"):
            report += "\n#### 🔄 Séances Remplacées\n"
            for detail in adherence["replaced_details"]:
                report += f"- **{detail['date']}**: {detail['name']}\n"
                report += f"  - Raison: {detail['reason']}\n"

        # Cancelled sessions
        if adherence.get("cancelled_details"):
            report += "\n#### ❌ Séances Annulées\n"
            for detail in adherence["cancelled_details"]:
                report += f"- **{detail['date']}**: {detail['name']}\n"
                report += f"  - Raison: {detail['reason']}\n"

        # If nothing skipped/replaced/cancelled
        if (
            not adherence.get("skipped_details")
            and not adherence.get("replaced_details")
            and not adherence.get("cancelled_details")
        ):
            report += "✅ Aucune séance manquée, remplacée ou annulée\n"

        report += """
### Patterns par Jour de Semaine

"""

        if adherence.get("day_patterns"):
            report += "| Jour | Planifié | Complété | Taux |\n"
            report += "|------|----------|----------|------|\n"
            for day, stats in adherence["day_patterns"].items():
                planned = stats["planned"]
                completed = stats["completed"]
                rate = completed / planned * 100 if planned > 0 else 0
                report += f"| {day} | {planned} | {completed} | {rate:.0f}% |\n"

        # NEW: Section 1.1 - Unsolicited Activities Analysis
        unsolicited = results.get("unsolicited_activities", {})
        if unsolicited.get("total_count", 0) > 0:
            report += f"""
### 🏃 Activités Non Sollicitées

- **Total**: {unsolicited.get('total_count', 0)} activités
- **TSS non planifié**: {unsolicited.get('total_tss', 0):.0f}
- **% du TSS total**: {unsolicited.get('percentage_of_total', 0):.1f}%

#### Détail
"""
            for activity in unsolicited.get("details", [])[:5]:  # Limit to first 5
                report += (
                    f"- **{activity['date']}**: {activity['name']} ({activity['tss']:.0f} TSS)\n"
                )
                if activity.get("avg_power"):
                    report += f"  - Puissance: {activity['avg_power']:.0f}W"
                    if activity.get("normalized_power"):
                        report += f" (NP: {activity['normalized_power']:.0f}W)"
                    report += "\n"

            # Explain TSS overload if applicable
            if unsolicited.get("percentage_of_total", 0) > 10:
                report += f"""
**💡 Analyse** : Les activités non sollicitées représentent {unsolicited.get('percentage_of_total', 0):.0f}% du TSS total, ce qui explique en grande partie la sur-charge observée (+{(tss.get('completion_rate', 1) - 1) * 100:.0f}% TSS vs planifié).
"""

        # NEW: Section 1.2 - Skip Reasons Analysis
        skip_reasons = adherence.get("skip_reasons_analysis", {})
        if skip_reasons.get("total", 0) > 0:
            report += f"""
### 🔍 Analyse Raisons Séances Sautées

- **Total séances analysées**: {skip_reasons.get('total', 0)}

#### Distribution par Catégorie
"""
            for category, stats in skip_reasons.get("distribution", {}).items():
                report += f"- **{category.replace('_', ' ').title()}**: {stats['count']} séances ({stats['percentage']:.0f}%)\n"

            # Dominant category analysis
            if skip_reasons.get("distribution"):
                dominant = max(skip_reasons["distribution"].items(), key=lambda x: x[1]["count"])
                dominant_category = dominant[0].replace("_", " ").title()
                dominant_pct = dominant[1]["percentage"]
                report += f"""
**💡 Pattern dominant** : {dominant_category} ({dominant_pct:.0f}% des séances sautées)
"""

        # NEW: Section 1.3 - Day/Type Patterns Analysis
        day_analysis = adherence.get("day_patterns_analysis", {})
        type_analysis = adherence.get("workout_type_patterns_analysis", {})

        if day_analysis.get("high_risk_days") or type_analysis.get("high_risk_types"):
            report += """
### 📊 Patterns à Risque

"""
            # High-risk days
            if day_analysis.get("high_risk_days"):
                report += "#### 📅 Jours à Risque\n"
                for day_risk in day_analysis["high_risk_days"]:
                    risk_emoji = "🔴" if day_risk["risk_score"] >= 60 else "🟠"
                    report += f"- {risk_emoji} **{day_risk['day']}**: {day_risk['adherence_rate'] * 100:.0f}% adherence (Risque: {day_risk['risk_score']:.0f}/100)\n"

            # High-risk types
            if type_analysis.get("high_risk_types"):
                report += "\n#### 🏋️ Types d'Entraînement à Risque\n"
                for type_risk in type_analysis["high_risk_types"]:
                    risk_emoji = "🔴" if type_risk["risk_score"] >= 60 else "🟠"
                    report += f"- {risk_emoji} **{type_risk['type']}**: {type_risk['adherence_rate'] * 100:.0f}% adherence (Risque: {type_risk['risk_score']:.0f}/100)\n"

            # Recommendations
            all_recommendations = []
            if day_analysis.get("recommendations"):
                all_recommendations.extend(day_analysis["recommendations"])
            if type_analysis.get("recommendations"):
                all_recommendations.extend(type_analysis["recommendations"])

            if all_recommendations:
                report += "\n#### 💡 Recommandations Patterns\n"
                for rec in all_recommendations:
                    report += f"{rec}\n"

        report += f"""
---

## 2. 💪 Charge Entraînement (TSS)

### Volumes
- **TSS Planifié**: {tss.get('planned_total', 0):.0f}
- **TSS Réalisé**: {tss.get('actual_total', 0):.0f}
- **Ratio Completion**: {tss.get('completion_rate', 0) * 100:.1f}%

### Moyennes Quotidiennes
- **TSS/jour Planifié**: {tss.get('avg_daily_planned', 0):.1f}
- **TSS/jour Réalisé**: {tss.get('avg_daily_actual', 0):.1f}

### Analyse
"""

        completion_rate = tss.get("completion_rate", 0)
        if completion_rate > 1.1:
            report += f"⚠️ **Sur-charge** : TSS réalisé significativement supérieur au planifié (+{(completion_rate - 1) * 100:.0f}%). Risque fatigue accumulée.\n"
        elif completion_rate < 0.85:
            report += f"⚠️ **Sous-charge** : TSS réalisé inférieur au planifié (-{(1 - completion_rate) * 100:.0f}%). Progression potentiellement limitée.\n"
        else:
            report += "✅ **Charge optimale** : TSS réalisé cohérent avec planification.\n"

        report += f"""
---

## 3. 📈 Evolution Fitness (TSB/CTL/ATL)

### Début Période ({metadata['period_start']})
- **TSB**: {tsb.get('start_tsb', 0):.1f}
- **CTL**: {tsb.get('start_ctl', 0):.1f}
- **ATL**: {tsb.get('start_atl', 0):.1f}

### Fin Période ({metadata['period_end']})
- **TSB**: {tsb.get('end_tsb', 0):.1f}
- **CTL**: {tsb.get('end_ctl', 0):.1f}
- **ATL**: {tsb.get('end_atl', 0):.1f}

### Evolution TSB
- **TSB Moyen**: {tsb.get('avg_tsb', 0):.1f}
- **Variation**: {tsb.get('start_tsb', 0):.1f} → {tsb.get('end_tsb', 0):.1f} ({tsb.get('end_tsb', 0) - tsb.get('start_tsb', 0):+.1f})

### Analyse Forme
"""

        end_tsb = tsb.get("end_tsb", 0)
        if end_tsb > 10:
            report += (
                "✅ **Forme excellente** : TSB élevé, prêt pour séances intensives ou tests.\n"
            )
        elif end_tsb > 5:
            report += "✅ **Forme bonne** : TSB positif, condition favorable.\n"
        elif end_tsb > -5:
            report += "⚠️ **Forme neutre** : TSB proche de zéro, équilibre fitness/fatigue.\n"
        else:
            report += "⚠️ **Fatigue** : TSB négatif, besoin récupération.\n"

        report += f"""
---

## 4. ❤️ Qualité Cardiovasculaire

### Découplage Cardiovasculaire
- **Moyenne**: {cv_coupling.get('avg', 0) * 100:.1f}%
- **Échantillons**: {cv_coupling.get('count', 0)}
- **Qualité**: {cv_coupling.get('quality', 'NO_DATA')}

### Référence
- **< 2.5%**: Excellent (aérobie optimal)
- **2.5 - 5%**: Bon (qualité maintenue)
- **5 - 7.5%**: Acceptable (drift léger)
- **> 7.5%**: Attention (qualité dégradée)

---

## 5. 🔍 Qualité Données (Data Quality Score)

### Score Global
- **Score**: {quality['score']}/100
- **Grade**: {quality['grade']}

### Détail Complétude
- **Adherence**: {quality['completeness'].get('adherence', 0) * 100:.0f}%
- **Wellness**: {quality['completeness'].get('wellness', 0) * 100:.0f}%
- **Activities**: {quality['completeness'].get('activities', 0)} records

### Gaps Détectés
"""

        if quality["gaps"]:
            report += f"⚠️ **{len(quality['gaps'])} jours manquants**:\n"
            for gap in quality["gaps"][:5]:  # Limit to first 5
                report += f"- {gap['date']} ({gap['type']})\n"
            if len(quality["gaps"]) > 5:
                report += f"- ... et {len(quality['gaps']) - 5} autres\n"
        else:
            report += "✅ Aucun gap détecté\n"

        report += "\n### Anomalies\n"

        if quality["anomalies"]:
            report += f"⚠️ **{len(quality['anomalies'])} anomalies**:\n"
            for anomaly in quality["anomalies"]:
                report += f"- {anomaly['date']}: {anomaly['type']}\n"
        else:
            report += "✅ Aucune anomalie détectée\n"

        report += """
---

## 6. 💡 Insights Clés

### Forces
"""

        insights_positive = []
        insights_negative = []
        insights_neutral = []

        # Adherence insights
        if adherence.get("rate", 0) >= 0.90:
            insights_positive.append(
                f"**Discipline excellente** : {adherence.get('rate', 0) * 100:.0f}% adherence maintenue"
            )
        elif adherence.get("rate", 0) >= 0.80:
            insights_neutral.append(
                f"**Discipline correcte** : {adherence.get('rate', 0) * 100:.0f}% adherence"
            )
        else:
            insights_negative.append(
                f"**Adherence limitée** : {adherence.get('rate', 0) * 100:.0f}% seulement"
            )

        # CV coupling insights
        if cv_coupling.get("quality") == "EXCELLENT":
            insights_positive.append(
                f"**Qualité aérobie optimale** : {cv_coupling.get('avg', 0) * 100:.1f}% découplage CV"
            )
        elif cv_coupling.get("quality") in ["GOOD", "ACCEPTABLE"]:
            insights_neutral.append(
                f"**Qualité aérobie maintenue** : {cv_coupling.get('avg', 0) * 100:.1f}% découplage CV"
            )

        # TSS insights
        if 0.95 <= tss.get("completion_rate", 0) <= 1.05:
            insights_positive.append("**Planification respectée** : TSS réel cohérent avec plan")
        elif tss.get("completion_rate", 0) > 1.1:
            insights_negative.append(
                f"**Sur-charge** : +{(tss.get('completion_rate', 0) - 1) * 100:.0f}% TSS vs planifié"
            )

        # Data quality insights
        if quality["score"] >= 90:
            insights_positive.append(
                f"**Infrastructure monitoring validée** : Score qualité {quality['score']}/100"
            )

        for insight in insights_positive:
            report += f"- ✅ {insight}\n"

        if insights_neutral:
            report += "\n### Points Neutres\n"
            for insight in insights_neutral:
                report += f"- ℹ️ {insight}\n"

        if insights_negative:
            report += "\n### Points Vigilance\n"
            for insight in insights_negative:
                report += f"- ⚠️ {insight}\n"

        report += """
---

## 7. 🎯 Recommandations

### Court Terme (S078 - S079)

"""

        # Recommendations based on TSB
        if end_tsb < -5:
            report += "1. **Récupération prioritaire** : TSB négatif, réduire volume 20 - 30%\n"
        elif end_tsb < 5 and completion_rate > 1.1:
            report += "1. **Affûtage léger** : Réduire volume 10 - 20% pour optimiser fraîcheur\n"
        else:
            report += "1. **Maintien plan** : Condition favorable, continuer programme\n"

        # Recommendations based on adherence
        if adherence.get("rate", 0) < 0.85:
            report += "2. **Améliorer adherence** : Identifier causes séances manquées\n"

        # Recommendations for CV quality
        if cv_coupling.get("quality") == "POOR":
            report += (
                "3. **Attention qualité Z2** : Découplage élevé, vérifier intensité endurance\n"
            )

        report += """
### Préparation Tests S080 (10 - 16 fév)

1. **Timing optimal** :
   - Semaine S079 (2 - 8 fév) : Affûtage léger
   - TSB cible : +10 à +15
   - Réduction TSS : -30 à -40%

2. **Protocole tests** :
   - Reprendre Zwift Camp Baseline (Flat Out Fast, Climb Control, etc.)
   - Conditions : Sommeil >7h, VFC normale, hydratation optimale

3. **Métriques post-tests** :
   - FTP mesuré
   - Comparaison vs Octobre 2025
   - Calibration PID complète (49 jours données + FTP)

### Collecte Données PID

✅ **Infrastructure validée** : Monitoring adherence opérationnel
✅ **Données complètes** : Adherence, TSS, TSB, CV coupling
⏳ **Tests S080** : Dernière pièce pour calibration PID

---

## 8. 📚 Annexes

### A. Contexte Historique

**Tests Zwift Camp Baseline (Octobre 2025)** :
- Dates : 11 - 14 octobre 2025
- FTP estimé : ~220W (basé sur NP tests)
- Gap temporel : 15 semaines depuis dernier test
- Cycle PID : Largement dépassé (vs 6 - 8 sem recommandé)

### B. Méthodologie

**Sources données** :
- Adherence : `~/data/monitoring/workout_adherence.jsonl`
- Intervals.icu : Wellness, Activities, Events (API)
- Cardiovascular : `logs/weekly_reports/S0XX/workout_history_*.md`

**Outils** :
- BaselineAnalyzer v1.0.0
- IntervalsClient (API wrapper)
- Python 3.11+

---

**Rapport généré automatiquement par BaselineAnalyzer**

*Sprint R9.F - Advanced Pattern Analysis*
"""

        return report


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Baseline Preliminary Analysis")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--output", default=None, help="Output directory (default: ~/data/pid)")

    args = parser.parse_args()

    # Create analyzer
    analyzer = BaselineAnalyzer(
        start_date=args.start,
        end_date=args.end,
        output_dir=Path(args.output) if args.output else None,
    )

    # Run analysis
    results = analyzer.run_analysis()

    # Generate outputs
    analyzer.generate_json_output(results)
    analyzer.generate_markdown_report(results)

    print("\n✅ Baseline analysis complete!")
    print(f"   JSON: {analyzer.output_dir / 'baseline_preliminary.json'}")
    print(f"   Report: {analyzer.output_dir / 'baseline_report_s076_s077.md'}")


if __name__ == "__main__":
    main()
