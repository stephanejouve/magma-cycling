"""Tests for TrainingIntelligenceLearningsMixin."""

from datetime import date

from magma_cycling.intelligence.training_intelligence import (
    ConfidenceLevel,
    TrainingIntelligence,
)
from magma_cycling.workflows.pid_eval.intelligence_learnings import (
    TrainingIntelligenceLearningsMixin,
)


class StubLearnings(TrainingIntelligenceLearningsMixin):
    """Stub class to test TrainingIntelligenceLearningsMixin."""

    def __init__(self):
        """Initialize stub with fresh TrainingIntelligence."""
        self.intelligence = TrainingIntelligence()


def _make_metrics(adherence=0.95, coupling=0.06, tss=0.92, days=30, workouts=25):
    return {
        "adherence_rate": adherence,
        "avg_cardiovascular_coupling": coupling,
        "tss_completion_rate": tss,
        "days_with_data": days,
        "total_workouts": workouts,
    }


class TestCreateIntelligenceLearnings:
    """Tests for create_intelligence_learnings."""

    def test_creates_three_learnings(self):
        """Three learnings created (adherence, cardiovascular, tss)."""
        stub = StubLearnings()
        stub.create_intelligence_learnings(_make_metrics(), date(2026, 1, 1), date(2026, 1, 31))
        assert len(stub.intelligence.learnings) == 3

    def test_excellent_adherence_low_impact(self):
        """Adherence >= 90% produces LOW impact."""
        stub = StubLearnings()
        stub.create_intelligence_learnings(
            _make_metrics(adherence=0.95), date(2026, 1, 1), date(2026, 1, 31)
        )
        learnings = list(stub.intelligence.learnings.values())
        adh = [lr for lr in learnings if lr.category == "adherence"][0]
        assert adh.impact == "LOW"

    def test_poor_adherence_high_impact(self):
        """Adherence < 80% produces HIGH impact."""
        stub = StubLearnings()
        stub.create_intelligence_learnings(
            _make_metrics(adherence=0.70), date(2026, 1, 1), date(2026, 1, 31)
        )
        learnings = list(stub.intelligence.learnings.values())
        adh = [lr for lr in learnings if lr.category == "adherence"][0]
        assert adh.impact == "HIGH"

    def test_confidence_validated_for_35_plus_days(self):
        """35+ days of data yields VALIDATED confidence."""
        stub = StubLearnings()
        stub.create_intelligence_learnings(
            _make_metrics(days=40), date(2026, 1, 1), date(2026, 2, 10)
        )
        learnings = list(stub.intelligence.learnings.values())
        assert all(lr.confidence == ConfidenceLevel.VALIDATED for lr in learnings)

    def test_confidence_low_for_few_days(self):
        """< 14 days yields LOW confidence."""
        stub = StubLearnings()
        stub.create_intelligence_learnings(
            _make_metrics(days=10), date(2026, 1, 1), date(2026, 1, 10)
        )
        learnings = list(stub.intelligence.learnings.values())
        assert all(lr.confidence == ConfidenceLevel.LOW for lr in learnings)

    def test_high_coupling_high_impact(self):
        """Coupling > 8.5% produces HIGH impact cardiovascular learning."""
        stub = StubLearnings()
        stub.create_intelligence_learnings(
            _make_metrics(coupling=0.10), date(2026, 1, 1), date(2026, 1, 31)
        )
        learnings = list(stub.intelligence.learnings.values())
        cv = [lr for lr in learnings if lr.category == "cardiovascular_quality"][0]
        assert cv.impact == "HIGH"
