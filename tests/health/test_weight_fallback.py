"""Tests for weight_fallback utility (BT-015 follow-up)."""

from datetime import date
from unittest.mock import MagicMock

from magma_cycling.health.weight_fallback import (
    apply_weight_fallback,
    get_last_known_weight,
)


class TestGetLastKnownWeight:
    def test_returns_weight_from_target_day(self):
        client = MagicMock()
        client.get_wellness.return_value = [
            {"id": "2026-05-28", "weight": 72.3},
        ]
        weight, day = get_last_known_weight(client, date(2026, 5, 28), max_days_back=14)
        assert weight == 72.3
        assert day == date(2026, 5, 28)

    def test_falls_back_to_earlier_day(self):
        client = MagicMock()
        client.get_wellness.return_value = [
            {"id": "2026-05-25", "weight": 72.5},
            {"id": "2026-05-26"},  # no weight
            {"id": "2026-05-27", "weight": 0},
            {"id": "2026-05-28"},  # no weight (target day)
        ]
        weight, day = get_last_known_weight(client, date(2026, 5, 28), max_days_back=14)
        assert weight == 72.5
        assert day == date(2026, 5, 25)

    def test_returns_none_when_no_entries(self):
        client = MagicMock()
        client.get_wellness.return_value = []
        weight, day = get_last_known_weight(client, date(2026, 5, 28))
        assert weight is None
        assert day is None

    def test_returns_none_when_no_weight_in_window(self):
        client = MagicMock()
        client.get_wellness.return_value = [
            {"id": "2026-05-26", "weight": 0},
            {"id": "2026-05-27"},
            {"id": "2026-05-28", "weight": None},
        ]
        weight, day = get_last_known_weight(client, date(2026, 5, 28))
        assert weight is None
        assert day is None

    def test_queries_correct_range(self):
        client = MagicMock()
        client.get_wellness.return_value = []
        get_last_known_weight(client, date(2026, 5, 28), max_days_back=14)
        client.get_wellness.assert_called_once_with(oldest="2026-05-14", newest="2026-05-28")

    def test_returns_none_when_client_raises(self):
        client = MagicMock()
        client.get_wellness.side_effect = RuntimeError("boom")
        weight, day = get_last_known_weight(client, date(2026, 5, 28))
        assert weight is None
        assert day is None


class TestApplyWeightFallback:
    def test_none_wellness_passes_through(self):
        client = MagicMock()
        result = apply_weight_fallback(client, date(2026, 5, 28), None)
        assert result is None
        client.get_wellness.assert_not_called()

    def test_existing_weight_unchanged(self):
        client = MagicMock()
        wellness = {"id": "2026-05-28", "weight": 72.0, "sleepSecs": 27000}
        result = apply_weight_fallback(client, date(2026, 5, 28), wellness)
        assert result is wellness
        client.get_wellness.assert_not_called()

    def test_fills_missing_weight_from_earlier_day(self):
        client = MagicMock()
        client.get_wellness.return_value = [
            {"id": "2026-05-25", "weight": 72.5},
            {"id": "2026-05-28"},
        ]
        wellness = {"id": "2026-05-28", "sleepSecs": 27000}
        result = apply_weight_fallback(client, date(2026, 5, 28), wellness)
        assert result["weight"] == 72.5
        assert result["sleepSecs"] == 27000
        assert wellness.get("weight") is None  # original not mutated

    def test_zero_weight_triggers_fallback(self):
        client = MagicMock()
        client.get_wellness.return_value = [
            {"id": "2026-05-25", "weight": 72.5},
            {"id": "2026-05-28", "weight": 0},
        ]
        wellness = {"id": "2026-05-28", "weight": 0}
        result = apply_weight_fallback(client, date(2026, 5, 28), wellness)
        assert result["weight"] == 72.5

    def test_no_fallback_available_leaves_wellness_unchanged(self):
        client = MagicMock()
        client.get_wellness.return_value = []
        wellness = {"id": "2026-05-28", "sleepSecs": 27000}
        result = apply_weight_fallback(client, date(2026, 5, 28), wellness)
        assert result == wellness
