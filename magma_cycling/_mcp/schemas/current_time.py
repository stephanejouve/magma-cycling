"""Current time tool schema — AC6 levier 2/3 du plan iso-config S093-S096."""

from mcp.types import Tool


def get_tools() -> list[Tool]:
    """Return current-time tool schema."""
    return [
        Tool(
            name="current-time",
            description=(
                "Return canonical server time information (UTC + local + timezone + "
                "ISO week + day-of-week FR). Authoritative time-of-truth callable — "
                "use this whenever you doubt your temporal context instead of inferring "
                "the date from conversation history. Ultra-light, no side effects, no "
                "arguments. Recommended at session start and after any long pause."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
    ]
