"""Analysis and backup handlers."""

import json
from datetime import timedelta
from pathlib import Path

from mcp.types import TextContent

from magma_cycling._mcp._utils import suppress_stdout_stderr

__all__ = [
    "handle_validate_week_consistency",
    "handle_get_recommendations",
    "handle_analyze_session_adherence",
    "handle_get_training_statistics",
    "handle_export_week_to_json",
    "handle_restore_week_from_backup",
    "handle_analyze_training_patterns",
]


async def handle_validate_week_consistency(args: dict) -> list[TextContent]:
    """Validate week planning consistency."""
    from magma_cycling.planning.control_tower import planning_tower

    week_id = args["week_id"]

    try:
        with suppress_stdout_stderr():
            plan = planning_tower.read_week(week_id)

            errors = []
            warnings = []

            # Check for date conflicts (multiple sessions on same day without a/b suffix)
            dates_seen = {}
            for session in plan.planned_sessions:
                date_str = str(session.session_date)
                if date_str in dates_seen:
                    # Check if both have proper a/b suffixes
                    prev_session = dates_seen[date_str]
                    if not (
                        session.session_id.endswith(("a", "b"))
                        and prev_session.session_id.endswith(("a", "b"))
                    ):
                        errors.append(
                            f"Date conflict: {date_str} has multiple sessions without proper a/b suffix"
                        )
                dates_seen[date_str] = session

            # Check TSS coherence (not too high for a single day)
            for session in plan.planned_sessions:
                if session.tss_planned and session.tss_planned > 300:
                    warnings.append(
                        f"{session.session_id}: Very high TSS ({session.tss_planned}) - verify if intentional"
                    )

            # Check for empty descriptions
            for session in plan.planned_sessions:
                if not session.description or session.description.strip() == "":
                    errors.append(f"{session.session_id}: Empty workout description")

            # Check week TSS total
            total_tss = sum(
                s.tss_planned or 0 for s in plan.planned_sessions if s.status != "cancelled"
            )
            if total_tss > 800:
                warnings.append(f"Very high weekly TSS ({total_tss}) - verify training load")
            elif total_tss < 200:
                warnings.append(f"Low weekly TSS ({total_tss}) - is this a recovery week?")

            result = {
                "week_id": week_id,
                "valid": len(errors) == 0,
                "total_sessions": len(plan.planned_sessions),
                "total_tss": total_tss,
                "errors": errors,
                "warnings": warnings,
                "message": (
                    "✅ Week planning is valid"
                    if len(errors) == 0
                    else "❌ Week planning has errors"
                ),
            }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"error": f"Validation error: {str(e)}", "week_id": week_id},
                    indent=2,
                ),
            )
        ]


async def handle_get_recommendations(args: dict) -> list[TextContent]:
    """Get PID and Peaks system recommendations for a week."""
    week_id = args["week_id"]

    try:
        with suppress_stdout_stderr():
            # Load recommendations from project docs if available
            rec_file = Path("project-docs") / "recommendations" / f"{week_id}_recommendations.json"

            if rec_file.exists():
                recommendations = json.loads(rec_file.read_text())
                result = {
                    "week_id": week_id,
                    "found": True,
                    "recommendations": recommendations,
                }
            else:
                # Try to find in planning notes
                from magma_cycling.planning.control_tower import planning_tower

                plan = planning_tower.read_week(week_id)

                result = {
                    "week_id": week_id,
                    "found": False,
                    "message": f"No recommendations file generated yet for {week_id}. "
                    "Run PID evaluation or end-of-week workflow to generate recommendations.",
                    "planning_notes": plan.notes if hasattr(plan, "notes") else None,
                }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"error": f"Failed to get recommendations: {str(e)}", "week_id": week_id},
                    indent=2,
                ),
            )
        ]


async def handle_analyze_session_adherence(args: dict) -> list[TextContent]:
    """Analyze adherence between planned session and completed activity."""
    from magma_cycling.config import create_intervals_client
    from magma_cycling.planning.control_tower import planning_tower

    session_id = args["session_id"]
    activity_id = args["activity_id"]

    try:
        with suppress_stdout_stderr():
            # Get planned session
            week_id = "-".join(session_id.split("-")[:1])  # Extract S081 from S081-04
            plan = planning_tower.read_week(week_id)

            planned_session = None
            for session in plan.planned_sessions:
                if session.session_id == session_id:
                    planned_session = session
                    break

            if not planned_session:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": f"Session {session_id} not found in week {week_id}"},
                            indent=2,
                        ),
                    )
                ]

            # Get completed activity
            client = create_intervals_client()
            activity = client.get_activity(activity_id)

            # Calculate adherence metrics
            planned_tss = planned_session.tss_planned or 0
            actual_tss = activity.get("icu_training_load", 0)
            tss_adherence = (actual_tss / planned_tss * 100) if planned_tss > 0 else 0

            planned_duration = planned_session.duration_min or 0
            actual_duration = activity.get("moving_time", 0) / 60  # Convert to minutes
            duration_adherence = (
                (actual_duration / planned_duration * 100) if planned_duration > 0 else 0
            )

            # Determine adherence quality
            if 90 <= tss_adherence <= 110:
                adherence_quality = "excellent"
            elif 80 <= tss_adherence <= 120:
                adherence_quality = "good"
            elif 70 <= tss_adherence <= 130:
                adherence_quality = "moderate"
            else:
                adherence_quality = "poor"

            result = {
                "session_id": session_id,
                "activity_id": activity_id,
                "planned": {
                    "tss": planned_tss,
                    "duration_minutes": planned_duration,
                    "description": planned_session.description[:100],
                },
                "actual": {
                    "tss": actual_tss,
                    "duration_minutes": round(actual_duration, 1),
                    "if": activity.get("icu_intensity"),
                    "average_watts": activity.get("average_watts"),
                },
                "adherence": {
                    "tss_percent": round(tss_adherence, 1),
                    "duration_percent": round(duration_adherence, 1),
                    "quality": adherence_quality,
                },
                "message": f"Adherence: {adherence_quality} (TSS: {tss_adherence:.1f}%, Duration: {duration_adherence:.1f}%)",
            }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Adherence analysis error: {str(e)}",
                        "session_id": session_id,
                        "activity_id": activity_id,
                    },
                    indent=2,
                ),
            )
        ]


async def handle_get_training_statistics(args: dict) -> list[TextContent]:
    """Get aggregated training statistics for a date range."""
    from magma_cycling.config import create_intervals_client

    start_date = args["start_date"]
    end_date = args["end_date"]

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()

            # Get activities and wellness data
            activities = client.get_activities(oldest=start_date, newest=end_date)
            wellness = client.get_wellness(oldest=start_date, newest=end_date)

            # Calculate statistics
            total_activities = len(activities)
            total_tss = sum(a.get("icu_training_load", 0) for a in activities)
            total_duration = sum(a.get("moving_time", 0) for a in activities) / 3600  # Hours
            total_distance = sum(a.get("distance", 0) for a in activities) / 1000  # Km

            avg_tss = total_tss / total_activities if total_activities > 0 else 0

            # Intensity distribution (Z1-Z5)
            intensity_distribution = {
                "z1": sum(1 for a in activities if (a.get("icu_intensity") or 0) < 0.55),
                "z2": sum(1 for a in activities if 0.55 <= (a.get("icu_intensity") or 0) < 0.75),
                "z3": sum(1 for a in activities if 0.75 <= (a.get("icu_intensity") or 0) < 0.85),
                "z4": sum(1 for a in activities if 0.85 <= (a.get("icu_intensity") or 0) < 0.95),
                "z5": sum(1 for a in activities if (a.get("icu_intensity") or 0) >= 0.95),
            }

            # CTL progression
            ctl_start = wellness[0].get("ctl") if wellness else None
            ctl_end = wellness[-1].get("ctl") if wellness else None
            ctl_change = (ctl_end - ctl_start) if (ctl_start and ctl_end) else None

            result = {
                "period": {"start": start_date, "end": end_date},
                "summary": {
                    "total_activities": total_activities,
                    "total_tss": round(total_tss, 1),
                    "total_duration_hours": round(total_duration, 1),
                    "total_distance_km": round(total_distance, 1),
                    "average_tss_per_session": round(avg_tss, 1),
                },
                "intensity_distribution": intensity_distribution,
                "fitness": {
                    "ctl_start": round(ctl_start, 1) if ctl_start else None,
                    "ctl_end": round(ctl_end, 1) if ctl_end else None,
                    "ctl_change": round(ctl_change, 1) if ctl_change else None,
                },
            }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Failed to get training statistics: {str(e)}",
                        "start_date": start_date,
                        "end_date": end_date,
                    },
                    indent=2,
                ),
            )
        ]


async def handle_export_week_to_json(args: dict) -> list[TextContent]:
    """Export week planning to JSON file for backup."""
    from magma_cycling.planning.control_tower import planning_tower

    week_id = args["week_id"]
    output_path = args.get("output_path", f"/tmp/{week_id}_backup.json")

    try:
        with suppress_stdout_stderr():
            plan = planning_tower.read_week(week_id)

            # Convert to dict
            plan_dict = {
                "week_id": plan.week_id,
                "start_date": str(plan.start_date),
                "end_date": str(plan.end_date),
                "planned_sessions": [
                    {
                        "session_id": s.session_id,
                        "name": s.name,
                        "session_date": str(s.session_date),
                        "category": s.session_type,
                        "status": s.status,
                        "planned_tss": s.tss_planned,
                        "planned_duration": s.duration_min,
                        "description": s.description,
                        "intervals_id": s.intervals_id,
                    }
                    for s in plan.planned_sessions
                ],
            }

            # Write to file
            output_file = Path(output_path)
            output_file.write_text(json.dumps(plan_dict, indent=2))

            result = {
                "success": True,
                "week_id": week_id,
                "backup_path": str(output_file),
                "message": f"✅ Week {week_id} exported to {output_file}",
            }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"error": f"Export error: {str(e)}", "week_id": week_id},
                    indent=2,
                ),
            )
        ]


async def handle_restore_week_from_backup(args: dict) -> list[TextContent]:
    """Restore week planning from JSON backup file."""
    from datetime import date as date_type

    from magma_cycling.planning.control_tower import planning_tower
    from magma_cycling.planning.models import Session, WeeklyPlan

    week_id = args["week_id"]
    backup_path = args["backup_path"]
    confirm = args.get("confirm", False)

    if not confirm:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": "Restore requires explicit confirmation",
                        "week_id": week_id,
                        "message": "Set confirm=true to proceed with restore",
                        "warning": "This will OVERWRITE current planning",
                    },
                    indent=2,
                ),
            )
        ]

    try:
        with suppress_stdout_stderr():
            # Read backup file
            backup_file = Path(backup_path)
            if not backup_file.exists():
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": f"Backup file not found: {backup_path}"},
                            indent=2,
                        ),
                    )
                ]

            backup_data = json.loads(backup_file.read_text())

            # Reconstruct WeeklyPlan
            sessions = [
                Session(
                    session_id=s["session_id"],
                    name=s["name"],
                    session_date=date_type.fromisoformat(s["session_date"]),
                    session_type=s.get("category", s.get("session_type", "END")),
                    status=s["status"],
                    tss_planned=s.get("planned_tss", 0),
                    duration_min=s.get("planned_duration", 0),
                    description=s["description"],
                    intervals_id=s.get("intervals_id"),
                )
                for s in backup_data["planned_sessions"]
            ]

            plan = WeeklyPlan(
                week_id=backup_data["week_id"],
                start_date=date_type.fromisoformat(backup_data["start_date"]),
                end_date=date_type.fromisoformat(backup_data["end_date"]),
                planned_sessions=sessions,
            )

            # Save via Control Tower
            def restore_plan(existing_plan):
                return plan

            planning_tower.modify_week(
                week_id=week_id,
                modification_function=restore_plan,
                requesting_script="restore-week-from-backup MCP tool",
                reason=f"Restored from backup: {backup_path}",
            )

            result = {
                "success": True,
                "week_id": week_id,
                "restored_sessions": len(sessions),
                "message": f"✅ Week {week_id} restored from {backup_file.name}",
            }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"error": f"Restore error: {str(e)}", "week_id": week_id},
                    indent=2,
                ),
            )
        ]


async def handle_analyze_training_patterns(args: dict) -> list[TextContent]:
    """META TOOL: Load all relevant data for comprehensive AI coach analysis."""
    from magma_cycling.config import create_intervals_client
    from magma_cycling.planning.control_tower import planning_tower

    week_id = args["week_id"]
    depth = args.get("depth", "standard")
    include_recommendations = args.get("include_recommendations", True)

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()

            # 1. Load current week planning
            current_plan = planning_tower.read_week(week_id)

            # 2. Load activities for the week
            activities_data = []
            for session in current_plan.planned_sessions:
                if session.status == "completed" and session.intervals_id:
                    try:
                        # Try to find the paired activity
                        events = client.get_events(
                            oldest=str(session.session_date),
                            newest=str(session.session_date),
                        )
                        for event in events:
                            if event.get("id") == session.intervals_id and event.get(
                                "paired_activity_id"
                            ):
                                activity = client.get_activity(event["paired_activity_id"])
                                activities_data.append(
                                    {
                                        "session_id": session.session_id,
                                        "activity_id": event["paired_activity_id"],
                                        "planned_tss": session.tss_planned,
                                        "actual_tss": activity.get("icu_training_load"),
                                        "actual_if": activity.get("icu_intensity"),
                                        "actual_duration": activity.get("moving_time", 0) / 60,
                                        "date": str(session.session_date),
                                    }
                                )
                    except Exception:
                        pass

            # 3. Load wellness data for the week
            wellness_data = client.get_wellness(
                oldest=str(current_plan.start_date),
                newest=str(current_plan.end_date),
            )

            # 4. Calculate week statistics
            completed_sessions = [
                s for s in current_plan.planned_sessions if s.status == "completed"
            ]
            planned_sessions = [s for s in current_plan.planned_sessions if s.status == "planned"]
            cancelled_sessions = [
                s for s in current_plan.planned_sessions if s.status == "cancelled"
            ]

            planned_tss = sum(
                s.tss_planned or 0 for s in current_plan.planned_sessions if s.status != "cancelled"
            )
            actual_tss = sum(a["actual_tss"] or 0 for a in activities_data)

            compliance_rate = (
                (len(completed_sessions) / len(current_plan.planned_sessions) * 100)
                if current_plan.planned_sessions
                else 0
            )

            # Base result structure
            result = {
                "week_id": week_id,
                "period": {
                    "start": str(current_plan.start_date),
                    "end": str(current_plan.end_date),
                },
                "planning": {
                    "total_sessions": len(current_plan.planned_sessions),
                    "completed": len(completed_sessions),
                    "planned": len(planned_sessions),
                    "cancelled": len(cancelled_sessions),
                    "planned_tss": planned_tss,
                    "actual_tss": actual_tss,
                    "tss_adherence_percent": (
                        round(actual_tss / planned_tss * 100, 1) if planned_tss > 0 else 0
                    ),
                    "compliance_rate_percent": round(compliance_rate, 1),
                },
                "sessions": [
                    {
                        "session_id": s.session_id,
                        "name": s.name,
                        "date": str(s.session_date),
                        "category": s.session_type,
                        "status": s.status,
                        "planned_tss": s.tss_planned,
                        "planned_duration": s.duration_min,
                        "description": s.description[:100] if s.description else "",
                        "intervals_id": s.intervals_id,
                    }
                    for s in current_plan.planned_sessions
                ],
                "activities": activities_data,
                "wellness": (
                    [
                        {
                            "date": w.get("id"),
                            "ctl": w.get("ctl"),
                            "atl": w.get("atl"),
                            "tsb": w.get("tsb"),
                            "ramp_rate": w.get("ramp_rate"),
                        }
                        for w in wellness_data
                    ]
                    if wellness_data
                    else []
                ),
            }

            # 5. Add previous week context for 'standard' and 'comprehensive'
            if depth in ["standard", "comprehensive"]:
                try:
                    prev_week_num = int(week_id[1:]) - 1
                    prev_week_id = f"S{prev_week_num:03d}"
                    prev_plan = planning_tower.read_week(prev_week_id)

                    prev_completed = [
                        s for s in prev_plan.planned_sessions if s.status == "completed"
                    ]
                    prev_tss = sum(s.tss_planned or 0 for s in prev_completed)

                    result["previous_week"] = {
                        "week_id": prev_week_id,
                        "completed_sessions": len(prev_completed),
                        "total_tss": prev_tss,
                    }
                except Exception:
                    result["previous_week"] = None

            # 6. Add comprehensive context
            if depth == "comprehensive":
                try:
                    # Load recommendations if available
                    if include_recommendations:
                        rec_file = (
                            Path("project-docs")
                            / "recommendations"
                            / f"{week_id}_recommendations.json"
                        )
                        if rec_file.exists():
                            result["recommendations"] = json.loads(rec_file.read_text())

                    # Add athlete profile
                    athlete = client.get_athlete()
                    result["athlete_profile"] = {
                        "ftp": athlete.get("ftp"),
                        "weight": athlete.get("weight"),
                        "ctl": athlete.get("ctl"),
                        "atl": athlete.get("atl"),
                    }

                    # Add last 4 weeks CTL trend
                    four_weeks_ago = str(current_plan.start_date - timedelta(days=28))
                    historical_wellness = client.get_wellness(
                        oldest=four_weeks_ago, newest=str(current_plan.end_date)
                    )
                    if historical_wellness:
                        result["ctl_trend"] = [
                            {"date": w.get("id"), "ctl": w.get("ctl")}
                            for w in historical_wellness[-28:]  # Last 4 weeks
                        ]
                except Exception as e:
                    result["comprehensive_data_warning"] = (
                        f"Some comprehensive data unavailable: {str(e)}"
                    )

            result["analysis_depth"] = depth
            result["message"] = f"✅ Loaded {depth} analysis data for {week_id}"

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Analysis error: {str(e)}",
                        "week_id": week_id,
                        "depth": depth,
                    },
                    indent=2,
                ),
            )
        ]
