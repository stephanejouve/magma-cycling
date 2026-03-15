"""Tests for TSSCapacityMixin."""

from datetime import date
from unittest.mock import MagicMock

from magma_cycling.workflows.pid_eval.tss_capacity import TSSCapacityMixin


class StubTSS(TSSCapacityMixin):
    """Stub class to test TSSCapacityMixin in isolation."""

    def __init__(self, client):
        """Initialize stub with mock client."""
        self.client = client


class TestCalculateTSSCompletion:
    """Tests for calculate_tss_completion."""

    def test_full_completion(self):
        """100% TSS completion rate."""
        client = MagicMock()
        client.get_events.return_value = [
            {"category": "WORKOUT", "name": "Endurance", "icu_training_load": 100},
        ]
        client.get_activities.return_value = [
            {"icu_training_load": 100},
        ]
        stub = StubTSS(client)
        rate = stub.calculate_tss_completion(date(2026, 1, 1), date(2026, 1, 7))
        assert abs(rate - 1.0) < 0.01

    def test_partial_completion(self):
        """50% TSS completion rate."""
        client = MagicMock()
        client.get_events.return_value = [
            {"category": "WORKOUT", "name": "Intervals", "icu_training_load": 100},
        ]
        client.get_activities.return_value = [
            {"icu_training_load": 50},
        ]
        stub = StubTSS(client)
        rate = stub.calculate_tss_completion(date(2026, 1, 1), date(2026, 1, 7))
        assert abs(rate - 0.5) < 0.01

    def test_no_planned_returns_one(self):
        """No planned workouts returns 1.0."""
        client = MagicMock()
        client.get_events.return_value = []
        client.get_activities.return_value = [{"icu_training_load": 50}]
        stub = StubTSS(client)
        rate = stub.calculate_tss_completion(date(2026, 1, 1), date(2026, 1, 7))
        assert rate == 1.0

    def test_skipped_events_excluded(self):
        """Events with name starting with '[' are excluded from planned."""
        client = MagicMock()
        client.get_events.return_value = [
            {"category": "WORKOUT", "name": "[SAUTÉE] Rest", "icu_training_load": 80},
            {"category": "WORKOUT", "name": "Endurance", "icu_training_load": 100},
        ]
        client.get_activities.return_value = [{"icu_training_load": 100}]
        stub = StubTSS(client)
        rate = stub.calculate_tss_completion(date(2026, 1, 1), date(2026, 1, 7))
        assert abs(rate - 1.0) < 0.01

    def test_api_error_returns_one(self):
        """API error returns 1.0 fallback."""
        client = MagicMock()
        client.get_events.side_effect = Exception("API down")
        stub = StubTSS(client)
        rate = stub.calculate_tss_completion(date(2026, 1, 1), date(2026, 1, 7))
        assert rate == 1.0
