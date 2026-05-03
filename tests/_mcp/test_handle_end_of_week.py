"""Tests for the MCP handler ``end-of-week`` (PR6 portage final).

Wraps ``EndOfWeekWorkflow`` (legacy CLI ``end-of-week``) to expose its
capability via MCP. Tests focus on the wiring (handler → workflow →
response), the auto_calculate logic, and arg propagation.
"""

import json
from datetime import date as _date
from unittest.mock import MagicMock, patch

import pytest

pytest_plugins = ("pytest_asyncio",)

WORKFLOW_PATCH = "magma_cycling.workflows.end_of_week.EndOfWeekWorkflow"
TRANSITION_PATCH = "magma_cycling.workflows.end_of_week.calculate_weekly_transition"


class TestHandleEndOfWeek:
    @pytest.mark.asyncio
    async def test_auto_calculate_default(self):
        """auto_calculate=true (default) → uses calculate_weekly_transition."""
        from magma_cycling.mcp_server import handle_end_of_week

        workflow = MagicMock()
        workflow.run.return_value = True

        with (
            patch(
                TRANSITION_PATCH,
                return_value=("S091", "S092", _date(2026, 4, 27), _date(2026, 5, 4)),
            ) as transition,
            patch(WORKFLOW_PATCH, return_value=workflow) as cls,
        ):
            result = await handle_end_of_week({})

        transition.assert_called_once_with()
        cls.assert_called_once_with(
            week_completed="S091",
            week_next="S092",
            provider="mcp_direct",
            dry_run=False,
            auto=True,
            archive=False,
        )
        workflow.run.assert_called_once()

        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["status"] == "success"
        assert data["week_completed"] == "S091"
        assert data["week_next"] == "S092"
        assert data["provider"] == "mcp_direct"

    @pytest.mark.asyncio
    async def test_explicit_weeks(self):
        """auto_calculate=false → uses explicit week_completed/week_next."""
        from magma_cycling.mcp_server import handle_end_of_week

        workflow = MagicMock()
        workflow.run.return_value = True

        with patch(WORKFLOW_PATCH, return_value=workflow) as cls:
            await handle_end_of_week(
                {
                    "auto_calculate": False,
                    "week_completed": "S080",
                    "week_next": "S081",
                }
            )

        cls.assert_called_once()
        kwargs = cls.call_args.kwargs
        assert kwargs["week_completed"] == "S080"
        assert kwargs["week_next"] == "S081"

    @pytest.mark.asyncio
    async def test_auto_calculate_false_missing_args_errors(self):
        """auto_calculate=false sans week_completed/week_next → error."""
        from magma_cycling.mcp_server import handle_end_of_week

        result = await handle_end_of_week({"auto_calculate": False})

        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["status"] == "error"
        assert "auto_calculate" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_failure_returns_failure_status(self):
        """workflow.run() returns False → status=failure."""
        from magma_cycling.mcp_server import handle_end_of_week

        workflow = MagicMock()
        workflow.run.return_value = False

        with (
            patch(
                TRANSITION_PATCH,
                return_value=("S091", "S092", _date(2026, 4, 27), _date(2026, 5, 4)),
            ),
            patch(WORKFLOW_PATCH, return_value=workflow),
        ):
            result = await handle_end_of_week({})

        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["status"] == "failure"

    @pytest.mark.asyncio
    async def test_dry_run_propagated(self):
        """dry_run=True propagated to workflow."""
        from magma_cycling.mcp_server import handle_end_of_week

        workflow = MagicMock()
        workflow.run.return_value = True

        with (
            patch(
                TRANSITION_PATCH,
                return_value=("S091", "S092", _date(2026, 4, 27), _date(2026, 5, 4)),
            ),
            patch(WORKFLOW_PATCH, return_value=workflow) as cls,
        ):
            result = await handle_end_of_week({"dry_run": True})

        kwargs = cls.call_args.kwargs
        assert kwargs["dry_run"] is True
        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["dry_run"] is True

    @pytest.mark.asyncio
    async def test_archive_propagated(self):
        """archive=True propagated to workflow."""
        from magma_cycling.mcp_server import handle_end_of_week

        workflow = MagicMock()
        workflow.run.return_value = True

        with (
            patch(
                TRANSITION_PATCH,
                return_value=("S091", "S092", _date(2026, 4, 27), _date(2026, 5, 4)),
            ),
            patch(WORKFLOW_PATCH, return_value=workflow) as cls,
        ):
            await handle_end_of_week({"archive": True})

        kwargs = cls.call_args.kwargs
        assert kwargs["archive"] is True

    @pytest.mark.asyncio
    async def test_provider_propagated(self):
        """provider arg propagated to workflow."""
        from magma_cycling.mcp_server import handle_end_of_week

        workflow = MagicMock()
        workflow.run.return_value = True

        with (
            patch(
                TRANSITION_PATCH,
                return_value=("S091", "S092", _date(2026, 4, 27), _date(2026, 5, 4)),
            ),
            patch(WORKFLOW_PATCH, return_value=workflow) as cls,
        ):
            await handle_end_of_week({"provider": "claude_api"})

        kwargs = cls.call_args.kwargs
        assert kwargs["provider"] == "claude_api"

    @pytest.mark.asyncio
    async def test_auto_always_true_in_mcp(self):
        """auto MUST be True in MCP context (no interactive prompts)."""
        from magma_cycling.mcp_server import handle_end_of_week

        workflow = MagicMock()
        workflow.run.return_value = True

        with (
            patch(
                TRANSITION_PATCH,
                return_value=("S091", "S092", _date(2026, 4, 27), _date(2026, 5, 4)),
            ),
            patch(WORKFLOW_PATCH, return_value=workflow) as cls,
        ):
            await handle_end_of_week({})

        # Le user ne peut PAS désactiver auto via MCP — toujours True
        kwargs = cls.call_args.kwargs
        assert kwargs["auto"] is True


class TestEndOfWeekWiring:
    """Verify the handler is properly wired into TOOL_HANDLERS dispatcher."""

    def test_handler_registered_in_dispatcher(self):
        from magma_cycling.mcp_server import TOOL_HANDLERS, handle_end_of_week

        assert "end-of-week" in TOOL_HANDLERS
        assert TOOL_HANDLERS["end-of-week"] is handle_end_of_week

    def test_tool_count_includes_new_handler(self):
        from magma_cycling.mcp_server import TOOL_HANDLERS

        assert "end-of-week" in TOOL_HANDLERS
        assert len(TOOL_HANDLERS) >= 67

    def test_tool_schema_exposed(self):
        from magma_cycling._mcp.schemas.planning import get_tools

        names = [t.name for t in get_tools()]
        assert "end-of-week" in names
