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
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
)

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
                        "description": "Session ID (e.g., S082-03)",
                        "pattern": "^S\\d{3}-\\d{2}$",
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

    # Redirect stdout to stderr to prevent JSON protocol pollution
    with redirect_stdout(sys.stderr):
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

    # Redirect stdout to stderr to prevent JSON protocol pollution
    with redirect_stdout(sys.stderr):
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
    )

    # Redirect stdout to stderr to prevent JSON protocol pollution
    with redirect_stdout(sys.stderr):
        # Run sync
        new_activities = sync.check_activities(check_date)

        # Mark as analyzed
        for activity in new_activities:
            sync.tracker.mark_analyzed(activity, datetime.now())

        # Auto-update session statuses
        if new_activities:
            sync.update_completed_sessions(new_activities)

    result = {
        "date": check_date.isoformat(),
        "activities_found": len(new_activities),
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

    # Redirect stdout to stderr to prevent JSON protocol pollution
    with redirect_stdout(sys.stderr):
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
