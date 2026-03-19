"""Rest and recovery handlers — pre-session safety gate."""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import TYPE_CHECKING

from magma_cycling._mcp._utils import mcp_response, suppress_stdout_stderr

if TYPE_CHECKING:
    from mcp.types import TextContent

__all__ = ["handle_pre_session_check", "handle_patch_coach_analysis"]

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


def _locate_entry(
    content: str, activity_id: str | None, session_id: str | None
) -> tuple[int, int] | None:
    """Locate a coach analysis entry in workouts-history.md.

    Returns (start, end) character offsets or None if not found.
    """
    anchor_pos = None

    # Priority: activity_id
    if activity_id:
        m = re.search(rf"^ID\s*:\s*{re.escape(activity_id)}\s*$", content, re.MULTILINE)
        if m:
            anchor_pos = m.start()

    # Fallback: session_id
    if anchor_pos is None and session_id:
        m = re.search(rf"^### {re.escape(session_id)}-", content, re.MULTILINE)
        if m:
            anchor_pos = m.start()

    if anchor_pos is None:
        return None

    # Walk back to the ### header containing this anchor
    header_start = content.rfind("\n### ", 0, anchor_pos)
    if header_start == -1:
        # Entry is at the very start of the file
        header_start = 0
    else:
        header_start += 1  # skip the leading newline

    # Find the next ### header (end of this entry)
    next_header = content.find("\n### ", anchor_pos)
    if next_header == -1:
        entry_end = len(content)
    else:
        entry_end = next_header

    return header_start, entry_end


async def handle_patch_coach_analysis(args: dict) -> list[TextContent]:
    """Patch a coach analysis entry in workouts-history.md."""
    with suppress_stdout_stderr():
        from magma_cycling.config import get_data_config

        activity_id = args.get("activity_id")
        session_id = args.get("session_id")
        sleep_hours = args.get("sleep_hours")
        note = args.get("note")

        if not activity_id and not session_id:
            raise ValueError("activity_id or session_id is required")

        if sleep_hours is None and not note:
            raise ValueError("At least one patch field (sleep_hours or note) is required")

        # Load file
        config = get_data_config()
        history_path = config.workouts_history_path
        content = history_path.read_text(encoding="utf-8")

        # Locate entry
        bounds = _locate_entry(content, activity_id, session_id)
        if bounds is None:
            lookup = activity_id or session_id
            return mcp_response(
                {
                    "status": "error",
                    "message": f"Entry not found for {lookup} in workouts-history.md",
                }
            )

        start, end = bounds
        block = content[start:end]
        patches_applied = []

        # Extract identifiers from the entry
        found_activity_id = activity_id
        found_session_id = session_id
        id_match = re.search(r"^ID\s*:\s*(\S+)", block, re.MULTILINE)
        if id_match:
            found_activity_id = id_match.group(1)
        header_match = re.match(r"^### (\S+)", block)
        if header_match:
            found_session_id = header_match.group(1)

        # Patch sleep_hours
        if sleep_hours is not None:
            sleep_re = re.compile(r"^(- Sommeil\s*:\s*)([\d.]+)(h.*)$", re.MULTILINE)
            m = sleep_re.search(block)
            if m:
                old_value = m.group(2)
                new_value = str(sleep_hours)
                marker = " [CORRIGÉ : sommeil canapé non détecté par Sleep Analyser]"

                # Replace in Métriques Pré-séance line
                block = sleep_re.sub(
                    rf"\g<1>{new_value}h{marker}",
                    block,
                    count=1,
                )

                # Replace old_value occurrences in Points d'Attention section
                attention_re = re.compile(
                    r"(#### Points d'Attention.*?)(?=####|\Z)",
                    re.DOTALL,
                )
                att_match = attention_re.search(block)
                if att_match:
                    att_section = att_match.group(0)
                    patched_att = att_section.replace(f"{old_value}h", f"{new_value}h")
                    block = block[: att_match.start()] + patched_att + block[att_match.end() :]

                patches_applied.append(
                    {
                        "field": "sleep_hours",
                        "old_value": float(old_value),
                        "new_value": sleep_hours,
                    }
                )
            else:
                patches_applied.append(
                    {
                        "field": "sleep_hours",
                        "warning": "Ligne 'Sommeil' non trouvée dans l'entrée",
                    }
                )

        # Patch note
        if note:
            correction_section = (
                f"\n#### Note de correction\n"
                f"{note}\n"
                f"*Patch appliqué le {date.today().isoformat()}*\n"
            )
            block = block.rstrip("\n") + "\n" + correction_section
            patches_applied.append({"field": "note", "added": True})

        # Rewrite file
        new_content = content[:start] + block + content[end:]
        history_path.write_text(new_content, encoding="utf-8")

    return mcp_response(
        {
            "status": "success",
            "activity_id": found_activity_id,
            "session_id": found_session_id,
            "patches_applied": patches_applied,
        }
    )
