"""Session manipulation tool schemas."""

from mcp.types import Tool


def get_tools() -> list[Tool]:
    """Return session manipulation tool schemas."""
    return [
        Tool(
            name="duplicate-session",
            description="Duplicate an existing session to a new date",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (e.g., S081)",
                        "pattern": "^S\\d{3}$",
                    },
                    "source_session_id": {
                        "type": "string",
                        "description": "Session ID to duplicate (e.g., S081-01)",
                        "pattern": "^S\\d{3}-\\d{2}[a-z]?$",
                    },
                    "target_date": {
                        "type": "string",
                        "description": "Target date for duplicated session (YYYY-MM-DD)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                },
                "required": ["week_id", "source_session_id", "target_date"],
            },
        ),
        Tool(
            name="swap-sessions",
            description="Swap the dates of two sessions",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (e.g., S081)",
                        "pattern": "^S\\d{3}$",
                    },
                    "session_id_1": {
                        "type": "string",
                        "description": "First session ID (e.g., S081-01)",
                        "pattern": "^S\\d{3}-\\d{2}[a-z]?$",
                    },
                    "session_id_2": {
                        "type": "string",
                        "description": "Second session ID (e.g., S081-02)",
                        "pattern": "^S\\d{3}-\\d{2}[a-z]?$",
                    },
                },
                "required": ["week_id", "session_id_1", "session_id_2"],
            },
        ),
        Tool(
            name="attach-workout",
            description="Attach a workout file (.zwo, .mrc, .erg) to a training session",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID (e.g., S081-01)",
                        "pattern": "^S\\d{3}-\\d{2}[a-z]?$",
                    },
                    "workout_name": {
                        "type": "string",
                        "description": "Workout name (e.g., 'FlatOutFast', 'ClimbControl')",
                    },
                    "workout_type": {
                        "type": "string",
                        "description": "Workout type code (e.g., 'TST', 'INT', 'END')",
                        "default": "WKT",
                    },
                    "content": {
                        "type": "string",
                        "description": "Workout file content (XML for .zwo, text for .mrc/.erg)",
                    },
                    "version": {
                        "type": "string",
                        "description": "Version (default: V001)",
                        "pattern": "^V\\d{3}$",
                        "default": "V001",
                    },
                    "extension": {
                        "type": "string",
                        "description": "File extension (default: zwo)",
                        "enum": ["zwo", "mrc", "erg"],
                        "default": "zwo",
                    },
                },
                "required": ["session_id", "workout_name", "content"],
            },
        ),
    ]
