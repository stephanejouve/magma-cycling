"""Rest and recovery tool schemas."""

from mcp.types import Tool


def get_tools() -> list[Tool]:
    """Return rest and recovery tool schemas."""
    return [
        Tool(
            name="pre-session-check",
            description=(
                "Pre-session safety check: evaluates sleep, fatigue (TSB), "
                "and overtraining risk before a planned session. "
                "Forces a Withings sync then runs the veto protocol."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date to check (YYYY-MM-DD, default: today)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (default: auto-detect from date)",
                        "pattern": "^S\\d{3}$",
                    },
                    "extra_sleep_hours": {
                        "type": "number",
                        "description": (
                            "Additional sleep hours not detected by Sleep Analyser "
                            "(e.g. nap or couch sleep). "
                            "Added to wellness sleep_hours before veto evaluation."
                        ),
                        "minimum": 0,
                        "maximum": 6,
                    },
                },
            },
        ),
    ]
