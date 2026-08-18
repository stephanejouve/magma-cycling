"""Analysis and backup handlers."""

from __future__ import annotations

import json
import re
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from magma_cycling._mcp._utils import mcp_response, suppress_stdout_stderr
from magma_cycling.utils.safe_io import safe_read_text, safe_write_text

if TYPE_CHECKING:
    from mcp.types import TextContent

__all__ = [
    "handle_validate_week_consistency",
    "handle_get_recommendations",
    "handle_analyze_session_adherence",
    "handle_get_training_statistics",
    "handle_export_week_to_json",
    "handle_restore_week_from_backup",
    "handle_analyze_training_patterns",
    "handle_get_coach_analysis",
    "handle_validate_local_remote_sync",
    "handle_pid_daily_evaluation",
    "handle_check_workout_adherence",
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

        return mcp_response(result)

    except Exception as e:
        error = {"error": f"Validation error: {str(e)}", "week_id": week_id}
        return mcp_response(error)


async def handle_get_recommendations(args: dict) -> list[TextContent]:
    """Get PID and Peaks system recommendations for a week."""
    week_id = args["week_id"]

    try:
        with suppress_stdout_stderr():
            # Load recommendations from project docs if available
            rec_file = Path("project-docs") / "recommendations" / f"{week_id}_recommendations.json"

            if rec_file.exists():
                recommendations = json.loads(safe_read_text(rec_file))
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

        return mcp_response(result)

    except Exception as e:
        error = {"error": f"Failed to get recommendations: {str(e)}", "week_id": week_id}
        return mcp_response(error)


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
                error = {"error": f"Session {session_id} not found in week {week_id}"}
                return mcp_response(error)

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

        return mcp_response(result)

    except Exception as e:
        error = {
            "error": f"Adherence analysis error: {str(e)}",
            "session_id": session_id,
            "activity_id": activity_id,
        }
        return mcp_response(error)


async def handle_get_training_statistics(args: dict) -> list[TextContent]:
    """Get aggregated training statistics for a date range.

    BT-042 : ``include_adherence=True`` (défaut ``False``) ajoute la dimension
    adhérence (cible initiale / active / réalisé / drift / tss_source_map)
    en scannant les plannings hebdo dans la plage. Défaut absent = zéro
    surcoût pour les usages actuels (charge réelle + wellness seulement).
    """
    from magma_cycling.config import create_intervals_client

    start_date = args["start_date"]
    end_date = args["end_date"]
    include_adherence = bool(args.get("include_adherence", False))

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()

            # Get activities and wellness data
            activities = client.get_activities(oldest=start_date, newest=end_date)
            wellness = client.get_wellness(oldest=start_date, newest=end_date)

            # Calculate statistics
            total_activities = len(activities)
            # BT-045 + BT-047 : ``.get(..., 0)`` ne protège pas contre valeur
            # ``None`` explicite renvoyée par Intervals.icu (activités sans
            # données puissance/HR/GPS). ``or 0`` uniforme sur toute la
            # surface des accumulators (TSS int, moving_time/distance float)
            # évite ``TypeError: int/float + NoneType``.
            total_tss = sum((a.get("icu_training_load") or 0) for a in activities)
            total_duration = sum((a.get("moving_time") or 0) for a in activities) / 3600  # Hours
            total_distance = sum((a.get("distance") or 0) for a in activities) / 1000  # Km

            avg_tss = total_tss / total_activities if total_activities > 0 else 0

            # BT-050 : distribution d'intensité en TEMPS par zone via
            # streams `watts` (remplace le comptage précédent d'activités
            # par IF global — faux et trompeur, cf issue #490). Coût
            # réseau : 1 requête `get_activity_streams` par activité,
            # amorti par le cache read-through local (BT-025). FTP
            # résolue par date d'activité via table de paliers historique
            # (interdit d'utiliser FTP courante sur data passée).
            from magma_cycling.analyzers.intensity_zones import (
                intensity_distribution_from_activities,
            )

            intensity_distribution = intensity_distribution_from_activities(activities, client)

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

            # BT-042 : dimension adhérence optionnelle
            if include_adherence:
                result["adherence"] = _compute_adherence_for_range(
                    start_date=start_date,
                    end_date=end_date,
                    activities=activities,
                )

        return mcp_response(result)

    except Exception as e:
        error = {
            "error": f"Failed to get training statistics: {str(e)}",
            "start_date": start_date,
            "end_date": end_date,
        }
        return mcp_response(error)


def _compute_adherence_for_range(start_date: str, end_date: str, activities: list[dict]) -> dict:
    """Compute adherence dimension for a date range (BT-042).

    Agrège cible initiale/active/réalisé + drift + tss_source_map sur
    les weekly plannings intersectant la plage ``[start_date, end_date]``.

    Args:
        start_date: ``YYYY-MM-DD`` inclusif.
        end_date: ``YYYY-MM-DD`` inclusif.
        activities: liste des activités Intervals de la plage (pour
            construire ``actual_tss_map`` id → icu_training_load).

    Returns:
        Dict avec :

        - ``tss_target_initial`` (int | None) : cumul ``week["tss_target"]``
          stocké (intention pré-annulations). ``None`` (BT-053) si au moins
          une semaine dans la plage a ``tss_target=0`` alors que sa somme
          active est >0 (désynchro de stockage — semaine non finalisée
          via handshake, cf BT-051).
        - ``tss_target_active`` (int) : cumul via
          :func:`compute_active_tss_target` (post-annulations). Toujours
          fiable (dérivé sessions).
        - ``tss_realized`` (int) : cumul sur sessions ``completed``/
          ``modified`` — utilise Intervals ``icu_training_load`` si
          match par ``intervals_id``, sinon fallback ``tss_planned``.
        - ``adherence_rate`` (float | None) : realized / active × 100.
          ``None`` si active=0 (semaine 100 % annulée) — protection
          division par zéro, rendu doit afficher « — ».
        - ``drift_initial_to_active_abs`` (int | None) : ``initial - active``
          en valeur absolue. ``None`` (BT-053) quand ``initial`` est
          désynchronisé (voir ci-dessus) — ne pas afficher plutôt que
          répondre faux (mieux vaut ne pas répondre que répondre faux).
        - ``initial_unreliable_reason`` (str, optionnel, BT-053) : présent
          uniquement si ``initial`` et ``drift`` sont ``None``. Explique
          la cause côté renderer / consommateur IA.
        - ``tss_source_map`` (dict) : ``{"intervals": [...],
          "planned_fallback": [...]}`` — liste ``session_id`` par origine
          du TSS réalisé. Le fallback signale « TSS depuis planifié, pas
          Intervals » — motif substitution silencieuse à surveiller.
        - ``weeks_in_range`` (list) : liste des ``week_id`` scannés
          (contrat traçabilité).
    """
    import json
    from datetime import date as _date

    from magma_cycling.analyzers.tss_target import compute_active_tss_target
    from magma_cycling.config import get_data_config

    range_start = _date.fromisoformat(start_date)
    range_end = _date.fromisoformat(end_date)

    # BT-048 : matching planning ⇔ activité passe par ``paired_event_id``,
    # PAS par ``activity.id``. Intervals distingue :
    #   - ``activity.id`` (ex ``"i162682746"``) : la course réalisée
    #   - ``activity.paired_event_id`` (ex ``119167963``) : l'event
    #     calendrier planifié qu'elle satisfait
    # Le planning stocke ``intervals_id = paired_event_id`` (event ID).
    # Indexer par ``activity.id`` produit un mismatch systématique →
    # tautologie adherence=100% (bug prod BT-039 monthly + BT-042 include
    # depuis 2 mois, masqué par fixtures test utilisant des id == intervals_id
    # scenarios impossibles en réel). Cf. patterns éprouvés
    # ``workflows/sync/activity_tracker.py:67`` et
    # ``workflows/sync/activity_detection.py:96``.
    actual_tss_map: dict[str, float] = {}
    for act in activities:
        peid = act.get("paired_event_id")
        tss = act.get("icu_training_load")
        # peid=None → activité non-planifiée (Zwift libre, etc.) → hors
        # adherence, la session planifiée tombera en fallback.
        if peid is not None and tss is not None:
            actual_tss_map[f"i{peid}"] = tss

    # Glob weekly plannings — filtre par intersection [start_date, end_date]
    data_config = get_data_config()
    planning_dir = data_config.data_repo_path / "data" / "week_planning"
    if not planning_dir.exists():
        # Fallback : legacy layout without data/ subdir
        planning_dir = data_config.data_repo_path / "week_planning"

    total_initial = 0
    total_active = 0
    total_realized = 0
    tss_source_map: dict[str, list[str]] = {"intervals": [], "planned_fallback": []}
    weeks_in_range: list[str] = []
    desync_detected = False  # BT-053

    if planning_dir.exists():
        for path in sorted(planning_dir.glob("week_planning_S*.json")):
            try:
                with open(path, encoding="utf-8") as fh:
                    week = json.load(fh)
            except (OSError, json.JSONDecodeError):
                continue
            # Intersect plage — semaine incluse si start_date de la semaine
            # ≤ end_date de la plage ET end_date de la semaine ≥ start_date
            try:
                week_start = _date.fromisoformat(week.get("start_date", ""))
                week_end = _date.fromisoformat(week.get("end_date", ""))
            except ValueError:
                continue
            if week_end < range_start or week_start > range_end:
                continue

            weeks_in_range.append(week.get("week_id", "?"))
            week_active = compute_active_tss_target(week)
            total_active += week_active
            # BT-053 v2 (2026-08-18, Coach AI) : retrait du fallback
            # opportuniste sur legacy ``tss_target > 0``. Position durcie :
            # SEUL ``tss_target_initial`` (renseigné via handshake
            # ``finalize-week-planning`` BT-051) est fiable. Sinon → drift
            # non exploitable, masquer plutôt que produire un écart entre
            # deux sources non comparables (règle « mieux vaut ne pas
            # répondre que répondre faux »).
            # Rétrocompat : ces semaines n'auront simplement pas de drift
            # dans les rapports post-BT-053v2 tant qu'elles ne sont pas
            # finalisées. Position Coach AI « ne rien reconstruire »
            # respectée strictement.
            week_initial = week.get("tss_target_initial")
            if week_initial is None:
                desync_detected = True
            else:
                total_initial += week_initial

            for session in week.get("planned_sessions", []):
                status = session.get("status")
                if status not in ("completed", "modified"):
                    continue
                sid = session.get("session_id", "?")
                intervals_id = session.get("intervals_id")
                key = f"i{intervals_id}" if intervals_id is not None else None
                if key and key in actual_tss_map:
                    total_realized += actual_tss_map[key]
                    tss_source_map["intervals"].append(sid)
                else:
                    total_realized += session.get("tss_planned", 0) or 0
                    tss_source_map["planned_fallback"].append(sid)

    adherence_rate: float | None = None
    if total_active > 0:
        adherence_rate = round(total_realized / total_active * 100, 1)

    # BT-053 : mieux vaut ne pas répondre que répondre faux (règle P2
    # partagée). Si au moins une semaine dans la plage a un ``tss_target``
    # stocké désynchronisé (=0 alors que sessions actives >0), le cumul
    # ``initial`` est structurellement sous-estimé → ``drift`` mesurerait
    # une désynchro de stockage plutôt qu'une dérive de plan. On masque
    # les deux champs avec ``None`` + drapeau ``initial_unreliable_reason``.
    # ``adherence_rate`` reste calculable (basé sur ``total_active`` fiable
    # dérivé sessions).
    if desync_detected:
        return {
            "tss_target_initial": None,
            "tss_target_active": total_active,
            "tss_realized": round(total_realized, 1),
            "adherence_rate": adherence_rate,
            "drift_initial_to_active_abs": None,
            "initial_unreliable_reason": (
                "tss_target stored=0 while sessions active >0 on at least "
                "one week in range — semaine(s) non finalisée(s) via handshake "
                "(BT-051 en cours). Ni le initial cumulé ni le drift ne sont "
                "significatifs. Voir issue #491."
            ),
            "tss_source_map": tss_source_map,
            "weeks_in_range": weeks_in_range,
        }
    return {
        "tss_target_initial": total_initial,
        "tss_target_active": total_active,
        "tss_realized": round(total_realized, 1),
        "adherence_rate": adherence_rate,
        "drift_initial_to_active_abs": abs(total_initial - total_active),
        "tss_source_map": tss_source_map,
        "weeks_in_range": weeks_in_range,
    }


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
            safe_write_text(output_file, json.dumps(plan_dict, indent=2))

            result = {
                "success": True,
                "week_id": week_id,
                "backup_path": str(output_file),
                "message": f"✅ Week {week_id} exported to {output_file}",
            }

        return mcp_response(result)

    except Exception as e:
        error = {"error": f"Export error: {str(e)}", "week_id": week_id}
        return mcp_response(error)


async def handle_restore_week_from_backup(args: dict) -> list[TextContent]:
    """Restore week planning from JSON backup file."""
    from datetime import date as date_type

    from magma_cycling.planning.control_tower import planning_tower
    from magma_cycling.planning.models import Session, WeeklyPlan

    week_id = args["week_id"]
    backup_path = args["backup_path"]
    confirm = args.get("confirm", False)

    if not confirm:
        error = {
            "error": "Restore requires explicit confirmation",
            "week_id": week_id,
            "message": "Set confirm=true to proceed with restore",
            "warning": "This will OVERWRITE current planning",
        }
        return mcp_response(error)

    try:
        with suppress_stdout_stderr():
            # Read backup file
            backup_file = Path(backup_path)
            if not backup_file.exists():
                error = {"error": f"Backup file not found: {backup_path}"}
                return mcp_response(error)

            backup_data = json.loads(safe_read_text(backup_file))

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

        return mcp_response(result)

    except Exception as e:
        error = {"error": f"Restore error: {str(e)}", "week_id": week_id}
        return mcp_response(error)


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
                            result["recommendations"] = json.loads(safe_read_text(rec_file))

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

        return mcp_response(result)

    except Exception as e:
        error = {
            "error": f"Analysis error: {str(e)}",
            "week_id": week_id,
            "depth": depth,
        }
        return mcp_response(error)


# ---------------------------------------------------------------------------
# Coach analysis history lookup
# ---------------------------------------------------------------------------

SECTION_MAP = {
    "metrics_pre": "Métriques Pré-séance",
    "execution": "Exécution",
    "technique": "Exécution Technique",
    "load": "Charge d'Entraînement",
    "validation": "Validation Objectifs",
    "attention": "Points d'Attention",
    "recommendations": "Recommandations Progression",
    "metrics_post": "Métriques Post-séance",
    "full": None,
}


def _parse_analysis_entry(entry_text: str) -> dict:
    """Parse a single analysis entry into structured fields."""
    lines = entry_text.strip().splitlines()
    if not lines:
        return {}

    # Extract title from first line (### TITLE)
    title_line = lines[0].lstrip("#").strip()
    activity_name = title_line

    # Extract ID, Date from header lines
    activity_id = ""
    date_str = ""
    for line in lines[1:5]:
        id_match = re.match(r"ID\s*:\s*(.+)", line.strip())
        if id_match:
            activity_id = id_match.group(1).strip()
        date_match = re.match(r"Date\s*:\s*(.+)", line.strip())
        if date_match:
            date_str = date_match.group(1).strip()

    # Extract week_id from activity_name (e.g. S084-04-END-... → S084)
    week_id = ""
    wid_match = re.match(r"(S\d{3})", activity_name)
    if wid_match:
        week_id = wid_match.group(1)

    # Parse #### sections
    sections: dict[str, str] = {}
    current_section = None
    current_lines: list[str] = []

    for line in lines:
        section_match = re.match(r"####\s+(.+)", line)
        if section_match:
            # Save previous section
            if current_section:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = section_match.group(1).strip()
            current_lines = []
        elif current_section is not None:
            current_lines.append(line)

    # Save last section
    if current_section:
        sections[current_section] = "\n".join(current_lines).strip()

    # Map French section titles to API keys
    mapped_sections: dict[str, str] = {}
    for key, french_title in SECTION_MAP.items():
        if french_title and french_title in sections:
            mapped_sections[key] = sections[french_title]

    return {
        "activity_name": activity_name,
        "activity_id": activity_id,
        "date": date_str,
        "week_id": week_id,
        "sections": mapped_sections,
        "content": entry_text.strip(),
    }


def _search_analyses(
    content: str,
    activity_id: str | None = None,
    session_id: str | None = None,
    date: str | None = None,
) -> list[str]:
    """Search analysis entries matching the given criteria."""
    # Split on ### headers — handle file starting with ### (no leading \n)
    raw_entries = re.split(r"(?:^|\n)(?=### )", content)
    entries = [e.strip() for e in raw_entries if e.strip()]

    results = []
    for entry in entries:
        if activity_id:
            pattern = rf"ID\s*:\s*{re.escape(activity_id)}\s*$"
            if not re.search(pattern, entry, re.MULTILINE):
                continue

        if session_id:
            # Word-boundary match to avoid S084-04 matching S084-040
            pattern = rf"^###\s+{re.escape(session_id)}\b"
            if not re.search(pattern, entry, re.MULTILINE):
                continue

        if date:
            # Convert YYYY-MM-DD to DD/MM/YYYY for matching
            try:
                parts = date.split("-")
                date_fr = f"{parts[2]}/{parts[1]}/{parts[0]}"
                pattern = rf"Date\s*:\s*{re.escape(date_fr)}\s*$"
                if not re.search(pattern, entry, re.MULTILINE):
                    continue
            except (IndexError, ValueError):
                continue

        results.append(entry)

    return results


def _search_daily_reports(
    reports_dir: Path,
    activity_id: str | None = None,
    session_id: str | None = None,
    date: str | None = None,
) -> list[str]:
    r"""Search daily report files for AI analyses as fallback.

    Daily reports use a different format than workouts-history.md::

        ### ACTIVITY_NAME
        - **ID**: activity_id
        ...
        #### 🤖 Analyse AI
        [analysis content]

    Returns analysis entries reconstituted in the workouts-history.md
    header format (``### NAME\nID : xxx\nDate : xxx``) so they can be
    parsed by ``_parse_analysis_entry``.
    """
    if not reports_dir.exists():
        return []

    # Determine which files to scan
    if date:
        # Target specific file
        target = reports_dir / f"daily_report_{date}.md"
        report_files = [target] if target.exists() else []
    else:
        # Scan recent files (last 30 days)
        from datetime import date as date_cls
        from datetime import timedelta as td

        today = date_cls.today()
        report_files = []
        for i in range(30):
            d = today - td(days=i)
            f = reports_dir / f"daily_report_{d.isoformat()}.md"
            if f.exists():
                report_files.append(f)

    results = []
    for report_file in report_files:
        content = report_file.read_text(encoding="utf-8")

        # Extract report date from filename (daily_report_YYYY-MM-DD.md)
        file_date_match = re.search(r"daily_report_(\d{4}-\d{2}-\d{2})\.md", report_file.name)
        if not file_date_match:
            continue
        file_date_iso = file_date_match.group(1)
        parts = file_date_iso.split("-")
        file_date_fr = f"{parts[2]}/{parts[1]}/{parts[0]}"

        # Split on ### headers (activity entries in daily report)
        raw_entries = re.split(r"(?:^|\n)(?=### )", content)

        for entry in raw_entries:
            entry = entry.strip()
            if not entry.startswith("### "):
                continue

            # Skip non-activity headings (e.g. report title)
            if entry.startswith("### ") and "Rapport" in entry.split("\n")[0]:
                continue

            # Extract activity name from ### line
            name_line = entry.split("\n")[0]
            act_name = name_line.lstrip("#").strip()

            # Extract ID from - **ID**: value
            id_match = re.search(r"-\s*\*\*ID\*\*\s*:\s*(\S+)", entry)
            act_id = id_match.group(1) if id_match else ""

            # Filter by activity_id
            if activity_id and act_id != activity_id:
                continue

            # Filter by session_id (prefix match on activity name)
            if session_id and not re.match(rf"{re.escape(session_id)}\b", act_name):
                continue

            # Extract AI analysis section
            ai_match = re.search(r"####\s*🤖\s*Analyse AI\s*\n(.*)", entry, re.DOTALL)
            if not ai_match:
                continue

            analysis_body = ai_match.group(1).strip()
            if not analysis_body:
                continue

            # Upgrade ##### back to #### (reverse the normalization done for reports)
            analysis_body = re.sub(r"^##### ", "#### ", analysis_body, flags=re.MULTILINE)

            # Reconstitute in workouts-history.md format
            reconstituted = (
                f"### {act_name}\n"
                f"ID : {act_id}\n"
                f"Date : {file_date_fr}\n\n"
                f"{analysis_body}"
            )
            results.append(reconstituted)

    return results


async def handle_get_coach_analysis(args: dict) -> list[TextContent]:
    """Retrieve coach AI analysis from workouts-history.md."""
    activity_id = args.get("activity_id")
    session_id = args.get("session_id")
    date = args.get("date")
    section = args.get("section", "full")

    # Validate: at least one search parameter required
    if not any([activity_id, session_id, date]):
        return mcp_response(
            {
                "error": "At least one search parameter required: activity_id, session_id, or date",
            }
        )

    # Validate section parameter
    if section not in SECTION_MAP:
        return mcp_response(
            {
                "error": f"Invalid section: {section}",
                "valid_sections": list(SECTION_MAP.keys()),
            }
        )

    try:
        from magma_cycling.config import get_data_config

        config = get_data_config()
        history_path = config.workouts_history_path

        # Search in workouts-history.md
        matched_entries = []
        if history_path.exists():
            content = history_path.read_text(encoding="utf-8")
            if content.strip():
                matched_entries = _search_analyses(
                    content,
                    activity_id=activity_id,
                    session_id=session_id,
                    date=date,
                )

        # Fallback: search in daily reports if nothing found
        source = "workouts_history"
        if not matched_entries:
            reports_dir = config.data_repo_path / "daily-reports"
            matched_entries = _search_daily_reports(
                reports_dir,
                activity_id=activity_id,
                session_id=session_id,
                date=date,
            )
            if matched_entries:
                source = "daily_report"

        # Parse and format results
        analyses = []
        for entry_text in matched_entries:
            parsed = _parse_analysis_entry(entry_text)
            if not parsed:
                continue

            if section != "full":
                # Return only the requested section
                section_content = parsed["sections"].get(section, "")
                analyses.append(
                    {
                        "activity_name": parsed["activity_name"],
                        "activity_id": parsed["activity_id"],
                        "date": parsed["date"],
                        "week_id": parsed["week_id"],
                        "sections": {section: section_content} if section_content else {},
                    }
                )
            else:
                analyses.append(parsed)

        count = len(analyses)
        message = f"{count} analysis found" if count == 1 else f"{count} analyses found"

        return mcp_response(
            {
                "status": "success",
                "analyses": analyses,
                "count": count,
                "source": source,
                "message": message,
            }
        )

    except Exception as e:
        return mcp_response({"error": f"Failed to retrieve coach analysis: {str(e)}"})


# ---------------------------------------------------------------------------
# Local ↔ Remote sync validator
# ---------------------------------------------------------------------------


def _parse_event_name(name: str) -> dict | None:
    """Parse an Intervals.icu event name using WORKOUT_NAME_REGEX.

    Returns dict with session_id, session_type, workout_name, version
    or None if the name doesn't match.
    """
    from magma_cycling.planning.models import WORKOUT_NAME_REGEX

    match = WORKOUT_NAME_REGEX.search(name)
    if not match:
        return None
    return {
        "session_id": match.group(1),
        "session_type": match.group(2),
        "workout_name": match.group(3),
        "version": match.group(4),
    }


async def handle_validate_local_remote_sync(args: dict) -> list[TextContent]:
    """Compare local planning vs remote Intervals.icu events to detect drift."""
    from magma_cycling._mcp._utils import SYNCABLE_STATUSES
    from magma_cycling.config import create_intervals_client
    from magma_cycling.planning.control_tower import planning_tower
    from magma_cycling.utils.event_sync import calculate_description_hash

    week_id = args["week_id"]
    include_description_check = args.get("include_description_check", False)

    try:
        with suppress_stdout_stderr():
            plan = planning_tower.read_week(week_id)

            client = create_intervals_client()
            remote_events = client.get_events(
                oldest=str(plan.start_date),
                newest=str(plan.end_date),
            )

            # Index all remote events by id (for intervals_id lookup).
            # BT-020: no category filter — orphan detection must cover
            # WORKOUT + NOTE + INJURED, otherwise NOTE de repos et INJURED
            # de kiné restent invisibles au validateur.
            remote_by_id: dict[int, dict] = {}
            for event in remote_events:
                eid = event.get("id")
                if eid is not None:
                    remote_by_id[eid] = event

            discrepancies: list[dict] = []
            dangling_references: list[dict] = []
            linked_remote_ids: set[int] = set()

            # Check each session that has an intervals_id
            for session in plan.planned_sessions:
                if session.intervals_id is None:
                    continue

                linked_remote_ids.add(session.intervals_id)
                remote_event = remote_by_id.get(session.intervals_id)

                if remote_event is None:
                    # BT-020: dangling reference — intervals_id local pointe
                    # vers un event absent (supprimé remote, hors fenêtre,
                    # ou jamais créé). Catégorie dédiée pour ne pas être
                    # confondu avec un vrai discrepancy structurel (name,
                    # type, date, description). La remédiation diffère :
                    # re-sync pour recréer l'event, ou effacer l'intervals_id
                    # local si l'event est parti intentionnellement.
                    dangling_references.append(
                        {
                            "session_id": session.session_id,
                            "intervals_id": session.intervals_id,
                            "date": str(session.session_date),
                        }
                    )
                    continue

                # Parse the remote event name
                parsed = _parse_event_name(remote_event.get("name", ""))
                if parsed is None:
                    # Unparseable remote name — skip structured checks
                    continue

                # 1. SESSION_ID_MISMATCH (detects swaps)
                if parsed["session_id"] != session.session_id:
                    discrepancies.append(
                        {
                            "session_id": session.session_id,
                            "intervals_id": session.intervals_id,
                            "type": "SESSION_ID_MISMATCH",
                            "local": session.session_id,
                            "remote": parsed["session_id"],
                            "severity": "HIGH",
                        }
                    )

                # 2. NAME_MISMATCH
                if parsed["workout_name"] != session.name:
                    discrepancies.append(
                        {
                            "session_id": session.session_id,
                            "intervals_id": session.intervals_id,
                            "type": "NAME_MISMATCH",
                            "local": session.name,
                            "remote": parsed["workout_name"],
                            "severity": "HIGH",
                        }
                    )

                # 3. TYPE_MISMATCH
                if parsed["session_type"] != session.session_type:
                    discrepancies.append(
                        {
                            "session_id": session.session_id,
                            "intervals_id": session.intervals_id,
                            "type": "TYPE_MISMATCH",
                            "local": session.session_type,
                            "remote": parsed["session_type"],
                            "severity": "HIGH",
                        }
                    )

                # 4. DATE_MISMATCH
                remote_date_str = remote_event.get("start_date_local", "")[:10]
                if remote_date_str and remote_date_str != str(session.session_date):
                    discrepancies.append(
                        {
                            "session_id": session.session_id,
                            "intervals_id": session.intervals_id,
                            "type": "DATE_MISMATCH",
                            "local": str(session.session_date),
                            "remote": remote_date_str,
                            "severity": "HIGH",
                        }
                    )

                # 5. DESCRIPTION_MISMATCH (opt-in, off by default)
                if include_description_check:
                    remote_desc = remote_event.get("description", "") or ""
                    local_desc = session.description or ""
                    if local_desc and remote_desc:
                        local_hash = calculate_description_hash(local_desc)
                        remote_hash = calculate_description_hash(remote_desc)
                        if local_hash != remote_hash:
                            discrepancies.append(
                                {
                                    "session_id": session.session_id,
                                    "intervals_id": session.intervals_id,
                                    "type": "DESCRIPTION_MISMATCH",
                                    "local": local_hash,
                                    "remote": remote_hash,
                                    "severity": "LOW",
                                }
                            )

            # Orphaned remote: events not linked to any local session.
            # BT-020: scan toutes catégories (WORKOUT, NOTE, INJURED, ...).
            # Le champ "category" est exposé pour orienter la remédiation
            # (delete-remote-event fait le job pour toutes catégories).
            orphaned_remote = []
            for event in remote_events:
                eid = event.get("id")
                if eid is None or eid in linked_remote_ids:
                    continue
                parsed = _parse_event_name(event.get("name", ""))
                orphaned_remote.append(
                    {
                        "intervals_id": eid,
                        "category": event.get("category"),
                        "name": event.get("name", ""),
                        "date": event.get("start_date_local", "")[:10],
                        "parsed": parsed,
                    }
                )

            # Unlinked local: sessions that should be synced but have no intervals_id
            unlinked_local = []
            for session in plan.planned_sessions:
                if session.intervals_id is None and session.status in SYNCABLE_STATUSES:
                    unlinked_local.append(
                        {
                            "session_id": session.session_id,
                            "name": session.name,
                            "status": session.status,
                            "date": str(session.session_date),
                        }
                    )

            sessions_checked = sum(1 for s in plan.planned_sessions if s.intervals_id is not None)
            status = (
                "DRIFT_DETECTED"
                if discrepancies or orphaned_remote or dangling_references
                else "IN_SYNC"
            )

            result = {
                "week_id": week_id,
                "status": status,
                "sessions_checked": sessions_checked,
                "discrepancies": discrepancies,
                "orphaned_remote": orphaned_remote,
                "unlinked_local": unlinked_local,
                "dangling_references": dangling_references,
            }

        return mcp_response(result)

    except FileNotFoundError:
        return mcp_response(
            {
                "error": f"Planning not found for {week_id}",
                "week_id": week_id,
            }
        )
    except Exception as e:
        return mcp_response(
            {
                "error": f"Sync validation error: {str(e)}",
                "week_id": week_id,
            }
        )


async def handle_pid_daily_evaluation(args: dict) -> list[TextContent]:
    """Run the PID training intelligence pipeline.

    Wraps the legacy CLI ``pid-daily-evaluation`` (PIDDailyEvaluator) to
    expose its capability via MCP. Two modes :

    - ``daily`` (default) : collect cycle metrics + create learnings + monitor
      CTL/Peaks + check FTP test opportunity. Idempotent on a given day.
    - ``cycle`` : recalibrate PID with the measured FTP at end of training
      cycle. Requires ``measured_ftp``. One-shot per cycle.

    Updates ``~/data/intelligence.json`` and appends to
    ``~/data/monitoring/pid_evaluation.jsonl`` (skipped in dry_run).
    """
    mode = args.get("mode", "daily")
    days_back = args.get("days_back", 7)
    measured_ftp = args.get("measured_ftp")
    cycle_weeks = args.get("cycle_weeks", 6)
    dry_run = args.get("dry_run", False)

    if mode == "cycle" and measured_ftp is None:
        return mcp_response(
            {
                "status": "error",
                "message": (
                    "measured_ftp is required when mode='cycle' "
                    "(measured FTP from end-of-cycle test, in W)."
                ),
            }
        )

    with suppress_stdout_stderr():
        from magma_cycling.scripts.pid_daily_evaluation import PIDDailyEvaluator

        evaluator = PIDDailyEvaluator(dry_run=dry_run)

        if mode == "cycle":
            result = evaluator.run_cycle_evaluation(
                measured_ftp=measured_ftp,
                cycle_duration_weeks=cycle_weeks,
            )
        else:
            result = evaluator.run_daily_evaluation(days_back=days_back)

    payload = {
        "mode": mode,
        "dry_run": dry_run,
        "status": result.get("status", "UNKNOWN"),
    }

    # Surface key fields without dumping the whole result blob (which can
    # contain heavy nested metrics). The consumer can request more specific
    # data via dedicated tools (analyze-training-patterns, get-recommendations).
    if "test_recommendation" in result:
        payload["test_recommendation"] = result["test_recommendation"]
    if "ctl_monitoring" in result:
        payload["ctl_monitoring"] = result["ctl_monitoring"]
    if "pid_correction" in result:
        payload["pid_correction"] = result["pid_correction"]
    if "metrics" in result:
        # Métriques cycle compactes : pas tout le détail, juste le top-level
        m = result["metrics"]
        if isinstance(m, dict):
            payload["metrics_summary"] = {
                k: v for k, v in m.items() if isinstance(v, (int, float, str, bool, type(None)))
            }

    return mcp_response(payload)


async def handle_check_workout_adherence(args: dict) -> list[TextContent]:
    """Daily-batch adherence check (legacy CLI check-workout-adherence).

    Wraps the legacy WorkoutAdherenceChecker (from scripts/monitoring/) to
    expose its capability via MCP. Different from analyze-session-adherence
    which is per-session — this one is a batch check of a day or a week.

    Three modes :
    - ``day`` (default) : check single date (defaults to today).
    - ``week`` : check Monday→Sunday of the date's week.
    - ``weekly_alert`` : R10 weekly adherence with alerts if <85%.
    """
    from datetime import datetime as _dt

    from scripts.monitoring.check_workout_adherence import WorkoutAdherenceChecker

    mode = args.get("mode", "day")
    date_str = args.get("date")
    dry_run = args.get("dry_run", False)

    if date_str:
        check_date = _dt.strptime(date_str, "%Y-%m-%d")
    else:
        check_date = _dt.now()

    with suppress_stdout_stderr():
        checker = WorkoutAdherenceChecker(dry_run=dry_run)

        if mode == "weekly_alert":
            result = checker.check_weekly_adherence_and_alert()
        elif mode == "week":
            week_start = check_date - timedelta(days=check_date.weekday())
            result = checker.check_week(week_start)
        else:
            result = checker.check_date(check_date)

    payload = {
        "mode": mode,
        "date": check_date.strftime("%Y-%m-%d"),
        "dry_run": dry_run,
        "status": "SUCCESS",
    }

    # Surface only scalar/dict-of-scalars from the checker result to keep
    # response compact. Heavy nested data (full session lists) stays out.
    if isinstance(result, dict):
        payload["adherence"] = {
            k: v
            for k, v in result.items()
            if isinstance(v, (int, float, str, bool, type(None), list))
        }

    return mcp_response(payload)
