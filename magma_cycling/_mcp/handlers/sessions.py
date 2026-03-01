"""Session manipulation handlers (duplicate, swap, attach-workout)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from magma_cycling._mcp._utils import compute_start_time, mcp_response, suppress_stdout_stderr

if TYPE_CHECKING:
    from mcp.types import TextContent

__all__ = [
    "handle_duplicate_session",
    "handle_swap_sessions",
    "handle_attach_workout",
]


async def handle_duplicate_session(args: dict) -> list[TextContent]:
    """Duplicate an existing session to a new date."""
    from datetime import datetime

    from magma_cycling.planning.control_tower import planning_tower
    from magma_cycling.planning.models import Session

    week_id = args["week_id"]
    source_session_id = args["source_session_id"]
    target_date_str = args["target_date"]
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()

    try:
        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            # Modify via Control Tower
            with planning_tower.modify_week(
                week_id,
                requesting_script="mcp-server",
                reason=f"MCP: Duplicate {source_session_id} to {target_date_str}",
            ) as plan:
                # Find source session
                source_session = None
                for session in plan.planned_sessions:
                    if session.session_id == source_session_id:
                        source_session = session
                        break

                if not source_session:
                    raise ValueError(f"Source session {source_session_id} not found in {week_id}")

                # Generate new session_id for target date
                day_num = target_date.weekday()
                day_index = day_num + 1

                existing_sessions = [
                    s for s in plan.planned_sessions if s.session_date == target_date
                ]

                if not existing_sessions:
                    new_session_id = f"{week_id}-{day_index:02d}"
                else:
                    existing_suffixes = []
                    for s in existing_sessions:
                        if len(s.session_id.split("-")[1]) > 2:
                            suffix = s.session_id.split("-")[1][2]
                            existing_suffixes.append(suffix)

                    if not existing_suffixes:
                        new_session_id = f"{week_id}-{day_index:02d}a"
                    else:
                        next_letter = chr(ord(max(existing_suffixes)) + 1)
                        new_session_id = f"{week_id}-{day_index:02d}{next_letter}"

                # Create duplicate session
                new_session = Session(
                    session_id=new_session_id,
                    date=target_date,
                    name=source_session.name,
                    type=source_session.session_type,
                    version=source_session.version,
                    tss_planned=source_session.tss_planned,
                    duration_min=source_session.duration_min,
                    description=source_session.description,
                    status="planned",  # Reset status
                    # Don't copy intervals_id, description_hash, skip_reason
                )

                # Add to plan
                plan.planned_sessions.append(new_session)
                plan.planned_sessions.sort(key=lambda s: (s.session_date, s.session_id))

        result = {
            "status": "success",
            "week_id": week_id,
            "source_session_id": source_session_id,
            "new_session_id": new_session_id,
            "target_date": target_date_str,
            "message": f"Session duplicated successfully: {source_session_id} -> {new_session_id}",
        }

        return mcp_response(result)

    except FileNotFoundError:
        error = {"error": f"Planning file not found for week {week_id}"}
        return mcp_response(error)
    except ValueError as e:
        error = {"error": str(e)}
        return mcp_response(error)
    except Exception as e:
        error = {"error": f"Error duplicating session: {str(e)}"}
        return mcp_response(error)


async def handle_swap_sessions(args: dict) -> list[TextContent]:
    """Swap the dates of two sessions and update remote events if synced."""
    from magma_cycling.config import create_intervals_client
    from magma_cycling.planning.control_tower import planning_tower

    week_id = args["week_id"]
    session_id_1 = args["session_id_1"]
    session_id_2 = args["session_id_2"]

    try:
        # Track session data for remote update after local swap
        intervals_id_1 = None
        intervals_id_2 = None
        new_date_1 = None
        new_date_2 = None

        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            # Modify via Control Tower
            with planning_tower.modify_week(
                week_id,
                requesting_script="mcp-server",
                reason=f"MCP: Swap sessions {session_id_1} <-> {session_id_2}",
            ) as plan:
                # Find both sessions
                session_1 = None
                session_2 = None

                for session in plan.planned_sessions:
                    if session.session_id == session_id_1:
                        session_1 = session
                    elif session.session_id == session_id_2:
                        session_2 = session

                if not session_1:
                    raise ValueError(f"Session {session_id_1} not found in {week_id}")
                if not session_2:
                    raise ValueError(f"Session {session_id_2} not found in {week_id}")

                # PROTECTION: Refuse to swap if either session is completed
                if session_1.status == "completed":
                    raise ValueError(
                        f"⛔ PROTECTION: Cannot swap session {session_id_1} - "
                        f"Status is 'completed'. Completed sessions are protected from modification."
                    )
                if session_2.status == "completed":
                    raise ValueError(
                        f"⛔ PROTECTION: Cannot swap session {session_id_2} - "
                        f"Status is 'completed'. Completed sessions are protected from modification."
                    )

                # Swap dates
                temp_date = session_1.session_date
                session_1.session_date = session_2.session_date
                session_2.session_date = temp_date

                # Swap session_ids so the day index matches the new date
                temp_id = session_1.session_id
                session_1.session_id = session_2.session_id
                session_2.session_id = temp_id

                # Capture data for remote update (after id swap)
                intervals_id_1 = session_1.intervals_id
                intervals_id_2 = session_2.intervals_id
                new_date_1 = session_1.session_date
                new_date_2 = session_2.session_date
                # Build new intervals_names with swapped session_ids
                new_name_1 = (
                    f"{session_1.session_id}-{session_1.session_type}"
                    f"-{session_1.name}-{session_1.version}"
                )
                new_name_2 = (
                    f"{session_2.session_id}-{session_2.session_type}"
                    f"-{session_2.name}-{session_2.version}"
                )

                # Re-sort sessions
                plan.planned_sessions.sort(key=lambda s: (s.session_date, s.session_id))

            # Update remote events if both sessions are synced
            remote_updated = False
            if intervals_id_1 and intervals_id_2:
                client = create_intervals_client()
                start_time_1 = compute_start_time(new_date_1, session_1.session_id)
                start_time_2 = compute_start_time(new_date_2, session_2.session_id)

                client.update_event(
                    intervals_id_1,
                    {
                        "name": new_name_1,
                        "start_date_local": f"{new_date_1}T{start_time_1}",
                    },
                )
                client.update_event(
                    intervals_id_2,
                    {
                        "name": new_name_2,
                        "start_date_local": f"{new_date_2}T{start_time_2}",
                    },
                )
                remote_updated = True

        result = {
            "status": "success",
            "week_id": week_id,
            "session_id_1": session_id_1,
            "session_id_2": session_id_2,
            "swapped_session_ids": [session_id_1, session_id_2],
            "remote_updated": remote_updated,
            "message": f"Sessions swapped successfully: {session_id_1} <-> {session_id_2}"
            + (" (+ remote events updated)" if remote_updated else ""),
        }

        return mcp_response(result)

    except FileNotFoundError:
        error = {"error": f"Planning file not found for week {week_id}"}
        return mcp_response(error)
    except ValueError as e:
        error = {"error": str(e)}
        return mcp_response(error)
    except Exception as e:
        error = {"error": f"Error swapping sessions: {str(e)}"}
        return mcp_response(error)


async def handle_attach_workout(args: dict) -> list[TextContent]:
    """Attach a workout file to a session."""
    from magma_cycling.config import get_data_config

    session_id = args["session_id"]
    workout_name = args["workout_name"]
    workout_type = args.get("workout_type", "WKT")
    content = args["content"]
    version = args.get("version", "V001")
    extension = args.get("extension", "zwo")

    try:
        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            # Get workouts directory
            config = get_data_config()
            workouts_dir = config.data_repo_path / "workouts"
            workouts_dir.mkdir(parents=True, exist_ok=True)

            # Build filename: {session_id}-{type}-{name}-{version}.{ext}
            filename = f"{session_id}-{workout_type}-{workout_name}-{version}.{extension}"
            file_path = workouts_dir / filename

            # Write workout file
            file_path.write_text(content, encoding="utf-8")

        result = {
            "status": "success",
            "session_id": session_id,
            "filename": filename,
            "path": str(file_path),
            "message": f"Workout attached successfully: {filename}",
        }

        return mcp_response(result)

    except Exception as e:
        error = {"error": f"Error attaching workout: {str(e)}"}
        return mcp_response(error)
