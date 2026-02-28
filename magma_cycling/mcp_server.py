#!/usr/bin/env python3
"""
MCP Server for Cyclisme Training Logs.

Exposes training management tools to Claude Desktop and other MCP clients.

This module is a thin facade that delegates to handler and schema sub-modules
under ``magma_cycling.mcp``.

Usage:
    poetry run mcp-server

Claude Desktop config (~/.config/claude/claude_desktop_config.json):
    {
      "mcpServers": {
        "magma-cycling": {
          "command": "poetry",
          "args": ["run", "mcp-server"],
          "cwd": "/path/to/magma-cycling"
        }
      }
    }
"""

import json
import os
import sys

from mcp.server import Server
from mcp.types import TextContent, Tool
from mcp_http_transport import MCPTransportManager

from magma_cycling._mcp.handlers.admin import (  # noqa: F401
    handle_reload_server,
)
from magma_cycling._mcp.handlers.analysis import (  # noqa: F401
    handle_analyze_session_adherence,
    handle_analyze_training_patterns,
    handle_export_week_to_json,
    handle_get_recommendations,
    handle_get_training_statistics,
    handle_restore_week_from_backup,
    handle_validate_week_consistency,
)
from magma_cycling._mcp.handlers.athlete import (  # noqa: F401
    handle_get_athlete_profile,
    handle_update_athlete_profile,
)
from magma_cycling._mcp.handlers.intervals import (  # noqa: F401
    handle_apply_workout_intervals,
    handle_backfill_activities,
    handle_compare_intervals,
    handle_create_remote_note,
    handle_delete_remote_session,
    handle_get_activity_details,
    handle_get_activity_intervals,
    handle_get_activity_streams,
    handle_list_remote_events,
    handle_sync_remote_to_local,
    handle_sync_week_to_intervals,
    handle_update_remote_session,
)

# ---------------------------------------------------------------------------
# Re-exports — backward compat: all 43 handlers importable from mcp_server
# ---------------------------------------------------------------------------
from magma_cycling._mcp.handlers.planning import (  # noqa: F401
    handle_create_session,
    handle_daily_sync,
    handle_delete_session,
    handle_get_metrics,
    handle_get_week_details,
    handle_list_weeks,
    handle_modify_session_details,
    handle_monthly_analysis,
    handle_rename_session,
    handle_update_session,
    handle_weekly_planner,
)
from magma_cycling._mcp.handlers.sessions import (  # noqa: F401
    handle_attach_workout,
    handle_duplicate_session,
    handle_swap_sessions,
)
from magma_cycling._mcp.handlers.withings import (  # noqa: F401
    handle_withings_analyze_trends,
    handle_withings_auth_status,
    handle_withings_authorize,
    handle_withings_enrich_session,
    handle_withings_get_readiness,
    handle_withings_get_sleep,
    handle_withings_get_weight,
    handle_withings_sync_to_intervals,
)
from magma_cycling._mcp.handlers.workouts import (  # noqa: F401
    handle_get_workout,
    handle_validate_workout,
)

# Schemas
from magma_cycling._mcp.schemas import admin as _s_admin
from magma_cycling._mcp.schemas import analysis as _s_analysis
from magma_cycling._mcp.schemas import athlete as _s_athlete
from magma_cycling._mcp.schemas import intervals as _s_intervals
from magma_cycling._mcp.schemas import planning as _s_planning
from magma_cycling._mcp.schemas import sessions as _s_sessions
from magma_cycling._mcp.schemas import withings as _s_withings
from magma_cycling._mcp.schemas import workouts as _s_workouts

# ---------------------------------------------------------------------------
# Server initialization
# ---------------------------------------------------------------------------
server = Server("magma-cycling")

# Transport configuration from environment variables
TRANSPORT_MODE = os.getenv("MCP_TRANSPORT", "stdio")  # "stdio" (default) or "http"
HTTP_HOST = os.getenv("MCP_HTTP_HOST", "localhost")
HTTP_PORT = int(os.getenv("MCP_HTTP_PORT", "3000"))


# ---------------------------------------------------------------------------
# Tool listing
# ---------------------------------------------------------------------------
@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available training management tools."""
    return [
        *_s_planning.get_tools(),
        *_s_sessions.get_tools(),
        *_s_workouts.get_tools(),
        *_s_intervals.get_tools(),
        *_s_athlete.get_tools(),
        *_s_analysis.get_tools(),
        *_s_admin.get_tools(),
        *_s_withings.get_tools(),
    ]


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------
TOOL_HANDLERS = {
    # Planning (11)
    "weekly-planner": handle_weekly_planner,
    "monthly-analysis": handle_monthly_analysis,
    "daily-sync": handle_daily_sync,
    "update-session": handle_update_session,
    "list-weeks": handle_list_weeks,
    "get-metrics": handle_get_metrics,
    "get-week-details": handle_get_week_details,
    "modify-session-details": handle_modify_session_details,
    "rename-session": handle_rename_session,
    "create-session": handle_create_session,
    "delete-session": handle_delete_session,
    # Sessions (3)
    "duplicate-session": handle_duplicate_session,
    "swap-sessions": handle_swap_sessions,
    "attach-workout": handle_attach_workout,
    # Workouts (2)
    "get-workout": handle_get_workout,
    "validate-workout": handle_validate_workout,
    # Intervals.icu (12)
    "sync-week-to-intervals": handle_sync_week_to_intervals,
    "delete-remote-session": handle_delete_remote_session,
    "list-remote-events": handle_list_remote_events,
    "get-activity-details": handle_get_activity_details,
    "get-activity-intervals": handle_get_activity_intervals,
    "get-activity-streams": handle_get_activity_streams,
    "compare-intervals": handle_compare_intervals,
    "apply-workout-intervals": handle_apply_workout_intervals,
    "update-remote-session": handle_update_remote_session,
    "create-remote-note": handle_create_remote_note,
    "sync-remote-to-local": handle_sync_remote_to_local,
    "backfill-activities": handle_backfill_activities,
    # Athlete (2)
    "get-athlete-profile": handle_get_athlete_profile,
    "update-athlete-profile": handle_update_athlete_profile,
    # Analysis (7)
    "validate-week-consistency": handle_validate_week_consistency,
    "get-recommendations": handle_get_recommendations,
    "analyze-session-adherence": handle_analyze_session_adherence,
    "get-training-statistics": handle_get_training_statistics,
    "export-week-to-json": handle_export_week_to_json,
    "restore-week-from-backup": handle_restore_week_from_backup,
    "analyze-training-patterns": handle_analyze_training_patterns,
    # Admin (1)
    "reload-server": handle_reload_server,
    # Withings (8)
    "withings-auth-status": handle_withings_auth_status,
    "withings-authorize": handle_withings_authorize,
    "withings-get-sleep": handle_withings_get_sleep,
    "withings-get-weight": handle_withings_get_weight,
    "withings-get-readiness": handle_withings_get_readiness,
    "withings-sync-to-intervals": handle_withings_sync_to_intervals,
    "withings-analyze-trends": handle_withings_analyze_trends,
    "withings-enrich-session": handle_withings_enrich_session,
}


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls from MCP clients."""
    try:
        handler = TOOL_HANDLERS.get(name)
        if not handler:
            raise ValueError(f"Unknown tool: {name}")
        return await handler(arguments)
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


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------
async def async_main():
    """Run MCP server with configured transport (stdio or HTTP/SSE)."""
    if TRANSPORT_MODE == "http":
        print(f"[MCP] Starting HTTP/SSE server on {HTTP_HOST}:{HTTP_PORT}", file=sys.stderr)
    else:
        print("[MCP] Starting stdio transport", file=sys.stderr)

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
