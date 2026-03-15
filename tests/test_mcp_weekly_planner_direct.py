"""Tests for mcp_direct provider in weekly planner handler."""

from __future__ import annotations

import asyncio
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling._mcp.handlers.planning import _parse_ai_workouts

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_workout_block(session_id, stype, name, version, first_line, body=""):
    """Build a single === WORKOUT ... === / === FIN WORKOUT === block."""
    header = f"{session_id}-{stype}-{name}-{version}"
    content = first_line
    if body:
        content += "\n" + body
    return f"=== WORKOUT {header} ===\n{content}\n=== FIN WORKOUT ==="


@pytest.fixture
def fake_ai_response():
    """Full AI response with 7 workouts."""
    blocks = [
        _make_workout_block(
            "S083-01",
            "END",
            "EnduranceDouce",
            "V001",
            "Endurance douce (60min, 45 TSS)",
            "- Z2 60min",
        ),
        _make_workout_block(
            "S083-02",
            "INT",
            "SweetSpotCourt",
            "V001",
            "Sweet Spot intervals (75min, 70 TSS)",
            "- Warmup 15min\n- 4x8min SS\n- Cooldown 10min",
        ),
        _make_workout_block(
            "S083-03",
            "REC",
            "RecupActive",
            "V001",
            "Récupération active (45min, 25 TSS)",
            "- Z1 45min",
        ),
        _make_workout_block(
            "S083-04",
            "INT",
            "VO2maxLong",
            "V001",
            "VO2max long intervals (90min, 95 TSS)",
            "- Warmup 15min\n- 5x5min VO2max\n- Cooldown 15min",
        ),
        _make_workout_block(
            "S083-05",
            "END",
            "EnduranceLongue",
            "V001",
            "Endurance longue (120min, 80 TSS)",
            "- Z2 120min",
        ),
        _make_workout_block(
            "S083-06",
            "INT",
            "Tempo",
            "V001",
            "Tempo soutenu (60min, 55 TSS)",
            "- Warmup 10min\n- 40min tempo\n- Cooldown 10min",
        ),
        _make_workout_block(
            "S083-07",
            "REC",
            "RecupLegere",
            "V001",
            "Récupération légère (30min, 15 TSS)",
            "- Z1 30min",
        ),
    ]
    return "\n\n".join(blocks)


START_DATE = date(2026, 3, 16)  # Monday


# ---------------------------------------------------------------------------
# Tests _parse_ai_workouts
# ---------------------------------------------------------------------------


class TestParseAiWorkouts:
    """Tests for _parse_ai_workouts helper."""

    def test_parse_7_workouts(self, fake_ai_response):
        """Parse complete response with 7 workouts."""
        result = _parse_ai_workouts(fake_ai_response, START_DATE)

        assert len(result) == 7
        # First workout
        assert result[0]["session_id"] == "S083-01"
        assert result[0]["type"] == "END"
        assert result[0]["name"] == "EnduranceDouce"
        assert result[0]["version"] == "V001"
        assert result[0]["tss_planned"] == 45
        assert result[0]["duration_min"] == 60
        assert result[0]["date"] == "2026-03-16"
        assert result[0]["status"] == "planned"
        # Last workout
        assert result[6]["session_id"] == "S083-07"
        assert result[6]["date"] == "2026-03-22"

    def test_parse_empty_response(self):
        """Empty text returns empty list."""
        assert _parse_ai_workouts("", START_DATE) == []

    def test_parse_partial_response(self):
        """Only 3 workouts in response."""
        blocks = "\n".join(
            [
                _make_workout_block("S083-01", "END", "A", "V001", "A (60min, 40 TSS)"),
                _make_workout_block("S083-02", "INT", "B", "V001", "B (75min, 70 TSS)"),
                _make_workout_block("S083-03", "REC", "C", "V001", "C (45min, 25 TSS)"),
            ]
        )
        result = _parse_ai_workouts(blocks, START_DATE)
        assert len(result) == 3

    def test_parse_malformed_name(self):
        """Malformed workout name is skipped without crash."""
        text = (
            "=== WORKOUT INVALID-NAME ===\n"
            "Some content\n"
            "=== FIN WORKOUT ===\n\n"
            + _make_workout_block("S083-01", "END", "Good", "V001", "Good (60min, 40 TSS)")
        )
        result = _parse_ai_workouts(text, START_DATE)
        assert len(result) == 1
        assert result[0]["session_id"] == "S083-01"

    def test_parse_no_tss_no_duration(self):
        """Workout without TSS/duration in first line gets 0 defaults."""
        text = _make_workout_block(
            "S083-01",
            "END",
            "Simple",
            "V001",
            "Just a simple workout",
        )
        result = _parse_ai_workouts(text, START_DATE)
        assert len(result) == 1
        assert result[0]["tss_planned"] == 0
        assert result[0]["duration_min"] == 0

    def test_parse_double_session(self):
        """Double session with letter suffix (e.g., S083-06a)."""
        text = _make_workout_block(
            "S083-06a",
            "INT",
            "Intervals",
            "V001",
            "Intervals (45min, 50 TSS)",
        )
        result = _parse_ai_workouts(text, START_DATE)
        assert len(result) == 1
        assert result[0]["session_id"] == "S083-06a"
        # Day 06 → offset 5 from Monday
        assert result[0]["date"] == "2026-03-21"


# ---------------------------------------------------------------------------
# Tests handle_weekly_planner with mcp_direct
# ---------------------------------------------------------------------------


def _run_async(coro):
    """Run async function synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_mock_planner():
    """Create a mock WeeklyPlanner with required attributes."""
    planner = MagicMock()
    planner.current_metrics = {"ftp": 250, "weight": 75}
    planner.planning_dir = MagicMock()
    planner.planning_dir.__truediv__ = MagicMock(return_value=MagicMock())
    return planner


class TestHandleWeeklyPlannerDirect:
    """Tests for handle_weekly_planner with provider=mcp_direct."""

    @patch("magma_cycling._mcp.handlers.planning._call_ai_provider")
    @patch("magma_cycling.weekly_planner.WeeklyPlanner")
    def test_mcp_direct_success(self, mock_planner_cls, mock_call_ai, fake_ai_response):
        """Successful mcp_direct flow returns plan_generated."""
        from magma_cycling._mcp.handlers.planning import handle_weekly_planner

        planner = _make_mock_planner()
        planner.generate_planning_prompt.return_value = "fake prompt"
        mock_planner_cls.return_value = planner
        mock_call_ai.return_value = fake_ai_response

        # Mock workouts_file path
        mock_file = MagicMock()
        planner.planning_dir.__truediv__.return_value = mock_file
        mock_file.__str__ = MagicMock(return_value="/tmp/S083_workouts.txt")

        result = _run_async(
            handle_weekly_planner(
                {
                    "week_id": "S083",
                    "start_date": "2026-03-16",
                    "provider": "mcp_direct",
                }
            )
        )

        import json

        data = json.loads(result[0].text)
        assert data["status"] == "plan_generated"
        assert data["sessions_count"] == 7
        assert len(data["sessions"]) == 7
        assert data["sessions"][0]["session_id"] == "S083-01"
        planner.save_planning_json.assert_called_once()

    @patch("magma_cycling._mcp.handlers.planning._call_ai_provider")
    @patch("magma_cycling.weekly_planner.WeeklyPlanner")
    def test_mcp_direct_ai_error_fallback(self, mock_planner_cls, mock_call_ai):
        """AI exception returns ai_error with prompt fallback."""
        from magma_cycling._mcp.handlers.planning import handle_weekly_planner

        planner = _make_mock_planner()
        planner.generate_planning_prompt.return_value = "fake prompt"
        mock_planner_cls.return_value = planner
        mock_call_ai.side_effect = RuntimeError("API timeout")

        result = _run_async(
            handle_weekly_planner(
                {
                    "week_id": "S083",
                    "start_date": "2026-03-16",
                    "provider": "mcp_direct",
                }
            )
        )

        import json

        data = json.loads(result[0].text)
        assert data["status"] == "ai_error"
        assert "API timeout" in data["error"]
        assert data["prompt"] == "fake prompt"

    @patch("magma_cycling._mcp.handlers.planning._call_ai_provider")
    @patch("magma_cycling.weekly_planner.WeeklyPlanner")
    def test_mcp_direct_parse_failure_fallback(self, mock_planner_cls, mock_call_ai):
        """AI returns text without workouts → ai_parse_failed."""
        from magma_cycling._mcp.handlers.planning import handle_weekly_planner

        planner = _make_mock_planner()
        planner.generate_planning_prompt.return_value = "fake prompt"
        mock_planner_cls.return_value = planner
        mock_call_ai.return_value = "Just some text without workout delimiters"

        mock_file = MagicMock()
        planner.planning_dir.__truediv__.return_value = mock_file

        result = _run_async(
            handle_weekly_planner(
                {
                    "week_id": "S083",
                    "start_date": "2026-03-16",
                    "provider": "mcp_direct",
                }
            )
        )

        import json

        data = json.loads(result[0].text)
        assert data["status"] == "ai_parse_failed"
        assert "no workouts could be parsed" in data["message"]
        assert "raw_response" in data

    @patch("magma_cycling._mcp.handlers.planning._call_ai_provider")
    @patch("magma_cycling.weekly_planner.WeeklyPlanner")
    def test_mcp_direct_partial_results(self, mock_planner_cls, mock_call_ai):
        """5/7 workouts parsed → plan_generated with warning."""
        from magma_cycling._mcp.handlers.planning import handle_weekly_planner

        partial_response = "\n\n".join(
            [
                _make_workout_block(
                    f"S083-0{i}", "END", f"W{i}", "V001", f"W{i} ({60}min, {40} TSS)"
                )
                for i in range(1, 6)
            ]
        )

        planner = _make_mock_planner()
        planner.generate_planning_prompt.return_value = "fake prompt"
        mock_planner_cls.return_value = planner
        mock_call_ai.return_value = partial_response

        mock_file = MagicMock()
        planner.planning_dir.__truediv__.return_value = mock_file
        mock_file.__str__ = MagicMock(return_value="/tmp/S083_workouts.txt")

        result = _run_async(
            handle_weekly_planner(
                {
                    "week_id": "S083",
                    "start_date": "2026-03-16",
                    "provider": "mcp_direct",
                }
            )
        )

        import json

        data = json.loads(result[0].text)
        assert data["status"] == "plan_generated"
        assert data["sessions_count"] == 5
        assert "warnings" in data
        assert "Only 5/7" in data["warnings"][0]

    @patch("magma_cycling._mcp.handlers.planning._call_ai_provider")
    @patch("magma_cycling.weekly_planner.WeeklyPlanner")
    def test_mcp_direct_saves_workouts_file(self, mock_planner_cls, mock_call_ai, fake_ai_response):
        """Verify workouts file is written."""
        from magma_cycling._mcp.handlers.planning import handle_weekly_planner

        planner = _make_mock_planner()
        planner.generate_planning_prompt.return_value = "fake prompt"
        mock_planner_cls.return_value = planner
        mock_call_ai.return_value = fake_ai_response

        mock_file = MagicMock()
        planner.planning_dir.__truediv__.return_value = mock_file
        mock_file.__str__ = MagicMock(return_value="/tmp/S083_workouts.txt")

        _run_async(
            handle_weekly_planner(
                {
                    "week_id": "S083",
                    "start_date": "2026-03-16",
                    "provider": "mcp_direct",
                }
            )
        )

        # Verify file was written with raw AI response
        mock_file.write_text.assert_called_once_with(fake_ai_response, encoding="utf-8")

    @patch("magma_cycling._mcp.handlers.planning._call_ai_provider")
    @patch("magma_cycling.weekly_planner.WeeklyPlanner")
    def test_mcp_direct_saves_planning_json(self, mock_planner_cls, mock_call_ai, fake_ai_response):
        """Verify save_planning_json is called with parsed workouts."""
        from magma_cycling._mcp.handlers.planning import handle_weekly_planner

        planner = _make_mock_planner()
        planner.generate_planning_prompt.return_value = "fake prompt"
        mock_planner_cls.return_value = planner
        mock_call_ai.return_value = fake_ai_response

        mock_file = MagicMock()
        planner.planning_dir.__truediv__.return_value = mock_file
        mock_file.__str__ = MagicMock(return_value="/tmp/S083_workouts.txt")

        _run_async(
            handle_weekly_planner(
                {
                    "week_id": "S083",
                    "start_date": "2026-03-16",
                    "provider": "mcp_direct",
                }
            )
        )

        planner.save_planning_json.assert_called_once()
        workouts_arg = planner.save_planning_json.call_args[0][0]
        assert len(workouts_arg) == 7
        assert workouts_arg[0]["session_id"] == "S083-01"
        assert workouts_arg[0]["status"] == "planned"


# ---------------------------------------------------------------------------
# Tests handle_weekly_planner with prompt_only
# ---------------------------------------------------------------------------


class TestHandleWeeklyPlannerPromptOnly:
    """Tests for handle_weekly_planner with provider=prompt_only."""

    @patch("magma_cycling.weekly_planner.WeeklyPlanner")
    def test_prompt_only_returns_full_prompt(self, mock_planner_cls):
        """prompt_only returns full prompt without AI call."""
        from magma_cycling._mcp.handlers.planning import handle_weekly_planner

        planner = _make_mock_planner()
        planner.generate_planning_prompt.return_value = "Full planning prompt content"
        mock_planner_cls.return_value = planner

        result = _run_async(
            handle_weekly_planner(
                {
                    "week_id": "S083",
                    "start_date": "2026-03-16",
                    "provider": "prompt_only",
                }
            )
        )

        import json

        data = json.loads(result[0].text)
        assert data["status"] == "prompt_ready"
        assert data["prompt"] == "Full planning prompt content"
        assert data["provider"] == "prompt_only"
        assert "next_steps" in data
        assert any("modify-session-details" in step for step in data["next_steps"])

    @patch("magma_cycling._mcp.handlers.planning._call_ai_provider")
    @patch("magma_cycling.weekly_planner.WeeklyPlanner")
    def test_prompt_only_does_not_call_ai(self, mock_planner_cls, mock_call_ai):
        """prompt_only must NOT trigger any AI API call."""
        from magma_cycling._mcp.handlers.planning import handle_weekly_planner

        planner = _make_mock_planner()
        planner.generate_planning_prompt.return_value = "prompt"
        mock_planner_cls.return_value = planner

        _run_async(
            handle_weekly_planner(
                {
                    "week_id": "S083",
                    "start_date": "2026-03-16",
                    "provider": "prompt_only",
                }
            )
        )

        mock_call_ai.assert_not_called()
