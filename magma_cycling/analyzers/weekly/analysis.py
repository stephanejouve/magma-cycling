"""AnalysisMixin for WeeklyAggregator — insights and recommendations."""

from typing import Any


class AnalysisMixin:
    """Training insights extraction and transition recommendations."""

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
