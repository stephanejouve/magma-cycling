"""Remote platform sync handlers (sync-week, sync-remote, backfill)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from magma_cycling._mcp._utils import (
    SYNCABLE_STATUSES,
    compute_start_time,
    load_workout_descriptions,
    mcp_response,
    suppress_stdout_stderr,
)
from magma_cycling.utils.event_sync import evaluate_sync

if TYPE_CHECKING:
    from mcp.types import TextContent

__all__ = [
    "handle_sync_week_to_calendar",
    "handle_sync_remote_to_local",
    "handle_backfill_activities",
]


async def handle_sync_week_to_calendar(args: dict) -> list[TextContent]:
    """Synchronize week planning to training calendar."""
    from magma_cycling.config import create_intervals_client
    from magma_cycling.planning.control_tower import planning_tower

    week_id = args["week_id"]
    dry_run = args.get("dry_run", False)
    force_update = args.get("force_update", False)
    session_ids = args.get("session_ids")

    try:
        with suppress_stdout_stderr():
            plan = planning_tower.read_week(week_id)
            client = create_intervals_client()

            start_date = str(plan.start_date)
            end_date = str(plan.end_date)
            remote_events = client.get_events(oldest=start_date, newest=end_date)
            remote_workouts = {e["id"]: e for e in remote_events if e.get("category") == "WORKOUT"}

            workout_descriptions = load_workout_descriptions(week_id)

            to_create = []
            to_update = []
            to_skip_protected = []
            warnings = []
            errors = []

            sessions_to_process = plan.planned_sessions
            if session_ids:
                session_ids_set = set(session_ids)
                sessions_to_process = [
                    s for s in plan.planned_sessions if s.session_id in session_ids_set
                ]

            for session in sessions_to_process:
                if session.status not in SYNCABLE_STATUSES:
                    to_skip_protected.append(
                        {
                            "session_id": session.session_id,
                            "name": session.name,
                            "status": session.status,
                            "reason": f"Session {session.status} - protected from sync",
                        }
                    )
                    continue

                start_time = compute_start_time(session.session_date, session.session_id)
                intervals_name = (
                    f"{session.session_id}-{session.session_type}-{session.name}-{session.version}"
                )
                full_description = workout_descriptions.get(intervals_name, session.description)

                event_data = {
                    "category": "WORKOUT",
                    "type": "VirtualRide",
                    "name": intervals_name,
                    "description": full_description,
                    "start_date_local": f"{session.session_date}T{start_time}",
                }

                if (
                    session.duration_min
                    and session.duration_min > 0
                    and full_description
                    and full_description.strip()
                ):
                    from magma_cycling.intervals_format_validator import (
                        IntervalsFormatValidator,
                    )

                    validator = IntervalsFormatValidator()
                    is_valid, val_errors, _val_warnings = validator.validate_workout(
                        full_description
                    )
                    if not is_valid:
                        errors.append(
                            f"Session {session.session_id}: workout validation failed — {val_errors}. "
                            f"Fix with validate-workout tool, then retry sync."
                        )
                        continue

                existing_event = None
                if session.intervals_id and session.intervals_id in remote_workouts:
                    existing_event = remote_workouts[session.intervals_id]

                decision = evaluate_sync(event_data, existing_event, force_update=force_update)

                if decision.action == "skip":
                    to_skip_protected.append(
                        {
                            "session_id": session.session_id,
                            "name": session.name,
                            "status": "remote_protected",
                            "reason": decision.reason,
                        }
                    )
                    continue

                if decision.action == "update" and existing_event and not force_update:
                    remote_name = existing_event.get("name", "")
                    remote_start = existing_event.get("start_date_local", "")
                    if (
                        remote_name != intervals_name
                        or remote_start != event_data["start_date_local"]
                    ):
                        warnings.append(
                            {
                                "session_id": session.session_id,
                                "intervals_id": session.intervals_id,
                                "type": "remote_modification_detected",
                                "message": f"⚠️ Remote event {session.intervals_id} has been manually modified in Intervals.icu",
                                "local_name": intervals_name,
                                "remote_name": remote_name,
                                "suggestion": "Use force_update=true to overwrite remote changes",
                            }
                        )
                        continue

                if decision.action == "create":
                    to_create.append(
                        {
                            "session_id": session.session_id,
                            "name": session.name,
                            "event_data": event_data,
                        }
                    )
                elif decision.action == "update":
                    update_data = {
                        "name": intervals_name,
                        "description": full_description,
                        "start_date_local": f"{session.session_date}T{start_time}",
                    }
                    to_update.append(
                        {
                            "session_id": session.session_id,
                            "intervals_id": decision.existing_event_id,
                            "name": session.name,
                            "event_data": update_data,
                        }
                    )

            created_count = 0
            updated_count = 0

            if not dry_run:
                for item in to_create:
                    try:
                        created = client.create_event(item["event_data"])

                        if created is None:
                            errors.append(
                                f"Failed to create {item['session_id']}: API returned None "
                                f"(check logs for HTTP errors)"
                            )
                        elif "id" not in created:
                            errors.append(
                                f"Failed to create {item['session_id']}: Response missing 'id' field. "
                                f"Got keys: {list(created.keys())}, "
                                f"Response preview: {str(created)[:200]}"
                            )
                        else:
                            new_intervals_id = created["id"]

                            with planning_tower.modify_week(
                                week_id,
                                requesting_script="mcp-server",
                                reason=f"MCP: Sync - Save Intervals.icu ID {new_intervals_id} for {item['session_id']}",
                            ) as plan:
                                for session in plan.planned_sessions:
                                    if session.session_id == item["session_id"]:
                                        session.intervals_id = new_intervals_id
                                        break

                            created_count += 1

                    except Exception as e:
                        errors.append(f"Error creating {item['session_id']}: {str(e)}")

                for item in to_update:
                    try:
                        updated = client.update_event(item["intervals_id"], item["event_data"])
                        if updated:
                            updated_count += 1
                        else:
                            errors.append(f"Failed to update {item['session_id']}")

                    except Exception as e:
                        errors.append(f"Error updating {item['session_id']}: {str(e)}")

        if errors:
            status = "partial_success"
        elif warnings:
            status = "success_with_warnings"
        else:
            status = "success"

        result = {
            "status": status,
            "week_id": week_id,
            "dry_run": dry_run,
            "summary": {
                "to_create": len(to_create),
                "to_update": len(to_update),
                "skipped_protected": len(to_skip_protected),
                "warnings": len(warnings),
                "created": created_count if not dry_run else 0,
                "updated": updated_count if not dry_run else 0,
                "errors": len(errors),
            },
            "details": {
                "to_create": [
                    {"session_id": item["session_id"], "name": item["name"]} for item in to_create
                ],
                "to_update": [
                    {
                        "session_id": item["session_id"],
                        "intervals_id": item["intervals_id"],
                        "name": item["name"],
                    }
                    for item in to_update
                ],
                "skipped_protected": to_skip_protected,
            },
            "warnings": warnings if warnings else None,
            "errors": errors if errors else None,
            "message": f"Sync {'preview' if dry_run else 'completed'} for {week_id}",
        }

        return mcp_response(result)

    except FileNotFoundError:
        error = {"error": f"Planning file not found for week {week_id}"}
        return mcp_response(error)
    except Exception as e:
        error = {"error": f"Sync error: {str(e)}"}
        return mcp_response(error)


async def handle_sync_remote_to_local(args: dict) -> list[TextContent]:
    """Sync local planning from remote events."""
    try:
        with suppress_stdout_stderr():
            from magma_cycling.config import create_intervals_client
            from magma_cycling.planning.control_tower import planning_tower

            week_id = args["week_id"]
            strategy = args.get("strategy", "merge")

            client = create_intervals_client()

            stats = planning_tower.sync_from_remote(
                week_id=week_id,
                intervals_client=client,
                strategy=strategy,
                requesting_script="mcp:sync-remote-to-local",
            )

            result = {
                "week_id": week_id,
                "strategy": strategy,
                "stats": stats,
                "message": f"Synced {week_id} from Intervals.icu",
            }

            changes = []
            if stats["sessions_added"]:
                changes.append(
                    f"✅ Added {len(stats['sessions_added'])} sessions: {', '.join(stats['sessions_added'])}"
                )
            if stats["sessions_updated"]:
                changes.append(
                    f"🔄 Updated {len(stats['sessions_updated'])} sessions: {', '.join(stats['sessions_updated'])}"
                )
            if stats["intervals_ids_fixed"]:
                changes.append(
                    f"🔧 Fixed {len(stats['intervals_ids_fixed'])} intervals_id mismatches"
                )
                for fix in stats["intervals_ids_fixed"]:
                    changes.append(f"  - {fix['session_id']}: {fix['old_id']} → {fix['new_id']}")
            if stats["sessions_removed"]:
                changes.append(
                    f"🗑️ Removed {len(stats['sessions_removed'])} sessions: {', '.join(stats['sessions_removed'])}"
                )

            if not changes:
                changes.append("ℹ️ No changes needed - local planning already in sync")

            result["changes"] = changes

            return mcp_response(result)
    except Exception as e:
        error = {
            "error": str(e),
            "week_id": args.get("week_id"),
        }
        return mcp_response(error)


async def handle_backfill_activities(args: dict) -> list[TextContent]:
    """Backfill historical activity data into local planning sessions."""
    with suppress_stdout_stderr():
        import re
        from datetime import datetime

        from magma_cycling.config import create_intervals_client, get_data_config
        from magma_cycling.daily_sync import DailySync
        from magma_cycling.planning.models import SESSION_ID_PATTERN, WeeklyPlan

        if "week_id" in args:
            week_id = args["week_id"]

            data_config = get_data_config()
            planning_file = data_config.week_planning_dir / f"week_planning_{week_id}.json"

            if not planning_file.exists():
                error = {"error": f"Planning file not found for {week_id}"}
                return mcp_response(error)

            plan = WeeklyPlan.from_json(planning_file)
            start_date_val = plan.start_date
            end_date_val = plan.end_date
            date_source = f"week {week_id}"

        else:
            start_date_val = datetime.fromisoformat(args["start_date"]).date()
            end_date_val = datetime.fromisoformat(args["end_date"]).date()
            date_source = f"{start_date_val} to {end_date_val}"

        client = create_intervals_client()
        activities = client.get_activities(oldest=start_date_val, newest=end_date_val)

        if not activities:
            info = {
                "message": f"No activities found for {date_source}",
                "start_date": str(start_date_val),
                "end_date": str(end_date_val),
                "activities_count": 0,
            }
            return mcp_response(info)

        data_config = get_data_config()
        tracking_file = data_config.data_repo_path / ".backfill_tracking.json"
        reports_dir = data_config.data_repo_path / "reports"
        reports_dir.mkdir(exist_ok=True)

        sync = DailySync(
            tracking_file=tracking_file,
            reports_dir=reports_dir,
            verbose=False,
        )

        activity_to_session_map = sync.update_completed_sessions(activities)

        updated = {}
        already_completed = {}
        unmatched = []

        from magma_cycling.planning.control_tower import planning_tower

        for activity in activities:
            activity_id = activity["id"]

            if activity_id in activity_to_session_map:
                updated[activity_id] = activity_to_session_map[activity_id]
                continue

            name = activity.get("name", "")
            match = re.search(SESSION_ID_PATTERN, name)

            if not match:
                unmatched.append(activity_id)
                continue

            session_id = match.group()
            week_id = session_id.split("-")[0]

            try:
                session_found = False

                with planning_tower.modify_week(
                    week_id,
                    requesting_script="mcp:backfill-activities",
                    reason=f"Backfill {session_id} from activity {activity_id}",
                ) as plan:
                    for session in plan.planned_sessions:
                        if session.session_id == session_id:
                            session_found = True
                            if session.status != "completed":
                                session.status = "completed"
                                updated[activity_id] = session_id
                            else:
                                already_completed[activity_id] = session_id
                            break

                if not session_found:
                    unmatched.append(activity_id)
            except Exception:
                unmatched.append(activity_id)

        result = {
            "message": f"Backfill complete: {len(updated)} updated, {len(already_completed)} already completed, {len(unmatched)} unmatched",
            "start_date": str(start_date_val),
            "end_date": str(end_date_val),
            "total_activities": len(activities),
            "updated": len(updated),
            "already_completed": len(already_completed),
            "unmatched": len(unmatched),
            "details": {
                "updated_sessions": [],
                "already_completed_sessions": [],
                "unmatched_activities": [],
            },
        }

        for activity_id, session_id in updated.items():
            activity = next((a for a in activities if a["id"] == activity_id), None)
            if activity:
                result["details"]["updated_sessions"].append(
                    {
                        "activity_id": activity_id,
                        "activity_name": activity.get("name", ""),
                        "session_id": session_id,
                        "date": activity.get("start_date_local", "")[:10],
                    }
                )

        for activity_id, session_id in already_completed.items():
            activity = next((a for a in activities if a["id"] == activity_id), None)
            if activity:
                result["details"]["already_completed_sessions"].append(
                    {
                        "activity_id": activity_id,
                        "activity_name": activity.get("name", ""),
                        "session_id": session_id,
                        "date": activity.get("start_date_local", "")[:10],
                    }
                )

        for activity_id in unmatched:
            activity = next((a for a in activities if a["id"] == activity_id), None)
            if activity:
                result["details"]["unmatched_activities"].append(
                    {
                        "activity_id": activity_id,
                        "activity_name": activity.get("name", ""),
                        "date": activity.get("start_date_local", "")[:10],
                    }
                )

        return mcp_response(result)
