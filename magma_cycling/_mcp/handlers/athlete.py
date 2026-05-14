"""Athlete profile handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from magma_cycling._mcp._utils import mcp_response, suppress_stdout_stderr
from magma_cycling.config.geo import GeoPoint, load_home_location, save_home_location

if TYPE_CHECKING:
    from mcp.types import TextContent

__all__ = [
    "handle_get_athlete_profile",
    "handle_update_athlete_profile",
]

# Local-only fields routed to the athlete YAML (not Intervals.icu).
# Extend this set as more portable fields land (PR5 iso-config and beyond).
_LOCAL_FIELDS = frozenset({"home_location"})


async def handle_get_athlete_profile(args: dict) -> list[TextContent]:
    """Get current athlete profile from training platform + local config."""
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

        # Local-only fields (MCT-XXX-0). ``None`` is returned when the YAML
        # hasn't been populated yet — migration-noop semantics expected by
        # downstream callers (find-suitable-circuits returns NEEDS_LOCATION).
        home = load_home_location()
        result["home_location"] = home.model_dump(exclude_none=True) if home else None

        return mcp_response(result)

    except Exception as e:
        return mcp_response({"error": f"Failed to get athlete profile: {str(e)}"})


async def handle_update_athlete_profile(args: dict) -> list[TextContent]:
    """Update athlete profile (dispatch local YAML vs Intervals.icu per field)."""
    from magma_cycling.config import create_intervals_client

    updates = dict(args["updates"])
    local_updates = {k: updates.pop(k) for k in list(updates) if k in _LOCAL_FIELDS}
    remote_updates = updates

    updated_fields: list[str] = []
    current_values: dict[str, object] = {}

    try:
        with suppress_stdout_stderr():
            # 1. Local fields (athlete YAML)
            if "home_location" in local_updates:
                location = GeoPoint.model_validate(local_updates["home_location"])
                save_home_location(location)
                updated_fields.append("home_location")
                current_values["home_location"] = location.model_dump(exclude_none=True)

            # 2. Remote fields (Intervals.icu)
            if remote_updates:
                client = create_intervals_client()
                updated_athlete = client.update_athlete(remote_updates)
                updated_fields.extend(remote_updates.keys())
                for field in remote_updates:
                    current_values[field] = updated_athlete.get(field)

            result = {
                "success": True,
                "updated_fields": updated_fields,
                "message": "✅ Athlete profile updated successfully",
                "current_values": current_values,
            }

        return mcp_response(result)

    except Exception as e:
        return mcp_response(
            {
                "error": f"Failed to update athlete profile: {str(e)}",
                "updates": args["updates"],
            }
        )
