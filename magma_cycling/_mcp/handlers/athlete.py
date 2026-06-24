"""Athlete profile handlers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from magma_cycling._mcp._utils import mcp_response, suppress_stdout_stderr
from magma_cycling.config.geo import GeoPoint, load_home_location, save_home_location
from magma_cycling.config.objectives import (
    PriorityObjective,
    clear_priority_objective,
    load_priority_objective,
    save_priority_objective,
)
from magma_cycling.config.profile_rich import (
    AvailabilityPattern,
    HrvBaseline,
    InjuryHistory,
    MacroPlan,
    NutritionStrategy,
    SleepBaseline,
    clear_availability_pattern,
    clear_hrv_baseline,
    clear_injury_history,
    clear_macro_plan,
    clear_nutrition_strategy,
    clear_sleep_baseline,
    load_availability_pattern,
    load_hrv_baseline,
    load_injury_history,
    load_macro_plan,
    load_nutrition_strategy,
    load_sleep_baseline,
    save_availability_pattern,
    save_hrv_baseline,
    save_injury_history,
    save_macro_plan,
    save_nutrition_strategy,
    save_sleep_baseline,
)

if TYPE_CHECKING:
    from mcp.types import TextContent
    from pydantic import BaseModel

logger = logging.getLogger(__name__)

__all__ = [
    "handle_get_athlete_profile",
    "handle_update_athlete_profile",
]

# BT-017 rich profile fields: (pydantic model, save fn, clear fn).
# Each is dispatched identically — validated, persisted to athlete YAML,
# or cleared when the update payload sends ``null``.
_RICH_FIELDS: dict[str, tuple[type["BaseModel"], object, object]] = {
    "hrv_baseline": (HrvBaseline, save_hrv_baseline, clear_hrv_baseline),
    "injury_history": (InjuryHistory, save_injury_history, clear_injury_history),
    "macro_plan": (MacroPlan, save_macro_plan, clear_macro_plan),
    "nutrition_strategy": (
        NutritionStrategy,
        save_nutrition_strategy,
        clear_nutrition_strategy,
    ),
    "sleep_baseline": (SleepBaseline, save_sleep_baseline, clear_sleep_baseline),
    "availability_pattern": (
        AvailabilityPattern,
        save_availability_pattern,
        clear_availability_pattern,
    ),
}

# Local-only fields routed to the athlete YAML (not Intervals.icu).
# Extend this set as more portable fields land (PR5 iso-config and beyond).
_LOCAL_FIELDS = frozenset({"home_location", "priority_objective"} | set(_RICH_FIELDS))


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

        priority = load_priority_objective()
        result["priority_objective"] = (
            priority.model_dump(mode="json", exclude_none=True) if priority else None
        )

        # BT-017 rich profile fields — all are optional / migration-noop.
        for field, loader in (
            ("hrv_baseline", load_hrv_baseline),
            ("injury_history", load_injury_history),
            ("macro_plan", load_macro_plan),
            ("nutrition_strategy", load_nutrition_strategy),
            ("sleep_baseline", load_sleep_baseline),
            ("availability_pattern", load_availability_pattern),
        ):
            obj = loader()
            result[field] = obj.model_dump(mode="json", exclude_none=True) if obj else None

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

            if "priority_objective" in local_updates:
                raw = local_updates["priority_objective"]
                if raw is None:
                    cleared = clear_priority_objective()
                    updated_fields.append("priority_objective")
                    current_values["priority_objective"] = None
                    if cleared is None:
                        logger.debug("priority_objective clear request with no existing value")
                else:
                    objective = PriorityObjective.model_validate(raw)
                    save_priority_objective(objective)
                    updated_fields.append("priority_objective")
                    current_values["priority_objective"] = objective.model_dump(
                        mode="json", exclude_none=True
                    )

            # BT-017 rich profile fields — same dispatch for the 6 of them.
            for field, (model_cls, save_fn, clear_fn) in _RICH_FIELDS.items():
                if field not in local_updates:
                    continue
                raw = local_updates[field]
                if raw is None:
                    cleared = clear_fn()  # type: ignore[operator]
                    updated_fields.append(field)
                    current_values[field] = None
                    if cleared is None:
                        logger.debug("%s clear request with no existing value", field)
                else:
                    obj = model_cls.model_validate(raw)
                    save_fn(obj)  # type: ignore[operator]
                    updated_fields.append(field)
                    current_values[field] = obj.model_dump(mode="json", exclude_none=True)

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
