"""Training intelligence learnings mixin for PID evaluation."""

from datetime import date
from typing import Any

from magma_cycling.intelligence.training_intelligence import AnalysisLevel, ConfidenceLevel


class TrainingIntelligenceLearningsMixin:
    """Convert metrics into learnings in TrainingIntelligence."""

    def create_intelligence_learnings(
        self,
        metrics: dict[str, Any],
        start_date: date,
        end_date: date,
    ) -> None:
        """Create learnings in TrainingIntelligence from metrics.

        Args:
            metrics: Cycle metrics dict
            start_date: Period start
            end_date: Period end
        """
        print(f"\n{'=' * 60}")
        print("🧠 Creating Intelligence Learnings")
        print(f"{'=' * 60}")

        days = metrics["days_with_data"]
        adherence = metrics["adherence_rate"]
        coupling = metrics["avg_cardiovascular_coupling"]
        tss_completion = metrics["tss_completion_rate"]

        # Learning 1: Adherence (discipline)
        adherence_evidence = [
            f"Période: {start_date} → {end_date} ({days} jours)",
            f"Taux adhérence: {adherence * 100:.1f}%",
            f"Workouts complétés: {metrics['total_workouts']}",
        ]

        if adherence >= 0.90:
            adherence_desc = f"Discipline excellente: {adherence * 100:.1f}% adhérence"
            impact = "LOW"
        elif adherence >= 0.80:
            adherence_desc = f"Discipline correcte: {adherence * 100:.1f}% adhérence"
            impact = "MEDIUM"
        else:
            adherence_desc = f"Discipline faible: {adherence * 100:.1f}% - Action requise"
            impact = "HIGH"

        learning_adh = self.intelligence.add_learning(
            category="adherence",
            description=adherence_desc,
            evidence=adherence_evidence,
            level=AnalysisLevel.WEEKLY,
        )
        learning_adh.impact = impact

        # Set confidence based on data quantity
        if days >= 35:
            learning_adh.confidence = ConfidenceLevel.VALIDATED
        elif days >= 21:
            learning_adh.confidence = ConfidenceLevel.HIGH
        elif days >= 14:
            learning_adh.confidence = ConfidenceLevel.MEDIUM
        else:
            learning_adh.confidence = ConfidenceLevel.LOW

        print(f"   ✅ Adherence learning: {learning_adh.confidence.value}")

        # Learning 2: Cardiovascular quality
        coupling_evidence = [
            f"Période: {start_date} → {end_date}",
            f"Découplage moyen: {coupling * 100:.1f}%",
            "Seuil optimal: <7.5%",
        ]

        if coupling <= 0.075:
            coupling_desc = f"Qualité cardiovasculaire excellente: {coupling * 100:.1f}% découplage"
            impact = "LOW"
        elif coupling <= 0.085:
            coupling_desc = f"Qualité cardiovasculaire dégradée: {coupling * 100:.1f}%"
            impact = "MEDIUM"
        else:
            coupling_desc = (
                f"Surcharge détectée: {coupling * 100:.1f}% découplage - Repos nécessaire"
            )
            impact = "HIGH"

        learning_cv = self.intelligence.add_learning(
            category="cardiovascular_quality",
            description=coupling_desc,
            evidence=coupling_evidence,
            level=AnalysisLevel.WEEKLY,
        )
        learning_cv.impact = impact
        learning_cv.confidence = learning_adh.confidence  # Same confidence

        print(f"   ✅ Cardiovascular learning: {learning_cv.confidence.value}")

        # Learning 3: TSS capacity
        tss_evidence = [
            f"Période: {start_date} → {end_date}",
            f"Taux complétion TSS: {tss_completion * 100:.1f}%",
        ]

        if tss_completion >= 0.90:
            tss_desc = f"Capacité TSS excellente: {tss_completion * 100:.1f}%"
            impact = "LOW"
        elif tss_completion >= 0.85:
            tss_desc = f"Capacité TSS limite: {tss_completion * 100:.1f}%"
            impact = "MEDIUM"
        else:
            tss_desc = f"Capacité TSS insuffisante: {tss_completion * 100:.1f}%"
            impact = "HIGH"

        learning_tss = self.intelligence.add_learning(
            category="tss_capacity",
            description=tss_desc,
            evidence=tss_evidence,
            level=AnalysisLevel.WEEKLY,
        )
        learning_tss.impact = impact
        learning_tss.confidence = learning_adh.confidence

        print(f"   ✅ TSS capacity learning: {learning_tss.confidence.value}")
