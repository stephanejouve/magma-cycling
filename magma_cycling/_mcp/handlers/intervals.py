"""Intervals.icu integration handlers (re-export shim).

All handler implementations live in dedicated sub-modules:
  - intervals_sync       : sync-week, sync-remote, backfill
  - intervals_events     : delete, list, update, create-note
  - intervals_activities : get-details, get-intervals, get-streams
  - intervals_analysis   : compare, apply-workout
"""

from magma_cycling._mcp.handlers.intervals_activities import (  # noqa: F401
    handle_get_activity_details,
    handle_get_activity_intervals,
    handle_get_activity_streams,
)
from magma_cycling._mcp.handlers.intervals_analysis import (  # noqa: F401
    handle_apply_workout_intervals,
    handle_compare_intervals,
)
from magma_cycling._mcp.handlers.intervals_events import (  # noqa: F401
    handle_create_remote_note,
    handle_delete_remote_session,
    handle_list_remote_events,
    handle_update_remote_session,
)
from magma_cycling._mcp.handlers.intervals_sync import (  # noqa: F401
    handle_backfill_activities,
    handle_sync_remote_to_local,
    handle_sync_week_to_intervals,
)

__all__ = [
    "handle_sync_week_to_intervals",
    "handle_delete_remote_session",
    "handle_list_remote_events",
    "handle_get_activity_details",
    "handle_get_activity_intervals",
    "handle_get_activity_streams",
    "handle_compare_intervals",
    "handle_apply_workout_intervals",
    "handle_update_remote_session",
    "handle_create_remote_note",
    "handle_sync_remote_to_local",
    "handle_backfill_activities",
]
