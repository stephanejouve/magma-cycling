"""Tests for the MCP handler ``sync-recent-activities`` (replaces session-monitor).

On-demand MCP equivalent of the legacy LaunchAgent ``session-monitor`` (poller
every 20 min). Detects new cycling activities and triggers the post-session
chain.

Tests focus on the detection logic + chain dispatch — not on the underlying
chained handlers (each has its own test suite).
"""

import json
from datetime import date as _date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import TextContent

pytest_plugins = ("pytest_asyncio",)


def _ok_text(payload):
    """Build a TextContent list as the chained handlers would return."""
    return [TextContent(type="text", text=json.dumps(payload) + "\n[meta]")]


@pytest.fixture
def fake_plan():
    """Plan with 2 sessions today (S091-02 pending, S091-03 completed)."""
    today = _date.today()
    plan = MagicMock()
    s2 = MagicMock(session_id="S091-02", session_date=today, status="pending")
    s3 = MagicMock(session_id="S091-03", session_date=today, status="completed")
    plan.planned_sessions = [s2, s3]
    return plan


class TestDetection:
    @pytest.mark.asyncio
    async def test_no_planning_returns_no_planning(self):
        from magma_cycling.mcp_server import handle_sync_recent_activities

        tower = MagicMock()
        tower.read_week.side_effect = FileNotFoundError("no week")

        with (
            patch(
                "magma_cycling.daily_sync.calculate_current_week_info",
                return_value=("S091", _date.today()),
            ),
            patch("magma_cycling.planning.control_tower.planning_tower", tower),
        ):
            result = await handle_sync_recent_activities({})

        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["status"] == "no_planning"

    @pytest.mark.asyncio
    async def test_no_session_today(self, fake_plan):
        from magma_cycling.mcp_server import handle_sync_recent_activities

        # Override : aucune session dont session_date == today
        fake_plan.planned_sessions = []
        tower = MagicMock()
        tower.read_week.return_value = fake_plan

        with (
            patch(
                "magma_cycling.daily_sync.calculate_current_week_info",
                return_value=("S091", _date.today()),
            ),
            patch("magma_cycling.planning.control_tower.planning_tower", tower),
        ):
            result = await handle_sync_recent_activities({})

        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["status"] == "no_session_today"

    @pytest.mark.asyncio
    async def test_all_terminal(self):
        from magma_cycling.mcp_server import handle_sync_recent_activities

        today = _date.today()
        plan = MagicMock()
        s = MagicMock(session_id="S091-02", session_date=today, status="completed")
        plan.planned_sessions = [s]

        tower = MagicMock()
        tower.read_week.return_value = plan

        with (
            patch(
                "magma_cycling.daily_sync.calculate_current_week_info",
                return_value=("S091", today),
            ),
            patch("magma_cycling.planning.control_tower.planning_tower", tower),
        ):
            result = await handle_sync_recent_activities({})

        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["status"] == "all_terminal"

    @pytest.mark.asyncio
    async def test_no_new_activity(self, fake_plan):
        """1 session pending + 1 completed + 1 activity Intervals → no_new_activity."""
        from magma_cycling.mcp_server import handle_sync_recent_activities

        tower = MagicMock()
        tower.read_week.return_value = fake_plan

        client = MagicMock()
        client.get_activities.return_value = [
            {"id": "i1", "type": "Ride", "icu_ignore_time": False}
        ]

        with (
            patch(
                "magma_cycling.daily_sync.calculate_current_week_info",
                return_value=("S091", _date.today()),
            ),
            patch("magma_cycling.planning.control_tower.planning_tower", tower),
            patch("magma_cycling.config.create_intervals_client", return_value=client),
        ):
            result = await handle_sync_recent_activities({})

        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["status"] == "no_new_activity"
        assert data["activities_count"] == 1
        assert data["completed_count"] == 1


class TestChain:
    @pytest.mark.asyncio
    async def test_force_skips_detection_runs_chain(self):
        """force=true bypass detection, run chain inconditionnellement."""
        from magma_cycling.mcp_server import handle_sync_recent_activities

        with (
            patch(
                "magma_cycling._mcp.handlers.planning.handle_daily_sync",
                new=AsyncMock(return_value=_ok_text({"ok": "daily"})),
            ) as ds,
            patch(
                "magma_cycling._mcp.handlers.analysis.handle_check_workout_adherence",
                new=AsyncMock(return_value=_ok_text({"ok": "adh"})),
            ) as adh,
            patch(
                "magma_cycling._mcp.handlers.analysis.handle_pid_daily_evaluation",
                new=AsyncMock(return_value=_ok_text({"ok": "pid"})),
            ) as pid,
        ):
            result = await handle_sync_recent_activities({"force": True})

        ds.assert_awaited_once()
        adh.assert_awaited_once_with({"mode": "weekly_alert"})
        pid.assert_awaited_once_with({"mode": "daily", "days_back": 7})

        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["status"] == "chain_executed"
        assert data["force"] is True
        assert data["chain"]["daily_sync"]["status"] == "ok"
        assert data["chain"]["adherence"]["status"] == "ok"
        assert data["chain"]["pid_evaluation"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_chain_continues_on_step_failure(self):
        """Si une étape lève, les suivantes s'exécutent quand même."""
        from magma_cycling.mcp_server import handle_sync_recent_activities

        with (
            patch(
                "magma_cycling._mcp.handlers.planning.handle_daily_sync",
                new=AsyncMock(side_effect=RuntimeError("daily-sync failed")),
            ),
            patch(
                "magma_cycling._mcp.handlers.analysis.handle_check_workout_adherence",
                new=AsyncMock(return_value=_ok_text({"ok": "adh"})),
            ) as adh,
            patch(
                "magma_cycling._mcp.handlers.analysis.handle_pid_daily_evaluation",
                new=AsyncMock(return_value=_ok_text({"ok": "pid"})),
            ) as pid,
        ):
            result = await handle_sync_recent_activities({"force": True})

        adh.assert_awaited_once()
        pid.assert_awaited_once()

        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["status"] == "chain_executed"
        assert data["chain"]["daily_sync"]["status"] == "error"
        assert "daily-sync failed" in data["chain"]["daily_sync"]["error"]
        assert data["chain"]["adherence"]["status"] == "ok"
        assert data["chain"]["pid_evaluation"]["status"] == "ok"


class TestSyncRecentActivitiesWiring:
    """Verify the handler is properly wired into TOOL_HANDLERS dispatcher."""

    def test_handler_registered_in_dispatcher(self):
        from magma_cycling.mcp_server import (
            TOOL_HANDLERS,
            handle_sync_recent_activities,
        )

        assert "sync-recent-activities" in TOOL_HANDLERS
        assert TOOL_HANDLERS["sync-recent-activities"] is handle_sync_recent_activities

    def test_tool_count_includes_new_handler(self):
        from magma_cycling.mcp_server import TOOL_HANDLERS

        assert "sync-recent-activities" in TOOL_HANDLERS
        assert len(TOOL_HANDLERS) >= 66

    def test_tool_schema_exposed(self):
        from magma_cycling._mcp.schemas.planning import get_tools

        names = [t.name for t in get_tools()]
        assert "sync-recent-activities" in names
