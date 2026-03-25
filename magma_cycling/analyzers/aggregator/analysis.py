"""Analysis mixin for WeeklyAggregator.

Insights, compliance, recommandations. Pur calcul, aucune dépendance externe.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class AnalysisMixin:
    """Extract insights, compliance, and recommendations."""

    def _extract_training_learnings(
        self, workouts: list[dict[str, Any]], feedback: dict[str, Any]
    ) -> list[str]:
        """Extract enseignements training (pour AI analysis).

        Args:
            workouts: Processed workouts with enriched data (tss, if, gear_metrics, etc.)
            feedback: Session feedback data
        """
        learnings = []

        # Patterns répétés - Defensive: handle None values
        high_tss_days = [w for w in workouts if (w.get("tss") or 0) > 80]

        if high_tss_days:
            learnings.append(f"{len(high_tss_days)} séances haute charge (TSS >80)")

        # IF élevés - Defensive: handle None values
        high_if_days = [w for w in workouts if (w.get("if") or 0) > 1.0]

        if high_if_days:
            learnings.append(f"{len(high_if_days)} séances intensité élevée (IF >1.0)")

        # Pedal balance imbalance - Defensive: handle None
        balances = [w.get("pedal_balance") for w in workouts if w.get("pedal_balance")]
        if balances:
            avg_balance = sum(balances) / len(balances)
            if avg_balance > 52.0:
                imbalance_pct = avg_balance - 50.0
                learnings.append(
                    f"Déséquilibre pédalage détecté: {avg_balance:.1f}% gauche "
                    f"(+{imbalance_pct:.1f}% vs équilibre)"
                )
            elif avg_balance < 48.0:
                imbalance_pct = 50.0 - avg_balance
                learnings.append(
                    f"Déséquilibre pédalage détecté: {avg_balance:.1f}% gauche "
                    f"(-{imbalance_pct:.1f}% vs équilibre)"
                )

        # Gear shift analysis (Di2) - Defensive: handle None
        outdoor_with_gears = [
            w for w in workouts if w.get("gear_metrics") and w["gear_metrics"].get("shifts")
        ]
        if outdoor_with_gears:
            total_shifts = sum(w["gear_metrics"]["shifts"] for w in outdoor_with_gears)
            total_duration_hours = sum(w.get("duration", 0) / 3600 for w in outdoor_with_gears)

            if total_duration_hours > 0:
                shifts_per_hour = total_shifts / total_duration_hours

                # Patterns de changement de vitesse
                if shifts_per_hour > 50:
                    learnings.append(
                        f"Changements de vitesse fréquents: {total_shifts} shifts "
                        f"({shifts_per_hour:.0f}/h) - considérer anticipation plus fluide"
                    )
                elif shifts_per_hour < 20 and total_shifts > 30:
                    learnings.append(
                        f"Bonne gestion des vitesses: {total_shifts} shifts "
                        f"({shifts_per_hour:.0f}/h) - changements bien anticipés"
                    )

                # Analyse ratio moyen pour sorties outdoor
                avg_ratios = [
                    w["gear_metrics"]["avg_gear_ratio"]
                    for w in outdoor_with_gears
                    if w["gear_metrics"].get("avg_gear_ratio")
                ]
                if avg_ratios:
                    overall_avg_ratio = sum(avg_ratios) / len(avg_ratios)
                    if overall_avg_ratio < 1.5:
                        learnings.append(
                            f"Développement faible moyen ({overall_avg_ratio:.2f}) - "
                            "terrain vallonné ou récupération"
                        )
                    elif overall_avg_ratio > 3.0:
                        learnings.append(
                            f"Développement élevé moyen ({overall_avg_ratio:.2f}) - "
                            "sorties plates ou tempo soutenu"
                        )

        # Feedback patterns - Defensive: handle None
        low_rpe = [
            fid for fid, f in feedback.items() if f.get("rpe") is not None and f.get("rpe") <= 3
        ]

        if low_rpe:
            learnings.append(f"{len(low_rpe)} séances RPE faible (≤3)")

        return learnings

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

    def _prepare_transition_data(
        self, summary: dict[str, Any], metrics_evolution: dict[str, Any], learnings: list[str]
    ) -> dict[str, Any]:
        """Préparer données transition semaine suivante."""
        transition: dict[str, Any] = {
            "current_state": {
                "total_tss": summary.get("total_tss", 0),
                "avg_tss": summary.get("avg_tss", 0),
                "final_tsb": summary.get("final_metrics", {}).get("tsb", 0),
            },
            "recommendations": [],
            "focus_areas": learnings[:3] if learnings else [],
        }

        # Recommandations basées sur TSB
        tsb = transition["current_state"]["final_tsb"]

        # Handle None TSB gracefully
        if tsb is not None:
            if tsb < -15:
                transition["recommendations"].append("Recovery week recommended (TSB very low)")
            elif tsb > 10:
                transition["recommendations"].append("Ready for intensity increase (TSB positive)")

        return transition

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
