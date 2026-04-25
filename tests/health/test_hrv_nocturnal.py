"""Tests for HRV nocturnal provider capability."""

from datetime import date
from unittest.mock import Mock

import pytest

from magma_cycling.health.base import HealthProvider
from magma_cycling.health.intervals_provider import IntervalsHealthProvider
from magma_cycling.health.null_provider import NullProvider
from magma_cycling.health.withings_provider import WithingsProvider
from magma_cycling.models.hrv_models import HrvReading


class TestHrvReadingModel:
    def test_minimal_valid_reading(self):
        r = HrvReading(
            measurement_date=date(2026, 4, 19),
            metric_type="rmssd",
            value_ms=42.5,
            context="nocturnal_end",
            source_provider="withings",
        )
        assert r.value_ms == 42.5
        assert r.data_quality == "ok"  # default

    def test_zero_value_rejected(self):
        with pytest.raises(ValueError):
            HrvReading(
                measurement_date=date(2026, 4, 19),
                metric_type="rmssd",
                value_ms=0,
                context="nocturnal_end",
                source_provider="withings",
            )

    def test_negative_value_rejected(self):
        with pytest.raises(ValueError):
            HrvReading(
                measurement_date=date(2026, 4, 19),
                metric_type="rmssd",
                value_ms=-1,
                context="nocturnal_end",
                source_provider="withings",
            )


class TestHealthProviderDefault:
    def test_null_provider_returns_none(self):
        assert NullProvider().get_hrv_nocturnal(date(2026, 4, 19)) is None

    def test_intervals_provider_returns_none_when_no_wellness(self):
        """IntervalsHealthProvider.get_hrv_nocturnal returns None when wellness is empty.

        Since 2026-04-25 (PR #284), this provider reads the `hrv` field from
        the Intervals.icu wellness payload. With an empty client response
        (no data for the date), it must return None.
        """
        client = Mock()
        client.get_wellness.return_value = []
        p = IntervalsHealthProvider(client)
        assert p.get_hrv_nocturnal(date(2026, 4, 19)) is None

    def test_base_returns_none_by_default(self):
        """HealthProvider.get_hrv_nocturnal has a concrete default returning None."""

        class _Stub(HealthProvider):
            # Abstract methods stubs — not under test
            def get_sleep_summary(self, target_date):
                return None

            def get_sleep_range(self, start_date, end_date):
                return []

            def get_body_composition(self):
                return None

            def get_body_composition_range(self, start_date, end_date):
                return []

            def get_blood_pressure_range(self, start_date, end_date):
                return []

            def get_readiness(self, target_date=None):
                return None

            def auth_status(self):
                return {}

        assert _Stub().get_hrv_nocturnal(date(2026, 4, 19)) is None


class TestWithingsHrvNocturnal:
    def test_returns_reading_when_rmssd_end_avg_present(self):
        client = Mock()
        client.get_sleep_hrv.return_value = [
            {
                "date": "2026-04-19",
                "rmssd_start_avg": 45,
                "rmssd_end_avg": 42,
                "model": 32,
                "model_id": 63,
            }
        ]
        p = WithingsProvider(client)
        reading = p.get_hrv_nocturnal(date(2026, 4, 19))
        assert reading is not None
        assert reading.metric_type == "rmssd"
        assert reading.value_ms == 42.0
        assert reading.context == "nocturnal_end"
        assert reading.source_provider == "withings"
        assert reading.measurement_date == date(2026, 4, 19)
        client.get_sleep_hrv.assert_called_once_with(date(2026, 4, 19), date(2026, 4, 19))

    def test_returns_none_when_no_summary(self):
        client = Mock()
        client.get_sleep_hrv.return_value = []
        p = WithingsProvider(client)
        assert p.get_hrv_nocturnal(date(2026, 4, 19)) is None

    def test_returns_none_when_rmssd_end_avg_missing(self):
        client = Mock()
        client.get_sleep_hrv.return_value = [
            {"date": "2026-04-19", "rmssd_start_avg": 45, "rmssd_end_avg": None}
        ]
        p = WithingsProvider(client)
        assert p.get_hrv_nocturnal(date(2026, 4, 19)) is None

    def test_returns_none_when_rmssd_end_avg_zero_or_negative(self):
        client = Mock()
        client.get_sleep_hrv.return_value = [{"date": "2026-04-19", "rmssd_end_avg": 0}]
        p = WithingsProvider(client)
        assert p.get_hrv_nocturnal(date(2026, 4, 19)) is None

        client.get_sleep_hrv.return_value = [{"date": "2026-04-19", "rmssd_end_avg": -1}]
        assert p.get_hrv_nocturnal(date(2026, 4, 19)) is None


class TestHrvMixinParsing:
    """HrvMixin unpacks Withings sleep/getsummary series to a normalized dict."""

    def test_unpacks_series(self):
        from magma_cycling.api.withings.hrv import HrvMixin

        class _FakeClient(HrvMixin):
            def __init__(self, body):
                self._body = body

            def _make_request(self, endpoint, params):
                return self._body

        body = {
            "series": [
                {
                    "date": "2026-04-18",
                    "model": 32,
                    "model_id": 63,
                    "data": {"rmssd_start_avg": 45, "rmssd_end_avg": 42},
                },
                {
                    "date": "2026-04-19",
                    "model": 32,
                    "model_id": 63,
                    "data": {"rmssd_start_avg": 42, "rmssd_end_avg": 42},
                },
            ]
        }
        rows = _FakeClient(body).get_sleep_hrv(date(2026, 4, 18), date(2026, 4, 19))
        assert len(rows) == 2
        assert rows[0]["rmssd_end_avg"] == 42
        assert rows[1]["model"] == 32

    def test_empty_series(self):
        from magma_cycling.api.withings.hrv import HrvMixin

        class _FakeClient(HrvMixin):
            def _make_request(self, endpoint, params):
                return {"series": []}

        assert _FakeClient().get_sleep_hrv(date(2026, 4, 19)) == []
