"""Tests for create_health_provider factory."""

from unittest.mock import Mock, patch

from magma_cycling.health.factory import create_health_provider
from magma_cycling.health.null_provider import NullProvider
from magma_cycling.health.withings_provider import WithingsProvider


class TestCreateHealthProvider:
    def test_returns_withings_provider_when_configured(self):
        mock_config = Mock()
        mock_config.is_configured.return_value = True
        mock_client = Mock()
        with (
            patch("magma_cycling.config.get_withings_config", return_value=mock_config),
            patch("magma_cycling.config.create_withings_client", return_value=mock_client),
        ):
            provider = create_health_provider()
        assert isinstance(provider, WithingsProvider)

    def test_returns_null_provider_when_not_configured(self):
        mock_config = Mock()
        mock_config.is_configured.return_value = False
        with patch("magma_cycling.config.get_withings_config", return_value=mock_config):
            provider = create_health_provider()
        assert isinstance(provider, NullProvider)

    def test_returns_null_provider_on_exception(self):
        with patch(
            "magma_cycling.config.get_withings_config",
            side_effect=RuntimeError("config broken"),
        ):
            provider = create_health_provider()
        assert isinstance(provider, NullProvider)
