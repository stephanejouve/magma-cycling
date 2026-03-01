"""Intervals.icu integration handlers."""

import json
from collections import defaultdict
from datetime import date, timedelta

from mcp.types import TextContent

from magma_cycling._mcp._utils import (
    SYNCABLE_STATUSES,
    compute_start_time,
    load_workout_descriptions,
    suppress_stdout_stderr,
)

__all__ = [
    "handle_sync_week_to_intervals",
    "handle_delete_remote_session",
    "handle_list_remote_events",
    "handle_get_activity_details",
    "handle_get_activity_intervals",
    "handle_get_activity_streams",
    "handle_compare_intervals",
    "handle_apply_workout_intervals",
    "handle_update_remote_session",
    "handle_create_remote_note",
    "handle_sync_remote_to_local",
    "handle_backfill_activities",
]


async def handle_sync_week_to_intervals(args: dict) -> list[TextContent]:
    """Synchronize week planning to Intervals.icu."""
    from magma_cycling.config import create_intervals_client
    from magma_cycling.planning.control_tower import planning_tower

    week_id = args["week_id"]
    dry_run = args.get("dry_run", False)
    force_update = args.get("force_update", False)
    session_ids = args.get("session_ids")

    try:
        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            # Read local planning
            plan = planning_tower.read_week(week_id)

            # Create Intervals.icu client
            client = create_intervals_client()

            # Get remote events for this week
            start_date = str(plan.start_date)
            end_date = str(plan.end_date)
            remote_events = client.get_events(oldest=start_date, newest=end_date)

            # Filter to workouts only
            remote_workouts = {e["id"]: e for e in remote_events if e.get("category") == "WORKOUT"}

            # Load full workout descriptions from workouts.txt
            workout_descriptions = load_workout_descriptions(week_id)

            # Track changes
            to_create = []
            to_update = []
            to_skip_protected = []
            warnings = []
            errors = []

            # Determine sessions to process (selective sync support)
            sessions_to_process = plan.planned_sessions
            if session_ids:
                session_ids_set = set(session_ids)
                sessions_to_process = [
                    s for s in plan.planned_sessions if s.session_id in session_ids_set
                ]

            # Process each session
            for session in sessions_to_process:
                # PROTECTION: Only sync sessions with syncable statuses
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

                # Compute start time using shared helper
                start_time = compute_start_time(session.session_date, session.session_id)

                # Build Intervals.icu event name: S082-03-INT-SweetSpotBlocs-V001
                intervals_name = (
                    f"{session.session_id}-{session.session_type}-{session.name}-{session.version}"
                )

                # Use full workout description from workouts.txt if available
                full_description = workout_descriptions.get(intervals_name, session.description)

                event_data = {
                    "category": "WORKOUT",
                    "type": "VirtualRide",
                    "name": intervals_name,
                    "description": full_description,
                    "start_date_local": f"{session.session_date}T{start_time}",
                }

                # Validate workout description before creating remote event
                if full_description and full_description.strip():
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

                if session.intervals_id:
                    # Check if event exists remotely
                    if session.intervals_id in remote_workouts:
                        # Event exists - check for conflicts
                        remote_event = remote_workouts[session.intervals_id]

                        # VALIDATION: Detect if remote was manually modified
                        remote_name = remote_event.get("name", "")
                        remote_start = remote_event.get("start_date_local", "")
                        local_start = f"{session.session_date}T{start_time}"

                        has_remote_changes = (
                            remote_name != intervals_name or remote_start != local_start
                        )

                        if has_remote_changes and not force_update:
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

                        # Check if update needed
                        needs_update = force_update or has_remote_changes

                        if needs_update:
                            update_data = {
                                "name": intervals_name,
                                "description": full_description,
                                "start_date_local": f"{session.session_date}T{start_time}",
                            }
                            to_update.append(
                                {
                                    "session_id": session.session_id,
                                    "intervals_id": session.intervals_id,
                                    "name": session.name,
                                    "event_data": update_data,
                                }
                            )
                    else:
                        # intervals_id set but event doesn't exist remotely
                        to_create.append(
                            {
                                "session_id": session.session_id,
                                "name": session.name,
                                "event_data": event_data,
                            }
                        )
                else:
                    # No intervals_id - create new event
                    to_create.append(
                        {
                            "session_id": session.session_id,
                            "name": session.name,
                            "event_data": event_data,
                        }
                    )

            # Apply changes if not dry run
            created_count = 0
            updated_count = 0

            if not dry_run:
                # Create new events
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

                            # Save intervals_id back to planning
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

                # Update existing events
                for item in to_update:
                    try:
                        updated = client.update_event(item["intervals_id"], item["event_data"])
                        if updated:
                            updated_count += 1
                        else:
                            errors.append(f"Failed to update {item['session_id']}")

                    except Exception as e:
                        errors.append(f"Error updating {item['session_id']}: {str(e)}")

        # Build result
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

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except FileNotFoundError:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Planning file not found for week {week_id}"}, indent=2),
            )
        ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Sync error: {str(e)}"}, indent=2),
            )
        ]


async def handle_delete_remote_session(args: dict) -> list[TextContent]:
    """Delete a workout event from Intervals.icu and update local planning via Control Tower."""
    from magma_cycling.config import create_intervals_client
    from magma_cycling.planning.control_tower import planning_tower

    event_id = args["event_id"]
    confirm = args.get("confirm", False)

    if not confirm:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": "Deletion requires explicit confirmation",
                        "event_id": event_id,
                        "message": "Set confirm=true to proceed with deletion",
                        "warning": "This action is PERMANENT and cannot be undone",
                    },
                    indent=2,
                ),
            )
        ]

    try:
        with suppress_stdout_stderr():
            # PROTECTION: Find session associated with this event
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
                                    return [
                                        TextContent(
                                            type="text",
                                            text=json.dumps(
                                                {
                                                    "error": "Cannot delete completed session",
                                                    "event_id": event_id,
                                                    "session_id": session.session_id,
                                                    "session_name": session.name,
                                                    "status": session.status,
                                                    "message": f"🛡️ PROTECTION: Session {session.session_id} is COMPLETED and cannot be deleted from Intervals.icu",
                                                    "reason": "Completed sessions are protected to preserve training history",
                                                },
                                                indent=2,
                                            ),
                                        )
                                    ]
                                found_week_id = week_id
                                found_session = session
                                break
                    except Exception:
                        continue

                    if found_session:
                        break

            # Create Intervals.icu client
            client = create_intervals_client()

            # Attempt deletion on Intervals.icu
            success = client.delete_event(event_id)

            if not success:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": False,
                                "event_id": event_id,
                                "message": f"❌ Failed to delete event {event_id} from Intervals.icu (check logs for details)",
                            },
                            indent=2,
                        ),
                    )
                ]

            # WRITE-BACK: If we found a local session, update it via Control Tower
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

        return [
            TextContent(
                type="text",
                text=json.dumps(result, indent=2),
            )
        ]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Delete error: {str(e)}",
                        "event_id": event_id,
                    },
                    indent=2,
                ),
            )
        ]


async def handle_list_remote_events(args: dict) -> list[TextContent]:
    """List all events from Intervals.icu for a date range."""
    from magma_cycling.config import create_intervals_client

    start_date_str = args["start_date"]
    end_date_str = args["end_date"]
    category_filter = args.get("category")

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()
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

        return [
            TextContent(
                type="text",
                text=json.dumps(result, indent=2),
            )
        ]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Failed to list remote events: {str(e)}",
                        "start_date": start_date_str,
                        "end_date": end_date_str,
                    },
                    indent=2,
                ),
            )
        ]


async def handle_get_activity_details(args: dict) -> list[TextContent]:
    """Get complete details for a completed activity from Intervals.icu."""
    from magma_cycling.config import create_intervals_client

    activity_id = args["activity_id"]
    include_streams = args.get("include_streams", False)

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()
            activity = client.get_activity(activity_id)

            average_watts = activity.get("average_watts")
            weighted_average_watts = activity.get("weighted_average_watts")

            # Fetch streams once if needed
            streams = None
            need_streams = (
                average_watts is None
                or weighted_average_watts is None
                or activity.get("average_heartrate") is not None
            )

            if need_streams:
                try:
                    streams = client.get_activity_streams(activity_id)
                except Exception:
                    streams = None

            # Calculate power metrics from streams if API doesn't provide them
            if (average_watts is None or weighted_average_watts is None) and streams:
                try:
                    watts_stream = next((s for s in streams if s["type"] == "watts"), None)

                    if watts_stream and watts_stream["data"]:
                        watts_data = watts_stream["data"]

                        if average_watts is None:
                            non_zero_watts = [w for w in watts_data if w > 0]
                            if non_zero_watts:
                                average_watts = round(sum(non_zero_watts) / len(non_zero_watts), 1)

                        if weighted_average_watts is None and len(watts_data) > 30:
                            rolling_avgs = []
                            for i in range(len(watts_data) - 29):
                                window = watts_data[i : i + 30]
                                rolling_avgs.append(sum(window) / 30)

                            if rolling_avgs:
                                fourth_powers = [p**4 for p in rolling_avgs]
                                avg_fourth = sum(fourth_powers) / len(fourth_powers)
                                weighted_average_watts = round(avg_fourth ** (1 / 4), 1)
                except Exception:
                    pass

            # Calculate cardiovascular decoupling
            cardiovascular_decoupling = None
            if streams:
                try:
                    watts_stream = next((s for s in streams if s["type"] == "watts"), None)
                    hr_stream = next((s for s in streams if s["type"] == "heartrate"), None)

                    if (
                        watts_stream
                        and hr_stream
                        and watts_stream["data"]
                        and hr_stream["data"]
                        and len(watts_stream["data"]) > 60
                        and weighted_average_watts is not None
                    ):
                        watts_data = watts_stream["data"]
                        hr_data = hr_stream["data"]

                        min_len = min(len(watts_data), len(hr_data))
                        watts_data = watts_data[:min_len]
                        hr_data = hr_data[:min_len]

                        midpoint = min_len // 2

                        watts_half1 = watts_data[:midpoint]
                        hr_half1 = hr_data[:midpoint]
                        watts_half2 = watts_data[midpoint:]
                        hr_half2 = hr_data[midpoint:]

                        def calc_np(watts):
                            rolling_avgs = []
                            for i in range(len(watts) - 29):
                                window = watts[i : i + 30]
                                rolling_avgs.append(sum(window) / 30)
                            fourth_powers = [p**4 for p in rolling_avgs]
                            avg_fourth = sum(fourth_powers) / len(fourth_powers)
                            return avg_fourth ** (1 / 4)

                        np_half1 = calc_np(watts_half1)
                        np_half2 = calc_np(watts_half2)

                        hr_half1_valid = [hr for hr in hr_half1 if hr > 0]
                        hr_half2_valid = [hr for hr in hr_half2 if hr > 0]

                        avg_hr_half1 = (
                            sum(hr_half1_valid) / len(hr_half1_valid) if hr_half1_valid else None
                        )
                        avg_hr_half2 = (
                            sum(hr_half2_valid) / len(hr_half2_valid) if hr_half2_valid else None
                        )

                        if (
                            np_half1
                            and np_half2
                            and avg_hr_half1
                            and avg_hr_half2
                            and avg_hr_half1 > 0
                        ):
                            ratio_half1 = np_half1 / avg_hr_half1
                            ratio_half2 = np_half2 / avg_hr_half2

                            cardiovascular_decoupling = round(
                                ((ratio_half2 - ratio_half1) / ratio_half1) * 100, 1
                            )
                except Exception:
                    pass

            # Format result
            result = {
                "id": activity.get("id"),
                "name": activity.get("name"),
                "start_date_local": activity.get("start_date_local"),
                "type": activity.get("type"),
                "moving_time": activity.get("moving_time"),
                "distance": activity.get("distance"),
                "total_elevation_gain": activity.get("total_elevation_gain"),
                "icu_training_load": activity.get("icu_training_load"),
                "icu_intensity": activity.get("icu_intensity"),
                "average_watts": average_watts,
                "weighted_average_watts": weighted_average_watts,
                "average_heartrate": activity.get("average_heartrate"),
                "average_cadence": activity.get("average_cadence"),
                "cardiovascular_decoupling": cardiovascular_decoupling,
                "description": activity.get("description", ""),
                "paired_event_id": activity.get("paired_event_id"),
            }

            # Include streams if requested
            if include_streams:
                streams = client.get_activity_streams(activity_id)
                result["streams"] = [
                    {"type": s["type"], "data_points": len(s["data"])} for s in streams
                ]

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Failed to get activity details: {str(e)}",
                        "activity_id": activity_id,
                    },
                    indent=2,
                ),
            )
        ]


async def handle_get_activity_intervals(args: dict) -> list[TextContent]:
    """Get aggregated interval/lap data for a completed activity from Intervals.icu."""
    from magma_cycling.config import create_intervals_client

    activity_id = args["activity_id"]

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()
            raw_intervals = client.get_activity_intervals(activity_id)

        keep_fields = {
            "type",
            "label",
            "start_index",
            "end_index",
            "elapsed_time",
            "moving_time",
            "distance",
            "average_watts",
            "weighted_average_watts",
            "min_watts",
            "max_watts",
            "average_heartrate",
            "min_heartrate",
            "max_heartrate",
            "average_cadence",
            "intensity",
            "training_load",
            "decoupling",
            "average_speed",
            "total_elevation_gain",
            "average_torque",
            "min_torque",
            "max_torque",
            "avg_lr_balance",
        }

        intervals = []
        total_elapsed = 0
        for iv in raw_intervals:
            filtered = {k: v for k, v in iv.items() if k in keep_fields and v is not None}
            intervals.append(filtered)
            total_elapsed += iv.get("elapsed_time", 0) or 0

        result = {
            "activity_id": activity_id,
            "total_intervals": len(intervals),
            "total_elapsed_seconds": total_elapsed,
            "intervals": intervals,
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Failed to get activity intervals: {str(e)}",
                        "activity_id": activity_id,
                    },
                    indent=2,
                ),
            )
        ]


async def handle_get_activity_streams(args: dict) -> list[TextContent]:
    """Get raw time-series stream data for an activity with optional slicing and type filtering."""
    from magma_cycling.config import create_intervals_client

    activity_id = args["activity_id"]
    requested_types = args.get("types")
    start_index = args.get("start_index", 0)
    end_index = args.get("end_index")

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()
            streams = client.get_activity_streams(activity_id)

        if not streams:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": f"No stream data found for activity {activity_id}",
                            "activity_id": activity_id,
                        },
                        indent=2,
                    ),
                )
            ]

        available_stream_types = [s["type"] for s in streams]

        # Filter by requested types
        missing_types = []
        if requested_types:
            available_set = set(available_stream_types)
            missing_types = [t for t in requested_types if t not in available_set]
            streams = [s for s in streams if s["type"] in set(requested_types)]

        # Determine total data points from first stream
        total_data_points = len(streams[0]["data"]) if streams else 0

        # Clamp indices
        start_index = max(0, start_index)
        if end_index is None:
            end_index = total_data_points
        end_index = max(start_index, min(end_index, total_data_points))

        # Slice and compute stats
        result_streams = []
        for stream in streams:
            data = stream["data"][start_index:end_index]
            stats = {}
            if data:
                stats["min"] = min(data)
                stats["max"] = max(data)
                stats["avg"] = round(sum(data) / len(data), 2)
                non_zero = [v for v in data if v != 0]
                stats["non_zero_count"] = len(non_zero)
                stats["non_zero_avg"] = round(sum(non_zero) / len(non_zero), 2) if non_zero else 0
            result_streams.append(
                {
                    "type": stream["type"],
                    "data_points": len(data),
                    "stats": stats,
                    "data": data,
                }
            )

        result = {
            "activity_id": activity_id,
            "total_data_points": total_data_points,
            "slice": {
                "start_index": start_index,
                "end_index": end_index,
                "length": end_index - start_index,
            },
            "available_stream_types": available_stream_types,
            "streams": result_streams,
        }

        if missing_types:
            result["missing_types"] = missing_types

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Failed to get activity streams: {str(e)}",
                        "activity_id": activity_id,
                    },
                    indent=2,
                ),
            )
        ]


async def handle_compare_intervals(args: dict) -> list[TextContent]:
    """Compare interval data across multiple activities to track progression."""
    from magma_cycling.config import create_intervals_client

    NUMERIC_METRICS = {
        "elapsed_time",
        "moving_time",
        "distance",
        "average_watts",
        "weighted_average_watts",
        "min_watts",
        "max_watts",
        "average_heartrate",
        "min_heartrate",
        "max_heartrate",
        "average_cadence",
        "intensity",
        "training_load",
        "decoupling",
        "average_speed",
        "total_elevation_gain",
        "average_torque",
        "min_torque",
        "max_torque",
        "avg_lr_balance",
    }

    activity_ids = args.get("activity_ids")
    name_pattern = args.get("name_pattern")
    weeks_back = args.get("weeks_back", 6)
    label_filter = args.get("label_filter")
    type_filter = args.get("type_filter")
    requested_metrics = args.get("metrics")

    if not activity_ids and not name_pattern:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": "Either 'activity_ids' or 'name_pattern' is required.",
                    },
                    indent=2,
                ),
            )
        ]

    if requested_metrics:
        invalid = [m for m in requested_metrics if m not in NUMERIC_METRICS]
        if invalid:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": f"Invalid metrics: {invalid}",
                            "available_metrics": sorted(NUMERIC_METRICS),
                        },
                        indent=2,
                    ),
                )
            ]

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()

        # Resolve activities
        if activity_ids:
            mode = "explicit"
            resolved = []
            for aid in activity_ids:
                with suppress_stdout_stderr():
                    act = client.get_activity(aid)
                resolved.append(
                    {
                        "id": aid,
                        "name": act.get("name", ""),
                        "date": (act.get("start_date_local", "") or "")[:10],
                    }
                )
        else:
            mode = "search"
            newest = date.today().isoformat()
            oldest = (date.today() - timedelta(weeks=weeks_back)).isoformat()
            with suppress_stdout_stderr():
                all_activities = client.get_activities(oldest=oldest, newest=newest)
            pattern_lower = name_pattern.lower()
            resolved = [
                {
                    "id": a.get("id", ""),
                    "name": a.get("name", ""),
                    "date": (a.get("start_date_local", "") or "")[:10],
                }
                for a in all_activities
                if pattern_lower in (a.get("name", "") or "").lower()
            ]
            resolved.sort(key=lambda x: x["date"])

            if not resolved:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "error": f"No activities matching '{name_pattern}' in the last {weeks_back} weeks.",
                            },
                            indent=2,
                        ),
                    )
                ]

        # Fetch intervals for each activity
        activity_intervals = {}
        for act_info in resolved:
            aid = act_info["id"]
            with suppress_stdout_stderr():
                raw = client.get_activity_intervals(aid)
            activity_intervals[aid] = raw

        # Build metadata
        activity_metadata = {a["id"]: {"name": a["name"], "date": a["date"]} for a in resolved}
        intervals_per_activity = {aid: len(ivs) for aid, ivs in activity_intervals.items()}

        # Filter intervals
        metrics_to_use = set(requested_metrics) if requested_metrics else NUMERIC_METRICS

        filtered_intervals = {}
        for aid, raw_ivs in activity_intervals.items():
            kept = []
            for iv in raw_ivs:
                if (iv.get("elapsed_time") or 0) <= 2:
                    continue
                if type_filter and iv.get("type") != type_filter:
                    continue
                if label_filter and label_filter.lower() not in (iv.get("label", "") or "").lower():
                    continue
                kept.append(iv)
            filtered_intervals[aid] = kept

        # Align by label
        label_groups = defaultdict(lambda: defaultdict(list))
        for aid, ivs in filtered_intervals.items():
            for iv in ivs:
                label = (iv.get("label", "") or "").strip().lower()
                label_groups[label][aid].append(iv)

        # Preserve original label casing
        label_display = {}
        for aid, ivs in filtered_intervals.items():
            for iv in ivs:
                norm = (iv.get("label", "") or "").strip().lower()
                if norm not in label_display:
                    label_display[norm] = (iv.get("label", "") or "").strip()

        # Build comparison
        ordered_ids = [a["id"] for a in resolved]
        comparison = []
        for norm_label in sorted(label_groups.keys()):
            group = label_groups[norm_label]
            activities_data = []
            values_by_metric = defaultdict(list)

            for aid in ordered_ids:
                if aid not in group:
                    activities_data.append(
                        {
                            "activity_id": aid,
                            "date": activity_metadata[aid]["date"],
                            "data": None,
                        }
                    )
                    continue

                ivs = group[aid]
                agg = {}
                for metric in metrics_to_use:
                    vals = [iv[metric] for iv in ivs if metric in iv and iv[metric] is not None]
                    if vals:
                        avg_val = sum(vals) / len(vals)
                        agg[metric] = round(avg_val, 2) if avg_val != int(avg_val) else int(avg_val)

                activities_data.append(
                    {
                        "activity_id": aid,
                        "date": activity_metadata[aid]["date"],
                        "data": agg if agg else None,
                    }
                )

                for metric, val in agg.items():
                    values_by_metric[metric].append(val)

            # Calculate trends
            trends = {}
            for metric, vals in values_by_metric.items():
                if len(vals) >= 2:
                    first = vals[0]
                    last = vals[-1]
                    delta = round(last - first, 2)
                    delta_pct = round((delta / first) * 100, 1) if first != 0 else None
                    avg = round(sum(vals) / len(vals), 2)
                    trends[metric] = {
                        "first": first,
                        "last": last,
                        "delta": delta,
                        "delta_pct": delta_pct,
                        "avg": avg,
                    }

            comparison.append(
                {
                    "label": label_display.get(norm_label, norm_label),
                    "activities": activities_data,
                    "trends": trends,
                }
            )

        result = {
            "mode": mode,
            "activities_compared": len(resolved),
            "activity_ids": ordered_ids,
            "activity_metadata": activity_metadata,
            "intervals_per_activity": intervals_per_activity,
            "filters_applied": {
                "label_filter": label_filter,
                "type_filter": type_filter,
                "metrics": requested_metrics if requested_metrics else "all",
            },
            "comparison": comparison,
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"error": f"Failed to compare intervals: {str(e)}"},
                    indent=2,
                ),
            )
        ]


async def handle_apply_workout_intervals(args: dict) -> list[TextContent]:
    """Apply custom interval boundaries to an Intervals.icu activity."""
    import re

    from magma_cycling.config import create_intervals_client
    from magma_cycling.planning.models import SESSION_ID_PATTERN
    from magma_cycling.workout_parser import (
        compute_intervals,
        load_workout_descriptions,
        parse_workout_text,
    )

    activity_id = args["activity_id"]
    dry_run = args.get("dry_run", True)
    manual_intervals = args.get("intervals")

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()

        # --- Manual mode ---
        if manual_intervals is not None:
            if dry_run:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "mode": "manual",
                                "dry_run": True,
                                "activity_id": activity_id,
                                "intervals_count": len(manual_intervals),
                                "intervals": manual_intervals,
                                "message": "Preview only. Set dry_run=false to apply.",
                            },
                            indent=2,
                        ),
                    )
                ]
            with suppress_stdout_stderr():
                result = client.put_activity_intervals(activity_id, manual_intervals)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "mode": "manual",
                            "dry_run": False,
                            "activity_id": activity_id,
                            "applied": True,
                            "result": result,
                        },
                        indent=2,
                    ),
                )
            ]

        # --- Auto mode ---
        session_id = args.get("session_id")
        if not session_id:
            with suppress_stdout_stderr():
                activity = client.get_activity(activity_id)
            activity_name = activity.get("name", "")
            m = re.search(SESSION_ID_PATTERN, activity_name)
            if not m:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "error": f"Cannot extract session_id from activity name: '{activity_name}'",
                                "hint": "Provide session_id parameter explicitly (e.g. S082-02)",
                            },
                            indent=2,
                        ),
                    )
                ]
            session_id = m.group()

        # Load workout description
        week_id = session_id.split("-")[0]
        descriptions = load_workout_descriptions(week_id)

        workout_text = None
        for name, text in descriptions.items():
            if session_id in name:
                workout_text = text
                break

        if workout_text is None:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": f"No workout found for session {session_id} in {week_id}_workouts.txt",
                            "available_workouts": list(descriptions.keys()),
                        },
                        indent=2,
                    ),
                )
            ]

        # Parse workout
        blocks = parse_workout_text(workout_text)
        if not blocks:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": f"Workout {session_id} is a rest day (no blocks to apply)",
                        },
                        indent=2,
                    ),
                )
            ]

        # Get stream to determine total points
        with suppress_stdout_stderr():
            streams = client.get_activity_streams(activity_id)

        if not streams or not streams[0].get("data"):
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": f"No stream data found for activity {activity_id}",
                        },
                        indent=2,
                    ),
                )
            ]
        total_points = len(streams[0]["data"])

        # Compute intervals
        computed = compute_intervals(blocks, total_points)

        interval_dicts = [
            {
                "type": iv.type,
                "label": iv.label,
                "start_index": iv.start_index,
                "end_index": iv.end_index,
            }
            for iv in computed
        ]

        from magma_cycling.workout_parser import Phase

        main_seconds = sum(b.duration_seconds for b in blocks if b.phase == Phase.MAIN_SET)
        cooldown_seconds = sum(b.duration_seconds for b in blocks if b.phase == Phase.COOLDOWN)
        prescription_seconds = sum(b.duration_seconds for b in blocks)
        warmup_absorbed = total_points - main_seconds - cooldown_seconds

        summary = {
            "mode": "auto",
            "dry_run": dry_run,
            "activity_id": activity_id,
            "session_id": session_id,
            "stream_points": total_points,
            "prescription_seconds": prescription_seconds,
            "warmup_absorbed": warmup_absorbed,
            "intervals_count": len(interval_dicts),
            "intervals": interval_dicts,
        }

        if dry_run:
            summary["message"] = "Preview only. Set dry_run=false to apply."
            return [TextContent(type="text", text=json.dumps(summary, indent=2))]

        with suppress_stdout_stderr():
            result = client.put_activity_intervals(activity_id, interval_dicts)
        summary["applied"] = True
        summary["result"] = result
        return [TextContent(type="text", text=json.dumps(summary, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Failed to apply workout intervals: {str(e)}",
                        "activity_id": activity_id,
                    },
                    indent=2,
                ),
            )
        ]


async def handle_update_remote_session(args: dict) -> list[TextContent]:
    """Update an existing workout event on Intervals.icu with write-back to local planning."""
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
                                    return [
                                        TextContent(
                                            type="text",
                                            text=json.dumps(
                                                {
                                                    "error": "Cannot update completed session",
                                                    "event_id": event_id,
                                                    "session_id": session.session_id,
                                                    "message": f"🛡️ PROTECTION: Session {session.session_id} is COMPLETED",
                                                },
                                                indent=2,
                                            ),
                                        )
                                    ]
                                target_week_id = week_id
                                target_session = session
                                break
                        if target_week_id:
                            break
                    except Exception:
                        continue

            client = create_intervals_client()
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

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"error": f"Update error: {str(e)}", "event_id": event_id},
                    indent=2,
                ),
            )
        ]


async def handle_create_remote_note(args: dict) -> list[TextContent]:
    """Create a NOTE (calendar note) directly on Intervals.icu with write-back to local planning."""
    import re

    from magma_cycling.config import create_intervals_client
    from magma_cycling.planning.control_tower import planning_tower
    from magma_cycling.planning.models import SESSION_ID_PATTERN, Session

    note_date = args["date"]
    name = args["name"]
    description = args["description"]

    ALLOWED_PREFIXES = ["[ANNULÉE]", "[SAUTÉE]", "[REMPLACÉE]"]
    if not any(name.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": False,
                        "error": f"Invalid NOTE name. Name must start with one of: {', '.join(ALLOWED_PREFIXES)}",
                        "provided_name": name,
                        "allowed_prefixes": ALLOWED_PREFIXES,
                    },
                    indent=2,
                ),
            )
        ]

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()

            event_data = {
                "category": "NOTE",
                "name": name,
                "description": description,
                "start_date_local": f"{note_date}T00:00:00",
            }

            created_event = client.create_event(event_data)

            if created_event and "id" in created_event:
                session_id_match = re.search(SESSION_ID_PATTERN, name)
                if session_id_match:
                    session_id = session_id_match.group()
                    week_id = session_id.split("-")[0]

                    try:
                        status_map = {
                            "[ANNULÉE]": "cancelled",
                            "[SAUTÉE]": "skipped",
                            "[REMPLACÉE]": "replaced",
                        }
                        new_status = next(
                            (
                                status
                                for prefix, status in status_map.items()
                                if name.startswith(prefix)
                            ),
                            "cancelled",
                        )

                        with planning_tower.modify_week(
                            week_id,
                            requesting_script="create-remote-note",
                            reason=f"Write-back from NOTE creation: {new_status} session {session_id}",
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
                else:
                    local_update_msg = " (no session_id found in name, local planning not updated)"

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

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Failed to create NOTE: {str(e)}",
                        "date": note_date,
                        "name": name,
                    },
                    indent=2,
                ),
            )
        ]


async def handle_sync_remote_to_local(args: dict) -> list[TextContent]:
    """Sync local planning from Intervals.icu remote events."""
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

            return [
                TextContent(
                    type="text",
                    text=json.dumps(result, indent=2),
                )
            ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": str(e),
                        "week_id": args.get("week_id"),
                    },
                    indent=2,
                ),
            )
        ]


async def handle_backfill_activities(args: dict) -> list[TextContent]:
    """Backfill historical activity data into local planning sessions."""
    with suppress_stdout_stderr():
        import re
        from datetime import datetime

        from magma_cycling.config import create_intervals_client, get_data_config
        from magma_cycling.daily_sync import DailySync
        from magma_cycling.planning.models import SESSION_ID_PATTERN, WeeklyPlan

        # Determine date range
        if "week_id" in args:
            week_id = args["week_id"]

            data_config = get_data_config()
            planning_file = data_config.week_planning_dir / f"week_planning_{week_id}.json"

            if not planning_file.exists():
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": f"Planning file not found for {week_id}"},
                            indent=2,
                        ),
                    )
                ]

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
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "message": f"No activities found for {date_source}",
                            "start_date": str(start_date_val),
                            "end_date": str(end_date_val),
                            "activities_count": 0,
                        },
                        indent=2,
                    ),
                )
            ]

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

        return [
            TextContent(
                type="text",
                text=json.dumps(result, indent=2),
            )
        ]
