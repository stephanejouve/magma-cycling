"""Tests unitaires pour magma_cycling.utils.event_resolver (BT-021)."""

from __future__ import annotations

import pytest

from magma_cycling.utils.event_resolver import (
    AmbiguousMatchError,
    parse_event_name,
    resolve_event_by_activity_id,
    resolve_event_by_session_id,
)


class TestParseEventName:
    """Parse d'un event.name via WORKOUT_NAME_REGEX."""

    def test_standard_workout(self):
        assert parse_event_name("S087-01-END-EnduranceDouce-V001") == {
            "session_id": "S087-01",
            "session_type": "END",
            "workout_name": "EnduranceDouce",
            "version": "V001",
        }

    def test_suffixed_session_id(self):
        assert parse_event_name("S104-05a-KIN-KineEpaule-V001") == {
            "session_id": "S104-05a",
            "session_type": "KIN",
            "workout_name": "KineEpaule",
            "version": "V001",
        }

    def test_cancelled_prefix(self):
        parsed = parse_event_name("[ANNULÉE] S087-04-INT-SweetSpot-V001")
        assert parsed is not None
        assert parsed["session_id"] == "S087-04"

    def test_empty_returns_none(self):
        assert parse_event_name("") is None

    def test_none_input_returns_none(self):
        assert parse_event_name(None) is None  # type: ignore[arg-type]

    def test_arbitrary_note_returns_none(self):
        assert parse_event_name("Note manuelle 31/07 workaround") is None


class TestResolveEventBySessionId:
    """Résolution stricte par session_id parsé — cœur du fix BT-021."""

    def test_single_match_returns_event(self):
        events = [
            {"id": 100, "name": "S104-05-INT-Tempo-V001"},
            {"id": 200, "name": "S104-06-END-Endurance-V001"},
        ]
        assert resolve_event_by_session_id(events, "S104-05") == events[0]

    def test_no_match_returns_none(self):
        events = [{"id": 100, "name": "S104-05-INT-Tempo-V001"}]
        assert resolve_event_by_session_id(events, "S999-99") is None

    def test_empty_list_returns_none(self):
        assert resolve_event_by_session_id([], "S104-05") is None

    @pytest.mark.parametrize(
        "target,expected_id",
        [("S104-05", 100), ("S104-05a", 200)],
    )
    def test_suffix_not_matched_as_prefix(self, target, expected_id):
        """BT-021 racine du bug #428: S104-05 ne match PAS S104-05a."""
        events = [
            {"id": 100, "name": "S104-05-INT-Tempo-V001"},
            {"id": 200, "name": "S104-05a-KIN-KineEpaule-V001"},
        ]
        assert resolve_event_by_session_id(events, target)["id"] == expected_id

    @pytest.mark.parametrize(
        "target,expected_id",
        [("S104-05", 100), ("S104-05a", 200)],
    )
    def test_independent_of_iteration_order(self, target, expected_id):
        """Fixture rejouée avec ordre inversé → même résultat."""
        events = [
            {"id": 200, "name": "S104-05a-KIN-KineEpaule-V001"},
            {"id": 100, "name": "S104-05-INT-Tempo-V001"},
        ]
        assert resolve_event_by_session_id(events, target)["id"] == expected_id

    def test_ambiguous_match_raises(self):
        """Deux events avec le même session_id parsé → AmbiguousMatchError."""
        events = [
            {"id": 100, "name": "S104-05-INT-Tempo-V001"},
            {"id": 200, "name": "S104-05-END-DoublonBug-V002"},
        ]
        with pytest.raises(AmbiguousMatchError, match="S104-05"):
            resolve_event_by_session_id(events, "S104-05")

    def test_ambiguous_error_includes_event_ids(self):
        """Message d'erreur = actionnable : contient les IDs impliqués."""
        events = [
            {"id": 100, "name": "S104-05-INT-Tempo-V001"},
            {"id": 200, "name": "S104-05-END-Doublon-V002"},
        ]
        with pytest.raises(AmbiguousMatchError) as exc_info:
            resolve_event_by_session_id(events, "S104-05")
        assert "100" in str(exc_info.value)
        assert "200" in str(exc_info.value)

    def test_unparseable_event_names_ignored(self):
        """Un event au name arbitraire (workaround manuel) n'est pas matché."""
        events = [
            {"id": 100, "name": "Random note manuelle"},
            {"id": 200, "name": "S104-05-INT-Tempo-V001"},
        ]
        assert resolve_event_by_session_id(events, "S104-05")["id"] == 200

    def test_missing_name_key_ignored(self):
        events = [{"id": 100}, {"id": 200, "name": "S104-05-INT-Tempo-V001"}]
        assert resolve_event_by_session_id(events, "S104-05")["id"] == 200


class TestResolveEventByActivityId:
    """Fix 3 — ceinture-bretelles sur paired_activity_id (unicité API)."""

    def test_single_match_returns_event(self):
        events = [
            {"id": 100, "paired_activity_id": "i123", "name": "..."},
            {"id": 200, "paired_activity_id": "i456", "name": "..."},
        ]
        assert resolve_event_by_activity_id(events, "i123")["id"] == 100

    def test_no_match_returns_none(self):
        events = [{"id": 100, "paired_activity_id": "i123"}]
        assert resolve_event_by_activity_id(events, "i999") is None

    def test_empty_list_returns_none(self):
        assert resolve_event_by_activity_id([], "i123") is None

    def test_unpaired_events_ignored(self):
        events = [
            {"id": 100},  # no paired_activity_id
            {"id": 200, "paired_activity_id": None},
            {"id": 300, "paired_activity_id": "i123"},
        ]
        assert resolve_event_by_activity_id(events, "i123")["id"] == 300

    def test_duplicate_paired_activity_raises(self):
        """Pathologique — API Intervals garantit unicité, mais on ne fait pas confiance aveugle."""
        events = [
            {"id": 100, "paired_activity_id": "i123"},
            {"id": 200, "paired_activity_id": "i123"},
        ]
        with pytest.raises(AmbiguousMatchError, match="i123"):
            resolve_event_by_activity_id(events, "i123")
