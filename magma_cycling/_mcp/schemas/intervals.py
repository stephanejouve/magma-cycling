"""Intervals.icu integration tool schemas."""

from mcp.types import Tool


def get_tools() -> list[Tool]:
    """Return Intervals.icu integration tool schemas."""
    return [
        Tool(
            name="sync-week-to-intervals",
            description="Synchronize a week's planning to Intervals.icu (PROTECTION: never modifies completed sessions)",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (e.g., S081)",
                        "pattern": "^S\\d{3}$",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Preview changes without applying (default: false)",
                        "default": False,
                    },
                    "force_update": {
                        "type": "boolean",
                        "description": "Force update all sessions even if unchanged (default: false)",
                        "default": False,
                    },
                    "session_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional: only sync these session IDs (e.g., ['S081-03', 'S081-06'])",
                    },
                },
                "required": ["week_id"],
            },
        ),
        Tool(
            name="delete-remote-session",
            description="Delete a workout event directly on Intervals.icu (WARNING: permanent deletion)",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Intervals.icu event ID to delete (e.g., 94494673)",
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Confirmation required for deletion (default: false)",
                        "default": False,
                    },
                },
                "required": ["event_id", "confirm"],
            },
        ),
        Tool(
            name="list-remote-events",
            description="List all events from Intervals.icu for a date range (workouts, notes, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by category (WORKOUT, NOTE, etc.) - optional",
                    },
                },
                "required": ["start_date", "end_date"],
            },
        ),
        Tool(
            name="get-activity-details",
            description="Get complete details for a completed activity from Intervals.icu (TSS, IF, power curves, streams)",
            inputSchema={
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": "Activity ID (format: i107424849 or numeric)",
                    },
                    "include_streams": {
                        "type": "boolean",
                        "description": "Include time-series data (watts, HR, cadence, etc.) - default: false",
                        "default": False,
                    },
                },
                "required": ["activity_id"],
            },
        ),
        Tool(
            name="get-activity-intervals",
            description="Get aggregated interval/lap data for a completed activity from Intervals.icu (avg power, HR, cadence per interval — ideal for block-by-block analysis)",
            inputSchema={
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": "Activity ID (format: i107424849 or numeric)",
                    },
                },
                "required": ["activity_id"],
            },
        ),
        Tool(
            name="get-activity-streams",
            description="Get raw time-series stream data for an activity with optional slicing and type filtering. Returns per-second data (watts, heartrate, cadence, etc.) with stats. Use start_index/end_index to zoom into a specific interval block without flooding the context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": "Activity ID (format: i107424849 or numeric)",
                    },
                    "types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter stream types (e.g. ['watts', 'heartrate', 'cadence']). If omitted, returns all available streams.",
                    },
                    "start_index": {
                        "type": "integer",
                        "description": "Start index for slicing (inclusive, default: 0). Maps to seconds from activity start.",
                        "default": 0,
                    },
                    "end_index": {
                        "type": "integer",
                        "description": "End index for slicing (exclusive, default: end of data). Use interval start_index/end_index from get-activity-intervals.",
                    },
                },
                "required": ["activity_id"],
            },
        ),
        Tool(
            name="compare-intervals",
            description="Compare interval data across multiple activities to track progression over time. Aligns intervals by label, calculates deltas and trends for metrics like power, HR, cadence, torque, decoupling.",
            inputSchema={
                "type": "object",
                "properties": {
                    "activity_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Explicit list of activity IDs to compare (e.g. ['i122793458', 'i126184461'])",
                    },
                    "name_pattern": {
                        "type": "string",
                        "description": "Search activities by name substring (case-insensitive, e.g. 'CadenceVariations')",
                    },
                    "weeks_back": {
                        "type": "integer",
                        "description": "Number of weeks to search back (default: 6, used with name_pattern)",
                        "default": 6,
                    },
                    "label_filter": {
                        "type": "string",
                        "description": "Only keep intervals whose label contains this substring (case-insensitive, e.g. '95rpm')",
                    },
                    "type_filter": {
                        "type": "string",
                        "enum": ["WORK", "RECOVERY"],
                        "description": "Only keep intervals of this type",
                    },
                    "metrics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Metrics to include in comparison (default: all numeric metrics)",
                    },
                },
            },
        ),
        Tool(
            name="apply-workout-intervals",
            description="Apply custom interval boundaries to an Intervals.icu activity. Auto mode: parses workout prescription to compute intervals. Manual mode: accepts explicit interval list. Always dry_run=true by default (preview only).",
            inputSchema={
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": "Activity ID (format: i107424849 or numeric)",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Session ID (e.g. S082-02). If omitted, extracted from activity name.",
                    },
                    "intervals": {
                        "type": "array",
                        "description": "Manual mode: explicit interval list [{type, label, start_index, end_index}]. If omitted, auto-computes from workout prescription.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "label": {"type": "string"},
                                "start_index": {"type": "integer"},
                                "end_index": {"type": "integer"},
                            },
                            "required": ["type", "label", "start_index", "end_index"],
                        },
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Preview only, do not modify (default: true)",
                    },
                },
                "required": ["activity_id"],
            },
        ),
        Tool(
            name="update-remote-session",
            description="Update an existing workout event on Intervals.icu (PROTECTION: cannot update completed sessions)",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Intervals.icu event ID to update",
                    },
                    "updates": {
                        "type": "object",
                        "description": "Fields to update (name, description, start_date_local, type, etc.)",
                    },
                },
                "required": ["event_id", "updates"],
            },
        ),
        Tool(
            name="create-remote-note",
            description="Create a NOTE (calendar note) directly on Intervals.icu (category=NOTE, type=null). NOTE: Name MUST start with one of the allowed prefixes: [ANNULÉE], [SAUTÉE], or [REMPLACÉE]",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date for the note (YYYY-MM-DD)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "name": {
                        "type": "string",
                        "description": "Note title - MUST start with [ANNULÉE], [SAUTÉE], or [REMPLACÉE] prefix followed by session details (e.g., '[ANNULÉE] S081-04-INT-TempoSoutenu')",
                        "pattern": "^\\[(ANNULÉE|SAUTÉE|REMPLACÉE)\\] .+",
                    },
                    "description": {
                        "type": "string",
                        "description": "Note content/description",
                    },
                },
                "required": ["date", "name", "description"],
            },
        ),
        Tool(
            name="sync-remote-to-local",
            description="Sync local planning from Intervals.icu remote events (fixes desync from pre-write-back operations)",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (e.g., S081)",
                        "pattern": "^S\\d{3}$",
                    },
                    "strategy": {
                        "type": "string",
                        "description": "Sync strategy: 'merge' (preserve local) or 'replace' (overwrite)",
                        "enum": ["merge", "replace"],
                        "default": "merge",
                    },
                },
                "required": ["week_id"],
            },
        ),
        Tool(
            name="backfill-activities",
            description="Backfill historical activity data into local planning sessions (matches activities to sessions)",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID to backfill (e.g., S081). Mutually exclusive with start_date/end_date.",
                        "pattern": "^S\\d{3}$",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD). Used with end_date instead of week_id.",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD). Used with start_date instead of week_id.",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                },
                "oneOf": [
                    {"required": ["week_id"]},
                    {"required": ["start_date", "end_date"]},
                ],
            },
        ),
    ]
