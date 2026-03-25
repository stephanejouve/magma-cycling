"""ProcessingMixin for WeeklyAggregator — data transformation and aggregation."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ProcessingMixin:
    """Data processing and aggregation methods for weekly analysis."""

    def _compute_weekly_summary(self, activities: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Calculate summary hebdomadaire.

        Note: Utilise champs Intervals.icu avec préfixe 'icu_':
        - icu_training_load (TSS)
        - icu_intensity (IF en %, nécessite normalisation).
        """
        # Defensive: filter out None values before summing

        summary = {
            "total_sessions": len(activities),
            "total_tss": sum((a.get("icu_training_load") or 0) for a in activities),
            "total_duration": sum((a.get("moving_time") or 0) for a in activities),
            "avg_tss": 0,
            "avg_if": 0,
            "total_distance": sum((a.get("distance") or 0) for a in activities),
            "avg_pedal_balance": None,
            "pedal_balance_imbalance": False,
        }

        if activities:
            summary["avg_tss"] = summary["total_tss"] / len(activities)

            # IF moyen (normaliser depuis pourcentage) - Defensive: handle None
            ifs = [
                (a.get("icu_intensity") or 0) / 100
                for a in activities
                if a.get("icu_intensity") and a.get("icu_intensity") > 0  # type: ignore[operator]  # Safe: checked for None in first condition
            ]
            if ifs:
                summary["avg_if"] = sum(ifs) / len(ifs)

            # Pedal balance moyen
            balances = [
                a.get("avg_lr_balance") for a in activities if a.get("avg_lr_balance") is not None
            ]
            if balances:
                avg_balance = sum(balances) / len(balances)
                summary["avg_pedal_balance"] = avg_balance
                # Déséquilibre si >52% ou <48% (tolérance 2%)
                summary["pedal_balance_imbalance"] = avg_balance > 52.0 or avg_balance < 48.0

        # Métriques finales (dernière journée)
        if activities:
            last_activity = activities[-1]

            # Extract wellness metrics from last activity
            from magma_cycling.utils.metrics import extract_wellness_metrics

            final_metrics = extract_wellness_metrics(last_activity)
            summary["final_metrics"] = final_metrics

        return summary

    def _process_workouts_detailed(
        self, activities: list[dict[str, Any]], feedback: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Process workouts avec détails pour workout_history.

        Map champs Intervals.icu (icu_ prefix) vers format interne:
        - icu_training_load → tss
        - icu_intensity (%) → if (normalisé 0.0-1.0)
        - icu_weighted_avg_watts → normalized_power
        - icu_average_watts → average_power
        - avg_lr_balance → pedal_balance (%).
        """
        workouts = []

        for i, activity in enumerate(activities, 1):
            activity_id = str(activity.get("id", ""))

            # Normaliser IF depuis pourcentage (66.36% → 0.66)
            icu_intensity = activity.get("icu_intensity", 0)
            if_normalized = icu_intensity / 100 if icu_intensity > 10 else icu_intensity

            workout = {
                "session_number": i,
                "date": activity.get("start_date_local", ""),
                "activity_id": activity_id,
                "name": activity.get("name", "Unknown"),
                "type": activity.get("type", "Ride"),
                "duration": activity.get("moving_time", 0),
                "tss": activity.get("icu_training_load", 0),
                "if": if_normalized,
                "normalized_power": activity.get("icu_weighted_avg_watts", 0),
                "average_power": activity.get("icu_average_watts", 0),
                "average_hr": activity.get("average_hr", 0),
                "max_hr": activity.get("max_hr", 0),
                "pedal_balance": activity.get("avg_lr_balance"),  # Left/Right balance (%)
            }

            # Ajouter feedback si disponible
            if activity_id in feedback:
                workout["feedback"] = feedback[activity_id]

            # Ajouter métriques gear (Di2) si activité outdoor
            is_outdoor = activity.get("trainer") is False or activity.get("type") == "Ride"
            if is_outdoor and activity_id:
                try:
                    gear_metrics = self._extract_gear_metrics(activity_id)
                    if gear_metrics:
                        workout["gear_metrics"] = gear_metrics
                        logger.debug(
                            f"Extracted gear metrics for {activity_id}: "
                            f"{gear_metrics.get('shifts', 0)} shifts"
                        )
                except Exception as e:
                    logger.warning(f"Failed to extract gear metrics for {activity_id}: {e}")

            workouts.append(workout)

        return workouts

    def _process_metrics_evolution(self, metrics_daily: list[dict[str, Any]]) -> dict[str, Any]:
        """Process évolution métriques."""
        if not metrics_daily:
            return {}

        evolution = {"daily": metrics_daily, "trends": {}}

        # Calculer tendances - Defensive: handle None values
        if len(metrics_daily) >= 2:
            first = metrics_daily[0]
            last = metrics_daily[-1]

            # Calculate metrics change using centralized utility
            from magma_cycling.utils.metrics import calculate_metrics_change

            evolution["trends"] = calculate_metrics_change(first, last)  # type: ignore[assignment]  # Complex nested dict type inference

        return evolution

    def _identify_protocol_changes(
        self, learnings: list[str], metrics_evolution: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Identify changements protocoles nécessaires."""
        adaptations = []

        # Check TSB trends - Defensive: handle None
        trends = metrics_evolution.get("trends", {})
        tsb_change = trends.get("tsb_change")

        if tsb_change is not None and tsb_change < -10:
            adaptations.append(
                {
                    "type": "recovery",
                    "reason": f"TSB dropped {tsb_change:.1f} points",
                    "recommendation": "Add recovery day next week",
                }
            )

        # Check pedal balance imbalance in learnings
        for learning in learnings:
            if "Déséquilibre pédalage" in learning:
                adaptations.append(
                    {
                        "type": "pedal_balance",
                        "reason": learning,
                        "recommendation": "Intégrer exercices unilatéraux (single leg drills) "
                        "et vérifier position/réglages",
                    }
                )
                break  # Only add once

        return adaptations

    def _compute_compliance(
        self, activities: list[dict[str, Any]], planned: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Calculate compliance planifié vs exécuté."""
        compliance = {
            "planned_count": len(planned),
            "executed_count": len(activities),
            "rate": 0,
            "missed": [],
            "extra": [],
        }

        if planned:
            compliance["rate"] = (len(activities) / len(planned)) * 100

        # Identifier séances manquées (simplification)
        if len(activities) < len(planned):
            compliance["missed"] = planned[len(activities) :]

        return compliance

    def _analyze_wellness(self, wellness: dict[str, Any]) -> dict[str, Any]:
        """Analyze données wellness."""
        insights = {"sleep_quality_avg": 0, "sleep_hours_avg": 0, "weight_trend": 0, "hrv_avg": 0}

        if not wellness:
            return insights

        # Moyennes - Defensive: handle None values
        sleep_qualities = [
            w["sleep_quality"]
            for w in wellness.values()
            if w.get("sleep_quality") is not None and w.get("sleep_quality") > 0
        ]

        if sleep_qualities:
            insights["sleep_quality_avg"] = sum(sleep_qualities) / len(sleep_qualities)

        sleep_hours = [
            w["sleep_hours"]
            for w in wellness.values()
            if w.get("sleep_hours") is not None and w.get("sleep_hours") > 0
        ]

        if sleep_hours:
            insights["sleep_hours_avg"] = sum(sleep_hours) / len(sleep_hours)

        # Tendance poids - Defensive: handle None values
        weights = [
            (date, w["weight"])
            for date, w in wellness.items()
            if w.get("weight") is not None and w.get("weight") > 0
        ]

        if len(weights) >= 2:
            weights.sort()
            insights["weight_trend"] = weights[-1][1] - weights[0][1]

        return insights
