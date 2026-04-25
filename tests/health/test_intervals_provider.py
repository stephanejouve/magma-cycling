"""Tests for IntervalsHealthProvider."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from magma_cycling.health.intervals_provider import IntervalsHealthProvider


@pytest.fixture
def mock_client():
    """Mock IntervalsClient with wellness data."""
    client = MagicMock()
    client.get_wellness.return_value = [
        {
            "id": "2026-04-15",
            "sleepTime": 27000,  # 7.5h in seconds
            "sleepScore": 82,
            "wakeupCount": 2,
        }
    ]
    return client


@pytest.fixture
def provider(mock_client):
    return IntervalsHealthProvider(mock_client)


class TestGetSleepSummary:
    def test_returns_sleep_data(self, provider):
        result = provider.get_sleep_summary(date(2026, 4, 15))
        assert result is not None
        assert result.total_sleep_hours == 7.5
        assert result.sleep_score == 82
        assert result.wakeup_count == 2

    def test_returns_none_when_no_wellness(self, mock_client):
        mock_client.get_wellness.return_value = []
        provider = IntervalsHealthProvider(mock_client)
        assert provider.get_sleep_summary(date(2026, 4, 15)) is None

    def test_returns_none_when_no_sleep_time(self, mock_client):
        mock_client.get_wellness.return_value = [{"id": "2026-04-15"}]
        provider = IntervalsHealthProvider(mock_client)
        assert provider.get_sleep_summary(date(2026, 4, 15)) is None


class TestGetReadiness:
    def test_good_sleep_all_systems_go(self, provider):
        readiness = provider.get_readiness(date(2026, 4, 15))
        assert readiness is not None
        assert readiness.ready_for_intense is True
        assert readiness.recommended_intensity == "all_systems_go"
        assert readiness.veto_reasons == []

    def test_low_sleep_veto(self, mock_client):
        mock_client.get_wellness.return_value = [
            {"id": "2026-04-15", "sleepTime": 18000, "sleepScore": 45}  # 5h
        ]
        provider = IntervalsHealthProvider(mock_client)
        readiness = provider.get_readiness(date(2026, 4, 15))
        assert readiness.recommended_intensity == "endurance_max"
        assert len(readiness.veto_reasons) == 1


class TestBodyComposition:
    def test_returns_none(self, provider):
        assert provider.get_body_composition() is None

    def test_range_returns_empty(self, provider):
        assert provider.get_body_composition_range(date(2026, 4, 1), date(2026, 4, 15)) == []


class TestAuthStatus:
    def test_configured(self, provider):
        status = provider.auth_status()
        assert status["configured"] is True
        assert status["provider"] == "intervals_icu_wellness"


class TestGetHrvNocturnal:
    """Read rMSSD HRV from Intervals.icu wellness `hrv` field."""

    def test_returns_hrv_reading(self, mock_client):
        mock_client.get_wellness.return_value = [
            {"id": "2026-04-15", "hrv": 47.5, "sleepTime": 27000}
        ]
        provider = IntervalsHealthProvider(mock_client)
        reading = provider.get_hrv_nocturnal(date(2026, 4, 15))

        assert reading is not None
        assert reading.measurement_date == date(2026, 4, 15)
        assert reading.metric_type == "rmssd"
        assert reading.value_ms == 47.5
        assert reading.context == "nocturnal_avg"
        assert reading.source_provider == "intervals_icu"

    def test_none_when_no_wellness(self, mock_client):
        mock_client.get_wellness.return_value = []
        provider = IntervalsHealthProvider(mock_client)
        assert provider.get_hrv_nocturnal(date(2026, 4, 15)) is None

    def test_none_when_field_absent(self, mock_client):
        mock_client.get_wellness.return_value = [{"id": "2026-04-15", "sleepTime": 27000}]
        provider = IntervalsHealthProvider(mock_client)
        assert provider.get_hrv_nocturnal(date(2026, 4, 15)) is None

    def test_none_when_value_zero_or_negative(self, mock_client):
        mock_client.get_wellness.return_value = [{"id": "2026-04-15", "hrv": 0}]
        provider = IntervalsHealthProvider(mock_client)
        assert provider.get_hrv_nocturnal(date(2026, 4, 15)) is None

        mock_client.get_wellness.return_value = [{"id": "2026-04-15", "hrv": -5}]
        provider = IntervalsHealthProvider(mock_client)
        assert provider.get_hrv_nocturnal(date(2026, 4, 15)) is None


class TestGetHrvRange:
    """Optimized range fetch: single wellness API call covers the whole window."""

    def test_returns_readings_filters_invalid(self, mock_client):
        mock_client.get_wellness.return_value = [
            {"id": "2026-04-13", "hrv": 42.0},
            {"id": "2026-04-14", "hrv": None},  # filtered
            {"id": "2026-04-15", "hrv": 0},  # filtered
            {"id": "2026-04-16", "hrv": 51.2},
        ]
        provider = IntervalsHealthProvider(mock_client)
        readings = provider.get_hrv_range(date(2026, 4, 13), date(2026, 4, 16))

        assert len(readings) == 2
        assert readings[0].measurement_date == date(2026, 4, 13)
        assert readings[0].value_ms == 42.0
        assert readings[1].measurement_date == date(2026, 4, 16)
        assert readings[1].value_ms == 51.2

    def test_skips_entries_with_invalid_id(self, mock_client):
        mock_client.get_wellness.return_value = [
            {"id": "not-a-date", "hrv": 50.0},
            {"hrv": 60.0},  # no id
            {"id": "2026-04-15", "hrv": 47.0},
        ]
        provider = IntervalsHealthProvider(mock_client)
        readings = provider.get_hrv_range(date(2026, 4, 15), date(2026, 4, 15))
        assert len(readings) == 1
        assert readings[0].value_ms == 47.0

    def test_empty_wellness_returns_empty_list(self, mock_client):
        mock_client.get_wellness.return_value = []
        provider = IntervalsHealthProvider(mock_client)
        assert provider.get_hrv_range(date(2026, 4, 15), date(2026, 4, 15)) == []
