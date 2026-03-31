"""Tests for rest day NOTE sync in _mcp/handlers/remote_sync.py."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling._mcp.handlers.remote_sync import handle_sync_week_to_calendar

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOCK_PROVIDER_INFO = {"provider": "intervals_icu", "athlete_id": "iXXXXXX", "status": "ready"}


def _make_session(
    session_id="S099-07",
    name="ReposComplet",
    session_type="REC",
    tss_planned=0,
    duration_min=0,
    session_date=date(2026, 4, 5),
    description="Repos complet",
    status="planned",
    intervals_id=None,
    version="V001",
):
    """Create a mock PlannedSession."""
    s = MagicMock()
    s.session_id = session_id
    s.name = name
    s.session_type = session_type
    s.tss_planned = tss_planned
    s.duration_min = duration_min
    s.session_date = session_date
    s.description = description
    s.status = status
    s.intervals_id = intervals_id
    s.version = version
    return s


def _make_plan(sessions, start_date=date(2026, 3, 30), end_date=date(2026, 4, 5)):
    """Create a mock WeeklyPlan."""
    plan = MagicMock()
    plan.start_date = start_date
    plan.end_date = end_date
    plan.planned_sessions = sessions
    return plan


@contextmanager
def _patch_sync(plan, client, workout_descriptions=None):
    """Patch planning_tower, intervals_client, and workout descriptions."""
    with (
        patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
        patch("magma_cycling.config.create_intervals_client") as mock_factory,
        patch(
            "magma_cycling._mcp.handlers.remote_sync.load_workout_descriptions",
            return_value=workout_descriptions or {},
        ),
    ):
        mock_tower.read_week.return_value = plan
        mock_factory.return_value = client
        yield mock_tower


def _make_client(create_return=None):
    """Create a mock IntervalsClient."""
    client = MagicMock()
    client.get_events.return_value = []
    client.get_provider_info.return_value = MOCK_PROVIDER_INFO
    client.create_event.return_value = create_return or {"id": 777}
    return client


def _extract(response):
    """Extract JSON from MCP response."""
    return json.loads(response[0].text)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRestDayCreatesNote:
    """Rest day sessions (REC, TSS=0, duration=0) → NOTE event."""

    @pytest.mark.asyncio
    async def test_rest_day_creates_note(self):
        """A rest day session should produce category=NOTE without type=VirtualRide."""
        session = _make_session()
        plan = _make_plan([session])
        client = _make_client()

        with _patch_sync(plan, client):
            result = _extract(await handle_sync_week_to_calendar({"week_id": "S099"}))

        assert result["summary"]["to_create"] == 1
        # Verify the event_data passed to create_event
        call_args = client.create_event.call_args[0][0]
        assert call_args["category"] == "NOTE"
        assert "type" not in call_args
        assert call_args["start_date_local"] == "2026-04-05T06:00:00"

    @pytest.mark.asyncio
    async def test_rest_day_writeback_intervals_id(self):
        """The intervals_id from the created NOTE should be written back to local planning."""
        session = _make_session()
        plan = _make_plan([session])
        client = _make_client(create_return={"id": 888})

        with _patch_sync(plan, client) as mock_tower:
            # Setup modify_week context manager
            modify_plan = MagicMock()
            modify_plan.planned_sessions = [_make_session(intervals_id=None)]

            @contextmanager
            def _modify_cm(*args, **kwargs):
                yield modify_plan

            mock_tower.modify_week.side_effect = _modify_cm

            result = _extract(await handle_sync_week_to_calendar({"week_id": "S099"}))

        assert result["summary"]["created"] == 1
        # Verify modify_week was called to write back the id
        mock_tower.modify_week.assert_called_once()
        assert modify_plan.planned_sessions[0].intervals_id == 888

    @pytest.mark.asyncio
    async def test_active_recovery_creates_workout(self):
        """A REC session with TSS>0 and duration>0 should remain a WORKOUT."""
        session = _make_session(
            session_id="S099-01",
            name="RecoveryActive",
            tss_planned=30,
            duration_min=45,
            description="- 45m 55% 85rpm",
        )
        plan = _make_plan([session])
        client = _make_client()

        with _patch_sync(plan, client):
            result = _extract(await handle_sync_week_to_calendar({"week_id": "S099"}))

        assert result["summary"]["to_create"] == 1
        call_args = client.create_event.call_args[0][0]
        assert call_args["category"] == "WORKOUT"
        assert call_args["type"] == "VirtualRide"

    @pytest.mark.asyncio
    async def test_rest_day_skips_validation(self):
        """Rest day should not trigger IntervalsFormatValidator."""
        session = _make_session()
        plan = _make_plan([session])
        client = _make_client()

        with (
            _patch_sync(plan, client),
            patch(
                "magma_cycling.intervals_format_validator.IntervalsFormatValidator"
            ) as mock_validator_cls,
        ):
            result = _extract(await handle_sync_week_to_calendar({"week_id": "S099"}))

        # Validator should never be instantiated for rest days
        mock_validator_cls.assert_not_called()
        assert result["summary"]["errors"] == 0
