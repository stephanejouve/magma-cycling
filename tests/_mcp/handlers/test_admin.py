"""Tests for _mcp/handlers/admin.py."""

import json
import types
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling._mcp.handlers.admin import handle_reload_server


class TestHandleReloadServer:
    """Tests for handle_reload_server."""

    @pytest.mark.asyncio
    async def test_reload_returns_list(self):
        """Returns a list of TextContent."""
        result = await handle_reload_server({})
        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_reload_response_is_valid_json(self):
        """Response text is valid JSON."""
        result = await handle_reload_server({})
        data = json.loads(result[0].text)
        assert "success" in data
        assert "reloaded_count" in data

    @pytest.mark.asyncio
    async def test_reload_handles_module_error(self):
        """Reports failed modules when reload raises."""
        bad_module = types.ModuleType("magma_cycling.config")

        with patch.dict("sys.modules", {"magma_cycling.config": bad_module}):
            with patch("importlib.reload", side_effect=ImportError("broken")):
                result = await handle_reload_server({})

        data = json.loads(result[0].text)
        assert len(data["failed"]) >= 1
        assert data["failed"][0]["error"] == "broken"

    @pytest.mark.asyncio
    async def test_reload_response_has_message(self):
        """Response always contains a message field."""
        result = await handle_reload_server({})
        data = json.loads(result[0].text)
        assert "message" in data

    @pytest.mark.asyncio
    async def test_reload_response_has_note(self):
        """Response contains note about handler limitation."""
        result = await handle_reload_server({})
        data = json.loads(result[0].text)
        assert "note" in data
        assert "NOT reloaded" in data["note"]


class TestHandleSystemInfoAIProvidersDiscovery:
    """ai_providers utilise AIConfig.get_available_providers (single source).

    Régression du bug d'origine : ``AIProviderFactory.create(name)`` était
    appelé avec un seul argument alors que la signature exige
    ``(provider, config)``, levant ``TypeError`` silencieusement avalée par
    ``except Exception: pass`` → ``ai_providers: []`` constant en prod.
    """

    @pytest.mark.asyncio
    async def test_uses_ai_config_get_available_providers(self):
        """Le retour ai_providers vient de get_ai_config().get_available_providers()."""
        from magma_cycling._mcp.handlers.admin import handle_system_info

        fake_config = MagicMock()
        fake_config.get_available_providers.return_value = ["mistral_api", "claude_api"]

        with patch("magma_cycling.config.get_ai_config", return_value=fake_config):
            result = await handle_system_info({})

        data = json.loads(result[0].text)
        assert data["ai_providers"] == ["mistral_api", "claude_api"]
        fake_config.get_available_providers.assert_called_once()

    @pytest.mark.asyncio
    async def test_discovery_failure_logs_warning_and_returns_empty(self, caplog):
        """Si get_ai_config() raise, log warning et retourne []."""
        import logging

        from magma_cycling._mcp.handlers.admin import handle_system_info

        with patch(
            "magma_cycling.config.get_ai_config",
            side_effect=RuntimeError("simulated config failure"),
        ):
            with caplog.at_level(logging.WARNING, logger="magma_cycling._mcp.handlers.admin"):
                result = await handle_system_info({})

        data = json.loads(result[0].text)
        assert data["ai_providers"] == []
        warnings = [r for r in caplog.records if "ai_provider discovery failed" in r.message]
        assert len(warnings) == 1
        assert "simulated config failure" in warnings[0].message
