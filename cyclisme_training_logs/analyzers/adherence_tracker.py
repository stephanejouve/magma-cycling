#!/usr/bin/env python3
"""
Adherence Tracker - Planned vs Realized Analysis for PID Correction.

Tracks execution adherence to planned workouts, detects patterns,
and provides corrective recommendations for closed-loop training control.

Examples:
    Track single session adherence::

        from cyclisme_training_logs.analyzers.adherence_tracker import AdherenceTracker

        tracker = AdherenceTracker()
        adherence = tracker.calculate_session_adherence(
            activity_id="i123456",
            planned_event=planned_workout_data
        )
        print(f"TSS adherence: {adherence['tss_adherence']:.1%}")

    Analyze mesocycle adherence patterns::

        mesocycle_data = tracker.analyze_mesocycle_adherence(
            weeks=["S077", "S078", "S079", "S080", "S081", "S082"]
        )
        print(mesocycle_data['insights'])

Author: Claude Code
Created: 2026-02-19
Version: 1.0.0
"""

from collections import defaultdict
from datetime import datetime

from cyclisme_training_logs.api.intervals_client import IntervalsClient
from cyclisme_training_logs.config import get_data_config, get_intervals_config


class AdherenceTracker:
    """
    Tracks adherence between planned and realized workouts.

    Captures metrics, detects patterns, and provides PID correction factors
    for closed-loop training control.
    """

    def __init__(self):
        """Initialize adherence tracker."""
        self.data_config = get_data_config()
        self.intervals_config = get_intervals_config()
        self.client = IntervalsClient(
            self.intervals_config.athlete_id, self.intervals_config.api_key
        )

    def calculate_session_adherence(
        self, activity: dict, planned_event: dict | None = None
    ) -> dict:
        """
        Calculate adherence metrics for a single session.

        Args:
            activity: Realized activity data from Intervals.icu
            planned_event: Planned workout data (optional, will fetch if None)

        Returns:
            Dict with adherence metrics

        Examples:
            >>> tracker = AdherenceTracker()
            >>> adherence = tracker.calculate_session_adherence(activity)
            >>> adherence['tss_adherence']
            0.95  # 95% adherence
        """
        # If no planned event provided, try to fetch it
        if planned_event is None:
            activity_date = datetime.fromisoformat(
                activity["start_date_local"].replace("Z", "+00:00")
            )
            planned_event = self.client.get_planned_workout(activity["id"], activity_date)

        # If still no planned event, can't calculate adherence
        if not planned_event or not planned_event.get("workout_doc"):
            return {
                "has_plan": False,
                "tss_adherence": None,
                "if_adherence": None,
                "duration_adherence": None,
                "completion": True,  # Completed, just no plan
            }

        # Extract planned metrics
        workout_doc = planned_event["workout_doc"]
        planned_tss = planned_event.get("icu_training_load", 0)
        planned_duration = workout_doc.get("duration", 0) / 60  # Convert to minutes
        planned_if = (
            planned_event.get("icu_intensity", 0) / 100.0
            if planned_event.get("icu_intensity")
            else 0
        )
        planned_avg_watts = workout_doc.get("average_watts", 0)

        # Extract realized metrics
        realized_tss = activity.get("icu_training_load", 0)
        realized_duration = activity.get("moving_time", 0) / 60  # Convert to minutes
        realized_if = (
            activity.get("icu_intensity", 0) / 100.0 if activity.get("icu_intensity") else 0
        )
        realized_avg_watts = activity.get("icu_average_watts", 0)

        # Calculate adherence percentages
        tss_adherence = (realized_tss / planned_tss) if planned_tss > 0 else None
        duration_adherence = (
            (realized_duration / planned_duration) if planned_duration > 0 else None
        )
        if_adherence = (realized_if / planned_if) if planned_if > 0 else None
        power_adherence = (
            (realized_avg_watts / planned_avg_watts) if planned_avg_watts > 0 else None
        )

        # Calculate deviations
        deviations = []
        if tss_adherence and abs(tss_adherence - 1.0) > 0.10:  # >10% deviation
            deviations.append(
                {
                    "metric": "TSS",
                    "planned": planned_tss,
                    "realized": realized_tss,
                    "deviation_pct": (tss_adherence - 1.0) * 100,
                }
            )

        if if_adherence and abs(if_adherence - 1.0) > 0.05:  # >5% deviation
            deviations.append(
                {
                    "metric": "IF",
                    "planned": planned_if,
                    "realized": realized_if,
                    "deviation_pct": (if_adherence - 1.0) * 100,
                }
            )

        return {
            "has_plan": True,
            "tss_adherence": tss_adherence,
            "if_adherence": if_adherence,
            "duration_adherence": duration_adherence,
            "power_adherence": power_adherence,
            "completion": True,
            "deviations": deviations,
            "planned": {
                "tss": planned_tss,
                "if": planned_if,
                "duration": planned_duration,
                "avg_watts": planned_avg_watts,
            },
            "realized": {
                "tss": realized_tss,
                "if": realized_if,
                "duration": realized_duration,
                "avg_watts": realized_avg_watts,
            },
        }

    def _get_week_activities(self, week_id: str) -> list[dict]:
        """
        Get all activities for a given week from workouts-history.md.

        Args:
            week_id: Week identifier (e.g., "S082")

        Returns:
            List of activity dicts with metrics
        """
        history_file = self.data_config.data_repo_path / "workouts-history.md"

        if not history_file.exists():
            return []

        # This is a simplified version - ideally we'd parse the full analysis
        # For now, just detect presence of week workouts
        # In full implementation, would extract metrics from analyses
        return []

    def analyze_mesocycle_adherence(self, weeks: list[str]) -> dict:
        """
        Analyze adherence patterns over a mesocycle (typically 6 weeks).

        Args:
            weeks: List of week IDs (e.g., ["S077", "S078", ...])

        Returns:
            Dict with aggregated adherence metrics and patterns

        Examples:
            >>> tracker = AdherenceTracker()
            >>> analysis = tracker.analyze_mesocycle_adherence(
            ...     ["S077", "S078", "S079", "S080", "S081", "S082"]
            ... )
            >>> analysis['tss_adherence_avg']
            0.85
        """
        # Load adherence data from storage
        from cyclisme_training_logs.analyzers.adherence_storage import AdherenceStorage

        storage = AdherenceStorage()
        stats = storage.calculate_mesocycle_stats(weeks)

        # Build adherence data structure for pattern detection
        adherence_data = {
            "weeks": weeks,
            "tss_adherence_values": stats.get("tss_adherence_values", []),
            "if_adherence_values": stats.get("if_adherence_values", []),
            "completion_rate_values": [],
            "cancelled_sessions": [],
            "systematic_deviations": defaultdict(list),
        }

        # Detect patterns
        patterns = self._detect_adherence_patterns(adherence_data)

        # Calculate aggregates
        avg_tss_adherence = stats.get("tss_adherence_avg", 0)
        avg_if_adherence = stats.get("if_adherence_avg", 0)

        # Calculate PID correction factor
        pid_correction_factor = 1 / avg_tss_adherence if avg_tss_adherence > 0.5 else 1.0

        # Calculate trend
        tss_trend = storage.get_adherence_trend(weeks, metric="tss")

        return {
            "weeks": weeks,
            "tss_adherence_avg": avg_tss_adherence,
            "if_adherence_avg": avg_if_adherence,
            "tss_adherence_trend": tss_trend,
            "completion_rate": 1.0 if stats.get("sessions_count", 0) > 0 else 0,
            "sessions_analyzed": stats.get("sessions_with_plan", 0),
            "total_sessions": stats.get("sessions_count", 0),
            "patterns": patterns,
            "pid_correction_factor": pid_correction_factor,
            "recommendations": self._generate_adherence_recommendations(
                avg_tss_adherence, avg_if_adherence, patterns
            ),
        }

    def _detect_adherence_patterns(self, adherence_data: dict) -> list[dict]:
        """
        Detect recurring patterns in adherence data.

        Args:
            adherence_data: Raw adherence data collected

        Returns:
            List of detected patterns with metadata
        """
        patterns = []

        # Pattern 1: Consistent under-delivery
        tss_values = adherence_data["tss_adherence_values"]
        if len(tss_values) >= 4:
            avg_adherence = sum(tss_values) / len(tss_values)
            variance = sum((x - avg_adherence) ** 2 for x in tss_values) / len(tss_values)

            if avg_adherence < 0.90 and variance < 0.01:  # Stable under-delivery
                patterns.append(
                    {
                        "type": "consistent_under_delivery",
                        "severity": "high",
                        "description": f"Adhérence TSS stable à {avg_adherence:.0%} (sous 90%)",
                        "recommendation": "Ajuster objectifs TSS à niveau soutenable ou identifier blocages",
                    }
                )

        # Pattern 2: IF systematic deviation
        if_values = adherence_data["if_adherence_values"]
        if len(if_values) >= 4:
            avg_if_adherence = sum(if_values) / len(if_values)

            if avg_if_adherence < 0.95:  # Consistently under IF
                patterns.append(
                    {
                        "type": "if_systematic_underperformance",
                        "severity": "medium",
                        "description": f"IF réalisée systématiquement {(1 - avg_if_adherence) * 100:.0f}% sous prévue",
                        "recommendation": "Réduire zones cibles de 3-5% ou vérifier FTP",
                    }
                )

        # Pattern 3: Recurring cancellations
        cancelled = adherence_data["cancelled_sessions"]
        if len(cancelled) >= 2:
            # Check if cancellations cluster on specific days
            days_cancelled = defaultdict(int)
            for session in cancelled:
                if "day" in session:
                    days_cancelled[session["day"]] += 1

            for day, count in days_cancelled.items():
                if count >= 2:
                    patterns.append(
                        {
                            "type": "recurring_cancellation",
                            "severity": "medium",
                            "description": f"{count} annulations le {day}",
                            "recommendation": f"Revoir séquençage : déplacer séances clés du {day}",
                        }
                    )

        return patterns

    def _calculate_trend(self, values: list[float]) -> str:
        """
        Calculate trend direction from list of values.

        Args:
            values: List of numeric values

        Returns:
            Trend description: "improving", "stable", "declining"
        """
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

    def _generate_adherence_recommendations(
        self, tss_adherence: float, if_adherence: float, patterns: list[dict]
    ) -> list[str]:
        """
        Generate actionable recommendations based on adherence analysis.

        Args:
            tss_adherence: Average TSS adherence
            if_adherence: Average IF adherence
            patterns: Detected patterns

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # TSS adherence recommendations
        if tss_adherence < 0.85:
            recommendations.append(
                f"**Adhérence TSS faible ({tss_adherence:.0%})** : "
                f"Réduire objectif à {int(tss_adherence * 350)} TSS/semaine OU "
                f"planifier {int(350 / tss_adherence)} TSS pour obtenir 350 effectifs"
            )
        elif tss_adherence > 1.05:
            recommendations.append(
                f"**Sur-adhérence TSS ({tss_adherence:.0%})** : "
                f"Augmenter objectifs progressivement (+5-10%)"
            )

        # IF adherence recommendations
        if if_adherence and if_adherence < 0.95:
            recommendations.append(
                f"**IF sous-estimée systématiquement ({if_adherence:.0%})** : "
                f"Réduire zones Sweet-Spot/FTP de {int((1 - if_adherence) * 100)}%"
            )

        # Pattern-based recommendations
        for pattern in patterns:
            if pattern.get("recommendation"):
                recommendations.append(
                    f"**{pattern['type'].title()}** : {pattern['recommendation']}"
                )

        # Default if no issues
        if not recommendations:
            recommendations.append("✅ Adhérence excellente, maintenir approche actuelle")

        return recommendations


def generate_adherence_report(weeks: list[str]) -> str:
    """
    Generate adherence analysis report for mesocycle.

    Args:
        weeks: List of week IDs to analyze

    Returns:
        Markdown formatted report

    Examples:
        >>> report = generate_adherence_report(["S077", "S078", "S079", "S080", "S081", "S082"])
        >>> "Adhérence" in report
        True
    """
    tracker = AdherenceTracker()

    try:
        analysis = tracker.analyze_mesocycle_adherence(weeks)

        # Check if we have data
        if analysis["sessions_analyzed"] == 0:
            return f"""
### 📊 Analyse Adhérence (Planned vs Realized)

**Période** : {weeks[0]} → {weeks[-1]}

ℹ️ **Données d'adhérence non disponibles pour ce cycle**

_L'analyse d'adhérence nécessite :_
- Workouts planifiés dans Intervals.icu
- Activités réalisées et analysées
- Données capturées via daily-sync

Cette fonctionnalité s'activera automatiquement lors des prochains cycles avec planning.

"""

        report = f"""
### 📊 Analyse Adhérence (Planned vs Realized)

**Période** : {weeks[0]} → {weeks[-1]}
**Séances analysées** : {analysis['sessions_analyzed']}/{analysis['total_sessions']}

**Performance vs Planning** :
- TSS moyen réalisé : {analysis['tss_adherence_avg']:.0%} du prévu
- IF moyenne réalisée : {analysis['if_adherence_avg']:.0%} du prévu
- Tendance TSS : {analysis['tss_adherence_trend']}

"""

        # Add patterns detected
        patterns = analysis.get("patterns", [])
        if patterns:
            report += "**Patterns détectés** :\n"
            for pattern in patterns:
                severity_emoji = {
                    "high": "🔴",
                    "medium": "⚠️",
                    "low": "ℹ️",
                }.get(pattern.get("severity", "low"), "ℹ️")

                report += f"{severity_emoji} **{pattern['description']}**\n"
                report += f"   → {pattern['recommendation']}\n\n"
        else:
            report += "✅ **Aucun pattern problématique détecté**\n\n"

        # Add recommendations
        recommendations = analysis.get("recommendations", [])
        if recommendations:
            report += "**Recommandations Adhérence** :\n"
            for rec in recommendations:
                report += f"- {rec}\n"
            report += "\n"

        # Add PID correction factor if significant
        pid_factor = analysis["pid_correction_factor"]
        if abs(pid_factor - 1.0) > 0.05:  # >5% deviation
            report += f"""
**💡 Facteur de correction PID** : {pid_factor:.2f}
"""
            if pid_factor > 1.0:
                report += f"_Planifier {int((pid_factor - 1) * 100)}% de TSS supplémentaire pour compenser sous-adhérence_\n"
            else:
                report += f"_Sur-adhérence détectée, réduire planification de {int((1 - pid_factor) * 100)}%_\n"
            report += "\n"

        return report

    except Exception as e:
        return f"""
### 📊 Analyse Adhérence

⚠️ Erreur lors de l'analyse : {e}

_Cette fonctionnalité sera disponible avec plus de données d'entraînement._

"""
