"""Withings health data tool schemas."""

from mcp.types import Tool


def get_tools() -> list[Tool]:
    """Return Withings health data tool schemas."""
    return [
        Tool(
            name="withings-auth-status",
            description="Check Withings OAuth authentication status and credentials validity",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="withings-authorize",
            description="Start Withings OAuth authorization flow or complete with authorization code",
            inputSchema={
                "type": "object",
                "properties": {
                    "authorization_code": {
                        "type": "string",
                        "description": "Authorization code from Withings OAuth callback (optional - if not provided, returns authorization URL)",
                    },
                },
            },
        ),
        Tool(
            name="withings-get-sleep",
            description="Get sleep data from Withings for training planning and analysis",
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
            name="withings-get-weight",
            description="Get weight and body composition measurements from Withings",
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
            name="withings-get-readiness",
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
            name="withings-sync-to-intervals",
            description="Synchronize Withings health data (sleep, weight, blood pressure) to Intervals.icu wellness fields",
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
            name="withings-analyze-trends",
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
            name="withings-enrich-session",
            description="Add Withings health metrics to a training session for comprehensive analysis",
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
                },
                "required": ["week_id", "session_id"],
            },
        ),
    ]
