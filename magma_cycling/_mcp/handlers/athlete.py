"""Athlete profile handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from magma_cycling._mcp._utils import mcp_response, suppress_stdout_stderr

if TYPE_CHECKING:
    from mcp.types import TextContent

__all__ = [
    "handle_get_athlete_profile",
    "handle_update_athlete_profile",
]


async def handle_get_athlete_profile(args: dict) -> list[TextContent]:
    """Get current athlete profile from training platform."""
    from magma_cycling.config import create_intervals_client

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

        return mcp_response(result)

    except Exception as e:
        return mcp_response({"error": f"Failed to get athlete profile: {str(e)}"})


async def handle_update_athlete_profile(args: dict) -> list[TextContent]:
    """Update athlete profile on training platform."""
    from magma_cycling.config import create_intervals_client

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

        return mcp_response(result)

    except Exception as e:
        return mcp_response(
            {
                "error": f"Failed to update athlete profile: {str(e)}",
                "updates": updates,
            }
        )
