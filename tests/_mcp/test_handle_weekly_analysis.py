"""Tests for the MCP handler ``weekly-analysis``.

Wraps ``run_weekly_analysis`` (legacy CLI ``weekly-analysis``) to expose its
capability via MCP. Tests focus on the wiring (handler → run_weekly_analysis
→ response), not on the underlying weekly aggregation/analyzer logic which
has its own test suite.
"""

import json
from datetime import date
from unittest.mock import patch

import pytest

pytest_plugins = ("pytest_asyncio",)

RUN_PATCH = "magma_cycling.workflows.workflow_weekly.run_weekly_analysis"


class TestHandleWeeklyAnalysis:
    @pytest.mark.asyncio
    async def test_success_generates_six_reports(self):
        """Happy path: returns the 6 report names + status."""
        from magma_cycling.mcp_server import handle_weekly_analysis

        fake_reports = {
            "bilan_final": "...",
            "transition": "...",
            "workout_history": "...",
            "metrics_evolution": "...",
            "training_learnings": "...",
            "protocol_adaptations": "...",
        }
        with patch(RUN_PATCH, return_value=fake_reports) as run:
            result = await handle_weekly_analysis({"week_id": "S091", "start_date": "2026-04-27"})

        run.assert_called_once_with(
            week="S091",
            start_date=date(2026, 4, 27),
            ai_analysis=False,
        )

        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["status"] == "success"
        assert data["week_id"] == "S091"
        assert data["start_date"] == "2026-04-27"
        assert data["report_count"] == 6
        assert sorted(data["reports_generated"]) == sorted(fake_reports.keys())

    @pytest.mark.asyncio
    async def test_ai_analysis_disabled_in_mcp(self):
        """ai_analysis MUST be False — clipboard side-effect not relevant in MCP."""
        from magma_cycling.mcp_server import handle_weekly_analysis

        with patch(RUN_PATCH, return_value={}) as run:
            await handle_weekly_analysis({"week_id": "S091", "start_date": "2026-04-27"})

        # Vérifie que ai_analysis=False est passé explicitement
        kwargs = run.call_args.kwargs
        assert kwargs.get("ai_analysis") is False

    @pytest.mark.asyncio
    async def test_invalid_date_format_raises(self):
        """Date pas au format YYYY-MM-DD → ValueError du datetime parser."""
        from magma_cycling.mcp_server import handle_weekly_analysis

        with pytest.raises(ValueError):
            await handle_weekly_analysis({"week_id": "S091", "start_date": "27/04/2026"})

    @pytest.mark.asyncio
    async def test_missing_required_args_raises(self):
        """week_id et start_date sont required."""
        from magma_cycling.mcp_server import handle_weekly_analysis

        with pytest.raises(KeyError):
            await handle_weekly_analysis({"week_id": "S091"})

        with pytest.raises(KeyError):
            await handle_weekly_analysis({"start_date": "2026-04-27"})


class TestWeeklyAnalysisWiring:
    """Verify the handler is properly wired into TOOL_HANDLERS dispatcher."""

    def test_handler_registered_in_dispatcher(self):
        from magma_cycling.mcp_server import TOOL_HANDLERS, handle_weekly_analysis

        assert "weekly-analysis" in TOOL_HANDLERS
        assert TOOL_HANDLERS["weekly-analysis"] is handle_weekly_analysis

    def test_tool_count_includes_new_handler(self):
        from magma_cycling.mcp_server import TOOL_HANDLERS

        # Test dynamique pour résilience aux ajouts futurs.
        assert "weekly-analysis" in TOOL_HANDLERS
        assert len(TOOL_HANDLERS) >= 62

    def test_tool_schema_exposed(self):
        from magma_cycling._mcp.schemas.planning import get_tools

        names = [t.name for t in get_tools()]
        assert "weekly-analysis" in names
