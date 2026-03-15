"""Tests for weekly planner MCP prompt exposure."""

from __future__ import annotations

import asyncio
from contextlib import nullcontext
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling._mcp.handlers.planning import handle_weekly_planner


def _run(coro):
    """Run async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


FAKE_PROMPT = "A" * 16000  # Simulates a 16k-char planning prompt


@pytest.fixture()
def _patch_planner():
    """Patch WeeklyPlanner to avoid real API/filesystem calls."""
    mock_cls = MagicMock()
    instance = mock_cls.return_value
    instance.collect_current_metrics.return_value = {}
    instance.load_previous_week_bilan.return_value = ""
    instance.load_context_files.return_value = {}
    instance.generate_planning_prompt.return_value = FAKE_PROMPT

    with (
        patch(
            "magma_cycling.weekly_planner.WeeklyPlanner",
            mock_cls,
        ),
        patch(
            "magma_cycling._mcp.handlers.planning.suppress_stdout_stderr",
            return_value=nullcontext(),
        ),
    ):
        yield


BASE_ARGS = {
    "week_id": "S099",
    "start_date": "2026-03-09",
}


@pytest.mark.usefixtures("_patch_planner")
class TestWeeklyPlannerPromptExposure:
    """Test prompt exposure in weekly planner MCP handler."""

    @patch("magma_cycling._mcp.handlers.planning.subprocess")
    def test_clipboard_provider_copies_to_clipboard(self, mock_subprocess):
        """Clipboard provider copies full prompt via pbcopy."""
        mock_subprocess.run.return_value = None
        args = {**BASE_ARGS, "provider": "clipboard"}
        result = _run(handle_weekly_planner(args))

        import json

        data = json.loads(result[0].text)
        assert data["status"] == "copied_to_clipboard"
        assert "prompt" not in data  # Full prompt NOT in response
        mock_subprocess.run.assert_called_once()

    @patch("magma_cycling._mcp.handlers.planning.subprocess")
    def test_clipboard_fallback_on_error(self, mock_subprocess):
        """Clipboard fallback returns full prompt when pbcopy fails."""
        mock_subprocess.run.side_effect = OSError("pbcopy not found")
        args = {**BASE_ARGS, "provider": "clipboard"}
        result = _run(handle_weekly_planner(args))

        import json

        data = json.loads(result[0].text)
        assert data["status"] == "clipboard_error"
        assert data["prompt"] == FAKE_PROMPT

    def test_claude_api_returns_full_prompt(self):
        """claude_api provider returns the complete prompt."""
        args = {**BASE_ARGS, "provider": "claude_api"}
        result = _run(handle_weekly_planner(args))

        import json

        data = json.loads(result[0].text)
        assert data["prompt"] == FAKE_PROMPT
        assert len(data["prompt"]) == 16000

    def test_mistral_api_returns_full_prompt(self):
        """mistral_api provider returns the complete prompt."""
        args = {**BASE_ARGS, "provider": "mistral_api"}
        result = _run(handle_weekly_planner(args))

        import json

        data = json.loads(result[0].text)
        assert data["prompt"] == FAKE_PROMPT
        assert len(data["prompt"]) == 16000

    def test_ai_provider_next_steps(self):
        """AI providers get next_steps mentioning modify-session-details."""
        args = {**BASE_ARGS, "provider": "claude_api"}
        result = _run(handle_weekly_planner(args))

        import json

        data = json.loads(result[0].text)
        steps_text = " ".join(data["next_steps"])
        assert "modify-session-details" in steps_text
        assert "sync-week-to-intervals" in steps_text
