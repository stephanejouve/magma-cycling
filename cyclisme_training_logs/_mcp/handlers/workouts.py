"""Workout handlers."""

import json

from mcp.types import TextContent

from cyclisme_training_logs._mcp._utils import suppress_stdout_stderr

__all__ = [
    "handle_get_workout",
    "handle_validate_workout",
]


async def handle_get_workout(args: dict) -> list[TextContent]:
    """Get workout file content for a session."""
    from cyclisme_training_logs.config import get_data_config

    session_id = args["session_id"]

    try:
        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            # Get workouts directory
            config = get_data_config()
            workouts_dir = config.data_repo_path / "workouts"

            # Find workout file(s) for this session
            # Pattern: {session_id}-*.{zwo,mrc,erg}
            workout_files = list(workouts_dir.glob(f"{session_id}-*"))

            if not workout_files:
                # No .zwo file — fall back to session description from planning
                from cyclisme_training_logs.planning.control_tower import planning_tower

                week_id = session_id[:4]  # "S082-02" → "S082"
                session_def = None
                try:
                    plan = planning_tower.read_week(week_id)
                    session_def = next(
                        (s for s in plan.planned_sessions if s.session_id == session_id),
                        None,
                    )
                except Exception:
                    pass

                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "found": False,
                                "session_id": session_id,
                                "structured_file": None,
                                "message": "No structured workout file (.zwo) found. "
                                "Session is defined via text description in the planning.",
                                "session_definition": (
                                    {
                                        "name": session_def.name if session_def else None,
                                        "type": (session_def.session_type if session_def else None),
                                        "description": (
                                            session_def.description if session_def else None
                                        ),
                                        "tss_planned": (
                                            session_def.tss_planned if session_def else None
                                        ),
                                        "duration_min": (
                                            session_def.duration_min if session_def else None
                                        ),
                                    }
                                    if session_def
                                    else None
                                ),
                            },
                            indent=2,
                        ),
                    )
                ]

            # If multiple files, return the first one (or could return all)
            workout_file = workout_files[0]

            # Read workout content
            content = workout_file.read_text(encoding="utf-8")

        result = {
            "status": "success",
            "session_id": session_id,
            "filename": workout_file.name,
            "extension": workout_file.suffix[1:],  # Remove leading dot
            "content": content,
            "message": f"Workout retrieved: {workout_file.name}",
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Error retrieving workout: {str(e)}"}, indent=2),
            )
        ]


async def handle_validate_workout(args: dict) -> list[TextContent]:
    """Validate Intervals.icu workout format."""
    from cyclisme_training_logs.intervals_format_validator import IntervalsFormatValidator

    workout_text = args["workout_text"]
    auto_fix = args.get("auto_fix", False)

    try:
        # Suppress all output to prevent JSON protocol pollution
        with suppress_stdout_stderr():
            validator = IntervalsFormatValidator()
            is_valid, errors, warnings = validator.validate_workout(workout_text)

            result = {
                "valid": is_valid,
                "errors": errors,
                "warnings": warnings,
            }

            # Si auto_fix demandé et qu'il y a des warnings
            if auto_fix and (errors or warnings):
                corrected_text = validator.fix_repetition_format(workout_text)

                # Revalider le texte corrigé
                is_valid_after, errors_after, warnings_after = validator.validate_workout(
                    corrected_text
                )

                result["auto_fixed"] = True
                result["corrected_workout"] = corrected_text
                result["valid_after_fix"] = is_valid_after
                result["errors_after_fix"] = errors_after
                result["warnings_after_fix"] = warnings_after

                if is_valid_after:
                    result["message"] = "Workout corrected and validated successfully"
                else:
                    result["message"] = (
                        "Some errors remain after auto-fix (manual correction needed)"
                    )
            else:
                result["auto_fixed"] = False
                if is_valid:
                    result["message"] = "Workout format is valid"
                else:
                    result["message"] = (
                        "Workout format has errors (use auto_fix:true to attempt automatic correction)"
                    )

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
                text=json.dumps({"error": f"Validation error: {str(e)}"}, indent=2),
            )
        ]
