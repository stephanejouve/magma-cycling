"""Athlete profile tool schemas."""

from mcp.types import Tool


def get_tools() -> list[Tool]:
    """Return athlete profile tool schemas."""
    return [
        Tool(
            name="get-athlete-profile",
            description="Get current athlete profile (FTP, weight, CTL, ATL, TSB, zones)",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="update-athlete-profile",
            description=(
                "Update athlete profile. The handler dispatches per field: "
                "Intervals.icu API for training fields (ftp, weight, max_hr, "
                "resting_hr, fthr, etc.) and the local athlete YAML for "
                "portable fields (home_location). MCT-XXX-0."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "updates": {
                        "type": "object",
                        "description": (
                            "Fields to update. Training fields (ftp, weight, "
                            "max_hr, resting_hr, fthr, etc.) hit Intervals.icu. "
                            "`home_location` (object with lat/lon + optional label) "
                            "is written to the local athlete YAML."
                        ),
                        "additionalProperties": True,
                        "properties": {
                            "home_location": {
                                "type": "object",
                                "description": (
                                    "Athlete's home / training base location. "
                                    "Latitude and longitude in decimal degrees, "
                                    "optional human label (e.g. 'Chas')."
                                ),
                                "properties": {
                                    "lat": {
                                        "type": "number",
                                        "minimum": -90,
                                        "maximum": 90,
                                    },
                                    "lon": {
                                        "type": "number",
                                        "minimum": -180,
                                        "maximum": 180,
                                    },
                                    "label": {"type": "string"},
                                },
                                "required": ["lat", "lon"],
                                "additionalProperties": False,
                            },
                            "priority_objective": {
                                "description": (
                                    "Priority training objective (event-style "
                                    "goal with target date). Stored in the user "
                                    "athlete YAML — never in the bundle. Pass "
                                    "null to clear an existing objective."
                                ),
                                "oneOf": [
                                    {"type": "null"},
                                    {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string", "minLength": 1},
                                            "type": {"type": "string", "minLength": 1},
                                            "target_date": {
                                                "type": "string",
                                                "format": "date",
                                                "description": "YYYY-MM-DD",
                                            },
                                            "priority": {
                                                "type": "string",
                                                "enum": ["A", "B", "C"],
                                                "default": "A",
                                            },
                                            "distance_km": {
                                                "type": "number",
                                                "exclusiveMinimum": 0,
                                            },
                                            "notes": {"type": "string"},
                                        },
                                        "required": ["name", "type", "target_date"],
                                        "additionalProperties": False,
                                    },
                                ],
                            },
                            "hrv_baseline": {
                                "description": (
                                    "HRV rMSSD baseline (range, fatigue alert "
                                    "threshold, documented anomalies, recovery "
                                    "pattern). Stored in the user athlete YAML. "
                                    "Pass null to clear."
                                ),
                                "oneOf": [
                                    {"type": "null"},
                                    {
                                        "type": "object",
                                        "properties": {
                                            "rmssd_min": {
                                                "type": "number",
                                                "exclusiveMinimum": 0,
                                            },
                                            "rmssd_max": {
                                                "type": "number",
                                                "exclusiveMinimum": 0,
                                            },
                                            "rmssd_peak": {
                                                "type": "number",
                                                "exclusiveMinimum": 0,
                                            },
                                            "alert_threshold": {
                                                "type": "number",
                                                "exclusiveMinimum": 0,
                                            },
                                            "anomalies": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "date": {
                                                            "type": "string",
                                                            "format": "date",
                                                        },
                                                        "value": {
                                                            "type": "number",
                                                            "exclusiveMinimum": 0,
                                                        },
                                                        "context": {
                                                            "type": "string",
                                                            "minLength": 1,
                                                        },
                                                        "exclude_from_stats": {
                                                            "type": "boolean",
                                                            "default": False,
                                                        },
                                                    },
                                                    "required": [
                                                        "date",
                                                        "value",
                                                        "context",
                                                    ],
                                                    "additionalProperties": False,
                                                },
                                            },
                                            "recovery_pattern": {"type": "string"},
                                        },
                                        "required": [
                                            "rmssd_min",
                                            "rmssd_max",
                                            "alert_threshold",
                                        ],
                                        "additionalProperties": False,
                                    },
                                ],
                            },
                            "injury_history": {
                                "description": (
                                    "Active injuries + standing watch points. "
                                    "Stored in the user athlete YAML. Pass null "
                                    "to clear."
                                ),
                                "oneOf": [
                                    {"type": "null"},
                                    {
                                        "type": "object",
                                        "properties": {
                                            "active": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "area": {
                                                            "type": "string",
                                                            "minLength": 1,
                                                        },
                                                        "status": {
                                                            "type": "string",
                                                            "enum": [
                                                                "active",
                                                                "monitoring",
                                                                "healed",
                                                            ],
                                                        },
                                                        "onset_date": {
                                                            "type": "string",
                                                            "format": "date",
                                                        },
                                                        "last_followup": {
                                                            "type": "string",
                                                            "format": "date",
                                                        },
                                                        "notes": {"type": "string"},
                                                    },
                                                    "required": ["area", "status"],
                                                    "additionalProperties": False,
                                                },
                                            },
                                            "watch_points": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                            },
                                        },
                                        "additionalProperties": False,
                                    },
                                ],
                            },
                            "macro_plan": {
                                "description": (
                                    "Macro training plan (weekly TSS targets, "
                                    "CTL target, peak event with strategy). "
                                    "Stored in the user athlete YAML. Pass null "
                                    "to clear."
                                ),
                                "oneOf": [
                                    {"type": "null"},
                                    {
                                        "type": "object",
                                        "properties": {
                                            "weekly_tss": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "week_label": {
                                                            "type": "string",
                                                            "minLength": 1,
                                                        },
                                                        "tss_target": {
                                                            "type": "integer",
                                                            "exclusiveMinimum": 0,
                                                        },
                                                        "notes": {"type": "string"},
                                                    },
                                                    "required": [
                                                        "week_label",
                                                        "tss_target",
                                                    ],
                                                    "additionalProperties": False,
                                                },
                                            },
                                            "ctl_target": {
                                                "type": "number",
                                                "exclusiveMinimum": 0,
                                            },
                                            "peak_event": {
                                                "type": "object",
                                                "properties": {
                                                    "name": {
                                                        "type": "string",
                                                        "minLength": 1,
                                                    },
                                                    "date": {
                                                        "type": "string",
                                                        "format": "date",
                                                    },
                                                    "ctl_target": {
                                                        "type": "number",
                                                        "exclusiveMinimum": 0,
                                                    },
                                                    "tsb_target_min": {"type": "number"},
                                                    "tsb_target_max": {"type": "number"},
                                                    "strategy": {"type": "string"},
                                                },
                                                "required": ["name", "date"],
                                                "additionalProperties": False,
                                            },
                                        },
                                        "additionalProperties": False,
                                    },
                                ],
                            },
                            "nutrition_strategy": {
                                "description": (
                                    "In-event nutrition strategy (carbs/h range "
                                    "+ known issues like cramps). Stored in the "
                                    "user athlete YAML. Pass null to clear."
                                ),
                                "oneOf": [
                                    {"type": "null"},
                                    {
                                        "type": "object",
                                        "properties": {
                                            "carbs_per_hour_min": {
                                                "type": "integer",
                                                "exclusiveMinimum": 0,
                                            },
                                            "carbs_per_hour_max": {
                                                "type": "integer",
                                                "exclusiveMinimum": 0,
                                            },
                                            "known_issues": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                            },
                                        },
                                        "required": [
                                            "carbs_per_hour_min",
                                            "carbs_per_hour_max",
                                        ],
                                        "additionalProperties": False,
                                    },
                                ],
                            },
                            "sleep_baseline": {
                                "description": (
                                    "Sleep baseline (average duration, nightly "
                                    "deficit, bedtime target). Stored in the "
                                    "user athlete YAML. Pass null to clear."
                                ),
                                "oneOf": [
                                    {"type": "null"},
                                    {
                                        "type": "object",
                                        "properties": {
                                            "avg_duration_minutes": {
                                                "type": "integer",
                                                "exclusiveMinimum": 0,
                                            },
                                            "deficit_per_night_minutes": {
                                                "type": "integer",
                                                "minimum": 0,
                                            },
                                            "bedtime_target": {
                                                "type": "string",
                                                "pattern": r"^([01]\d|2[0-3]):[0-5]\d$",
                                                "description": "HH:MM 24h",
                                            },
                                        },
                                        "required": [
                                            "avg_duration_minutes",
                                            "deficit_per_night_minutes",
                                        ],
                                        "additionalProperties": False,
                                    },
                                ],
                            },
                            "availability_pattern": {
                                "description": (
                                    "Recurring weekly availability (slots with "
                                    "day, time window, activity). Stored in the "
                                    "user athlete YAML. Pass null to clear."
                                ),
                                "oneOf": [
                                    {"type": "null"},
                                    {
                                        "type": "object",
                                        "properties": {
                                            "weekly_slots": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "day_of_week": {
                                                            "type": "string",
                                                            "enum": [
                                                                "mon",
                                                                "tue",
                                                                "wed",
                                                                "thu",
                                                                "fri",
                                                                "sat",
                                                                "sun",
                                                            ],
                                                        },
                                                        "time_window": {
                                                            "type": "string",
                                                            "pattern": (
                                                                r"^([01]\d|2[0-3]):"
                                                                r"[0-5]\d-"
                                                                r"([01]\d|2[0-3]):"
                                                                r"[0-5]\d$"
                                                            ),
                                                            "description": ("HH:MM-HH:MM 24h"),
                                                        },
                                                        "activity": {
                                                            "type": "string",
                                                            "minLength": 1,
                                                        },
                                                        "typical_tss": {
                                                            "type": "integer",
                                                            "minimum": 0,
                                                        },
                                                    },
                                                    "required": [
                                                        "day_of_week",
                                                        "time_window",
                                                        "activity",
                                                    ],
                                                    "additionalProperties": False,
                                                },
                                            },
                                            "notes": {"type": "string"},
                                        },
                                        "additionalProperties": False,
                                    },
                                ],
                            },
                        },
                    },
                },
                "required": ["updates"],
            },
        ),
    ]
