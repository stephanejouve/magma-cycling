"""Athlete profile tool schemas."""

from mcp.types import Tool


def get_tools() -> list[Tool]:
    """Return athlete profile tool schemas."""
    return [
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
    ]
