"""Tests for the MCP handler ``insert-workout-history``.

Wraps ``WorkoutHistoryManager.insert_analysis`` (legacy CLI ``insert-analysis``)
to expose its capability via MCP. Tests focus on the wiring (handler → manager
→ response), not on the underlying ``insert_analysis`` logic which has its own
test suite in ``tests/workflows/test_insert_analysis.py``.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

pytest_plugins = ("pytest_asyncio",)

MGR_PATCH = "magma_cycling.inserter.history.WorkoutHistoryManager"


class TestHandleInsertWorkoutHistory:
    @pytest.mark.asyncio
    async def test_success_inserts_via_manager(self):
        """Happy path: manager returns True → handler returns success."""
        from magma_cycling.mcp_server import handle_insert_workout_history

        mgr = MagicMock()
        mgr.insert_analysis.return_value = True

        with patch(MGR_PATCH, return_value=mgr) as mgr_cls:
            result = await handle_insert_workout_history(
                {"analysis_text": "### S091-02 | INT | 28/04/2026\n\nfake analysis"}
            )

        # Manager called with yes_confirm default False
        mgr_cls.assert_called_once_with(yes_confirm=False)
        mgr.insert_analysis.assert_called_once()

        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["status"] == "success"
        assert "inserted" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_yes_confirm_propagated_to_manager(self):
        """yes_confirm=True passes through to WorkoutHistoryManager constructor."""
        from magma_cycling.mcp_server import handle_insert_workout_history

        mgr = MagicMock()
        mgr.insert_analysis.return_value = True

        with patch(MGR_PATCH, return_value=mgr) as mgr_cls:
            await handle_insert_workout_history(
                {
                    "analysis_text": "### S091-03 | TEC | 29/04/2026\n\nfake",
                    "yes_confirm": True,
                }
            )

        mgr_cls.assert_called_once_with(yes_confirm=True)

    @pytest.mark.asyncio
    async def test_failure_returns_error_status(self):
        """Manager returns False (duplicate, parse error) → handler returns error."""
        from magma_cycling.mcp_server import handle_insert_workout_history

        mgr = MagicMock()
        mgr.insert_analysis.return_value = False

        with patch(MGR_PATCH, return_value=mgr):
            result = await handle_insert_workout_history(
                {"analysis_text": "### dup | INT | 28/04/2026\n\nx"}
            )

        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["status"] == "error"
        assert "duplicate" in data["message"].lower() or "parsing" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_missing_analysis_text_raises(self):
        """Empty / missing analysis_text rejected with ValueError."""
        from magma_cycling.mcp_server import handle_insert_workout_history

        with pytest.raises(ValueError, match="analysis_text"):
            await handle_insert_workout_history({})

        with pytest.raises(ValueError, match="analysis_text"):
            await handle_insert_workout_history({"analysis_text": ""})

        with pytest.raises(ValueError, match="analysis_text"):
            await handle_insert_workout_history({"analysis_text": None})


class TestInsertWorkoutHistoryWiring:
    """Verify the handler is properly wired into TOOL_HANDLERS dispatcher."""

    def test_handler_registered_in_dispatcher(self):
        from magma_cycling.mcp_server import TOOL_HANDLERS, handle_insert_workout_history

        assert "insert-workout-history" in TOOL_HANDLERS
        assert TOOL_HANDLERS["insert-workout-history"] is handle_insert_workout_history

    def test_tool_count_includes_new_handler(self):
        from magma_cycling.mcp_server import TOOL_HANDLERS

        # Test dynamique pour résilience aux ajouts futurs : on vérifie que
        # le handler est bien dans le dispatcher, pas la valeur exacte de la
        # constante (qui évolue à chaque nouveau handler ajouté).
        assert "insert-workout-history" in TOOL_HANDLERS
        assert len(TOOL_HANDLERS) >= 61

    def test_tool_schema_exposed(self):
        from magma_cycling._mcp.schemas.rest import get_tools

        names = [t.name for t in get_tools()]
        assert "insert-workout-history" in names
