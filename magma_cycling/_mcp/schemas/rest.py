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
                "Forces a health sync then runs the veto protocol."
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
        Tool(
            name="insert-workout-history",
            description=(
                "Insert a new entry into workouts-history.md at the chronologically "
                "correct position. Wraps WorkoutHistoryManager.insert_analysis "
                "(legacy CLI insert-analysis) — handles duplicate detection and "
                "atomic write. For correcting an existing entry, use "
                "patch-coach-analysis instead."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "analysis_text": {
                        "type": "string",
                        "description": (
                            "Full markdown analysis block to insert. Must contain "
                            "a date in DD/MM/YYYY format (used for chronological "
                            "placement). Typically a complete `### SXXX-NN | type | "
                            "date` entry with metrics + analysis."
                        ),
                    },
                    "yes_confirm": {
                        "type": "boolean",
                        "description": (
                            "Auto-confirm overwrite if a similar entry exists for "
                            "the same date. Default false — will refuse with a "
                            "clear error if duplicate detected."
                        ),
                        "default": False,
                    },
                },
                "required": ["analysis_text"],
            },
        ),
        Tool(
            name="patch-coach-analysis",
            description=(
                "Patch a coach analysis entry in workouts-history.md without "
                "re-running the AI prompt. Useful for correcting metrics "
                "(e.g. sleep hours) that were wrong at generation time."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": (
                            "Activity ID (e.g. i133337326). "
                            "Takes priority over session_id if both provided."
                        ),
                    },
                    "session_id": {
                        "type": "string",
                        "description": (
                            "Session ID prefix (e.g. S085-04). "
                            "Used to locate the entry by ### header."
                        ),
                    },
                    "sleep_hours": {
                        "type": "number",
                        "description": (
                            "Corrected sleep hours value. Replaces the existing "
                            "value in 'Métriques Pré-séance' and 'Points d'Attention'."
                        ),
                        "minimum": 0,
                        "maximum": 24,
                    },
                    "note": {
                        "type": "string",
                        "description": (
                            "Free-text correction note appended as "
                            "'#### Note de correction' section."
                        ),
                    },
                },
            },
        ),
    ]
