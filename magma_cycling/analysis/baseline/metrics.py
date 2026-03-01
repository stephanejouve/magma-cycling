"""Metrics calculation methods for BaselineAnalyzer."""

from datetime import datetime, timedelta
from typing import Any


class MetricsMixin:
    """Calcul métriques."""

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
