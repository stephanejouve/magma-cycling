"""Workout tool schemas."""

from mcp.types import Tool


def get_tools() -> list[Tool]:
    """Return workout tool schemas."""
    return [
        Tool(
            name="get-workout",
            description="Get the workout file content for a training session",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID (e.g., S081-01)",
                        "pattern": "^S\\d{3}-\\d{2}[a-z]?$",
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="upload-workouts",
            description=(
                "Upload structured workouts to Intervals.icu calendar for a "
                "given week. Wraps the legacy CLI upload-workouts. Reads "
                "workouts from a file relative to the data repo (typically "
                "data/week_planning/{week_id}_workouts.txt). Auto-backup before "
                "real upload. Use dry_run=true for a no-op simulation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (e.g., S091)",
                        "pattern": "^S\\d{3}$",
                    },
                    "workouts_file_path": {
                        "type": "string",
                        "description": (
                            "Path to workouts file, relative to data repo root "
                            "(e.g., data/week_planning/S091_workouts.txt). "
                            "Path traversal is rejected — must stay within data repo."
                        ),
                    },
                    "start_date": {
                        "type": "string",
                        "description": (
                            "Week start date YYYY-MM-DD (Monday). If absent, "
                            "auto-computed from week_id via planning data."
                        ),
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Simulation mode, no real upload (default: false)",
                        "default": False,
                    },
                    "auto_backup": {
                        "type": "boolean",
                        "description": "Auto-backup planning files before upload (default: true)",
                        "default": True,
                    },
                },
                "required": ["week_id", "workouts_file_path"],
            },
        ),
        Tool(
            name="validate-workout",
            description="Validate structured workout format syntax and optionally fix common errors",
            inputSchema={
                "type": "object",
                "properties": {
                    "workout_text": {
                        "type": "string",
                        "description": "Workout description in structured format",
                    },
                    "auto_fix": {
                        "type": "boolean",
                        "description": "Automatically fix common formatting issues (default: false)",
                        "default": False,
                    },
                },
                "required": ["workout_text"],
            },
        ),
    ]
