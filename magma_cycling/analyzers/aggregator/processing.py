"""Processing mixin for WeeklyAggregator.

Transformation et enrichissement des données brutes.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ProcessingMixin:
    """Transform and enrich raw training data."""

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

    def _extract_gear_metrics(self, activity_id: str) -> dict[str, Any] | None:
        """
        Extract gear metrics (Di2) from activity streams.

        Extrait métriques de changements de vitesse depuis les streams.

        Args:
            activity_id: Activity ID

        Returns:
            Dict avec métriques gear ou None si pas disponibles:
            - shifts: Nombre total de changements
            - front_shifts: Changements plateau avant
            - rear_shifts: Changements pignon arrière
            - avg_gear_ratio: Ratio moyen
            - gear_ratio_distribution: Distribution des ratios utilisés
        """
        if not self.api:
            return None

        try:
            # Fetch streams
            streams = self.api.get_activity_streams(activity_id)

            # Find gear streams
            front_gear_stream = next((s for s in streams if s.get("type") == "FrontGear"), None)
            rear_gear_stream = next((s for s in streams if s.get("type") == "RearGear"), None)
            gear_ratio_stream = next((s for s in streams if s.get("type") == "GearRatio"), None)

            if not (front_gear_stream and rear_gear_stream):
                return None  # Pas de données gear disponibles

            front_data = front_gear_stream.get("data", [])
            rear_data = rear_gear_stream.get("data", [])
            ratio_data = gear_ratio_stream.get("data", []) if gear_ratio_stream else []

            # Remove None values and calculate metrics
            front_clean = [f for f in front_data if f is not None]
            rear_clean = [r for r in rear_data if r is not None]
            ratio_clean = [r for r in ratio_data if r is not None]

            if not front_clean or not rear_clean:
                return None

            # Count shifts (changes in gear values)
            front_shifts = sum(
                1 for i in range(1, len(front_clean)) if front_clean[i] != front_clean[i - 1]
            )
            rear_shifts = sum(
                1 for i in range(1, len(rear_clean)) if rear_clean[i] != rear_clean[i - 1]
            )

            total_shifts = front_shifts + rear_shifts

            # Calculate average gear ratio
            avg_ratio = sum(ratio_clean) / len(ratio_clean) if ratio_clean else None

            # Build gear ratio distribution (top 5 most used)
            from collections import Counter

            ratio_counts = Counter(round(r, 2) for r in ratio_clean if r)
            top_ratios = dict(ratio_counts.most_common(5))

            return {
                "shifts": total_shifts,
                "front_shifts": front_shifts,
                "rear_shifts": rear_shifts,
                "avg_gear_ratio": round(avg_ratio, 2) if avg_ratio else None,
                "gear_ratio_distribution": top_ratios,
            }

        except Exception as e:
            logger.warning(f"Error extracting gear metrics for {activity_id}: {e}")
            return None

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
