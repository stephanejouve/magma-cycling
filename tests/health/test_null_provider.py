"""Tests for NullProvider — silent fallback when no health device is configured."""

from datetime import date

from magma_cycling.health.base import HealthProvider
from magma_cycling.health.null_provider import NullProvider


class TestNullProviderABC:
    def test_is_health_provider_subclass(self):
        assert issubclass(NullProvider, HealthProvider)

    def test_instantiation(self):
        provider = NullProvider()
        assert isinstance(provider, HealthProvider)


class TestNullProviderMethods:
    def setup_method(self):
        self.provider = NullProvider()

    def test_get_sleep_summary_returns_none(self):
        assert self.provider.get_sleep_summary(date(2026, 2, 28)) is None

    def test_get_sleep_range_returns_empty_list(self):
        result = self.provider.get_sleep_range(date(2026, 2, 21), date(2026, 2, 28))
        assert result == []

    def test_get_body_composition_returns_none(self):
        assert self.provider.get_body_composition() is None

    def test_get_body_composition_range_returns_empty_list(self):
        result = self.provider.get_body_composition_range(date(2026, 2, 21), date(2026, 2, 28))
        assert result == []

    def test_get_readiness_returns_none(self):
        assert self.provider.get_readiness(date(2026, 2, 28)) is None

    def test_get_readiness_no_arg_returns_none(self):
        assert self.provider.get_readiness() is None

    def test_auth_status_returns_not_configured(self):
        status = self.provider.auth_status()
        assert status["configured"] is False
        assert status["has_credentials"] is False
        assert "message" in status

    def test_get_provider_info(self):
        info = self.provider.get_provider_info()
        assert info["provider"] == "NullProvider"
        assert info["status"] == "not_configured"
