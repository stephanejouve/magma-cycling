"""
Additional MCP handler tests — push mcp_server.py from 50% to 60%.

Focuses on: handle_update_session, handle_sync_week_to_calendar,
handle_get_metrics, handle_get_sleep, handle_get_body_composition,
handle_get_readiness, handle_apply_workout_intervals,
handle_compare_activity_intervals.
"""

import json
from datetime import date, datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

pytest_plugins = ("pytest_asyncio",)

TOWER_PATCH = "magma_cycling.planning.control_tower.planning_tower"
INTERVALS_PATCH = "magma_cycling.config.create_intervals_client"


# =======================
# Shared Fixtures
# =======================


@pytest.fixture
def mock_session():
    s = Mock()
    s.session_id = "S081-03"
    s.session_date = date(2026, 2, 19)
    s.name = "TempoCourt"
    s.session_type = "INT"
    s.version = "V001"
    s.tss_planned = 65
    s.duration_min = 60
    s.description = "Warmup\n- 10m ramp 50-75% 85rpm\n\nMain set 3x\n- 10m 88% 90rpm\n- 3m 60% 85rpm\n\nCooldown\n- 10m ramp 70-50% 85rpm"
    s.status = "pending"
    s.intervals_id = None
    s.skip_reason = None
    return s


@pytest.fixture
def mock_plan(mock_session):
    p = Mock()
    p.week_id = "S081"
    p.start_date = date(2026, 2, 17)
    p.end_date = date(2026, 2, 23)
    p.planned_sessions = [mock_session]
    return p


@pytest.fixture
def mock_tower(mock_plan):
    return make_tower(mock_plan)


def make_tower(plan):
    tower = Mock()
    tower.read_week.return_value = plan
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=plan)
    ctx.__exit__ = Mock(return_value=False)
    tower.modify_week.return_value = ctx
    return tower


# =======================
# TestHandleUpdateSession
# =======================


class TestHandleUpdateSession:
    @pytest.mark.asyncio
    async def test_success_no_sync(self, mock_plan, mock_session):
        """Success path without sync to Intervals.icu."""
        from magma_cycling.mcp_server import handle_update_session

        tower = make_tower(mock_plan)
        args = {
            "week_id": "S081",
            "session_id": "S081-03",
            "status": "skipped",
            "reason": "Sick",
        }
        with patch(TOWER_PATCH, tower):
            result = await handle_update_session(args)
        data = json.loads(result[0].text)
        assert data["week_id"] == "S081"
        assert data["session_id"] == "S081-03"
        assert data["status"] == "skipped"
        assert data["synced"] is False

    @pytest.mark.asyncio
    async def test_session_not_found_raises_value_error(self, mock_tower):
        """Session not found raises ValueError (propagates to call_tool dispatcher)."""
        from magma_cycling.mcp_server import handle_update_session

        args = {
            "week_id": "S081",
            "session_id": "S081-99",
            "status": "cancelled",
        }
        with patch(TOWER_PATCH, mock_tower):
            with pytest.raises(ValueError, match="S081-99"):
                await handle_update_session(args)

    @pytest.mark.asyncio
    async def test_file_not_found_raises(self, mock_tower):
        """FileNotFoundError propagates from handle_update_session (no try/except)."""
        from magma_cycling.mcp_server import handle_update_session

        mock_tower.modify_week.side_effect = FileNotFoundError("not found")
        args = {"week_id": "S099", "session_id": "S099-01", "status": "skipped"}
        with patch(TOWER_PATCH, mock_tower):
            with pytest.raises(FileNotFoundError):
                await handle_update_session(args)

    @pytest.mark.asyncio
    async def test_with_reason_and_skipped_status(self, mock_plan, mock_session):
        """Test with skip reason for skipped status."""
        from magma_cycling.mcp_server import handle_update_session

        tower = make_tower(mock_plan)
        args = {
            "week_id": "S081",
            "session_id": "S081-03",
            "status": "cancelled",
            "reason": "Weather was bad",
        }
        with patch(TOWER_PATCH, tower):
            result = await handle_update_session(args)
        data = json.loads(result[0].text)
        assert data["status"] == "cancelled"
        assert data["reason"] == "Weather was bad"

    @pytest.mark.asyncio
    async def test_sync_with_existing_intervals_id(self, mock_plan, mock_session):
        """Test sync to intervals.icu when session has intervals_id."""
        from magma_cycling.mcp_server import handle_update_session

        mock_session.intervals_id = 12345
        mock_session.status = "pending"
        tower = make_tower(mock_plan)
        mock_client = Mock()
        mock_client.update_event.return_value = {"id": 12345}

        args = {
            "week_id": "S081",
            "session_id": "S081-03",
            "status": "completed",
            "sync": True,
        }
        with patch(TOWER_PATCH, tower):
            with patch(INTERVALS_PATCH, return_value=mock_client):
                result = await handle_update_session(args)
        data = json.loads(result[0].text)
        assert data["synced"] is True


# =======================
# TestHandleSyncWeekToIntervals
# =======================


LOAD_WORKOUTS_PATCH = "magma_cycling._mcp.handlers.remote_sync.load_workout_descriptions"


class TestHandleSyncWeekToIntervals:
    @pytest.mark.asyncio
    async def test_dry_run_no_api_calls(self, mock_plan, mock_session):
        """dry_run=True: computes plan but skips API create/update calls."""
        from magma_cycling.mcp_server import handle_sync_week_to_calendar

        mock_session.intervals_id = None
        mock_plan.planned_sessions = [mock_session]
        tower = make_tower(mock_plan)
        mock_client = Mock()
        mock_client.get_events.return_value = []

        args = {"week_id": "S081", "dry_run": True}
        with patch(TOWER_PATCH, tower):
            with patch(INTERVALS_PATCH, return_value=mock_client):
                with patch(LOAD_WORKOUTS_PATCH, return_value={}):
                    result = await handle_sync_week_to_calendar(args)
        data = json.loads(result[0].text)
        assert data["dry_run"] is True
        assert data["summary"]["to_create"] == 1
        assert data["summary"]["created"] == 0  # dry_run: no actual creation
        mock_client.create_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_completed_session_skipped(self, mock_plan, mock_session):
        """Completed sessions are protected — skipped from sync."""
        from magma_cycling.mcp_server import handle_sync_week_to_calendar

        mock_session.status = "completed"
        mock_session.intervals_id = 12345
        mock_plan.planned_sessions = [mock_session]
        tower = make_tower(mock_plan)
        mock_client = Mock()
        mock_client.get_events.return_value = []

        args = {"week_id": "S081", "dry_run": True}
        with patch(TOWER_PATCH, tower):
            with patch(INTERVALS_PATCH, return_value=mock_client):
                with patch(LOAD_WORKOUTS_PATCH, return_value={}):
                    result = await handle_sync_week_to_calendar(args)
        data = json.loads(result[0].text)
        assert data["summary"]["skipped_protected"] == 1
        assert data["summary"]["to_create"] == 0

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self, mock_tower):
        """FileNotFoundError from planning_tower returns error."""
        from magma_cycling.mcp_server import handle_sync_week_to_calendar

        mock_tower.read_week.side_effect = FileNotFoundError("not found")
        mock_client = Mock()
        args = {"week_id": "S099"}
        with patch(TOWER_PATCH, mock_tower):
            with patch(INTERVALS_PATCH, return_value=mock_client):
                result = await handle_sync_week_to_calendar(args)
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_intervals_id_conflict_with_force_update(self, mock_plan, mock_session):
        """Session with intervals_id that exists remotely — force_update flag."""
        from magma_cycling.mcp_server import handle_sync_week_to_calendar

        mock_session.intervals_id = "evt123"
        mock_session.status = "pending"
        mock_session.name = "TempoCourt"
        valid_desc = "Warmup\n- 10m ramp 50-75% 85rpm\n\nMain set 3x\n- 10m 88% 90rpm\n- 3m 60% 85rpm\n\nCooldown\n- 10m ramp 70-50% 85rpm"
        mock_session.description = valid_desc
        mock_plan.planned_sessions = [mock_session]
        tower = make_tower(mock_plan)
        mock_client = Mock()
        # Remote event with full intervals_name, matching start_date and description (no conflict)
        mock_client.get_events.return_value = [
            {
                "id": "evt123",
                "category": "WORKOUT",
                "name": "S081-03-INT-TempoCourt-V001",
                "description": valid_desc,
                "start_date_local": "2026-02-19T17:00:00",
            },
        ]
        mock_client.update_event.return_value = True

        args = {"week_id": "S081", "dry_run": True, "force_update": False}
        with patch(TOWER_PATCH, tower):
            with patch(INTERVALS_PATCH, return_value=mock_client):
                with patch(LOAD_WORKOUTS_PATCH, return_value={}):
                    result = await handle_sync_week_to_calendar(args)
        data = json.loads(result[0].text)
        # No changes needed (same name and date)
        assert data["summary"]["to_update"] == 0

    @pytest.mark.asyncio
    async def test_remote_conflict_detected(self, mock_plan, mock_session):
        """Session with intervals_id but remote was manually modified → warning."""
        from magma_cycling.mcp_server import handle_sync_week_to_calendar

        mock_session.intervals_id = "evt123"
        mock_session.status = "pending"
        mock_session.name = "TempoCourt"
        mock_session.description = "Warmup\n- 10m ramp 50-75% 85rpm\n\nMain set 3x\n- 10m 88% 90rpm\n- 3m 60% 85rpm\n\nCooldown\n- 10m ramp 70-50% 85rpm"
        mock_plan.planned_sessions = [mock_session]
        tower = make_tower(mock_plan)
        mock_client = Mock()
        # Remote event has different name (manually modified in Intervals.icu)
        mock_client.get_events.return_value = [
            {
                "id": "evt123",
                "category": "WORKOUT",
                "name": "ManuallyRenamedWorkout",
                "start_date_local": "2026-02-19T17:00:00",
            },
        ]

        args = {"week_id": "S081", "dry_run": True, "force_update": False}
        with patch(TOWER_PATCH, tower):
            with patch(INTERVALS_PATCH, return_value=mock_client):
                with patch(LOAD_WORKOUTS_PATCH, return_value={}):
                    result = await handle_sync_week_to_calendar(args)
        data = json.loads(result[0].text)
        assert data["summary"]["warnings"] == 1
        assert data["status"] == "success_with_warnings"

    @pytest.mark.asyncio
    async def test_skipped_session_not_synced(self, mock_plan, mock_session):
        """Skipped sessions are protected — not synced to Intervals.icu."""
        from magma_cycling.mcp_server import handle_sync_week_to_calendar

        mock_session.status = "skipped"
        mock_session.intervals_id = None
        mock_plan.planned_sessions = [mock_session]
        tower = make_tower(mock_plan)
        mock_client = Mock()
        mock_client.get_events.return_value = []

        args = {"week_id": "S081", "dry_run": True}
        with patch(TOWER_PATCH, tower):
            with patch(INTERVALS_PATCH, return_value=mock_client):
                with patch(LOAD_WORKOUTS_PATCH, return_value={}):
                    result = await handle_sync_week_to_calendar(args)
        data = json.loads(result[0].text)
        assert data["summary"]["skipped_protected"] == 1
        assert data["summary"]["to_create"] == 0
        assert data["details"]["skipped_protected"][0]["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_rest_day_session_not_synced(self, mock_plan, mock_session):
        """Rest day sessions are protected — not synced to Intervals.icu."""
        from magma_cycling.mcp_server import handle_sync_week_to_calendar

        mock_session.status = "rest_day"
        mock_session.intervals_id = None
        mock_plan.planned_sessions = [mock_session]
        tower = make_tower(mock_plan)
        mock_client = Mock()
        mock_client.get_events.return_value = []

        args = {"week_id": "S081", "dry_run": True}
        with patch(TOWER_PATCH, tower):
            with patch(INTERVALS_PATCH, return_value=mock_client):
                with patch(LOAD_WORKOUTS_PATCH, return_value={}):
                    result = await handle_sync_week_to_calendar(args)
        data = json.loads(result[0].text)
        assert data["summary"]["skipped_protected"] == 1
        assert data["summary"]["to_create"] == 0
        assert data["details"]["skipped_protected"][0]["status"] == "rest_day"

    @pytest.mark.asyncio
    async def test_name_comparison_uses_full_intervals_name(self, mock_plan, mock_session):
        """Bug 2: Comparison uses full intervals_name, not short session.name."""
        from magma_cycling.mcp_server import handle_sync_week_to_calendar

        mock_session.intervals_id = "evt123"
        mock_session.status = "pending"
        mock_session.name = "TempoCourt"
        mock_session.session_type = "INT"
        mock_session.version = "V001"
        mock_plan.planned_sessions = [mock_session]
        tower = make_tower(mock_plan)
        mock_client = Mock()
        # Remote has short name (old bug would match wrongly)
        mock_client.get_events.return_value = [
            {
                "id": "evt123",
                "category": "WORKOUT",
                "name": "TempoCourt",  # Short name, NOT full intervals_name
                "start_date_local": "2026-02-19T17:00:00",
            },
        ]

        args = {"week_id": "S081", "dry_run": True, "force_update": False}
        with patch(TOWER_PATCH, tower):
            with patch(INTERVALS_PATCH, return_value=mock_client):
                with patch(LOAD_WORKOUTS_PATCH, return_value={}):
                    result = await handle_sync_week_to_calendar(args)
        data = json.loads(result[0].text)
        # Short name != full intervals_name → conflict detected
        assert data["summary"]["warnings"] == 1

    @pytest.mark.asyncio
    async def test_update_payload_includes_description(self, mock_plan, mock_session):
        """Update payload sends name + description + start_date_local."""
        from magma_cycling.mcp_server import handle_sync_week_to_calendar

        mock_session.intervals_id = "evt123"
        mock_session.status = "pending"
        mock_session.name = "TempoCourt"
        mock_session.session_type = "INT"
        mock_session.version = "V001"
        valid_desc = "Warmup\n- 10m ramp 50-75% 85rpm\n\nMain set 3x\n- 10m 88% 90rpm\n- 3m 60% 85rpm\n\nCooldown\n- 10m ramp 70-50% 85rpm"
        mock_session.description = valid_desc
        mock_plan.planned_sessions = [mock_session]
        tower = make_tower(mock_plan)
        mock_client = Mock()
        # Remote has different date (triggers update)
        mock_client.get_events.return_value = [
            {
                "id": "evt123",
                "category": "WORKOUT",
                "name": "S081-03-INT-TempoCourt-V001",
                "start_date_local": "2026-02-20T17:00:00",  # Wrong date
            },
        ]
        mock_client.update_event.return_value = True

        args = {"week_id": "S081", "dry_run": False, "force_update": True}
        with patch(TOWER_PATCH, tower):
            with patch(INTERVALS_PATCH, return_value=mock_client):
                with patch(LOAD_WORKOUTS_PATCH, return_value={}):
                    result = await handle_sync_week_to_calendar(args)
        data = json.loads(result[0].text)
        assert data["summary"]["updated"] == 1
        # Verify the update_event was called with description
        update_call = mock_client.update_event.call_args
        event_data = update_call[0][1]
        assert "description" in event_data
        assert event_data["description"] == valid_desc
        assert "name" in event_data
        assert "start_date_local" in event_data

    @pytest.mark.asyncio
    async def test_session_ids_filter(self, mock_plan, mock_session):
        """Bug 4: session_ids parameter filters which sessions are synced."""
        from magma_cycling.mcp_server import handle_sync_week_to_calendar

        # Add a second session
        session2 = Mock()
        session2.session_id = "S081-06"
        session2.session_date = date(2026, 2, 22)
        session2.name = "EnduranceLongue"
        session2.session_type = "END"
        session2.version = "V001"
        session2.description = "Warmup\n- 15m ramp 50-70% 85rpm\n\nMain set\n- 60m 68% 85rpm\n\nCooldown\n- 15m ramp 65-50% 85rpm"
        session2.duration_min = 90
        session2.tss_planned = 55
        session2.status = "pending"
        session2.intervals_id = None
        session2.skip_reason = None
        mock_session.intervals_id = None
        mock_plan.planned_sessions = [mock_session, session2]
        tower = make_tower(mock_plan)
        mock_client = Mock()
        mock_client.get_events.return_value = []

        # Only sync session2
        args = {"week_id": "S081", "dry_run": True, "session_ids": ["S081-06"]}
        with patch(TOWER_PATCH, tower):
            with patch(INTERVALS_PATCH, return_value=mock_client):
                with patch(LOAD_WORKOUTS_PATCH, return_value={}):
                    result = await handle_sync_week_to_calendar(args)
        data = json.loads(result[0].text)
        assert data["summary"]["to_create"] == 1
        assert data["details"]["to_create"][0]["session_id"] == "S081-06"


# =======================
# TestHandleGetMetrics
# =======================


# =======================
# TestSyncValidationGate
# =======================


class TestSyncValidationGate:
    """Validation gate rejects invalid workout descriptions before sync."""

    @pytest.mark.asyncio
    async def test_sync_rejects_invalid_workout(self, mock_plan, mock_session):
        """Session with '5min' duration → validation error, no API create."""
        from magma_cycling.mcp_server import handle_sync_week_to_calendar

        mock_session.intervals_id = None
        mock_session.status = "pending"
        mock_plan.planned_sessions = [mock_session]
        tower = make_tower(mock_plan)
        mock_client = Mock()
        mock_client.get_events.return_value = []

        # Workout with invalid duration (5min instead of 5m)
        invalid_workout = "Warmup\n- 5min ramp 50-65%\n\nMain set\n- 10m 90%"
        workout_descriptions = {
            f"{mock_session.session_id}-{mock_session.session_type}-{mock_session.name}-{mock_session.version}": invalid_workout,
        }

        args = {"week_id": "S081", "dry_run": False}
        with patch(TOWER_PATCH, tower):
            with patch(INTERVALS_PATCH, return_value=mock_client):
                with patch(LOAD_WORKOUTS_PATCH, return_value=workout_descriptions):
                    result = await handle_sync_week_to_calendar(args)
        data = json.loads(result[0].text)
        # Session should be rejected — no creation
        assert data["summary"]["to_create"] == 0
        assert data["summary"]["created"] == 0
        assert len(data["errors"]) > 0
        assert "validation failed" in data["errors"][0].lower()
        mock_client.create_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_accepts_valid_workout(self, mock_plan, mock_session):
        """Session with valid '5m' duration → create API called normally."""
        from magma_cycling.mcp_server import handle_sync_week_to_calendar

        mock_session.intervals_id = None
        mock_session.status = "pending"
        mock_plan.planned_sessions = [mock_session]
        tower = make_tower(mock_plan)
        mock_client = Mock()
        mock_client.get_events.return_value = []
        mock_client.create_event.return_value = {"id": "evt999"}

        # Valid workout description
        valid_workout = "Warmup\n- 5m ramp 50-65%\n\nMain set\n- 10m 90%"
        workout_descriptions = {
            f"{mock_session.session_id}-{mock_session.session_type}-{mock_session.name}-{mock_session.version}": valid_workout,
        }

        args = {"week_id": "S081", "dry_run": False}
        with patch(TOWER_PATCH, tower):
            with patch(INTERVALS_PATCH, return_value=mock_client):
                with patch(LOAD_WORKOUTS_PATCH, return_value=workout_descriptions):
                    result = await handle_sync_week_to_calendar(args)
        data = json.loads(result[0].text)
        assert data["summary"]["to_create"] == 1
        assert data["summary"]["created"] == 1
        mock_client.create_event.assert_called_once()


# =======================
# TestHandleGetMetrics
# =======================


class TestHandleGetMetrics:
    @pytest.mark.asyncio
    async def test_success_returns_wellness_data(self):
        from magma_cycling.mcp_server import handle_get_metrics

        mock_config = Mock()
        mock_config.athlete_id = "iXXXXXX"
        mock_config.api_key = "apikey123"
        mock_client = Mock()
        mock_client.get_wellness.return_value = [
            {
                "id": "2026-02-24",
                "ctl": 65,
                "atl": 70,
                "tsb": -5,
                "rampRate": 1.2,
                "ctlLoad": 65,
                "atlLoad": 70,
            },
        ]

        with patch("magma_cycling.config.get_intervals_config", return_value=mock_config):
            with patch(
                "magma_cycling.api.intervals_client.IntervalsClient",
                return_value=mock_client,
            ):
                result = await handle_get_metrics({})
        data = json.loads(result[0].text)
        assert data["ctl"] == 65
        assert data["atl"] == 70

    @pytest.mark.asyncio
    async def test_no_wellness_data_returns_error(self):
        from magma_cycling.mcp_server import handle_get_metrics

        mock_config = Mock()
        mock_config.athlete_id = "iXXXXXX"
        mock_config.api_key = "apikey123"
        mock_client = Mock()
        mock_client.get_wellness.return_value = []

        with patch("magma_cycling.config.get_intervals_config", return_value=mock_config):
            with patch(
                "magma_cycling.api.intervals_client.IntervalsClient",
                return_value=mock_client,
            ):
                result = await handle_get_metrics({})
        data = json.loads(result[0].text)
        assert "error" in data


# =======================
# TestHandleWithingsGetSleep
# =======================


class TestHandleWithingsGetSleep:
    @pytest.mark.asyncio
    async def test_last_night_only_with_data(self):
        from magma_cycling.mcp_server import handle_get_sleep
        from magma_cycling.models.withings_models import SleepData

        mock_provider = Mock()
        mock_provider.get_sleep_summary.return_value = SleepData(
            date=date(2026, 2, 22),
            start_datetime=datetime(2026, 2, 21, 22, 30),
            end_datetime=datetime(2026, 2, 22, 6, 0),
            total_sleep_hours=7.5,
            sleep_score=85,
            wakeup_count=1,
        )
        with patch("magma_cycling.health.create_health_provider", return_value=mock_provider):
            result = await handle_get_sleep({"last_night_only": True})
        data = json.loads(result[0].text)
        assert "last_night_sleep" in data
        assert data["last_night_sleep"]["total_sleep_hours"] == 7.5

    @pytest.mark.asyncio
    async def test_last_night_only_no_data(self):
        from magma_cycling.mcp_server import handle_get_sleep

        mock_provider = Mock()
        mock_provider.get_sleep_summary.return_value = None
        with patch("magma_cycling.health.create_health_provider", return_value=mock_provider):
            result = await handle_get_sleep({"last_night_only": True})
        data = json.loads(result[0].text)
        assert data["last_night_sleep"] is None
        assert "message" in data

    @pytest.mark.asyncio
    async def test_date_range_returns_sessions(self):
        from magma_cycling.mcp_server import handle_get_sleep
        from magma_cycling.models.withings_models import SleepData

        mock_provider = Mock()
        mock_provider.get_sleep_range.return_value = [
            SleepData(
                date=date(2026, 2, 17),
                start_datetime=datetime(2026, 2, 16, 23, 0),
                end_datetime=datetime(2026, 2, 17, 6, 0),
                total_sleep_hours=7.0,
                wakeup_count=0,
            ),
        ]
        with patch("magma_cycling.health.create_health_provider", return_value=mock_provider):
            result = await handle_get_sleep(
                {
                    "start_date": "2026-02-17",
                    "end_date": "2026-02-23",
                }
            )
        data = json.loads(result[0].text)
        assert data["count"] == 1
        assert len(data["sleep_sessions"]) == 1

    @pytest.mark.asyncio
    async def test_default_7_days_range(self):
        from magma_cycling.mcp_server import handle_get_sleep

        mock_provider = Mock()
        mock_provider.get_sleep_range.return_value = []
        with patch("magma_cycling.health.create_health_provider", return_value=mock_provider):
            result = await handle_get_sleep({})
        data = json.loads(result[0].text)
        assert "start_date" in data
        assert data["count"] == 0


# =======================
# TestHandleWithingsGetWeight
# =======================


class TestHandleWithingsGetWeight:
    @pytest.mark.asyncio
    async def test_latest_only_with_data(self):
        from magma_cycling.mcp_server import handle_get_body_composition
        from magma_cycling.models.withings_models import WeightMeasurement

        mock_provider = Mock()
        mock_provider.get_body_composition.return_value = WeightMeasurement(
            date=date(2026, 2, 22),
            datetime=datetime(2026, 2, 22, 8, 0),
            weight_kg=72.3,
        )
        with patch("magma_cycling.health.create_health_provider", return_value=mock_provider):
            result = await handle_get_body_composition({"latest_only": True})
        data = json.loads(result[0].text)
        assert data["latest_weight"]["weight_kg"] == 72.3

    @pytest.mark.asyncio
    async def test_latest_only_no_data(self):
        from magma_cycling.mcp_server import handle_get_body_composition

        mock_provider = Mock()
        mock_provider.get_body_composition.return_value = None
        with patch("magma_cycling.health.create_health_provider", return_value=mock_provider):
            result = await handle_get_body_composition({"latest_only": True})
        data = json.loads(result[0].text)
        assert data["latest_weight"] is None
        assert "message" in data

    @pytest.mark.asyncio
    async def test_date_range_returns_measurements(self):
        from magma_cycling.mcp_server import handle_get_body_composition
        from magma_cycling.models.withings_models import WeightMeasurement

        mock_provider = Mock()
        mock_provider.get_body_composition_range.return_value = [
            WeightMeasurement(
                date=date(2026, 2, 17),
                datetime=datetime(2026, 2, 17, 8, 0),
                weight_kg=72.5,
            ),
        ]
        with patch("magma_cycling.health.create_health_provider", return_value=mock_provider):
            result = await handle_get_body_composition(
                {
                    "start_date": "2026-02-17",
                    "end_date": "2026-02-23",
                }
            )
        data = json.loads(result[0].text)
        assert data["count"] == 1

    @pytest.mark.asyncio
    async def test_default_30_days_range(self):
        from magma_cycling.mcp_server import handle_get_body_composition

        mock_provider = Mock()
        mock_provider.get_body_composition_range.return_value = []
        with patch("magma_cycling.health.create_health_provider", return_value=mock_provider):
            result = await handle_get_body_composition({})
        data = json.loads(result[0].text)
        assert "start_date" in data
        assert data["count"] == 0


# =======================
# TestHandleWithingsGetReadiness
# =======================


class TestHandleWithingsGetReadiness:
    @pytest.mark.asyncio
    async def test_no_sleep_data_returns_no_data_status(self):
        from magma_cycling.mcp_server import handle_get_readiness

        mock_provider = Mock()
        mock_provider.get_readiness.return_value = None
        with patch("magma_cycling.health.create_health_provider", return_value=mock_provider):
            result = await handle_get_readiness({})
        data = json.loads(result[0].text)
        assert data["status"] == "no_data"

    @pytest.mark.asyncio
    async def test_with_sleep_data_evaluates_readiness(self):
        from magma_cycling.mcp_server import handle_get_readiness
        from magma_cycling.models.withings_models import TrainingReadiness

        mock_provider = Mock()
        mock_provider.get_readiness.return_value = TrainingReadiness(
            date=date(2026, 2, 24),
            sleep_hours=8.0,
            sleep_score=90,
            ready_for_intense=True,
            recommended_intensity="all_systems_go",
            weight_kg=72.0,
        )
        with patch("magma_cycling.health.create_health_provider", return_value=mock_provider):
            result = await handle_get_readiness({"date": "2026-02-24"})
        data = json.loads(result[0].text)
        assert data["status"] == "evaluated"
        assert "readiness" in data

    @pytest.mark.asyncio
    async def test_with_date_parameter(self):
        from magma_cycling.mcp_server import handle_get_readiness

        mock_provider = Mock()
        mock_provider.get_readiness.return_value = None
        with patch("magma_cycling.health.create_health_provider", return_value=mock_provider):
            result = await handle_get_readiness({"date": "2026-02-20"})
        data = json.loads(result[0].text)
        assert data["date"] == "2026-02-20"


# =======================
# TestHandleListWeeksException
# =======================


class TestHandleListWeeksException:
    @pytest.mark.asyncio
    async def test_malformed_json_file_is_skipped(self, tmp_path):
        """Malformed JSON in a planning file is silently skipped."""
        from magma_cycling.mcp_server import handle_list_weeks

        # Write bad JSON
        (tmp_path / "week_planning_S081.json").write_text("{bad json}")
        mc = Mock()
        mc.week_planning_dir = tmp_path
        with patch("magma_cycling.config.get_data_config", return_value=mc):
            result = await handle_list_weeks({"limit": 10})
        data = json.loads(result[0].text)
        assert data["total_found"] == 0  # Bad file skipped


# =======================
# TestDailySyncDefaultProvider
# =======================


AI_CONFIG_PATCH = "magma_cycling.daily_sync.get_ai_config"
AI_FACTORY_PATCH = "magma_cycling.daily_sync.AIProviderFactory"
INTERVALS_CLIENT_PATCH = "magma_cycling.daily_sync.create_intervals_client"


class TestDailySyncDefaultProvider:
    def test_respects_default_provider(self, tmp_path):
        """DailySync.__init__ picks default_provider over available[0]."""
        from magma_cycling.daily_sync import DailySync

        mock_ai_config = Mock()
        mock_ai_config.default_provider = "mistral_api"
        mock_ai_config.get_available_providers.return_value = [
            "claude_api",
            "mistral_api",
        ]
        mock_ai_config.get_provider_config.return_value = {"mistral_api_key": "key"}

        mock_analyzer = Mock()
        mock_factory = Mock()
        mock_factory.create.return_value = mock_analyzer

        with (
            patch(AI_CONFIG_PATCH, return_value=mock_ai_config),
            patch(AI_FACTORY_PATCH, mock_factory),
            patch(INTERVALS_CLIENT_PATCH, return_value=Mock()),
        ):
            sync = DailySync(
                tracking_file=tmp_path / "tracking.json",
                reports_dir=tmp_path / "reports",
                enable_ai_analysis=True,
            )

        # Factory must be called with mistral_api (default), NOT claude_api (available[0])
        mock_factory.create.assert_called_once_with("mistral_api", {"mistral_api_key": "key"})
        assert sync.ai_analyzer is mock_analyzer

    def test_falls_back_to_first_available_if_default_not_configured(self, tmp_path):
        """DailySync.__init__ falls back to available[0] when default not in list."""
        from magma_cycling.daily_sync import DailySync

        mock_ai_config = Mock()
        mock_ai_config.default_provider = "openai"  # Not in available list
        mock_ai_config.get_available_providers.return_value = ["claude_api"]
        mock_ai_config.get_provider_config.return_value = {"claude_api_key": "key"}

        mock_factory = Mock()
        mock_factory.create.return_value = Mock()

        with (
            patch(AI_CONFIG_PATCH, return_value=mock_ai_config),
            patch(AI_FACTORY_PATCH, mock_factory),
            patch(INTERVALS_CLIENT_PATCH, return_value=Mock()),
        ):
            DailySync(
                tracking_file=tmp_path / "tracking.json",
                reports_dir=tmp_path / "reports",
                enable_ai_analysis=True,
            )

        # Falls back to claude_api (available[0])
        mock_factory.create.assert_called_once_with("claude_api", {"claude_api_key": "key"})


# =======================
# TestDailySyncMCPAiParam
# =======================


class TestDailySyncMCPAiParam:
    """Test that handle_daily_sync passes ai_analysis param to DailySync."""

    def _make_patches(self, tmp_path):
        """Return common patches for handle_daily_sync tests."""
        from contextlib import nullcontext

        mock_config = Mock()
        mock_config.data_repo_path = tmp_path

        mock_sync = Mock()
        mock_sync.run.return_value = None
        mock_sync.check_activities.return_value = ([], [])
        mock_sync.ai_analyzer = None

        return {
            "sync_cls": patch(
                "magma_cycling.daily_sync.DailySync",
                return_value=mock_sync,
            ),
            "calc_week": patch(
                "magma_cycling.daily_sync.calculate_current_week_info",
                return_value=("S082", date(2026, 2, 23)),
            ),
            "data_config": patch(
                "magma_cycling.config.get_data_config",
                return_value=mock_config,
            ),
            "suppress": patch(
                "magma_cycling._mcp.handlers.planning.suppress_stdout_stderr",
                nullcontext,
            ),
        }

    @pytest.mark.asyncio
    async def test_ai_analysis_enabled_by_default(self, tmp_path):
        """handle_daily_sync passes enable_ai_analysis=True by default."""
        from magma_cycling.mcp_server import handle_daily_sync

        patches = self._make_patches(tmp_path)
        with (
            patches["sync_cls"] as mock_cls,
            patches["calc_week"],
            patches["data_config"],
            patches["suppress"],
        ):
            await handle_daily_sync({"date": "2026-02-24"})

        # DailySync instantiated with enable_ai_analysis=True
        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args
        assert call_kwargs[1]["enable_ai_analysis"] is True

    @pytest.mark.asyncio
    async def test_ai_analysis_disabled_via_param(self, tmp_path):
        """handle_daily_sync passes enable_ai_analysis=False when ai_analysis=false."""
        from magma_cycling.mcp_server import handle_daily_sync

        patches = self._make_patches(tmp_path)
        with (
            patches["sync_cls"] as mock_cls,
            patches["calc_week"],
            patches["data_config"],
            patches["suppress"],
        ):
            result = await handle_daily_sync({"date": "2026-02-24", "ai_analysis": False})

        # DailySync instantiated with enable_ai_analysis=False
        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args
        assert call_kwargs[1]["enable_ai_analysis"] is False
        data = json.loads(result[0].text)
        assert data["ai_analysis"] is False


# =======================
# TestSessionPrescription
# =======================

DAILY_SYNC_TOWER_PATCH = "magma_cycling.workflows.sync.ai_analysis.planning_tower"


class TestSessionPrescription:
    """Test the Prescription → Exécution → Ressenti triptyque."""

    def test_analyze_activity_includes_session_prescription(self, tmp_path):
        """analyze_activity extracts prescription from planning and passes it to generate_prompt."""
        from magma_cycling.daily_sync import DailySync

        # Build a mock plan with a session that has a description
        mock_session = Mock()
        mock_session.session_id = "S082-01"
        mock_session.description = "Tempo 3x10min à 85% FTP — focus cadence haute"

        mock_plan = Mock()
        mock_plan.planned_sessions = [mock_session]

        mock_tower = Mock()
        mock_tower.read_week.return_value = mock_plan

        # Build a DailySync with mocked internals
        mock_ai_config = Mock()
        mock_ai_config.default_provider = "claude_api"
        mock_ai_config.get_available_providers.return_value = ["claude_api"]
        mock_ai_config.get_provider_config.return_value = {"claude_api_key": "k"}

        mock_analyzer = Mock()
        mock_analyzer.analyze_session.return_value = "AI analysis text"
        mock_factory = Mock()
        mock_factory.create.return_value = mock_analyzer

        with (
            patch(AI_CONFIG_PATCH, return_value=mock_ai_config),
            patch(AI_FACTORY_PATCH, mock_factory),
            patch(INTERVALS_CLIENT_PATCH, return_value=Mock()),
        ):
            sync = DailySync(
                tracking_file=tmp_path / "tracking.json",
                reports_dir=tmp_path / "reports",
                enable_ai_analysis=True,
            )

        # Mock all dependencies of analyze_activity
        sync.client = Mock()
        sync.client.get_wellness.return_value = [{"ctl": 50, "atl": 40, "tsb": 10}]
        sync.client.get_planned_workout.return_value = None

        sync.prompt_generator = Mock()
        sync.prompt_generator.generate_prompt.return_value = "fake prompt"
        sync.history_manager = Mock()
        sync.history_manager.get_existing_analysis.return_value = None
        sync.ai_analyzer = mock_analyzer

        activity = {
            "id": "i12345",
            "name": "S082-01-END-EnduranceBase-V001",
            "start_date_local": "2026-02-23T18:00:00",
        }

        with patch(DAILY_SYNC_TOWER_PATCH, mock_tower):
            sync.analyze_activity(activity)

        # Verify generate_prompt was called with session_prescription
        call_kwargs = sync.prompt_generator.generate_prompt.call_args
        assert call_kwargs[1]["session_prescription"] == (
            "Tempo 3x10min à 85% FTP — focus cadence haute"
        )

    def test_generate_prompt_includes_prescription_section(self, tmp_path):
        """generate_prompt includes Prescription Coach section when prescription provided."""
        from magma_cycling.prepare_analysis import PromptGenerator

        gen = PromptGenerator(project_root=tmp_path)
        raw = {
            "id": 99,
            "name": "S082-01-INT-Tempo-V001",
            "type": "Ride",
            "start_date_local": "2026-02-23T10:00:00",
            "moving_time": 3600,
            "icu_training_load": 65,
            "icu_intensity": 75,
            "source": "GARMIN",
        }
        activity_data = gen.format_activity_data(raw)

        prompt = gen.generate_prompt(
            activity_data=activity_data,
            wellness_pre=None,
            wellness_post=None,
            athlete_context=None,
            recent_workouts=None,
            session_prescription="Tempo 3x10min à 85% FTP — focus cadence haute",
        )

        assert "Prescription Coach" in prompt
        assert "Tempo 3x10min à 85% FTP" in prompt
        assert "focus cadence haute" in prompt
        assert "Évaluer si l'exécution répond aux objectifs prescrits" in prompt

    def test_generate_prompt_skips_prescription_when_none(self, tmp_path):
        """generate_prompt omits Prescription Coach section when prescription is None."""
        from magma_cycling.prepare_analysis import PromptGenerator

        gen = PromptGenerator(project_root=tmp_path)
        raw = {
            "id": 99,
            "name": "S082-01-INT-Tempo-V001",
            "type": "Ride",
            "start_date_local": "2026-02-23T10:00:00",
            "moving_time": 3600,
            "icu_training_load": 65,
            "icu_intensity": 75,
            "source": "GARMIN",
        }
        activity_data = gen.format_activity_data(raw)

        prompt = gen.generate_prompt(
            activity_data=activity_data,
            wellness_pre=None,
            wellness_post=None,
            athlete_context=None,
            recent_workouts=None,
            session_prescription=None,
        )

        assert "Prescription Coach" not in prompt


# =======================
# TestHandleGetActivityIntervals
# =======================


class TestHandleGetActivityIntervals:
    @pytest.mark.asyncio
    async def test_get_activity_intervals_success(self):
        """Success path: 3 intervals returned with filtered fields."""
        from magma_cycling.mcp_server import handle_get_activity_intervals

        mock_client = Mock()
        mock_client.get_activity_intervals.return_value = [
            {
                "type": "RECOVERY",
                "label": "Warmup",
                "start_index": 0,
                "end_index": 600,
                "elapsed_time": 600,
                "moving_time": 580,
                "distance": 5000,
                "average_watts": 150,
                "min_watts": 80,
                "max_watts": 200,
                "average_heartrate": 120,
                "min_heartrate": 90,
                "max_heartrate": 140,
                "average_cadence": 85.5,
                "intensity": 62,
                "training_load": 10,
                "average_torque": 14.4,
                "avg_lr_balance": 51.8,
                "some_extra_field": "ignored",
                "average_dfa_a1": 0.8,
            },
            {
                "type": "WORK",
                "label": "3x10min Tempo",
                "start_index": 600,
                "end_index": 2400,
                "elapsed_time": 1800,
                "moving_time": 1800,
                "distance": 18000,
                "average_watts": 230,
                "weighted_average_watts": 235,
                "min_watts": 210,
                "max_watts": 260,
                "average_heartrate": 155,
                "min_heartrate": 140,
                "max_heartrate": 170,
                "average_cadence": 90.2,
                "intensity": 88,
                "training_load": 45,
                "decoupling": 2.1,
                "average_torque": 21.4,
                "min_torque": 17.6,
                "max_torque": 34.5,
                "avg_lr_balance": 52.7,
                "some_extra_field": "ignored",
                "average_dfa_a1": 0.5,
            },
            {
                "type": "RECOVERY",
                "label": "Cooldown",
                "start_index": 2400,
                "end_index": 3000,
                "elapsed_time": 600,
                "moving_time": 590,
                "distance": 4000,
                "average_watts": 120,
                "min_watts": 70,
                "max_watts": 160,
                "average_heartrate": 110,
                "min_heartrate": 95,
                "max_heartrate": 130,
                "average_cadence": 80.0,
                "intensity": 55,
                "training_load": 8,
                "some_extra_field": "ignored",
                "average_dfa_a1": 0.9,
            },
        ]

        with patch(INTERVALS_PATCH, return_value=mock_client):
            result = await handle_get_activity_intervals({"activity_id": "i107424849"})
        data = json.loads(result[0].text)
        assert data["activity_id"] == "i107424849"
        assert data["total_intervals"] == 3
        assert data["total_elapsed_seconds"] == 3000
        assert len(data["intervals"]) == 3
        # Extra fields should be filtered out
        assert "some_extra_field" not in data["intervals"][0]
        assert "average_dfa_a1" not in data["intervals"][0]
        # Check kept fields
        assert data["intervals"][1]["type"] == "WORK"
        assert data["intervals"][1]["average_watts"] == 230
        assert data["intervals"][1]["average_heartrate"] == 155
        assert data["intervals"][1]["decoupling"] == 2.1
        assert data["intervals"][1]["average_torque"] == 21.4
        assert data["intervals"][1]["avg_lr_balance"] == 52.7

    @pytest.mark.asyncio
    async def test_get_activity_intervals_api_error(self):
        """API error returns error JSON."""
        from magma_cycling.mcp_server import handle_get_activity_intervals

        mock_client = Mock()
        mock_client.get_activity_intervals.side_effect = RuntimeError("API timeout")

        with patch(INTERVALS_PATCH, return_value=mock_client):
            result = await handle_get_activity_intervals({"activity_id": "i999999"})
        data = json.loads(result[0].text)
        assert "error" in data
        assert "API timeout" in data["error"]
        assert data["activity_id"] == "i999999"

    @pytest.mark.asyncio
    async def test_get_activity_intervals_empty(self):
        """Empty intervals list returns total_intervals == 0."""
        from magma_cycling.mcp_server import handle_get_activity_intervals

        mock_client = Mock()
        mock_client.get_activity_intervals.return_value = []

        with patch(INTERVALS_PATCH, return_value=mock_client):
            result = await handle_get_activity_intervals({"activity_id": "i107424849"})
        data = json.loads(result[0].text)
        assert data["total_intervals"] == 0
        assert data["total_elapsed_seconds"] == 0
        assert data["intervals"] == []


WORKOUT_PARSER_PATCH = "magma_cycling.workout_parser.load_workout_descriptions"


class TestHandleApplyWorkoutIntervals:
    """Tests for handle_apply_workout_intervals."""

    @pytest.mark.asyncio
    async def test_manual_mode_dry_run(self):
        """Manual mode with dry_run=true returns preview without PUT."""
        from magma_cycling.mcp_server import handle_apply_workout_intervals

        mock_client = Mock()

        intervals = [
            {"type": "RECOVERY", "label": "Warmup", "start_index": 0, "end_index": 499},
            {"type": "WORK", "label": "Set1", "start_index": 500, "end_index": 999},
        ]
        args = {
            "activity_id": "i127869034",
            "intervals": intervals,
            "dry_run": True,
        }

        with patch(INTERVALS_PATCH, return_value=mock_client):
            result = await handle_apply_workout_intervals(args)

        data = json.loads(result[0].text)
        assert data["mode"] == "manual"
        assert data["dry_run"] is True
        assert data["intervals_count"] == 2
        assert data["intervals"] == intervals
        # PUT should NOT have been called
        mock_client.put_activity_intervals.assert_not_called()

    @pytest.mark.asyncio
    async def test_manual_mode_apply(self):
        """Manual mode with dry_run=false calls PUT."""
        from magma_cycling.mcp_server import handle_apply_workout_intervals

        mock_client = Mock()
        mock_client.put_activity_intervals.return_value = {"status": "ok"}

        intervals = [
            {"type": "WORK", "label": "Set1", "start_index": 0, "end_index": 999},
        ]
        args = {
            "activity_id": "i127869034",
            "intervals": intervals,
            "dry_run": False,
        }

        with patch(INTERVALS_PATCH, return_value=mock_client):
            result = await handle_apply_workout_intervals(args)

        data = json.loads(result[0].text)
        assert data["mode"] == "manual"
        assert data["dry_run"] is False
        assert data["applied"] is True
        mock_client.put_activity_intervals.assert_called_once_with("i127869034", intervals)

    @pytest.mark.asyncio
    async def test_auto_mode_dry_run(self):
        """Auto mode parses workout and returns preview."""
        from magma_cycling.mcp_server import handle_apply_workout_intervals

        mock_client = Mock()
        mock_client.get_activity_streams.return_value = [{"type": "watts", "data": [0] * 3000}]

        workout_text = """\
Variations Cadence (40min, 32 TSS)

Warmup
- 5m ramp 50-65% 85rpm

Main set 3x
- 3m 70% 95rpm
- 2m 70% 80rpm
- 3m 70% 105rpm
- 2m 65% 85rpm

Cooldown
- 5m ramp 65-50% 85rpm"""

        mock_descriptions = {"S082-02-TEC-CadenceVariations-V001": workout_text}

        args = {
            "activity_id": "i127869034",
            "session_id": "S082-02",
            "dry_run": True,
        }

        with (
            patch(INTERVALS_PATCH, return_value=mock_client),
            patch(WORKOUT_PARSER_PATCH, return_value=mock_descriptions),
        ):
            result = await handle_apply_workout_intervals(args)

        data = json.loads(result[0].text)
        assert data["mode"] == "auto"
        assert data["dry_run"] is True
        assert data["session_id"] == "S082-02"
        assert data["stream_points"] == 3000
        assert data["intervals_count"] > 0
        assert "message" in data
        # PUT should NOT have been called
        mock_client.put_activity_intervals.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_no_session_in_name(self):
        """Activity name without session pattern → error with hint."""
        from magma_cycling.mcp_server import handle_apply_workout_intervals

        mock_client = Mock()
        mock_client.get_activity.return_value = {"name": "Morning Ride"}

        args = {"activity_id": "i127869034"}

        with patch(INTERVALS_PATCH, return_value=mock_client):
            result = await handle_apply_workout_intervals(args)

        data = json.loads(result[0].text)
        assert "error" in data
        assert "hint" in data
        assert "session_id" in data["hint"].lower() or "session_id" in data["hint"]

    @pytest.mark.asyncio
    async def test_default_dry_run_true(self):
        """dry_run defaults to true when not specified (safety)."""
        from magma_cycling.mcp_server import handle_apply_workout_intervals

        mock_client = Mock()

        intervals = [
            {"type": "WORK", "label": "Set1", "start_index": 0, "end_index": 999},
        ]
        args = {
            "activity_id": "i127869034",
            "intervals": intervals,
            # dry_run not specified → should default to True
        }

        with patch(INTERVALS_PATCH, return_value=mock_client):
            result = await handle_apply_workout_intervals(args)

        data = json.loads(result[0].text)
        assert data["dry_run"] is True
        mock_client.put_activity_intervals.assert_not_called()

    @pytest.mark.asyncio
    async def test_api_error(self):
        """API exception → JSON error response."""
        from magma_cycling.mcp_server import handle_apply_workout_intervals

        mock_client = Mock()
        mock_client.put_activity_intervals.side_effect = RuntimeError("API timeout")

        args = {
            "activity_id": "i127869034",
            "intervals": [{"type": "WORK", "label": "S1", "start_index": 0, "end_index": 99}],
            "dry_run": False,
        }

        with patch(INTERVALS_PATCH, return_value=mock_client):
            result = await handle_apply_workout_intervals(args)

        data = json.loads(result[0].text)
        assert "error" in data
        assert "API timeout" in data["error"]
        assert data["activity_id"] == "i127869034"


class TestHandleCompareIntervals:
    """Tests for handle_compare_activity_intervals."""

    def _make_interval(self, label, type_="WORK", elapsed_time=300, **kwargs):
        """Helper to build a mock interval dict."""
        iv = {
            "type": type_,
            "label": label,
            "start_index": 0,
            "end_index": 999,
            "elapsed_time": elapsed_time,
            "average_watts": 150,
            "average_heartrate": 130,
            "average_cadence": 90,
            "average_torque": 40.0,
        }
        iv.update(kwargs)
        return iv

    @pytest.mark.asyncio
    async def test_explicit_ids_success(self):
        """3 explicit IDs with common labels → comparison + trends."""
        from magma_cycling.mcp_server import handle_compare_activity_intervals

        mock_client = Mock()
        mock_client.get_activity.side_effect = [
            {"name": "S079-03-CAD", "start_date_local": "2026-02-04T10:00:00"},
            {"name": "S080-03-CAD", "start_date_local": "2026-02-11T10:00:00"},
            {"name": "S081-03-CAD", "start_date_local": "2026-02-18T10:00:00"},
        ]
        mock_client.get_activity_intervals.side_effect = [
            [self._make_interval("Set1 95rpm", average_cadence=94)],
            [self._make_interval("Set1 95rpm", average_cadence=95)],
            [self._make_interval("Set1 95rpm", average_cadence=96)],
        ]

        args = {"activity_ids": ["i100", "i200", "i300"]}
        with patch(INTERVALS_PATCH, return_value=mock_client):
            result = await handle_compare_activity_intervals(args)

        data = json.loads(result[0].text)
        assert data["mode"] == "explicit"
        assert data["activities_compared"] == 3
        assert len(data["comparison"]) == 1
        assert data["comparison"][0]["label"] == "Set1 95rpm"
        trends = data["comparison"][0]["trends"]
        assert "average_cadence" in trends
        assert trends["average_cadence"]["first"] == 94
        assert trends["average_cadence"]["last"] == 96
        assert trends["average_cadence"]["delta"] == 2

    @pytest.mark.asyncio
    async def test_search_mode_success(self):
        """name_pattern + weeks_back → filters matching activities, mode='search'."""
        from magma_cycling.mcp_server import handle_compare_activity_intervals

        mock_client = Mock()
        mock_client.get_activities.return_value = [
            {
                "id": "i100",
                "name": "S079-03-CadenceVariations",
                "start_date_local": "2026-02-04T10:00:00",
            },
            {"id": "i200", "name": "S080-01-Endurance", "start_date_local": "2026-02-08T10:00:00"},
            {
                "id": "i300",
                "name": "S081-03-CadenceVariations",
                "start_date_local": "2026-02-18T10:00:00",
            },
        ]
        mock_client.get_activity_intervals.side_effect = [
            [self._make_interval("Set1")],
            [self._make_interval("Set1")],
        ]

        args = {"name_pattern": "CadenceVariations", "weeks_back": 4}
        with patch(INTERVALS_PATCH, return_value=mock_client):
            result = await handle_compare_activity_intervals(args)

        data = json.loads(result[0].text)
        assert data["mode"] == "search"
        assert data["activities_compared"] == 2
        assert "i200" not in data["activity_ids"]
        assert "i100" in data["activity_ids"]
        assert "i300" in data["activity_ids"]

    @pytest.mark.asyncio
    async def test_no_matching_activities_search(self):
        """Pattern that matches nothing → error."""
        from magma_cycling.mcp_server import handle_compare_activity_intervals

        mock_client = Mock()
        mock_client.get_activities.return_value = [
            {"id": "i100", "name": "S079-01-Endurance", "start_date_local": "2026-02-04T10:00:00"},
        ]

        args = {"name_pattern": "NonExistentWorkout"}
        with patch(INTERVALS_PATCH, return_value=mock_client):
            result = await handle_compare_activity_intervals(args)

        data = json.loads(result[0].text)
        assert "error" in data
        assert "NonExistentWorkout" in data["error"]

    @pytest.mark.asyncio
    async def test_missing_both_params(self):
        """Neither activity_ids nor name_pattern → error."""
        from magma_cycling.mcp_server import handle_compare_activity_intervals

        args = {}
        result = await handle_compare_activity_intervals(args)

        data = json.loads(result[0].text)
        assert "error" in data
        assert "activity_ids" in data["error"]
        assert "name_pattern" in data["error"]

    @pytest.mark.asyncio
    async def test_gap_intervals_filtered(self):
        """Intervals with elapsed_time <= 2 are excluded."""
        from magma_cycling.mcp_server import handle_compare_activity_intervals

        mock_client = Mock()
        mock_client.get_activity.side_effect = [
            {"name": "A1", "start_date_local": "2026-02-04T10:00:00"},
        ]
        mock_client.get_activity_intervals.return_value = [
            self._make_interval("Set1", elapsed_time=300),
            self._make_interval("Gap", elapsed_time=1),
            self._make_interval("Set2", elapsed_time=300),
        ]

        args = {"activity_ids": ["i100"]}
        with patch(INTERVALS_PATCH, return_value=mock_client):
            result = await handle_compare_activity_intervals(args)

        data = json.loads(result[0].text)
        labels = [c["label"] for c in data["comparison"]]
        assert "Set1" in labels
        assert "Set2" in labels
        assert "Gap" not in labels

    @pytest.mark.asyncio
    async def test_label_filter(self):
        """label_filter='95rpm' → only 95rpm intervals kept."""
        from magma_cycling.mcp_server import handle_compare_activity_intervals

        mock_client = Mock()
        mock_client.get_activity.side_effect = [
            {"name": "A1", "start_date_local": "2026-02-04T10:00:00"},
        ]
        mock_client.get_activity_intervals.return_value = [
            self._make_interval("Set1 95rpm"),
            self._make_interval("Set2 80rpm"),
            self._make_interval("Set3 95rpm"),
        ]

        args = {"activity_ids": ["i100"], "label_filter": "95rpm"}
        with patch(INTERVALS_PATCH, return_value=mock_client):
            result = await handle_compare_activity_intervals(args)

        data = json.loads(result[0].text)
        labels = [c["label"] for c in data["comparison"]]
        assert all("95rpm" in lbl for lbl in labels)
        assert not any("80rpm" in lbl for lbl in labels)

    @pytest.mark.asyncio
    async def test_type_filter_work_only(self):
        """type_filter='WORK' → only WORK intervals kept."""
        from magma_cycling.mcp_server import handle_compare_activity_intervals

        mock_client = Mock()
        mock_client.get_activity.side_effect = [
            {"name": "A1", "start_date_local": "2026-02-04T10:00:00"},
        ]
        mock_client.get_activity_intervals.return_value = [
            self._make_interval("Set1", type_="WORK"),
            self._make_interval("Recovery", type_="RECOVERY"),
        ]

        args = {"activity_ids": ["i100"], "type_filter": "WORK"}
        with patch(INTERVALS_PATCH, return_value=mock_client):
            result = await handle_compare_activity_intervals(args)

        data = json.loads(result[0].text)
        labels = [c["label"] for c in data["comparison"]]
        assert "Set1" in labels
        assert "Recovery" not in labels

    @pytest.mark.asyncio
    async def test_metrics_selection(self):
        """metrics=['average_watts','average_heartrate'] → only those 2 in data."""
        from magma_cycling.mcp_server import handle_compare_activity_intervals

        mock_client = Mock()
        mock_client.get_activity.side_effect = [
            {"name": "A1", "start_date_local": "2026-02-04T10:00:00"},
        ]
        mock_client.get_activity_intervals.return_value = [
            self._make_interval(
                "Set1", average_watts=200, average_heartrate=140, average_cadence=95
            ),
        ]

        args = {
            "activity_ids": ["i100"],
            "metrics": ["average_watts", "average_heartrate"],
        }
        with patch(INTERVALS_PATCH, return_value=mock_client):
            result = await handle_compare_activity_intervals(args)

        data = json.loads(result[0].text)
        interval_data = data["comparison"][0]["activities"][0]["data"]
        assert "average_watts" in interval_data
        assert "average_heartrate" in interval_data
        assert "average_cadence" not in interval_data

    @pytest.mark.asyncio
    async def test_invalid_metrics(self):
        """metrics=['bogus'] → error with available_metrics list."""
        from magma_cycling.mcp_server import handle_compare_activity_intervals

        args = {"activity_ids": ["i100"], "metrics": ["bogus"]}
        result = await handle_compare_activity_intervals(args)

        data = json.loads(result[0].text)
        assert "error" in data
        assert "bogus" in data["error"]
        assert "available_metrics" in data

    @pytest.mark.asyncio
    async def test_label_mismatch_across_activities(self):
        """A has Set1+Set2, B has Set1 only → Set2 data=null for B."""
        from magma_cycling.mcp_server import handle_compare_activity_intervals

        mock_client = Mock()
        mock_client.get_activity.side_effect = [
            {"name": "A1", "start_date_local": "2026-02-04T10:00:00"},
            {"name": "A2", "start_date_local": "2026-02-11T10:00:00"},
        ]
        mock_client.get_activity_intervals.side_effect = [
            [
                self._make_interval("Set1"),
                self._make_interval("Set2"),
            ],
            [
                self._make_interval("Set1"),
            ],
        ]

        args = {"activity_ids": ["i100", "i200"]}
        with patch(INTERVALS_PATCH, return_value=mock_client):
            result = await handle_compare_activity_intervals(args)

        data = json.loads(result[0].text)
        set2_entry = [c for c in data["comparison"] if c["label"] == "Set2"][0]
        # First activity has data, second has null
        assert set2_entry["activities"][0]["data"] is not None
        assert set2_entry["activities"][1]["data"] is None
