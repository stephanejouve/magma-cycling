"""Tests for duration recalculation from workout blocks."""

import json
from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling._mcp.handlers.planning import _parse_ai_workouts


class TestParseAiWorkoutsRecalculatesDuration:
    """Test that _parse_ai_workouts recalculates duration from blocks."""

    def test_blocks_override_header_duration(self):
        """Header says 90min but blocks total 75min → duration_min == 75."""
        raw_text = """\
=== WORKOUT S087-03-SST-SweetSpotProgressif-V001 ===
SweetSpot Progressif (90min, 72 TSS)

Warmup
- 10m ramp 50-65% 85rpm
- 5m 65% 90rpm

Main set
- 40m 88-92% 90rpm
- 5m 62% 85rpm

Cooldown
- 10m ramp 65-50% 85rpm
- 5m 50% 80rpm
=== FIN WORKOUT ==="""

        start_date = date(2026, 3, 30)
        workouts = _parse_ai_workouts(raw_text, start_date)

        assert len(workouts) == 1
        assert workouts[0]["duration_min"] == 75  # blocks: 10+5+40+5+10+5
        assert workouts[0]["tss_planned"] == 72  # TSS still from header


class TestModifySessionAutoCalculatesDuration:
    """Test that modify-session-details auto-calculates duration from blocks."""

    @pytest.mark.asyncio
    async def test_auto_calculates_duration_from_description(self):
        """Description with structured blocks → auto-calculated duration."""
        from magma_cycling._mcp.handlers.planning import handle_modify_session_details
        from magma_cycling.planning.models import Session, WeeklyPlan

        # Build a mock plan with one session
        session = Session(
            session_id="S087-03",
            date=date(2026, 4, 2),
            name="SweetSpotProgressif",
            type="SST",
            version="V001",
            tss_planned=72,
            duration_min=90,
            description="Old description",
            status="planned",
        )
        mock_plan = WeeklyPlan(
            week_id="S087",
            start_date=date(2026, 3, 30),
            end_date=date(2026, 4, 5),
            tss_target=350,
            planned_sessions=[session],
            created_at=datetime.now(UTC),
            last_updated=datetime.now(UTC),
            version=1,
            athlete_id="i000000",
        )

        new_description = """\
SweetSpot Progressif (90min, 72 TSS)

Warmup
- 10m ramp 50-65% 85rpm
- 5m 65% 90rpm

Main set
- 40m 88-92% 90rpm
- 5m 62% 85rpm

Cooldown
- 10m ramp 65-50% 85rpm
- 5m 50% 80rpm"""

        # Mock the context manager from planning_tower.modify_week
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_plan)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.workout_parser.update_workouts_file"),
        ):
            mock_tower.modify_week.return_value = mock_cm

            result = await handle_modify_session_details(
                {
                    "week_id": "S087",
                    "session_id": "S087-03",
                    "description": new_description,
                    # No duration_min provided → should auto-calculate
                }
            )

        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert "duration=75min (auto)" in data["modifications"]

        # Verify the session was actually modified
        modified = mock_plan.planned_sessions[0]
        assert modified.description == new_description
        assert modified.duration_min == 75
