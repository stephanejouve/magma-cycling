"""Reconciliation of planned sessions vs actual Intervals.icu activities."""

from typing import Any

from magma_cycling.config import get_logger
from magma_cycling.planning.models import WeeklyPlan

logger = get_logger(__name__)


def _get_session_field(session, field: str):
    """Get field from Session object or dict."""
    from magma_cycling.planning.models import Session

    if isinstance(session, Session):
        # Map field names: dict key → Session attribute
        field_map = {"date": "session_date", "type": "session_type"}
        attr_name = field_map.get(field, field)
        return getattr(session, attr_name)
    return session[field]


def _set_session_field(session, field: str, value):
    """Set field on Session object or dict."""
    from magma_cycling.planning.models import Session

    if isinstance(session, Session):
        field_map = {"date": "session_date", "type": "session_type"}
        attr_name = field_map.get(field, field)
        setattr(session, attr_name, value)
    else:
        session[field] = value


def reconcile_planned_vs_actual(
    week_planning: WeeklyPlan | dict, intervals_activities: list[dict]
) -> dict[str, list]:
    """
    Compare planning hebdomadaire vs activités réelles Intervals.icu.

    Args:
        week_planning: Planning semaine (WeeklyPlan ou dict legacy)
        intervals_activities: Activités récupérées API

    Returns:
        Dict avec:
        - 'matched': Sessions planifiées + exécutées
        - 'rest_days': Repos planifiés
        - 'cancelled': Séances annulées
        - 'unplanned': Activités non planifiées.
    """
    result: dict[str, list[Any]] = {
        "matched": [],
        "rest_days": [],
        "cancelled": [],
        "skipped": [],
        "unplanned": [],
    }

    # Normaliser accès (support WeeklyPlan et dict)
    if isinstance(week_planning, WeeklyPlan):
        week_id = week_planning.week_id
        planned_sessions = week_planning.planned_sessions
    else:
        week_id = week_planning["week_id"]
        planned_sessions = week_planning["planned_sessions"]

    # Index activités par date
    activities_by_date: dict[str, list[dict[str, Any]]] = {}
    for activity in intervals_activities:
        date = activity["start_date_local"][:10]  # YYYY-MM-DD
        if date not in activities_by_date:
            activities_by_date[date] = []
        activities_by_date[date].append(activity)

    # Traiter chaque session planifiée
    planned_dates = set()
    for session in planned_sessions:
        session_date = _get_session_field(session, "date")
        planned_dates.add(session_date)
        status = _get_session_field(session, "status")

        if status == "rest_day":
            result["rest_days"].append(session)

        elif status == "cancelled":
            result["cancelled"].append(session)

        elif status == "skipped":
            result["skipped"].append(session)

        elif status in ["completed", "replaced"]:
            # Chercher activité correspondante
            if session_date in activities_by_date:
                # Trouver la meilleure correspondance
                matched_activity = None
                for activity in activities_by_date[session_date]:
                    # Heuristique : comparer noms ou IDs
                    activity_name = activity.get("name", "").upper()
                    session_id = _get_session_field(session, "session_id").upper()
                    session_name = _get_session_field(session, "name").upper()

                    if session_id in activity_name or session_name in activity_name:
                        matched_activity = activity
                        break

                # Si pas de match par nom, prendre la première du jour
                if not matched_activity and activities_by_date[session_date]:
                    matched_activity = activities_by_date[session_date][0]

                if matched_activity:
                    result["matched"].append({"session": session, "activity": matched_activity})
                    # Retirer de la liste pour détecter non planifiées
                    activities_by_date[session_date].remove(matched_activity)
            else:
                # Planifiée comme completed mais pas d'activité
                # Traiter comme skipped plutôt que cancelled
                logger.warning(
                    f"Session {_get_session_field(session, 'session_id')} marquée completed "
                    f"mais aucune activité trouvée le {session_date} "
                    f"→ Reclassée comme SKIPPED"
                )
                # Marquer comme sautée avec contexte (modification directe pour persistence)
                _set_session_field(
                    session, "skip_reason", "Planifiée completed mais activité introuvable"
                )
                _set_session_field(session, "status", "skipped")
                result["skipped"].append(session)

    # Activités restantes = non planifiées
    for _, activities in activities_by_date.items():
        for activity in activities:
            # Toute activité restante est non planifiée
            result["unplanned"].append(activity)

    # Log résumé
    logger.info("=" * 70)
    logger.info(f"Réconciliation {week_id}")
    logger.info("=" * 70)
    logger.info(f"Sessions planifiées : {len(planned_sessions)}")
    logger.info(f"Sessions exécutées : {len(result['matched'])}")
    logger.info(f"Repos planifiés : {len(result['rest_days'])}")
    logger.info(f"Séances annulées : {len(result['cancelled'])}")
    logger.info(f"Séances sautées : {len(result['skipped'])}")
    logger.info(f"Activités non planifiées : {len(result['unplanned'])}")
    logger.info("=" * 70)

    return result
