"""Résolveurs stricts d'events Intervals.icu par identifiant local.

BT-021 : chaque résolveur retourne 0 ou 1 candidat, jamais un choix
silencieux parmi plusieurs. Ambiguïté = exception, à charge de l'appelant
de la propager (chemin interactif) ou de la logger (chemin batch à échec
visible).
"""

from __future__ import annotations

import logging
from typing import Any

from magma_cycling.planning.models import WORKOUT_NAME_REGEX

logger = logging.getLogger(__name__)


class AmbiguousMatchError(Exception):
    """Raised when a resolver finds more than one candidate matching its predicate.

    The exception message includes the identifier that caused the ambiguity
    and the list of candidate event IDs, so the caller can either surface
    the conflict to a human (interactive path) or log it and skip (batch
    path with visible failure).
    """


def parse_event_name(name: str) -> dict | None:
    """Parse an Intervals.icu event name via the canonical WORKOUT_NAME_REGEX.

    Returns dict with session_id / session_type / workout_name / version,
    or None if the name doesn't match (arbitrary notes, external events,
    workaround-created events without the canonical shape).
    """
    if not name:
        return None
    match = WORKOUT_NAME_REGEX.search(name)
    if not match:
        return None
    return {
        "session_id": match.group(1),
        "session_type": match.group(2),
        "workout_name": match.group(3),
        "version": match.group(4),
    }


def resolve_event_by_session_id(
    events: list[dict[str, Any]], session_id: str
) -> dict[str, Any] | None:
    """Return the unique event whose parsed session_id equals `session_id`.

    Comparison is strict equality on the parsed session_id extracted from
    the event's `name` field — NOT a substring match. This prevents the
    class of bugs where searching for `S104-05` also matches events named
    with suffixed IDs like `S104-05a-KIN-...`.

    Raises:
        AmbiguousMatchError: if 2+ events match. The caller decides how
            to surface it (raise further for interactive contexts, log
            + return None for batch contexts with visible failure).

    Returns:
        The unique matching event, or None if no event matches.
    """
    matches = [
        event
        for event in events
        if (parsed := parse_event_name(event.get("name", "")))
        and parsed["session_id"] == session_id
    ]
    if len(matches) == 0:
        logger.debug("resolve_event_by_session_id(%r): 0 match", session_id)
        return None
    if len(matches) == 1:
        return matches[0]
    ids = [event.get("id") for event in matches]
    raise AmbiguousMatchError(f"Multiple events match session_id={session_id!r}: event_ids={ids}")


def resolve_event_by_activity_id(
    events: list[dict[str, Any]], activity_id: str
) -> dict[str, Any] | None:
    """Return the unique event whose paired_activity_id equals `activity_id`.

    Intervals.icu guarantees uniqueness of paired_activity_id per activity
    at the server level, but we don't trust a third-party invariant blindly
    — the belt-and-suspenders check protects against server bugs or
    duplicated events from any prior tooling incident.

    Raises:
        AmbiguousMatchError: if 2+ events match (pathological — should
            never happen in a well-formed remote state).

    Returns:
        The unique matching event, or None if no event matches.
    """
    matches = [event for event in events if event.get("paired_activity_id") == activity_id]
    if len(matches) == 0:
        logger.debug("resolve_event_by_activity_id(%r): 0 match", activity_id)
        return None
    if len(matches) == 1:
        return matches[0]
    ids = [event.get("id") for event in matches]
    raise AmbiguousMatchError(
        f"Multiple events match paired_activity_id={activity_id!r}: event_ids={ids}"
    )
