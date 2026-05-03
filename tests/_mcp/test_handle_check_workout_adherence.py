"""Tests for the MCP handler ``check-workout-adherence`` (daily batch).

Wraps ``WorkoutAdherenceChecker`` (legacy CLI ``check-workout-adherence``)
to expose its capability via MCP. Different from ``analyze-session-adherence``
which is per-session.

Tests focus on the wiring (handler → checker → response) and mode dispatch
(day, week, weekly_alert).
"""

import json
from unittest.mock import MagicMock, patch

import pytest

pytest_plugins = ("pytest_asyncio",)

CHECKER_PATCH = "scripts.monitoring.check_workout_adherence.WorkoutAdherenceChecker"


class TestHandleCheckWorkoutAdherence:
    @pytest.mark.asyncio
    async def test_day_mode_default(self):
        """mode=day (default) → check_date called."""
        from magma_cycling.mcp_server import handle_check_workout_adherence

        checker = MagicMock()
        checker.check_date.return_value = {"date": "2026-05-03", "adherence_pct": 92.0}

        with patch(CHECKER_PATCH, return_value=checker) as cls:
            result = await handle_check_workout_adherence({"date": "2026-05-03"})

        cls.assert_called_once_with(dry_run=False)
        checker.check_date.assert_called_once()
        checker.check_week.assert_not_called()
        checker.check_weekly_adherence_and_alert.assert_not_called()

        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["mode"] == "day"
        assert data["date"] == "2026-05-03"
        assert data["status"] == "SUCCESS"

    @pytest.mark.asyncio
    async def test_week_mode_calls_check_week(self):
        """mode=week → check_week called with Monday of date's week."""
        from magma_cycling.mcp_server import handle_check_workout_adherence

        checker = MagicMock()
        checker.check_week.return_value = {"week": "S091", "adherence_pct": 85.0}

        # 2026-05-03 is a Sunday → Monday is 2026-04-27
        with patch(CHECKER_PATCH, return_value=checker):
            await handle_check_workout_adherence({"mode": "week", "date": "2026-05-03"})

        checker.check_week.assert_called_once()
        call_arg = checker.check_week.call_args.args[0]
        # Monday should be 2026-04-27
        assert call_arg.strftime("%Y-%m-%d") == "2026-04-27"

    @pytest.mark.asyncio
    async def test_weekly_alert_mode(self):
        """mode=weekly_alert → check_weekly_adherence_and_alert called."""
        from magma_cycling.mcp_server import handle_check_workout_adherence

        checker = MagicMock()
        checker.check_weekly_adherence_and_alert.return_value = {
            "alert_sent": False,
            "adherence_pct": 90.0,
        }

        with patch(CHECKER_PATCH, return_value=checker):
            await handle_check_workout_adherence({"mode": "weekly_alert"})

        checker.check_weekly_adherence_and_alert.assert_called_once()
        checker.check_date.assert_not_called()
        checker.check_week.assert_not_called()

    @pytest.mark.asyncio
    async def test_dry_run_propagated(self):
        """dry_run=True propagated to checker constructor."""
        from magma_cycling.mcp_server import handle_check_workout_adherence

        checker = MagicMock()
        checker.check_date.return_value = {"adherence_pct": 95.0}

        with patch(CHECKER_PATCH, return_value=checker) as cls:
            result = await handle_check_workout_adherence({"dry_run": True})

        cls.assert_called_once_with(dry_run=True)
        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["dry_run"] is True

    @pytest.mark.asyncio
    async def test_default_date_today(self):
        """Sans date arg → utilise today."""
        from datetime import datetime as _dt

        from magma_cycling.mcp_server import handle_check_workout_adherence

        checker = MagicMock()
        checker.check_date.return_value = {}

        with patch(CHECKER_PATCH, return_value=checker):
            result = await handle_check_workout_adherence({})

        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["date"] == _dt.now().strftime("%Y-%m-%d")


class TestCheckWorkoutAdherenceWiring:
    """Verify the handler is properly wired into TOOL_HANDLERS dispatcher."""

    def test_handler_registered_in_dispatcher(self):
        from magma_cycling.mcp_server import (
            TOOL_HANDLERS,
            handle_check_workout_adherence,
        )

        assert "check-workout-adherence" in TOOL_HANDLERS
        assert TOOL_HANDLERS["check-workout-adherence"] is handle_check_workout_adherence

    def test_tool_count_includes_new_handler(self):
        from magma_cycling.mcp_server import TOOL_HANDLERS

        assert "check-workout-adherence" in TOOL_HANDLERS
        assert len(TOOL_HANDLERS) >= 65

    def test_tool_schema_exposed(self):
        from magma_cycling._mcp.schemas.analysis import get_tools

        names = [t.name for t in get_tools()]
        assert "check-workout-adherence" in names

    def test_check_workout_adherence_distinct_from_analyze_session_adherence(self):
        """Both tools coexist — one is daily batch, the other is per-session."""
        from magma_cycling.mcp_server import TOOL_HANDLERS

        assert "check-workout-adherence" in TOOL_HANDLERS  # batch (PR3)
        assert "analyze-session-adherence" in TOOL_HANDLERS  # per-session (existing)
        assert (
            TOOL_HANDLERS["check-workout-adherence"]
            is not TOOL_HANDLERS["analyze-session-adherence"]
        )
