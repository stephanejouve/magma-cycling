"""Shared event sync decision logic for Intervals.icu."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from typing import Literal


@dataclass(frozen=True)
class SyncDecision:
    """Result of evaluate_sync: action to take and reason."""

    action: Literal["create", "update", "skip"]
    reason: str
    existing_event_id: str | None = None


def calculate_description_hash(description: str) -> str:
    """Calculate SHA256 hash of workout description for change detection.

    Args:
        description: Workout description text.

    Returns:
        16-character hex hash (first 16 chars of SHA256).
    """
    return hashlib.sha256(description.encode("utf-8")).hexdigest()[:16]


def compute_start_time(session_date: date, session_id: str) -> str:
    """Compute start time for an Intervals.icu event.

    Args:
        session_date: Date of the session (date object with .weekday()).
        session_id: Session ID (e.g., "S081-04", "S081-06a", "S081-06b").

    Returns:
        Time string like "09:00:00" or "17:00:00".
    """
    day_of_week = session_date.weekday()  # 0=Monday, 5=Saturday
    session_day_part = session_id.split("-")[-1]  # e.g., "04" or "06a"
    session_suffix = session_day_part[-1] if session_day_part[-1].isalpha() else None

    if session_suffix == "a":
        return "09:00:00"  # Morning
    elif session_suffix == "b":
        return "15:00:00"  # Afternoon
    else:
        # Saturday → 09:00, other days → 17:00
        return "09:00:00" if day_of_week == 5 else "17:00:00"


def evaluate_sync(
    event_data: dict,
    existing_event: dict | None,
    force_update: bool = False,
) -> SyncDecision:
    """Decide whether to create, update, or skip an event sync.

    Decision logic:
        1. No existing event → create
        2. paired_activity_id present → skip (protected, already executed)
        3. force_update → update
        4. Hash identical + name/start identical → skip
        5. Otherwise → update

    Args:
        event_data: Local event data to sync (must have name, description,
            start_date_local keys).
        existing_event: Remote event dict from Intervals.icu, or None.
        force_update: If True, force update even if content matches.

    Returns:
        SyncDecision with action, reason, and optional existing_event_id.
    """
    if existing_event is None:
        return SyncDecision(action="create", reason="no existing event")

    event_id = existing_event.get("id")

    # Protection: never overwrite a completed workout
    if existing_event.get("paired_activity_id"):
        return SyncDecision(
            action="skip",
            reason=f"protected (paired_activity_id: {existing_event['paired_activity_id']})",
            existing_event_id=event_id,
        )

    if force_update:
        return SyncDecision(action="update", reason="force_update", existing_event_id=event_id)

    # Compare content hash
    new_hash = calculate_description_hash(event_data.get("description", ""))
    existing_hash = calculate_description_hash(existing_event.get("description", ""))

    # Compare name and start_date_local
    name_match = event_data.get("name") == existing_event.get("name")
    start_match = event_data.get("start_date_local") == existing_event.get("start_date_local")

    if new_hash == existing_hash and name_match and start_match:
        return SyncDecision(action="skip", reason="identical content", existing_event_id=event_id)

    return SyncDecision(action="update", reason="content changed", existing_event_id=event_id)
