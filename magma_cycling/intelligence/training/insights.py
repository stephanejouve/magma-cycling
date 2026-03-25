"""InsightsMixin — Multi-temporal insights (daily, weekly, monthly)."""

from typing import Any

from magma_cycling.intelligence.models import ConfidenceLevel


class InsightsMixin:
    """Multi-temporal insights generation from accumulated intelligence."""

    def get_daily_insights(self, context: dict[str, Any]) -> dict[str, Any]:
        """Get daily insights based on current context and accumulated intelligence.

        Args:
            context: Current session/day context (workout_type, intensity, etc.)

        Returns:
            Dict with keys:
                - relevant_learnings: List[TrainingLearning]
                - active_patterns: List[Pattern] (matching current conditions)
                - recommendations: List[str]

        Example:
            >>> intelligence = TrainingIntelligence()
            >>> insights = intelligence.get_daily_insights({
            ...     "workout_type": "sweet-spot",
            ...     "planned_intensity": 89
            ... })
        """
        relevant_learnings = []

        active_patterns = []
        recommendations = []

        # Find relevant learnings
        workout_type = context.get("workout_type", "")
        for learning in self.learnings.values():
            if workout_type.lower() in learning.category.lower():
                relevant_learnings.append(learning)

                # Generate recommendation
                conf_str = learning.confidence.value.upper()
                evidence_count = len(learning.evidence)
                rec = f"{learning.description} (Confidence: {conf_str}, {evidence_count} observations)"
                recommendations.append(rec)

        # Find matching patterns
        for pattern in self.patterns.values():
            if pattern.matches(context):
                active_patterns.append(pattern)

                # Add warning recommendation
                warning = (
                    f"\u26a0\ufe0f Pattern detected: {pattern.name} - {pattern.observed_outcome}"
                )
                recommendations.append(warning)

        return {
            "relevant_learnings": relevant_learnings,
            "active_patterns": active_patterns,
            "recommendations": recommendations,
        }

    def get_weekly_synthesis(self, week_number: int) -> dict[str, Any]:
        """Get weekly synthesis of intelligence state.

        Args:
            week_number: ISO week number

        Returns:
            Dict with keys:
                - total_learnings: int
                - high_confidence_learnings: List[TrainingLearning]
                - active_patterns: List[Pattern]
                - pending_adaptations: List[ProtocolAdaptation]

        Example:
            >>> intelligence = TrainingIntelligence()
            >>> synthesis = intelligence.get_weekly_synthesis(week_num=2).
        """
        high_confidence_learnings = [
            learning
            for learning in self.learnings.values()
            if learning.confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.VALIDATED]
        ]

        active_patterns = [
            pattern
            for pattern in self.patterns.values()
            if pattern.confidence
            in [ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH, ConfidenceLevel.VALIDATED]
        ]

        pending_adaptations = [
            adaptation
            for adaptation in self.adaptations.values()
            if adaptation.status == "PROPOSED"
        ]

        return {
            "total_learnings": len(self.learnings),
            "high_confidence_learnings": high_confidence_learnings,
            "active_patterns": active_patterns,
            "pending_adaptations": pending_adaptations,
        }

    def get_monthly_trends(self, month: int, year: int) -> dict[str, Any]:
        """Get monthly trends analysis.

        Args:
            month: Month number (1-12)
            year: Year

        Returns:
            Dict with keys:
                - validated_learnings: List[TrainingLearning]
                - top_patterns: List[Pattern] (sorted by frequency)
                - validated_adaptations: List[ProtocolAdaptation]

        Example:
            >>> intelligence = TrainingIntelligence()
            >>> trends = intelligence.get_monthly_trends(month=1, year=2026).
        """
        validated_learnings = [
            learning for learning in self.learnings.values() if learning.validated
        ]

        # Sort patterns by frequency
        top_patterns = sorted(self.patterns.values(), key=lambda p: p.frequency, reverse=True)[
            :10
        ]  # Top 10 patterns

        validated_adaptations = [
            adaptation
            for adaptation in self.adaptations.values()
            if adaptation.status == "VALIDATED"
        ]

        return {
            "validated_learnings": validated_learnings,
            "top_patterns": top_patterns,
            "validated_adaptations": validated_adaptations,
        }
