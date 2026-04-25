"""Health data tool schemas."""

from mcp.types import Tool


def get_tools() -> list[Tool]:
    """Return health data tool schemas."""
    return [
        Tool(
            name="health-auth-status",
            description="Check health provider OAuth authentication status and credentials validity",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="health-authorize",
            description="Start health provider OAuth authorization flow or complete with authorization code",
            inputSchema={
                "type": "object",
                "properties": {
                    "authorization_code": {
                        "type": "string",
                        "description": "Authorization code from OAuth callback (optional - if not provided, returns authorization URL)",
                    },
                },
            },
        ),
        Tool(
            name="get-sleep",
            description="Get sleep data for training planning and analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD, default: today)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "last_night_only": {
                        "type": "boolean",
                        "description": "Get only last night's sleep (ignores date range)",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="get-body-composition",
            description="Get weight and body composition measurements (weight, muscle mass, body water, bone mass)",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD, default: today)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "latest_only": {
                        "type": "boolean",
                        "description": "Get only latest measurement",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="get-readiness",
            description="Evaluate training readiness based on sleep quality and health metrics",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date to evaluate (YYYY-MM-DD, default: today)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                },
            },
        ),
        Tool(
            name="get-hrv",
            description="Get nocturnal HRV (rMSSD) readings from the configured health provider (Withings Sleep Analyzer or Intervals.icu wellness)",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD, default: today)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "last_night_only": {
                        "type": "boolean",
                        "description": "Get only last night's HRV (ignores date range)",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="sync-health-to-calendar",
            description="Synchronize health data (sleep, weight, blood pressure) to training calendar wellness fields",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD, default: today)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "data_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["sleep", "weight", "blood_pressure", "all"],
                        },
                        "description": "Data types to sync (default: all)",
                    },
                },
                "required": ["start_date"],
            },
        ),
        Tool(
            name="analyze-health-trends",
            description="Analyze health trends (sleep patterns, weight changes) over a time period",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": ["week", "month", "custom"],
                        "description": "Analysis period (default: week)",
                        "default": "week",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date for custom period (YYYY-MM-DD)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date for custom period (YYYY-MM-DD)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                },
            },
        ),
        Tool(
            name="enrich-session-health",
            description="Add health metrics to a training session for comprehensive analysis",
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
                        "description": "Session ID (e.g., S082-03)",
                        "pattern": "^S\\d{3}-\\d{2}[a-z]?$",
                    },
                    "auto_readiness_check": {
                        "type": "boolean",
                        "description": "Add training readiness evaluation (default: true)",
                        "default": True,
                    },
                    "sync_to_calendar": {
                        "type": "boolean",
                        "description": "Push health data to training calendar wellness (default: true)",
                        "default": True,
                    },
                },
                "required": ["week_id", "session_id"],
            },
        ),
    ]
