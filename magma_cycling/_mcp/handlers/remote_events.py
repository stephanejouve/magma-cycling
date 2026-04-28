"""Remote event management handlers (delete, list, update, create-note)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from magma_cycling._mcp._utils import mcp_response, suppress_stdout_stderr

if TYPE_CHECKING:
    from mcp.types import TextContent

__all__ = [
    "handle_delete_remote_event",
    "handle_list_remote_events",
    "handle_update_remote_event",
    "handle_create_remote_note",
]


async def handle_delete_remote_event(args: dict) -> list[TextContent]:
    """Delete a remote workout event and update local planning via Control Tower."""
    from magma_cycling.config import create_intervals_client
    from magma_cycling.planning.control_tower import planning_tower

    event_id = args["event_id"]
    confirm = args.get("confirm", False)

    if not confirm:
        error = {
            "error": "Deletion requires explicit confirmation",
            "event_id": event_id,
            "message": "Set confirm=true to proceed with deletion",
            "warning": "This action is PERMANENT and cannot be undone",
        }
        return mcp_response(error)

    try:
        with suppress_stdout_stderr():
            found_week_id = None
            found_session = None

            if planning_tower.planning_dir.exists():
                for week_file in planning_tower.planning_dir.glob("week_planning_S???.json"):
                    try:
                        week_id = week_file.stem.replace("week_planning_", "")
                        plan = planning_tower.read_week(week_id)
                        for session in plan.planned_sessions:
                            if session.intervals_id == event_id:
                                if session.status == "completed":
                                    error = {
                                        "error": "Cannot delete completed session",
                                        "event_id": event_id,
                                        "session_id": session.session_id,
                                        "session_name": session.name,
                                        "status": session.status,
                                        "message": f"🛡️ PROTECTION: Session {session.session_id} is COMPLETED and cannot be deleted from Intervals.icu",
                                        "reason": "Completed sessions are protected to preserve training history",
                                    }
                                    return mcp_response(error)
                                found_week_id = week_id
                                found_session = session
                                break
                    except Exception:
                        continue

                    if found_session:
                        break

            client = create_intervals_client()
            _provider_info = client.get_provider_info()
            success = client.delete_event(event_id)

            if not success:
                error = {
                    "success": False,
                    "event_id": event_id,
                    "message": f"❌ Failed to delete event {event_id} from Intervals.icu (check logs for details)",
                }
                return mcp_response(error)

            local_update_status = None
            if found_week_id and found_session:
                try:
                    from magma_cycling.planning.models import Session

                    with planning_tower.modify_week(
                        week_id=found_week_id,
                        requesting_script="delete-remote-session",
                        reason=f"Write-back: removed intervals_id after deleting event {event_id}",
                    ) as plan:
                        updated_sessions = []
                        for session in plan.planned_sessions:
                            if session.intervals_id == event_id:
                                session_dict = session.model_dump()
                                session_dict["intervals_id"] = None
                                if session_dict["status"] == "uploaded":
                                    session_dict["status"] = "planned"
                                updated_session = Session(**session_dict)
                                updated_sessions.append(updated_session)
                            else:
                                updated_sessions.append(session)

                        plan.planned_sessions = updated_sessions

                    local_update_status = {
                        "updated": True,
                        "week_id": found_week_id,
                        "session_id": found_session.session_id,
                        "message": f"🔄 Local planning updated: intervals_id removed from {found_session.session_id}",
                    }
                except Exception as e:
                    local_update_status = {
                        "updated": False,
                        "error": str(e),
                        "message": f"⚠️ Event deleted from Intervals.icu but failed to update local planning: {e}",
                    }

            result = {
                "success": True,
                "event_id": event_id,
                "message": f"✅ Event {event_id} deleted successfully from Intervals.icu",
                "local_planning_update": local_update_status,
            }

        return mcp_response(result, provider_info=_provider_info)

    except Exception as e:
        error = {
            "error": f"Delete error: {str(e)}",
            "event_id": event_id,
        }
        return mcp_response(error)


async def handle_list_remote_events(args: dict) -> list[TextContent]:
    """List all remote events for a date range."""
    from magma_cycling.config import create_intervals_client

    start_date_str = args["start_date"]
    end_date_str = args["end_date"]
    category_filter = args.get("category")

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()
            _provider_info = client.get_provider_info()
            events = client.get_events(oldest=start_date_str, newest=end_date_str)

            if category_filter:
                events = [e for e in events if e.get("category") == category_filter]

            formatted_events = []
            for event in events:
                formatted_event = {
                    "id": event.get("id"),
                    "category": event.get("category"),
                    "name": event.get("name"),
                    "description": (event.get("description") or "")[:100],
                    "start_date_local": event.get("start_date_local"),
                    "type": event.get("type"),
                }
                formatted_events.append(formatted_event)

            result = {
                "start_date": start_date_str,
                "end_date": end_date_str,
                "total_events": len(formatted_events),
                "events": formatted_events,
            }

            if category_filter:
                result["filtered_by"] = category_filter

        return mcp_response(result, provider_info=_provider_info)

    except Exception as e:
        error = {
            "error": f"Failed to list remote events: {str(e)}",
            "start_date": start_date_str,
            "end_date": end_date_str,
        }
        return mcp_response(error)


async def handle_update_remote_event(args: dict) -> list[TextContent]:
    """Update an existing remote workout event with write-back to local planning."""
    from datetime import datetime

    from magma_cycling.config import create_intervals_client
    from magma_cycling.planning.control_tower import planning_tower
    from magma_cycling.planning.models import Session

    event_id = args["event_id"]
    updates = args["updates"]

    try:
        with suppress_stdout_stderr():
            target_week_id = None
            target_session = None

            if planning_tower.planning_dir.exists():
                for week_file in planning_tower.planning_dir.glob("week_planning_S???.json"):
                    try:
                        week_id = week_file.stem.replace("week_planning_", "")
                        plan = planning_tower.read_week(week_id)
                        for session in plan.planned_sessions:
                            if session.intervals_id == event_id:
                                if session.status == "completed":
                                    error = {
                                        "error": "Cannot update completed session",
                                        "event_id": event_id,
                                        "session_id": session.session_id,
                                        "message": f"🛡️ PROTECTION: Session {session.session_id} is COMPLETED",
                                    }
                                    return mcp_response(error)
                                target_week_id = week_id
                                target_session = session
                                break
                        if target_week_id:
                            break
                    except Exception:
                        continue

            client = create_intervals_client()
            _provider_info = client.get_provider_info()
            updated_event = client.update_event(event_id, updates)

            if updated_event:
                if target_week_id and target_session:
                    with planning_tower.modify_week(
                        target_week_id,
                        requesting_script="update-remote-session",
                        reason=f"Write-back from Intervals.icu update: {list(updates.keys())}",
                    ) as plan:
                        updated_sessions = []
                        for session in plan.planned_sessions:
                            if session.session_id == target_session.session_id:
                                session_dict = session.model_dump()

                                if "name" in updates:
                                    parts = updates["name"].split("-")
                                    raw_name = parts[-1]
                                    if raw_name.startswith("V") and raw_name[1:].isdigit():
                                        raw_name = parts[-2] if len(parts) >= 2 else updates["name"]
                                    session_dict["name"] = raw_name

                                if "start_date_local" in updates:
                                    date_str = updates["start_date_local"].split("T")[0]
                                    session_dict["session_date"] = datetime.strptime(
                                        date_str, "%Y-%m-%d"
                                    ).date()

                                updated_session = Session(**session_dict)
                                updated_sessions.append(updated_session)
                            else:
                                updated_sessions.append(session)

                        plan.planned_sessions = updated_sessions

                result = {
                    "success": True,
                    "event_id": event_id,
                    "updated_fields": list(updates.keys()),
                    "local_planning_updated": target_week_id is not None,
                    "week_id": target_week_id,
                    "session_id": target_session.session_id if target_session else None,
                    "message": f"✅ Event {event_id} updated successfully"
                    + (" (+ local planning)" if target_week_id else ""),
                }
            else:
                result = {
                    "success": False,
                    "event_id": event_id,
                    "message": f"❌ Failed to update event {event_id}",
                }

        return mcp_response(result, provider_info=_provider_info)

    except Exception as e:
        error = {"error": f"Update error: {str(e)}", "event_id": event_id}
        return mcp_response(error)


async def handle_create_remote_note(args: dict) -> list[TextContent]:
    """Create a NOTE (calendar note) on remote platform with write-back to local planning."""
    import re

    from magma_cycling.config import create_intervals_client
    from magma_cycling.planning.control_tower import planning_tower
    from magma_cycling.planning.models import SESSION_ID_PATTERN, Session

    note_date = args["date"]
    name = args["name"]
    description = args["description"]

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()
            _provider_info = client.get_provider_info()

            event_data = {
                "category": "NOTE",
                "name": name,
                "description": description,
                "start_date_local": f"{note_date}T00:00:00",
            }

            created_event = client.create_event(event_data)

            if created_event and "id" in created_event:
                # Status write-back is opt-in: only triggered if the note name
                # starts with an explicit status prefix. A note merely mentioning
                # a session_id (e.g. documentation) must NOT mutate the planning.
                status_map = {
                    "[ANNULÉE]": "cancelled",
                    "[SAUTÉE]": "skipped",
                    "[REMPLACÉE]": "replaced",
                }
                new_status = next(
                    (status for prefix, status in status_map.items() if name.startswith(prefix)),
                    None,
                )

                if new_status is None:
                    local_update_msg = (
                        " (documentary note — local planning not updated; "
                        "use [ANNULÉE]/[SAUTÉE]/[REMPLACÉE] prefix to opt in)"
                    )
                else:
                    session_id_match = re.search(SESSION_ID_PATTERN, name)
                    if not session_id_match:
                        local_update_msg = (
                            " (status prefix found but no session_id — "
                            "local planning not updated)"
                        )
                    else:
                        session_id = session_id_match.group()
                        week_id = session_id.split("-")[0]
                        try:
                            with planning_tower.modify_week(
                                week_id,
                                requesting_script="create-remote-note",
                                reason=(
                                    f"Write-back from NOTE creation: "
                                    f"{new_status} session {session_id}"
                                ),
                            ) as plan:
                                updated_sessions = []
                                for session in plan.planned_sessions:
                                    if session.session_id == session_id:
                                        session_dict = session.model_dump()
                                        session_dict["status"] = new_status
                                        session_dict["reason"] = description[:100]
                                        updated_session = Session(**session_dict)
                                        updated_sessions.append(updated_session)
                                    else:
                                        updated_sessions.append(session)

                                plan.planned_sessions = updated_sessions

                            local_update_msg = (
                                f" (+ local planning {week_id}/{session_id} → {new_status})"
                            )
                        except Exception as e:
                            local_update_msg = f" (local planning update failed: {str(e)})"

                result = {
                    "success": True,
                    "event_id": created_event["id"],
                    "date": note_date,
                    "name": name,
                    "message": f"✅ NOTE created successfully on Intervals.icu (ID: {created_event['id']}){local_update_msg}",
                }
            else:
                result = {
                    "success": False,
                    "message": "❌ Failed to create NOTE - no ID returned from Intervals.icu",
                }

        return mcp_response(result, provider_info=_provider_info)

    except Exception as e:
        error = {
            "error": f"Failed to create NOTE: {str(e)}",
            "date": note_date,
            "name": name,
        }
        return mcp_response(error)
