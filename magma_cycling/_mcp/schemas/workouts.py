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
