"""
Tests for additional MCP handlers — Sprint R14 Phase 0 coverage.

Targets: mcp_server.py 20% → 60%
Strategy: Test handlers directly with mocked dependencies.
"""

import json
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

pytest_plugins = ("pytest_asyncio",)

# Common patch paths
TOWER_PATCH = "magma_cycling.planning.control_tower.planning_tower"
INTERVALS_PATCH = "magma_cycling.config.create_intervals_client"
DATA_CONFIG_PATCH = "magma_cycling.config.get_data_config"
HEALTH_PROVIDER_PATCH = "magma_cycling.health.create_health_provider"
_HEALTH_PROVIDER_INFO = {"provider": "WithingsProvider", "status": "ready"}


def _mock_health_provider(**kwargs):
    """Create a Mock HealthProvider with get_provider_info pre-configured."""
    provider = Mock(**kwargs)
    provider.get_provider_info.return_value = _HEALTH_PROVIDER_INFO
    return provider


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
    s.description = "Tempo 3x10min"
    s.status = "pending"
    s.intervals_id = None
    s.skip_reason = None
    s.category = "INT"
    return s


@pytest.fixture
def mock_session2():
    s = Mock()
    s.session_id = "S081-06"
    s.session_date = date(2026, 2, 22)
    s.name = "EnduranceLongue"
    s.session_type = "END"
    s.version = "V001"
    s.tss_planned = 80
    s.duration_min = 90
    s.description = "90min endurance"
    s.status = "pending"
    s.intervals_id = None
    s.skip_reason = None
    s.category = "END"
    return s


@pytest.fixture
def mock_plan(mock_session):
    p = Mock()
    p.week_id = "S081"
    p.start_date = date(2026, 2, 17)
    p.end_date = date(2026, 2, 23)
    p.athlete_id = "iXXXXXX"
    p.tss_target = 300
    p.created_at = "2026-02-17T10:00:00"
    p.last_updated = "2026-02-17T10:00:00"
    p.version = 1
    p.planned_sessions = [mock_session]
    p.notes = None
    return p


def make_tower(plan):
    """Create a mock planning_tower with a given plan."""
    tower = Mock()
    tower.read_week.return_value = plan
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=plan)
    ctx.__exit__ = Mock(return_value=False)
    tower.modify_week.return_value = ctx
    tower.planning_dir = Mock()
    tower.planning_dir.exists.return_value = False
    return tower


@pytest.fixture
def mock_tower(mock_plan):
    return make_tower(mock_plan)


@pytest.fixture
def mock_intervals():
    client = Mock()
    client.get_activities.return_value = []
    client.get_events.return_value = []
    client.get_wellness.return_value = [{"id": "2026-02-17", "ctl": 65, "atl": 70, "tsb": -5}]
    client.get_athlete.return_value = {
        "name": "Test Athlete",
        "icu_weight": 72.5,
        "icu_resting_hr": 45,
        "sportSettings": [
            {
                "types": ["Ride", "VirtualRide"],
                "ftp": 240,
                "max_hr": 180,
                "lthr": 160,
                "w_prime": 20000,
                "power_zones": [55, 75, 90, 105, 120, 150, 999],
                "power_zone_names": [
                    "Active Recovery",
                    "Endurance",
                    "Tempo",
                    "Threshold",
                    "VO2 Max",
                    "Anaerobic",
                    "Neuromuscular",
                ],
                "hr_zones": [120, 135, 145, 155, 165, 175, 180],
                "hr_zone_names": [
                    "Recovery",
                    "Aerobic",
                    "Tempo",
                    "SubThreshold",
                    "SuperThreshold",
                    "Aerobic Capacity",
                    "Anaerobic",
                ],
            }
        ],
    }
    client.create_event.return_value = {"id": "evt123"}
    client.update_event.return_value = True
    client.delete_event.return_value = True
    client.get_provider_info.return_value = {
        "provider": "intervals_icu",
        "athlete_id": "i12345",
        "status": "ready",
    }
    return client


# =======================
# TestHandleListWeeks
# =======================


class TestHandleListWeeks:
    @pytest.mark.asyncio
    async def test_empty_dir_returns_zero_weeks(self, tmp_path):
        from magma_cycling.mcp_server import handle_list_weeks

        mc = Mock()
        mc.week_planning_dir = tmp_path
        with patch(DATA_CONFIG_PATCH, return_value=mc):
            result = await handle_list_weeks({"limit": 10})
        data = json.loads(result[0].text)
        assert data["total_found"] == 0
        assert data["weeks"] == []

    @pytest.mark.asyncio
    async def test_with_planning_file(self, tmp_path):
        from magma_cycling.mcp_server import handle_list_weeks

        week_data = {
            "week_id": "S081",
            "start_date": "2026-02-17",
            "end_date": "2026-02-23",
            "tss_target": 300,
            "planned_sessions": [{"session_id": "S081-01"}],
        }
        (tmp_path / "week_planning_S081.json").write_text(json.dumps(week_data))
        mc = Mock()
        mc.week_planning_dir = tmp_path
        with patch(DATA_CONFIG_PATCH, return_value=mc):
            result = await handle_list_weeks({"limit": 10, "recent": False})
        data = json.loads(result[0].text)
        assert data["total_found"] == 1
        assert data["weeks"][0]["week_id"] == "S081"
        assert data["weeks"][0]["sessions"] == 1

    @pytest.mark.asyncio
    async def test_recent_reverses_order(self, tmp_path):
        from magma_cycling.mcp_server import handle_list_weeks

        for wid in ["S080", "S081"]:
            week_data = {
                "week_id": wid,
                "start_date": "2026-02-17",
                "end_date": "2026-02-23",
                "tss_target": 300,
                "planned_sessions": [],
            }
            (tmp_path / f"week_planning_{wid}.json").write_text(json.dumps(week_data))
        mc = Mock()
        mc.week_planning_dir = tmp_path
        with patch(DATA_CONFIG_PATCH, return_value=mc):
            result = await handle_list_weeks({"limit": 10, "recent": True})
        data = json.loads(result[0].text)
        assert data["total_found"] == 2
        assert data["weeks"][0]["week_id"] == "S081"

    @pytest.mark.asyncio
    async def test_limit_applied(self, tmp_path):
        from magma_cycling.mcp_server import handle_list_weeks

        for wid in ["S080", "S081", "S082"]:
            week_data = {
                "week_id": wid,
                "start_date": "2026-02-17",
                "end_date": "2026-02-23",
                "tss_target": 300,
                "planned_sessions": [],
            }
            (tmp_path / f"week_planning_{wid}.json").write_text(json.dumps(week_data))
        mc = Mock()
        mc.week_planning_dir = tmp_path
        with patch(DATA_CONFIG_PATCH, return_value=mc):
            result = await handle_list_weeks({"limit": 2})
        data = json.loads(result[0].text)
        assert data["showing"] == 2


# =======================
# TestHandleGetWeekDetails
# =======================


class TestHandleGetWeekDetails:
    @pytest.mark.asyncio
    async def test_success_returns_plan(self, mock_tower, mock_plan, mock_session):
        from magma_cycling.mcp_server import handle_get_week_details

        with patch(TOWER_PATCH, mock_tower):
            result = await handle_get_week_details({"week_id": "S081"})
        data = json.loads(result[0].text)
        assert data["week_id"] == "S081"
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["session_id"] == "S081-03"

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self, mock_tower):
        from magma_cycling.mcp_server import handle_get_week_details

        mock_tower.read_week.side_effect = FileNotFoundError("not found")
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_get_week_details({"week_id": "S099"})
        data = json.loads(result[0].text)
        assert "error" in data
        assert "S099" in data["error"]

    @pytest.mark.asyncio
    async def test_generic_exception_returns_error(self, mock_tower):
        from magma_cycling.mcp_server import handle_get_week_details

        mock_tower.read_week.side_effect = RuntimeError("internal error")
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_get_week_details({"week_id": "S081"})
        data = json.loads(result[0].text)
        assert "error" in data


# =======================
# TestHandleModifySessionDetails
# =======================


class TestHandleModifySessionDetails:
    @pytest.mark.asyncio
    async def test_success_modifies_name(self, mock_tower, mock_session):
        from magma_cycling.mcp_server import handle_modify_session_details

        args = {"week_id": "S081", "session_id": "S081-03", "name": "NewName", "tss_planned": 70}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_modify_session_details(args)
        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert "name=NewName" in data["modifications"]

    @pytest.mark.asyncio
    async def test_no_changes_still_succeeds(self, mock_tower):
        from magma_cycling.mcp_server import handle_modify_session_details

        args = {"week_id": "S081", "session_id": "S081-03"}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_modify_session_details(args)
        data = json.loads(result[0].text)
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_session_not_found_returns_value_error(self, mock_tower):
        from magma_cycling.mcp_server import handle_modify_session_details

        args = {"week_id": "S081", "session_id": "S081-99"}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_modify_session_details(args)
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self, mock_tower):
        from magma_cycling.mcp_server import handle_modify_session_details

        mock_tower.modify_week.side_effect = FileNotFoundError("not found")
        args = {"week_id": "S099", "session_id": "S099-01"}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_modify_session_details(args)
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_generic_exception_returns_error(self, mock_tower):
        from magma_cycling.mcp_server import handle_modify_session_details

        mock_tower.modify_week.side_effect = RuntimeError("boom")
        args = {"week_id": "S081", "session_id": "S081-03"}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_modify_session_details(args)
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    @pytest.mark.parametrize("off_bike_type", ["KIN", "INJ"])
    async def test_off_bike_transition_with_nonzero_tss_rejected(self, mock_tower, off_bike_type):
        """Transition to off-bike type while final tss stays non-zero rejected."""
        from magma_cycling.mcp_server import handle_modify_session_details

        # mock_session starts as INT with tss_planned=65
        args = {"week_id": "S081", "session_id": "S081-03", "type": off_bike_type}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_modify_session_details(args)
        data = json.loads(result[0].text)
        assert "error" in data
        assert off_bike_type in data["error"]
        assert "tss_planned=0" in data["error"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("off_bike_type", ["KIN", "INJ"])
    async def test_off_bike_transition_with_explicit_tss_reset_accepted(
        self, mock_tower, off_bike_type
    ):
        """Transition to off-bike type while resetting tss to 0 in same call succeeds."""
        from magma_cycling.mcp_server import handle_modify_session_details

        args = {
            "week_id": "S081",
            "session_id": "S081-03",
            "type": off_bike_type,
            "tss_planned": 0,
        }
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_modify_session_details(args)
        data = json.loads(result[0].text)
        assert data["status"] == "success"


# =======================
# TestHandleCreateSession
# =======================


class TestHandleCreateSession:
    @pytest.mark.asyncio
    async def test_success_creates_session(self, mock_tower, mock_plan):
        from magma_cycling.mcp_server import handle_create_session

        # Thursday = weekday 3, day_index 4
        args = {
            "week_id": "S081",
            "session_date": "2026-02-19",
            "name": "NewSession",
            "type": "REC",
            "tss_planned": 30,
            "duration_min": 45,
        }
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_create_session(args)
        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert "S081-04" in data["session_id"]

    @pytest.mark.asyncio
    async def test_default_values(self, mock_tower, mock_plan):
        from magma_cycling.mcp_server import handle_create_session

        # Saturday = day_index 6
        args = {"week_id": "S081", "session_date": "2026-02-21"}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_create_session(args)
        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert data["name"] == "NewSession"

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self, mock_tower):
        from magma_cycling.mcp_server import handle_create_session

        mock_tower.modify_week.side_effect = FileNotFoundError("not found")
        args = {"week_id": "S099", "session_date": "2026-02-19"}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_create_session(args)
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_double_session_gets_letter_suffix(self, mock_tower, mock_plan, mock_session):
        """When there's already a session on the same date, new one gets 'a' suffix."""
        from magma_cycling.mcp_server import handle_create_session

        # mock_session is on 2026-02-19 (Thursday = day_index 4), no suffix
        args = {
            "week_id": "S081",
            "session_date": "2026-02-19",
            "name": "SecondSession",
        }
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_create_session(args)
        data = json.loads(result[0].text)
        assert data["status"] == "success"
        # Should get 'a' suffix since first session (S081-03) has no suffix
        assert data["session_id"].endswith("a")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("off_bike_type", ["KIN", "INJ"])
    async def test_off_bike_with_nonzero_tss_rejected(self, mock_tower, mock_plan, off_bike_type):
        """Creating an off-bike session with non-zero TSS is rejected clearly."""
        from magma_cycling.mcp_server import handle_create_session

        args = {
            "week_id": "S081",
            "session_date": "2026-02-19",
            "name": "OffBike",
            "type": off_bike_type,
            "tss_planned": 30,
            "duration_min": 30,
        }
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_create_session(args)
        data = json.loads(result[0].text)
        assert "error" in data
        assert off_bike_type in data["error"]
        assert "tss_planned=0" in data["error"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("off_bike_type", ["KIN", "INJ"])
    async def test_off_bike_with_zero_tss_accepted(self, mock_tower, mock_plan, off_bike_type):
        """Creating an off-bike session with tss=0 succeeds."""
        from magma_cycling.mcp_server import handle_create_session

        args = {
            "week_id": "S081",
            "session_date": "2026-02-19",
            "name": "OffBike",
            "type": off_bike_type,
            "tss_planned": 0,
            "duration_min": 30,
            "description": "Séance hors charge",
        }
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_create_session(args)
        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert data["type"] == off_bike_type


# =======================
# TestHandleDeleteSession
# =======================


class TestHandleDeleteSession:
    @pytest.mark.asyncio
    async def test_success_deletes_session(self, mock_tower, mock_session, mock_plan):
        from magma_cycling.mcp_server import handle_delete_session

        args = {"week_id": "S081", "session_id": "S081-03"}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_delete_session(args)
        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert data["session_id"] == "S081-03"

    @pytest.mark.asyncio
    async def test_completed_session_raises_value_error(self, mock_plan, mock_session):
        from magma_cycling.mcp_server import handle_delete_session

        mock_session.status = "completed"
        tower = make_tower(mock_plan)
        args = {"week_id": "S081", "session_id": "S081-03"}
        with patch(TOWER_PATCH, tower):
            result = await handle_delete_session(args)
        data = json.loads(result[0].text)
        assert "error" in data
        assert "completed" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_synced_session_raises_value_error(self, mock_plan, mock_session):
        from magma_cycling.mcp_server import handle_delete_session

        mock_session.intervals_id = 12345
        tower = make_tower(mock_plan)
        args = {"week_id": "S081", "session_id": "S081-03"}
        with patch(TOWER_PATCH, tower):
            result = await handle_delete_session(args)
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_session_not_found_returns_error(self, mock_tower):
        from magma_cycling.mcp_server import handle_delete_session

        args = {"week_id": "S081", "session_id": "S081-99"}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_delete_session(args)
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self, mock_tower):
        from magma_cycling.mcp_server import handle_delete_session

        mock_tower.modify_week.side_effect = FileNotFoundError("not found")
        args = {"week_id": "S099", "session_id": "S099-01"}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_delete_session(args)
        data = json.loads(result[0].text)
        assert "error" in data


# =======================
# TestHandleDuplicateSession
# =======================


class TestHandleDuplicateSession:
    @pytest.mark.asyncio
    async def test_success_duplicates_to_new_date(self, mock_tower, mock_plan, mock_session):
        from magma_cycling.mcp_server import handle_duplicate_session

        # Target Friday (weekday 4, day_index 5) - no session there
        args = {
            "week_id": "S081",
            "source_session_id": "S081-03",
            "target_date": "2026-02-20",
        }
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_duplicate_session(args)
        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert data["source_session_id"] == "S081-03"
        assert "S081-05" in data["new_session_id"]

    @pytest.mark.asyncio
    async def test_source_not_found_returns_error(self, mock_tower):
        from magma_cycling.mcp_server import handle_duplicate_session

        args = {
            "week_id": "S081",
            "source_session_id": "S081-99",
            "target_date": "2026-02-20",
        }
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_duplicate_session(args)
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self, mock_tower):
        from magma_cycling.mcp_server import handle_duplicate_session

        mock_tower.modify_week.side_effect = FileNotFoundError("not found")
        args = {
            "week_id": "S099",
            "source_session_id": "S099-01",
            "target_date": "2026-02-20",
        }
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_duplicate_session(args)
        data = json.loads(result[0].text)
        assert "error" in data


# =======================
# TestHandleSwapSessions
# =======================


class TestHandleSwapSessions:
    @pytest.mark.asyncio
    async def test_success_swaps_dates(self, mock_plan, mock_session, mock_session2):
        from magma_cycling.mcp_server import handle_swap_sessions

        mock_plan.planned_sessions = [mock_session, mock_session2]
        tower = make_tower(mock_plan)
        args = {
            "week_id": "S081",
            "session_id_1": "S081-03",
            "session_id_2": "S081-06",
        }
        with patch(TOWER_PATCH, tower):
            result = await handle_swap_sessions(args)
        data = json.loads(result[0].text)
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_session_1_not_found_returns_error(self, mock_tower, mock_plan):
        from magma_cycling.mcp_server import handle_swap_sessions

        args = {"week_id": "S081", "session_id_1": "S081-99", "session_id_2": "S081-03"}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_swap_sessions(args)
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_completed_session_blocked(self, mock_plan, mock_session, mock_session2):
        from magma_cycling.mcp_server import handle_swap_sessions

        mock_session.status = "completed"
        mock_plan.planned_sessions = [mock_session, mock_session2]
        tower = make_tower(mock_plan)
        args = {"week_id": "S081", "session_id_1": "S081-03", "session_id_2": "S081-06"}
        with patch(TOWER_PATCH, tower):
            result = await handle_swap_sessions(args)
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self, mock_tower):
        from magma_cycling.mcp_server import handle_swap_sessions

        mock_tower.modify_week.side_effect = FileNotFoundError("not found")
        args = {"week_id": "S099", "session_id_1": "S099-01", "session_id_2": "S099-02"}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_swap_sessions(args)
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_swap_updates_remote_events(self, mock_plan, mock_session, mock_session2):
        """Enhancement: swap updates remote events with new name + date."""
        from magma_cycling.mcp_server import handle_swap_sessions

        mock_session.intervals_id = "evt1"
        mock_session2.intervals_id = "evt2"
        mock_plan.planned_sessions = [mock_session, mock_session2]
        tower = make_tower(mock_plan)
        mock_client = Mock()
        mock_client.update_event.return_value = True

        args = {
            "week_id": "S081",
            "session_id_1": "S081-03",
            "session_id_2": "S081-06",
        }
        with patch(TOWER_PATCH, tower):
            with patch(INTERVALS_PATCH, return_value=mock_client):
                result = await handle_swap_sessions(args)
        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert data["remote_updated"] is True
        assert set(data["swapped_session_ids"]) == {"S081-03", "S081-06"}
        # Both remote events should have been updated with name + start_date_local
        assert mock_client.update_event.call_count == 2
        for call in mock_client.update_event.call_args_list:
            event_data = call[0][1]
            assert "name" in event_data
            assert "start_date_local" in event_data

    @pytest.mark.asyncio
    async def test_swap_session_ids_are_exchanged(self, mock_plan, mock_session, mock_session2):
        """Session IDs are swapped so day index matches the new date."""
        from magma_cycling.mcp_server import handle_swap_sessions

        mock_plan.planned_sessions = [mock_session, mock_session2]
        tower = make_tower(mock_plan)
        args = {
            "week_id": "S081",
            "session_id_1": "S081-03",
            "session_id_2": "S081-06",
        }
        with patch(TOWER_PATCH, tower):
            result = await handle_swap_sessions(args)
        data = json.loads(result[0].text)
        assert data["status"] == "success"
        # After swap: session_1 (TempoCourt) should now have id S081-06
        # and session_2 (EnduranceLongue) should now have id S081-03
        assert mock_session.session_id == "S081-06"
        assert mock_session2.session_id == "S081-03"

    @pytest.mark.asyncio
    async def test_swap_no_remote_update_without_intervals_ids(
        self, mock_plan, mock_session, mock_session2
    ):
        """No remote update when sessions lack intervals_id."""
        from magma_cycling.mcp_server import handle_swap_sessions

        mock_session.intervals_id = None
        mock_session2.intervals_id = "evt2"  # Only one has id
        mock_plan.planned_sessions = [mock_session, mock_session2]
        tower = make_tower(mock_plan)
        mock_client = Mock()

        args = {
            "week_id": "S081",
            "session_id_1": "S081-03",
            "session_id_2": "S081-06",
        }
        with patch(TOWER_PATCH, tower):
            with patch(INTERVALS_PATCH, return_value=mock_client):
                result = await handle_swap_sessions(args)
        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert data["remote_updated"] is False
        mock_client.update_event.assert_not_called()


# =======================
# TestHandleAttachWorkout
# =======================


class TestHandleAttachWorkout:
    @pytest.mark.asyncio
    async def test_success_writes_file(self, tmp_path):
        from magma_cycling.mcp_server import handle_attach_workout

        mc = Mock()
        mc.data_repo_path = tmp_path
        args = {
            "session_id": "S081-03",
            "workout_name": "TempoCourt",
            "content": "<workout>3x10min tempo</workout>",
        }
        with patch(DATA_CONFIG_PATCH, return_value=mc):
            result = await handle_attach_workout(args)
        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert "S081-03-WKT-TempoCourt-V001.zwo" in data["filename"]
        # File should exist
        assert (tmp_path / "workouts" / data["filename"]).exists()

    @pytest.mark.asyncio
    async def test_custom_type_and_extension(self, tmp_path):
        from magma_cycling.mcp_server import handle_attach_workout

        mc = Mock()
        mc.data_repo_path = tmp_path
        args = {
            "session_id": "S081-03",
            "workout_name": "Intervals",
            "content": "SECONDS=60,POWER=250",
            "workout_type": "INT",
            "extension": "mrc",
            "version": "V002",
        }
        with patch(DATA_CONFIG_PATCH, return_value=mc):
            result = await handle_attach_workout(args)
        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert "S081-03-INT-Intervals-V002.mrc" in data["filename"]


# =======================
# TestHandleGetWorkout
# =======================


class TestHandleGetWorkout:
    @pytest.mark.asyncio
    async def test_workout_not_found_returns_planning_description(self, tmp_path):
        from magma_cycling.mcp_server import handle_get_workout

        mock_session = Mock()
        mock_session.session_id = "S081-03"
        mock_session.name = "EnduranceBase"
        mock_session.session_type = "END"
        mock_session.description = "2h endurance Z2"
        mock_session.tss_planned = 80
        mock_session.duration_min = 120

        mock_plan = Mock()
        mock_plan.planned_sessions = [mock_session]

        mc = Mock()
        mc.data_repo_path = tmp_path
        mc.week_planning_dir = tmp_path / "week_planning"
        mc.data_dir = tmp_path / "data"
        (tmp_path / "workouts").mkdir()

        tower_mock = Mock()
        tower_mock.read_week.return_value = mock_plan

        with (
            patch(DATA_CONFIG_PATCH, return_value=mc),
            patch(TOWER_PATCH, tower_mock),
            patch(
                "magma_cycling.workout_parser.load_workout_descriptions",
                return_value={},
            ),
        ):
            result = await handle_get_workout({"session_id": "S081-03"})
        data = json.loads(result[0].text)
        assert data["found"] is True
        assert data["structured_file"] is None
        assert data["session_definition"]["name"] == "EnduranceBase"
        assert data["session_definition"]["description"] == "2h endurance Z2"
        assert data["session_definition"]["tss_planned"] == 80
        assert data["full_description"] is None

    @pytest.mark.asyncio
    async def test_workout_fallback_loads_workouts_txt(self, tmp_path):
        """get-workout loads full description from {week_id}_workouts.txt."""
        from magma_cycling.mcp_server import handle_get_workout

        mc = Mock()
        mc.data_repo_path = tmp_path
        (tmp_path / "workouts").mkdir()

        tower_mock = Mock()
        tower_mock.read_week.side_effect = Exception("no plan")

        full_desc = "2x20min @ 85% FTP\nRecup 5min entre series"

        with (
            patch(DATA_CONFIG_PATCH, return_value=mc),
            patch(TOWER_PATCH, tower_mock),
            patch(
                "magma_cycling.workout_parser.load_workout_descriptions",
                return_value={"S081-03": full_desc},
            ),
        ):
            result = await handle_get_workout({"session_id": "S081-03"})
        data = json.loads(result[0].text)
        assert data["found"] is True
        assert data["full_description"] == full_desc
        assert data["session_definition"] is None

    @pytest.mark.asyncio
    async def test_workout_found_returns_content(self, tmp_path):
        from magma_cycling.mcp_server import handle_get_workout

        workouts_dir = tmp_path / "workouts"
        workouts_dir.mkdir()
        workout_file = workouts_dir / "S081-03-WKT-Tempo-V001.zwo"
        workout_file.write_text("<workout>content</workout>")

        mc = Mock()
        mc.data_repo_path = tmp_path
        with patch(DATA_CONFIG_PATCH, return_value=mc):
            result = await handle_get_workout({"session_id": "S081-03"})
        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert data["content"] == "<workout>content</workout>"
        assert data["extension"] == "zwo"


# =======================
# TestHandleValidateWorkout
# =======================


class TestHandleValidateWorkout:
    @pytest.mark.asyncio
    async def test_valid_workout(self):
        from magma_cycling.mcp_server import handle_validate_workout

        mock_validator = Mock()
        mock_validator.validate_workout.return_value = (True, [], [])

        with patch(
            "magma_cycling.intervals_format_validator.IntervalsFormatValidator",
            return_value=mock_validator,
        ):
            result = await handle_validate_workout({"workout_text": "valid workout text"})
        data = json.loads(result[0].text)
        assert data["valid"] is True
        assert data["errors"] == []

    @pytest.mark.asyncio
    async def test_invalid_workout_with_auto_fix(self):
        from magma_cycling.mcp_server import handle_validate_workout

        mock_validator = Mock()
        mock_validator.validate_workout.side_effect = [
            (False, ["error1"], ["warn1"]),
            (True, [], []),
        ]
        mock_validator.fix_repetition_format.return_value = "fixed workout text"
        mock_validator.fix_warmup_cooldown.return_value = "fixed workout text"

        with patch(
            "magma_cycling.intervals_format_validator.IntervalsFormatValidator",
            return_value=mock_validator,
        ):
            result = await handle_validate_workout(
                {
                    "workout_text": "broken workout",
                    "auto_fix": True,
                }
            )
        data = json.loads(result[0].text)
        assert data["auto_fixed"] is True
        assert data["valid_after_fix"] is True

    @pytest.mark.asyncio
    async def test_invalid_workout_no_auto_fix(self):
        from magma_cycling.mcp_server import handle_validate_workout

        mock_validator = Mock()
        mock_validator.validate_workout.return_value = (False, ["bad format"], [])

        with patch(
            "magma_cycling.intervals_format_validator.IntervalsFormatValidator",
            return_value=mock_validator,
        ):
            result = await handle_validate_workout({"workout_text": "bad workout"})
        data = json.loads(result[0].text)
        assert data["valid"] is False
        assert data["auto_fixed"] is False


# =======================
# TestHandleDeleteRemoteEvent
# =======================


class TestHandleDeleteRemoteEvent:
    @pytest.mark.asyncio
    async def test_no_confirm_returns_error(self):
        from magma_cycling.mcp_server import handle_delete_remote_event

        result = await handle_delete_remote_event({"event_id": "evt123"})
        data = json.loads(result[0].text)
        assert "error" in data
        assert "confirmation" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_no_confirm_explicit_false(self):
        from magma_cycling.mcp_server import handle_delete_remote_event

        result = await handle_delete_remote_event({"event_id": "evt123", "confirm": False})
        data = json.loads(result[0].text)
        assert "error" in data


# =======================
# TestHandleListRemoteEvents
# =======================


class TestHandleListRemoteEvents:
    @pytest.mark.asyncio
    async def test_success_returns_events(self, mock_intervals):
        from magma_cycling.mcp_server import handle_list_remote_events

        mock_intervals.get_events.return_value = [
            {
                "id": "evt1",
                "category": "WORKOUT",
                "name": "Tempo",
                "start_date_local": "2026-02-19T17:00:00",
                "type": "VirtualRide",
                "description": "",
            },
            {
                "id": "evt2",
                "category": "NOTE",
                "name": "Note",
                "start_date_local": "2026-02-20T00:00:00",
                "type": None,
                "description": "",
            },
        ]
        with patch(INTERVALS_PATCH, return_value=mock_intervals):
            result = await handle_list_remote_events(
                {
                    "start_date": "2026-02-17",
                    "end_date": "2026-02-23",
                }
            )
        data = json.loads(result[0].text)
        assert data["total_events"] == 2

    @pytest.mark.asyncio
    async def test_category_filter(self, mock_intervals):
        from magma_cycling.mcp_server import handle_list_remote_events

        mock_intervals.get_events.return_value = [
            {
                "id": "evt1",
                "category": "WORKOUT",
                "name": "Tempo",
                "start_date_local": "2026-02-19",
                "type": "VirtualRide",
                "description": "",
            },
            {
                "id": "evt2",
                "category": "NOTE",
                "name": "Note",
                "start_date_local": "2026-02-20",
                "type": None,
                "description": "",
            },
        ]
        with patch(INTERVALS_PATCH, return_value=mock_intervals):
            result = await handle_list_remote_events(
                {
                    "start_date": "2026-02-17",
                    "end_date": "2026-02-23",
                    "category": "WORKOUT",
                }
            )
        data = json.loads(result[0].text)
        assert data["total_events"] == 1
        assert data["filtered_by"] == "WORKOUT"

    @pytest.mark.asyncio
    async def test_api_error_returns_error(self, mock_intervals):
        from magma_cycling.mcp_server import handle_list_remote_events

        mock_intervals.get_events.side_effect = RuntimeError("API error")
        with patch(INTERVALS_PATCH, return_value=mock_intervals):
            result = await handle_list_remote_events(
                {
                    "start_date": "2026-02-17",
                    "end_date": "2026-02-23",
                }
            )
        data = json.loads(result[0].text)
        assert "error" in data


# =======================
# TestHandleGetAthleteProfile
# =======================


class TestHandleGetAthleteProfile:
    @pytest.mark.asyncio
    async def test_success_returns_profile(self, mock_intervals):
        from magma_cycling.mcp_server import handle_get_athlete_profile

        with patch(INTERVALS_PATCH, return_value=mock_intervals):
            result = await handle_get_athlete_profile({})
        data = json.loads(result[0].text)
        assert data["ftp"] == 240
        assert data["weight"] == 72.5
        assert data["resting_hr"] == 45
        assert data["fthr"] == 160
        assert data["power_zones"][0]["name"] == "Active Recovery"
        assert data["hr_zones"][0]["name"] == "Recovery"

    @pytest.mark.asyncio
    async def test_api_error_returns_error(self, mock_intervals):
        from magma_cycling.mcp_server import handle_get_athlete_profile

        mock_intervals.get_athlete.side_effect = RuntimeError("API error")
        with patch(INTERVALS_PATCH, return_value=mock_intervals):
            result = await handle_get_athlete_profile({})
        data = json.loads(result[0].text)
        assert "error" in data


# =======================
# TestHandleUpdateAthleteProfileError
# =======================


class TestHandleUpdateAthleteProfileError:
    @pytest.mark.asyncio
    async def test_api_error_returns_error(self, mock_intervals):
        from magma_cycling.mcp_server import handle_update_athlete_profile

        mock_intervals.update_athlete.side_effect = RuntimeError("API error")
        with patch(INTERVALS_PATCH, return_value=mock_intervals):
            result = await handle_update_athlete_profile({"updates": {"ftp": 250}})
        data = json.loads(result[0].text)
        assert "error" in data


class TestHandleUpdateAthleteProfilePriorityObjective:
    @pytest.mark.asyncio
    async def test_save_priority_objective(self, tmp_path, monkeypatch):
        from magma_cycling.mcp_server import handle_update_athlete_profile

        yaml_path = tmp_path / "athlete.yaml"
        monkeypatch.setenv("ATHLETE_CONFIG_PATH", str(yaml_path))

        result = await handle_update_athlete_profile(
            {
                "updates": {
                    "priority_objective": {
                        "name": "Les Copains 81km",
                        "type": "granfondo",
                        "target_date": "2026-07-04",
                        "priority": "A",
                        "distance_km": 81,
                        "notes": "Build + taper",
                    }
                }
            }
        )
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert "priority_objective" in data["updated_fields"]
        assert data["current_values"]["priority_objective"]["name"] == "Les Copains 81km"
        assert yaml_path.is_file()

    @pytest.mark.asyncio
    async def test_clear_priority_objective(self, tmp_path, monkeypatch):
        from magma_cycling.mcp_server import handle_update_athlete_profile

        yaml_path = tmp_path / "athlete.yaml"
        yaml_path.write_text(
            "athlete:\n"
            "  priority_objective:\n"
            "    name: x\n"
            "    type: granfondo\n"
            "    target_date: 2026-07-04\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("ATHLETE_CONFIG_PATH", str(yaml_path))

        result = await handle_update_athlete_profile({"updates": {"priority_objective": None}})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert "priority_objective" in data["updated_fields"]
        assert data["current_values"]["priority_objective"] is None

    @pytest.mark.asyncio
    async def test_invalid_objective_returns_error(self, tmp_path, monkeypatch):
        from magma_cycling.mcp_server import handle_update_athlete_profile

        monkeypatch.setenv("ATHLETE_CONFIG_PATH", str(tmp_path / "athlete.yaml"))
        result = await handle_update_athlete_profile(
            {"updates": {"priority_objective": {"name": "x"}}}  # missing required
        )
        data = json.loads(result[0].text)
        assert "error" in data


# =======================
# TestHandleValidateWeekConsistency
# =======================


class TestHandleValidateWeekConsistency:
    @pytest.mark.asyncio
    async def test_success_valid_plan(self, mock_tower, mock_session):
        from magma_cycling.mcp_server import handle_validate_week_consistency

        with patch(TOWER_PATCH, mock_tower):
            result = await handle_validate_week_consistency({"week_id": "S081"})
        data = json.loads(result[0].text)
        assert data["week_id"] == "S081"
        assert "valid" in data
        assert data["total_sessions"] == 1

    @pytest.mark.asyncio
    async def test_empty_description_is_error(self, mock_plan, mock_session):
        from magma_cycling.mcp_server import handle_validate_week_consistency

        mock_session.description = ""
        tower = make_tower(mock_plan)
        with patch(TOWER_PATCH, tower):
            result = await handle_validate_week_consistency({"week_id": "S081"})
        data = json.loads(result[0].text)
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    @pytest.mark.asyncio
    async def test_high_tss_is_warning(self, mock_plan, mock_session):
        from magma_cycling.mcp_server import handle_validate_week_consistency

        mock_session.tss_planned = 350  # > 300 threshold
        tower = make_tower(mock_plan)
        with patch(TOWER_PATCH, tower):
            result = await handle_validate_week_consistency({"week_id": "S081"})
        data = json.loads(result[0].text)
        assert len(data["warnings"]) > 0

    @pytest.mark.asyncio
    async def test_exception_returns_error(self, mock_tower):
        from magma_cycling.mcp_server import handle_validate_week_consistency

        mock_tower.read_week.side_effect = RuntimeError("boom")
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_validate_week_consistency({"week_id": "S081"})
        data = json.loads(result[0].text)
        assert "error" in data


# =======================
# TestHandleGetRecommendations
# =======================


class TestHandleGetRecommendations:
    @pytest.mark.asyncio
    async def test_no_file_returns_planning_notes(self, mock_tower, mock_plan):
        from magma_cycling.mcp_server import handle_get_recommendations

        mock_plan.notes = "No rec file"
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_get_recommendations({"week_id": "S081"})
        data = json.loads(result[0].text)
        assert data["week_id"] == "S081"
        assert data["found"] is False

    @pytest.mark.asyncio
    async def test_exception_returns_error(self, mock_tower):
        from magma_cycling.mcp_server import handle_get_recommendations

        mock_tower.read_week.side_effect = RuntimeError("boom")
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_get_recommendations({"week_id": "S081"})
        data = json.loads(result[0].text)
        assert "error" in data


# =======================
# TestHandleGetTrainingStatistics
# =======================


class TestHandleGetTrainingStatistics:
    @pytest.mark.asyncio
    async def test_success_empty_activities(self, mock_intervals):
        from magma_cycling.mcp_server import handle_get_training_statistics

        mock_intervals.get_activities.return_value = []
        mock_intervals.get_wellness.return_value = []
        with patch(INTERVALS_PATCH, return_value=mock_intervals):
            result = await handle_get_training_statistics(
                {
                    "start_date": "2026-02-17",
                    "end_date": "2026-02-23",
                }
            )
        data = json.loads(result[0].text)
        assert data["summary"]["total_activities"] == 0

    @pytest.mark.asyncio
    async def test_success_with_activities(self, mock_intervals):
        from magma_cycling.mcp_server import handle_get_training_statistics

        mock_intervals.get_activities.return_value = [
            {
                "icu_training_load": 80,
                "moving_time": 3600,
                "distance": 30000,
                "icu_intensity": 0.78,
            },
            {
                "icu_training_load": 65,
                "moving_time": 5400,
                "distance": 45000,
                "icu_intensity": 0.65,
            },
        ]
        mock_intervals.get_wellness.return_value = [
            {"ctl": 60, "id": "2026-02-17"},
            {"ctl": 65, "id": "2026-02-23"},
        ]
        with patch(INTERVALS_PATCH, return_value=mock_intervals):
            result = await handle_get_training_statistics(
                {
                    "start_date": "2026-02-17",
                    "end_date": "2026-02-23",
                }
            )
        data = json.loads(result[0].text)
        assert data["summary"]["total_activities"] == 2
        assert data["summary"]["total_tss"] == 145.0

    @pytest.mark.asyncio
    async def test_api_error_returns_error(self, mock_intervals):
        from magma_cycling.mcp_server import handle_get_training_statistics

        mock_intervals.get_activities.side_effect = RuntimeError("API error")
        with patch(INTERVALS_PATCH, return_value=mock_intervals):
            result = await handle_get_training_statistics(
                {
                    "start_date": "2026-02-17",
                    "end_date": "2026-02-23",
                }
            )
        data = json.loads(result[0].text)
        assert "error" in data


class TestBT042IncludeAdherence:
    """BT-042 : ``include_adherence=True`` (défaut False) ajoute la dimension
    cible initiale + active + réalisé + drift + tss_source_map en scannant
    les weekly plannings dans la plage."""

    @pytest.mark.asyncio
    async def test_default_false_no_adherence_key(self, mock_intervals):
        """Défaut ``include_adherence=False`` : clé ``adherence`` absente
        (zéro surcoût pour les usages actuels)."""
        from magma_cycling.mcp_server import handle_get_training_statistics

        mock_intervals.get_activities.return_value = []
        mock_intervals.get_wellness.return_value = []
        with patch(INTERVALS_PATCH, return_value=mock_intervals):
            result = await handle_get_training_statistics(
                {
                    "start_date": "2026-02-17",
                    "end_date": "2026-02-23",
                }
            )
        data = json.loads(result[0].text)
        assert "adherence" not in data, (
            "BT-042: par défaut, include_adherence=False → pas de clé "
            "adherence (contrat legacy inchangé)"
        )

    @pytest.mark.asyncio
    async def test_include_adherence_true_adds_6_fields(self, mock_intervals, tmp_path):
        """BT-042 : ``include_adherence=True`` avec 1 semaine dans plage
        → 6 champs (initiale/active/realized/drift/adherence_rate/tss_source_map)."""
        from magma_cycling.mcp_server import handle_get_training_statistics

        # Fixture semaine avec 1 session completed + 1 skipped (fantôme)
        week = {
            "week_id": "S999",
            "start_date": "2026-02-17",
            "end_date": "2026-02-23",
            "tss_target": 150,
            "planned_sessions": [
                {
                    "session_id": "S999-01",
                    "date": "2026-02-18",
                    "name": "Endurance",
                    "type": "END",
                    "version": "V001",
                    "tss_planned": 100,
                    "duration_min": 60,
                    "description": "Endurance Z2",
                    "status": "completed",
                    "intervals_id": 12345,
                },
                {
                    "session_id": "S999-02",
                    "date": "2026-02-19",
                    "name": "Repos",
                    "type": "END",
                    "version": "V001",
                    "tss_planned": 50,  # fantôme (skipped avec tss>0)
                    "duration_min": 45,
                    "description": "Skipped",
                    "status": "skipped",
                    "skip_reason": "Fatigue",
                },
            ],
        }
        planning_dir = tmp_path / "week_planning"
        planning_dir.mkdir()
        (planning_dir / "week_planning_S999.json").write_text(json.dumps(week))

        # Activité correspondant à S999-01 avec TSS différent du planned.
        # BT-048 : le matching se fait via ``paired_event_id`` (event
        # calendrier planifié) et NON via ``activity.id`` (course réalisée).
        # ``id`` est un identifiant strictement différent (ex: activity
        # ``i162682746`` avec ``paired_event_id=119167963`` = event S100-06).
        mock_intervals.get_activities.return_value = [
            {
                "id": "i88888",
                "paired_event_id": 12345,
                "icu_training_load": 105,
                "moving_time": 3600,
                "distance": 30000,
                "icu_intensity": 0.72,
            },
        ]
        mock_intervals.get_wellness.return_value = []

        # Patch data_config pour pointer vers tmp_path
        with patch(INTERVALS_PATCH, return_value=mock_intervals):
            # Cf. handler: data_repo_path/data/week_planning ou fallback
            # data_repo_path/week_planning — on utilise la 2e (legacy)
            with patch("magma_cycling.config.get_data_config") as mock_dc:
                mock_dc.return_value.data_repo_path = tmp_path
                result = await handle_get_training_statistics(
                    {
                        "start_date": "2026-02-17",
                        "end_date": "2026-02-23",
                        "include_adherence": True,
                    }
                )

        data = json.loads(result[0].text)
        adh = data.get("adherence")
        assert adh is not None, "BT-042: adherence key doit être présente"
        # Cible initiale stockée = 150
        assert adh["tss_target_initial"] == 150
        # Cible active = 100 (S999-01 seule active, S999-02 skipped exclue)
        assert adh["tss_target_active"] == 100
        # Réalisé via Intervals = 105 (icu_training_load, pas tss_planned 100)
        assert adh["tss_realized"] == 105.0
        # Adherence = 105/100 = 105%
        assert adh["adherence_rate"] == 105.0
        # Drift = |150 - 100| = 50 TSS fantômes
        assert adh["drift_initial_to_active_abs"] == 50
        # Source map : S999-01 vient d'intervals
        assert "S999-01" in adh["tss_source_map"]["intervals"]
        assert "S999-01" not in adh["tss_source_map"]["planned_fallback"]
        assert adh["weeks_in_range"] == ["S999"]

    @pytest.mark.asyncio
    async def test_all_cancelled_week_adherence_none_no_div_zero(self, mock_intervals, tmp_path):
        """BT-042 : semaine 100% annulée dans la plage → active=0 →
        adherence_rate=None (protection div/0, rendu affiche « — »)."""
        from magma_cycling.mcp_server import handle_get_training_statistics

        week = {
            "week_id": "S999",
            "start_date": "2026-02-17",
            "end_date": "2026-02-23",
            "tss_target": 200,
            "planned_sessions": [
                {
                    "session_id": "S999-01",
                    "date": "2026-02-18",
                    "name": "Rest",
                    "type": "END",
                    "version": "V001",
                    "tss_planned": 100,
                    "duration_min": 60,
                    "description": "Rest",
                    "status": "rest_day",
                },
                {
                    "session_id": "S999-02",
                    "date": "2026-02-19",
                    "name": "Skip",
                    "type": "END",
                    "version": "V001",
                    "tss_planned": 100,
                    "duration_min": 60,
                    "description": "Skip",
                    "status": "skipped",
                    "skip_reason": "Fatigue",
                },
            ],
        }
        planning_dir = tmp_path / "week_planning"
        planning_dir.mkdir()
        (planning_dir / "week_planning_S999.json").write_text(json.dumps(week))

        mock_intervals.get_activities.return_value = []
        mock_intervals.get_wellness.return_value = []

        with patch(INTERVALS_PATCH, return_value=mock_intervals):
            with patch("magma_cycling.config.get_data_config") as mock_dc:
                mock_dc.return_value.data_repo_path = tmp_path
                result = await handle_get_training_statistics(
                    {
                        "start_date": "2026-02-17",
                        "end_date": "2026-02-23",
                        "include_adherence": True,
                    }
                )

        data = json.loads(result[0].text)
        adh = data["adherence"]
        # 100% annulé : cible active = 0, adherence None (pas de crash div/0)
        assert adh["tss_target_active"] == 0
        assert adh["adherence_rate"] is None, (
            "BT-042: semaine 100% annulée → adherence_rate=None " "(protection div/0, pas crash)"
        )

    @pytest.mark.asyncio
    async def test_include_adherence_fallback_source_on_missing_intervals_id(
        self, mock_intervals, tmp_path
    ):
        """BT-042 : session completed sans intervals_id → fallback tss_planned,
        listée dans ``tss_source_map.planned_fallback``. Cas prod récurrent KIN."""
        from magma_cycling.mcp_server import handle_get_training_statistics

        week = {
            "week_id": "S999",
            "start_date": "2026-02-17",
            "end_date": "2026-02-23",
            "tss_target": 50,
            "planned_sessions": [
                {
                    "session_id": "S999-KIN01",
                    "date": "2026-02-18",
                    "name": "KIN",
                    "type": "KIN",
                    "version": "V001",
                    "tss_planned": 0,
                    "duration_min": 30,
                    "description": "Protocole",
                    "status": "completed",
                    "intervals_id": None,  # pas d'ID → fallback planned
                },
            ],
        }
        planning_dir = tmp_path / "week_planning"
        planning_dir.mkdir()
        (planning_dir / "week_planning_S999.json").write_text(json.dumps(week))

        mock_intervals.get_activities.return_value = []
        mock_intervals.get_wellness.return_value = []

        with patch(INTERVALS_PATCH, return_value=mock_intervals):
            with patch("magma_cycling.config.get_data_config") as mock_dc:
                mock_dc.return_value.data_repo_path = tmp_path
                result = await handle_get_training_statistics(
                    {
                        "start_date": "2026-02-17",
                        "end_date": "2026-02-23",
                        "include_adherence": True,
                    }
                )

        data = json.loads(result[0].text)
        adh = data["adherence"]
        assert "S999-KIN01" in adh["tss_source_map"]["planned_fallback"]
        assert "S999-KIN01" not in adh["tss_source_map"]["intervals"]


class TestBT048AdherenceMatchViaPairedEventId:
    """BT-048 : ``_compute_adherence_for_range`` doit indexer ``actual_tss_map``
    par ``paired_event_id`` et non par ``activity.id``.

    Régression prod S100 (2026-06-29 → 2026-07-05, appel Coach AI post
    v3.72.2) : ``tss_source_map.intervals=[]``, tout en ``planned_fallback``
    → ``tss_realized = sum(tss_planned) = 269`` tautologique →
    adherence 100 % par construction. Réel attendu : 348/269 ≈ 129 %
    (activités matchant les 4 sessions completed via ``paired_event_id``).

    Cause : Intervals distingue ``activity.id`` (ex ``"i162682746"``) de
    ``paired_event_id`` (ex ``119167963``, event calendrier planifié). Le
    planning stocke ``intervals_id = paired_event_id``. Indexer par
    ``activity.id`` produit un mismatch systématique.

    Fix : ``actual_tss_map[f"i{paired_event_id}"] = tss``, aligne avec le
    lookup ``f"i{intervals_id}"``. Pattern éprouvé cf.
    ``workflows/sync/activity_tracker.py:67`` et
    ``workflows/sync/activity_detection.py:96``.

    Note historique : les hypothèses BT-046 (double préfixage) puis
    fixture "id == intervals_id" étaient toutes deux fausses — mode
    correction en 2 étapes documenté par ce test.
    """

    @pytest.mark.asyncio
    async def test_prod_paired_event_id_matches_and_uses_actual_tss(self, mock_intervals, tmp_path):
        """Fixture réaliste S100-06 : activity.id ≠ paired_event_id."""
        from magma_cycling.mcp_server import handle_get_training_statistics

        week = {
            "week_id": "S999",
            "start_date": "2026-06-29",
            "end_date": "2026-07-05",
            "tss_target": 300,
            "planned_sessions": [
                {
                    "session_id": "S999-06",
                    "date": "2026-07-04",
                    "name": "Endurance longue",
                    "type": "END",
                    "version": "V001",
                    "tss_planned": 211,
                    "duration_min": 240,
                    "description": "Sortie Les Copains 81km",
                    "status": "completed",
                    # Stocké = paired_event_id de l'activité réalisée
                    "intervals_id": 119167963,
                },
            ],
        }
        planning_dir = tmp_path / "week_planning"
        planning_dir.mkdir()
        (planning_dir / "week_planning_S999.json").write_text(json.dumps(week))

        # Format PROD RÉEL : id activité ≠ paired_event_id
        mock_intervals.get_activities.return_value = [
            {
                "id": "i162682746",  # activity ID (course réalisée)
                "paired_event_id": 119167963,  # event calendrier planifié
                "icu_training_load": 270,
                "moving_time": 14400,
            },
            # Activité non-planifiée (Zwift libre) : peid=None → hors adherence
            {
                "id": "i162680577",
                "paired_event_id": None,
                "icu_training_load": 6,
                "moving_time": 600,
            },
        ]
        mock_intervals.get_wellness.return_value = []

        with patch(INTERVALS_PATCH, return_value=mock_intervals):
            with patch("magma_cycling.config.get_data_config") as mock_dc:
                mock_dc.return_value.data_repo_path = tmp_path
                result = await handle_get_training_statistics(
                    {
                        "start_date": "2026-06-29",
                        "end_date": "2026-07-05",
                        "include_adherence": True,
                    }
                )

        data = json.loads(result[0].text)
        adh = data["adherence"]
        assert adh["tss_realized"] == 270.0, (
            f"BT-048: real Intervals TSS (270 via paired_event_id) attendu, "
            f"got {adh['tss_realized']} — si 211 = mismatch, activity indexé "
            f"par id au lieu de paired_event_id revenu"
        )
        assert "S999-06" in adh["tss_source_map"]["intervals"]
        assert "S999-06" not in adh["tss_source_map"]["planned_fallback"]


class TestBT053MaskDriftWhenTssTargetDesync:
    """BT-053 : ``_compute_adherence_for_range`` masque ``initial`` +
    ``drift`` quand au moins une semaine a ``tss_target=0`` avec somme
    active >0 (désynchro de stockage — semaine non finalisée via
    handshake, cf. BT-051).

    Motif : mieux vaut ne pas répondre que répondre faux. Le drift
    mélangerait dérive de plan et désynchro de stockage.
    """

    @pytest.mark.asyncio
    async def test_desync_masks_initial_and_drift(self, mock_intervals, tmp_path):
        """Semaine désynchronisée détectée → initial=None, drift=None."""
        from magma_cycling.mcp_server import handle_get_training_statistics

        week = {
            "week_id": "S999",
            "start_date": "2026-02-17",
            "end_date": "2026-02-23",
            "tss_target": 0,  # BT-053 : désynchro
            "planned_sessions": [
                {
                    "session_id": "S999-01",
                    "date": "2026-02-18",
                    "name": "Endurance",
                    "type": "END",
                    "version": "V001",
                    "tss_planned": 100,  # active >0 alors stored=0
                    "duration_min": 60,
                    "description": "Endurance Z2",
                    "status": "completed",
                    "intervals_id": 12345,
                },
            ],
        }
        planning_dir = tmp_path / "week_planning"
        planning_dir.mkdir()
        (planning_dir / "week_planning_S999.json").write_text(json.dumps(week))

        mock_intervals.get_activities.return_value = [
            {"id": "i88888", "paired_event_id": 12345, "icu_training_load": 105},
        ]
        mock_intervals.get_wellness.return_value = []

        with patch(INTERVALS_PATCH, return_value=mock_intervals):
            with patch("magma_cycling.config.get_data_config") as mock_dc:
                mock_dc.return_value.data_repo_path = tmp_path
                result = await handle_get_training_statistics(
                    {
                        "start_date": "2026-02-17",
                        "end_date": "2026-02-23",
                        "include_adherence": True,
                    }
                )

        data = json.loads(result[0].text)
        adh = data["adherence"]
        assert adh["tss_target_initial"] is None, "BT-053: initial masqué"
        assert adh["drift_initial_to_active_abs"] is None, "BT-053: drift masqué"
        assert adh["tss_target_active"] == 100, "active reste fiable"
        assert adh["tss_realized"] == 105.0, "realized reste fiable"
        assert adh["adherence_rate"] == 105.0, "rate reste calculable"
        assert "initial_unreliable_reason" in adh
        assert "BT-051" in adh["initial_unreliable_reason"]

    @pytest.mark.asyncio
    async def test_no_desync_keeps_initial_and_drift(self, mock_intervals, tmp_path):
        """Sans désynchro, comportement inchangé (initial + drift présents)."""
        from magma_cycling.mcp_server import handle_get_training_statistics

        week = {
            "week_id": "S999",
            "start_date": "2026-02-17",
            "end_date": "2026-02-23",
            "tss_target": 150,  # stocké cohérent
            "planned_sessions": [
                {
                    "session_id": "S999-01",
                    "date": "2026-02-18",
                    "name": "Endurance",
                    "type": "END",
                    "version": "V001",
                    "tss_planned": 100,
                    "duration_min": 60,
                    "description": "Endurance Z2",
                    "status": "completed",
                    "intervals_id": 12345,
                },
            ],
        }
        planning_dir = tmp_path / "week_planning"
        planning_dir.mkdir()
        (planning_dir / "week_planning_S999.json").write_text(json.dumps(week))

        mock_intervals.get_activities.return_value = [
            {"id": "i88888", "paired_event_id": 12345, "icu_training_load": 105},
        ]
        mock_intervals.get_wellness.return_value = []

        with patch(INTERVALS_PATCH, return_value=mock_intervals):
            with patch("magma_cycling.config.get_data_config") as mock_dc:
                mock_dc.return_value.data_repo_path = tmp_path
                result = await handle_get_training_statistics(
                    {
                        "start_date": "2026-02-17",
                        "end_date": "2026-02-23",
                        "include_adherence": True,
                    }
                )

        data = json.loads(result[0].text)
        adh = data["adherence"]
        assert adh["tss_target_initial"] == 150
        assert adh["drift_initial_to_active_abs"] == 50
        assert "initial_unreliable_reason" not in adh


class TestBT045NoneTssTolerance:
    """BT-045 : ``get-training-statistics`` doit tolérer ``icu_training_load=None``.

    Régression preprod v3.72.0 : activité Intervals sans données puissance/HR
    renvoie ``icu_training_load: None`` (pas absent). ``.get(..., 0)`` ne
    filtre pas ``None`` explicite → ``TypeError: int + NoneType`` sur la
    somme cumulée. Fix : ``(a.get(...) or 0)``.
    """

    @pytest.mark.asyncio
    async def test_activity_with_none_tss_does_not_crash(self, mock_intervals):
        """Une activité avec ``icu_training_load=None`` ne crash pas la somme."""
        from magma_cycling.mcp_server import handle_get_training_statistics

        mock_intervals.get_activities.return_value = [
            {"id": 1, "icu_training_load": 80, "moving_time": 3600, "distance": 30000},
            {"id": 2, "icu_training_load": None, "moving_time": 1800, "distance": 15000},
            {"id": 3, "icu_training_load": 45, "moving_time": 1800, "distance": 15000},
        ]
        mock_intervals.get_wellness.return_value = []
        with patch(INTERVALS_PATCH, return_value=mock_intervals):
            result = await handle_get_training_statistics(
                {"start_date": "2026-08-10", "end_date": "2026-08-17"}
            )
        data = json.loads(result[0].text)
        assert "error" not in data, f"BT-045: doit tolérer None, got {data}"
        assert data["summary"]["total_tss"] == 125.0, "somme 80 + 0 + 45 = 125"


class TestBT047AllAccumulatorsNoneTolerance:
    """BT-047 : audit exhaustif accumulators ``get-training-statistics``.

    BT-045 fixait uniquement ``icu_training_load`` (int). Junior a montré
    que le crash migrait ensuite sur ``float + NoneType`` — les
    accumulators ``moving_time`` et ``distance`` (float après /3600 et
    /1000) sont vulnérables au même pattern. Fix uniforme ``(a.get(...) or 0)``.
    """

    @pytest.mark.asyncio
    async def test_activity_with_all_none_metrics_does_not_crash(self, mock_intervals):
        """Activité avec ``moving_time=None`` **et** ``distance=None`` : pas de crash."""
        from magma_cycling.mcp_server import handle_get_training_statistics

        mock_intervals.get_activities.return_value = [
            {"id": 1, "icu_training_load": 80, "moving_time": 3600, "distance": 30000},
            {"id": 2, "icu_training_load": None, "moving_time": None, "distance": None},
            {"id": 3, "icu_training_load": 45, "moving_time": 1800, "distance": 15000},
        ]
        mock_intervals.get_wellness.return_value = []
        with patch(INTERVALS_PATCH, return_value=mock_intervals):
            result = await handle_get_training_statistics(
                {"start_date": "2026-08-10", "end_date": "2026-08-17"}
            )
        data = json.loads(result[0].text)
        assert "error" not in data, f"BT-047: doit tolérer None sur tous les champs, got {data}"
        summary = data["summary"]
        assert summary["total_tss"] == 125.0, "80 + 0 + 45 = 125"
        # (3600 + 0 + 1800) / 3600 = 1.5 h
        assert summary["total_duration_hours"] == 1.5
        # (30000 + 0 + 15000) / 1000 = 45.0 km
        assert summary["total_distance_km"] == 45.0


# =======================
# TestHandleExportWeekToJson
# =======================


class TestHandleExportWeekToJson:
    @pytest.mark.asyncio
    async def test_exception_returns_error(self, mock_tower):
        from magma_cycling.mcp_server import handle_export_week_to_json

        mock_tower.read_week.side_effect = RuntimeError("boom")
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_export_week_to_json({"week_id": "S081"})
        data = json.loads(result[0].text)
        assert "error" in data


# =======================
# TestHandleRestoreWeekFromBackup
# =======================


class TestHandleRestoreWeekFromBackup:
    @pytest.mark.asyncio
    async def test_no_confirm_returns_error(self):
        from magma_cycling.mcp_server import handle_restore_week_from_backup

        result = await handle_restore_week_from_backup(
            {
                "week_id": "S081",
                "backup_path": "/tmp/backup.json",
            }
        )
        data = json.loads(result[0].text)
        assert "error" in data
        assert "confirm" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_no_confirm_explicit_false(self):
        from magma_cycling.mcp_server import handle_restore_week_from_backup

        result = await handle_restore_week_from_backup(
            {
                "week_id": "S081",
                "backup_path": "/tmp/backup.json",
                "confirm": False,
            }
        )
        data = json.loads(result[0].text)
        assert "error" in data


# =======================
# TestHandleReloadServer
# =======================


class TestHandleReloadServer:
    @pytest.fixture(autouse=True)
    def preserve_planning_tower(self):
        """Preserve planning_tower state across reload tests.

        handle_reload_server calls importlib.reload on control_tower,
        weekly_planner, and daily_sync. This recreates the planning_tower
        singleton and re-imports it in reloaded modules, creating
        desynchronized references. We must restore the original singleton
        in ALL affected modules so later tests work correctly.
        """
        import sys

        from magma_cycling.planning import control_tower as ct_module

        original_tower = ct_module.planning_tower

        # Collect all modules that hold a planning_tower reference
        modules_with_tower = []
        for mod_name, mod in sys.modules.items():
            if mod and hasattr(mod, "planning_tower") and mod is not ct_module:
                modules_with_tower.append((mod_name, mod))

        yield

        # Restore the original singleton in control_tower
        ct_module.planning_tower = original_tower
        # Restore in all modules that may have been reloaded with a new reference
        for mod_name, mod in modules_with_tower:
            if hasattr(mod, "planning_tower"):
                mod.planning_tower = original_tower

    @pytest.mark.asyncio
    async def test_success_reloads_modules(self):
        from magma_cycling.mcp_server import handle_reload_server

        result = await handle_reload_server({})
        data = json.loads(result[0].text)
        assert "reloaded_count" in data
        assert "reloaded_modules" in data
        assert "failed" in data

    @pytest.mark.asyncio
    async def test_returns_note_about_handlers(self):
        from magma_cycling.mcp_server import handle_reload_server

        result = await handle_reload_server({})
        data = json.loads(result[0].text)
        assert "note" in data


# =======================
# TestHandleHealthAuthStatus
# =======================


class TestHandleHealthAuthStatus:
    @pytest.mark.asyncio
    async def test_not_configured(self):
        from magma_cycling.mcp_server import handle_health_auth_status

        mock_config = Mock()
        mock_config.is_configured.return_value = False
        mock_config.has_valid_credentials.return_value = False
        with patch("magma_cycling.config.get_withings_config", return_value=mock_config):
            result = await handle_health_auth_status({})
        data = json.loads(result[0].text)
        assert data["configured"] is False
        assert "message" in data

    @pytest.mark.asyncio
    async def test_configured_but_no_credentials(self):
        from magma_cycling.mcp_server import handle_health_auth_status

        mock_config = Mock()
        mock_config.is_configured.return_value = True
        mock_config.has_valid_credentials.return_value = False
        with patch("magma_cycling.config.get_withings_config", return_value=mock_config):
            result = await handle_health_auth_status({})
        data = json.loads(result[0].text)
        assert data["configured"] is True
        assert data["has_credentials"] is False

    @pytest.mark.asyncio
    async def test_fully_authenticated(self):
        from magma_cycling.mcp_server import handle_health_auth_status

        mock_config = Mock()
        mock_config.is_configured.return_value = True
        mock_config.has_valid_credentials.return_value = True
        mock_config.credentials_path = Path("/tmp/withings.json")
        with patch("magma_cycling.config.get_withings_config", return_value=mock_config):
            result = await handle_health_auth_status({})
        data = json.loads(result[0].text)
        assert data["configured"] is True
        assert data["has_credentials"] is True
        assert "message" in data


# =======================
# TestHandleHealthAuthorize
# =======================


class TestHandleHealthAuthorize:
    @pytest.mark.asyncio
    async def test_no_code_returns_auth_url(self):
        from magma_cycling.mcp_server import handle_health_authorize

        mock_client = Mock()
        mock_client.get_authorization_url.return_value = (
            "https://account.withings.com/oauth2_user/authorize2?..."
        )
        with patch("magma_cycling.config.create_withings_client", return_value=mock_client):
            result = await handle_health_authorize({})
        data = json.loads(result[0].text)
        assert data["step"] == "authorization_required"
        assert "authorization_url" in data
        assert "instructions" in data

    @pytest.mark.asyncio
    async def test_no_code_passes_csrf_state_to_client(self):
        """Withings exige le param `state` (anti-CSRF) — handler doit le générer.

        Sans `state`, Withings répond `invalid_request — The state parameter is
        required` au callback. Régression observée 2026-05-08 lors d'un
        re-OAuth bundle local.
        """
        from magma_cycling.mcp_server import handle_health_authorize

        mock_client = Mock()
        mock_client.get_authorization_url.return_value = "https://account.withings.com/...&state=x"

        with patch("magma_cycling.config.create_withings_client", return_value=mock_client):
            await handle_health_authorize({})
            await handle_health_authorize({})

        assert mock_client.get_authorization_url.call_count == 2
        states = [
            call.kwargs.get("state") for call in mock_client.get_authorization_url.call_args_list
        ]
        assert all(states), "state must be passed to get_authorization_url"
        assert states[0] != states[1], "state must be a fresh random nonce per call"
        for s in states:
            assert isinstance(s, str) and len(s) >= 16, "state must be a non-trivial string"

    @pytest.mark.asyncio
    async def test_with_code_exchanges_successfully(self):
        from magma_cycling.mcp_server import handle_health_authorize

        mock_client = Mock()
        mock_client.exchange_code.return_value = {"user_id": "12345", "access_token": "tok"}
        with patch("magma_cycling.config.create_withings_client", return_value=mock_client):
            result = await handle_health_authorize({"authorization_code": "authcode123"})
        data = json.loads(result[0].text)
        assert data["step"] == "authorization_complete"
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_with_code_exchange_failure(self):
        from magma_cycling.mcp_server import handle_health_authorize

        mock_client = Mock()
        mock_client.exchange_code.side_effect = RuntimeError("invalid code")
        with patch("magma_cycling.config.create_withings_client", return_value=mock_client):
            result = await handle_health_authorize({"authorization_code": "badcode"})
        data = json.loads(result[0].text)
        assert data["step"] == "authorization_failed"
        assert data["status"] == "error"


# =======================
# TestHandleAnalyzeHealthTrends
# =======================


class TestHandleAnalyzeHealthTrends:
    @pytest.mark.asyncio
    async def test_week_period_no_data(self):
        from magma_cycling.mcp_server import handle_analyze_health_trends

        mock_provider = _mock_health_provider()
        mock_provider.get_sleep_range.return_value = []
        mock_provider.get_body_composition_range.return_value = []
        with patch("magma_cycling.health.create_health_provider", return_value=mock_provider):
            result = await handle_analyze_health_trends({"period": "week"})
        data = json.loads(result[0].text)
        assert data["period"] == "week"
        assert data["sleep_analysis"]["total_nights"] == 0

    @pytest.mark.asyncio
    async def test_month_period(self):
        from magma_cycling.mcp_server import handle_analyze_health_trends
        from magma_cycling.models.withings_models import SleepData, WeightMeasurement

        mock_provider = _mock_health_provider()
        mock_provider.get_sleep_range.return_value = [
            SleepData(
                date=date(2026, 2, 1),
                start_datetime=datetime(2026, 1, 31, 23, 0),
                end_datetime=datetime(2026, 2, 1, 6, 30),
                total_sleep_hours=7.5,
                sleep_score=85,
                wakeup_count=1,
            ),
            SleepData(
                date=date(2026, 2, 2),
                start_datetime=datetime(2026, 2, 1, 23, 0),
                end_datetime=datetime(2026, 2, 2, 7, 0),
                total_sleep_hours=8.0,
                sleep_score=90,
                wakeup_count=0,
            ),
        ]
        mock_provider.get_body_composition_range.return_value = [
            WeightMeasurement(
                date=date(2026, 2, 1), datetime=datetime(2026, 2, 1, 8, 0), weight_kg=72.5
            ),
            WeightMeasurement(
                date=date(2026, 2, 2), datetime=datetime(2026, 2, 2, 8, 0), weight_kg=72.0
            ),
        ]
        with patch("magma_cycling.health.create_health_provider", return_value=mock_provider):
            result = await handle_analyze_health_trends({"period": "month"})
        data = json.loads(result[0].text)
        assert data["period"] == "month"
        assert data["sleep_analysis"]["total_nights"] == 2

    @pytest.mark.asyncio
    async def test_custom_period_missing_dates_returns_error(self):
        from magma_cycling.mcp_server import handle_analyze_health_trends

        mock_provider = _mock_health_provider()
        with patch("magma_cycling.health.create_health_provider", return_value=mock_provider):
            result = await handle_analyze_health_trends({"period": "custom"})
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_custom_period_with_dates(self):
        from magma_cycling.mcp_server import handle_analyze_health_trends

        mock_provider = _mock_health_provider()
        mock_provider.get_sleep_range.return_value = []
        mock_provider.get_body_composition_range.return_value = []
        with patch("magma_cycling.health.create_health_provider", return_value=mock_provider):
            result = await handle_analyze_health_trends(
                {
                    "period": "custom",
                    "start_date": "2026-02-01",
                    "end_date": "2026-02-28",
                }
            )
        data = json.loads(result[0].text)
        assert data["period"] == "custom"


# =======================
# TestHandleRenameSession
# =======================


class TestHandleRenameSession:
    @pytest.mark.asyncio
    async def test_rename_success(self, mock_tower, mock_session):
        from magma_cycling.mcp_server import handle_rename_session

        args = {
            "week_id": "S081",
            "session_id": "S081-03",
            "new_session_id": "S081-03a",
        }
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_rename_session(args)
        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert data["old_session_id"] == "S081-03"
        assert data["new_session_id"] == "S081-03a"
        assert mock_session.session_id == "S081-03a"
        assert data["remote_updated"] is False

    @pytest.mark.asyncio
    async def test_rename_with_remote_sync(self, mock_session):
        from magma_cycling.mcp_server import handle_rename_session

        mock_session.intervals_id = "evt456"
        plan = Mock()
        plan.planned_sessions = [mock_session]
        tower = make_tower(plan)

        mock_client = Mock()
        mock_client.update_event.return_value = True

        args = {
            "week_id": "S081",
            "session_id": "S081-03",
            "new_session_id": "S081-03b",
        }
        with patch(TOWER_PATCH, tower), patch(INTERVALS_PATCH, return_value=mock_client):
            result = await handle_rename_session(args)
        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert data["remote_updated"] is True
        mock_client.update_event.assert_called_once()
        call_args = mock_client.update_event.call_args
        assert call_args[0][0] == "evt456"
        assert "S081-03b-INT-TempoCourt-V001" in call_args[0][1]["name"]
        assert "15:00:00" in call_args[0][1]["start_date_local"]

    @pytest.mark.asyncio
    async def test_rename_completed_raises(self, mock_tower, mock_session):
        from magma_cycling.mcp_server import handle_rename_session

        mock_session.status = "completed"
        args = {
            "week_id": "S081",
            "session_id": "S081-03",
            "new_session_id": "S081-03a",
        }
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_rename_session(args)
        data = json.loads(result[0].text)
        assert "error" in data
        assert "completed" in data["error"]

    @pytest.mark.asyncio
    async def test_rename_duplicate_raises(self, mock_session, mock_session2):
        from magma_cycling.mcp_server import handle_rename_session

        plan = Mock()
        plan.planned_sessions = [mock_session, mock_session2]
        tower = make_tower(plan)

        args = {
            "week_id": "S081",
            "session_id": "S081-03",
            "new_session_id": "S081-06",
        }
        with patch(TOWER_PATCH, tower):
            result = await handle_rename_session(args)
        data = json.loads(result[0].text)
        assert "error" in data
        assert "already exists" in data["error"]

    @pytest.mark.asyncio
    async def test_rename_invalid_format(self):
        from magma_cycling.mcp_server import handle_rename_session

        args = {
            "week_id": "S081",
            "session_id": "S081-03",
            "new_session_id": "S081-ABC",
        }
        result = await handle_rename_session(args)
        data = json.loads(result[0].text)
        assert "error" in data
        assert "Invalid session_id format" in data["error"]

    @pytest.mark.asyncio
    async def test_rename_cross_week_rejected(self):
        from magma_cycling.mcp_server import handle_rename_session

        args = {
            "week_id": "S081",
            "session_id": "S081-03",
            "new_session_id": "S082-03",
        }
        result = await handle_rename_session(args)
        data = json.loads(result[0].text)
        assert "error" in data
        assert "Cannot rename across weeks" in data["error"]

    @pytest.mark.asyncio
    async def test_rename_session_not_found(self, mock_tower):
        from magma_cycling.mcp_server import handle_rename_session

        args = {
            "week_id": "S081",
            "session_id": "S081-99",
            "new_session_id": "S081-99a",
        }
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_rename_session(args)
        data = json.loads(result[0].text)
        assert "error" in data
        assert "not found" in data["error"]


# =======================
# TestHandleEnrichSessionHealth
# =======================


class TestHandleEnrichSessionHealth:
    """Tests for enrich-session-health handler (session.date → session.session_date fix)."""

    @pytest.fixture
    def mock_tower(self):
        from magma_cycling.planning.models import Session, WeeklyPlan

        session = Session(
            session_id="S082-03",
            session_date=date(2026, 2, 25),
            name="SweetSpotBlocs",
            session_type="INT",
            tss_planned=80,
            duration_min=75,
            description="SweetSpot intervals",
            status="planned",
        )
        plan = Mock(spec=WeeklyPlan)
        plan.planned_sessions = [session]

        tower = MagicMock()
        tower.modify_week.return_value.__enter__ = Mock(return_value=plan)
        tower.modify_week.return_value.__exit__ = Mock(return_value=False)
        return tower

    @pytest.mark.asyncio
    async def test_enrich_session_success(self, mock_tower):
        """Enrich session accesses session.session_date without AttributeError."""
        from magma_cycling.mcp_server import handle_enrich_session_health
        from magma_cycling.models.withings_models import (
            SleepData,
            TrainingReadiness,
            WeightMeasurement,
        )

        mock_provider = _mock_health_provider()
        mock_provider.get_sleep_range.return_value = [
            SleepData(
                date=date(2026, 2, 25),
                start_datetime=datetime(2026, 2, 24, 23, 0),
                end_datetime=datetime(2026, 2, 25, 6, 30),
                total_sleep_hours=7.5,
                sleep_score=82,
                deep_sleep_minutes=90,
                wakeup_count=1,
            ),
        ]
        mock_provider.get_body_composition.return_value = WeightMeasurement(
            date=date(2026, 2, 25),
            datetime=datetime(2026, 2, 25, 8, 0),
            weight_kg=84.2,
        )
        mock_provider.get_readiness.return_value = TrainingReadiness(
            date=date(2026, 2, 25),
            sleep_hours=7.5,
            ready_for_intense=True,
            recommended_intensity="all_systems_go",
            veto_reasons=[],
            recommendations=[],
        )

        with (
            patch(TOWER_PATCH, mock_tower),
            patch(
                "magma_cycling.health.create_health_provider",
                return_value=mock_provider,
            ),
        ):
            result = await handle_enrich_session_health(
                {
                    "week_id": "S082",
                    "session_id": "S082-03",
                    "auto_readiness_check": True,
                }
            )

        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert data["session_date"] == "2026-02-25"
        assert data["health_metrics_added"]["sleep_hours"] == 7.5
        assert data["health_metrics_added"]["weight_kg"] == 84.2

    @pytest.mark.asyncio
    async def test_enrich_session_not_found(self, mock_tower):
        """Returns error when session not found."""
        from magma_cycling.mcp_server import handle_enrich_session_health

        mock_provider = _mock_health_provider()

        with (
            patch(TOWER_PATCH, mock_tower),
            patch(
                "magma_cycling.health.create_health_provider",
                return_value=mock_provider,
            ),
        ):
            result = await handle_enrich_session_health(
                {"week_id": "S082", "session_id": "S082-99"}
            )

        data = json.loads(result[0].text)
        assert data["status"] == "error"
        assert "not found" in data["error"]

    @pytest.mark.asyncio
    async def test_enrich_session_syncs_to_calendar(self, mock_tower):
        """Default sync_to_calendar=True triggers sync_health_to_calendar."""
        from magma_cycling.mcp_server import handle_enrich_session_health
        from magma_cycling.models.withings_models import SleepData, WeightMeasurement

        mock_provider = _mock_health_provider()
        mock_provider.get_sleep_range.return_value = [
            SleepData(
                date=date(2026, 2, 25),
                start_datetime=datetime(2026, 2, 24, 23, 0),
                end_datetime=datetime(2026, 2, 25, 6, 30),
                total_sleep_hours=7.5,
                sleep_score=82,
                deep_sleep_minutes=90,
                wakeup_count=1,
            ),
        ]
        mock_provider.get_body_composition.return_value = WeightMeasurement(
            date=date(2026, 2, 25),
            datetime=datetime(2026, 2, 25, 8, 0),
            weight_kg=84.2,
        )
        mock_provider.get_readiness.return_value = None

        mock_sync = Mock(return_value={"synced_dates": ["2026-02-25"], "errors": []})

        with (
            patch(TOWER_PATCH, mock_tower),
            patch(HEALTH_PROVIDER_PATCH, return_value=mock_provider),
            patch(
                "magma_cycling._mcp.handlers.health.sync_health_to_calendar",
                mock_sync,
            ),
        ):
            result = await handle_enrich_session_health(
                {"week_id": "S082", "session_id": "S082-03"}
            )

        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert data["calendar_sync"]["synced"] is True
        assert "2026-02-25" in data["calendar_sync"]["synced_dates"]
        mock_sync.assert_called_once_with(
            start_date=date(2026, 2, 25),
            end_date=date(2026, 2, 25),
            data_types=["sleep", "weight"],
        )

    @pytest.mark.asyncio
    async def test_enrich_session_skip_calendar_sync(self, mock_tower):
        """sync_to_calendar=False skips calendar push."""
        from magma_cycling.mcp_server import handle_enrich_session_health
        from magma_cycling.models.withings_models import SleepData, WeightMeasurement

        mock_provider = _mock_health_provider()
        mock_provider.get_sleep_range.return_value = [
            SleepData(
                date=date(2026, 2, 25),
                start_datetime=datetime(2026, 2, 24, 23, 0),
                end_datetime=datetime(2026, 2, 25, 6, 30),
                total_sleep_hours=7.5,
                sleep_score=82,
                deep_sleep_minutes=90,
                wakeup_count=1,
            ),
        ]
        mock_provider.get_body_composition.return_value = WeightMeasurement(
            date=date(2026, 2, 25),
            datetime=datetime(2026, 2, 25, 8, 0),
            weight_kg=84.2,
        )
        mock_provider.get_readiness.return_value = None

        mock_sync = Mock()

        with (
            patch(TOWER_PATCH, mock_tower),
            patch(HEALTH_PROVIDER_PATCH, return_value=mock_provider),
            patch(
                "magma_cycling._mcp.handlers.health.sync_health_to_calendar",
                mock_sync,
            ),
        ):
            result = await handle_enrich_session_health(
                {
                    "week_id": "S082",
                    "session_id": "S082-03",
                    "sync_to_calendar": False,
                }
            )

        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert "calendar_sync" not in data
        mock_sync.assert_not_called()

    @pytest.mark.asyncio
    async def test_enrich_session_calendar_sync_error_non_blocking(self, mock_tower):
        """Calendar sync failure does not block enrichment success."""
        from magma_cycling.mcp_server import handle_enrich_session_health
        from magma_cycling.models.withings_models import SleepData, WeightMeasurement

        mock_provider = _mock_health_provider()
        mock_provider.get_sleep_range.return_value = [
            SleepData(
                date=date(2026, 2, 25),
                start_datetime=datetime(2026, 2, 24, 23, 0),
                end_datetime=datetime(2026, 2, 25, 6, 30),
                total_sleep_hours=7.5,
                sleep_score=82,
                deep_sleep_minutes=90,
                wakeup_count=1,
            ),
        ]
        mock_provider.get_body_composition.return_value = WeightMeasurement(
            date=date(2026, 2, 25),
            datetime=datetime(2026, 2, 25, 8, 0),
            weight_kg=84.2,
        )
        mock_provider.get_readiness.return_value = None

        mock_sync = Mock(side_effect=ConnectionError("API unreachable"))

        with (
            patch(TOWER_PATCH, mock_tower),
            patch(HEALTH_PROVIDER_PATCH, return_value=mock_provider),
            patch(
                "magma_cycling._mcp.handlers.health.sync_health_to_calendar",
                mock_sync,
            ),
        ):
            result = await handle_enrich_session_health(
                {"week_id": "S082", "session_id": "S082-03"}
            )

        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert data["calendar_sync"]["synced"] is False
        assert "API unreachable" in data["calendar_sync"]["error"]


class TestBT051FinalizeWeekPlanning:
    """BT-051 : handshake ``finalize-week-planning`` — write-once
    ``tss_target_initial``. Spec Coach AI 2026-08-17.

    Préconditions testées :
    - Semaine existe (file present)
    - Pas déjà finalisée (idempotence via ``finalized_at``)
    - Au moins une session active
    - Somme active > 0

    Effet testé :
    - Écrit ``tss_target_initial`` = sum(active)
    - Écrit ``tss_target_current`` = même valeur
    - Écrit ``finalized_at`` = now
    """

    def _plan(self, sessions=None, **overrides):
        from magma_cycling.planning.models import WeeklyPlan

        defaults = dict(
            week_id="S108",
            start_date=date(2026, 8, 24),
            end_date=date(2026, 8, 30),
            created_at=datetime(2026, 8, 24, 12, 0),
            last_updated=datetime(2026, 8, 24, 12, 0),
            version=1,
            athlete_id="iXXXXXX",
        )
        defaults.update(overrides)
        if sessions is not None:
            defaults["planned_sessions"] = sessions
        return WeeklyPlan(**defaults)

    def _active_session(self, session_id="S108-01", tss=100, status="completed"):
        from magma_cycling.planning.models import Session

        kwargs = dict(
            session_id=session_id,
            date=date(2026, 8, 24),
            name="Endurance",
            type="END",
            version="V001",
            tss_planned=tss,
            duration_min=60,
            description="test",
            status=status,
        )
        if status == "skipped":
            kwargs["skip_reason"] = "test"
        return Session(**kwargs)

    @pytest.mark.asyncio
    async def test_success_writes_initial_current_and_finalized_at(self, mock_tower):
        """Happy path : sessions actives, initial>0, pas encore finalisée."""
        from magma_cycling.mcp_server import handle_finalize_week_planning

        sessions = [
            self._active_session("S108-01", tss=100),
            self._active_session("S108-02", tss=80, status="planned"),
        ]
        plan = self._plan(sessions=sessions)
        mock_tower.read_week.return_value = plan

        # Context manager mock (modify_week)
        from contextlib import contextmanager

        modified_plan = self._plan(sessions=sessions)

        @contextmanager
        def _modify_ctx(*args, **kwargs):
            yield modified_plan

        mock_tower.modify_week = _modify_ctx

        with patch(TOWER_PATCH, mock_tower):
            result = await handle_finalize_week_planning({"week_id": "S108"})

        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert data["week_id"] == "S108"
        assert data["tss_target_initial"] == 180  # 100 + 80
        assert data["tss_target_current"] == 180
        assert data["active_sessions_count"] == 2
        assert "finalized_at" in data
        # Le plan modifié dans le context manager doit avoir les valeurs
        assert modified_plan.tss_target_initial == 180
        assert modified_plan.tss_target_current == 180
        assert modified_plan.finalized_at is not None

    @pytest.mark.asyncio
    async def test_refuses_if_already_finalized(self, mock_tower):
        """Idempotence : second appel refusé avec message explicite."""
        from magma_cycling.mcp_server import handle_finalize_week_planning

        already_finalized_at = datetime(2026, 8, 17, 10, 0)
        plan = self._plan(
            sessions=[self._active_session("S108-01", tss=100)],
            tss_target_initial=100,
            tss_target_current=100,
            finalized_at=already_finalized_at,
        )
        mock_tower.read_week.return_value = plan

        with patch(TOWER_PATCH, mock_tower):
            result = await handle_finalize_week_planning({"week_id": "S108"})

        data = json.loads(result[0].text)
        assert "error" in data
        assert "already finalized" in data["error"].lower()
        assert data["tss_target_initial"] == 100
        assert data["finalized_at"] == already_finalized_at.isoformat()
        assert "hint" in data
        # modify_week ne doit PAS avoir été appelé
        mock_tower.modify_week.assert_not_called()

    @pytest.mark.asyncio
    async def test_refuses_if_no_active_sessions(self, mock_tower):
        """Semaine 100% annulée → refus."""
        from magma_cycling.mcp_server import handle_finalize_week_planning

        sessions = [
            self._active_session("S108-01", tss=100, status="skipped"),
            self._active_session("S108-02", tss=80, status="rest_day"),
        ]
        plan = self._plan(sessions=sessions)
        mock_tower.read_week.return_value = plan

        with patch(TOWER_PATCH, mock_tower):
            result = await handle_finalize_week_planning({"week_id": "S108"})

        data = json.loads(result[0].text)
        assert "error" in data
        assert "no active sessions" in data["error"].lower()
        mock_tower.modify_week.assert_not_called()

    @pytest.mark.asyncio
    async def test_refuses_if_all_active_zero(self, mock_tower):
        """Sessions actives avec tss_planned=0 partout → refus."""
        from magma_cycling.mcp_server import handle_finalize_week_planning

        sessions = [
            self._active_session("S108-01", tss=0),
            self._active_session("S108-02", tss=0, status="planned"),
        ]
        plan = self._plan(sessions=sessions)
        mock_tower.read_week.return_value = plan

        with patch(TOWER_PATCH, mock_tower):
            result = await handle_finalize_week_planning({"week_id": "S108"})

        data = json.loads(result[0].text)
        assert "error" in data
        assert "tss_planned=0" in data["error"] or "zero intention" in data["error"]
        mock_tower.modify_week.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_error_on_file_not_found(self, mock_tower):
        """Semaine inexistante → error clair."""
        from magma_cycling.mcp_server import handle_finalize_week_planning

        mock_tower.read_week.side_effect = FileNotFoundError("Planning file not found")

        with patch(TOWER_PATCH, mock_tower):
            result = await handle_finalize_week_planning({"week_id": "S999"})

        data = json.loads(result[0].text)
        assert "error" in data
        assert "not found" in data["error"].lower()
        assert data["week_id"] == "S999"
