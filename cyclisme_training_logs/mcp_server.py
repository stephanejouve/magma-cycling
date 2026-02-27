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
          "cwd": "/path/to/cyclisme-training-logs"
        }
      }
    }
"""

import json
import os
import sys
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from io import StringIO
from pathlib import Path

from mcp.server import Server
from mcp.types import (
    TextContent,
    Tool,
)
from mcp_http_transport import MCPTransportManager


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

# Transport configuration from environment variables
TRANSPORT_MODE = os.getenv("MCP_TRANSPORT", "stdio")  # "stdio" (default) or "http"
HTTP_HOST = os.getenv("MCP_HTTP_HOST", "localhost")
HTTP_PORT = int(os.getenv("MCP_HTTP_PORT", "3000"))


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
                    "session_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional: only sync these session IDs (e.g., ['S081-03', 'S081-06'])",
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
            name="get-activity-intervals",
            description="Get aggregated interval/lap data for a completed activity from Intervals.icu (avg power, HR, cadence per interval — ideal for block-by-block analysis)",
            inputSchema={
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": "Activity ID (format: i107424849 or numeric)",
                    },
                },
                "required": ["activity_id"],
            },
        ),
        Tool(
            name="compare-intervals",
            description="Compare interval data across multiple activities to track progression over time. Aligns intervals by label, calculates deltas and trends for metrics like power, HR, cadence, torque, decoupling.",
            inputSchema={
                "type": "object",
                "properties": {
                    "activity_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Explicit list of activity IDs to compare (e.g. ['i122793458', 'i126184461'])",
                    },
                    "name_pattern": {
                        "type": "string",
                        "description": "Search activities by name substring (case-insensitive, e.g. 'CadenceVariations')",
                    },
                    "weeks_back": {
                        "type": "integer",
                        "description": "Number of weeks to search back (default: 6, used with name_pattern)",
                        "default": 6,
                    },
                    "label_filter": {
                        "type": "string",
                        "description": "Only keep intervals whose label contains this substring (case-insensitive, e.g. '95rpm')",
                    },
                    "type_filter": {
                        "type": "string",
                        "enum": ["WORK", "RECOVERY"],
                        "description": "Only keep intervals of this type",
                    },
                    "metrics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Metrics to include in comparison (default: all numeric metrics)",
                    },
                },
            },
        ),
        Tool(
            name="apply-workout-intervals",
            description="Apply custom interval boundaries to an Intervals.icu activity. Auto mode: parses workout prescription to compute intervals. Manual mode: accepts explicit interval list. Always dry_run=true by default (preview only).",
            inputSchema={
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": "Activity ID (format: i107424849 or numeric)",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Session ID (e.g. S082-02). If omitted, extracted from activity name.",
                    },
                    "intervals": {
                        "type": "array",
                        "description": "Manual mode: explicit interval list [{type, label, start_index, end_index}]. If omitted, auto-computes from workout prescription.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "label": {"type": "string"},
                                "start_index": {"type": "integer"},
                                "end_index": {"type": "integer"},
                            },
                            "required": ["type", "label", "start_index", "end_index"],
                        },
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Preview only, do not modify (default: true)",
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
        # === Withings Health Data Tools ===
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
            description="Synchronize Withings health data (sleep, weight) to Intervals.icu wellness fields",
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
                        "items": {"type": "string", "enum": ["sleep", "weight", "all"]},
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
        elif name == "get-activity-intervals":
            return await handle_get_activity_intervals(arguments)
        elif name == "compare-intervals":
            return await handle_compare_intervals(arguments)
        elif name == "apply-workout-intervals":
            return await handle_apply_workout_intervals(arguments)
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
        elif name == "withings-auth-status":
            return await handle_withings_auth_status(arguments)
        elif name == "withings-authorize":
            return await handle_withings_authorize(arguments)
        elif name == "withings-get-sleep":
            return await handle_withings_get_sleep(arguments)
        elif name == "withings-get-weight":
            return await handle_withings_get_weight(arguments)
        elif name == "withings-get-readiness":
            return await handle_withings_get_readiness(arguments)
        elif name == "withings-sync-to-intervals":
            return await handle_withings_sync_to_intervals(arguments)
        elif name == "withings-analyze-trends":
            return await handle_withings_analyze_trends(arguments)
        elif name == "withings-enrich-session":
            return await handle_withings_enrich_session(arguments)
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
    """Sync with Intervals.icu (full pipeline: check, AI analysis, report)."""
    from cyclisme_training_logs.daily_sync import DailySync, calculate_current_week_info

    check_date_str = args.get("date")
    enable_ai = args.get("ai_analysis", True)

    if check_date_str:
        check_date = datetime.strptime(check_date_str, "%Y-%m-%d").date()
    else:
        check_date = date.today()

    # Auto-calculate week_id and start_date
    week_id = args.get("week_id")
    with suppress_stdout_stderr():
        calculated_week_id, calculated_start_date = calculate_current_week_info(check_date)
    if not week_id:
        week_id = calculated_week_id
    start_date = calculated_start_date

    # Setup paths
    from cyclisme_training_logs.config import get_data_config

    config = get_data_config()
    tracking_file = config.data_repo_path / "activities_tracking.json"
    reports_dir = config.data_repo_path / "daily-reports"

    # DailySync init may print AI provider info — suppress it
    with suppress_stdout_stderr():
        sync = DailySync(
            tracking_file=tracking_file,
            reports_dir=reports_dir,
            enable_ai_analysis=enable_ai,
            enable_auto_servo=False,
            verbose=False,
        )

    # Run full sync pipeline (check, AI analysis, update sessions, report)
    with suppress_stdout_stderr():
        sync.run(
            check_date=check_date,
            week_id=week_id,
            start_date=start_date,
        )

    # Re-read completed activities for response building (lightweight API GET)
    with suppress_stdout_stderr():
        _, completed_activities = sync.check_activities(check_date)
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
                "session_id": activity_to_session_map.get(activity_id),
            }
            activities_details.append(activity_detail)

    # Report file path
    report_file = reports_dir / f"daily_report_{check_date.isoformat()}.md"

    # AI provider info
    ai_provider = None
    if enable_ai and sync.ai_analyzer:
        ai_provider = type(sync.ai_analyzer).__name__

    result = {
        "date": check_date.isoformat(),
        "week_id": week_id,
        "completed_activities": len(completed_activities) if completed_activities else 0,
        "activities": activities_details,
        "ai_analysis": enable_ai and sync.ai_analyzer is not None,
        "ai_provider": ai_provider,
        "report_file": str(report_file) if report_file.exists() else None,
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
    session_type = None
    session_version = None
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
                    session_type = session.session_type
                    session_version = session.version
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

                # Build Intervals.icu event name: S082-03-INT-SweetSpotBlocs-V001
                intervals_name = f"{session_id}-{session_type}-{session_name}-{session_version}"

                event_data = {
                    "category": "WORKOUT",
                    "type": "VirtualRide",
                    "name": intervals_name,
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
    """Swap the dates of two sessions and update remote events if synced."""
    from cyclisme_training_logs.config import create_intervals_client
    from cyclisme_training_logs.planning.control_tower import planning_tower

    week_id = args["week_id"]
    session_id_1 = args["session_id_1"]
    session_id_2 = args["session_id_2"]

    try:
        # Track session data for remote update after local swap
        intervals_id_1 = None
        intervals_id_2 = None
        new_date_1 = None
        new_date_2 = None

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

                # Swap session_ids so the day index matches the new date
                # e.g., S082-04 (Thu) <-> S082-05 (Fri) → each keeps its
                # workout content but gets the other's id+date slot
                temp_id = session_1.session_id
                session_1.session_id = session_2.session_id
                session_2.session_id = temp_id

                # Capture data for remote update (after id swap)
                intervals_id_1 = session_1.intervals_id
                intervals_id_2 = session_2.intervals_id
                new_date_1 = session_1.session_date
                new_date_2 = session_2.session_date
                # Build new intervals_names with swapped session_ids
                new_name_1 = (
                    f"{session_1.session_id}-{session_1.session_type}"
                    f"-{session_1.name}-{session_1.version}"
                )
                new_name_2 = (
                    f"{session_2.session_id}-{session_2.session_type}"
                    f"-{session_2.name}-{session_2.version}"
                )

                # Re-sort sessions
                plan.planned_sessions.sort(key=lambda s: (s.session_date, s.session_id))

            # Update remote events if both sessions are synced
            remote_updated = False
            if intervals_id_1 and intervals_id_2:
                client = create_intervals_client()
                start_time_1 = _compute_start_time(new_date_1, session_1.session_id)
                start_time_2 = _compute_start_time(new_date_2, session_2.session_id)

                client.update_event(
                    intervals_id_1,
                    {
                        "name": new_name_1,
                        "start_date_local": f"{new_date_1}T{start_time_1}",
                    },
                )
                client.update_event(
                    intervals_id_2,
                    {
                        "name": new_name_2,
                        "start_date_local": f"{new_date_2}T{start_time_2}",
                    },
                )
                remote_updated = True

        result = {
            "status": "success",
            "week_id": week_id,
            "session_id_1": session_id_1,
            "session_id_2": session_id_2,
            "swapped_session_ids": [session_id_1, session_id_2],
            "remote_updated": remote_updated,
            "message": f"Sessions swapped successfully: {session_id_1} <-> {session_id_2}"
            + (" (+ remote events updated)" if remote_updated else ""),
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
                # No .zwo file — fall back to session description from planning
                from cyclisme_training_logs.planning.control_tower import planning_tower

                week_id = session_id[:4]  # "S082-02" → "S082"
                session_def = None
                try:
                    plan = planning_tower.read_week(week_id)
                    session_def = next(
                        (s for s in plan.planned_sessions if s.session_id == session_id),
                        None,
                    )
                except Exception:
                    pass

                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "found": False,
                                "session_id": session_id,
                                "structured_file": None,
                                "message": "No structured workout file (.zwo) found. "
                                "Session is defined via text description in the planning.",
                                "session_definition": (
                                    {
                                        "name": session_def.name if session_def else None,
                                        "type": session_def.session_type if session_def else None,
                                        "description": (
                                            session_def.description if session_def else None
                                        ),
                                        "tss_planned": (
                                            session_def.tss_planned if session_def else None
                                        ),
                                        "duration_min": (
                                            session_def.duration_min if session_def else None
                                        ),
                                    }
                                    if session_def
                                    else None
                                ),
                            },
                            indent=2,
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


# Statuses that should be synced to Intervals.icu.
# Any other status (completed, skipped, cancelled, rest_day, replaced) is protected.
SYNCABLE_STATUSES = {"pending", "planned", "uploaded", "modified"}


def _compute_start_time(session_date, session_id: str) -> str:
    """Compute start time for an Intervals.icu event.

    Args:
        session_date: Date of the session (date object with .weekday()).
        session_id: Session ID (e.g., "S081-04", "S081-06a", "S081-06b").

    Returns:
        Time string like "09:00:00" or "17:00:00".
    """
    day_of_week = session_date.weekday()  # 0=Monday, 5=Saturday
    session_day_part = session_id.split("-")[-1]  # e.g., "04" or "06a"
    session_suffix = session_day_part[-1] if session_day_part[-1].isalpha() else None

    if session_suffix == "a":
        return "09:00:00"  # Morning
    elif session_suffix == "b":
        return "15:00:00"  # Afternoon
    else:
        # Saturday → 09:00, other days → 17:00
        return "09:00:00" if day_of_week == 5 else "17:00:00"


def _load_workout_descriptions(week_id: str) -> dict[str, str]:
    """Load full workout descriptions from {week_id}_workouts.txt.

    Delegates to workout_parser.load_workout_descriptions.
    """
    from cyclisme_training_logs.workout_parser import load_workout_descriptions

    return load_workout_descriptions(week_id)


async def handle_sync_week_to_intervals(args: dict) -> list[TextContent]:
    """Synchronize week planning to Intervals.icu."""
    from cyclisme_training_logs.config import create_intervals_client
    from cyclisme_training_logs.planning.control_tower import planning_tower

    week_id = args["week_id"]
    dry_run = args.get("dry_run", False)
    force_update = args.get("force_update", False)
    session_ids = args.get("session_ids")

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

            # Load full workout descriptions from workouts.txt
            workout_descriptions = _load_workout_descriptions(week_id)

            # Track changes
            to_create = []
            to_update = []
            to_skip_protected = []
            warnings = []
            errors = []

            # Determine sessions to process (selective sync support)
            sessions_to_process = plan.planned_sessions
            if session_ids:
                session_ids_set = set(session_ids)
                sessions_to_process = [
                    s for s in plan.planned_sessions if s.session_id in session_ids_set
                ]

            # Process each session
            for session in sessions_to_process:
                # PROTECTION: Only sync sessions with syncable statuses
                if session.status not in SYNCABLE_STATUSES:
                    to_skip_protected.append(
                        {
                            "session_id": session.session_id,
                            "name": session.name,
                            "status": session.status,
                            "reason": f"Session {session.status} - protected from sync",
                        }
                    )
                    continue

                # Compute start time using shared helper
                start_time = _compute_start_time(session.session_date, session.session_id)

                # Build Intervals.icu event name: S082-03-INT-SweetSpotBlocs-V001
                intervals_name = (
                    f"{session.session_id}-{session.session_type}-{session.name}-{session.version}"
                )

                # Use full workout description from workouts.txt if available
                full_description = workout_descriptions.get(intervals_name, session.description)

                event_data = {
                    "category": "WORKOUT",
                    "type": "VirtualRide",
                    "name": intervals_name,
                    "description": full_description,
                    "start_date_local": f"{session.session_date}T{start_time}",
                }

                # Validate workout description before creating remote event
                if full_description and full_description.strip():
                    from cyclisme_training_logs.intervals_format_validator import (
                        IntervalsFormatValidator,
                    )

                    validator = IntervalsFormatValidator()
                    is_valid, val_errors, _val_warnings = validator.validate_workout(
                        full_description
                    )
                    if not is_valid:
                        errors.append(
                            f"Session {session.session_id}: workout validation failed — {val_errors}. "
                            f"Fix with validate-workout tool, then retry sync."
                        )
                        continue

                if session.intervals_id:
                    # Check if event exists remotely
                    if session.intervals_id in remote_workouts:
                        # Event exists - check for conflicts
                        remote_event = remote_workouts[session.intervals_id]

                        # 🛡️ VALIDATION: Detect if remote was manually modified
                        # Compare full intervals_name (not short session.name) and date
                        remote_name = remote_event.get("name", "")
                        remote_start = remote_event.get("start_date_local", "")
                        local_start = f"{session.session_date}T{start_time}"

                        has_remote_changes = (
                            remote_name != intervals_name or remote_start != local_start
                        )

                        if has_remote_changes and not force_update:
                            # Remote has been manually modified - warn about conflict
                            warnings.append(
                                {
                                    "session_id": session.session_id,
                                    "intervals_id": session.intervals_id,
                                    "type": "remote_modification_detected",
                                    "message": f"⚠️ Remote event {session.intervals_id} has been manually modified in Intervals.icu",
                                    "local_name": intervals_name,
                                    "remote_name": remote_name,
                                    "suggestion": "Use force_update=true to overwrite remote changes",
                                }
                            )
                            # Skip this session unless force_update
                            continue

                        # Check if update needed
                        needs_update = force_update or has_remote_changes

                        if needs_update:
                            # For updates: only send name + start_date_local,
                            # NOT description (remote is source of truth for workout content)
                            update_data = {
                                "name": intervals_name,
                                "start_date_local": f"{session.session_date}T{start_time}",
                            }
                            to_update.append(
                                {
                                    "session_id": session.session_id,
                                    "intervals_id": session.intervals_id,
                                    "name": session.name,
                                    "event_data": update_data,
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
                "skipped_protected": len(to_skip_protected),
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
                "skipped_protected": to_skip_protected,
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


async def handle_get_activity_intervals(args: dict) -> list[TextContent]:
    """Get aggregated interval/lap data for a completed activity from Intervals.icu."""
    from cyclisme_training_logs.config import create_intervals_client

    activity_id = args["activity_id"]

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()
            raw_intervals = client.get_activity_intervals(activity_id)

        # Fields to keep from each interval (filter nulls to lighten context)
        # Field names match Intervals.icu API response format
        keep_fields = {
            "type",
            "label",
            "start_index",
            "end_index",
            "elapsed_time",
            "moving_time",
            "distance",
            "average_watts",
            "weighted_average_watts",
            "min_watts",
            "max_watts",
            "average_heartrate",
            "min_heartrate",
            "max_heartrate",
            "average_cadence",
            "intensity",
            "training_load",
            "decoupling",
            "average_speed",
            "total_elevation_gain",
            "average_torque",
            "min_torque",
            "max_torque",
            "avg_lr_balance",
        }

        intervals = []
        total_elapsed = 0
        for iv in raw_intervals:
            filtered = {k: v for k, v in iv.items() if k in keep_fields and v is not None}
            intervals.append(filtered)
            total_elapsed += iv.get("elapsed_time", 0) or 0

        result = {
            "activity_id": activity_id,
            "total_intervals": len(intervals),
            "total_elapsed_seconds": total_elapsed,
            "intervals": intervals,
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Failed to get activity intervals: {str(e)}",
                        "activity_id": activity_id,
                    },
                    indent=2,
                ),
            )
        ]


async def handle_compare_intervals(args: dict) -> list[TextContent]:
    """Compare interval data across multiple activities to track progression."""
    from cyclisme_training_logs.config import create_intervals_client

    NUMERIC_METRICS = {
        "elapsed_time",
        "moving_time",
        "distance",
        "average_watts",
        "weighted_average_watts",
        "min_watts",
        "max_watts",
        "average_heartrate",
        "min_heartrate",
        "max_heartrate",
        "average_cadence",
        "intensity",
        "training_load",
        "decoupling",
        "average_speed",
        "total_elevation_gain",
        "average_torque",
        "min_torque",
        "max_torque",
        "avg_lr_balance",
    }

    activity_ids = args.get("activity_ids")
    name_pattern = args.get("name_pattern")
    weeks_back = args.get("weeks_back", 6)
    label_filter = args.get("label_filter")
    type_filter = args.get("type_filter")
    requested_metrics = args.get("metrics")

    # Validation: need at least one mode
    if not activity_ids and not name_pattern:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": "Either 'activity_ids' or 'name_pattern' is required.",
                    },
                    indent=2,
                ),
            )
        ]

    # Validate metrics if provided
    if requested_metrics:
        invalid = [m for m in requested_metrics if m not in NUMERIC_METRICS]
        if invalid:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": f"Invalid metrics: {invalid}",
                            "available_metrics": sorted(NUMERIC_METRICS),
                        },
                        indent=2,
                    ),
                )
            ]

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()

        # Resolve activities
        if activity_ids:
            mode = "explicit"
            resolved = []
            for aid in activity_ids:
                with suppress_stdout_stderr():
                    act = client.get_activity(aid)
                resolved.append(
                    {
                        "id": aid,
                        "name": act.get("name", ""),
                        "date": (act.get("start_date_local", "") or "")[:10],
                    }
                )
        else:
            mode = "search"
            newest = date.today().isoformat()
            oldest = (date.today() - timedelta(weeks=weeks_back)).isoformat()
            with suppress_stdout_stderr():
                all_activities = client.get_activities(oldest=oldest, newest=newest)
            pattern_lower = name_pattern.lower()
            resolved = [
                {
                    "id": a.get("id", ""),
                    "name": a.get("name", ""),
                    "date": (a.get("start_date_local", "") or "")[:10],
                }
                for a in all_activities
                if pattern_lower in (a.get("name", "") or "").lower()
            ]
            resolved.sort(key=lambda x: x["date"])

            if not resolved:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "error": f"No activities matching '{name_pattern}' in the last {weeks_back} weeks.",
                            },
                            indent=2,
                        ),
                    )
                ]

        # Fetch intervals for each activity
        activity_intervals = {}
        for act_info in resolved:
            aid = act_info["id"]
            with suppress_stdout_stderr():
                raw = client.get_activity_intervals(aid)
            activity_intervals[aid] = raw

        # Build metadata
        activity_metadata = {a["id"]: {"name": a["name"], "date": a["date"]} for a in resolved}
        intervals_per_activity = {aid: len(ivs) for aid, ivs in activity_intervals.items()}

        # Filter intervals
        metrics_to_use = set(requested_metrics) if requested_metrics else NUMERIC_METRICS

        filtered_intervals = {}
        for aid, raw_ivs in activity_intervals.items():
            kept = []
            for iv in raw_ivs:
                # Skip gap intervals (auto-inserted by Intervals.icu)
                if (iv.get("elapsed_time") or 0) <= 2:
                    continue
                if type_filter and iv.get("type") != type_filter:
                    continue
                if label_filter and label_filter.lower() not in (iv.get("label", "") or "").lower():
                    continue
                kept.append(iv)
            filtered_intervals[aid] = kept

        # Align by label
        from collections import defaultdict

        label_groups = defaultdict(lambda: defaultdict(list))
        for aid, ivs in filtered_intervals.items():
            for iv in ivs:
                label = (iv.get("label", "") or "").strip().lower()
                label_groups[label][aid].append(iv)

        # Preserve original label casing from first occurrence
        label_display = {}
        for aid, ivs in filtered_intervals.items():
            for iv in ivs:
                norm = (iv.get("label", "") or "").strip().lower()
                if norm not in label_display:
                    label_display[norm] = (iv.get("label", "") or "").strip()

        # Build comparison
        ordered_ids = [a["id"] for a in resolved]
        comparison = []
        for norm_label in sorted(label_groups.keys()):
            group = label_groups[norm_label]
            activities_data = []
            values_by_metric = defaultdict(list)

            for aid in ordered_ids:
                if aid not in group:
                    activities_data.append(
                        {
                            "activity_id": aid,
                            "date": activity_metadata[aid]["date"],
                            "data": None,
                        }
                    )
                    continue

                ivs = group[aid]
                # Aggregate: average if multiple intervals with same label
                agg = {}
                for metric in metrics_to_use:
                    vals = [iv[metric] for iv in ivs if metric in iv and iv[metric] is not None]
                    if vals:
                        avg_val = sum(vals) / len(vals)
                        agg[metric] = round(avg_val, 2) if avg_val != int(avg_val) else int(avg_val)

                activities_data.append(
                    {
                        "activity_id": aid,
                        "date": activity_metadata[aid]["date"],
                        "data": agg if agg else None,
                    }
                )

                # Collect for trends
                for metric, val in agg.items():
                    values_by_metric[metric].append(val)

            # Calculate trends
            trends = {}
            for metric, vals in values_by_metric.items():
                if len(vals) >= 2:
                    first = vals[0]
                    last = vals[-1]
                    delta = round(last - first, 2)
                    delta_pct = round((delta / first) * 100, 1) if first != 0 else None
                    avg = round(sum(vals) / len(vals), 2)
                    trends[metric] = {
                        "first": first,
                        "last": last,
                        "delta": delta,
                        "delta_pct": delta_pct,
                        "avg": avg,
                    }

            comparison.append(
                {
                    "label": label_display.get(norm_label, norm_label),
                    "activities": activities_data,
                    "trends": trends,
                }
            )

        result = {
            "mode": mode,
            "activities_compared": len(resolved),
            "activity_ids": ordered_ids,
            "activity_metadata": activity_metadata,
            "intervals_per_activity": intervals_per_activity,
            "filters_applied": {
                "label_filter": label_filter,
                "type_filter": type_filter,
                "metrics": requested_metrics if requested_metrics else "all",
            },
            "comparison": comparison,
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"error": f"Failed to compare intervals: {str(e)}"},
                    indent=2,
                ),
            )
        ]


async def handle_apply_workout_intervals(args: dict) -> list[TextContent]:
    """Apply custom interval boundaries to an Intervals.icu activity."""
    import re

    from cyclisme_training_logs.config import create_intervals_client
    from cyclisme_training_logs.workout_parser import (
        compute_intervals,
        load_workout_descriptions,
        parse_workout_text,
    )

    activity_id = args["activity_id"]
    dry_run = args.get("dry_run", True)
    manual_intervals = args.get("intervals")

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()

        # --- Manual mode ---
        if manual_intervals is not None:
            if dry_run:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "mode": "manual",
                                "dry_run": True,
                                "activity_id": activity_id,
                                "intervals_count": len(manual_intervals),
                                "intervals": manual_intervals,
                                "message": "Preview only. Set dry_run=false to apply.",
                            },
                            indent=2,
                        ),
                    )
                ]
            with suppress_stdout_stderr():
                result = client.put_activity_intervals(activity_id, manual_intervals)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "mode": "manual",
                            "dry_run": False,
                            "activity_id": activity_id,
                            "applied": True,
                            "result": result,
                        },
                        indent=2,
                    ),
                )
            ]

        # --- Auto mode ---
        # 1. Get activity to extract session_id from name
        session_id = args.get("session_id")
        if not session_id:
            with suppress_stdout_stderr():
                activity = client.get_activity(activity_id)
            activity_name = activity.get("name", "")
            m = re.search(r"(S\d{3}-\d{2}[a-z]?)", activity_name)
            if not m:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "error": f"Cannot extract session_id from activity name: '{activity_name}'",
                                "hint": "Provide session_id parameter explicitly (e.g. S082-02)",
                            },
                            indent=2,
                        ),
                    )
                ]
            session_id = m.group(1)

        # 2. Load workout description
        week_id = session_id.split("-")[0]
        descriptions = load_workout_descriptions(week_id)

        # Find matching workout (session_id appears in workout name)
        workout_text = None
        for name, text in descriptions.items():
            if session_id in name:
                workout_text = text
                break

        if workout_text is None:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": f"No workout found for session {session_id} in {week_id}_workouts.txt",
                            "available_workouts": list(descriptions.keys()),
                        },
                        indent=2,
                    ),
                )
            ]

        # 3. Parse workout
        blocks = parse_workout_text(workout_text)
        if not blocks:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": f"Workout {session_id} is a rest day (no blocks to apply)",
                        },
                        indent=2,
                    ),
                )
            ]

        # 4. Get stream to determine total points
        with suppress_stdout_stderr():
            streams = client.get_activity_streams(activity_id)

        if not streams or not streams[0].get("data"):
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": f"No stream data found for activity {activity_id}",
                        },
                        indent=2,
                    ),
                )
            ]
        total_points = len(streams[0]["data"])

        # 5. Compute intervals
        computed = compute_intervals(blocks, total_points)

        # Build interval dicts for API
        interval_dicts = [
            {
                "type": iv.type,
                "label": iv.label,
                "start_index": iv.start_index,
                "end_index": iv.end_index,
            }
            for iv in computed
        ]

        # Compute summary info
        from cyclisme_training_logs.workout_parser import Phase

        main_seconds = sum(b.duration_seconds for b in blocks if b.phase == Phase.MAIN_SET)
        cooldown_seconds = sum(b.duration_seconds for b in blocks if b.phase == Phase.COOLDOWN)
        prescription_seconds = sum(b.duration_seconds for b in blocks)
        warmup_absorbed = total_points - main_seconds - cooldown_seconds

        summary = {
            "mode": "auto",
            "dry_run": dry_run,
            "activity_id": activity_id,
            "session_id": session_id,
            "stream_points": total_points,
            "prescription_seconds": prescription_seconds,
            "warmup_absorbed": warmup_absorbed,
            "intervals_count": len(interval_dicts),
            "intervals": interval_dicts,
        }

        if dry_run:
            summary["message"] = "Preview only. Set dry_run=false to apply."
            return [TextContent(type="text", text=json.dumps(summary, indent=2))]

        # Apply
        with suppress_stdout_stderr():
            result = client.put_activity_intervals(activity_id, interval_dicts)
        summary["applied"] = True
        summary["result"] = result
        return [TextContent(type="text", text=json.dumps(summary, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Failed to apply workout intervals: {str(e)}",
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
                                    # Extract exercise name from Intervals.icu format
                                    # S082-03-INT-SweetSpotBlocs-V001 → SweetSpotBlocs
                                    parts = updates["name"].split("-")
                                    raw_name = parts[-1]
                                    # If last segment is version (V001, V002...), take the one before
                                    if raw_name.startswith("V") and raw_name[1:].isdigit():
                                        raw_name = parts[-2] if len(parts) >= 2 else updates["name"]
                                    session_dict["name"] = raw_name

                                if "start_date_local" in updates:
                                    # Extract date from datetime string (YYYY-MM-DDTHH:MM:SS)
                                    date_str = updates["start_date_local"].split("T")[0]
                                    session_dict["session_date"] = datetime.strptime(
                                        date_str, "%Y-%m-%d"
                                    ).date()

                                # NOTE: description is NOT written back to local planning.
                                # The planning JSON holds a SHORT description; full workout
                                # content lives in _workouts.txt / .zwo files and Intervals.icu.

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

            # Sport settings for cycling (ftp, zones, hr) are nested in sportSettings
            sport_settings = next(
                (s for s in athlete.get("sportSettings", []) if "Ride" in s.get("types", [])),
                {},
            )

            # Build power zones with names
            power_zone_values = sport_settings.get("power_zones", [])
            power_zone_names = sport_settings.get("power_zone_names", [])
            power_zones = (
                [{"name": n, "max_pct_ftp": v} for n, v in zip(power_zone_names, power_zone_values)]
                if power_zone_values
                else None
            )

            # Build HR zones with names
            hr_zone_values = sport_settings.get("hr_zones", [])
            hr_zone_names = sport_settings.get("hr_zone_names", [])
            hr_zones = (
                [{"name": n, "max_bpm": v} for n, v in zip(hr_zone_names, hr_zone_values)]
                if hr_zone_values
                else None
            )

            result = {
                "name": athlete.get("name"),
                # Top-level icu_ fields
                "weight": athlete.get("icu_weight"),
                "resting_hr": athlete.get("icu_resting_hr"),
                # Cycling sport settings
                "ftp": sport_settings.get("ftp"),
                "max_hr": sport_settings.get("max_hr"),
                "fthr": sport_settings.get("lthr"),
                "w_prime": sport_settings.get("w_prime"),
                "power_zones": power_zones,
                "hr_zones": hr_zones,
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
                    "message": f"No recommendations file generated yet for {week_id}. "
                    "Run PID evaluation or end-of-week workflow to generate recommendations.",
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


# === Withings Health Data Handlers ===


async def handle_withings_auth_status(args: dict) -> list[TextContent]:
    """Check Withings OAuth authentication status."""
    with suppress_stdout_stderr():
        from cyclisme_training_logs.config import get_withings_config

        config = get_withings_config()

        status = {
            "configured": config.is_configured(),
            "has_credentials": config.has_valid_credentials(),
        }

        if not config.is_configured():
            status["message"] = "Withings not configured"
            status["next_steps"] = (
                "Set WITHINGS_CLIENT_ID and WITHINGS_CLIENT_SECRET environment variables"
            )
        elif not config.has_valid_credentials():
            status["message"] = "Not authenticated"
            status["next_steps"] = (
                "Run 'withings-authorize' tool to get authorization URL, "
                "then call again with authorization_code parameter"
            )
        else:
            status["message"] = "Authenticated and ready"
            status["credentials_path"] = str(config.credentials_path)

    return [TextContent(type="text", text=json.dumps(status, indent=2))]


async def handle_withings_authorize(args: dict) -> list[TextContent]:
    """Handle Withings OAuth authorization flow."""
    with suppress_stdout_stderr():
        from cyclisme_training_logs.config import create_withings_client

        client = create_withings_client()
        authorization_code = args.get("authorization_code")

        if not authorization_code:
            # Step 1: Return authorization URL
            auth_url = client.get_authorization_url()

            result = {
                "step": "authorization_required",
                "authorization_url": auth_url,
                "instructions": [
                    "1. Visit the authorization URL above in your browser",
                    "2. Authorize the application",
                    "3. Copy the authorization code from the callback URL",
                    "4. Call this tool again with authorization_code parameter",
                ],
                "note": (
                    "Alternatively, run the setup script: "
                    "python -m cyclisme_training_logs.scripts.setup_withings"
                ),
            }
        else:
            # Step 2: Exchange code for tokens
            try:
                tokens = client.exchange_code(authorization_code)

                result = {
                    "step": "authorization_complete",
                    "status": "success",
                    "message": "✓ Successfully authenticated with Withings",
                    "user_id": tokens["user_id"],
                    "credentials_saved": True,
                }
            except Exception as e:
                result = {"step": "authorization_failed", "status": "error", "error": str(e)}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_withings_get_sleep(args: dict) -> list[TextContent]:
    """Get sleep data from Withings."""
    with suppress_stdout_stderr():
        from datetime import date, timedelta

        from cyclisme_training_logs.config import create_withings_client

        client = create_withings_client()

        last_night_only = args.get("last_night_only", False)

        if last_night_only:
            # Get last night's sleep
            sleep_data = client.get_last_night_sleep()
            result = {"last_night_sleep": sleep_data if sleep_data else None}

            if not sleep_data:
                result["message"] = "No sleep data available for last night"
        else:
            # Get sleep for date range
            start_date_str = args.get("start_date")
            end_date_str = args.get("end_date")

            if not start_date_str:
                # Default: last 7 days
                end_date = date.today()
                start_date = end_date - timedelta(days=7)
            else:
                start_date = date.fromisoformat(start_date_str)
                end_date = date.fromisoformat(end_date_str) if end_date_str else date.today()

            sleep_sessions = client.get_sleep(start_date, end_date)

            result = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "sleep_sessions": sleep_sessions,
                "count": len(sleep_sessions),
            }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_withings_get_weight(args: dict) -> list[TextContent]:
    """Get weight measurements from Withings."""
    with suppress_stdout_stderr():
        from datetime import date, timedelta

        from cyclisme_training_logs.config import create_withings_client

        client = create_withings_client()

        latest_only = args.get("latest_only", False)

        if latest_only:
            # Get latest weight
            weight_data = client.get_latest_weight()
            result = {"latest_weight": weight_data if weight_data else None}

            if not weight_data:
                result["message"] = "No weight data available"
        else:
            # Get weight for date range
            start_date_str = args.get("start_date")
            end_date_str = args.get("end_date")

            if not start_date_str:
                # Default: last 30 days
                end_date = date.today()
                start_date = end_date - timedelta(days=30)
            else:
                start_date = date.fromisoformat(start_date_str)
                end_date = date.fromisoformat(end_date_str) if end_date_str else date.today()

            measurements = client.get_measurements(
                start_date, end_date, measure_types=[1, 6, 8, 76, 88]
            )

            result = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "measurements": measurements,
                "count": len(measurements),
            }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_withings_get_readiness(args: dict) -> list[TextContent]:
    """Evaluate training readiness based on health metrics."""
    with suppress_stdout_stderr():
        from datetime import date

        from cyclisme_training_logs.config import create_withings_client

        client = create_withings_client()

        eval_date_str = args.get("date")
        eval_date = date.fromisoformat(eval_date_str) if eval_date_str else date.today()

        # Get last night's sleep
        sleep_data = client.get_last_night_sleep()

        if not sleep_data:
            result = {
                "date": eval_date.isoformat(),
                "status": "no_data",
                "message": "No sleep data available for evaluation",
            }
        else:
            # Evaluate readiness
            readiness = client.evaluate_training_readiness(sleep_data)

            # Get latest weight for context
            weight_data = client.get_latest_weight()
            if weight_data:
                readiness["weight_kg"] = weight_data["weight_kg"]

            result = {
                "date": eval_date.isoformat(),
                "status": "evaluated",
                "readiness": readiness,
            }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_withings_sync_to_intervals(args: dict) -> list[TextContent]:
    """Synchronize Withings data to Intervals.icu wellness."""
    with suppress_stdout_stderr():
        from datetime import date

        from cyclisme_training_logs.config import create_intervals_client, create_withings_client

        withings_client = create_withings_client()
        intervals_client = create_intervals_client()

        start_date_str = args["start_date"]
        end_date_str = args.get("end_date")
        data_types = args.get("data_types", ["all"])

        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str) if end_date_str else date.today()

        # Determine what to sync
        sync_sleep = "all" in data_types or "sleep" in data_types
        sync_weight = "all" in data_types or "weight" in data_types

        synced_dates = []
        errors = []

        # Fetch Withings data
        sleep_data_list = []
        weight_data_list = []

        if sync_sleep:
            sleep_data_list = withings_client.get_sleep(start_date, end_date)

        if sync_weight:
            weight_data_list = withings_client.get_measurements(start_date, end_date)

        # Create lookup dictionaries
        sleep_by_date = {s["date"]: s for s in sleep_data_list}
        weight_by_date = {w["date"]: w for w in weight_data_list}

        # Iterate through each date and sync
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.isoformat()

            try:
                # Get current wellness data for this date
                wellness = intervals_client.get_wellness(date_str)

                if wellness is None:
                    wellness = {}

                # Update with sleep data
                if sync_sleep and date_str in sleep_by_date:
                    sleep_info = sleep_by_date[date_str]
                    wellness["sleepSecs"] = int(sleep_info["total_sleep_hours"] * 3600)
                    wellness["sleepQuality"] = sleep_info.get("sleep_score")

                # Update with weight data
                if sync_weight and date_str in weight_by_date:
                    weight_info = weight_by_date[date_str]
                    wellness["weight"] = weight_info["weight_kg"]

                # Only update if we have data to sync
                if date_str in sleep_by_date or date_str in weight_by_date:
                    intervals_client.update_wellness(date_str, wellness)
                    synced_dates.append(date_str)

            except Exception as e:
                errors.append({"date": date_str, "error": str(e)})

            current_date = current_date + timedelta(days=1)

        result = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "data_types": data_types,
            "synced_dates": synced_dates,
            "synced_count": len(synced_dates),
            "errors": errors,
            "status": "success" if not errors else "partial_success",
        }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_withings_analyze_trends(args: dict) -> list[TextContent]:
    """Analyze health trends over time."""
    with suppress_stdout_stderr():
        from datetime import date, timedelta

        from cyclisme_training_logs.config import create_withings_client

        client = create_withings_client()

        period = args.get("period", "week")

        if period == "week":
            end_date = date.today()
            start_date = end_date - timedelta(days=7)
        elif period == "month":
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
        else:  # custom
            start_date_str = args.get("start_date")
            end_date_str = args.get("end_date")

            if not start_date_str or not end_date_str:
                result = {
                    "error": "start_date and end_date required for custom period",
                    "status": "error",
                }
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)

        # Fetch data
        sleep_sessions = client.get_sleep(start_date, end_date)
        weight_measurements = client.get_measurements(start_date, end_date)

        # Analyze sleep trends
        total_nights = len(sleep_sessions)

        if total_nights > 0:
            total_sleep_hours = sum(s["total_sleep_hours"] for s in sleep_sessions)
            avg_sleep_hours = total_sleep_hours / total_nights

            sleep_scores = [s["sleep_score"] for s in sleep_sessions if s.get("sleep_score")]
            avg_sleep_score = sum(sleep_scores) / len(sleep_scores) if sleep_scores else None

            nights_above_7h = sum(1 for s in sleep_sessions if s["total_sleep_hours"] >= 7)

            # Calculate sleep debt (assume 7h target)
            sleep_debt_hours = (7 * total_nights) - total_sleep_hours
        else:
            avg_sleep_hours = 0
            avg_sleep_score = None
            nights_above_7h = 0
            sleep_debt_hours = 0

        # Analyze weight trends
        if weight_measurements:
            weight_start = weight_measurements[0]["weight_kg"]
            weight_end = weight_measurements[-1]["weight_kg"]
            weight_delta = weight_end - weight_start
        else:
            weight_start = None
            weight_end = None
            weight_delta = None

        # Determine status
        if avg_sleep_hours >= 7.5 and nights_above_7h / max(total_nights, 1) >= 0.85:
            status = "optimal"
        elif avg_sleep_hours >= 6.5:
            status = "adequate"
        elif avg_sleep_hours >= 5.5:
            status = "debt"
        else:
            status = "critical"

        # Generate alerts
        alerts = []
        if sleep_debt_hours > 7:
            alerts.append(f"Sleep debt: {sleep_debt_hours:.1f}h over {total_nights} nights")
        if avg_sleep_hours < 6.5:
            alerts.append(f"Low average sleep: {avg_sleep_hours:.1f}h/night")
        if weight_delta and abs(weight_delta) > 2:
            alerts.append(f"Significant weight change: {weight_delta:+.1f} kg")

        result = {
            "period": period,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "sleep_analysis": {
                "avg_sleep_hours": round(avg_sleep_hours, 2),
                "avg_sleep_score": round(avg_sleep_score, 1) if avg_sleep_score else None,
                "nights_above_7h": nights_above_7h,
                "total_nights": total_nights,
                "sleep_debt_hours": round(sleep_debt_hours, 1),
            },
            "weight_analysis": {
                "weight_start_kg": weight_start,
                "weight_end_kg": weight_end,
                "weight_delta_kg": round(weight_delta, 2) if weight_delta else None,
            },
            "status": status,
            "alerts": alerts,
        }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_withings_enrich_session(args: dict) -> list[TextContent]:
    """Enrich training session with Withings health metrics."""
    with suppress_stdout_stderr():
        from datetime import date, timedelta

        from cyclisme_training_logs.config import create_withings_client
        from cyclisme_training_logs.planning.control_tower import planning_tower

        week_id = args["week_id"]
        session_id = args["session_id"]
        auto_readiness_check = args.get("auto_readiness_check", True)

        withings_client = create_withings_client()

        # Load session
        with planning_tower.modify_week(
            week_id, requesting_script="mcp-server", reason="Enrich session with Withings data"
        ) as plan:
            # Find session
            session = None
            for s in plan.planned_sessions:
                if s.session_id == session_id:
                    session = s
                    break

            if not session:
                result = {
                    "error": f"Session {session_id} not found in week {week_id}",
                    "status": "error",
                }
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            # Get session date
            session_date = date.fromisoformat(session.date)

            # Get sleep from previous night
            sleep_date = session_date - timedelta(days=1)
            sleep_sessions = withings_client.get_sleep(sleep_date, session_date)

            sleep_data = sleep_sessions[-1] if sleep_sessions else None

            # Get latest weight
            weight_data = withings_client.get_latest_weight()

            # Initialize health_metrics if not present
            if not hasattr(session, "health_metrics"):
                session.health_metrics = {}

            # Add sleep metrics
            if sleep_data:
                session.health_metrics["sleep_hours"] = sleep_data["total_sleep_hours"]
                session.health_metrics["sleep_score"] = sleep_data.get("sleep_score")
                session.health_metrics["deep_sleep_minutes"] = sleep_data.get("deep_sleep_minutes")

                # Evaluate readiness
                if auto_readiness_check:
                    readiness = withings_client.evaluate_training_readiness(sleep_data)
                    session.health_metrics["training_readiness"] = readiness[
                        "recommended_intensity"
                    ]
                    session.health_metrics["ready_for_intense"] = readiness["ready_for_intense"]
                    session.health_metrics["veto_reasons"] = readiness["veto_reasons"]
                    session.health_metrics["recommendations"] = readiness["recommendations"]

            # Add weight
            if weight_data:
                session.health_metrics["weight_kg"] = weight_data["weight_kg"]

            result = {
                "week_id": week_id,
                "session_id": session_id,
                "session_date": session.date,
                "health_metrics_added": session.health_metrics,
                "status": "success",
            }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def async_main():
    """Run MCP server with configured transport (stdio or HTTP/SSE)."""
    # Log transport mode to stderr (visible in debug logs)
    if TRANSPORT_MODE == "http":
        print(f"[MCP] Starting HTTP/SSE server on {HTTP_HOST}:{HTTP_PORT}", file=sys.stderr)
    else:
        print("[MCP] Starting stdio transport", file=sys.stderr)

    # Create and start transport manager
    transport = MCPTransportManager(
        server=server,
        transport_mode=TRANSPORT_MODE,
        host=HTTP_HOST,
        port=HTTP_PORT,
    )

    await transport.start()


def main():
    """Entry point for Poetry script."""
    import asyncio

    asyncio.run(async_main())


if __name__ == "__main__":
    main()
