"""Tests for WithingsProvider — wraps WithingsClient with Pydantic models."""

from datetime import date
from unittest.mock import Mock

import pytest

from magma_cycling.health.base import HealthProvider
from magma_cycling.health.withings_provider import WithingsProvider
from magma_cycling.models.withings_models import (
    SleepData,
    TrainingReadiness,
    WeightMeasurement,
)


@pytest.fixture
def mock_client():
    return Mock()


@pytest.fixture
def provider(mock_client):
    return WithingsProvider(mock_client)


class TestWithingsProviderABC:
    def test_is_health_provider_subclass(self):
        assert issubclass(WithingsProvider, HealthProvider)

    def test_instantiation(self, mock_client):
        p = WithingsProvider(mock_client)
        assert isinstance(p, HealthProvider)

    def test_client_property(self, mock_client, provider):
        assert provider.client is mock_client


class TestNormalizeSleepData:
    """Test _normalize_sleep_data handles Withings API ratio → percentage."""

    def test_ratio_converted_to_percentage(self):
        data = {"sleep_efficiency": 0.96}
        result = WithingsProvider._normalize_sleep_data(data)
        assert result["sleep_efficiency"] == 96

    def test_ratio_zero_stays_zero(self):
        data = {"sleep_efficiency": 0.0}
        result = WithingsProvider._normalize_sleep_data(data)
        assert result["sleep_efficiency"] == 0

    def test_ratio_one_becomes_100(self):
        data = {"sleep_efficiency": 1.0}
        result = WithingsProvider._normalize_sleep_data(data)
        assert result["sleep_efficiency"] == 100

    def test_already_percentage_stays_unchanged(self):
        data = {"sleep_efficiency": 92}
        result = WithingsProvider._normalize_sleep_data(data)
        assert result["sleep_efficiency"] == 92

    def test_none_stays_none(self):
        data = {"sleep_efficiency": None}
        result = WithingsProvider._normalize_sleep_data(data)
        assert result["sleep_efficiency"] is None

    def test_missing_key_no_error(self):
        data = {"total_sleep_hours": 7.5}
        result = WithingsProvider._normalize_sleep_data(data)
        assert "sleep_efficiency" not in result


class TestGetSleepSummary:
    def test_returns_sleep_data(self, mock_client, provider):
        mock_client.get_last_night_sleep.return_value = {
            "date": "2026-02-28",
            "start_datetime": "2026-02-27T23:00:00",
            "end_datetime": "2026-02-28T06:30:00",
            "total_sleep_hours": 7.5,
            "wakeup_count": 2,
            "sleep_score": 85,
        }
        result = provider.get_sleep_summary(date(2026, 2, 28))
        assert isinstance(result, SleepData)
        assert result.total_sleep_hours == 7.5
        assert result.sleep_score == 85

    def test_normalizes_sleep_efficiency_ratio(self, mock_client, provider):
        """Withings returns sleep_efficiency as 0-1 ratio, model expects 0-100 int."""
        mock_client.get_last_night_sleep.return_value = {
            "date": "2026-02-28",
            "start_datetime": "2026-02-27T23:00:00",
            "end_datetime": "2026-02-28T06:30:00",
            "total_sleep_hours": 7.5,
            "wakeup_count": 1,
            "sleep_efficiency": 0.96,
        }
        result = provider.get_sleep_summary(date(2026, 2, 28))
        assert isinstance(result, SleepData)
        assert result.sleep_efficiency == 96

    def test_returns_none_when_no_data(self, mock_client, provider):
        mock_client.get_last_night_sleep.return_value = None
        assert provider.get_sleep_summary(date(2026, 2, 28)) is None


class TestSleepDataWithSegments:
    def test_sleep_data_accepts_segments_fields(self):
        data = SleepData(
            date="2026-03-07",
            start_datetime="2026-03-06T22:08:00",
            end_datetime="2026-03-07T07:09:00",
            total_sleep_hours=8.7,
            wakeup_count=3,
            segments_count=2,
            segments_detail=[
                {"start": "22:08", "end": "01:30", "duration_hours": 3.2},
                {"start": "01:30", "end": "07:09", "duration_hours": 5.5},
            ],
        )
        assert data.segments_count == 2
        assert len(data.segments_detail) == 2
        dumped = data.model_dump()
        assert dumped["segments_count"] == 2
        assert dumped["segments_detail"][0]["start"] == "22:08"

    def test_sleep_data_defaults_single_segment(self):
        data = SleepData(
            date="2026-03-07",
            start_datetime="2026-03-06T23:00:00",
            end_datetime="2026-03-07T06:30:00",
            total_sleep_hours=7.5,
            wakeup_count=1,
        )
        assert data.segments_count == 1
        assert data.segments_detail is None


class TestGetSleepRange:
    def test_returns_list_of_sleep_data(self, mock_client, provider):
        mock_client.get_sleep.return_value = [
            {
                "date": "2026-02-27",
                "start_datetime": "2026-02-26T23:00:00",
                "end_datetime": "2026-02-27T06:00:00",
                "total_sleep_hours": 7.0,
                "wakeup_count": 1,
            },
            {
                "date": "2026-02-28",
                "start_datetime": "2026-02-27T23:30:00",
                "end_datetime": "2026-02-28T07:00:00",
                "total_sleep_hours": 7.5,
                "wakeup_count": 0,
            },
        ]
        result = provider.get_sleep_range(date(2026, 2, 27), date(2026, 2, 28))
        assert len(result) == 2
        assert all(isinstance(s, SleepData) for s in result)

    def test_empty_range(self, mock_client, provider):
        mock_client.get_sleep.return_value = []
        assert provider.get_sleep_range(date(2026, 2, 27), date(2026, 2, 28)) == []


class TestGetBodyComposition:
    def test_returns_weight_measurement(self, mock_client, provider):
        mock_client.get_latest_weight.return_value = {
            "date": "2026-02-28",
            "datetime": "2026-02-28T08:00:00",
            "weight_kg": 75.5,
            "fat_mass_kg": 12.3,
        }
        result = provider.get_body_composition()
        assert isinstance(result, WeightMeasurement)
        assert result.weight_kg == 75.5

    def test_returns_none_when_no_data(self, mock_client, provider):
        mock_client.get_latest_weight.return_value = None
        assert provider.get_body_composition() is None


class TestGetBodyCompositionRange:
    def test_returns_list_of_measurements(self, mock_client, provider):
        mock_client.get_measurements.return_value = [
            {
                "date": "2026-02-27",
                "datetime": "2026-02-27T08:00:00",
                "weight_kg": 76.0,
            },
            {
                "date": "2026-02-28",
                "datetime": "2026-02-28T08:00:00",
                "weight_kg": 75.5,
            },
        ]
        result = provider.get_body_composition_range(date(2026, 2, 27), date(2026, 2, 28))
        assert len(result) == 2
        assert all(isinstance(m, WeightMeasurement) for m in result)
        mock_client.get_measurements.assert_called_once_with(
            date(2026, 2, 27), date(2026, 2, 28), measure_types=[1, 6, 8, 76, 88]
        )


class TestGetReadiness:
    def test_returns_training_readiness(self, mock_client, provider):
        mock_client.get_last_night_sleep.return_value = {
            "date": "2026-02-28",
            "start_datetime": "2026-02-27T23:00:00",
            "end_datetime": "2026-02-28T06:30:00",
            "total_sleep_hours": 7.5,
            "wakeup_count": 1,
            "sleep_score": 85,
        }
        mock_client.evaluate_training_readiness.return_value = {
            "date": "2026-02-28",
            "sleep_hours": 7.5,
            "sleep_score": 85,
            "deep_sleep_minutes": 0,
            "ready_for_intense": True,
            "recommended_intensity": "all_systems_go",
            "veto_reasons": [],
            "recommendations": ["Conditions optimales"],
            "sufficient_duration": True,
            "deep_sleep_ok": False,
        }
        mock_client.get_latest_weight.return_value = {
            "date": "2026-02-28",
            "datetime": "2026-02-28T08:00:00",
            "weight_kg": 75.5,
        }
        result = provider.get_readiness(date(2026, 2, 28))
        assert isinstance(result, TrainingReadiness)
        assert result.ready_for_intense is True
        assert result.weight_kg == 75.5

    def test_returns_none_when_no_sleep(self, mock_client, provider):
        mock_client.get_last_night_sleep.return_value = None
        assert provider.get_readiness(date(2026, 2, 28)) is None

    def test_readiness_without_weight(self, mock_client, provider):
        mock_client.get_last_night_sleep.return_value = {
            "date": "2026-02-28",
            "start_datetime": "2026-02-27T23:00:00",
            "end_datetime": "2026-02-28T06:00:00",
            "total_sleep_hours": 6.0,
            "wakeup_count": 3,
        }
        mock_client.evaluate_training_readiness.return_value = {
            "date": "2026-02-28",
            "sleep_hours": 6.0,
            "ready_for_intense": False,
            "recommended_intensity": "endurance_max",
            "veto_reasons": ["Sommeil insuffisant"],
            "recommendations": ["Zone endurance maximum"],
            "sufficient_duration": False,
            "deep_sleep_ok": False,
        }
        mock_client.get_latest_weight.return_value = None
        result = provider.get_readiness(date(2026, 2, 28))
        assert isinstance(result, TrainingReadiness)
        assert result.weight_kg is None


class TestAuthAndInfo:
    def test_auth_status(self, mock_client, provider):
        mock_client.is_authenticated.return_value = True
        status = provider.auth_status()
        assert status["configured"] is True
        assert status["has_credentials"] is True

    def test_get_provider_info(self, provider):
        info = provider.get_provider_info()
        assert info["provider"] == "WithingsProvider"
        assert info["status"] == "ready"
