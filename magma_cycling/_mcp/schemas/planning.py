"""Planning tool schemas."""

from mcp.types import Tool


def get_tools() -> list[Tool]:
    """Return planning tool schemas."""
    return [
        Tool(
            name="weekly-planner",
            description="Generate weekly training plan with AI-powered workout recommendations",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (e.g., S082)",
                        "pattern": "^S\\d{3}$",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Week start date (YYYY-MM-DD, Monday)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "provider": {
                        "type": "string",
                        "description": "AI provider for workout generation",
                        "enum": [
                            "clipboard",
                            "claude_api",
                            "mistral_api",
                            "mcp_direct",
                            "prompt_only",
                        ],
                        "default": "clipboard",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force overwrite if a planning already exists for this week (creates backup first). Default false — will reject if planning exists.",
                        "default": False,
                    },
                },
                "required": ["week_id", "start_date"],
            },
        ),
        Tool(
            name="monthly-analysis",
            description="Generate comprehensive monthly training analysis with statistics and AI insights",
            inputSchema={
                "type": "object",
                "properties": {
                    "month": {
                        "type": "string",
                        "description": "Month to analyze (YYYY-MM)",
                        "pattern": "^\\d{4}-\\d{2}$",
                    },
                    "provider": {
                        "type": "string",
                        "description": "AI provider for analysis",
                        "enum": ["mistral_api", "claude_api", "openai", "ollama"],
                        "default": "mistral_api",
                    },
                    "no_ai": {
                        "type": "boolean",
                        "description": "Skip AI analysis, only generate statistics",
                        "default": False,
                    },
                },
                "required": ["month"],
            },
        ),
        Tool(
            name="daily-sync",
            description="Sync training activities and update session statuses",
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
                        "description": "Week ID for planning check (e.g., S082)",
                        "pattern": "^S\\d{3}$",
                    },
                    "ai_analysis": {
                        "type": "boolean",
                        "description": "Enable AI analysis of activities (default: true)",
                        "default": True,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="update-session",
            description="Update training session status (completed, skipped, cancelled, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (e.g., S082)",
                        "pattern": "^S\\d{3}$",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Session ID (e.g., S082-03, S081-06a)",
                        "pattern": "^S\\d{3}-\\d{2}[a-z]?$",
                    },
                    "status": {
                        "type": "string",
                        "description": "New status",
                        "enum": [
                            "pending",
                            "planned",
                            "uploaded",
                            "completed",
                            "skipped",
                            "cancelled",
                            "rest_day",
                            "replaced",
                            "modified",
                        ],
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for status change (required for skipped/cancelled/replaced)",
                    },
                    "sync": {
                        "type": "boolean",
                        "description": "Sync to training calendar",
                        "default": False,
                    },
                },
                "required": ["week_id", "session_id", "status"],
            },
        ),
        Tool(
            name="list-weeks",
            description="List available weekly planning files with dates and basic info",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of weeks to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 52,
                    },
                    "recent": {
                        "type": "boolean",
                        "description": "Return most recent weeks first",
                        "default": True,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get-metrics",
            description="Get current training metrics (CTL, ATL, TSB, FTP) from latest data",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get-week-details",
            description="Get detailed information about a specific week planning including all sessions",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (e.g., S081)",
                        "pattern": "^S\\d{3}$",
                    }
                },
                "required": ["week_id"],
            },
        ),
        Tool(
            name="modify-session-details",
            description="Modify detailed information of a training session (name, type, description, TSS, duration)",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (e.g., S081)",
                        "pattern": "^S\\d{3}$",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Session ID (e.g., S081-06a)",
                        "pattern": "^S\\d{3}-\\d{2}[a-z]?$",
                    },
                    "name": {
                        "type": "string",
                        "description": "Session name (e.g., 'SweetSpotCourt', 'EnduranceLongue')",
                    },
                    "type": {
                        "type": "string",
                        "description": "Session type",
                        "enum": ["END", "INT", "REC", "RACE"],
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed session description (workout structure, objectives, etc.)",
                    },
                    "tss_planned": {
                        "type": "number",
                        "description": "Planned Training Stress Score",
                    },
                    "duration_min": {
                        "type": "number",
                        "description": "Planned duration in minutes",
                    },
                },
                "required": ["week_id", "session_id"],
            },
        ),
        Tool(
            name="rename-session",
            description="Rename a session_id within a weekly plan. Updates remote event name if synced.",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (e.g. S082)",
                        "pattern": "^S\\d{3}$",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Current session ID (e.g. S082-06)",
                        "pattern": "^S\\d{3}-\\d{2}[a-z]?$",
                    },
                    "new_session_id": {
                        "type": "string",
                        "description": "New session ID (e.g. S082-06b)",
                        "pattern": "^S\\d{3}-\\d{2}[a-z]?$",
                    },
                    "sync_remote": {
                        "type": "boolean",
                        "description": "Update remote event on training calendar if synced (default: true)",
                        "default": True,
                    },
                },
                "required": ["week_id", "session_id", "new_session_id"],
            },
        ),
        Tool(
            name="create-session",
            description="Create a new training session in a weekly plan",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (e.g., S081)",
                        "pattern": "^S\\d{3}$",
                    },
                    "session_date": {
                        "type": "string",
                        "description": "Session date (YYYY-MM-DD)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "name": {
                        "type": "string",
                        "description": "Session name (default: 'NewSession')",
                        "default": "NewSession",
                    },
                    "type": {
                        "type": "string",
                        "description": "Session type (default: END)",
                        "enum": ["END", "INT", "REC", "RACE"],
                        "default": "END",
                    },
                    "description": {
                        "type": "string",
                        "description": "Workout description (default: 'À définir')",
                        "default": "À définir",
                    },
                    "tss_planned": {
                        "type": "integer",
                        "description": "Planned TSS (default: 0)",
                        "default": 0,
                    },
                    "duration_min": {
                        "type": "integer",
                        "description": "Duration in minutes (default: 0)",
                        "default": 0,
                    },
                },
                "required": ["week_id", "session_date"],
            },
        ),
        Tool(
            name="delete-session",
            description="Delete a training session from a weekly plan",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (e.g., S081)",
                        "pattern": "^S\\d{3}$",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Session ID to delete (e.g., S081-06a)",
                        "pattern": "^S\\d{3}-\\d{2}[a-z]?$",
                    },
                },
                "required": ["week_id", "session_id"],
            },
        ),
    ]
