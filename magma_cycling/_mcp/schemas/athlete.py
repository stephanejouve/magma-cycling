"""Athlete profile tool schemas."""

from mcp.types import Tool


def get_tools() -> list[Tool]:
    """Return athlete profile tool schemas."""
    return [
        Tool(
            name="get-athlete-profile",
            description="Get current athlete profile (FTP, weight, CTL, ATL, TSB, zones)",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="update-athlete-profile",
            description=(
                "Update athlete profile. The handler dispatches per field: "
                "Intervals.icu API for training fields (ftp, weight, max_hr, "
                "resting_hr, fthr, etc.) and the local athlete YAML for "
                "portable fields (home_location). MCT-XXX-0."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "updates": {
                        "type": "object",
                        "description": (
                            "Fields to update. Training fields (ftp, weight, "
                            "max_hr, resting_hr, fthr, etc.) hit Intervals.icu. "
                            "`home_location` (object with lat/lon + optional label) "
                            "is written to the local athlete YAML."
                        ),
                        "additionalProperties": True,
                        "properties": {
                            "home_location": {
                                "type": "object",
                                "description": (
                                    "Athlete's home / training base location. "
                                    "Latitude and longitude in decimal degrees, "
                                    "optional human label (e.g. 'Chas')."
                                ),
                                "properties": {
                                    "lat": {
                                        "type": "number",
                                        "minimum": -90,
                                        "maximum": 90,
                                    },
                                    "lon": {
                                        "type": "number",
                                        "minimum": -180,
                                        "maximum": 180,
                                    },
                                    "label": {"type": "string"},
                                },
                                "required": ["lat", "lon"],
                                "additionalProperties": False,
                            },
                        },
                    },
                },
                "required": ["updates"],
            },
        ),
    ]
