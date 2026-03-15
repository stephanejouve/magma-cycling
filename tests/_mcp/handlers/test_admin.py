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
