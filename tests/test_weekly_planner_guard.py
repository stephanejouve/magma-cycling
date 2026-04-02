"""Tests for weekly-planner overwrite guard (Bug #3 — S087)."""

import json
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling._mcp.handlers.planning import handle_weekly_planner


def _extract_result(response):
    """Extract the JSON result from MCP TextContent response."""
    return json.loads(response[0].text)


@contextmanager
def _noop_suppress():
    """No-op replacement for suppress_stdout_stderr."""
    yield


@pytest.fixture
def mock_planner(tmp_path):
    """Create a mock WeeklyPlanner with a temp planning_dir."""
    planner = MagicMock()
    planner.planning_dir = tmp_path
    planner.current_metrics = {}
    planner.previous_week_bilan = None
    planner.context_files = {}
    planner.generate_planning_prompt.return_value = "test prompt"
    planner.collect_current_metrics.return_value = {}
    planner.load_previous_week_bilan.return_value = None
    planner.load_context_files.return_value = {}
    return planner


class TestWeeklyPlannerGuard:
    """Test the overwrite protection guard."""

    @pytest.mark.asyncio
    async def test_rejects_overwrite_without_force(self, mock_planner, tmp_path):
        """Existing planning + no force → error with suggestion."""
        existing = tmp_path / "week_planning_S087.json"
        existing.write_text("{}", encoding="utf-8")

        with (
            patch(
                "magma_cycling.weekly_planner.WeeklyPlanner",
                return_value=mock_planner,
            ),
            patch(
                "magma_cycling._mcp.handlers.planning.suppress_stdout_stderr",
                _noop_suppress,
            ),
        ):
            response = await handle_weekly_planner({"week_id": "S087", "start_date": "2026-03-30"})

        result = _extract_result(response)
        assert result["error"] == "planning_exists"
        assert "force=true" in result["message"]

    @pytest.mark.asyncio
    async def test_allows_overwrite_with_force(self, mock_planner, tmp_path):
        """Existing planning + force=True → backup created + continues."""
        existing = tmp_path / "week_planning_S087.json"
        existing.write_text("{}", encoding="utf-8")

        mock_backup = MagicMock()
        mock_tower = MagicMock()
        mock_tower.backup_system.backup_week_files = mock_backup

        with (
            patch(
                "magma_cycling.weekly_planner.WeeklyPlanner",
                return_value=mock_planner,
            ),
            patch(
                "magma_cycling._mcp.handlers.planning.suppress_stdout_stderr",
                _noop_suppress,
            ),
            patch(
                "magma_cycling.planning.control_tower.planning_tower",
                mock_tower,
            ),
        ):
            response = await handle_weekly_planner(
                {"week_id": "S087", "start_date": "2026-03-30", "force": True}
            )

        result = _extract_result(response)
        assert "error" not in result or result.get("error") != "planning_exists"
        mock_backup.assert_called_once_with("S087")

    @pytest.mark.asyncio
    async def test_creates_new_without_force(self, mock_planner, tmp_path):
        """No existing planning + no force → proceeds normally."""
        with (
            patch(
                "magma_cycling.weekly_planner.WeeklyPlanner",
                return_value=mock_planner,
            ),
            patch(
                "magma_cycling._mcp.handlers.planning.suppress_stdout_stderr",
                _noop_suppress,
            ),
        ):
            response = await handle_weekly_planner({"week_id": "S087", "start_date": "2026-03-30"})

        result = _extract_result(response)
        assert result.get("error") != "planning_exists"
        assert result["week_id"] == "S087"
