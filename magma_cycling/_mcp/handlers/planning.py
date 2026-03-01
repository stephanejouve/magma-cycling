"""Planning tool handlers."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from magma_cycling._mcp._utils import compute_start_time, mcp_response, suppress_stdout_stderr

if TYPE_CHECKING:
    from mcp.types import TextContent

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


async def handle_weekly_planner(args: dict) -> list[TextContent]:
    """Generate weekly training plan."""
    from magma_cycling.weekly_planner import WeeklyPlanner

    week_id = args["week_id"]
    start_date_str = args["start_date"]
    provider = args.get("provider", "clipboard")

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()

    # Suppress all output to prevent JSON protocol pollution
    with suppress_stdout_stderr():
        planner = WeeklyPlanner(week_number=week_id, start_date=start_date, project_root=Path.cwd())

        # Collect metrics
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
        "next_steps": [
            f"Copy prompt and paste to {provider}",
            "Generate 7 workouts",
            "Save workouts to file",
            "Run upload-workouts to sync to Intervals.icu",
        ],
    }

    if provider == "clipboard":
        result["prompt"] = prompt[:500] + "..." if len(prompt) > 500 else prompt

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
    """Sync with Intervals.icu (full pipeline: check, AI analysis, report)."""
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

                # Prepare event data
                # Determine start time based on day and session suffix
                day_of_week = session_date.weekday()  # 0=Monday, 5=Saturday
                session_day_part = session_id.split("-")[-1]  # e.g., "04" or "06a"

                # Check if session has letter suffix (double session)
                session_suffix = session_day_part[-1] if session_day_part[-1].isalpha() else None

                # Double session (a/b)
                if session_suffix == "a":
                    start_time = "09:00:00"  # Morning
                elif session_suffix == "b":
                    start_time = "15:00:00"  # Afternoon
                else:
                    # Saturday → 09:00, other days → 17:00
                    start_time = "09:00:00" if day_of_week == 5 else "17:00:00"

                # Build Intervals.icu event name: S082-03-INT-SweetSpotBlocs-V001
                intervals_name = f"{session_id}-{session_type}-{session_name}-{session_version}"

                event_data = {
                    "category": "WORKOUT",
                    "type": "VirtualRide",
                    "name": intervals_name,
                    "description": session_description,
                    "start_date_local": f"{session_date}T{start_time}",
                }

                if intervals_id:
                    # Update existing event
                    client.update_event(intervals_id, event_data)
                    sync_result = f"Updated Intervals.icu event {intervals_id}"
                else:
                    # Create new event
                    created = client.create_event(event_data)
                    if created and "id" in created:
                        new_intervals_id = created["id"]
                        # Save intervals_id back to planning
                        with planning_tower.modify_week(
                            week_id,
                            requesting_script="mcp-server",
                            reason=f"MCP: Save Intervals.icu ID {new_intervals_id} for {session_id}",
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
