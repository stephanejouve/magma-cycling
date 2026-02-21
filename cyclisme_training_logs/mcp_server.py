#!/usr/bin/env python3
"""
MCP Server for Cyclisme Training Logs.

Exposes training management tools to Claude Desktop and other MCP clients.

Tools provided:
- weekly-planner: Generate weekly training plans
- monthly-analysis: Monthly training analysis and insights
- daily-sync: Sync with Intervals.icu
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
                "required": [],
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
        for activity in new_activities:
            sync.tracker.mark_analyzed(activity, datetime.now())

        # Auto-update session statuses using ALL completed activities (not just new ones)
        # This ensures status updates even for activities analyzed in previous runs
        if completed_activities:
            sync.update_completed_sessions(completed_activities)

    result = {
        "date": check_date.isoformat(),
        "completed_activities": len(completed_activities),
        "new_activities": len(new_activities),
        "status": "completed",
        "message": f"Sync completed for {check_date.isoformat()}",
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_update_session(args: dict) -> list[TextContent]:
    """Update session status."""
    from cyclisme_training_logs.planning.control_tower import planning_tower

    week_id = args["week_id"]
    session_id = args["session_id"]
    new_status = args["status"]
    reason = args.get("reason")

    # Suppress all output to prevent JSON protocol pollution
    with suppress_stdout_stderr():
        # Update via Control Tower
        with planning_tower.modify_week(
            week_id,
            requesting_script="mcp-server",
            reason=f"MCP: Update {session_id} to {new_status}: {reason or 'N/A'}",
        ) as plan:
            session_found = False
            for session in plan.planned_sessions:
                if session.session_id == session_id:
                    # Set skip_reason BEFORE status (Pydantic validator)
                    if reason and new_status in ("skipped", "cancelled", "replaced"):
                        session.skip_reason = reason

                    session.status = new_status
                    session_found = True
                    break

            if not session_found:
                raise ValueError(f"Session {session_id} not found in {week_id}")

    result = {
        "week_id": week_id,
        "session_id": session_id,
        "status": new_status,
        "reason": reason,
        "message": f"Session {session_id} updated to {new_status}",
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
