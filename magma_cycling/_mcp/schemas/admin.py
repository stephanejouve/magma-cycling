"""Admin tool schemas."""

from mcp.types import Tool


def get_tools() -> list[Tool]:
    """Return admin tool schemas."""
    return [
        Tool(
            name="reload-server",
            description="[DEV] Reload MCP server modules to pick up code changes without restarting Claude Desktop",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="system-info",
            description="Return active providers and system metadata (health, calendar, AI). Use at conversation start to discover the runtime configuration.",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]
