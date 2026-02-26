"""
Tests for additional MCP handlers — Sprint R14 Phase 0 coverage.

Targets: mcp_server.py 20% → 60%
Strategy: Test handlers directly with mocked dependencies.
"""

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

pytest_plugins = ("pytest_asyncio",)

# Common patch paths
TOWER_PATCH = "cyclisme_training_logs.planning.control_tower.planning_tower"
INTERVALS_PATCH = "cyclisme_training_logs.config.create_intervals_client"
DATA_CONFIG_PATCH = "cyclisme_training_logs.config.get_data_config"


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
    s.planned_duration = 60
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
    s.planned_tss = 80
    s.duration_min = 90
    s.planned_duration = 90
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
    return client


# =======================
# TestHandleListWeeks
# =======================


class TestHandleListWeeks:
    @pytest.mark.asyncio
    async def test_empty_dir_returns_zero_weeks(self, tmp_path):
        from cyclisme_training_logs.mcp_server import handle_list_weeks

        mc = Mock()
        mc.week_planning_dir = tmp_path
        with patch(DATA_CONFIG_PATCH, return_value=mc):
            result = await handle_list_weeks({"limit": 10})
        data = json.loads(result[0].text)
        assert data["total_found"] == 0
        assert data["weeks"] == []

    @pytest.mark.asyncio
    async def test_with_planning_file(self, tmp_path):
        from cyclisme_training_logs.mcp_server import handle_list_weeks

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
        from cyclisme_training_logs.mcp_server import handle_list_weeks

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
        from cyclisme_training_logs.mcp_server import handle_list_weeks

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
        from cyclisme_training_logs.mcp_server import handle_get_week_details

        with patch(TOWER_PATCH, mock_tower):
            result = await handle_get_week_details({"week_id": "S081"})
        data = json.loads(result[0].text)
        assert data["week_id"] == "S081"
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["session_id"] == "S081-03"

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self, mock_tower):
        from cyclisme_training_logs.mcp_server import handle_get_week_details

        mock_tower.read_week.side_effect = FileNotFoundError("not found")
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_get_week_details({"week_id": "S099"})
        data = json.loads(result[0].text)
        assert "error" in data
        assert "S099" in data["error"]

    @pytest.mark.asyncio
    async def test_generic_exception_returns_error(self, mock_tower):
        from cyclisme_training_logs.mcp_server import handle_get_week_details

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
        from cyclisme_training_logs.mcp_server import handle_modify_session_details

        args = {"week_id": "S081", "session_id": "S081-03", "name": "NewName", "tss_planned": 70}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_modify_session_details(args)
        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert "name=NewName" in data["modifications"]

    @pytest.mark.asyncio
    async def test_no_changes_still_succeeds(self, mock_tower):
        from cyclisme_training_logs.mcp_server import handle_modify_session_details

        args = {"week_id": "S081", "session_id": "S081-03"}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_modify_session_details(args)
        data = json.loads(result[0].text)
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_session_not_found_returns_value_error(self, mock_tower):
        from cyclisme_training_logs.mcp_server import handle_modify_session_details

        args = {"week_id": "S081", "session_id": "S081-99"}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_modify_session_details(args)
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self, mock_tower):
        from cyclisme_training_logs.mcp_server import handle_modify_session_details

        mock_tower.modify_week.side_effect = FileNotFoundError("not found")
        args = {"week_id": "S099", "session_id": "S099-01"}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_modify_session_details(args)
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_generic_exception_returns_error(self, mock_tower):
        from cyclisme_training_logs.mcp_server import handle_modify_session_details

        mock_tower.modify_week.side_effect = RuntimeError("boom")
        args = {"week_id": "S081", "session_id": "S081-03"}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_modify_session_details(args)
        data = json.loads(result[0].text)
        assert "error" in data


# =======================
# TestHandleCreateSession
# =======================


class TestHandleCreateSession:
    @pytest.mark.asyncio
    async def test_success_creates_session(self, mock_tower, mock_plan):
        from cyclisme_training_logs.mcp_server import handle_create_session

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
        from cyclisme_training_logs.mcp_server import handle_create_session

        # Saturday = day_index 6
        args = {"week_id": "S081", "session_date": "2026-02-21"}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_create_session(args)
        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert data["name"] == "NewSession"

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self, mock_tower):
        from cyclisme_training_logs.mcp_server import handle_create_session

        mock_tower.modify_week.side_effect = FileNotFoundError("not found")
        args = {"week_id": "S099", "session_date": "2026-02-19"}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_create_session(args)
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_double_session_gets_letter_suffix(self, mock_tower, mock_plan, mock_session):
        """When there's already a session on the same date, new one gets 'a' suffix."""
        from cyclisme_training_logs.mcp_server import handle_create_session

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


# =======================
# TestHandleDeleteSession
# =======================


class TestHandleDeleteSession:
    @pytest.mark.asyncio
    async def test_success_deletes_session(self, mock_tower, mock_session, mock_plan):
        from cyclisme_training_logs.mcp_server import handle_delete_session

        args = {"week_id": "S081", "session_id": "S081-03"}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_delete_session(args)
        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert data["session_id"] == "S081-03"

    @pytest.mark.asyncio
    async def test_completed_session_raises_value_error(self, mock_plan, mock_session):
        from cyclisme_training_logs.mcp_server import handle_delete_session

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
        from cyclisme_training_logs.mcp_server import handle_delete_session

        mock_session.intervals_id = 12345
        tower = make_tower(mock_plan)
        args = {"week_id": "S081", "session_id": "S081-03"}
        with patch(TOWER_PATCH, tower):
            result = await handle_delete_session(args)
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_session_not_found_returns_error(self, mock_tower):
        from cyclisme_training_logs.mcp_server import handle_delete_session

        args = {"week_id": "S081", "session_id": "S081-99"}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_delete_session(args)
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self, mock_tower):
        from cyclisme_training_logs.mcp_server import handle_delete_session

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
        from cyclisme_training_logs.mcp_server import handle_duplicate_session

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
        from cyclisme_training_logs.mcp_server import handle_duplicate_session

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
        from cyclisme_training_logs.mcp_server import handle_duplicate_session

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
        from cyclisme_training_logs.mcp_server import handle_swap_sessions

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
        from cyclisme_training_logs.mcp_server import handle_swap_sessions

        args = {"week_id": "S081", "session_id_1": "S081-99", "session_id_2": "S081-03"}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_swap_sessions(args)
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_completed_session_blocked(self, mock_plan, mock_session, mock_session2):
        from cyclisme_training_logs.mcp_server import handle_swap_sessions

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
        from cyclisme_training_logs.mcp_server import handle_swap_sessions

        mock_tower.modify_week.side_effect = FileNotFoundError("not found")
        args = {"week_id": "S099", "session_id_1": "S099-01", "session_id_2": "S099-02"}
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_swap_sessions(args)
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_swap_updates_remote_events(self, mock_plan, mock_session, mock_session2):
        """Enhancement: swap updates remote events when both sessions have intervals_id."""
        from cyclisme_training_logs.mcp_server import handle_swap_sessions

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
        # Both remote events should have been updated
        assert mock_client.update_event.call_count == 2

    @pytest.mark.asyncio
    async def test_swap_no_remote_update_without_intervals_ids(
        self, mock_plan, mock_session, mock_session2
    ):
        """No remote update when sessions lack intervals_id."""
        from cyclisme_training_logs.mcp_server import handle_swap_sessions

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
        from cyclisme_training_logs.mcp_server import handle_attach_workout

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
        from cyclisme_training_logs.mcp_server import handle_attach_workout

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
        from cyclisme_training_logs.mcp_server import handle_get_workout

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

        with patch(DATA_CONFIG_PATCH, return_value=mc), patch(TOWER_PATCH, tower_mock):
            result = await handle_get_workout({"session_id": "S081-03"})
        data = json.loads(result[0].text)
        assert data["found"] is False
        assert data["structured_file"] is None
        assert data["session_definition"]["name"] == "EnduranceBase"
        assert data["session_definition"]["description"] == "2h endurance Z2"
        assert data["session_definition"]["tss_planned"] == 80

    @pytest.mark.asyncio
    async def test_workout_found_returns_content(self, tmp_path):
        from cyclisme_training_logs.mcp_server import handle_get_workout

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
        from cyclisme_training_logs.mcp_server import handle_validate_workout

        mock_validator = Mock()
        mock_validator.validate_workout.return_value = (True, [], [])

        with patch(
            "cyclisme_training_logs.intervals_format_validator.IntervalsFormatValidator",
            return_value=mock_validator,
        ):
            result = await handle_validate_workout({"workout_text": "valid workout text"})
        data = json.loads(result[0].text)
        assert data["valid"] is True
        assert data["errors"] == []

    @pytest.mark.asyncio
    async def test_invalid_workout_with_auto_fix(self):
        from cyclisme_training_logs.mcp_server import handle_validate_workout

        mock_validator = Mock()
        mock_validator.validate_workout.side_effect = [
            (False, ["error1"], ["warn1"]),
            (True, [], []),
        ]
        mock_validator.fix_repetition_format.return_value = "fixed workout text"

        with patch(
            "cyclisme_training_logs.intervals_format_validator.IntervalsFormatValidator",
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
        from cyclisme_training_logs.mcp_server import handle_validate_workout

        mock_validator = Mock()
        mock_validator.validate_workout.return_value = (False, ["bad format"], [])

        with patch(
            "cyclisme_training_logs.intervals_format_validator.IntervalsFormatValidator",
            return_value=mock_validator,
        ):
            result = await handle_validate_workout({"workout_text": "bad workout"})
        data = json.loads(result[0].text)
        assert data["valid"] is False
        assert data["auto_fixed"] is False


# =======================
# TestHandleDeleteRemoteSession
# =======================


class TestHandleDeleteRemoteSession:
    @pytest.mark.asyncio
    async def test_no_confirm_returns_error(self):
        from cyclisme_training_logs.mcp_server import handle_delete_remote_session

        result = await handle_delete_remote_session({"event_id": "evt123"})
        data = json.loads(result[0].text)
        assert "error" in data
        assert "confirmation" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_no_confirm_explicit_false(self):
        from cyclisme_training_logs.mcp_server import handle_delete_remote_session

        result = await handle_delete_remote_session({"event_id": "evt123", "confirm": False})
        data = json.loads(result[0].text)
        assert "error" in data


# =======================
# TestHandleListRemoteEvents
# =======================


class TestHandleListRemoteEvents:
    @pytest.mark.asyncio
    async def test_success_returns_events(self, mock_intervals):
        from cyclisme_training_logs.mcp_server import handle_list_remote_events

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
        from cyclisme_training_logs.mcp_server import handle_list_remote_events

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
        from cyclisme_training_logs.mcp_server import handle_list_remote_events

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
        from cyclisme_training_logs.mcp_server import handle_get_athlete_profile

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
        from cyclisme_training_logs.mcp_server import handle_get_athlete_profile

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
        from cyclisme_training_logs.mcp_server import handle_update_athlete_profile

        mock_intervals.update_athlete.side_effect = RuntimeError("API error")
        with patch(INTERVALS_PATCH, return_value=mock_intervals):
            result = await handle_update_athlete_profile({"updates": {"ftp": 250}})
        data = json.loads(result[0].text)
        assert "error" in data


# =======================
# TestHandleValidateWeekConsistency
# =======================


class TestHandleValidateWeekConsistency:
    @pytest.mark.asyncio
    async def test_success_valid_plan(self, mock_tower, mock_session):
        from cyclisme_training_logs.mcp_server import handle_validate_week_consistency

        with patch(TOWER_PATCH, mock_tower):
            result = await handle_validate_week_consistency({"week_id": "S081"})
        data = json.loads(result[0].text)
        assert data["week_id"] == "S081"
        assert "valid" in data
        assert data["total_sessions"] == 1

    @pytest.mark.asyncio
    async def test_empty_description_is_error(self, mock_plan, mock_session):
        from cyclisme_training_logs.mcp_server import handle_validate_week_consistency

        mock_session.description = ""
        tower = make_tower(mock_plan)
        with patch(TOWER_PATCH, tower):
            result = await handle_validate_week_consistency({"week_id": "S081"})
        data = json.loads(result[0].text)
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    @pytest.mark.asyncio
    async def test_high_tss_is_warning(self, mock_plan, mock_session):
        from cyclisme_training_logs.mcp_server import handle_validate_week_consistency

        mock_session.planned_tss = 350  # > 300 threshold
        tower = make_tower(mock_plan)
        with patch(TOWER_PATCH, tower):
            result = await handle_validate_week_consistency({"week_id": "S081"})
        data = json.loads(result[0].text)
        assert len(data["warnings"]) > 0

    @pytest.mark.asyncio
    async def test_exception_returns_error(self, mock_tower):
        from cyclisme_training_logs.mcp_server import handle_validate_week_consistency

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
        from cyclisme_training_logs.mcp_server import handle_get_recommendations

        mock_plan.notes = "No rec file"
        with patch(TOWER_PATCH, mock_tower):
            result = await handle_get_recommendations({"week_id": "S081"})
        data = json.loads(result[0].text)
        assert data["week_id"] == "S081"
        assert data["found"] is False

    @pytest.mark.asyncio
    async def test_exception_returns_error(self, mock_tower):
        from cyclisme_training_logs.mcp_server import handle_get_recommendations

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
        from cyclisme_training_logs.mcp_server import handle_get_training_statistics

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
        from cyclisme_training_logs.mcp_server import handle_get_training_statistics

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
        from cyclisme_training_logs.mcp_server import handle_get_training_statistics

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


# =======================
# TestHandleExportWeekToJson
# =======================


class TestHandleExportWeekToJson:
    @pytest.mark.asyncio
    async def test_exception_returns_error(self, mock_tower):
        from cyclisme_training_logs.mcp_server import handle_export_week_to_json

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
        from cyclisme_training_logs.mcp_server import handle_restore_week_from_backup

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
        from cyclisme_training_logs.mcp_server import handle_restore_week_from_backup

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

        from cyclisme_training_logs.planning import control_tower as ct_module

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
        from cyclisme_training_logs.mcp_server import handle_reload_server

        result = await handle_reload_server({})
        data = json.loads(result[0].text)
        assert "reloaded_count" in data
        assert "reloaded_modules" in data
        assert "failed" in data

    @pytest.mark.asyncio
    async def test_returns_note_about_handlers(self):
        from cyclisme_training_logs.mcp_server import handle_reload_server

        result = await handle_reload_server({})
        data = json.loads(result[0].text)
        assert "note" in data


# =======================
# TestHandleWithingsAuthStatus
# =======================


class TestHandleWithingsAuthStatus:
    @pytest.mark.asyncio
    async def test_not_configured(self):
        from cyclisme_training_logs.mcp_server import handle_withings_auth_status

        mock_config = Mock()
        mock_config.is_configured.return_value = False
        mock_config.has_valid_credentials.return_value = False
        with patch("cyclisme_training_logs.config.get_withings_config", return_value=mock_config):
            result = await handle_withings_auth_status({})
        data = json.loads(result[0].text)
        assert data["configured"] is False
        assert "message" in data

    @pytest.mark.asyncio
    async def test_configured_but_no_credentials(self):
        from cyclisme_training_logs.mcp_server import handle_withings_auth_status

        mock_config = Mock()
        mock_config.is_configured.return_value = True
        mock_config.has_valid_credentials.return_value = False
        with patch("cyclisme_training_logs.config.get_withings_config", return_value=mock_config):
            result = await handle_withings_auth_status({})
        data = json.loads(result[0].text)
        assert data["configured"] is True
        assert data["has_credentials"] is False

    @pytest.mark.asyncio
    async def test_fully_authenticated(self):
        from cyclisme_training_logs.mcp_server import handle_withings_auth_status

        mock_config = Mock()
        mock_config.is_configured.return_value = True
        mock_config.has_valid_credentials.return_value = True
        mock_config.credentials_path = Path("/tmp/withings.json")
        with patch("cyclisme_training_logs.config.get_withings_config", return_value=mock_config):
            result = await handle_withings_auth_status({})
        data = json.loads(result[0].text)
        assert data["configured"] is True
        assert data["has_credentials"] is True
        assert "message" in data


# =======================
# TestHandleWithingsAuthorize
# =======================


class TestHandleWithingsAuthorize:
    @pytest.mark.asyncio
    async def test_no_code_returns_auth_url(self):
        from cyclisme_training_logs.mcp_server import handle_withings_authorize

        mock_client = Mock()
        mock_client.get_authorization_url.return_value = (
            "https://account.withings.com/oauth2_user/authorize2?..."
        )
        with patch(
            "cyclisme_training_logs.config.create_withings_client", return_value=mock_client
        ):
            result = await handle_withings_authorize({})
        data = json.loads(result[0].text)
        assert data["step"] == "authorization_required"
        assert "authorization_url" in data
        assert "instructions" in data

    @pytest.mark.asyncio
    async def test_with_code_exchanges_successfully(self):
        from cyclisme_training_logs.mcp_server import handle_withings_authorize

        mock_client = Mock()
        mock_client.exchange_code.return_value = {"user_id": "12345", "access_token": "tok"}
        with patch(
            "cyclisme_training_logs.config.create_withings_client", return_value=mock_client
        ):
            result = await handle_withings_authorize({"authorization_code": "authcode123"})
        data = json.loads(result[0].text)
        assert data["step"] == "authorization_complete"
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_with_code_exchange_failure(self):
        from cyclisme_training_logs.mcp_server import handle_withings_authorize

        mock_client = Mock()
        mock_client.exchange_code.side_effect = RuntimeError("invalid code")
        with patch(
            "cyclisme_training_logs.config.create_withings_client", return_value=mock_client
        ):
            result = await handle_withings_authorize({"authorization_code": "badcode"})
        data = json.loads(result[0].text)
        assert data["step"] == "authorization_failed"
        assert data["status"] == "error"


# =======================
# TestHandleWithingsAnalyzeTrends
# =======================


class TestHandleWithingsAnalyzeTrends:
    @pytest.mark.asyncio
    async def test_week_period_no_data(self):
        from cyclisme_training_logs.mcp_server import handle_withings_analyze_trends

        mock_client = Mock()
        mock_client.get_sleep.return_value = []
        mock_client.get_measurements.return_value = []
        with patch(
            "cyclisme_training_logs.config.create_withings_client", return_value=mock_client
        ):
            result = await handle_withings_analyze_trends({"period": "week"})
        data = json.loads(result[0].text)
        assert data["period"] == "week"
        assert data["sleep_analysis"]["total_nights"] == 0

    @pytest.mark.asyncio
    async def test_month_period(self):
        from cyclisme_training_logs.mcp_server import handle_withings_analyze_trends

        mock_client = Mock()
        mock_client.get_sleep.return_value = [
            {"total_sleep_hours": 7.5, "sleep_score": 85},
            {"total_sleep_hours": 8.0, "sleep_score": 90},
        ]
        mock_client.get_measurements.return_value = [
            {"weight_kg": 72.5},
            {"weight_kg": 72.0},
        ]
        with patch(
            "cyclisme_training_logs.config.create_withings_client", return_value=mock_client
        ):
            result = await handle_withings_analyze_trends({"period": "month"})
        data = json.loads(result[0].text)
        assert data["period"] == "month"
        assert data["sleep_analysis"]["total_nights"] == 2

    @pytest.mark.asyncio
    async def test_custom_period_missing_dates_returns_error(self):
        from cyclisme_training_logs.mcp_server import handle_withings_analyze_trends

        mock_client = Mock()
        with patch(
            "cyclisme_training_logs.config.create_withings_client", return_value=mock_client
        ):
            result = await handle_withings_analyze_trends({"period": "custom"})
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_custom_period_with_dates(self):
        from cyclisme_training_logs.mcp_server import handle_withings_analyze_trends

        mock_client = Mock()
        mock_client.get_sleep.return_value = []
        mock_client.get_measurements.return_value = []
        with patch(
            "cyclisme_training_logs.config.create_withings_client", return_value=mock_client
        ):
            result = await handle_withings_analyze_trends(
                {
                    "period": "custom",
                    "start_date": "2026-02-01",
                    "end_date": "2026-02-28",
                }
            )
        data = json.loads(result[0].text)
        assert data["period"] == "custom"
