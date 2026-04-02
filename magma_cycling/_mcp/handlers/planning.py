"""Planning tool handlers."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from magma_cycling._mcp._utils import (
    compute_start_time,
    load_workout_descriptions,
    mcp_response,
    suppress_stdout_stderr,
)

if TYPE_CHECKING:
    from mcp.types import TextContent

logger = logging.getLogger(__name__)

__all__ = [
    "handle_weekly_planner",
    "handle_monthly_analysis",
    "handle_daily_sync",
    "handle_update_session",
    "handle_list_weeks",
    "handle_get_metrics",
    "handle_get_week_details",
    "handle_modify_session_details",
    "handle_rename_session",
    "handle_create_session",
    "handle_delete_session",
]


def _parse_ai_workouts(raw_text: str, start_date: date) -> list[dict]:
    """Parse AI response into structured workout dicts.

    Args:
        raw_text: Raw AI response containing delimited workouts.
        start_date: Week start date (Monday) for computing session dates.

    Returns:
        List of dicts compatible with save_planning_json() format.
    """
    from magma_cycling.planning.models import WORKOUT_NAME_REGEX

    pattern = r"=== WORKOUT (.*?) ===\n(.*?)\n=== FIN WORKOUT ==="
    matches = re.findall(pattern, raw_text, re.DOTALL)

    workouts = []
    for workout_name, workout_content in matches:
        workout_name = workout_name.strip()

        # Parse structured name: S083-01-END-EnduranceDouce-V001
        name_match = WORKOUT_NAME_REGEX.match(workout_name)
        if not name_match:
            logger.warning(f"_parse_ai_workouts: skipping malformed name: {workout_name}")
            continue

        session_id = name_match.group(1)
        session_type = name_match.group(2)
        name = name_match.group(3)
        version = name_match.group(4)

        # Extract day number from session_id (e.g., S083-01 → 1)
        day_match = re.search(r"-(\d{2})", session_id)
        day_num = int(day_match.group(1)) if day_match else 1
        session_date = start_date + timedelta(days=day_num - 1)

        # Parse TSS and duration from content
        tss = 0
        duration = 0
        content_stripped = workout_content.strip()
        first_line = content_stripped.split("\n")[0] if content_stripped else ""

        # Pattern: "Endurance Base (60min, 45 TSS)" or "60 min" or "45 TSS"
        tss_match = re.search(r"(\d+)\s*TSS", first_line, re.IGNORECASE)
        if tss_match:
            tss = int(tss_match.group(1))
        dur_match = re.search(r"(\d+)\s*min", first_line, re.IGNORECASE)
        if dur_match:
            duration = int(dur_match.group(1))

        # Recalculate from blocks (source of truth)
        from magma_cycling.workout_parser import calculate_workout_duration

        calculated = calculate_workout_duration(content_stripped)
        if calculated is not None:
            duration = calculated

        workouts.append(
            {
                "session_id": session_id,
                "date": session_date.strftime("%Y-%m-%d"),
                "name": name,
                "type": session_type,
                "version": version,
                "tss_planned": tss,
                "duration_min": duration,
                "description": content_stripped,
                "status": "planned",
            }
        )

    return workouts


def _call_ai_provider(prompt: str, current_metrics: dict) -> str:
    """Call AI provider for weekly planning.

    Args:
        prompt: Full planning prompt to send.
        current_metrics: Current athlete metrics for system prompt.

    Returns:
        Raw AI response text.
    """
    from magma_cycling.ai_providers.factory import AIProviderFactory
    from magma_cycling.prompts.prompt_builder import build_prompt

    system_prompt, _ = build_prompt(
        mission="weekly_planning",
        current_metrics=current_metrics,
        workflow_data="",
    )

    analyzer = AIProviderFactory.create("mcp_direct", {})
    return analyzer.analyze_session(prompt, system_prompt=system_prompt)


async def handle_weekly_planner(args: dict) -> list[TextContent]:
    """Generate weekly training plan."""
    from magma_cycling.weekly_planner import WeeklyPlanner

    week_id = args["week_id"]
    start_date_str = args["start_date"]
    provider = args.get("provider", "clipboard")
    force = args.get("force", False)

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()

    # Suppress all output to prevent JSON protocol pollution
    with suppress_stdout_stderr():
        planner = WeeklyPlanner(week_number=week_id, start_date=start_date, project_root=Path.cwd())

    # --- Guard: reject overwrite unless force=True ---
    existing_file = planner.planning_dir / f"week_planning_{week_id}.json"
    if existing_file.exists():
        if not force:
            return mcp_response(
                {
                    "error": "planning_exists",
                    "week_id": week_id,
                    "existing_file": str(existing_file),
                    "message": (
                        f"Planning {week_id} already exists. "
                        "Use force=true to overwrite (a backup will be created first)."
                    ),
                }
            )
        # force=True → backup before overwrite
        from magma_cycling.planning.control_tower import planning_tower

        with suppress_stdout_stderr():
            planning_tower.backup_system.backup_week_files(week_id)
        logger.info("Backup created for %s before forced overwrite", week_id)

    # Collect metrics
    with suppress_stdout_stderr():
        planner.current_metrics = planner.collect_current_metrics()
        planner.previous_week_bilan = planner.load_previous_week_bilan()
        planner.context_files = planner.load_context_files()

        # Generate prompt
        prompt = planner.generate_planning_prompt()

    result = {
        "week_id": week_id,
        "start_date": start_date_str,
        "status": "prompt_generated",
        "provider": provider,
        "prompt_length": len(prompt),
        "message": f"Planning prompt generated for {week_id}",
    }

    if provider == "mcp_direct":
        try:
            # 1. Call AI provider
            with suppress_stdout_stderr():
                raw_response = _call_ai_provider(prompt, planner.current_metrics)

            # 2. Save raw text to {week_id}_workouts.txt (with backup)
            from magma_cycling.planning.backup import safe_write

            workouts_file = planner.planning_dir / f"{week_id}_workouts.txt"
            safe_write(workouts_file, raw_response)

            # 3. Parse workouts
            workouts_data = _parse_ai_workouts(raw_response, start_date)

            if not workouts_data:
                # Fallback: return prompt for manual consumption
                result["status"] = "ai_parse_failed"
                result["prompt"] = prompt
                result["raw_response"] = raw_response[:2000]
                result["message"] = "AI responded but no workouts could be parsed"
            else:
                # 4. Save planning JSON via Control Tower
                with suppress_stdout_stderr():
                    planner.save_planning_json(workouts_data)

                result["status"] = "plan_generated"
                result["sessions_count"] = len(workouts_data)
                result["sessions"] = [
                    {
                        "session_id": w["session_id"],
                        "name": w["name"],
                        "type": w["type"],
                        "tss": w["tss_planned"],
                    }
                    for w in workouts_data
                ]
                result["workouts_file"] = str(workouts_file)
                result["message"] = f"Generated {len(workouts_data)}/7 sessions for {week_id}"
                if len(workouts_data) < 7:
                    result["warnings"] = [f"Only {len(workouts_data)}/7 workouts parsed"]

        except Exception as exc:
            logger.exception("mcp_direct: AI call failed")
            # Graceful fallback: return raw prompt
            result["status"] = "ai_error"
            result["error"] = str(exc)
            result["prompt"] = prompt
            result["message"] = f"AI call failed, prompt returned for manual use: {exc}"

    elif provider == "prompt_only":
        # Return full prompt for direct consumption by the MCP client (e.g., Claude).
        # No external API call — the AI client reads the prompt from the tool result,
        # generates 7 workouts, and writes them via modify-session-details.

        # Create skeleton planning JSON with 7 empty sessions so that
        # modify-session-details can find the file and update sessions.
        with suppress_stdout_stderr():
            planning_file = planner.save_planning_json(None)

        result["status"] = "prompt_ready"
        result["prompt"] = prompt
        result["planning_file"] = str(planning_file)
        result["sessions"] = [
            {"session_id": f"{week_id}-{d + 1:02d}", "status": "planned"} for d in range(7)
        ]
        result["next_steps"] = [
            "Read the prompt above and generate 7 structured workouts",
            f"Call modify-session-details for each session ({week_id}-01 to {week_id}-07)",
            "Call sync-week-to-calendar to upload to training calendar",
        ]

    elif provider == "clipboard":
        try:
            subprocess.run(["pbcopy"], input=prompt.encode("utf-8"), check=True)
            result["status"] = "copied_to_clipboard"
            result["message"] = f"Prompt ({len(prompt):,} chars) copied to clipboard for {week_id}"
        except Exception as e:
            result["status"] = "clipboard_error"
            result["message"] = f"Failed to copy to clipboard: {e}"
            result["prompt"] = prompt  # Fallback: return full prompt

        result["next_steps"] = [
            "Paste prompt into your AI provider (Cmd+V)",
            "Generate 7 workouts with === WORKOUT ... === delimiters",
            f"Save to {week_id}_workouts.txt",
            "Run upload-workouts to sync to training calendar",
        ]
    else:
        # Full prompt for AI providers — any MCP client can consume it
        result["prompt"] = prompt
        result["next_steps"] = [
            "Use the prompt field to generate 7 structured workouts",
            "Call modify-session-details for each session with the workout description",
            "Call sync-week-to-calendar to upload to training calendar",
        ]

    return mcp_response(result)


async def handle_monthly_analysis(args: dict) -> list[TextContent]:
    """Generate monthly training analysis."""
    from magma_cycling.monthly_analysis import MonthlyAnalyzer

    month = args["month"]
    provider = args.get("provider", "mistral_api")
    no_ai = args.get("no_ai", False)

    # Suppress all output to prevent JSON protocol pollution
    with suppress_stdout_stderr():
        analyzer = MonthlyAnalyzer(month=month, provider=provider, no_ai=no_ai)
        report = analyzer.run()

    if not report:
        error = {"error": f"No planning data found for {month}"}
        return mcp_response(error)

    # Extract key metrics from report
    result = {
        "month": month,
        "report_length": len(report),
        "report": report,
    }

    return mcp_response(result)


async def handle_daily_sync(args: dict) -> list[TextContent]:
    """Sync with training platform (full pipeline: check, AI analysis, report)."""
    from magma_cycling.daily_sync import DailySync, calculate_current_week_info

    check_date_str = args.get("date")
    enable_ai = args.get("ai_analysis", True)

    if check_date_str:
        check_date = datetime.strptime(check_date_str, "%Y-%m-%d").date()
    else:
        check_date = date.today()

    # Auto-calculate week_id and start_date
    week_id = args.get("week_id")
    with suppress_stdout_stderr():
        calculated_week_id, calculated_start_date = calculate_current_week_info(check_date)
    if not week_id:
        week_id = calculated_week_id
    start_date = calculated_start_date

    # Setup paths
    from magma_cycling.config import get_data_config

    config = get_data_config()
    tracking_file = config.data_repo_path / "activities_tracking.json"
    reports_dir = config.data_repo_path / "daily-reports"

    # DailySync init may print AI provider info — suppress it
    with suppress_stdout_stderr():
        sync = DailySync(
            tracking_file=tracking_file,
            reports_dir=reports_dir,
            enable_ai_analysis=enable_ai,
            enable_auto_servo=False,
            verbose=False,
        )

    # Run full sync pipeline (check, AI analysis, update sessions, report)
    with suppress_stdout_stderr():
        sync.run(
            check_date=check_date,
            week_id=week_id,
            start_date=start_date,
        )

    # Re-read completed activities for response building (lightweight API GET)
    with suppress_stdout_stderr():
        _, completed_activities = sync.check_activities(check_date)
        activity_to_session_map = {}
        if completed_activities:
            activity_to_session_map = sync.update_completed_sessions(completed_activities)

    # Enrich result with activity details
    activities_details = []
    if completed_activities:
        for activity in completed_activities:
            if activity is None:
                continue
            activity_id = activity.get("id")
            activity_detail = {
                "activity_id": activity_id,
                "name": activity.get("name"),
                "type": activity.get("type"),
                "start_time": activity.get("start_date_local"),
                "tss": activity.get("icu_training_load"),
                "intensity_factor": activity.get("icu_intensity"),
                "duration_min": (
                    round(activity.get("moving_time", 0) / 60)
                    if activity.get("moving_time")
                    else None
                ),
                "distance_km": (
                    round(activity.get("distance", 0) / 1000, 1)
                    if activity.get("distance")
                    else None
                ),
                "average_watts": activity.get("average_watts"),
                "session_id": activity_to_session_map.get(activity_id),
            }
            activities_details.append(activity_detail)

    # Report file path
    report_file = reports_dir / f"daily_report_{check_date.isoformat()}.md"

    # AI provider info
    ai_provider = None
    if enable_ai and sync.ai_analyzer:
        ai_provider = type(sync.ai_analyzer).__name__

    result = {
        "date": check_date.isoformat(),
        "week_id": week_id,
        "completed_activities": len(completed_activities) if completed_activities else 0,
        "activities": activities_details,
        "ai_analysis": enable_ai and sync.ai_analyzer is not None,
        "ai_provider": ai_provider,
        "report_file": str(report_file) if report_file.exists() else None,
        "status": "completed",
        "message": f"Sync completed for {check_date.isoformat()}",
    }

    return mcp_response(result)


async def handle_update_session(args: dict) -> list[TextContent]:
    """Update session status."""
    from magma_cycling.config import create_intervals_client
    from magma_cycling.planning.control_tower import planning_tower

    week_id = args["week_id"]
    session_id = args["session_id"]
    new_status = args["status"]
    reason = args.get("reason")
    sync_to_intervals = args.get("sync", False)

    # Track if we found session and its old status
    session_found = False
    old_status = None
    intervals_id = None
    session_date = None
    session_name = None
    session_type = None
    session_version = None
    session_description = None
    session_tss = None
    session_duration = None

    # Suppress all output to prevent JSON protocol pollution
    with suppress_stdout_stderr():
        # Update via Control Tower
        with planning_tower.modify_week(
            week_id,
            requesting_script="mcp-server",
            reason=f"MCP: Update {session_id} to {new_status}: {reason or 'N/A'}",
        ) as plan:
            for session in plan.planned_sessions:
                if session.session_id == session_id:
                    old_status = session.status
                    intervals_id = session.intervals_id
                    session_date = session.session_date
                    session_name = session.name
                    session_type = session.session_type
                    session_version = session.version
                    session_description = session.description
                    session_tss = session.tss_planned
                    session_duration = session.duration_min

                    # PROTECTION: Never modify completed sessions in Intervals.icu
                    if sync_to_intervals and old_status == "completed":
                        raise ValueError(
                            f"Cannot sync session {session_id}: "
                            f"Status is 'completed'. Refusing to modify completed sessions."
                        )

                    # Set skip_reason BEFORE status (Pydantic validator)
                    if reason and new_status in ("skipped", "cancelled", "replaced"):
                        session.skip_reason = reason

                    session.status = new_status
                    session_found = True
                    break

            if not session_found:
                raise ValueError(f"Session {session_id} not found in {week_id}")

        # Sync to Intervals.icu if requested
        sync_result = None
        if sync_to_intervals and session_found:
            try:
                client = create_intervals_client()

                if new_status in ("skipped", "cancelled", "replaced", "modified"):
                    # Delegate to CLI sync function which handles
                    # NOTE conversion (skipped/cancelled/replaced)
                    # and description update (modified) correctly.
                    # print() calls are captured by suppress_stdout_stderr().
                    from magma_cycling.update_session_status import (
                        sync_with_intervals,
                    )

                    session_info = {
                        "name": session_name,
                        "type": session_type,
                        "version": session_version,
                        "description": session_description,
                        "tss_planned": session_tss,
                        "duration_min": session_duration,
                    }

                    sync_ok = sync_with_intervals(
                        client=client,
                        session_id=session_id,
                        session_date=str(session_date),
                        new_status=new_status,
                        reason=reason,
                        session_info=session_info,
                    )

                    status_label = {
                        "skipped": "SAUTÉE",
                        "cancelled": "ANNULÉE",
                        "replaced": "REMPLACÉE",
                        "modified": "modified",
                    }.get(new_status, new_status)

                    if sync_ok:
                        sync_result = (
                            f"Converted Intervals.icu event to NOTE "
                            f"[{status_label}] for {session_id}"
                        )
                    else:
                        sync_result = f"Failed to convert Intervals.icu event " f"for {session_id}"

                else:
                    # For planned/uploaded/pending: WORKOUT create/update
                    start_time = compute_start_time(session_date, session_id)
                    intervals_name = (
                        f"{session_id}-{session_type}-" f"{session_name}-{session_version}"
                    )

                    # Load full workout description from {week_id}_workouts.txt
                    # Fallback to short session_description if not found
                    full_descriptions = load_workout_descriptions(week_id)
                    full_desc = full_descriptions.get(intervals_name, session_description)

                    event_data = {
                        "category": "WORKOUT",
                        "type": "VirtualRide",
                        "name": intervals_name,
                        "description": full_desc,
                        "start_date_local": f"{session_date}T{start_time}",
                    }

                    if intervals_id:
                        client.update_event(intervals_id, event_data)
                        sync_result = f"Updated Intervals.icu event {intervals_id}"
                    else:
                        created = client.create_event(event_data)
                        if created and "id" in created:
                            new_intervals_id = created["id"]
                            with planning_tower.modify_week(
                                week_id,
                                requesting_script="mcp-server",
                                reason=(
                                    f"MCP: Save Intervals.icu ID "
                                    f"{new_intervals_id} for {session_id}"
                                ),
                            ) as plan:
                                for session in plan.planned_sessions:
                                    if session.session_id == session_id:
                                        session.intervals_id = new_intervals_id
                                        break
                            sync_result = f"Created Intervals.icu event {new_intervals_id}"
                        else:
                            sync_result = "Failed to create Intervals.icu event"

            except Exception as e:
                sync_result = f"Sync error: {str(e)}"

    result = {
        "week_id": week_id,
        "session_id": session_id,
        "status": new_status,
        "reason": reason,
        "message": f"Session {session_id} updated to {new_status}",
        "synced": sync_to_intervals,
        "sync_result": sync_result if sync_to_intervals else None,
    }

    return mcp_response(result)


async def handle_list_weeks(args: dict) -> list[TextContent]:
    """List available weekly plannings."""
    from magma_cycling.config import get_data_config

    config = get_data_config()
    planning_dir = config.week_planning_dir

    limit = args.get("limit", 10)
    recent = args.get("recent", True)

    planning_files = sorted(planning_dir.glob("week_planning_S*.json"))

    if recent:
        planning_files = planning_files[::-1]

    weeks = []
    for planning_file in planning_files[:limit]:
        try:
            with open(planning_file, encoding="utf-8") as f:
                data = json.load(f)

            weeks.append(
                {
                    "week_id": data.get("week_id"),
                    "start_date": data.get("start_date"),
                    "end_date": data.get("end_date"),
                    "tss_target": data.get("tss_target", 0),
                    "sessions": len(data.get("planned_sessions", [])),
                }
            )
        except Exception:
            continue

    result = {
        "total_found": len(weeks),
        "showing": min(limit, len(weeks)),
        "weeks": weeks,
    }

    return mcp_response(result)


async def handle_get_metrics(args: dict) -> list[TextContent]:
    """Get current training metrics."""
    from magma_cycling.api.intervals_client import IntervalsClient
    from magma_cycling.config import get_intervals_config

    config = get_intervals_config()
    client = IntervalsClient(athlete_id=config.athlete_id, api_key=config.api_key)

    # Get latest wellness data
    today = date.today()
    oldest = (today - timedelta(days=7)).isoformat()
    newest = today.isoformat()

    wellness_data = client.get_wellness(oldest=oldest, newest=newest)

    if wellness_data:
        latest = wellness_data[-1]  # Most recent
        result = {
            "date": latest.get("id"),
            "ctl": latest.get("ctl"),
            "atl": latest.get("atl"),
            "tsb": latest.get("tsb"),
            "rampRate": latest.get("rampRate"),
            "ctlLoad": latest.get("ctlLoad"),
            "atlLoad": latest.get("atlLoad"),
        }
    else:
        result = {"error": "No wellness data found"}

    return mcp_response(result)


async def handle_get_week_details(args: dict) -> list[TextContent]:
    """Get detailed information about a specific week planning."""
    from magma_cycling.planning.control_tower import planning_tower

    week_id = args["week_id"]

    try:
        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            # Read planning via Control Tower
            plan = planning_tower.read_week(week_id)

        # Convert to dict for JSON serialization
        result = {
            "week_id": plan.week_id,
            "start_date": str(plan.start_date),
            "end_date": str(plan.end_date),
            "athlete_id": plan.athlete_id,
            "tss_target": plan.tss_target,
            "created_at": str(plan.created_at),
            "last_updated": str(plan.last_updated),
            "version": plan.version,
            "sessions": [
                {
                    "session_id": session.session_id,
                    "date": str(session.session_date),
                    "name": session.name,
                    "type": session.session_type,
                    "version": session.version,
                    "tss_planned": session.tss_planned,
                    "duration_min": session.duration_min,
                    "description": session.description,
                    "status": session.status,
                    "intervals_id": session.intervals_id,
                    "skip_reason": session.skip_reason,
                }
                for session in plan.planned_sessions
            ],
        }

        return mcp_response(result)

    except FileNotFoundError:
        error = {"error": f"Planning file not found for week {week_id}"}
        return mcp_response(error)
    except Exception as e:
        error = {"error": f"Error reading planning: {str(e)}"}
        return mcp_response(error)


async def handle_modify_session_details(args: dict) -> list[TextContent]:
    """Modify detailed information of a training session."""
    from magma_cycling.planning.control_tower import planning_tower

    week_id = args["week_id"]
    session_id = args["session_id"]

    # Extract optional fields
    name = args.get("name")
    session_type = args.get("type")
    description = args.get("description")
    tss_planned = args.get("tss_planned")
    duration_min = args.get("duration_min")

    # Build modification summary
    modifications = []
    if name:
        modifications.append(f"name={name}")
    if session_type:
        modifications.append(f"type={session_type}")
    if description:
        modifications.append("description updated")
    if tss_planned is not None:
        modifications.append(f"TSS={tss_planned}")
    if duration_min is not None:
        modifications.append(f"duration={duration_min}min")

    modification_summary = ", ".join(modifications) if modifications else "no changes"

    try:
        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            # Modify via Control Tower
            with planning_tower.modify_week(
                week_id,
                requesting_script="mcp-server",
                reason=f"MCP: Modify {session_id} details - {modification_summary}",
            ) as plan:
                session_found = False
                for session in plan.planned_sessions:
                    if session.session_id == session_id:
                        # PROTECTION: Refuse to modify completed sessions
                        if session.status == "completed":
                            raise ValueError(
                                f"⛔ PROTECTION: Cannot modify session {session_id} - "
                                f"Status is 'completed'. Completed sessions are protected from modification."
                            )

                        # Update fields if provided
                        if name:
                            session.name = name
                        if session_type:
                            session.session_type = session_type
                        if description:
                            session.description = description
                            # Auto-recalculate duration from blocks if not explicitly provided
                            if duration_min is None:
                                from magma_cycling.workout_parser import (
                                    calculate_workout_duration,
                                )

                                calculated = calculate_workout_duration(description)
                                if calculated is not None:
                                    session.duration_min = calculated
                                    modifications.append(f"duration={calculated}min (auto)")
                        if tss_planned is not None:
                            session.tss_planned = tss_planned
                        if duration_min is not None:
                            session.duration_min = duration_min

                        session_found = True
                        break

                if not session_found:
                    raise ValueError(f"Session {session_id} not found in {week_id}")

        result = {
            "status": "success",
            "week_id": week_id,
            "session_id": session_id,
            "modifications": modifications,
            "message": f"Session {session_id} updated successfully",
        }

        return mcp_response(result)

    except FileNotFoundError:
        error = {"error": f"Planning file not found for week {week_id}"}
        return mcp_response(error)
    except ValueError as e:
        error = {"error": str(e)}
        return mcp_response(error)
    except Exception as e:
        error = {"error": f"Error modifying session: {str(e)}"}
        return mcp_response(error)


async def handle_rename_session(args: dict) -> list[TextContent]:
    """Rename a session_id within a weekly plan."""
    from magma_cycling.config import create_intervals_client
    from magma_cycling.planning.control_tower import planning_tower
    from magma_cycling.planning.models import SESSION_ID_REGEX

    week_id = args["week_id"]
    session_id = args["session_id"]
    new_session_id = args["new_session_id"]
    sync_remote = args.get("sync_remote", True)

    # Validate format
    if not SESSION_ID_REGEX.match(new_session_id):
        error = {
            "error": f"Invalid session_id format: '{new_session_id}'. " f"Expected: S###-##[a-z]"
        }
        return mcp_response(error)

    # Validate same week
    new_week = new_session_id.split("-")[0]
    if new_week != week_id:
        error = {
            "error": f"Cannot rename across weeks: "
            f"{session_id} ({week_id}) → {new_session_id} ({new_week})"
        }
        return mcp_response(error)

    remote_updated = False
    old_intervals_name = None
    new_intervals_name = None
    intervals_id = None
    session_date = None

    try:
        with suppress_stdout_stderr():
            with planning_tower.modify_week(
                week_id,
                requesting_script="mcp-server",
                reason=f"MCP: Rename {session_id} → {new_session_id}",
            ) as plan:
                # Find session
                session = None
                for s in plan.planned_sessions:
                    if s.session_id == session_id:
                        session = s
                        break
                if not session:
                    raise ValueError(f"Session {session_id} not found in {week_id}")

                # Protect completed sessions
                if session.status == "completed":
                    raise ValueError(
                        f"⛔ PROTECTION: Cannot rename {session_id} — " f"status is 'completed'"
                    )

                # Check uniqueness
                for s in plan.planned_sessions:
                    if s.session_id == new_session_id:
                        raise ValueError(f"Session {new_session_id} already exists in {week_id}")

                # Build intervals names for reference
                old_intervals_name = (
                    f"{session_id}-{session.session_type}-" f"{session.name}-{session.version}"
                )

                # Rename
                session.session_id = new_session_id

                new_intervals_name = (
                    f"{new_session_id}-{session.session_type}-" f"{session.name}-{session.version}"
                )
                intervals_id = session.intervals_id
                session_date = session.session_date

        # Sync remote if needed (outside modify_week to avoid long lock)
        if sync_remote and intervals_id:
            try:
                client = create_intervals_client()
                new_start_time = compute_start_time(session_date, new_session_id)
                client.update_event(
                    intervals_id,
                    {
                        "name": new_intervals_name,
                        "start_date_local": f"{session_date}T{new_start_time}",
                    },
                )
                remote_updated = True
            except Exception as e:
                partial = {
                    "status": "partial",
                    "message": f"Session renamed locally but remote update failed: {e}",
                    "week_id": week_id,
                    "old_session_id": session_id,
                    "new_session_id": new_session_id,
                }
                return mcp_response(partial)

        result = {
            "status": "success",
            "week_id": week_id,
            "old_session_id": session_id,
            "new_session_id": new_session_id,
            "old_intervals_name": old_intervals_name,
            "new_intervals_name": new_intervals_name,
            "remote_updated": remote_updated,
            "intervals_id": intervals_id,
        }
        return mcp_response(result)

    except FileNotFoundError:
        error = {"error": f"Planning file not found for week {week_id}"}
        return mcp_response(error)
    except ValueError as e:
        error = {"error": str(e)}
        return mcp_response(error)
    except Exception as e:
        error = {"error": f"Error renaming session: {str(e)}"}
        return mcp_response(error)


async def handle_create_session(args: dict) -> list[TextContent]:
    """Create a new training session."""
    from datetime import datetime

    from magma_cycling.planning.control_tower import planning_tower
    from magma_cycling.planning.models import Session

    week_id = args["week_id"]
    session_date_str = args["session_date"]
    session_date = datetime.strptime(session_date_str, "%Y-%m-%d").date()

    # Extract optional fields with defaults
    name = args.get("name", "NewSession")
    session_type = args.get("type", "END")
    description = args.get("description", "À définir")
    tss_planned = args.get("tss_planned", 0)
    duration_min = args.get("duration_min", 0)

    try:
        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            # Modify via Control Tower
            with planning_tower.modify_week(
                week_id,
                requesting_script="mcp-server",
                reason=f"MCP: Create new session on {session_date_str} - {name}",
            ) as plan:
                # Generate session_id
                # Find day of week (Monday=0, Sunday=6)
                day_num = session_date.weekday()
                day_index = day_num + 1  # Convert to 1-based (Monday=1, Sunday=7)

                # Find existing sessions on this date
                existing_sessions = [
                    s for s in plan.planned_sessions if s.session_date == session_date
                ]

                if not existing_sessions:
                    # First session for this day
                    session_id = f"{week_id}-{day_index:02d}"
                else:
                    # Multiple sessions - add letter suffix
                    # Find next available letter (a, b, c, etc.)
                    existing_suffixes = []
                    for s in existing_sessions:
                        # Extract suffix from session_id (e.g., "S081-06a" -> "a")
                        if len(s.session_id.split("-")[1]) > 2:
                            suffix = s.session_id.split("-")[1][2]
                            existing_suffixes.append(suffix)

                    if not existing_suffixes:
                        # First session has no suffix, second gets 'a'
                        session_id = f"{week_id}-{day_index:02d}a"
                    else:
                        # Find next letter
                        next_letter = chr(ord(max(existing_suffixes)) + 1)
                        session_id = f"{week_id}-{day_index:02d}{next_letter}"

                # Create new session
                new_session = Session(
                    session_id=session_id,
                    date=session_date,
                    name=name,
                    type=session_type,
                    version="V001",
                    tss_planned=tss_planned,
                    duration_min=duration_min,
                    description=description,
                    status="planned",
                )

                # Add to plan (insert in chronological order)
                plan.planned_sessions.append(new_session)
                plan.planned_sessions.sort(key=lambda s: (s.session_date, s.session_id))

        result = {
            "status": "success",
            "week_id": week_id,
            "session_id": session_id,
            "session_date": session_date_str,
            "name": name,
            "type": session_type,
            "message": f"Session {session_id} created successfully",
        }

        return mcp_response(result)

    except FileNotFoundError:
        error = {"error": f"Planning file not found for week {week_id}"}
        return mcp_response(error)
    except Exception as e:
        error = {"error": f"Error creating session: {str(e)}"}
        return mcp_response(error)


async def handle_delete_session(args: dict) -> list[TextContent]:
    """Delete a training session."""
    from magma_cycling.planning.control_tower import planning_tower

    week_id = args["week_id"]
    session_id = args["session_id"]

    try:
        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            # Modify via Control Tower
            with planning_tower.modify_week(
                week_id,
                requesting_script="mcp-server",
                reason=f"MCP: Delete session {session_id}",
            ) as plan:
                # Find and remove session
                session_found = False
                for i, session in enumerate(plan.planned_sessions):
                    if session.session_id == session_id:
                        # PROTECTION 1: Refuse to delete completed sessions
                        if session.status == "completed":
                            raise ValueError(
                                f"⛔ PROTECTION: Cannot delete session {session_id} - "
                                f"Status is 'completed'. Completed sessions are protected from deletion."
                            )

                        # PROTECTION 2: Warn about deleting synced sessions
                        if session.intervals_id:
                            raise ValueError(
                                f"⛔ PROTECTION: Cannot delete session {session_id} - "
                                f"Has intervals_id={session.intervals_id}. "
                                f"Session is synced with Intervals.icu. "
                                f"Delete from Intervals.icu first or use force parameter."
                            )

                        plan.planned_sessions.pop(i)
                        session_found = True
                        break

                if not session_found:
                    raise ValueError(f"Session {session_id} not found in {week_id}")

        result = {
            "status": "success",
            "week_id": week_id,
            "session_id": session_id,
            "message": f"Session {session_id} deleted successfully",
        }

        return mcp_response(result)

    except FileNotFoundError:
        error = {"error": f"Planning file not found for week {week_id}"}
        return mcp_response(error)
    except ValueError as e:
        error = {"error": str(e)}
        return mcp_response(error)
    except Exception as e:
        error = {"error": f"Error deleting session: {str(e)}"}
        return mcp_response(error)
