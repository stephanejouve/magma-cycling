"""Tests for validate-local-remote-sync MCP tool."""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling._mcp.handlers.analysis import (
    _parse_event_name,
    handle_validate_local_remote_sync,
)

# ---------------------------------------------------------------------------
# Helper: _parse_event_name
# ---------------------------------------------------------------------------


class TestParseEventName:
    """Unit tests for _parse_event_name helper."""

    def test_standard_name(self):
        result = _parse_event_name("S087-01-REC-RecoveryActive-V001")
        assert result == {
            "session_id": "S087-01",
            "session_type": "REC",
            "workout_name": "RecoveryActive",
            "version": "V001",
        }

    def test_double_session_suffix(self):
        result = _parse_event_name("S081-06a-INT-TempoSoutenu-V001")
        assert result == {
            "session_id": "S081-06a",
            "session_type": "INT",
            "workout_name": "TempoSoutenu",
            "version": "V001",
        }

    def test_cancelled_prefix(self):
        result = _parse_event_name("[ANNULÉE] S087-04-INT-SweetSpot-V001")
        assert result is not None
        assert result["session_id"] == "S087-04"
        assert result["session_type"] == "INT"
        assert result["workout_name"] == "SweetSpot"

    def test_no_match(self):
        assert _parse_event_name("Random Note Title") is None
        assert _parse_event_name("") is None

    def test_partial_match(self):
        assert _parse_event_name("S087-01-REC") is None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_session(
    session_id="S087-01",
    name="RecoveryActive",
    session_type="REC",
    session_date=date(2026, 3, 30),
    intervals_id=101,
    status="uploaded",
    description="Easy spin",
):
    """Create a mock Session object."""
    s = MagicMock()
    s.session_id = session_id
    s.name = name
    s.session_type = session_type
    s.session_date = session_date
    s.intervals_id = intervals_id
    s.status = status
    s.description = description
    return s


def _make_event(
    eid=101,
    name="S087-01-REC-RecoveryActive-V001",
    start_date="2026-03-30T08:00:00",
    description="Easy spin",
    category="WORKOUT",
):
    """Create a mock remote event dict."""
    return {
        "id": eid,
        "name": name,
        "start_date_local": start_date,
        "description": description,
        "category": category,
    }


def _extract_result(response):
    """Extract the JSON result from an MCP response."""
    return json.loads(response[0].text)


# ---------------------------------------------------------------------------
# Handler tests
# ---------------------------------------------------------------------------


class TestValidateLocalRemoteSync:
    """Tests for handle_validate_local_remote_sync."""

    @pytest.mark.asyncio
    async def test_in_sync(self):
        """All sessions match remote — IN_SYNC."""
        session = _make_session()
        event = _make_event()

        plan = MagicMock()
        plan.start_date = date(2026, 3, 30)
        plan.end_date = date(2026, 4, 5)
        plan.planned_sessions = [session]

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.config.create_intervals_client") as mock_client_factory,
        ):
            mock_tower.read_week.return_value = plan
            mock_client = MagicMock()
            mock_client.get_events.return_value = [event]
            mock_client_factory.return_value = mock_client

            result = _extract_result(await handle_validate_local_remote_sync({"week_id": "S087"}))

        assert result["status"] == "IN_SYNC"
        assert result["sessions_checked"] == 1
        assert result["discrepancies"] == []
        assert result["orphaned_remote"] == []

    @pytest.mark.asyncio
    async def test_name_mismatch(self):
        """Local name differs from remote parsed name."""
        session = _make_session(name="SweetSpotProgressif")
        event = _make_event(name="S087-01-REC-RecoveryActive-V001")

        plan = MagicMock()
        plan.start_date = date(2026, 3, 30)
        plan.end_date = date(2026, 4, 5)
        plan.planned_sessions = [session]

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.config.create_intervals_client") as mock_client_factory,
        ):
            mock_tower.read_week.return_value = plan
            mock_client = MagicMock()
            mock_client.get_events.return_value = [event]
            mock_client_factory.return_value = mock_client

            result = _extract_result(await handle_validate_local_remote_sync({"week_id": "S087"}))

        assert result["status"] == "DRIFT_DETECTED"
        names = [d["type"] for d in result["discrepancies"]]
        assert "NAME_MISMATCH" in names

    @pytest.mark.asyncio
    async def test_type_mismatch(self):
        """Local type differs from remote parsed type."""
        session = _make_session(session_type="INT")
        event = _make_event(name="S087-01-REC-RecoveryActive-V001")

        plan = MagicMock()
        plan.start_date = date(2026, 3, 30)
        plan.end_date = date(2026, 4, 5)
        plan.planned_sessions = [session]

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.config.create_intervals_client") as mock_client_factory,
        ):
            mock_tower.read_week.return_value = plan
            mock_client = MagicMock()
            mock_client.get_events.return_value = [event]
            mock_client_factory.return_value = mock_client

            result = _extract_result(await handle_validate_local_remote_sync({"week_id": "S087"}))

        assert result["status"] == "DRIFT_DETECTED"
        types = [d["type"] for d in result["discrepancies"]]
        assert "TYPE_MISMATCH" in types

    @pytest.mark.asyncio
    async def test_date_mismatch(self):
        """Local date differs from remote date."""
        session = _make_session(session_date=date(2026, 3, 30))
        event = _make_event(start_date="2026-03-31T08:00:00")

        plan = MagicMock()
        plan.start_date = date(2026, 3, 30)
        plan.end_date = date(2026, 4, 5)
        plan.planned_sessions = [session]

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.config.create_intervals_client") as mock_client_factory,
        ):
            mock_tower.read_week.return_value = plan
            mock_client = MagicMock()
            mock_client.get_events.return_value = [event]
            mock_client_factory.return_value = mock_client

            result = _extract_result(await handle_validate_local_remote_sync({"week_id": "S087"}))

        assert result["status"] == "DRIFT_DETECTED"
        types = [d["type"] for d in result["discrepancies"]]
        assert "DATE_MISMATCH" in types

    @pytest.mark.asyncio
    async def test_session_id_mismatch_detects_swap(self):
        """Session ID in remote name differs from local — detects swap."""
        session = _make_session(session_id="S087-01")
        event = _make_event(name="S087-03-REC-RecoveryActive-V001")

        plan = MagicMock()
        plan.start_date = date(2026, 3, 30)
        plan.end_date = date(2026, 4, 5)
        plan.planned_sessions = [session]

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.config.create_intervals_client") as mock_client_factory,
        ):
            mock_tower.read_week.return_value = plan
            mock_client = MagicMock()
            mock_client.get_events.return_value = [event]
            mock_client_factory.return_value = mock_client

            result = _extract_result(await handle_validate_local_remote_sync({"week_id": "S087"}))

        assert result["status"] == "DRIFT_DETECTED"
        swap = [d for d in result["discrepancies"] if d["type"] == "SESSION_ID_MISMATCH"]
        assert len(swap) == 1
        assert swap[0]["local"] == "S087-01"
        assert swap[0]["remote"] == "S087-03"

    @pytest.mark.asyncio
    async def test_description_mismatch_skipped_by_default(self):
        """Description check is off by default — no DESCRIPTION_MISMATCH."""
        session = _make_session(description="Local description v2")
        event = _make_event(description="Remote description v1")

        plan = MagicMock()
        plan.start_date = date(2026, 3, 30)
        plan.end_date = date(2026, 4, 5)
        plan.planned_sessions = [session]

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.config.create_intervals_client") as mock_client_factory,
        ):
            mock_tower.read_week.return_value = plan
            mock_client = MagicMock()
            mock_client.get_events.return_value = [event]
            mock_client_factory.return_value = mock_client

            result = _extract_result(await handle_validate_local_remote_sync({"week_id": "S087"}))

        assert result["status"] == "IN_SYNC"
        desc = [d for d in result["discrepancies"] if d["type"] == "DESCRIPTION_MISMATCH"]
        assert len(desc) == 0

    @pytest.mark.asyncio
    async def test_description_mismatch_opt_in(self):
        """Description check enabled via include_description_check=true."""
        session = _make_session(description="Local description v2")
        event = _make_event(description="Remote description v1")

        plan = MagicMock()
        plan.start_date = date(2026, 3, 30)
        plan.end_date = date(2026, 4, 5)
        plan.planned_sessions = [session]

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.config.create_intervals_client") as mock_client_factory,
        ):
            mock_tower.read_week.return_value = plan
            mock_client = MagicMock()
            mock_client.get_events.return_value = [event]
            mock_client_factory.return_value = mock_client

            result = _extract_result(
                await handle_validate_local_remote_sync(
                    {
                        "week_id": "S087",
                        "include_description_check": True,
                    }
                )
            )

        desc = [d for d in result["discrepancies"] if d["type"] == "DESCRIPTION_MISMATCH"]
        assert len(desc) == 1
        assert desc[0]["severity"] == "LOW"

    @pytest.mark.asyncio
    async def test_remote_missing_now_dangling_reference(self):
        """BT-020: intervals_id local sans event remote → dangling_references
        (auparavant discrepancies[type=REMOTE_MISSING]). Reclassé pour ne
        pas être confondu avec un discrepancy structurel — la remédiation
        est distincte (re-sync vs unlink)."""
        session = _make_session(intervals_id=999)

        plan = MagicMock()
        plan.start_date = date(2026, 3, 30)
        plan.end_date = date(2026, 4, 5)
        plan.planned_sessions = [session]

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.config.create_intervals_client") as mock_client_factory,
        ):
            mock_tower.read_week.return_value = plan
            mock_client = MagicMock()
            mock_client.get_events.return_value = []
            mock_client_factory.return_value = mock_client

            result = _extract_result(await handle_validate_local_remote_sync({"week_id": "S087"}))

        assert result["status"] == "DRIFT_DETECTED"
        assert len(result["dangling_references"]) == 1
        dangling = result["dangling_references"][0]
        assert dangling["intervals_id"] == 999
        assert dangling["session_id"] == "S087-01"
        assert dangling["date"] == "2026-03-30"
        # Migration: le cas ne remonte plus dans discrepancies
        remote_missing = [d for d in result["discrepancies"] if d.get("type") == "REMOTE_MISSING"]
        assert remote_missing == []

    @pytest.mark.asyncio
    async def test_orphaned_remote(self):
        """Remote WORKOUT event not linked to any local session."""
        session = _make_session(intervals_id=101)
        event_linked = _make_event(eid=101)
        event_orphan = _make_event(
            eid=202,
            name="S087-05-END-EnduranceDouce-V001",
            start_date="2026-04-01T08:00:00",
        )

        plan = MagicMock()
        plan.start_date = date(2026, 3, 30)
        plan.end_date = date(2026, 4, 5)
        plan.planned_sessions = [session]

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.config.create_intervals_client") as mock_client_factory,
        ):
            mock_tower.read_week.return_value = plan
            mock_client = MagicMock()
            mock_client.get_events.return_value = [event_linked, event_orphan]
            mock_client_factory.return_value = mock_client

            result = _extract_result(await handle_validate_local_remote_sync({"week_id": "S087"}))

        assert result["status"] == "DRIFT_DETECTED"
        assert len(result["orphaned_remote"]) == 1
        assert result["orphaned_remote"][0]["intervals_id"] == 202

    @pytest.mark.asyncio
    async def test_unlinked_local(self):
        """Local session is syncable but has no intervals_id."""
        session_linked = _make_session(intervals_id=101)
        session_unlinked = _make_session(
            session_id="S087-02",
            name="Tempo",
            intervals_id=None,
            status="planned",
        )
        event = _make_event(eid=101)

        plan = MagicMock()
        plan.start_date = date(2026, 3, 30)
        plan.end_date = date(2026, 4, 5)
        plan.planned_sessions = [session_linked, session_unlinked]

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.config.create_intervals_client") as mock_client_factory,
        ):
            mock_tower.read_week.return_value = plan
            mock_client = MagicMock()
            mock_client.get_events.return_value = [event]
            mock_client_factory.return_value = mock_client

            result = _extract_result(await handle_validate_local_remote_sync({"week_id": "S087"}))

        assert len(result["unlinked_local"]) == 1
        assert result["unlinked_local"][0]["session_id"] == "S087-02"

    @pytest.mark.asyncio
    async def test_planning_not_found(self):
        """Returns error when planning file doesn't exist."""
        with patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower:
            mock_tower.read_week.side_effect = FileNotFoundError("not found")

            result = _extract_result(await handle_validate_local_remote_sync({"week_id": "S999"}))

        assert "error" in result
        assert "not found" in result["error"].lower() or "Planning" in result["error"]

    @pytest.mark.asyncio
    async def test_api_error(self):
        """Returns error when Intervals.icu API fails."""
        plan = MagicMock()
        plan.start_date = date(2026, 3, 30)
        plan.end_date = date(2026, 4, 5)
        plan.planned_sessions = []

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.config.create_intervals_client") as mock_client_factory,
        ):
            mock_tower.read_week.return_value = plan
            mock_client = MagicMock()
            mock_client.get_events.side_effect = Exception("API timeout")
            mock_client_factory.return_value = mock_client

            result = _extract_result(await handle_validate_local_remote_sync({"week_id": "S087"}))

        assert "error" in result
        assert "API timeout" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("off_bike_type", ["KIN", "INJ"])
    async def test_off_bike_synced_is_in_sync(self, off_bike_type):
        """A synced off-bike session (INJURED remote event) → IN_SYNC, no drift."""
        session = _make_session(
            session_id="S104-05",
            name="KineEpaule",
            session_type=off_bike_type,
            intervals_id=555,
            description="Bandes élastiques",
        )
        injured_event = _make_event(
            eid=555,
            name=f"S104-05-{off_bike_type}-KineEpaule-V001",
            start_date=f"{session.session_date}T09:00:00",
            description="Bandes élastiques",
            category="INJURED",
        )

        plan = MagicMock()
        plan.start_date = date(2026, 3, 30)
        plan.end_date = date(2026, 4, 5)
        plan.planned_sessions = [session]

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.config.create_intervals_client") as mock_client_factory,
        ):
            mock_tower.read_week.return_value = plan
            mock_client = MagicMock()
            mock_client.get_events.return_value = [injured_event]
            mock_client_factory.return_value = mock_client

            result = _extract_result(await handle_validate_local_remote_sync({"week_id": "S104"}))

        assert result["status"] == "IN_SYNC"
        assert result["discrepancies"] == []
        assert result["orphaned_remote"] == []
        assert result["unlinked_local"] == []

    @pytest.mark.asyncio
    async def test_off_bike_injured_orphan_now_flagged(self):
        """BT-020: un event INJURED orphelin est maintenant flagué.
        Auparavant ignoré par le filtre WORKOUT-only — précisément le
        bug qui rendait invisibles les KIN post-hoc non nettoyées."""
        session = _make_session(intervals_id=101)
        event_linked = _make_event(eid=101)
        injured_orphan = {
            "id": 777,
            "name": "S087-05-KIN-KineEpaule-V001",
            "category": "INJURED",
            "start_date_local": "2026-04-01T09:00:00",
        }

        plan = MagicMock()
        plan.start_date = date(2026, 3, 30)
        plan.end_date = date(2026, 4, 5)
        plan.planned_sessions = [session]

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.config.create_intervals_client") as mock_client_factory,
        ):
            mock_tower.read_week.return_value = plan
            mock_client = MagicMock()
            mock_client.get_events.return_value = [event_linked, injured_orphan]
            mock_client_factory.return_value = mock_client

            result = _extract_result(await handle_validate_local_remote_sync({"week_id": "S087"}))

        assert result["status"] == "DRIFT_DETECTED"
        assert len(result["orphaned_remote"]) == 1
        orphan = result["orphaned_remote"][0]
        assert orphan["intervals_id"] == 777
        assert orphan["category"] == "INJURED"

    @pytest.mark.asyncio
    async def test_note_orphan_now_flagged(self):
        """BT-020: un event NOTE orphelin est maintenant flagué. Cas
        typique = repos supprimé du planning local mais NOTE Intervals.icu
        oubliée (S105 09/08 event 126839319 lors du chantier housekeeping)."""
        session = _make_session(intervals_id=101)
        event = _make_event(eid=101)
        note_orphan = {
            "id": 300,
            "name": "S087-07-REC-ReposComplet-V001",
            "category": "NOTE",
            "start_date_local": "2026-04-05T06:00:00",
        }

        plan = MagicMock()
        plan.start_date = date(2026, 3, 30)
        plan.end_date = date(2026, 4, 5)
        plan.planned_sessions = [session]

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.config.create_intervals_client") as mock_client_factory,
        ):
            mock_tower.read_week.return_value = plan
            mock_client = MagicMock()
            mock_client.get_events.return_value = [event, note_orphan]
            mock_client_factory.return_value = mock_client

            result = _extract_result(await handle_validate_local_remote_sync({"week_id": "S087"}))

        assert result["status"] == "DRIFT_DETECTED"
        assert len(result["orphaned_remote"]) == 1
        orphan = result["orphaned_remote"][0]
        assert orphan["intervals_id"] == 300
        assert orphan["category"] == "NOTE"

    @pytest.mark.asyncio
    async def test_note_referenced_locally_stays_non_orphan(self):
        """Non-régression scan élargi : une NOTE référencée par une
        session locale ne remonte PAS en orphan (le scan sans filtre
        catégorie doit toujours respecter linked_remote_ids)."""
        # Session repos qui pointe vers la NOTE 300 côté remote
        session = _make_session(
            session_id="S087-07",
            name="ReposComplet",
            session_type="REC",
            intervals_id=300,
        )
        note_event = {
            "id": 300,
            "name": "S087-07-REC-ReposComplet-V001",
            "category": "NOTE",
            "start_date_local": "2026-04-05T06:00:00",
        }

        plan = MagicMock()
        plan.start_date = date(2026, 3, 30)
        plan.end_date = date(2026, 4, 5)
        plan.planned_sessions = [session]

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.config.create_intervals_client") as mock_client_factory,
        ):
            mock_tower.read_week.return_value = plan
            mock_client = MagicMock()
            mock_client.get_events.return_value = [note_event]
            mock_client_factory.return_value = mock_client

            result = _extract_result(await handle_validate_local_remote_sync({"week_id": "S087"}))

        assert result["orphaned_remote"] == []
        # Note: le REC référencé aura un DATE_MISMATCH (session_date
        # 30/03 par défaut du helper, note event daté 05/04) — ce n'est
        # pas ce qui est testé ici.

    @pytest.mark.asyncio
    async def test_orphan_with_unparseable_name_still_reported(self):
        """Non-régression scan élargi : un event NOTE au name arbitraire
        (workaround `create-remote-note` ex-31/07) doit remonter en orphan
        même si _parse_event_name renvoie None. parsed=None est acceptable
        dans le shape output, le orphan reste actionnable via intervals_id."""
        session = _make_session(intervals_id=101)
        event_linked = _make_event(eid=101)
        note_workaround = {
            "id": 555,
            "name": "Note manuelle du 31/07 — pas de pattern",
            "category": "NOTE",
            "start_date_local": "2026-04-01T00:00:00",
        }

        plan = MagicMock()
        plan.start_date = date(2026, 3, 30)
        plan.end_date = date(2026, 4, 5)
        plan.planned_sessions = [session]

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.config.create_intervals_client") as mock_client_factory,
        ):
            mock_tower.read_week.return_value = plan
            mock_client = MagicMock()
            mock_client.get_events.return_value = [event_linked, note_workaround]
            mock_client_factory.return_value = mock_client

            result = _extract_result(await handle_validate_local_remote_sync({"week_id": "S087"}))

        assert len(result["orphaned_remote"]) == 1
        orphan = result["orphaned_remote"][0]
        assert orphan["intervals_id"] == 555
        assert orphan["parsed"] is None
        assert orphan["category"] == "NOTE"

    @pytest.mark.asyncio
    async def test_completed_session_without_intervals_id_not_unlinked(self):
        """Completed sessions without intervals_id are not reported as unlinked."""
        session = _make_session(intervals_id=None, status="completed")

        plan = MagicMock()
        plan.start_date = date(2026, 3, 30)
        plan.end_date = date(2026, 4, 5)
        plan.planned_sessions = [session]

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.config.create_intervals_client") as mock_client_factory,
        ):
            mock_tower.read_week.return_value = plan
            mock_client = MagicMock()
            mock_client.get_events.return_value = []
            mock_client_factory.return_value = mock_client

            result = _extract_result(await handle_validate_local_remote_sync({"week_id": "S087"}))

        assert result["unlinked_local"] == []

    @pytest.mark.asyncio
    async def test_rest_day_note_not_remote_missing(self):
        """A rest day synced as NOTE should not trigger REMOTE_MISSING."""
        session = _make_session(
            session_id="S087-07",
            name="ReposComplet",
            session_type="REC",
            intervals_id=500,
            status="uploaded",
        )
        # The remote event is a NOTE (not a WORKOUT)
        note_event = _make_event(
            eid=500,
            name="S087-07-REC-ReposComplet-V001",
            category="NOTE",
        )

        plan = MagicMock()
        plan.start_date = date(2026, 3, 30)
        plan.end_date = date(2026, 4, 5)
        plan.planned_sessions = [session]

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.config.create_intervals_client") as mock_client_factory,
        ):
            mock_tower.read_week.return_value = plan
            mock_client = MagicMock()
            mock_client.get_events.return_value = [note_event]
            mock_client_factory.return_value = mock_client

            result = _extract_result(await handle_validate_local_remote_sync({"week_id": "S087"}))

        # No REMOTE_MISSING — the NOTE event is found in remote_by_id
        missing = [d for d in result["discrepancies"] if d["type"] == "REMOTE_MISSING"]
        assert len(missing) == 0
        assert result["status"] == "IN_SYNC"

    @pytest.mark.asyncio
    async def test_metadata_present(self):
        """Response includes _metadata."""
        plan = MagicMock()
        plan.start_date = date(2026, 3, 30)
        plan.end_date = date(2026, 4, 5)
        plan.planned_sessions = []

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.config.create_intervals_client") as mock_client_factory,
        ):
            mock_tower.read_week.return_value = plan
            mock_client = MagicMock()
            mock_client.get_events.return_value = []
            mock_client_factory.return_value = mock_client

            result = _extract_result(await handle_validate_local_remote_sync({"week_id": "S087"}))

        assert "_metadata" in result
        assert "response_date" in result["_metadata"]


class TestBT020DetectionCompleteness:
    """BT-020 spec — complétude de la détection du validateur.

    Une seule fixture parametrized qui construit une semaine « corner-case
    complète » couvrant les 3 catégories de sortie et leurs non-régressions
    symétriques. Vérifie que le shape output est arrêté (orphaned_remote
    toutes catégories, unlinked_local existant, dangling_references nouveau)
    et que le validateur reste read-only (aucun side effect testé).
    """

    def _build_full_fixture(self):
        """Fixture unique couvrant toutes les combinaisons de la spec."""
        # 1 WORKOUT référencé (noise IN_SYNC)
        s_workout_linked = _make_session(
            session_id="S087-01",
            name="Tempo",
            session_type="INT",
            session_date=date(2026, 3, 30),
            intervals_id=101,
        )
        # 1 session locale avec intervals_id absent (dangling_references)
        s_dangling = _make_session(
            session_id="S087-02",
            name="Endurance",
            session_type="END",
            session_date=date(2026, 3, 31),
            intervals_id=999,  # jamais dans les events remote
        )
        # 1 session locale sans intervals_id, syncable (unlinked_local)
        s_unlinked = _make_session(
            session_id="S087-03",
            name="SweetSpot",
            session_type="INT",
            session_date=date(2026, 4, 1),
            intervals_id=None,
            status="planned",
        )
        # 1 NOTE référencée localement (non-régression scan élargi ne
        # doit PAS la classer en orphan)
        s_note_linked = _make_session(
            session_id="S087-07",
            name="ReposComplet",
            session_type="REC",
            session_date=date(2026, 4, 5),
            intervals_id=300,
        )

        # Remote events :
        e_workout_linked = _make_event(
            eid=101,
            name="S087-01-INT-Tempo-V001",
            start_date="2026-03-30T08:00:00",
        )
        # WORKOUT orphelin (non référencé) — cas nominal historique
        e_workout_orphan = _make_event(
            eid=201,
            name="S087-99-END-EnduranceOrpheline-V001",
            start_date="2026-04-02T08:00:00",
        )
        # NOTE orphelin (BT-020 dim 1)
        e_note_orphan = {
            "id": 202,
            "name": "S087-98-REC-NoteResidu-V001",
            "category": "NOTE",
            "start_date_local": "2026-04-03T06:00:00",
        }
        # INJURED orphelin (BT-020 dim 1, généralisation catégorie)
        e_injured_orphan = {
            "id": 203,
            "name": "S087-97-KIN-KineResiduelle-V001",
            "category": "INJURED",
            "start_date_local": "2026-04-04T09:00:00",
        }
        # NOTE référencée (non-régression)
        e_note_linked = {
            "id": 300,
            "name": "S087-07-REC-ReposComplet-V001",
            "category": "NOTE",
            "start_date_local": "2026-04-05T06:00:00",
        }

        plan = MagicMock()
        plan.start_date = date(2026, 3, 30)
        plan.end_date = date(2026, 4, 5)
        plan.planned_sessions = [s_workout_linked, s_dangling, s_unlinked, s_note_linked]

        remote_events = [
            e_workout_linked,
            e_workout_orphan,
            e_note_orphan,
            e_injured_orphan,
            e_note_linked,
        ]
        return plan, remote_events

    @pytest.mark.asyncio
    async def test_full_fixture_populates_all_three_output_buckets(self):
        """Une seule invocation doit ranger chaque anomalie dans le bon pot."""
        plan, remote_events = self._build_full_fixture()

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.config.create_intervals_client") as mock_client_factory,
        ):
            mock_tower.read_week.return_value = plan
            mock_client = MagicMock()
            mock_client.get_events.return_value = remote_events
            mock_client_factory.return_value = mock_client

            result = _extract_result(await handle_validate_local_remote_sync({"week_id": "S087"}))

        # Status
        assert result["status"] == "DRIFT_DETECTED"

        # orphaned_remote : 3 events (WORKOUT + NOTE + INJURED),
        # les 2 events référencés (WORKOUT 101 et NOTE 300) n'y figurent pas
        orphan_ids = {o["intervals_id"] for o in result["orphaned_remote"]}
        assert orphan_ids == {201, 202, 203}
        # Chaque orphan expose sa catégorie pour orienter la remédiation
        orphan_categories = {o["intervals_id"]: o["category"] for o in result["orphaned_remote"]}
        assert orphan_categories == {201: "WORKOUT", 202: "NOTE", 203: "INJURED"}

        # dangling_references : 1 session (S087-02 → intervals_id 999 absent)
        assert len(result["dangling_references"]) == 1
        dangling = result["dangling_references"][0]
        assert dangling["session_id"] == "S087-02"
        assert dangling["intervals_id"] == 999
        assert dangling["date"] == "2026-03-31"

        # unlinked_local : 1 session (S087-03 planned sans intervals_id)
        assert len(result["unlinked_local"]) == 1
        assert result["unlinked_local"][0]["session_id"] == "S087-03"

        # sessions_checked = nombre de sessions locales avec intervals_id
        # non-null (workout linked + dangling + note linked) = 3
        assert result["sessions_checked"] == 3

    @pytest.mark.asyncio
    async def test_nominal_in_sync_stays_clean(self):
        """Non-régression : fenêtre 100 % nominale (WORKOUT référencé +
        NOTE référencée + rien d'autre) → toutes les listes vides,
        status IN_SYNC."""
        s_workout = _make_session(intervals_id=101)
        s_rest = _make_session(
            session_id="S087-07",
            name="ReposComplet",
            session_type="REC",
            session_date=date(2026, 4, 5),
            intervals_id=300,
        )
        e_workout = _make_event(eid=101)
        e_rest = {
            "id": 300,
            "name": "S087-07-REC-ReposComplet-V001",
            "category": "NOTE",
            "start_date_local": "2026-04-05T06:00:00",
        }

        plan = MagicMock()
        plan.start_date = date(2026, 3, 30)
        plan.end_date = date(2026, 4, 5)
        plan.planned_sessions = [s_workout, s_rest]

        with (
            patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower,
            patch("magma_cycling.config.create_intervals_client") as mock_client_factory,
        ):
            mock_tower.read_week.return_value = plan
            mock_client = MagicMock()
            mock_client.get_events.return_value = [e_workout, e_rest]
            mock_client_factory.return_value = mock_client

            result = _extract_result(await handle_validate_local_remote_sync({"week_id": "S087"}))

        assert result["status"] == "IN_SYNC"
        assert result["discrepancies"] == []
        assert result["orphaned_remote"] == []
        assert result["dangling_references"] == []
        assert result["unlinked_local"] == []
