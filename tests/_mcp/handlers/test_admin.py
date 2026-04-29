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


class TestHandleSystemInfoToolCount:
    """tool_count est aligné avec TOOL_HANDLERS (single source of truth)."""

    @pytest.mark.asyncio
    async def test_tool_count_matches_handlers(self):
        """`tool_count` retourné == `len(TOOL_HANDLERS)` — pas de drift possible.

        Régression : avant le fix, system-info re-listait 10 schemas et
        oubliait `terrain` + `handoff`, retournant 54 alors que TOOL_HANDLERS
        en contient 60. Ce test pin l'invariant : ce que system-info compte
        doit être exactement ce que le serveur peut dispatcher.
        """
        from magma_cycling._mcp.handlers.admin import handle_system_info
        from magma_cycling.mcp_server import TOOL_HANDLERS

        result = await handle_system_info({})
        data = json.loads(result[0].text)
        assert data["tool_count"] == len(TOOL_HANDLERS)
