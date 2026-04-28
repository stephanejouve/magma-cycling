"""Tests for _mcp/handlers/remote_events.py — event management handlers."""

import json
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling._mcp.handlers.remote_events import (
    handle_create_remote_note,
    handle_delete_remote_event,
    handle_list_remote_events,
    handle_update_remote_event,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


MOCK_PROVIDER_INFO = {"provider": "intervals_icu", "athlete_id": "iXXXXXX", "status": "ready"}


@pytest.fixture
def mock_client():
    """Mock IntervalsClient returned by create_intervals_client."""
    client = MagicMock()
    client.delete_event.return_value = True
    client.get_events.return_value = []
    client.update_event.return_value = {"id": 42, "name": "updated"}
    client.create_event.return_value = {"id": 99}
    client.get_provider_info.return_value = MOCK_PROVIDER_INFO
    return client


@pytest.fixture
def mock_planning_dir(tmp_path):
    """Create a temporary planning dir with one week file."""
    planning_dir = tmp_path / "week_planning"
    planning_dir.mkdir()

    plan_data = {
        "week_id": "S999",
        "start_date": "2026-03-02",
        "end_date": "2026-03-08",
        "created_at": "2026-03-01T20:00:00Z",
        "last_updated": "2026-03-01T20:00:00Z",
        "version": 1,
        "athlete_id": "iXXXXXX",
        "tss_target": 350,
        "planned_sessions": [
            {
                "session_id": "S999-01",
                "date": "2026-03-02",
                "name": "Endurance",
                "type": "END",
                "version": "V001",
                "tss_planned": 50,
                "duration_min": 60,
                "description": "Endurance Z2",
                "status": "uploaded",
                "intervals_id": 42,
                "description_hash": None,
            },
            {
                "session_id": "S999-02",
                "date": "2026-03-03",
                "name": "Interval",
                "type": "INT",
                "version": "V001",
                "tss_planned": 70,
                "duration_min": 65,
                "description": "Sweet Spot 3x10",
                "status": "completed",
                "intervals_id": 55,
                "description_hash": None,
            },
        ],
    }

    plan_file = planning_dir / "week_planning_S999.json"
    plan_file.write_text(json.dumps(plan_data))
    return planning_dir


@pytest.fixture
def patch_tower(mock_planning_dir):
    """Redirect planning_tower to use tmp_path (no mock — real singleton)."""
    from magma_cycling.planning.control_tower import planning_tower

    original_dir = planning_tower.planning_dir
    original_backup_dir = planning_tower.backup_system.planning_dir
    planning_tower.planning_dir = mock_planning_dir
    planning_tower.backup_system.planning_dir = mock_planning_dir

    yield mock_planning_dir

    planning_tower.planning_dir = original_dir
    planning_tower.backup_system.planning_dir = original_backup_dir


# ---------------------------------------------------------------------------
# handle_delete_remote_event
# ---------------------------------------------------------------------------


class TestHandleDeleteRemoteEvent:
    """Tests for handle_delete_remote_event."""

    @pytest.mark.asyncio
    async def test_requires_confirmation(self):
        """Returns error when confirm is not set."""
        result = await handle_delete_remote_event({"event_id": 42})
        data = json.loads(result[0].text)
        assert "error" in data
        assert "confirm" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_requires_confirmation_false(self):
        """Returns error when confirm=False."""
        result = await handle_delete_remote_event({"event_id": 42, "confirm": False})
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    @patch("magma_cycling.config.create_intervals_client")
    async def test_successful_delete_no_local_match(self, mock_factory, mock_client):
        """Deletes event from API when no local planning match found."""
        mock_factory.return_value = mock_client

        with patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower:
            mock_tower.planning_dir.exists.return_value = False

            result = await handle_delete_remote_event({"event_id": 42, "confirm": True})

        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["event_id"] == 42
        mock_client.delete_event.assert_called_once_with(42)

    @pytest.mark.asyncio
    @patch("magma_cycling.config.create_intervals_client")
    async def test_delete_failure_returns_error(self, mock_factory, mock_client):
        """Returns error when API delete fails."""
        mock_client.delete_event.return_value = False
        mock_factory.return_value = mock_client

        with patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower:
            mock_tower.planning_dir.exists.return_value = False

            result = await handle_delete_remote_event({"event_id": 42, "confirm": True})

        data = json.loads(result[0].text)
        assert data["success"] is False

    @pytest.mark.asyncio
    @patch("magma_cycling.config.create_intervals_client")
    async def test_blocks_delete_of_completed_session(self, mock_factory, patch_tower):
        """Cannot delete a completed session (protection)."""
        client = MagicMock()
        client.get_provider_info.return_value = MOCK_PROVIDER_INFO
        mock_factory.return_value = client

        result = await handle_delete_remote_event({"event_id": 55, "confirm": True})

        data = json.loads(result[0].text)
        assert "error" in data
        assert "completed" in data["error"].lower() or "COMPLETED" in data.get("message", "")


# ---------------------------------------------------------------------------
# handle_list_remote_events
# ---------------------------------------------------------------------------


class TestHandleListRemoteEvents:
    """Tests for handle_list_remote_events."""

    @pytest.mark.asyncio
    @patch("magma_cycling.config.create_intervals_client")
    async def test_list_events_empty(self, mock_factory, mock_client):
        """Returns empty list when no events."""
        mock_factory.return_value = mock_client

        result = await handle_list_remote_events(
            {"start_date": "2026-03-01", "end_date": "2026-03-07"}
        )
        data = json.loads(result[0].text)
        assert data["total_events"] == 0
        assert data["events"] == []

    @pytest.mark.asyncio
    @patch("magma_cycling.config.create_intervals_client")
    async def test_list_events_with_results(self, mock_factory):
        """Returns formatted events."""
        client = MagicMock()
        client.get_provider_info.return_value = MOCK_PROVIDER_INFO
        client.get_events.return_value = [
            {
                "id": 1,
                "category": "WORKOUT",
                "name": "Endurance Z2",
                "description": "Easy ride",
                "start_date_local": "2026-03-02T08:00:00",
                "type": "Ride",
            }
        ]
        mock_factory.return_value = client

        result = await handle_list_remote_events(
            {"start_date": "2026-03-01", "end_date": "2026-03-07"}
        )
        data = json.loads(result[0].text)
        assert data["total_events"] == 1
        assert data["events"][0]["name"] == "Endurance Z2"

    @pytest.mark.asyncio
    @patch("magma_cycling.config.create_intervals_client")
    async def test_list_events_with_category_filter(self, mock_factory):
        """Filters events by category."""
        client = MagicMock()
        client.get_provider_info.return_value = MOCK_PROVIDER_INFO
        client.get_events.return_value = [
            {"id": 1, "category": "WORKOUT", "name": "W1"},
            {"id": 2, "category": "NOTE", "name": "N1"},
        ]
        mock_factory.return_value = client

        result = await handle_list_remote_events(
            {"start_date": "2026-03-01", "end_date": "2026-03-07", "category": "NOTE"}
        )
        data = json.loads(result[0].text)
        assert data["total_events"] == 1
        assert data["filtered_by"] == "NOTE"

    @pytest.mark.asyncio
    @patch("magma_cycling.config.create_intervals_client")
    async def test_list_events_api_error(self, mock_factory):
        """Returns error on API failure."""
        mock_factory.side_effect = Exception("API down")

        result = await handle_list_remote_events(
            {"start_date": "2026-03-01", "end_date": "2026-03-07"}
        )
        data = json.loads(result[0].text)
        assert "error" in data


# ---------------------------------------------------------------------------
# handle_update_remote_event
# ---------------------------------------------------------------------------


class TestHandleUpdateRemoteEvent:
    """Tests for handle_update_remote_event."""

    @pytest.mark.asyncio
    @patch("magma_cycling.config.create_intervals_client")
    async def test_update_success_no_local_match(self, mock_factory):
        """Updates event on API when no local planning match."""
        client = MagicMock()
        client.get_provider_info.return_value = MOCK_PROVIDER_INFO
        client.update_event.return_value = {"id": 42, "name": "Updated"}
        mock_factory.return_value = client

        with patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower:
            mock_tower.planning_dir.exists.return_value = False

            result = await handle_update_remote_event(
                {"event_id": 42, "updates": {"name": "New Name"}}
            )

        data = json.loads(result[0].text)
        assert data["success"] is True
        assert "name" in data["updated_fields"]

    @pytest.mark.asyncio
    @patch("magma_cycling.config.create_intervals_client")
    async def test_update_failure(self, mock_factory):
        """Returns error when API update fails."""
        client = MagicMock()
        client.get_provider_info.return_value = MOCK_PROVIDER_INFO
        client.update_event.return_value = None
        mock_factory.return_value = client

        with patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower:
            mock_tower.planning_dir.exists.return_value = False

            result = await handle_update_remote_event({"event_id": 42, "updates": {"name": "X"}})

        data = json.loads(result[0].text)
        assert data["success"] is False

    @pytest.mark.asyncio
    @patch("magma_cycling.config.create_intervals_client")
    async def test_blocks_update_of_completed_session(self, mock_factory, patch_tower):
        """Cannot update a completed session."""
        client = MagicMock()
        client.get_provider_info.return_value = MOCK_PROVIDER_INFO
        mock_factory.return_value = client

        result = await handle_update_remote_event({"event_id": 55, "updates": {"name": "X"}})
        data = json.loads(result[0].text)
        assert "error" in data
        assert "completed" in data["error"].lower() or "COMPLETED" in data.get("message", "")


# ---------------------------------------------------------------------------
# handle_create_remote_note
# ---------------------------------------------------------------------------


class TestHandleCreateRemoteNote:
    """Tests for handle_create_remote_note."""

    @pytest.mark.asyncio
    @patch("magma_cycling.config.create_intervals_client")
    async def test_create_note_freeform(self, mock_factory, mock_client):
        """Accepts free-form note names (no prefix restriction)."""
        mock_factory.return_value = mock_client

        with patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower:
            mock_tower.planning_dir.exists.return_value = False

            result = await handle_create_remote_note(
                {
                    "date": "2026-03-02",
                    "name": "Course reconnaissance parcours",
                    "description": "test",
                }
            )

        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["event_id"] == 99

    @pytest.mark.asyncio
    @patch("magma_cycling.config.create_intervals_client")
    async def test_create_note_success(self, mock_factory, mock_client):
        """Creates note with prefix on API successfully."""
        mock_factory.return_value = mock_client

        with patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower:
            mock_tower.planning_dir.exists.return_value = False

            result = await handle_create_remote_note(
                {
                    "date": "2026-03-02",
                    "name": "[ANNULÉE] S999-01 Endurance",
                    "description": "Fatigue",
                }
            )

        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["event_id"] == 99

    @pytest.mark.asyncio
    @patch("magma_cycling.config.create_intervals_client")
    async def test_create_note_api_failure(self, mock_factory):
        """Returns error when API create fails."""
        client = MagicMock()
        client.get_provider_info.return_value = MOCK_PROVIDER_INFO
        client.create_event.return_value = {}  # no 'id' key
        mock_factory.return_value = client

        with patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower:
            mock_tower.planning_dir.exists.return_value = False

            result = await handle_create_remote_note(
                {
                    "date": "2026-03-02",
                    "name": "[SAUTÉE] S999-01 Endurance",
                    "description": "Oubli",
                }
            )

        data = json.loads(result[0].text)
        assert data["success"] is False

    @pytest.mark.asyncio
    @patch("magma_cycling.config.create_intervals_client")
    async def test_create_note_with_local_planning_update(self, mock_factory, patch_tower):
        """Creates note and updates local planning when session_id found."""
        client = MagicMock()
        client.get_provider_info.return_value = MOCK_PROVIDER_INFO
        client.create_event.return_value = {"id": 99}
        mock_factory.return_value = client

        result = await handle_create_remote_note(
            {
                "date": "2026-03-02",
                "name": "[ANNULÉE] S999-01 Endurance",
                "description": "Fatigue accumulée",
            }
        )

        data = json.loads(result[0].text)
        assert data["success"] is True
        # Verify local planning was updated
        assert "local planning" in data["message"].lower()

    @pytest.mark.asyncio
    @patch("magma_cycling.config.create_intervals_client")
    async def test_documentary_note_does_not_mutate_planning(self, mock_factory, patch_tower):
        """Note name leading with the session_id (without status prefix) is documentary
        and must NOT mutate the local planning status."""
        client = MagicMock()
        client.get_provider_info.return_value = MOCK_PROVIDER_INFO
        client.create_event.return_value = {"id": 99}
        mock_factory.return_value = client

        result = await handle_create_remote_note(
            {
                "date": "2026-03-02",
                "name": "S999-01 données complètes — patch impossible",
                "description": "Documentation only",
            }
        )

        data = json.loads(result[0].text)
        assert data["success"] is True
        assert "local planning not updated" in data["message"]
        assert "documentary" in data["message"]

        plan_path = patch_tower / "week_planning_S999.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        s01 = next(s for s in plan["planned_sessions"] if s["session_id"] == "S999-01")
        assert s01["status"] == "uploaded"

    @pytest.mark.asyncio
    @patch("magma_cycling.config.create_intervals_client")
    async def test_session_id_mid_sentence_does_not_mutate_planning(
        self, mock_factory, patch_tower
    ):
        """Session_id buried in prose (mid-name) must NOT mutate the local planning."""
        client = MagicMock()
        client.get_provider_info.return_value = MOCK_PROVIDER_INFO
        client.create_event.return_value = {"id": 99}
        mock_factory.return_value = client

        result = await handle_create_remote_note(
            {
                "date": "2026-03-02",
                "name": "Analyse hebdo — résultats S999-01 et S999-02",
                "description": "Recap analytique",
            }
        )

        data = json.loads(result[0].text)
        assert data["success"] is True
        assert "documentary" in data["message"]

        plan_path = patch_tower / "week_planning_S999.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        s01 = next(s for s in plan["planned_sessions"] if s["session_id"] == "S999-01")
        assert s01["status"] == "uploaded"

    @pytest.mark.asyncio
    @patch("magma_cycling.config.create_intervals_client")
    async def test_skipped_prefix_sets_status_skipped(self, mock_factory, patch_tower):
        """[SAUTÉE] prefix sets status=skipped."""
        client = MagicMock()
        client.get_provider_info.return_value = MOCK_PROVIDER_INFO
        client.create_event.return_value = {"id": 99}
        mock_factory.return_value = client

        await handle_create_remote_note(
            {
                "date": "2026-03-02",
                "name": "[SAUTÉE] S999-01 Endurance",
                "description": "Oubli",
            }
        )

        plan_path = patch_tower / "week_planning_S999.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        s01 = next(s for s in plan["planned_sessions"] if s["session_id"] == "S999-01")
        assert s01["status"] == "skipped"

    @pytest.mark.asyncio
    @patch("magma_cycling.config.create_intervals_client")
    async def test_replaced_prefix_sets_status_replaced(self, mock_factory, patch_tower):
        """[REMPLACÉE] prefix sets status=replaced."""
        client = MagicMock()
        client.get_provider_info.return_value = MOCK_PROVIDER_INFO
        client.create_event.return_value = {"id": 99}
        mock_factory.return_value = client

        await handle_create_remote_note(
            {
                "date": "2026-03-02",
                "name": "[REMPLACÉE] S999-01 par INT",
                "description": "Swap",
            }
        )

        plan_path = patch_tower / "week_planning_S999.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        s01 = next(s for s in plan["planned_sessions"] if s["session_id"] == "S999-01")
        assert s01["status"] == "replaced"

    @pytest.mark.asyncio
    @patch("magma_cycling.config.create_intervals_client")
    async def test_prefix_without_session_id_no_planning_update(self, mock_factory, patch_tower):
        """[ANNULÉE] without a parseable session_id in the name → planning untouched,
        explicit message in response."""
        client = MagicMock()
        client.get_provider_info.return_value = MOCK_PROVIDER_INFO
        client.create_event.return_value = {"id": 99}
        mock_factory.return_value = client

        result = await handle_create_remote_note(
            {
                "date": "2026-03-02",
                "name": "[ANNULÉE] vacances",
                "description": "Off-week",
            }
        )

        data = json.loads(result[0].text)
        assert data["success"] is True
        assert "no session_id" in data["message"]

        plan_path = patch_tower / "week_planning_S999.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        s01 = next(s for s in plan["planned_sessions"] if s["session_id"] == "S999-01")
        assert s01["status"] == "uploaded"
