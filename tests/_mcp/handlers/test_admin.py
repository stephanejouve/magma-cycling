"""Tests for _mcp/handlers/admin.py."""

import json
import types
from unittest.mock import patch

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


class TestHandleSystemInfoAIProvidersLogging:
    """Probe failures sur ai_providers loggent un warning au lieu d'être silencés."""

    @pytest.mark.asyncio
    async def test_provider_probe_exception_is_logged(self, caplog):
        """Si AIProviderFactory.create() ou validate_config() raise, log warning.

        Régression : le bare `except: pass` rendait invisible la cause de
        `ai_providers: []` côté preprod alors que Mistral fonctionnait à
        l'exécution. Maintenant l'opérateur voit la cause au log.
        """
        import logging

        from magma_cycling._mcp.handlers.admin import handle_system_info

        with patch(
            "magma_cycling.ai_providers.factory.AIProviderFactory.create",
            side_effect=RuntimeError("simulated probe failure"),
        ):
            with caplog.at_level(logging.WARNING, logger="magma_cycling._mcp.handlers.admin"):
                await handle_system_info({})

        # 3 providers probés (claude_api, mistral_api, ollama) → 3 warnings
        warnings = [r for r in caplog.records if "ai_provider probe failed" in r.message]
        assert len(warnings) == 3
        for w in warnings:
            assert "simulated probe failure" in w.message
