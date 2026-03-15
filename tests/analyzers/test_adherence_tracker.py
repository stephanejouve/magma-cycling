"""Tests for analyzers.adherence_tracker module.

Tests AdherenceTracker : calculate_session_adherence, pattern detection, recommendations.
Utilise mocks pour IntervalsClient et config.
"""

from collections import defaultdict
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.analyzers.adherence_tracker import AdherenceTracker


@pytest.fixture
def tracker():
    """Create AdherenceTracker with mocked dependencies."""
    with (
        patch("magma_cycling.analyzers.adherence_tracker.get_data_config") as mock_data,
        patch("magma_cycling.analyzers.adherence_tracker.get_intervals_config") as mock_intervals,
        patch("magma_cycling.analyzers.adherence_tracker.IntervalsClient") as mock_client_cls,
    ):
        mock_data.return_value = MagicMock()
        mock_intervals_config = MagicMock()
        mock_intervals_config.athlete_id = "iXXXXXX"
        mock_intervals_config.api_key = "test_key"
        mock_intervals.return_value = mock_intervals_config
        mock_client_cls.return_value = MagicMock()

        t = AdherenceTracker()
        yield t


class TestCalculateSessionAdherence:
    """Tests for calculate_session_adherence()."""

    def test_no_planned_event(self, tracker):
        tracker.client.get_planned_workout.return_value = None
        activity = {
            "id": "i123",
            "start_date_local": "2026-03-01T08:00:00",
            "icu_training_load": 50,
            "moving_time": 3600,
        }
        result = tracker.calculate_session_adherence(activity)
        assert result["has_plan"] is False
        assert result["tss_adherence"] is None
        assert result["completion"] is True

    def test_with_planned_event(self, tracker):
        activity = {
            "id": "i123",
            "icu_training_load": 45,
            "moving_time": 3600,
            "icu_intensity": 80,
            "icu_average_watts": 190,
        }
        planned_event = {
            "workout_doc": {"duration": 3600, "average_watts": 200},
            "icu_training_load": 50,
            "icu_intensity": 85,
        }
        result = tracker.calculate_session_adherence(activity, planned_event)
        assert result["has_plan"] is True
        assert result["tss_adherence"] == pytest.approx(0.9)  # 45/50
        assert result["completion"] is True

    def test_perfect_adherence(self, tracker):
        activity = {
            "icu_training_load": 50,
            "moving_time": 3600,
            "icu_intensity": 80,
            "icu_average_watts": 200,
        }
        planned_event = {
            "workout_doc": {"duration": 3600, "average_watts": 200},
            "icu_training_load": 50,
            "icu_intensity": 80,
        }
        result = tracker.calculate_session_adherence(activity, planned_event)
        assert result["tss_adherence"] == pytest.approx(1.0)
        assert result["if_adherence"] == pytest.approx(1.0)
        assert result["deviations"] == []

    def test_detects_tss_deviation(self, tracker):
        activity = {
            "icu_training_load": 30,
            "moving_time": 3600,
            "icu_intensity": 80,
            "icu_average_watts": 200,
        }
        planned_event = {
            "workout_doc": {"duration": 3600, "average_watts": 200},
            "icu_training_load": 50,
            "icu_intensity": 80,
        }
        result = tracker.calculate_session_adherence(activity, planned_event)
        assert len(result["deviations"]) > 0
        tss_deviation = next(d for d in result["deviations"] if d["metric"] == "TSS")
        assert tss_deviation["deviation_pct"] < 0

    def test_no_workout_doc(self, tracker):
        activity = {
            "id": "i123",
            "start_date_local": "2026-03-01T08:00:00",
        }
        planned_event = {"workout_doc": None, "icu_training_load": 50}
        result = tracker.calculate_session_adherence(activity, planned_event)
        assert result["has_plan"] is False

    def test_zero_planned_metrics(self, tracker):
        activity = {
            "icu_training_load": 50,
            "moving_time": 3600,
            "icu_intensity": 0,
            "icu_average_watts": 200,
        }
        planned_event = {
            "workout_doc": {"duration": 0, "average_watts": 0},
            "icu_training_load": 0,
            "icu_intensity": 0,
        }
        result = tracker.calculate_session_adherence(activity, planned_event)
        assert result["tss_adherence"] is None
        assert result["if_adherence"] is None


class TestDetectAdherencePatterns:
    """Tests for _detect_adherence_patterns()."""

    def test_consistent_under_delivery(self, tracker):
        adherence_data = {
            "tss_adherence_values": [0.80, 0.82, 0.79, 0.81, 0.80],
            "if_adherence_values": [],
            "cancelled_sessions": [],
            "systematic_deviations": defaultdict(list),
        }
        patterns = tracker._detect_adherence_patterns(adherence_data)
        assert any(p["type"] == "consistent_under_delivery" for p in patterns)

    def test_if_systematic_underperformance(self, tracker):
        adherence_data = {
            "tss_adherence_values": [0.95, 0.96, 0.94, 0.95],
            "if_adherence_values": [0.85, 0.87, 0.84, 0.86],
            "cancelled_sessions": [],
            "systematic_deviations": defaultdict(list),
        }
        patterns = tracker._detect_adherence_patterns(adherence_data)
        assert any(p["type"] == "if_systematic_underperformance" for p in patterns)

    def test_recurring_cancellation(self, tracker):
        adherence_data = {
            "tss_adherence_values": [],
            "if_adherence_values": [],
            "cancelled_sessions": [
                {"day": "Thursday"},
                {"day": "Thursday"},
                {"day": "Monday"},
            ],
            "systematic_deviations": defaultdict(list),
        }
        patterns = tracker._detect_adherence_patterns(adherence_data)
        assert any(p["type"] == "recurring_cancellation" for p in patterns)

    def test_no_patterns(self, tracker):
        adherence_data = {
            "tss_adherence_values": [0.95, 0.97],
            "if_adherence_values": [0.98, 0.99],
            "cancelled_sessions": [],
            "systematic_deviations": defaultdict(list),
        }
        patterns = tracker._detect_adherence_patterns(adherence_data)
        assert patterns == []


class TestCalculateTrend:
    """Tests for _calculate_trend()."""

    def test_improving(self, tracker):
        assert tracker._calculate_trend([0.70, 0.80, 0.90, 0.95]) == "improving"

    def test_declining(self, tracker):
        assert tracker._calculate_trend([0.95, 0.85, 0.75, 0.65]) == "declining"

    def test_stable(self, tracker):
        assert tracker._calculate_trend([0.90, 0.90, 0.90, 0.90]) == "stable"

    def test_insufficient_data(self, tracker):
        assert tracker._calculate_trend([0.90, 0.95]) == "insufficient_data"


class TestGenerateAdherenceRecommendations:
    """Tests for _generate_adherence_recommendations()."""

    def test_low_tss_recommendation(self, tracker):
        recs = tracker._generate_adherence_recommendations(0.75, 0.98, [])
        assert any("TSS faible" in r for r in recs)

    def test_high_tss_recommendation(self, tracker):
        recs = tracker._generate_adherence_recommendations(1.10, 0.98, [])
        assert any("Sur-adhérence" in r for r in recs)

    def test_low_if_recommendation(self, tracker):
        recs = tracker._generate_adherence_recommendations(0.95, 0.88, [])
        assert any("IF" in r for r in recs)

    def test_pattern_recommendations(self, tracker):
        patterns = [{"type": "test_pattern", "recommendation": "Fix the thing"}]
        recs = tracker._generate_adherence_recommendations(0.95, 0.98, patterns)
        assert any("Fix the thing" in r for r in recs)

    def test_excellent_adherence(self, tracker):
        recs = tracker._generate_adherence_recommendations(0.97, 0.98, [])
        assert any("excellente" in r for r in recs)
