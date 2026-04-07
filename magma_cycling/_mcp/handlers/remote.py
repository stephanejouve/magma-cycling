"""Remote training platform integration handlers (re-export shim).

All handler implementations live in dedicated sub-modules:
  - remote_sync       : sync-week, sync-remote, backfill
  - remote_events     : delete, list, update, create-note
  - remote_activities : get-details, get-intervals, get-streams
  - remote_analysis   : compare, apply-workout
"""

from magma_cycling._mcp.handlers.remote_activities import (  # noqa: F401
    handle_get_activity_details,
    handle_get_activity_intervals,
    handle_get_activity_streams,
    handle_list_activities,
)
from magma_cycling._mcp.handlers.remote_analysis import (  # noqa: F401
    handle_apply_workout_intervals,
    handle_compare_activity_intervals,
)
from magma_cycling._mcp.handlers.remote_events import (  # noqa: F401
    handle_create_remote_note,
    handle_delete_remote_event,
    handle_list_remote_events,
    handle_update_remote_event,
)
from magma_cycling._mcp.handlers.remote_sync import (  # noqa: F401
    handle_backfill_activities,
    handle_sync_remote_to_local,
    handle_sync_week_to_calendar,
)

__all__ = [
    "handle_sync_week_to_calendar",
    "handle_delete_remote_event",
    "handle_list_remote_events",
    "handle_list_activities",
    "handle_get_activity_details",
    "handle_get_activity_intervals",
    "handle_get_activity_streams",
    "handle_compare_activity_intervals",
    "handle_apply_workout_intervals",
    "handle_update_remote_event",
    "handle_create_remote_note",
    "handle_sync_remote_to_local",
    "handle_backfill_activities",
]
