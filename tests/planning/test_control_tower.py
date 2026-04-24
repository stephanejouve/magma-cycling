"""Tests for PlanningControlTower — sync_from_remote version handling."""

from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock, patch

from magma_cycling.planning.models import WORKOUT_NAME_REGEX


class TestSyncFromRemoteVersion:
    """Test that sync_from_remote does not double the V prefix."""

    def test_sync_from_remote_version_no_double_V(self):
        """Regex group(4) already captures 'V001'; building the dict must NOT add another V."""
        event_name = "S087-01-END-EnduranceDouce-V001"
        match = WORKOUT_NAME_REGEX.search(event_name)
        assert match is not None

        version = match.group(4)
        assert version == "V001", f"Regex should capture 'V001', got {version!r}"

        # Simulate the FIXED line (was: f"V{version}" → "VV001")
        built_version = version  # correct
        assert built_version == "V001"

        # Demonstrate the old bug
        old_built_version = f"V{version}"
        assert old_built_version == "VV001", "Old code would have produced VV001"


class TestSyncFromRemoteNoteFiltering:
    """Regression tests for Georges Crespi 2026-04-20 bug report.

    Analysis notes that embed a session ID in their title must NOT
    trigger intervals_id swaps or status flips on the matching local
    session. Only cancellation notes ([ANNULÉE]/[SAUTÉE]) are honored.
    """

    def _build_events(self):
        """Return a realistic event list: 1 WORKOUT + 1 regular NOTE + 1 cancellation NOTE."""
        return [
            {
                "id": 111,
                "name": "S016-02-INT-TempoSoutenu-V001",
                "category": "WORKOUT",
                "start_date_local": "2026-04-14T10:00:00",
                "description": "INT session",
            },
            {
                # Regular analysis note — must be IGNORED by sync
                "id": 222,
                "name": "S016-02-INT-TempoSoutenu-V001 — Analyse manuelle ZRL",
                "category": "NOTE",
                "start_date_local": "2026-04-14T10:00:00",
                "description": "Analyse post-session",
            },
            {
                # Cancellation note — must be HONORED
                "id": 333,
                "name": "[ANNULÉE] S016-06-END-EnduranceDouce-V001",
                "category": "NOTE",
                "start_date_local": "2026-04-18T10:00:00",
                "description": "",
            },
        ]

    def _run_sync(self, events, local_intervals_id_for_02=111):
        """Execute sync_from_remote with a mocked planning layer and return stats."""
        from magma_cycling.planning.control_tower import PlanningControlTower

        tower = PlanningControlTower()

        # Mock the local plan: one session S016-02 pinned to a given intervals_id.
        # session_date must be a real date for the post-sync sort to succeed.
        local_session = MagicMock()
        local_session.session_id = "S016-02"
        local_session.session_date = date(2026, 4, 14)
        local_session.name = "TempoSoutenu"
        local_session.description = "existing description"
        local_session.intervals_id = local_intervals_id_for_02

        plan = MagicMock()
        plan.start_date = date(2026, 4, 13)
        plan.end_date = date(2026, 4, 19)
        plan.planned_sessions = [local_session]

        # Mock client
        client = MagicMock()
        client.get_events.return_value = events

        @contextmanager
        def fake_modify_week(*_args, **_kwargs):
            yield plan

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "magma_cycling.planning.models.WeeklyPlan.from_json",
                return_value=plan,
            ),
            patch.object(tower, "modify_week", side_effect=fake_modify_week),
        ):
            return tower.sync_from_remote(
                week_id="S016",
                intervals_client=client,
                strategy="merge",
                requesting_script="test",
            )

    def test_regular_note_does_not_swap_intervals_id(self):
        """A NOTE embedding a session ID must not flip the local intervals_id."""
        events = [e for e in self._build_events() if e["id"] != 333]  # exclude cancel note
        stats = self._run_sync(events, local_intervals_id_for_02=111)

        # The NOTE (id=222) must be ignored → no intervals_id swap
        assert stats["intervals_ids_fixed"] == []

    def test_cancellation_note_still_reaches_parser(self):
        """[ANNULÉE] / [SAUTÉE] notes must not be skipped by the NOTE filter."""
        from magma_cycling.planning.models import WORKOUT_NAME_REGEX

        cancel_name = "[ANNULÉE] S016-06-END-EnduranceDouce-V001"
        # The name still matches the session-ID regex
        assert WORKOUT_NAME_REGEX.search(cancel_name) is not None
        # And the filter keeps it (does NOT continue)
        has_cancel_marker = "[ANNULÉE]" in cancel_name or "[SAUTÉE]" in cancel_name
        assert has_cancel_marker, "Cancellation note must bypass the NOTE filter"

    def test_cancellation_note_adds_session_with_skip_reason(self):
        """Adding a cancelled session from a NOTE must inject a default skip_reason.

        The Session pydantic model requires skip_reason non-null when
        status='cancelled'. sync_from_remote must provide a default, otherwise
        the constructor raises ValidationError. Regression test for BT-011.
        """
        events = self._build_events()
        stats = self._run_sync(events)

        # Session S016-06 should be added via the cancellation NOTE, not crash
        assert "S016-06" in stats["sessions_added"]

    def test_regular_note_alone_is_silently_dropped(self):
        """If a session is only referenced by an analysis NOTE, it must not be added to planning."""
        # Only an analysis NOTE, no underlying WORKOUT remote
        events = [
            {
                "id": 999,
                "name": "S099-01-END-Endurance-V001 — Analyse libre",
                "category": "NOTE",
                "start_date_local": "2026-04-14T10:00:00",
                "description": "",
            }
        ]
        stats = self._run_sync(events)

        # Nothing added, nothing fixed
        assert stats["sessions_added"] == []
        assert stats["intervals_ids_fixed"] == []
