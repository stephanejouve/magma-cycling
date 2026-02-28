"""Athlete profile handlers."""

import json

from mcp.types import TextContent

from cyclisme_training_logs._mcp._utils import suppress_stdout_stderr

__all__ = [
    "handle_get_athlete_profile",
    "handle_update_athlete_profile",
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
                    {
                        "error": f"Failed to update athlete profile: {str(e)}",
                        "updates": updates,
                    },
                    indent=2,
                ),
            )
        ]
