"""
Additional MCP handler tests — push mcp_server.py from 50% to 60%.

Focuses on: handle_update_session, handle_sync_week_to_intervals,
handle_get_metrics, handle_withings_get_sleep, handle_withings_get_weight,
handle_withings_get_readiness.
"""

import json
from datetime import date
from unittest.mock import MagicMock, Mock, patch

import pytest

pytest_plugins = ("pytest_asyncio",)

TOWER_PATCH = "cyclisme_training_logs.planning.control_tower.planning_tower"
INTERVALS_PATCH = "cyclisme_training_logs.config.create_intervals_client"


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
    s.planned_tss = 65
    s.duration_min = 60
    s.description = "Tempo 3x10min"
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
        from cyclisme_training_logs.mcp_server import handle_update_session

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
        from cyclisme_training_logs.mcp_server import handle_update_session

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
        from cyclisme_training_logs.mcp_server import handle_update_session

        mock_tower.modify_week.side_effect = FileNotFoundError("not found")
        args = {"week_id": "S099", "session_id": "S099-01", "status": "skipped"}
        with patch(TOWER_PATCH, mock_tower):
            with pytest.raises(FileNotFoundError):
                await handle_update_session(args)

    @pytest.mark.asyncio
    async def test_with_reason_and_skipped_status(self, mock_plan, mock_session):
        """Test with skip reason for skipped status."""
        from cyclisme_training_logs.mcp_server import handle_update_session

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
        from cyclisme_training_logs.mcp_server import handle_update_session

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


class TestHandleSyncWeekToIntervals:
    @pytest.mark.asyncio
    async def test_dry_run_no_api_calls(self, mock_plan, mock_session):
        """dry_run=True: computes plan but skips API create/update calls."""
        from cyclisme_training_logs.mcp_server import handle_sync_week_to_intervals

        mock_session.intervals_id = None
        mock_plan.planned_sessions = [mock_session]
        tower = make_tower(mock_plan)
        mock_client = Mock()
        mock_client.get_events.return_value = []

        args = {"week_id": "S081", "dry_run": True}
        with patch(TOWER_PATCH, tower):
            with patch(INTERVALS_PATCH, return_value=mock_client):
                result = await handle_sync_week_to_intervals(args)
        data = json.loads(result[0].text)
        assert data["dry_run"] is True
        assert data["summary"]["to_create"] == 1
        assert data["summary"]["created"] == 0  # dry_run: no actual creation
        mock_client.create_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_completed_session_skipped(self, mock_plan, mock_session):
        """Completed sessions are protected — skipped from sync."""
        from cyclisme_training_logs.mcp_server import handle_sync_week_to_intervals

        mock_session.status = "completed"
        mock_session.intervals_id = 12345
        mock_plan.planned_sessions = [mock_session]
        tower = make_tower(mock_plan)
        mock_client = Mock()
        mock_client.get_events.return_value = []

        args = {"week_id": "S081", "dry_run": True}
        with patch(TOWER_PATCH, tower):
            with patch(INTERVALS_PATCH, return_value=mock_client):
                result = await handle_sync_week_to_intervals(args)
        data = json.loads(result[0].text)
        assert data["summary"]["skipped_completed"] == 1
        assert data["summary"]["to_create"] == 0

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self, mock_tower):
        """FileNotFoundError from planning_tower returns error."""
        from cyclisme_training_logs.mcp_server import handle_sync_week_to_intervals

        mock_tower.read_week.side_effect = FileNotFoundError("not found")
        mock_client = Mock()
        args = {"week_id": "S099"}
        with patch(TOWER_PATCH, mock_tower):
            with patch(INTERVALS_PATCH, return_value=mock_client):
                result = await handle_sync_week_to_intervals(args)
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_intervals_id_conflict_with_force_update(self, mock_plan, mock_session):
        """Session with intervals_id that exists remotely — force_update flag."""
        from cyclisme_training_logs.mcp_server import handle_sync_week_to_intervals

        mock_session.intervals_id = "evt123"
        mock_session.status = "pending"
        mock_session.name = "SameName"
        mock_session.description = "Same description"
        mock_plan.planned_sessions = [mock_session]
        tower = make_tower(mock_plan)
        mock_client = Mock()
        # Remote event with same name/description (no conflict)
        mock_client.get_events.return_value = [
            {
                "id": "evt123",
                "category": "WORKOUT",
                "name": "SameName",
                "description": "Same description",
            },
        ]
        mock_client.update_event.return_value = True

        args = {"week_id": "S081", "dry_run": True, "force_update": False}
        with patch(TOWER_PATCH, tower):
            with patch(INTERVALS_PATCH, return_value=mock_client):
                result = await handle_sync_week_to_intervals(args)
        data = json.loads(result[0].text)
        # No changes needed (same name/desc)
        assert data["summary"]["to_update"] == 0

    @pytest.mark.asyncio
    async def test_remote_conflict_detected(self, mock_plan, mock_session):
        """Session with intervals_id but remote was manually modified → warning."""
        from cyclisme_training_logs.mcp_server import handle_sync_week_to_intervals

        mock_session.intervals_id = "evt123"
        mock_session.status = "pending"
        mock_session.name = "LocalName"
        mock_session.description = "Local desc"
        mock_plan.planned_sessions = [mock_session]
        tower = make_tower(mock_plan)
        mock_client = Mock()
        # Remote event has different name (manually modified)
        mock_client.get_events.return_value = [
            {
                "id": "evt123",
                "category": "WORKOUT",
                "name": "RemoteName",
                "description": "Remote desc",
            },
        ]

        args = {"week_id": "S081", "dry_run": True, "force_update": False}
        with patch(TOWER_PATCH, tower):
            with patch(INTERVALS_PATCH, return_value=mock_client):
                result = await handle_sync_week_to_intervals(args)
        data = json.loads(result[0].text)
        assert data["summary"]["warnings"] == 1
        assert data["status"] == "success_with_warnings"


# =======================
# TestHandleGetMetrics
# =======================


class TestHandleGetMetrics:
    @pytest.mark.asyncio
    async def test_success_returns_wellness_data(self):
        from cyclisme_training_logs.mcp_server import handle_get_metrics

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

        with patch("cyclisme_training_logs.config.get_intervals_config", return_value=mock_config):
            with patch(
                "cyclisme_training_logs.api.intervals_client.IntervalsClient",
                return_value=mock_client,
            ):
                result = await handle_get_metrics({})
        data = json.loads(result[0].text)
        assert data["ctl"] == 65
        assert data["atl"] == 70

    @pytest.mark.asyncio
    async def test_no_wellness_data_returns_error(self):
        from cyclisme_training_logs.mcp_server import handle_get_metrics

        mock_config = Mock()
        mock_config.athlete_id = "iXXXXXX"
        mock_config.api_key = "apikey123"
        mock_client = Mock()
        mock_client.get_wellness.return_value = []

        with patch("cyclisme_training_logs.config.get_intervals_config", return_value=mock_config):
            with patch(
                "cyclisme_training_logs.api.intervals_client.IntervalsClient",
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
        from cyclisme_training_logs.mcp_server import handle_withings_get_sleep

        mock_client = Mock()
        mock_client.get_last_night_sleep.return_value = {
            "total_sleep_hours": 7.5,
            "sleep_score": 85,
        }
        with patch(
            "cyclisme_training_logs.config.create_withings_client", return_value=mock_client
        ):
            result = await handle_withings_get_sleep({"last_night_only": True})
        data = json.loads(result[0].text)
        assert "last_night_sleep" in data
        assert data["last_night_sleep"]["total_sleep_hours"] == 7.5

    @pytest.mark.asyncio
    async def test_last_night_only_no_data(self):
        from cyclisme_training_logs.mcp_server import handle_withings_get_sleep

        mock_client = Mock()
        mock_client.get_last_night_sleep.return_value = None
        with patch(
            "cyclisme_training_logs.config.create_withings_client", return_value=mock_client
        ):
            result = await handle_withings_get_sleep({"last_night_only": True})
        data = json.loads(result[0].text)
        assert data["last_night_sleep"] is None
        assert "message" in data

    @pytest.mark.asyncio
    async def test_date_range_returns_sessions(self):
        from cyclisme_training_logs.mcp_server import handle_withings_get_sleep

        mock_client = Mock()
        mock_client.get_sleep.return_value = [
            {"date": "2026-02-17", "total_sleep_hours": 7.0},
        ]
        with patch(
            "cyclisme_training_logs.config.create_withings_client", return_value=mock_client
        ):
            result = await handle_withings_get_sleep(
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
        from cyclisme_training_logs.mcp_server import handle_withings_get_sleep

        mock_client = Mock()
        mock_client.get_sleep.return_value = []
        with patch(
            "cyclisme_training_logs.config.create_withings_client", return_value=mock_client
        ):
            result = await handle_withings_get_sleep({})
        data = json.loads(result[0].text)
        assert "start_date" in data
        assert data["count"] == 0


# =======================
# TestHandleWithingsGetWeight
# =======================


class TestHandleWithingsGetWeight:
    @pytest.mark.asyncio
    async def test_latest_only_with_data(self):
        from cyclisme_training_logs.mcp_server import handle_withings_get_weight

        mock_client = Mock()
        mock_client.get_latest_weight.return_value = {"weight_kg": 72.3}
        with patch(
            "cyclisme_training_logs.config.create_withings_client", return_value=mock_client
        ):
            result = await handle_withings_get_weight({"latest_only": True})
        data = json.loads(result[0].text)
        assert data["latest_weight"]["weight_kg"] == 72.3

    @pytest.mark.asyncio
    async def test_latest_only_no_data(self):
        from cyclisme_training_logs.mcp_server import handle_withings_get_weight

        mock_client = Mock()
        mock_client.get_latest_weight.return_value = None
        with patch(
            "cyclisme_training_logs.config.create_withings_client", return_value=mock_client
        ):
            result = await handle_withings_get_weight({"latest_only": True})
        data = json.loads(result[0].text)
        assert data["latest_weight"] is None
        assert "message" in data

    @pytest.mark.asyncio
    async def test_date_range_returns_measurements(self):
        from cyclisme_training_logs.mcp_server import handle_withings_get_weight

        mock_client = Mock()
        mock_client.get_measurements.return_value = [
            {"date": "2026-02-17", "weight_kg": 72.5},
        ]
        with patch(
            "cyclisme_training_logs.config.create_withings_client", return_value=mock_client
        ):
            result = await handle_withings_get_weight(
                {
                    "start_date": "2026-02-17",
                    "end_date": "2026-02-23",
                }
            )
        data = json.loads(result[0].text)
        assert data["count"] == 1

    @pytest.mark.asyncio
    async def test_default_30_days_range(self):
        from cyclisme_training_logs.mcp_server import handle_withings_get_weight

        mock_client = Mock()
        mock_client.get_measurements.return_value = []
        with patch(
            "cyclisme_training_logs.config.create_withings_client", return_value=mock_client
        ):
            result = await handle_withings_get_weight({})
        data = json.loads(result[0].text)
        assert "start_date" in data
        assert data["count"] == 0


# =======================
# TestHandleWithingsGetReadiness
# =======================


class TestHandleWithingsGetReadiness:
    @pytest.mark.asyncio
    async def test_no_sleep_data_returns_no_data_status(self):
        from cyclisme_training_logs.mcp_server import handle_withings_get_readiness

        mock_client = Mock()
        mock_client.get_last_night_sleep.return_value = None
        with patch(
            "cyclisme_training_logs.config.create_withings_client", return_value=mock_client
        ):
            result = await handle_withings_get_readiness({})
        data = json.loads(result[0].text)
        assert data["status"] == "no_data"

    @pytest.mark.asyncio
    async def test_with_sleep_data_evaluates_readiness(self):
        from cyclisme_training_logs.mcp_server import handle_withings_get_readiness

        mock_client = Mock()
        mock_client.get_last_night_sleep.return_value = {
            "total_sleep_hours": 8.0,
            "sleep_score": 90,
        }
        mock_client.evaluate_training_readiness.return_value = {
            "recommended_intensity": "normal",
            "ready_for_intense": True,
        }
        mock_client.get_latest_weight.return_value = {"weight_kg": 72.0}
        with patch(
            "cyclisme_training_logs.config.create_withings_client", return_value=mock_client
        ):
            result = await handle_withings_get_readiness({"date": "2026-02-24"})
        data = json.loads(result[0].text)
        assert data["status"] == "evaluated"
        assert "readiness" in data

    @pytest.mark.asyncio
    async def test_with_date_parameter(self):
        from cyclisme_training_logs.mcp_server import handle_withings_get_readiness

        mock_client = Mock()
        mock_client.get_last_night_sleep.return_value = None
        with patch(
            "cyclisme_training_logs.config.create_withings_client", return_value=mock_client
        ):
            result = await handle_withings_get_readiness({"date": "2026-02-20"})
        data = json.loads(result[0].text)
        assert data["date"] == "2026-02-20"


# =======================
# TestHandleListWeeksException
# =======================


class TestHandleListWeeksException:
    @pytest.mark.asyncio
    async def test_malformed_json_file_is_skipped(self, tmp_path):
        """Malformed JSON in a planning file is silently skipped."""
        from cyclisme_training_logs.mcp_server import handle_list_weeks

        # Write bad JSON
        (tmp_path / "week_planning_S081.json").write_text("{bad json}")
        mc = Mock()
        mc.week_planning_dir = tmp_path
        with patch("cyclisme_training_logs.config.get_data_config", return_value=mc):
            result = await handle_list_weeks({"limit": 10})
        data = json.loads(result[0].text)
        assert data["total_found"] == 0  # Bad file skipped
