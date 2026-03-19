"""Rest and recovery handlers — pre-session safety gate."""

from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING

from magma_cycling._mcp._utils import mcp_response, suppress_stdout_stderr

if TYPE_CHECKING:
    from mcp.types import TextContent

__all__ = ["handle_pre_session_check"]

logger = logging.getLogger(__name__)


def _find_week_id_for_date(target: date) -> str | None:
    """Find the week_id whose date range contains *target*."""
    import json

    from magma_cycling.config import get_data_config

    config = get_data_config()
    for path in sorted(config.week_planning_dir.glob("week_planning_S*.json")):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        start = data.get("start_date")
        end = data.get("end_date")
        if start and end:
            sd = date.fromisoformat(start)
            ed = date.fromisoformat(end)
            if sd <= target <= ed:
                return data.get("week_id")
    return None


def _find_session_for_date(week_id: str, target: date) -> dict | None:
    """Return the first planned session matching *target* in the planning."""
    from magma_cycling.planning.control_tower import planning_tower

    try:
        plan = planning_tower.read_week(week_id)
    except FileNotFoundError:
        return None

    for session in plan.planned_sessions:
        if session.session_date == target:
            return {
                "session_id": session.session_id,
                "name": session.name,
                "tss_planned": session.tss_planned,
                "session_type": session.session_type,
                "duration_min": session.duration_min,
                "status": session.status,
            }
    return None


async def handle_pre_session_check(args: dict) -> list[TextContent]:
    """Pre-session safety gate: Withings sync + veto protocol."""
    with suppress_stdout_stderr():
        from magma_cycling.config import AthleteProfile, create_intervals_client
        from magma_cycling.health import create_health_provider
        from magma_cycling.workflows.rest.veto_check import check_pre_session_veto

        # 1. Parse date + extra_sleep_hours
        date_str = args.get("date")
        target = date.fromisoformat(date_str) if date_str else date.today()
        date_str = target.isoformat()
        extra_sleep_hours = float(args.get("extra_sleep_hours", 0.0))

        # 2. Withings sync (best-effort — fallback to cached data)
        wellness_source = "fresh"
        try:
            from magma_cycling._mcp.handlers.withings import (
                sync_withings_to_intervals,
            )

            sync_withings_to_intervals(
                start_date=target,
                end_date=target,
                data_types=["sleep"],
            )
        except Exception as exc:
            logger.warning("Withings sync failed, using cached data: %s", exc)
            wellness_source = "cached"

        # 3. Wellness from Intervals.icu
        client = create_intervals_client()
        wellness_list = client.get_wellness(oldest=date_str, newest=date_str)
        wellness_raw = wellness_list[0] if wellness_list else {}

        sleep_hours = wellness_raw.get("sleepTime")
        if sleep_hours and isinstance(sleep_hours, (int, float)) and sleep_hours > 24:
            # sleepTime is in seconds from Intervals.icu
            sleep_hours = round(sleep_hours / 3600, 2)

        wellness = {
            "ctl": wellness_raw.get("ctl", 0),
            "atl": wellness_raw.get("atl", 0),
            "tsb": wellness_raw.get("ctl", 0) - wellness_raw.get("atl", 0),
            "sleep_hours": sleep_hours,
            "systolic": wellness_raw.get("systolic"),
            "diastolic": wellness_raw.get("diastolic"),
        }

        # 4. Readiness from HealthProvider (best-effort, before veto)
        readiness_data = None
        try:
            provider = create_health_provider()
            readiness = provider.get_readiness(target)
            if readiness:
                readiness_data = readiness.model_dump(mode="json")
                # Enrich wellness with Withings sleep if Intervals.icu has none
                if wellness["sleep_hours"] is None and readiness.sleep_hours:
                    wellness["sleep_hours"] = readiness.sleep_hours
        except Exception:
            pass

        # 4b. Apply extra_sleep_hours override (couch sleep, nap, etc.)
        if extra_sleep_hours > 0 and wellness.get("sleep_hours") is not None:
            wellness["sleep_hours"] = round(wellness["sleep_hours"] + extra_sleep_hours, 2)
            wellness["sleep_hours_source"] = "withings+manual_override"

            # Persist corrected sleep to Intervals.icu so daily reports use it
            try:
                corrected_secs = int(wellness["sleep_hours"] * 3600)
                client.update_wellness(date_str, {"sleepSecs": corrected_secs})
                logger.info(
                    "Persisted corrected sleepSecs=%d to Intervals.icu for %s",
                    corrected_secs,
                    date_str,
                )
            except Exception as exc:
                logger.warning("Failed to persist sleep override: %s", exc)

        # 5. Planned session from planning
        week_id = args.get("week_id") or _find_week_id_for_date(target)
        session_info = None
        if week_id:
            session_info = _find_session_for_date(week_id, target)

        # 6. Athlete profile
        profile = AthleteProfile.from_env()

        # 7. Veto check
        intensity = None
        if session_info and session_info.get("session_type") in (
            "INT",
            "VO2",
            "FRC",
            "TMP",
            "MAP",
        ):
            intensity = 90.0  # high-intensity proxy

        veto_result = check_pre_session_veto(
            wellness_data=wellness,
            athlete_profile=profile.model_dump(),
            session_intensity=intensity,
        )

        # 8. Build verdict
        if veto_result["veto"]:
            verdict = "VETO"
        elif veto_result["risk_level"] in ("high", "medium"):
            verdict = "CAUTION"
        else:
            verdict = "GO"

        result = {
            "date": date_str,
            "verdict": verdict,
            "risk_level": veto_result["risk_level"],
            "veto": veto_result["veto"],
            "factors": veto_result["factors"],
            "recommendation": veto_result["recommendation"],
            "wellness": wellness,
            "wellness_source": wellness_source,
            "override": {
                "extra_sleep_hours": extra_sleep_hours,
                "applied": extra_sleep_hours > 0,
            },
        }

        if session_info:
            result["session"] = session_info
        else:
            result["session"] = None
            result["session_note"] = (
                "No planned session found for this date"
                if week_id
                else "Could not auto-detect week_id — provide week_id parameter"
            )

        if readiness_data:
            result["readiness"] = readiness_data

    return mcp_response(result)
