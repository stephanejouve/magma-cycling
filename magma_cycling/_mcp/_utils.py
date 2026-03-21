"""Shared utilities for MCP handlers."""

import json
import sys
from contextlib import contextmanager
from datetime import date, datetime
from io import StringIO

from mcp.types import TextContent

from magma_cycling.utils.event_sync import compute_start_time  # noqa: F401 — re-export


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


def load_workout_descriptions(week_id: str) -> dict[str, str]:
    """Load full workout descriptions from {week_id}_workouts.txt.

    Delegates to workout_parser.load_workout_descriptions.
    """
    from magma_cycling.workout_parser import load_workout_descriptions as _load

    return _load(week_id)


def mcp_response(
    result: dict, *, provider_info: dict | None = None, **json_kwargs
) -> list[TextContent]:
    """Wrap a result dict with _metadata and return as MCP TextContent."""
    now = datetime.now()
    metadata: dict = {
        "response_date": date.today().isoformat(),
        "response_timestamp": now.isoformat(),
    }
    if provider_info:
        metadata["provider"] = provider_info
    result["_metadata"] = metadata
    json_kwargs.setdefault("indent", 2)
    return [TextContent(type="text", text=json.dumps(result, **json_kwargs))]
