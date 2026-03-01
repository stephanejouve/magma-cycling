"""Shared utilities for MCP handlers."""

import json
import sys
from contextlib import contextmanager
from datetime import date, datetime
from io import StringIO

from mcp.types import TextContent


@contextmanager
def suppress_stdout_stderr():
    """Suppress all stdout/stderr to prevent MCP protocol pollution."""
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    try:
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


# Statuses that should be synced to Intervals.icu.
# Any other status (completed, skipped, cancelled, rest_day, replaced) is protected.
SYNCABLE_STATUSES = {"pending", "planned", "uploaded", "modified"}


def compute_start_time(session_date, session_id: str) -> str:
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


def load_workout_descriptions(week_id: str) -> dict[str, str]:
    """Load full workout descriptions from {week_id}_workouts.txt.

    Delegates to workout_parser.load_workout_descriptions.
    """
    from magma_cycling.workout_parser import load_workout_descriptions as _load

    return _load(week_id)


def mcp_response(result: dict, **json_kwargs) -> list[TextContent]:
    """Wrap a result dict with _metadata and return as MCP TextContent."""
    now = datetime.now()
    result["_metadata"] = {
        "response_date": date.today().isoformat(),
        "response_timestamp": now.isoformat(),
    }
    json_kwargs.setdefault("indent", 2)
    return [TextContent(type="text", text=json.dumps(result, **json_kwargs))]
