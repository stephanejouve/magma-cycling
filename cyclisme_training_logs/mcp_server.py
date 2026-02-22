#!/usr/bin/env python3
"""
MCP Server for Cyclisme Training Logs.

Exposes training management tools to Claude Desktop and other MCP clients.

Tools provided:
- weekly-planner: Generate weekly training plans
- monthly-analysis: Monthly training analysis and insights
- daily-sync: Sync with Intervals.icu
- sync-remote-to-local: Sync local planning from remote events (fixes desync)
- backfill-activities: Backfill historical activity data into sessions
- update-session: Update session status
- list-weeks: List available weekly plannings
- get-metrics: Get current training metrics

Usage:
    poetry run mcp-server

Claude Desktop config (~/.config/claude/claude_desktop_config.json):
    {
      "mcpServers": {
        "cyclisme-training": {
          "command": "poetry",
          "args": ["run", "mcp-server"],
          "cwd": "/Users/stephanejouve/cyclisme-training-logs"
        }
      }
    }
"""

import json
import sys
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from io import StringIO
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
)


@contextmanager
def suppress_stdout_stderr():
    """Suppress all stdout/stderr to prevent MCP protocol pollution."""
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    try:
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


# Initialize MCP server
server = Server("cyclisme-training-logs")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available training management tools."""
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
                        "enum": ["clipboard", "claude_api", "mistral_api"],
                        "default": "clipboard",
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
            description="Sync training activities from Intervals.icu and update session statuses",
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
                        "description": "Sync to Intervals.icu",
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
                },
                "required": ["week_id"],
            },
        ),
        Tool(
            name="validate-workout",
            description="Validate Intervals.icu workout format syntax and optionally fix common errors",
            inputSchema={
                "type": "object",
                "properties": {
                    "workout_text": {
                        "type": "string",
                        "description": "Workout description in Intervals.icu format",
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
            name="get-athlete-profile",
            description="Get current athlete profile from Intervals.icu (FTP, weight, CTL, ATL, TSB, zones)",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="update-athlete-profile",
            description="Update athlete profile on Intervals.icu (FTP, weight, max_hr, resting_hr, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "updates": {
                        "type": "object",
                        "description": "Fields to update (ftp, weight, max_hr, resting_hr, fthr, etc.)",
                        "additionalProperties": True,
                    },
                },
                "required": ["updates"],
            },
        ),
        Tool(
            name="validate-week-consistency",
            description="Validate week planning consistency (no conflicts, TSS coherent, sessions well-formed)",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (e.g., S081)",
                        "pattern": "^S\\d{3}$",
                    },
                },
                "required": ["week_id"],
            },
        ),
        Tool(
            name="get-recommendations",
            description="Get PID and Peaks system recommendations for a week",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (e.g., S081)",
                        "pattern": "^S\\d{3}$",
                    },
                },
                "required": ["week_id"],
            },
        ),
        Tool(
            name="analyze-session-adherence",
            description="Analyze adherence between planned session and completed activity (TSS, IF, duration comparison)",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID (e.g., S081-04)",
                    },
                    "activity_id": {
                        "type": "string",
                        "description": "Activity ID (format: i107424849)",
                    },
                },
                "required": ["session_id", "activity_id"],
            },
        ),
        Tool(
            name="get-training-statistics",
            description="Get aggregated training statistics for a date range (TSS, compliance, intensity distribution)",
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
                },
                "required": ["start_date", "end_date"],
            },
        ),
        Tool(
            name="export-week-to-json",
            description="Export week planning to JSON file for backup",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (e.g., S081)",
                        "pattern": "^S\\d{3}$",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output file path (optional, defaults to /tmp/)",
                    },
                },
                "required": ["week_id"],
            },
        ),
        Tool(
            name="restore-week-from-backup",
            description="Restore week planning from JSON backup file (PROTECTION: requires confirmation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (e.g., S081)",
                        "pattern": "^S\\d{3}$",
                    },
                    "backup_path": {
                        "type": "string",
                        "description": "Path to backup JSON file",
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Confirmation required for restore (default: false)",
                        "default": False,
                    },
                },
                "required": ["week_id", "backup_path", "confirm"],
            },
        ),
        Tool(
            name="analyze-training-patterns",
            description="META TOOL: Comprehensive analysis loading all relevant data (planning, activities, wellness, adherence) for AI coach analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID to analyze (e.g., S081)",
                        "pattern": "^S\\d{3}$",
                    },
                    "depth": {
                        "type": "string",
                        "description": "Analysis depth: 'quick' (current week only), 'standard' (current + prev week), 'comprehensive' (current + prev + context)",
                        "enum": ["quick", "standard", "comprehensive"],
                        "default": "standard",
                    },
                    "include_recommendations": {
                        "type": "boolean",
                        "description": "Include PID/Peaks recommendations if available (default: true)",
                        "default": True,
                    },
                },
                "required": ["week_id"],
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
            name="reload-server",
            description="[DEV] Reload MCP server modules to pick up code changes without restarting Claude Desktop",
            inputSchema={"type": "object", "properties": {}},
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


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls from MCP clients."""
    try:
        if name == "weekly-planner":
            return await handle_weekly_planner(arguments)
        elif name == "monthly-analysis":
            return await handle_monthly_analysis(arguments)
        elif name == "daily-sync":
            return await handle_daily_sync(arguments)
        elif name == "update-session":
            return await handle_update_session(arguments)
        elif name == "list-weeks":
            return await handle_list_weeks(arguments)
        elif name == "get-metrics":
            return await handle_get_metrics(arguments)
        elif name == "get-week-details":
            return await handle_get_week_details(arguments)
        elif name == "modify-session-details":
            return await handle_modify_session_details(arguments)
        elif name == "create-session":
            return await handle_create_session(arguments)
        elif name == "delete-session":
            return await handle_delete_session(arguments)
        elif name == "duplicate-session":
            return await handle_duplicate_session(arguments)
        elif name == "swap-sessions":
            return await handle_swap_sessions(arguments)
        elif name == "attach-workout":
            return await handle_attach_workout(arguments)
        elif name == "get-workout":
            return await handle_get_workout(arguments)
        elif name == "sync-week-to-intervals":
            return await handle_sync_week_to_intervals(arguments)
        elif name == "validate-workout":
            return await handle_validate_workout(arguments)
        elif name == "delete-remote-session":
            return await handle_delete_remote_session(arguments)
        elif name == "list-remote-events":
            return await handle_list_remote_events(arguments)
        elif name == "get-activity-details":
            return await handle_get_activity_details(arguments)
        elif name == "update-remote-session":
            return await handle_update_remote_session(arguments)
        elif name == "get-athlete-profile":
            return await handle_get_athlete_profile(arguments)
        elif name == "update-athlete-profile":
            return await handle_update_athlete_profile(arguments)
        elif name == "validate-week-consistency":
            return await handle_validate_week_consistency(arguments)
        elif name == "get-recommendations":
            return await handle_get_recommendations(arguments)
        elif name == "analyze-session-adherence":
            return await handle_analyze_session_adherence(arguments)
        elif name == "get-training-statistics":
            return await handle_get_training_statistics(arguments)
        elif name == "export-week-to-json":
            return await handle_export_week_to_json(arguments)
        elif name == "restore-week-from-backup":
            return await handle_restore_week_from_backup(arguments)
        elif name == "analyze-training-patterns":
            return await handle_analyze_training_patterns(arguments)
        elif name == "create-remote-note":
            return await handle_create_remote_note(arguments)
        elif name == "sync-remote-to-local":
            return await handle_sync_remote_to_local(arguments)
        elif name == "backfill-activities":
            return await handle_backfill_activities(arguments)
        elif name == "reload-server":
            return await handle_reload_server(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": str(e),
                        "tool": name,
                        "arguments": arguments,
                    },
                    indent=2,
                ),
            )
        ]


async def handle_weekly_planner(args: dict) -> list[TextContent]:
    """Generate weekly training plan."""
    from cyclisme_training_logs.weekly_planner import WeeklyPlanner

    week_id = args["week_id"]
    start_date_str = args["start_date"]
    provider = args.get("provider", "clipboard")

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()

    # Suppress all output to prevent JSON protocol pollution
    with suppress_stdout_stderr():
        planner = WeeklyPlanner(week_number=week_id, start_date=start_date, project_root=Path.cwd())

        # Collect metrics
        planner.current_metrics = planner.collect_current_metrics()
        planner.previous_week_bilan = planner.load_previous_week_bilan()
        planner.context_files = planner.load_context_files()

        # Generate prompt
        prompt = planner.generate_planning_prompt()

    result = {
        "week_id": week_id,
        "start_date": start_date_str,
        "status": "prompt_generated",
        "provider": provider,
        "prompt_length": len(prompt),
        "message": f"Planning prompt generated for {week_id}",
        "next_steps": [
            f"Copy prompt and paste to {provider}",
            "Generate 7 workouts",
            "Save workouts to file",
            "Run upload-workouts to sync to Intervals.icu",
        ],
    }

    if provider == "clipboard":
        result["prompt"] = prompt[:500] + "..." if len(prompt) > 500 else prompt

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_monthly_analysis(args: dict) -> list[TextContent]:
    """Generate monthly training analysis."""
    from cyclisme_training_logs.monthly_analysis import MonthlyAnalyzer

    month = args["month"]
    provider = args.get("provider", "mistral_api")
    no_ai = args.get("no_ai", False)

    # Suppress all output to prevent JSON protocol pollution
    with suppress_stdout_stderr():
        analyzer = MonthlyAnalyzer(month=month, provider=provider, no_ai=no_ai)
        report = analyzer.run()

    if not report:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"No planning data found for {month}"}, indent=2),
            )
        ]

    # Extract key metrics from report
    result = {
        "month": month,
        "report_length": len(report),
        "report": report,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_daily_sync(args: dict) -> list[TextContent]:
    """Sync with Intervals.icu."""
    from cyclisme_training_logs.daily_sync import DailySync

    check_date_str = args.get("date")

    if check_date_str:
        check_date = datetime.strptime(check_date_str, "%Y-%m-%d").date()
    else:
        check_date = date.today()

    # Setup paths
    from cyclisme_training_logs.config import get_data_config

    config = get_data_config()
    tracking_file = config.data_repo_path / "activities_tracking.json"
    reports_dir = config.data_repo_path / "daily-reports"

    sync = DailySync(
        tracking_file=tracking_file,
        reports_dir=reports_dir,
        enable_ai_analysis=False,
        enable_auto_servo=False,
        verbose=False,  # Disable prints to prevent MCP protocol pollution
    )

    # Suppress all output to prevent JSON protocol pollution
    with suppress_stdout_stderr():
        # Run sync - returns (new_activities, completed_activities)
        new_activities, completed_activities = sync.check_activities(check_date)

        # Mark new activities as analyzed
        if new_activities:
            for activity in new_activities:
                if activity is None:
                    continue
                sync.tracker.mark_analyzed(activity, datetime.now())

        # Auto-update session statuses using ALL completed activities (not just new ones)
        # This ensures status updates even for activities analyzed in previous runs
        activity_to_session_map = {}
        if completed_activities:
            activity_to_session_map = sync.update_completed_sessions(completed_activities)

    # Enrich result with activity details
    activities_details = []
    if completed_activities:
        for activity in completed_activities:
            if activity is None:
                continue
            activity_id = activity.get("id")
            activity_detail = {
                "activity_id": activity_id,
                "name": activity.get("name"),
                "type": activity.get("type"),
                "start_time": activity.get("start_date_local"),
                "tss": activity.get("icu_training_load"),
                "intensity_factor": activity.get("icu_intensity"),
                "duration_min": (
                    round(activity.get("moving_time", 0) / 60)
                    if activity.get("moving_time")
                    else None
                ),
                "distance_km": (
                    round(activity.get("distance", 0) / 1000, 1)
                    if activity.get("distance")
                    else None
                ),
                "average_watts": activity.get("average_watts"),
                "session_id": activity_to_session_map.get(activity_id),  # From matching
            }
            activities_details.append(activity_detail)

    result = {
        "date": check_date.isoformat(),
        "completed_activities": len(completed_activities) if completed_activities else 0,
        "new_activities": len(new_activities) if new_activities else 0,
        "activities": activities_details,  # Detailed activity info with session mapping
        "status": "completed",
        "message": f"Sync completed for {check_date.isoformat()}",
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_update_session(args: dict) -> list[TextContent]:
    """Update session status."""
    from cyclisme_training_logs.config import create_intervals_client
    from cyclisme_training_logs.planning.control_tower import planning_tower

    week_id = args["week_id"]
    session_id = args["session_id"]
    new_status = args["status"]
    reason = args.get("reason")
    sync_to_intervals = args.get("sync", False)

    # Track if we found session and its old status
    session_found = False
    old_status = None
    intervals_id = None
    session_date = None
    session_name = None
    session_description = None

    # Suppress all output to prevent JSON protocol pollution
    with suppress_stdout_stderr():
        # Update via Control Tower
        with planning_tower.modify_week(
            week_id,
            requesting_script="mcp-server",
            reason=f"MCP: Update {session_id} to {new_status}: {reason or 'N/A'}",
        ) as plan:
            for session in plan.planned_sessions:
                if session.session_id == session_id:
                    old_status = session.status
                    intervals_id = session.intervals_id
                    session_date = session.session_date
                    session_name = session.name
                    session_description = session.description

                    # PROTECTION: Never modify completed sessions in Intervals.icu
                    if sync_to_intervals and old_status == "completed":
                        raise ValueError(
                            f"Cannot sync session {session_id}: "
                            f"Status is 'completed'. Refusing to modify completed sessions."
                        )

                    # Set skip_reason BEFORE status (Pydantic validator)
                    if reason and new_status in ("skipped", "cancelled", "replaced"):
                        session.skip_reason = reason

                    session.status = new_status
                    session_found = True
                    break

            if not session_found:
                raise ValueError(f"Session {session_id} not found in {week_id}")

        # Sync to Intervals.icu if requested
        sync_result = None
        if sync_to_intervals and session_found:
            try:
                client = create_intervals_client()

                # Prepare event data
                # Determine start time based on day and session suffix
                day_of_week = session_date.weekday()  # 0=Monday, 5=Saturday
                session_day_part = session_id.split("-")[-1]  # e.g., "04" or "06a"

                # Check if session has letter suffix (double session)
                session_suffix = session_day_part[-1] if session_day_part[-1].isalpha() else None

                # Double session (a/b)
                if session_suffix == "a":
                    start_time = "09:00:00"  # Morning
                elif session_suffix == "b":
                    start_time = "15:00:00"  # Afternoon
                else:
                    # Saturday → 09:00, other days → 17:00
                    start_time = "09:00:00" if day_of_week == 5 else "17:00:00"

                event_data = {
                    "category": "WORKOUT",
                    "type": "VirtualRide",
                    "name": session_name,
                    "description": session_description,
                    "start_date_local": f"{session_date}T{start_time}",
                }

                if intervals_id:
                    # Update existing event
                    client.update_event(intervals_id, event_data)
                    sync_result = f"Updated Intervals.icu event {intervals_id}"
                else:
                    # Create new event
                    created = client.create_event(event_data)
                    if created and "id" in created:
                        new_intervals_id = created["id"]
                        # Save intervals_id back to planning
                        with planning_tower.modify_week(
                            week_id,
                            requesting_script="mcp-server",
                            reason=f"MCP: Save Intervals.icu ID {new_intervals_id} for {session_id}",
                        ) as plan:
                            for session in plan.planned_sessions:
                                if session.session_id == session_id:
                                    session.intervals_id = new_intervals_id
                                    break
                        sync_result = f"Created Intervals.icu event {new_intervals_id}"
                    else:
                        sync_result = "Failed to create Intervals.icu event"

            except Exception as e:
                sync_result = f"Sync error: {str(e)}"

    result = {
        "week_id": week_id,
        "session_id": session_id,
        "status": new_status,
        "reason": reason,
        "message": f"Session {session_id} updated to {new_status}",
        "synced": sync_to_intervals,
        "sync_result": sync_result if sync_to_intervals else None,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_list_weeks(args: dict) -> list[TextContent]:
    """List available weekly plannings."""
    from cyclisme_training_logs.config import get_data_config

    config = get_data_config()
    planning_dir = config.week_planning_dir

    limit = args.get("limit", 10)
    recent = args.get("recent", True)

    planning_files = sorted(planning_dir.glob("week_planning_S*.json"))

    if recent:
        planning_files = planning_files[::-1]

    weeks = []
    for planning_file in planning_files[:limit]:
        try:
            with open(planning_file, encoding="utf-8") as f:
                data = json.load(f)

            weeks.append(
                {
                    "week_id": data.get("week_id"),
                    "start_date": data.get("start_date"),
                    "end_date": data.get("end_date"),
                    "tss_target": data.get("tss_target", 0),
                    "sessions": len(data.get("planned_sessions", [])),
                }
            )
        except Exception:
            continue

    result = {
        "total_found": len(weeks),
        "showing": min(limit, len(weeks)),
        "weeks": weeks,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_get_metrics(args: dict) -> list[TextContent]:
    """Get current training metrics."""
    from cyclisme_training_logs.api.intervals_client import IntervalsClient
    from cyclisme_training_logs.config import get_intervals_config

    config = get_intervals_config()
    client = IntervalsClient(athlete_id=config.athlete_id, api_key=config.api_key)

    # Get latest wellness data
    today = date.today()
    oldest = (today - timedelta(days=7)).isoformat()
    newest = today.isoformat()

    wellness_data = client.get_wellness(oldest=oldest, newest=newest)

    if wellness_data:
        latest = wellness_data[0]  # Most recent
        result = {
            "date": latest.get("id"),
            "ctl": latest.get("ctl"),
            "atl": latest.get("atl"),
            "tsb": latest.get("tsb"),
            "rampRate": latest.get("rampRate"),
            "ctlLoad": latest.get("ctlLoad"),
            "atlLoad": latest.get("atlLoad"),
        }
    else:
        result = {"error": "No wellness data found"}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_get_week_details(args: dict) -> list[TextContent]:
    """Get detailed information about a specific week planning."""
    from cyclisme_training_logs.planning.control_tower import planning_tower

    week_id = args["week_id"]

    try:
        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            # Read planning via Control Tower
            plan = planning_tower.read_week(week_id)

        # Convert to dict for JSON serialization
        result = {
            "week_id": plan.week_id,
            "start_date": str(plan.start_date),
            "end_date": str(plan.end_date),
            "athlete_id": plan.athlete_id,
            "tss_target": plan.tss_target,
            "created_at": str(plan.created_at),
            "last_updated": str(plan.last_updated),
            "version": plan.version,
            "sessions": [
                {
                    "session_id": session.session_id,
                    "date": str(session.session_date),
                    "name": session.name,
                    "type": session.session_type,
                    "version": session.version,
                    "tss_planned": session.tss_planned,
                    "duration_min": session.duration_min,
                    "description": session.description,
                    "status": session.status,
                    "intervals_id": session.intervals_id,
                    "skip_reason": session.skip_reason,
                }
                for session in plan.planned_sessions
            ],
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except FileNotFoundError:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Planning file not found for week {week_id}"}, indent=2),
            )
        ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Error reading planning: {str(e)}"}, indent=2),
            )
        ]


async def handle_modify_session_details(args: dict) -> list[TextContent]:
    """Modify detailed information of a training session."""
    from cyclisme_training_logs.planning.control_tower import planning_tower

    week_id = args["week_id"]
    session_id = args["session_id"]

    # Extract optional fields
    name = args.get("name")
    session_type = args.get("type")
    description = args.get("description")
    tss_planned = args.get("tss_planned")
    duration_min = args.get("duration_min")

    # Build modification summary
    modifications = []
    if name:
        modifications.append(f"name={name}")
    if session_type:
        modifications.append(f"type={session_type}")
    if description:
        modifications.append("description updated")
    if tss_planned is not None:
        modifications.append(f"TSS={tss_planned}")
    if duration_min is not None:
        modifications.append(f"duration={duration_min}min")

    modification_summary = ", ".join(modifications) if modifications else "no changes"

    try:
        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            # Modify via Control Tower
            with planning_tower.modify_week(
                week_id,
                requesting_script="mcp-server",
                reason=f"MCP: Modify {session_id} details - {modification_summary}",
            ) as plan:
                session_found = False
                for session in plan.planned_sessions:
                    if session.session_id == session_id:
                        # 🛡️ PROTECTION: Refuse to modify completed sessions
                        if session.status == "completed":
                            raise ValueError(
                                f"⛔ PROTECTION: Cannot modify session {session_id} - "
                                f"Status is 'completed'. Completed sessions are protected from modification."
                            )

                        # Update fields if provided
                        if name:
                            session.name = name
                        if session_type:
                            session.session_type = session_type
                        if description:
                            session.description = description
                        if tss_planned is not None:
                            session.tss_planned = tss_planned
                        if duration_min is not None:
                            session.duration_min = duration_min

                        session_found = True
                        break

                if not session_found:
                    raise ValueError(f"Session {session_id} not found in {week_id}")

        result = {
            "status": "success",
            "week_id": week_id,
            "session_id": session_id,
            "modifications": modifications,
            "message": f"Session {session_id} updated successfully",
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except FileNotFoundError:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Planning file not found for week {week_id}"}, indent=2),
            )
        ]
    except ValueError as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2),
            )
        ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Error modifying session: {str(e)}"}, indent=2),
            )
        ]


async def handle_create_session(args: dict) -> list[TextContent]:
    """Create a new training session."""
    from datetime import datetime

    from cyclisme_training_logs.planning.control_tower import planning_tower
    from cyclisme_training_logs.planning.models import Session

    week_id = args["week_id"]
    session_date_str = args["session_date"]
    session_date = datetime.strptime(session_date_str, "%Y-%m-%d").date()

    # Extract optional fields with defaults
    name = args.get("name", "NewSession")
    session_type = args.get("type", "END")
    description = args.get("description", "À définir")
    tss_planned = args.get("tss_planned", 0)
    duration_min = args.get("duration_min", 0)

    try:
        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            # Modify via Control Tower
            with planning_tower.modify_week(
                week_id,
                requesting_script="mcp-server",
                reason=f"MCP: Create new session on {session_date_str} - {name}",
            ) as plan:
                # Generate session_id
                # Find day of week (Monday=0, Sunday=6)
                day_num = session_date.weekday()
                day_index = day_num + 1  # Convert to 1-based (Monday=1, Sunday=7)

                # Find existing sessions on this date
                existing_sessions = [
                    s for s in plan.planned_sessions if s.session_date == session_date
                ]

                if not existing_sessions:
                    # First session for this day
                    session_id = f"{week_id}-{day_index:02d}"
                else:
                    # Multiple sessions - add letter suffix
                    # Find next available letter (a, b, c, etc.)
                    existing_suffixes = []
                    for s in existing_sessions:
                        # Extract suffix from session_id (e.g., "S081-06a" -> "a")
                        if len(s.session_id.split("-")[1]) > 2:
                            suffix = s.session_id.split("-")[1][2]
                            existing_suffixes.append(suffix)

                    if not existing_suffixes:
                        # First session has no suffix, second gets 'a'
                        session_id = f"{week_id}-{day_index:02d}a"
                    else:
                        # Find next letter
                        next_letter = chr(ord(max(existing_suffixes)) + 1)
                        session_id = f"{week_id}-{day_index:02d}{next_letter}"

                # Create new session
                new_session = Session(
                    session_id=session_id,
                    date=session_date,
                    name=name,
                    type=session_type,
                    version="V001",
                    tss_planned=tss_planned,
                    duration_min=duration_min,
                    description=description,
                    status="planned",
                )

                # Add to plan (insert in chronological order)
                plan.planned_sessions.append(new_session)
                plan.planned_sessions.sort(key=lambda s: (s.session_date, s.session_id))

        result = {
            "status": "success",
            "week_id": week_id,
            "session_id": session_id,
            "session_date": session_date_str,
            "name": name,
            "type": session_type,
            "message": f"Session {session_id} created successfully",
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except FileNotFoundError:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Planning file not found for week {week_id}"}, indent=2),
            )
        ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Error creating session: {str(e)}"}, indent=2),
            )
        ]


async def handle_delete_session(args: dict) -> list[TextContent]:
    """Delete a training session."""
    from cyclisme_training_logs.planning.control_tower import planning_tower

    week_id = args["week_id"]
    session_id = args["session_id"]

    try:
        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            # Modify via Control Tower
            with planning_tower.modify_week(
                week_id,
                requesting_script="mcp-server",
                reason=f"MCP: Delete session {session_id}",
            ) as plan:
                # Find and remove session
                session_found = False
                for i, session in enumerate(plan.planned_sessions):
                    if session.session_id == session_id:
                        # 🛡️ PROTECTION 1: Refuse to delete completed sessions
                        if session.status == "completed":
                            raise ValueError(
                                f"⛔ PROTECTION: Cannot delete session {session_id} - "
                                f"Status is 'completed'. Completed sessions are protected from deletion."
                            )

                        # 🛡️ PROTECTION 2: Warn about deleting synced sessions
                        if session.intervals_id:
                            raise ValueError(
                                f"⛔ PROTECTION: Cannot delete session {session_id} - "
                                f"Has intervals_id={session.intervals_id}. "
                                f"Session is synced with Intervals.icu. "
                                f"Delete from Intervals.icu first or use force parameter."
                            )

                        plan.planned_sessions.pop(i)
                        session_found = True
                        break

                if not session_found:
                    raise ValueError(f"Session {session_id} not found in {week_id}")

        result = {
            "status": "success",
            "week_id": week_id,
            "session_id": session_id,
            "message": f"Session {session_id} deleted successfully",
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except FileNotFoundError:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Planning file not found for week {week_id}"}, indent=2),
            )
        ]
    except ValueError as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2),
            )
        ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Error deleting session: {str(e)}"}, indent=2),
            )
        ]


async def handle_duplicate_session(args: dict) -> list[TextContent]:
    """Duplicate an existing session to a new date."""
    from datetime import datetime

    from cyclisme_training_logs.planning.control_tower import planning_tower
    from cyclisme_training_logs.planning.models import Session

    week_id = args["week_id"]
    source_session_id = args["source_session_id"]
    target_date_str = args["target_date"]
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()

    try:
        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            # Modify via Control Tower
            with planning_tower.modify_week(
                week_id,
                requesting_script="mcp-server",
                reason=f"MCP: Duplicate {source_session_id} to {target_date_str}",
            ) as plan:
                # Find source session
                source_session = None
                for session in plan.planned_sessions:
                    if session.session_id == source_session_id:
                        source_session = session
                        break

                if not source_session:
                    raise ValueError(f"Source session {source_session_id} not found in {week_id}")

                # Generate new session_id for target date
                day_num = target_date.weekday()
                day_index = day_num + 1

                existing_sessions = [
                    s for s in plan.planned_sessions if s.session_date == target_date
                ]

                if not existing_sessions:
                    new_session_id = f"{week_id}-{day_index:02d}"
                else:
                    existing_suffixes = []
                    for s in existing_sessions:
                        if len(s.session_id.split("-")[1]) > 2:
                            suffix = s.session_id.split("-")[1][2]
                            existing_suffixes.append(suffix)

                    if not existing_suffixes:
                        new_session_id = f"{week_id}-{day_index:02d}a"
                    else:
                        next_letter = chr(ord(max(existing_suffixes)) + 1)
                        new_session_id = f"{week_id}-{day_index:02d}{next_letter}"

                # Create duplicate session
                new_session = Session(
                    session_id=new_session_id,
                    date=target_date,
                    name=source_session.name,
                    type=source_session.session_type,
                    version=source_session.version,
                    tss_planned=source_session.tss_planned,
                    duration_min=source_session.duration_min,
                    description=source_session.description,
                    status="planned",  # Reset status
                    # Don't copy intervals_id, description_hash, skip_reason
                )

                # Add to plan
                plan.planned_sessions.append(new_session)
                plan.planned_sessions.sort(key=lambda s: (s.session_date, s.session_id))

        result = {
            "status": "success",
            "week_id": week_id,
            "source_session_id": source_session_id,
            "new_session_id": new_session_id,
            "target_date": target_date_str,
            "message": f"Session duplicated successfully: {source_session_id} -> {new_session_id}",
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except FileNotFoundError:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Planning file not found for week {week_id}"}, indent=2),
            )
        ]
    except ValueError as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2),
            )
        ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Error duplicating session: {str(e)}"}, indent=2),
            )
        ]


async def handle_swap_sessions(args: dict) -> list[TextContent]:
    """Swap the dates of two sessions."""
    from cyclisme_training_logs.planning.control_tower import planning_tower

    week_id = args["week_id"]
    session_id_1 = args["session_id_1"]
    session_id_2 = args["session_id_2"]

    try:
        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            # Modify via Control Tower
            with planning_tower.modify_week(
                week_id,
                requesting_script="mcp-server",
                reason=f"MCP: Swap sessions {session_id_1} <-> {session_id_2}",
            ) as plan:
                # Find both sessions
                session_1 = None
                session_2 = None

                for session in plan.planned_sessions:
                    if session.session_id == session_id_1:
                        session_1 = session
                    elif session.session_id == session_id_2:
                        session_2 = session

                if not session_1:
                    raise ValueError(f"Session {session_id_1} not found in {week_id}")
                if not session_2:
                    raise ValueError(f"Session {session_id_2} not found in {week_id}")

                # 🛡️ PROTECTION: Refuse to swap if either session is completed
                if session_1.status == "completed":
                    raise ValueError(
                        f"⛔ PROTECTION: Cannot swap session {session_id_1} - "
                        f"Status is 'completed'. Completed sessions are protected from modification."
                    )
                if session_2.status == "completed":
                    raise ValueError(
                        f"⛔ PROTECTION: Cannot swap session {session_id_2} - "
                        f"Status is 'completed'. Completed sessions are protected from modification."
                    )

                # Swap dates
                temp_date = session_1.session_date
                session_1.session_date = session_2.session_date
                session_2.session_date = temp_date

                # Re-sort sessions
                plan.planned_sessions.sort(key=lambda s: (s.session_date, s.session_id))

        result = {
            "status": "success",
            "week_id": week_id,
            "session_id_1": session_id_1,
            "session_id_2": session_id_2,
            "message": f"Sessions swapped successfully: {session_id_1} <-> {session_id_2}",
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except FileNotFoundError:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Planning file not found for week {week_id}"}, indent=2),
            )
        ]
    except ValueError as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2),
            )
        ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Error swapping sessions: {str(e)}"}, indent=2),
            )
        ]


async def handle_attach_workout(args: dict) -> list[TextContent]:
    """Attach a workout file to a session."""
    from cyclisme_training_logs.config import get_data_config

    session_id = args["session_id"]
    workout_name = args["workout_name"]
    workout_type = args.get("workout_type", "WKT")
    content = args["content"]
    version = args.get("version", "V001")
    extension = args.get("extension", "zwo")

    try:
        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            # Get workouts directory
            config = get_data_config()
            workouts_dir = config.data_repo_path / "workouts"
            workouts_dir.mkdir(parents=True, exist_ok=True)

            # Build filename: {session_id}-{type}-{name}-{version}.{ext}
            filename = f"{session_id}-{workout_type}-{workout_name}-{version}.{extension}"
            file_path = workouts_dir / filename

            # Write workout file
            file_path.write_text(content, encoding="utf-8")

        result = {
            "status": "success",
            "session_id": session_id,
            "filename": filename,
            "path": str(file_path),
            "message": f"Workout attached successfully: {filename}",
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Error attaching workout: {str(e)}"}, indent=2),
            )
        ]


async def handle_get_workout(args: dict) -> list[TextContent]:
    """Get workout file content for a session."""
    from cyclisme_training_logs.config import get_data_config

    session_id = args["session_id"]

    try:
        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            # Get workouts directory
            config = get_data_config()
            workouts_dir = config.data_repo_path / "workouts"

            # Find workout file(s) for this session
            # Pattern: {session_id}-*.{zwo,mrc,erg}
            workout_files = list(workouts_dir.glob(f"{session_id}-*"))

            if not workout_files:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": f"No workout file found for session {session_id}"}, indent=2
                        ),
                    )
                ]

            # If multiple files, return the first one (or could return all)
            workout_file = workout_files[0]

            # Read workout content
            content = workout_file.read_text(encoding="utf-8")

        result = {
            "status": "success",
            "session_id": session_id,
            "filename": workout_file.name,
            "extension": workout_file.suffix[1:],  # Remove leading dot
            "content": content,
            "message": f"Workout retrieved: {workout_file.name}",
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Error retrieving workout: {str(e)}"}, indent=2),
            )
        ]


async def handle_sync_week_to_intervals(args: dict) -> list[TextContent]:
    """Synchronize week planning to Intervals.icu."""
    from cyclisme_training_logs.config import create_intervals_client
    from cyclisme_training_logs.planning.control_tower import planning_tower

    week_id = args["week_id"]
    dry_run = args.get("dry_run", False)
    force_update = args.get("force_update", False)

    try:
        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            # Read local planning
            plan = planning_tower.read_week(week_id)

            # Create Intervals.icu client
            client = create_intervals_client()

            # Get remote events for this week
            start_date = str(plan.start_date)
            end_date = str(plan.end_date)
            remote_events = client.get_events(oldest=start_date, newest=end_date)

            # Filter to workouts only
            remote_workouts = {e["id"]: e for e in remote_events if e.get("category") == "WORKOUT"}

            # Track changes
            to_create = []
            to_update = []
            to_skip_completed = []
            warnings = []
            errors = []

            # Process each session
            for session in plan.planned_sessions:
                # PROTECTION: Never modify completed sessions
                if session.status == "completed":
                    to_skip_completed.append(
                        {
                            "session_id": session.session_id,
                            "name": session.name,
                            "reason": "Session completed - protected from sync",
                        }
                    )
                    continue

                # Prepare event data
                # Determine start time based on day and session suffix
                day_of_week = session.session_date.weekday()  # 0=Monday, 5=Saturday
                session_day_part = session.session_id.split("-")[-1]  # e.g., "04" or "06a"

                # Check if session has letter suffix (double session)
                session_suffix = session_day_part[-1] if session_day_part[-1].isalpha() else None

                # Double session (a/b)
                if session_suffix == "a":
                    start_time = "09:00:00"  # Morning
                elif session_suffix == "b":
                    start_time = "15:00:00"  # Afternoon
                else:
                    # Saturday → 09:00, other days → 17:00
                    start_time = "09:00:00" if day_of_week == 5 else "17:00:00"

                event_data = {
                    "category": "WORKOUT",
                    "type": "VirtualRide",
                    "name": session.name,
                    "description": session.description,
                    "start_date_local": f"{session.session_date}T{start_time}",
                }

                if session.intervals_id:
                    # Check if event exists remotely
                    if session.intervals_id in remote_workouts:
                        # Event exists - check for conflicts
                        remote_event = remote_workouts[session.intervals_id]

                        # 🛡️ VALIDATION: Detect if remote was manually modified
                        remote_name = remote_event.get("name", "")
                        remote_desc = remote_event.get("description", "")
                        local_name = session.name
                        local_desc = session.description

                        has_remote_changes = remote_name != local_name or remote_desc != local_desc

                        if has_remote_changes and not force_update:
                            # Remote has been manually modified - warn about conflict
                            warnings.append(
                                {
                                    "session_id": session.session_id,
                                    "intervals_id": session.intervals_id,
                                    "type": "remote_modification_detected",
                                    "message": f"⚠️ Remote event {session.intervals_id} has been manually modified in Intervals.icu",
                                    "local_name": local_name,
                                    "remote_name": remote_name,
                                    "suggestion": "Use force_update=true to overwrite remote changes",
                                }
                            )
                            # Skip this session unless force_update
                            continue

                        # Check if update needed
                        needs_update = force_update or has_remote_changes

                        if needs_update:
                            to_update.append(
                                {
                                    "session_id": session.session_id,
                                    "intervals_id": session.intervals_id,
                                    "name": session.name,
                                    "event_data": event_data,
                                }
                            )
                    else:
                        # intervals_id set but event doesn't exist remotely
                        # Create new event
                        to_create.append(
                            {
                                "session_id": session.session_id,
                                "name": session.name,
                                "event_data": event_data,
                            }
                        )
                else:
                    # No intervals_id - create new event
                    to_create.append(
                        {
                            "session_id": session.session_id,
                            "name": session.name,
                            "event_data": event_data,
                        }
                    )

            # Apply changes if not dry run
            created_count = 0
            updated_count = 0

            if not dry_run:
                # Create new events
                for item in to_create:
                    try:
                        created = client.create_event(item["event_data"])

                        # Debug: Log what we got back
                        if created is None:
                            errors.append(
                                f"Failed to create {item['session_id']}: API returned None "
                                f"(check logs for HTTP errors)"
                            )
                        elif "id" not in created:
                            errors.append(
                                f"Failed to create {item['session_id']}: Response missing 'id' field. "
                                f"Got keys: {list(created.keys())}, "
                                f"Response preview: {str(created)[:200]}"
                            )
                        else:
                            new_intervals_id = created["id"]

                            # Save intervals_id back to planning
                            with planning_tower.modify_week(
                                week_id,
                                requesting_script="mcp-server",
                                reason=f"MCP: Sync - Save Intervals.icu ID {new_intervals_id} for {item['session_id']}",
                            ) as plan:
                                for session in plan.planned_sessions:
                                    if session.session_id == item["session_id"]:
                                        session.intervals_id = new_intervals_id
                                        break

                            created_count += 1

                    except Exception as e:
                        errors.append(f"Error creating {item['session_id']}: {str(e)}")

                # Update existing events
                for item in to_update:
                    try:
                        updated = client.update_event(item["intervals_id"], item["event_data"])
                        if updated:
                            updated_count += 1
                        else:
                            errors.append(f"Failed to update {item['session_id']}")

                    except Exception as e:
                        errors.append(f"Error updating {item['session_id']}: {str(e)}")

        # Build result
        # Determine status based on warnings and errors
        if errors:
            status = "partial_success"
        elif warnings:
            status = "success_with_warnings"
        else:
            status = "success"

        result = {
            "status": status,
            "week_id": week_id,
            "dry_run": dry_run,
            "summary": {
                "to_create": len(to_create),
                "to_update": len(to_update),
                "skipped_completed": len(to_skip_completed),
                "warnings": len(warnings),
                "created": created_count if not dry_run else 0,
                "updated": updated_count if not dry_run else 0,
                "errors": len(errors),
            },
            "details": {
                "to_create": [
                    {"session_id": item["session_id"], "name": item["name"]} for item in to_create
                ],
                "to_update": [
                    {
                        "session_id": item["session_id"],
                        "intervals_id": item["intervals_id"],
                        "name": item["name"],
                    }
                    for item in to_update
                ],
                "skipped_completed": to_skip_completed,
            },
            "warnings": warnings if warnings else None,
            "errors": errors if errors else None,
            "message": f"Sync {'preview' if dry_run else 'completed'} for {week_id}",
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except FileNotFoundError:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Planning file not found for week {week_id}"}, indent=2),
            )
        ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Sync error: {str(e)}"}, indent=2),
            )
        ]


async def handle_validate_workout(args: dict) -> list[TextContent]:
    """Validate Intervals.icu workout format."""
    from cyclisme_training_logs.intervals_format_validator import IntervalsFormatValidator

    workout_text = args["workout_text"]
    auto_fix = args.get("auto_fix", False)

    try:
        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            validator = IntervalsFormatValidator()
            is_valid, errors, warnings = validator.validate_workout(workout_text)

            result = {
                "valid": is_valid,
                "errors": errors,
                "warnings": warnings,
            }

            # Si auto_fix demandé et qu'il y a des warnings
            if auto_fix and (errors or warnings):
                corrected_text = validator.fix_repetition_format(workout_text)

                # Revalider le texte corrigé
                is_valid_after, errors_after, warnings_after = validator.validate_workout(
                    corrected_text
                )

                result["auto_fixed"] = True
                result["corrected_workout"] = corrected_text
                result["valid_after_fix"] = is_valid_after
                result["errors_after_fix"] = errors_after
                result["warnings_after_fix"] = warnings_after

                if is_valid_after:
                    result["message"] = "Workout corrected and validated successfully"
                else:
                    result["message"] = (
                        "Some errors remain after auto-fix (manual correction needed)"
                    )
            else:
                result["auto_fixed"] = False
                if is_valid:
                    result["message"] = "Workout format is valid"
                else:
                    result["message"] = (
                        "Workout format has errors (use auto_fix:true to attempt automatic correction)"
                    )

        return [
            TextContent(
                type="text",
                text=json.dumps(result, indent=2),
            )
        ]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Validation error: {str(e)}"}, indent=2),
            )
        ]


async def handle_delete_remote_session(args: dict) -> list[TextContent]:
    """Delete a workout event from Intervals.icu and update local planning via Control Tower."""
    from cyclisme_training_logs.config import create_intervals_client
    from cyclisme_training_logs.planning.control_tower import planning_tower

    event_id = args["event_id"]
    confirm = args.get("confirm", False)

    # Safety check: require explicit confirmation
    if not confirm:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": "Deletion requires explicit confirmation",
                        "event_id": event_id,
                        "message": "Set confirm=true to proceed with deletion",
                        "warning": "This action is PERMANENT and cannot be undone",
                    },
                    indent=2,
                ),
            )
        ]

    try:
        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            # 🛡️ PROTECTION: Find session associated with this event
            # Search through all weeks to find if this intervals_id is associated with a session
            found_week_id = None
            found_session = None

            if planning_tower.planning_dir.exists():
                for week_file in planning_tower.planning_dir.glob("week_planning_S???.json"):
                    try:
                        week_id = week_file.stem.replace("week_planning_", "")
                        plan = planning_tower.read_week(week_id)
                        for session in plan.planned_sessions:
                            if session.intervals_id == event_id:
                                # Found matching session - check if completed
                                if session.status == "completed":
                                    return [
                                        TextContent(
                                            type="text",
                                            text=json.dumps(
                                                {
                                                    "error": "Cannot delete completed session",
                                                    "event_id": event_id,
                                                    "session_id": session.session_id,
                                                    "session_name": session.name,
                                                    "status": session.status,
                                                    "message": f"🛡️ PROTECTION: Session {session.session_id} is COMPLETED and cannot be deleted from Intervals.icu",
                                                    "reason": "Completed sessions are protected to preserve training history",
                                                },
                                                indent=2,
                                            ),
                                        )
                                    ]
                                # Session exists but not completed - store for later modification
                                found_week_id = week_id
                                found_session = session
                                break
                    except Exception:
                        # Skip weeks that can't be read
                        continue

                    if found_session:
                        break

            # Create Intervals.icu client
            client = create_intervals_client()

            # Attempt deletion on Intervals.icu
            success = client.delete_event(event_id)

            if not success:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": False,
                                "event_id": event_id,
                                "message": f"❌ Failed to delete event {event_id} from Intervals.icu (check logs for details)",
                            },
                            indent=2,
                        ),
                    )
                ]

            # WRITE-BACK: If we found a local session, update it via Control Tower to remove intervals_id
            local_update_status = None
            if found_week_id and found_session:
                try:
                    from cyclisme_training_logs.planning.models import Session

                    # Use Control Tower context manager to modify the planning
                    with planning_tower.modify_week(
                        week_id=found_week_id,
                        requesting_script="delete-remote-session",
                        reason=f"Write-back: removed intervals_id after deleting event {event_id}",
                    ) as plan:
                        updated_sessions = []
                        for session in plan.planned_sessions:
                            if session.intervals_id == event_id:
                                # Remove intervals_id and reset to planned if it was uploaded
                                session_dict = session.model_dump()
                                session_dict["intervals_id"] = None
                                if session_dict["status"] == "uploaded":
                                    session_dict["status"] = "planned"
                                updated_session = Session(**session_dict)
                                updated_sessions.append(updated_session)
                            else:
                                updated_sessions.append(session)

                        plan.planned_sessions = updated_sessions

                    local_update_status = {
                        "updated": True,
                        "week_id": found_week_id,
                        "session_id": found_session.session_id,
                        "message": f"🔄 Local planning updated: intervals_id removed from {found_session.session_id}",
                    }
                except Exception as e:
                    local_update_status = {
                        "updated": False,
                        "error": str(e),
                        "message": f"⚠️ Event deleted from Intervals.icu but failed to update local planning: {e}",
                    }

            result = {
                "success": True,
                "event_id": event_id,
                "message": f"✅ Event {event_id} deleted successfully from Intervals.icu",
                "local_planning_update": local_update_status,
            }

        return [
            TextContent(
                type="text",
                text=json.dumps(result, indent=2),
            )
        ]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Delete error: {str(e)}",
                        "event_id": event_id,
                    },
                    indent=2,
                ),
            )
        ]


async def handle_list_remote_events(args: dict) -> list[TextContent]:
    """List all events from Intervals.icu for a date range."""
    from cyclisme_training_logs.config import create_intervals_client

    start_date = args["start_date"]
    end_date = args["end_date"]
    category_filter = args.get("category")

    try:
        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            # Create Intervals.icu client
            client = create_intervals_client()

            # Fetch events
            events = client.get_events(oldest=start_date, newest=end_date)

            # Filter by category if specified
            if category_filter:
                events = [e for e in events if e.get("category") == category_filter]

            # Format results with relevant fields
            formatted_events = []
            for event in events:
                formatted_event = {
                    "id": event.get("id"),
                    "category": event.get("category"),
                    "name": event.get("name"),
                    "description": event.get("description", "")[:100],  # First 100 chars
                    "start_date_local": event.get("start_date_local"),
                    "type": event.get("type"),
                }
                formatted_events.append(formatted_event)

            result = {
                "start_date": start_date,
                "end_date": end_date,
                "total_events": len(formatted_events),
                "events": formatted_events,
            }

            if category_filter:
                result["filtered_by"] = category_filter

        return [
            TextContent(
                type="text",
                text=json.dumps(result, indent=2),
            )
        ]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Failed to list remote events: {str(e)}",
                        "start_date": start_date,
                        "end_date": end_date,
                    },
                    indent=2,
                ),
            )
        ]


async def handle_get_activity_details(args: dict) -> list[TextContent]:
    """Get complete details for a completed activity from Intervals.icu."""
    from cyclisme_training_logs.config import create_intervals_client

    activity_id = args["activity_id"]
    include_streams = args.get("include_streams", False)

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()

            # Get activity details
            activity = client.get_activity(activity_id)

            # Get power metrics (calculate from streams if API doesn't provide)
            average_watts = activity.get("average_watts")
            weighted_average_watts = activity.get("weighted_average_watts")

            # Fetch streams once if needed (for power calculation or decoupling)
            streams = None
            need_streams = (
                average_watts is None
                or weighted_average_watts is None
                or activity.get("average_heartrate")
                is not None  # Has HR data, can calculate decoupling
            )

            if need_streams:
                try:
                    streams = client.get_activity_streams(activity_id)
                except Exception:
                    streams = None

            # Calculate power metrics from streams if API doesn't provide them
            if (average_watts is None or weighted_average_watts is None) and streams:
                try:
                    watts_stream = next((s for s in streams if s["type"] == "watts"), None)

                    if watts_stream and watts_stream["data"]:
                        watts_data = watts_stream["data"]

                        # Calculate average watts (excluding zeros for stopped periods)
                        if average_watts is None:
                            non_zero_watts = [w for w in watts_data if w > 0]
                            if non_zero_watts:
                                average_watts = round(sum(non_zero_watts) / len(non_zero_watts), 1)

                        # Calculate Normalized Power (NP) using 30s rolling average
                        if weighted_average_watts is None and len(watts_data) > 30:
                            # 30-second rolling average (assuming 1Hz sampling)
                            rolling_avgs = []
                            for i in range(len(watts_data) - 29):
                                window = watts_data[i : i + 30]
                                rolling_avgs.append(sum(window) / 30)

                            # NP formula: (average of 4th power)^(1/4)
                            if rolling_avgs:
                                fourth_powers = [p**4 for p in rolling_avgs]
                                avg_fourth = sum(fourth_powers) / len(fourth_powers)
                                weighted_average_watts = round(avg_fourth ** (1 / 4), 1)
                except Exception:
                    # Silently fail - use API values (None) if calculation fails
                    pass

            # Calculate cardiovascular decoupling (Pw:HR drift) from streams if available
            cardiovascular_decoupling = None
            if streams:
                try:
                    watts_stream = next((s for s in streams if s["type"] == "watts"), None)
                    hr_stream = next((s for s in streams if s["type"] == "heartrate"), None)

                    if (
                        watts_stream
                        and hr_stream
                        and watts_stream["data"]
                        and hr_stream["data"]
                        and len(watts_stream["data"]) > 60
                        and weighted_average_watts is not None
                    ):
                        watts_data = watts_stream["data"]
                        hr_data = hr_stream["data"]

                        # Ensure both streams have the same length
                        min_len = min(len(watts_data), len(hr_data))
                        watts_data = watts_data[:min_len]
                        hr_data = hr_data[:min_len]

                        # Split into two halves
                        midpoint = min_len // 2

                        # First half
                        watts_half1 = watts_data[:midpoint]
                        hr_half1 = hr_data[:midpoint]

                        # Second half
                        watts_half2 = watts_data[midpoint:]
                        hr_half2 = hr_data[midpoint:]

                        # Calculate NP for each half
                        # Note: Guaranteed len(watts) >= 30 because we check len(watts_data) > 60
                        def calc_np(watts):
                            rolling_avgs = []
                            for i in range(len(watts) - 29):
                                window = watts[i : i + 30]
                                rolling_avgs.append(sum(window) / 30)
                            fourth_powers = [p**4 for p in rolling_avgs]
                            avg_fourth = sum(fourth_powers) / len(fourth_powers)
                            return avg_fourth ** (1 / 4)

                        np_half1 = calc_np(watts_half1)
                        np_half2 = calc_np(watts_half2)

                        # Calculate average HR for each half (exclude zeros)
                        hr_half1_valid = [hr for hr in hr_half1 if hr > 0]
                        hr_half2_valid = [hr for hr in hr_half2 if hr > 0]

                        avg_hr_half1 = (
                            sum(hr_half1_valid) / len(hr_half1_valid) if hr_half1_valid else None
                        )
                        avg_hr_half2 = (
                            sum(hr_half2_valid) / len(hr_half2_valid) if hr_half2_valid else None
                        )

                        # Calculate Pw:HR ratios
                        if (
                            np_half1
                            and np_half2
                            and avg_hr_half1
                            and avg_hr_half2
                            and avg_hr_half1 > 0
                        ):
                            ratio_half1 = np_half1 / avg_hr_half1
                            ratio_half2 = np_half2 / avg_hr_half2

                            # Decoupling % = (ratio_2 - ratio_1) / ratio_1 * 100
                            cardiovascular_decoupling = round(
                                ((ratio_half2 - ratio_half1) / ratio_half1) * 100, 1
                            )
                except Exception:
                    # Silently fail - decoupling calculation is optional
                    pass

            # Format result
            result = {
                "id": activity.get("id"),
                "name": activity.get("name"),
                "start_date_local": activity.get("start_date_local"),
                "type": activity.get("type"),
                "moving_time": activity.get("moving_time"),
                "distance": activity.get("distance"),
                "total_elevation_gain": activity.get("total_elevation_gain"),
                "icu_training_load": activity.get("icu_training_load"),  # TSS
                "icu_intensity": activity.get("icu_intensity"),  # IF
                "average_watts": average_watts,
                "weighted_average_watts": weighted_average_watts,
                "average_heartrate": activity.get("average_heartrate"),
                "average_cadence": activity.get("average_cadence"),
                "cardiovascular_decoupling": cardiovascular_decoupling,
                "description": activity.get("description", ""),
                "paired_event_id": activity.get("paired_event_id"),
            }

            # Include streams if requested
            if include_streams:
                streams = client.get_activity_streams(activity_id)
                result["streams"] = [
                    {"type": s["type"], "data_points": len(s["data"])} for s in streams
                ]

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Failed to get activity details: {str(e)}",
                        "activity_id": activity_id,
                    },
                    indent=2,
                ),
            )
        ]


async def handle_update_remote_session(args: dict) -> list[TextContent]:
    """Update an existing workout event on Intervals.icu with write-back to local planning."""
    from datetime import datetime

    from cyclisme_training_logs.config import create_intervals_client
    from cyclisme_training_logs.planning.control_tower import planning_tower
    from cyclisme_training_logs.planning.models import Session

    event_id = args["event_id"]
    updates = args["updates"]

    try:
        with suppress_stdout_stderr():
            # Find which week/session this event belongs to
            target_week_id = None
            target_session = None

            if planning_tower.planning_dir.exists():
                for week_file in planning_tower.planning_dir.glob("week_planning_S???.json"):
                    try:
                        week_id = week_file.stem.replace("week_planning_", "")
                        plan = planning_tower.read_week(week_id)
                        for session in plan.planned_sessions:
                            if session.intervals_id == event_id:
                                # PROTECTION: Check if completed
                                if session.status == "completed":
                                    return [
                                        TextContent(
                                            type="text",
                                            text=json.dumps(
                                                {
                                                    "error": "Cannot update completed session",
                                                    "event_id": event_id,
                                                    "session_id": session.session_id,
                                                    "message": f"🛡️ PROTECTION: Session {session.session_id} is COMPLETED",
                                                },
                                                indent=2,
                                            ),
                                        )
                                    ]
                                target_week_id = week_id
                                target_session = session
                                break
                        if target_week_id:
                            break
                    except Exception:
                        continue

            # Update on Intervals.icu
            client = create_intervals_client()
            updated_event = client.update_event(event_id, updates)

            if updated_event:
                # WRITE-BACK: Update local planning if we found the session
                if target_week_id and target_session:
                    with planning_tower.modify_week(
                        target_week_id,
                        requesting_script="update-remote-session",
                        reason=f"Write-back from Intervals.icu update: {list(updates.keys())}",
                    ) as plan:
                        # Find and update the session
                        updated_sessions = []
                        for session in plan.planned_sessions:
                            if session.session_id == target_session.session_id:
                                # Map Intervals.icu fields to local planning fields
                                session_dict = session.model_dump()

                                if "name" in updates:
                                    session_dict["name"] = (
                                        updates["name"]
                                        .split("-")[-1]
                                        .replace("-V001", "")
                                        .replace("-V002", "")
                                        .replace("-V003", "")
                                    )

                                if "start_date_local" in updates:
                                    # Extract date from datetime string (YYYY-MM-DDTHH:MM:SS)
                                    date_str = updates["start_date_local"].split("T")[0]
                                    session_dict["session_date"] = datetime.strptime(
                                        date_str, "%Y-%m-%d"
                                    ).date()

                                if "description" in updates:
                                    session_dict["description"] = updates["description"]

                                updated_session = Session(**session_dict)
                                updated_sessions.append(updated_session)
                            else:
                                updated_sessions.append(session)

                        plan.planned_sessions = updated_sessions

                result = {
                    "success": True,
                    "event_id": event_id,
                    "updated_fields": list(updates.keys()),
                    "local_planning_updated": target_week_id is not None,
                    "week_id": target_week_id,
                    "session_id": target_session.session_id if target_session else None,
                    "message": f"✅ Event {event_id} updated successfully"
                    + (" (+ local planning)" if target_week_id else ""),
                }
            else:
                result = {
                    "success": False,
                    "event_id": event_id,
                    "message": f"❌ Failed to update event {event_id}",
                }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"error": f"Update error: {str(e)}", "event_id": event_id},
                    indent=2,
                ),
            )
        ]


async def handle_get_athlete_profile(args: dict) -> list[TextContent]:
    """Get current athlete profile from Intervals.icu."""
    from cyclisme_training_logs.config import create_intervals_client

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()
            athlete = client.get_athlete()

            # Format result with key metrics
            result = {
                "name": athlete.get("name"),
                "ftp": athlete.get("ftp"),
                "weight": athlete.get("weight"),
                "max_hr": athlete.get("max_hr"),
                "resting_hr": athlete.get("resting_hr"),
                "fthr": athlete.get("fthr"),
                "ctl": athlete.get("ctl"),
                "atl": athlete.get("atl"),
                "ramp_rate": athlete.get("ramp_rate"),
                "weight_class": athlete.get("weight_class"),
                "power_zones": athlete.get("power_zones"),
                "hr_zones": athlete.get("hr_zones"),
            }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Failed to get athlete profile: {str(e)}"}, indent=2),
            )
        ]


async def handle_update_athlete_profile(args: dict) -> list[TextContent]:
    """Update athlete profile on Intervals.icu."""
    from cyclisme_training_logs.config import create_intervals_client

    updates = args["updates"]

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()
            updated_athlete = client.update_athlete(updates)

            result = {
                "success": True,
                "updated_fields": list(updates.keys()),
                "message": "✅ Athlete profile updated successfully",
                "current_values": {field: updated_athlete.get(field) for field in updates.keys()},
            }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"error": f"Failed to update athlete profile: {str(e)}", "updates": updates},
                    indent=2,
                ),
            )
        ]


async def handle_validate_week_consistency(args: dict) -> list[TextContent]:
    """Validate week planning consistency."""
    from cyclisme_training_logs.planning.control_tower import planning_tower

    week_id = args["week_id"]

    try:
        with suppress_stdout_stderr():
            plan = planning_tower.read_week(week_id)

            errors = []
            warnings = []

            # Check for date conflicts (multiple sessions on same day without a/b suffix)
            dates_seen = {}
            for session in plan.planned_sessions:
                date_str = str(session.session_date)
                if date_str in dates_seen:
                    # Check if both have proper a/b suffixes
                    prev_session = dates_seen[date_str]
                    if not (
                        session.session_id.endswith(("a", "b"))
                        and prev_session.session_id.endswith(("a", "b"))
                    ):
                        errors.append(
                            f"Date conflict: {date_str} has multiple sessions without proper a/b suffix"
                        )
                dates_seen[date_str] = session

            # Check TSS coherence (not too high for a single day)
            for session in plan.planned_sessions:
                if session.planned_tss and session.planned_tss > 300:
                    warnings.append(
                        f"{session.session_id}: Very high TSS ({session.planned_tss}) - verify if intentional"
                    )

            # Check for empty descriptions
            for session in plan.planned_sessions:
                if not session.description or session.description.strip() == "":
                    errors.append(f"{session.session_id}: Empty workout description")

            # Check week TSS total
            total_tss = sum(
                s.planned_tss or 0 for s in plan.planned_sessions if s.status != "cancelled"
            )
            if total_tss > 800:
                warnings.append(f"Very high weekly TSS ({total_tss}) - verify training load")
            elif total_tss < 200:
                warnings.append(f"Low weekly TSS ({total_tss}) - is this a recovery week?")

            result = {
                "week_id": week_id,
                "valid": len(errors) == 0,
                "total_sessions": len(plan.planned_sessions),
                "total_tss": total_tss,
                "errors": errors,
                "warnings": warnings,
                "message": (
                    "✅ Week planning is valid"
                    if len(errors) == 0
                    else "❌ Week planning has errors"
                ),
            }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"error": f"Validation error: {str(e)}", "week_id": week_id},
                    indent=2,
                ),
            )
        ]


async def handle_get_recommendations(args: dict) -> list[TextContent]:
    """Get PID and Peaks system recommendations for a week."""
    week_id = args["week_id"]

    try:
        with suppress_stdout_stderr():
            # Load recommendations from project docs if available
            rec_file = Path("project-docs") / "recommendations" / f"{week_id}_recommendations.json"

            if rec_file.exists():
                recommendations = json.loads(rec_file.read_text())
                result = {
                    "week_id": week_id,
                    "found": True,
                    "recommendations": recommendations,
                }
            else:
                # Try to find in planning notes
                from cyclisme_training_logs.planning.control_tower import planning_tower

                plan = planning_tower.read_week(week_id)

                result = {
                    "week_id": week_id,
                    "found": False,
                    "message": f"No recommendations file found for {week_id}",
                    "planning_notes": plan.notes if hasattr(plan, "notes") else None,
                }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"error": f"Failed to get recommendations: {str(e)}", "week_id": week_id},
                    indent=2,
                ),
            )
        ]


async def handle_analyze_session_adherence(args: dict) -> list[TextContent]:
    """Analyze adherence between planned session and completed activity."""
    from cyclisme_training_logs.config import create_intervals_client
    from cyclisme_training_logs.planning.control_tower import planning_tower

    session_id = args["session_id"]
    activity_id = args["activity_id"]

    try:
        with suppress_stdout_stderr():
            # Get planned session
            week_id = "-".join(session_id.split("-")[:1])  # Extract S081 from S081-04
            plan = planning_tower.read_week(week_id)

            planned_session = None
            for session in plan.planned_sessions:
                if session.session_id == session_id:
                    planned_session = session
                    break

            if not planned_session:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": f"Session {session_id} not found in week {week_id}"},
                            indent=2,
                        ),
                    )
                ]

            # Get completed activity
            client = create_intervals_client()
            activity = client.get_activity(activity_id)

            # Calculate adherence metrics
            planned_tss = planned_session.tss_planned or 0
            actual_tss = activity.get("icu_training_load", 0)
            tss_adherence = (actual_tss / planned_tss * 100) if planned_tss > 0 else 0

            planned_duration = planned_session.duration_min or 0
            actual_duration = activity.get("moving_time", 0) / 60  # Convert to minutes
            duration_adherence = (
                (actual_duration / planned_duration * 100) if planned_duration > 0 else 0
            )

            # Determine adherence quality
            if 90 <= tss_adherence <= 110:
                adherence_quality = "excellent"
            elif 80 <= tss_adherence <= 120:
                adherence_quality = "good"
            elif 70 <= tss_adherence <= 130:
                adherence_quality = "moderate"
            else:
                adherence_quality = "poor"

            result = {
                "session_id": session_id,
                "activity_id": activity_id,
                "planned": {
                    "tss": planned_tss,
                    "duration_minutes": planned_duration,
                    "description": planned_session.description[:100],
                },
                "actual": {
                    "tss": actual_tss,
                    "duration_minutes": round(actual_duration, 1),
                    "if": activity.get("icu_intensity"),
                    "average_watts": activity.get("average_watts"),
                },
                "adherence": {
                    "tss_percent": round(tss_adherence, 1),
                    "duration_percent": round(duration_adherence, 1),
                    "quality": adherence_quality,
                },
                "message": f"Adherence: {adherence_quality} (TSS: {tss_adherence:.1f}%, Duration: {duration_adherence:.1f}%)",
            }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Adherence analysis error: {str(e)}",
                        "session_id": session_id,
                        "activity_id": activity_id,
                    },
                    indent=2,
                ),
            )
        ]


async def handle_get_training_statistics(args: dict) -> list[TextContent]:
    """Get aggregated training statistics for a date range."""
    from cyclisme_training_logs.config import create_intervals_client

    start_date = args["start_date"]
    end_date = args["end_date"]

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()

            # Get activities and wellness data
            activities = client.get_activities(oldest=start_date, newest=end_date)
            wellness = client.get_wellness(oldest=start_date, newest=end_date)

            # Calculate statistics
            total_activities = len(activities)
            total_tss = sum(a.get("icu_training_load", 0) for a in activities)
            total_duration = sum(a.get("moving_time", 0) for a in activities) / 3600  # Hours
            total_distance = sum(a.get("distance", 0) for a in activities) / 1000  # Km

            avg_tss = total_tss / total_activities if total_activities > 0 else 0

            # Intensity distribution (Z1-Z5)
            intensity_distribution = {
                "z1": sum(1 for a in activities if (a.get("icu_intensity") or 0) < 0.55),
                "z2": sum(1 for a in activities if 0.55 <= (a.get("icu_intensity") or 0) < 0.75),
                "z3": sum(1 for a in activities if 0.75 <= (a.get("icu_intensity") or 0) < 0.85),
                "z4": sum(1 for a in activities if 0.85 <= (a.get("icu_intensity") or 0) < 0.95),
                "z5": sum(1 for a in activities if (a.get("icu_intensity") or 0) >= 0.95),
            }

            # CTL progression
            ctl_start = wellness[0].get("ctl") if wellness else None
            ctl_end = wellness[-1].get("ctl") if wellness else None
            ctl_change = (ctl_end - ctl_start) if (ctl_start and ctl_end) else None

            result = {
                "period": {"start": start_date, "end": end_date},
                "summary": {
                    "total_activities": total_activities,
                    "total_tss": round(total_tss, 1),
                    "total_duration_hours": round(total_duration, 1),
                    "total_distance_km": round(total_distance, 1),
                    "average_tss_per_session": round(avg_tss, 1),
                },
                "intensity_distribution": intensity_distribution,
                "fitness": {
                    "ctl_start": round(ctl_start, 1) if ctl_start else None,
                    "ctl_end": round(ctl_end, 1) if ctl_end else None,
                    "ctl_change": round(ctl_change, 1) if ctl_change else None,
                },
            }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Failed to get training statistics: {str(e)}",
                        "start_date": start_date,
                        "end_date": end_date,
                    },
                    indent=2,
                ),
            )
        ]


async def handle_export_week_to_json(args: dict) -> list[TextContent]:
    """Export week planning to JSON file for backup."""
    from cyclisme_training_logs.planning.control_tower import planning_tower

    week_id = args["week_id"]
    output_path = args.get("output_path", f"/tmp/{week_id}_backup.json")

    try:
        with suppress_stdout_stderr():
            plan = planning_tower.read_week(week_id)

            # Convert to dict
            plan_dict = {
                "week_id": plan.week_id,
                "start_date": str(plan.start_date),
                "end_date": str(plan.end_date),
                "planned_sessions": [
                    {
                        "session_id": s.session_id,
                        "name": s.name,
                        "session_date": str(s.session_date),
                        "category": s.category,
                        "status": s.status,
                        "planned_tss": s.planned_tss,
                        "planned_duration": s.planned_duration,
                        "description": s.description,
                        "intervals_id": s.intervals_id,
                    }
                    for s in plan.planned_sessions
                ],
            }

            # Write to file
            output_file = Path(output_path)
            output_file.write_text(json.dumps(plan_dict, indent=2))

            result = {
                "success": True,
                "week_id": week_id,
                "backup_path": str(output_file),
                "message": f"✅ Week {week_id} exported to {output_file}",
            }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"error": f"Export error: {str(e)}", "week_id": week_id},
                    indent=2,
                ),
            )
        ]


async def handle_restore_week_from_backup(args: dict) -> list[TextContent]:
    """Restore week planning from JSON backup file."""
    from datetime import date as date_type

    from cyclisme_training_logs.planning.control_tower import planning_tower
    from cyclisme_training_logs.planning.models import Session, WeeklyPlan

    week_id = args["week_id"]
    backup_path = args["backup_path"]
    confirm = args.get("confirm", False)

    if not confirm:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": "Restore requires explicit confirmation",
                        "week_id": week_id,
                        "message": "Set confirm=true to proceed with restore",
                        "warning": "This will OVERWRITE current planning",
                    },
                    indent=2,
                ),
            )
        ]

    try:
        with suppress_stdout_stderr():
            # Read backup file
            backup_file = Path(backup_path)
            if not backup_file.exists():
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": f"Backup file not found: {backup_path}"},
                            indent=2,
                        ),
                    )
                ]

            backup_data = json.loads(backup_file.read_text())

            # Reconstruct WeeklyPlan
            sessions = [
                Session(
                    session_id=s["session_id"],
                    name=s["name"],
                    session_date=date_type.fromisoformat(s["session_date"]),
                    category=s["category"],
                    status=s["status"],
                    planned_tss=s.get("planned_tss"),
                    planned_duration=s.get("planned_duration"),
                    description=s["description"],
                    intervals_id=s.get("intervals_id"),
                )
                for s in backup_data["planned_sessions"]
            ]

            plan = WeeklyPlan(
                week_id=backup_data["week_id"],
                start_date=date_type.fromisoformat(backup_data["start_date"]),
                end_date=date_type.fromisoformat(backup_data["end_date"]),
                planned_sessions=sessions,
            )

            # Save via Control Tower
            def restore_plan(existing_plan):
                return plan

            planning_tower.modify_week(
                week_id=week_id,
                modification_function=restore_plan,
                requesting_script="restore-week-from-backup MCP tool",
                reason=f"Restored from backup: {backup_path}",
            )

            result = {
                "success": True,
                "week_id": week_id,
                "restored_sessions": len(sessions),
                "message": f"✅ Week {week_id} restored from {backup_file.name}",
            }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"error": f"Restore error: {str(e)}", "week_id": week_id},
                    indent=2,
                ),
            )
        ]


async def handle_analyze_training_patterns(args: dict) -> list[TextContent]:
    """META TOOL: Load all relevant data for comprehensive AI coach analysis."""
    from cyclisme_training_logs.config import create_intervals_client
    from cyclisme_training_logs.planning.control_tower import planning_tower

    week_id = args["week_id"]
    depth = args.get("depth", "standard")
    include_recommendations = args.get("include_recommendations", True)

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()

            # 1. Load current week planning
            current_plan = planning_tower.read_week(week_id)

            # 2. Load activities for the week
            activities_data = []
            for session in current_plan.planned_sessions:
                if session.status == "completed" and session.intervals_id:
                    try:
                        # Try to find the paired activity
                        events = client.get_events(
                            oldest=str(session.session_date), newest=str(session.session_date)
                        )
                        for event in events:
                            if event.get("id") == session.intervals_id and event.get(
                                "paired_activity_id"
                            ):
                                activity = client.get_activity(event["paired_activity_id"])
                                activities_data.append(
                                    {
                                        "session_id": session.session_id,
                                        "activity_id": event["paired_activity_id"],
                                        "planned_tss": session.planned_tss,
                                        "actual_tss": activity.get("icu_training_load"),
                                        "actual_if": activity.get("icu_intensity"),
                                        "actual_duration": activity.get("moving_time", 0) / 60,
                                        "date": str(session.session_date),
                                    }
                                )
                    except Exception:
                        pass

            # 3. Load wellness data for the week
            wellness_data = client.get_wellness(
                oldest=str(current_plan.start_date), newest=str(current_plan.end_date)
            )

            # 4. Calculate week statistics
            completed_sessions = [
                s for s in current_plan.planned_sessions if s.status == "completed"
            ]
            planned_sessions = [s for s in current_plan.planned_sessions if s.status == "planned"]
            cancelled_sessions = [
                s for s in current_plan.planned_sessions if s.status == "cancelled"
            ]

            planned_tss = sum(
                s.planned_tss or 0 for s in current_plan.planned_sessions if s.status != "cancelled"
            )
            actual_tss = sum(a["actual_tss"] or 0 for a in activities_data)

            compliance_rate = (
                (len(completed_sessions) / len(current_plan.planned_sessions) * 100)
                if current_plan.planned_sessions
                else 0
            )

            # Base result structure
            result = {
                "week_id": week_id,
                "period": {
                    "start": str(current_plan.start_date),
                    "end": str(current_plan.end_date),
                },
                "planning": {
                    "total_sessions": len(current_plan.planned_sessions),
                    "completed": len(completed_sessions),
                    "planned": len(planned_sessions),
                    "cancelled": len(cancelled_sessions),
                    "planned_tss": planned_tss,
                    "actual_tss": actual_tss,
                    "tss_adherence_percent": (
                        round(actual_tss / planned_tss * 100, 1) if planned_tss > 0 else 0
                    ),
                    "compliance_rate_percent": round(compliance_rate, 1),
                },
                "sessions": [
                    {
                        "session_id": s.session_id,
                        "name": s.name,
                        "date": str(s.session_date),
                        "category": s.category,
                        "status": s.status,
                        "planned_tss": s.planned_tss,
                        "planned_duration": s.planned_duration,
                        "description": s.description[:100] if s.description else "",
                        "intervals_id": s.intervals_id,
                    }
                    for s in current_plan.planned_sessions
                ],
                "activities": activities_data,
                "wellness": (
                    [
                        {
                            "date": w.get("id"),
                            "ctl": w.get("ctl"),
                            "atl": w.get("atl"),
                            "tsb": w.get("tsb"),
                            "ramp_rate": w.get("ramp_rate"),
                        }
                        for w in wellness_data
                    ]
                    if wellness_data
                    else []
                ),
            }

            # 5. Add previous week context for 'standard' and 'comprehensive'
            if depth in ["standard", "comprehensive"]:
                try:
                    prev_week_num = int(week_id[1:]) - 1
                    prev_week_id = f"S{prev_week_num:03d}"
                    prev_plan = planning_tower.read_week(prev_week_id)

                    prev_completed = [
                        s for s in prev_plan.planned_sessions if s.status == "completed"
                    ]
                    prev_tss = sum(s.planned_tss or 0 for s in prev_completed)

                    result["previous_week"] = {
                        "week_id": prev_week_id,
                        "completed_sessions": len(prev_completed),
                        "total_tss": prev_tss,
                    }
                except Exception:
                    result["previous_week"] = None

            # 6. Add comprehensive context
            if depth == "comprehensive":
                try:
                    # Load recommendations if available
                    if include_recommendations:
                        rec_file = (
                            Path("project-docs")
                            / "recommendations"
                            / f"{week_id}_recommendations.json"
                        )
                        if rec_file.exists():
                            result["recommendations"] = json.loads(rec_file.read_text())

                    # Add athlete profile
                    athlete = client.get_athlete()
                    result["athlete_profile"] = {
                        "ftp": athlete.get("ftp"),
                        "weight": athlete.get("weight"),
                        "ctl": athlete.get("ctl"),
                        "atl": athlete.get("atl"),
                    }

                    # Add last 4 weeks CTL trend
                    four_weeks_ago = str(current_plan.start_date - timedelta(days=28))
                    historical_wellness = client.get_wellness(
                        oldest=four_weeks_ago, newest=str(current_plan.end_date)
                    )
                    if historical_wellness:
                        result["ctl_trend"] = [
                            {"date": w.get("id"), "ctl": w.get("ctl")}
                            for w in historical_wellness[-28:]  # Last 4 weeks
                        ]
                except Exception as e:
                    result["comprehensive_data_warning"] = (
                        f"Some comprehensive data unavailable: {str(e)}"
                    )

            result["analysis_depth"] = depth
            result["message"] = f"✅ Loaded {depth} analysis data for {week_id}"

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Analysis error: {str(e)}",
                        "week_id": week_id,
                        "depth": depth,
                    },
                    indent=2,
                ),
            )
        ]


async def handle_create_remote_note(args: dict) -> list[TextContent]:
    """Create a NOTE (calendar note) directly on Intervals.icu with write-back to local planning."""
    import re

    from cyclisme_training_logs.config import create_intervals_client
    from cyclisme_training_logs.planning.control_tower import planning_tower
    from cyclisme_training_logs.planning.models import Session

    date = args["date"]
    name = args["name"]
    description = args["description"]

    # Validate required prefix
    ALLOWED_PREFIXES = ["[ANNULÉE]", "[SAUTÉE]", "[REMPLACÉE]"]
    if not any(name.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": False,
                        "error": f"Invalid NOTE name. Name must start with one of: {', '.join(ALLOWED_PREFIXES)}",
                        "provided_name": name,
                        "allowed_prefixes": ALLOWED_PREFIXES,
                    },
                    indent=2,
                ),
            )
        ]

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()

            # Create NOTE event (category=NOTE, type=null, no workout)
            event_data = {
                "category": "NOTE",
                "name": name,
                "description": description,
                "start_date_local": f"{date}T00:00:00",  # Notes at midnight
            }

            # Create event on Intervals.icu
            created_event = client.create_event(event_data)

            if created_event and "id" in created_event:
                # WRITE-BACK: Update local planning
                # Extract session_id from name (e.g., "[ANNULÉE] S081-04-INT-TempoSoutenu" → "S081-04")
                session_id_match = re.search(r"S\d{3}-\d{2}[a-z]?", name)
                if session_id_match:
                    session_id = session_id_match.group()
                    week_id = session_id.split("-")[0]  # Extract S081 from S081-04

                    try:
                        # Determine status from prefix
                        status_map = {
                            "[ANNULÉE]": "cancelled",
                            "[SAUTÉE]": "skipped",
                            "[REMPLACÉE]": "replaced",
                        }
                        new_status = next(
                            (
                                status
                                for prefix, status in status_map.items()
                                if name.startswith(prefix)
                            ),
                            "cancelled",
                        )

                        # Update local planning
                        with planning_tower.modify_week(
                            week_id,
                            requesting_script="create-remote-note",
                            reason=f"Write-back from NOTE creation: {new_status} session {session_id}",
                        ) as plan:
                            updated_sessions = []
                            for session in plan.planned_sessions:
                                if session.session_id == session_id:
                                    session_dict = session.model_dump()
                                    session_dict["status"] = new_status
                                    session_dict["reason"] = description[:100]  # First 100 chars
                                    # Note: We don't update intervals_id because NOTE is separate from session
                                    updated_session = Session(**session_dict)
                                    updated_sessions.append(updated_session)
                                else:
                                    updated_sessions.append(session)

                            plan.planned_sessions = updated_sessions

                        local_update_msg = (
                            f" (+ local planning {week_id}/{session_id} → {new_status})"
                        )
                    except Exception as e:
                        local_update_msg = f" (local planning update failed: {str(e)})"
                else:
                    local_update_msg = " (no session_id found in name, local planning not updated)"

                result = {
                    "success": True,
                    "event_id": created_event["id"],
                    "date": date,
                    "name": name,
                    "message": f"✅ NOTE created successfully on Intervals.icu (ID: {created_event['id']}){local_update_msg}",
                }
            else:
                result = {
                    "success": False,
                    "message": "❌ Failed to create NOTE - no ID returned from Intervals.icu",
                }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Failed to create NOTE: {str(e)}",
                        "date": date,
                        "name": name,
                    },
                    indent=2,
                ),
            )
        ]


async def handle_sync_remote_to_local(args: dict) -> list[TextContent]:
    """
    Sync local planning from Intervals.icu remote events.

    Handles desync cases from pre-write-back operations (e.g., S081-07 → S081-07a, S081-07b).
    """
    try:
        with suppress_stdout_stderr():
            from cyclisme_training_logs.config import create_intervals_client
            from cyclisme_training_logs.planning.control_tower import planning_tower

            week_id = args["week_id"]
            strategy = args.get("strategy", "merge")

            # Create Intervals.icu client
            client = create_intervals_client()

            # Sync from remote
            stats = planning_tower.sync_from_remote(
                week_id=week_id,
                intervals_client=client,
                strategy=strategy,
                requesting_script="mcp:sync-remote-to-local",
            )

            # Build response
            result = {
                "week_id": week_id,
                "strategy": strategy,
                "stats": stats,
                "message": f"Synced {week_id} from Intervals.icu",
            }

            # Add details about changes
            changes = []
            if stats["sessions_added"]:
                changes.append(
                    f"✅ Added {len(stats['sessions_added'])} sessions: {', '.join(stats['sessions_added'])}"
                )
            if stats["sessions_updated"]:
                changes.append(
                    f"🔄 Updated {len(stats['sessions_updated'])} sessions: {', '.join(stats['sessions_updated'])}"
                )
            if stats["intervals_ids_fixed"]:
                changes.append(
                    f"🔧 Fixed {len(stats['intervals_ids_fixed'])} intervals_id mismatches"
                )
                for fix in stats["intervals_ids_fixed"]:
                    changes.append(f"  - {fix['session_id']}: {fix['old_id']} → {fix['new_id']}")
            if stats["sessions_removed"]:
                changes.append(
                    f"🗑️ Removed {len(stats['sessions_removed'])} sessions: {', '.join(stats['sessions_removed'])}"
                )

            if not changes:
                changes.append("ℹ️ No changes needed - local planning already in sync")

            result["changes"] = changes

            return [
                TextContent(
                    type="text",
                    text=json.dumps(result, indent=2),
                )
            ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": str(e),
                        "week_id": args.get("week_id"),
                    },
                    indent=2,
                ),
            )
        ]


async def handle_backfill_activities(args: dict) -> list[TextContent]:
    """
    Backfill historical activity data into local planning sessions.

    Matches activities to planned sessions and updates session status to completed.
    """
    with suppress_stdout_stderr():
        from datetime import datetime

        from cyclisme_training_logs.config import create_intervals_client, get_data_config
        from cyclisme_training_logs.daily_sync import DailySync
        from cyclisme_training_logs.planning.models import WeeklyPlan

        # Determine date range
        if "week_id" in args:
            week_id = args["week_id"]

            # Load week planning to get date range
            data_config = get_data_config()
            planning_file = data_config.week_planning_dir / f"week_planning_{week_id}.json"

            if not planning_file.exists():
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": f"Planning file not found for {week_id}"}, indent=2
                        ),
                    )
                ]

            plan = WeeklyPlan.from_json(planning_file)
            start_date = plan.start_date
            end_date = plan.end_date
            date_source = f"week {week_id}"

        else:
            start_date = datetime.fromisoformat(args["start_date"]).date()
            end_date = datetime.fromisoformat(args["end_date"]).date()
            date_source = f"{start_date} to {end_date}"

        # Create Intervals.icu client
        client = create_intervals_client()

        # Fetch all activities in date range
        activities = client.get_activities(oldest=start_date, newest=end_date)

        if not activities:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "message": f"No activities found for {date_source}",
                            "start_date": str(start_date),
                            "end_date": str(end_date),
                            "activities_count": 0,
                        },
                        indent=2,
                    ),
                )
            ]

        # Create DailySync instance (reuses matching logic)
        data_config = get_data_config()

        # Use temporary tracking file for backfill (won't duplicate analysis)
        tracking_file = data_config.data_repo_path / ".backfill_tracking.json"
        reports_dir = data_config.data_repo_path / "reports"
        reports_dir.mkdir(exist_ok=True)

        sync = DailySync(
            tracking_file=tracking_file,
            reports_dir=reports_dir,
            verbose=False,
        )

        # Use update_completed_sessions to match and update (matches via workouts)
        activity_to_session_map = sync.update_completed_sessions(activities)

        # Track categories for better reporting
        updated = {}  # Sessions that were updated
        already_completed = {}  # Sessions that were already completed
        unmatched = []  # Activities without matching sessions

        # For backfill, also try direct matching from activity names
        # (for activities where workout event no longer exists)
        import re

        from cyclisme_training_logs.planning.control_tower import planning_tower

        for activity in activities:
            activity_id = activity["id"]

            # Skip if already matched by DailySync
            if activity_id in activity_to_session_map:
                updated[activity_id] = activity_to_session_map[activity_id]
                continue

            # Try to extract session_id from activity name
            # Format: S081-01-END-EnduranceBase-V001
            name = activity.get("name", "")
            match = re.search(r"(S\d{3}-\d{2}[a-z]?)", name)

            if not match:
                unmatched.append(activity_id)
                continue

            session_id = match.group(1)
            week_id = session_id.split("-")[0]

            # Try to update session status in local planning
            try:
                session_found = False

                with planning_tower.modify_week(
                    week_id,
                    requesting_script="mcp:backfill-activities",
                    reason=f"Backfill {session_id} from activity {activity_id}",
                ) as plan:
                    for session in plan.planned_sessions:
                        if session.session_id == session_id:
                            session_found = True
                            if session.status != "completed":
                                session.status = "completed"
                                updated[activity_id] = session_id
                            else:
                                already_completed[activity_id] = session_id
                            break

                if not session_found:
                    unmatched.append(activity_id)
            except Exception:
                # Week planning might not exist for old weeks
                unmatched.append(activity_id)

        # Build response with detailed categorization
        result = {
            "message": f"Backfill complete: {len(updated)} updated, {len(already_completed)} already completed, {len(unmatched)} unmatched",
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_activities": len(activities),
            "updated": len(updated),
            "already_completed": len(already_completed),
            "unmatched": len(unmatched),
            "details": {
                "updated_sessions": [],
                "already_completed_sessions": [],
                "unmatched_activities": [],
            },
        }

        # Add details about updated sessions
        for activity_id, session_id in updated.items():
            activity = next((a for a in activities if a["id"] == activity_id), None)
            if activity:
                result["details"]["updated_sessions"].append(
                    {
                        "activity_id": activity_id,
                        "activity_name": activity.get("name", ""),
                        "session_id": session_id,
                        "date": activity.get("start_date_local", "")[:10],
                    }
                )

        # Add details about already completed sessions
        for activity_id, session_id in already_completed.items():
            activity = next((a for a in activities if a["id"] == activity_id), None)
            if activity:
                result["details"]["already_completed_sessions"].append(
                    {
                        "activity_id": activity_id,
                        "activity_name": activity.get("name", ""),
                        "session_id": session_id,
                        "date": activity.get("start_date_local", "")[:10],
                    }
                )

        # Add details about unmatched activities
        for activity_id in unmatched:
            activity = next((a for a in activities if a["id"] == activity_id), None)
            if activity:
                result["details"]["unmatched_activities"].append(
                    {
                        "activity_id": activity_id,
                        "activity_name": activity.get("name", ""),
                        "date": activity.get("start_date_local", "")[:10],
                    }
                )

        return [
            TextContent(
                type="text",
                text=json.dumps(result, indent=2),
            )
        ]


async def handle_reload_server(args: dict) -> list[TextContent]:
    """Reload MCP server modules (dev tool for hot reload without restarting Claude Desktop)."""
    import importlib
    import sys

    try:
        # List of modules to reload (in dependency order)
        modules_to_reload = [
            "cyclisme_training_logs.config",
            "cyclisme_training_logs.planning.models",
            "cyclisme_training_logs.planning.control_tower",
            "cyclisme_training_logs.daily_sync",
            "cyclisme_training_logs.weekly_planner",
            # Add other modules as needed
        ]

        reloaded = []
        failed = []

        for module_name in modules_to_reload:
            try:
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                    reloaded.append(module_name)
            except Exception as e:
                failed.append({"module": module_name, "error": str(e)})

        result = {
            "success": len(failed) == 0,
            "reloaded_count": len(reloaded),
            "reloaded_modules": reloaded,
            "failed": failed,
            "message": (
                f"✅ Reloaded {len(reloaded)} modules"
                if len(failed) == 0
                else f"⚠️ Reloaded {len(reloaded)} modules, {len(failed)} failed"
            ),
            "note": "MCP server handlers NOT reloaded (requires watchdog auto-restart or manual restart)",
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Reload failed: {str(e)}",
                        "message": "⚠️ Module reload error - may need full restart",
                    },
                    indent=2,
                ),
            )
        ]


async def main():
    """Run MCP server using stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
