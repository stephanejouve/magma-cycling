"""Pattern analysis methods for BaselineAnalyzer."""

import re
from typing import Any


class PatternAnalysisMixin:
    """Analyse patterns & scoring risque."""

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
