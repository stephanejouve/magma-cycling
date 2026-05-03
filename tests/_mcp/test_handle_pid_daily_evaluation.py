"""Tests for the MCP handler ``pid-daily-evaluation``.

Wraps ``PIDDailyEvaluator`` (legacy CLI ``pid-daily-evaluation``) to expose
its capability via MCP. Tests focus on the wiring (handler → evaluator →
response) and mode dispatch (daily vs cycle).
"""

import json
from unittest.mock import MagicMock, patch

import pytest

pytest_plugins = ("pytest_asyncio",)

EVAL_PATCH = "magma_cycling.scripts.pid_daily_evaluation.PIDDailyEvaluator"


class TestHandlePidDailyEvaluation:
    @pytest.mark.asyncio
    async def test_daily_mode_default(self):
        """mode=daily (default) → run_daily_evaluation called."""
        from magma_cycling.mcp_server import handle_pid_daily_evaluation

        evaluator = MagicMock()
        evaluator.run_daily_evaluation.return_value = {
            "status": "SUCCESS",
            "metrics": {"ctl_avg": 35.2, "atl_avg": 28.0},
            "test_recommendation": None,
        }

        with patch(EVAL_PATCH, return_value=evaluator) as cls:
            result = await handle_pid_daily_evaluation({})

        cls.assert_called_once_with(dry_run=False)
        evaluator.run_daily_evaluation.assert_called_once_with(days_back=7)
        evaluator.run_cycle_evaluation.assert_not_called()

        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["mode"] == "daily"
        assert data["status"] == "SUCCESS"
        assert data["dry_run"] is False
        assert "metrics_summary" in data

    @pytest.mark.asyncio
    async def test_daily_mode_custom_days_back(self):
        """days_back propagated."""
        from magma_cycling.mcp_server import handle_pid_daily_evaluation

        evaluator = MagicMock()
        evaluator.run_daily_evaluation.return_value = {"status": "SUCCESS"}

        with patch(EVAL_PATCH, return_value=evaluator):
            await handle_pid_daily_evaluation({"days_back": 14})

        evaluator.run_daily_evaluation.assert_called_once_with(days_back=14)

    @pytest.mark.asyncio
    async def test_cycle_mode_requires_measured_ftp(self):
        """mode=cycle without measured_ftp → error response, no eval call."""
        from magma_cycling.mcp_server import handle_pid_daily_evaluation

        with patch(EVAL_PATCH) as cls:
            result = await handle_pid_daily_evaluation({"mode": "cycle"})

        cls.assert_not_called()
        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["status"] == "error"
        assert "measured_ftp" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_cycle_mode_with_ftp(self):
        """mode=cycle + measured_ftp → run_cycle_evaluation called with FTP."""
        from magma_cycling.mcp_server import handle_pid_daily_evaluation

        evaluator = MagicMock()
        evaluator.run_cycle_evaluation.return_value = {
            "status": "SUCCESS",
            "pid_correction": {"tss_per_week_adjusted": 420},
        }

        with patch(EVAL_PATCH, return_value=evaluator):
            result = await handle_pid_daily_evaluation(
                {"mode": "cycle", "measured_ftp": 285.5, "cycle_weeks": 4}
            )

        evaluator.run_cycle_evaluation.assert_called_once_with(
            measured_ftp=285.5,
            cycle_duration_weeks=4,
        )

        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["mode"] == "cycle"
        assert data["status"] == "SUCCESS"
        assert "pid_correction" in data

    @pytest.mark.asyncio
    async def test_dry_run_propagated(self):
        """dry_run=True propagated to evaluator constructor."""
        from magma_cycling.mcp_server import handle_pid_daily_evaluation

        evaluator = MagicMock()
        evaluator.run_daily_evaluation.return_value = {"status": "SUCCESS"}

        with patch(EVAL_PATCH, return_value=evaluator) as cls:
            result = await handle_pid_daily_evaluation({"dry_run": True})

        cls.assert_called_once_with(dry_run=True)
        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["dry_run"] is True


class TestPidDailyEvaluationWiring:
    """Verify the handler is properly wired into TOOL_HANDLERS dispatcher."""

    def test_handler_registered_in_dispatcher(self):
        from magma_cycling.mcp_server import TOOL_HANDLERS, handle_pid_daily_evaluation

        assert "pid-daily-evaluation" in TOOL_HANDLERS
        assert TOOL_HANDLERS["pid-daily-evaluation"] is handle_pid_daily_evaluation

    def test_tool_count_includes_new_handler(self):
        from magma_cycling.mcp_server import TOOL_HANDLERS

        assert "pid-daily-evaluation" in TOOL_HANDLERS
        assert len(TOOL_HANDLERS) >= 64

    def test_tool_schema_exposed(self):
        from magma_cycling._mcp.schemas.analysis import get_tools

        names = [t.name for t in get_tools()]
        assert "pid-daily-evaluation" in names
