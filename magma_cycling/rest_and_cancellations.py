#!/usr/bin/env python3
"""
Track rest days and canceled sessions with impact analysis.

Façade module — delegates to workflows/rest/ sub-modules:
    - veto_check: Pre-session VETO check (P0 CRITICAL)
    - planning_ops: Week planning loading & validation + constants
    - markdown_entries: Markdown generation for rest/skipped/cancelled
    - reconciliation: Planned vs actual reconciliation

Re-exports all public functions for backward compatibility.

Author: Stéphane Jouve
Created: 2024-10-XX
Updated: 2025-12-26 (Standardization Prompt 3 Priority 2)

Metadata:
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: I
    Status: Production
    Priority: P2
    Version: v2
"""

from pathlib import Path

from magma_cycling.config import get_logger
from magma_cycling.workflows.rest.markdown_entries import (
    generate_cancelled_session_entry,
    generate_rest_day_entry,
    generate_skipped_session_entry,
)
from magma_cycling.workflows.rest.planning_ops import (
    VALID_STATUSES,
    VALID_TYPES,
    load_week_planning,
    validate_week_planning,
)
from magma_cycling.workflows.rest.reconciliation import reconcile_planned_vs_actual
from magma_cycling.workflows.rest.veto_check import check_pre_session_veto

logger = get_logger(__name__)

# Re-exports for backward compatibility
__all__ = [
    "check_pre_session_veto",
    "VALID_STATUSES",
    "VALID_TYPES",
    "load_week_planning",
    "validate_week_planning",
    "generate_rest_day_entry",
    "generate_skipped_session_entry",
    "generate_cancelled_session_entry",
    "reconcile_planned_vs_actual",
    "process_week_with_rest_handling",
]


# ============================================================================
# WORKFLOW PRINCIPAL AVEC GESTION REPOS
# ============================================================================


def process_week_with_rest_handling(
    week_id: str,
    start_date: str,
    end_date: str,
    planning_dir: Path | None = None,
    output_file: Path | None = None,
) -> dict:
    """
    Workflow complet avec gestion repos/annulations (Sprint R9.B Phase 2).

    Process:
    1. Charger planning semaine (week_planning.json)
    2. Récupérer activités Intervals.icu
    3. Réconcilier planifié vs réalisé
    4. Générer entrées markdown:
       - Séances exécutées : analyse standard
       - Repos planifiés : template repos
       - Séances annulées : template annulation
    5. Insérer dans workouts-history.md (ordre chronologique)
    6. Logger rapport réconciliation

    Args:
        week_id: Ex "S070"
        start_date: "2025-12-02"
        end_date: "2025-12-08"
        planning_dir: Répertoire plannings (optionnel)
        output_file: Fichier sortie markdown (optionnel)

    Returns:
        Dict avec résumé réconciliation et chemins fichiers générés

    Note:
        Credentials are loaded automatically via create_intervals_client().
    """
    from magma_cycling.config import create_intervals_client

    logger.info(f"\n{'=' * 70}")
    logger.info(f"WORKFLOW SEMAINE {week_id} AVEC GESTION REPOS/ANNULATIONS")
    logger.info(f"{'=' * 70}\n")

    # 1. Charger planning
    try:
        planning = load_week_planning(week_id, planning_dir)
    except FileNotFoundError as e:
        logger.warning(f"Planning non trouvé : {e}")
        logger.warning("Fallback mode standard (sans planning)")
        return {"status": "fallback", "message": "Planning non trouvé, utiliser workflow standard"}

    # 2. Récupérer activités Intervals.icu (centralized client creation)
    api = create_intervals_client()
    activities = api.get_activities(oldest=start_date, newest=end_date)
    logger.info(f"Activités récupérées : {len(activities)}")

    # 3. Réconcilier
    reconciliation = reconcile_planned_vs_actual(planning, activities)

    # 4. Générer entrées markdown
    markdown_entries = []

    # Traiter par ordre chronologique
    # Note: planning is a WeeklyPlan object, access via .planned_sessions
    all_sessions = sorted(planning.planned_sessions, key=lambda x: x.session_date)

    for session in all_sessions:
        status = session.status

        # Convert Session object to dict for compatibility with markdown generators
        # (markdown generators expect dict format)
        session_dict = {
            "session_id": session.session_id,
            "date": str(session.session_date),
            "type": session.session_type,
            "name": session.name,
            "status": session.status,
            "tss_planned": session.tss_planned,
            "duration_planned": session.duration_min * 60,  # Convert to seconds
            "version": session.version,
            "rest_reason": getattr(session, "rest_reason", None),
            "cancellation_reason": getattr(session, "cancellation_reason", None),
            "skip_reason": getattr(session, "skip_reason", None),
            "physiological_notes": getattr(session, "physiological_notes", ""),
        }

        # Récupérer métriques (simulation pour l'exemple)
        # En production, récupérer depuis API Intervals.icu wellness
        metrics_pre = {"ctl": 50, "atl": 35, "tsb": 15, "sleep_duration": "7h00", "sleep_score": 75}
        metrics_post = {"ctl": 50, "atl": 35, "tsb": 15}

        if status == "rest_day":
            entry = generate_rest_day_entry(
                session_data=session_dict,
                metrics_pre=metrics_pre,
                metrics_post=metrics_post,
                athlete_feedback={
                    "sleep_duration": "6h12min",
                    "sleep_score": 78,
                    "hrv": 66,
                    "resting_hr": 44,
                },
            )
            markdown_entries.append(entry)
            logger.info(f"✓ Repos : {session.session_id}")

        elif status == "cancelled":
            entry = generate_cancelled_session_entry(
                session_data=session_dict,
                metrics_pre=metrics_pre,
                reason=session.cancellation_reason or "Non spécifiée",
            )
            markdown_entries.append(entry)
            logger.info(f"✗ Annulée : {session.session_id}")

        elif status == "skipped":
            # Nouvelle gestion séances sautées
            entry = generate_skipped_session_entry(
                session_data=session_dict,
                metrics_pre=metrics_pre,
                reason=session.skip_reason or "Séance planifiée non exécutée",
            )
            markdown_entries.append(entry)
            logger.info(f"⏭️  Sautée : {session.session_id}")

        elif status == "completed":
            # Chercher dans les matched
            matched = next(
                (
                    m
                    for m in reconciliation["matched"]
                    if m["session"].session_id == session.session_id
                ),
                None,
            )
            if matched:
                logger.info(f"✓ Exécutée : {session.session_id}")
                # Ici intégration avec analyse standard (à implémenter)
                # Pour l'instant, on log juste
            else:
                logger.warning(
                    f"⚠ Session {session.session_id} marquée completed "
                    f"mais pas d'activité trouvée"
                )

    # 5. Écrire dans fichier si spécifié
    if output_file:
        with open(output_file, "a", encoding="utf-8") as f:
            for entry in markdown_entries:
                f.write(entry + "\n")
        logger.info(f"\n✓ Entrées écrites dans {output_file}")

    # 6. Rapport final
    logger.info(f"\n{'=' * 70}")
    logger.info(f"RAPPORT FINAL - {week_id}")
    logger.info(f"{'=' * 70}")

    # Calculer TSS
    # Note: m["session"] is a Session object (from WeeklyPlan.planned_sessions)
    tss_completed = sum(m["session"].tss_planned for m in reconciliation["matched"])
    tss_planned = sum(s.tss_planned for s in all_sessions if s.status != "rest_day")
    tss_completion = (tss_completed / tss_planned * 100) if tss_planned > 0 else 0

    logger.info(f"\nSessions planifiées : {len(all_sessions)}")
    logger.info(f"Sessions exécutées : {len(reconciliation['matched'])}")
    logger.info(f"Repos planifiés : {len(reconciliation['rest_days'])}")
    logger.info(f"Séances annulées : {len(reconciliation['cancelled'])}")
    logger.info(f"Séances sautées : {len(reconciliation['skipped'])}")
    logger.info(
        f"\nTSS Semaine : {tss_completed} réalisé / {tss_planned} planifié ({tss_completion:.0f}%)"
    )
    logger.info(f"{'=' * 70}\n")

    return {
        "status": "success",
        "week_id": week_id,
        "reconciliation": reconciliation,
        "tss_completed": tss_completed,
        "tss_planned": tss_planned,
        "markdown_entries_count": len(markdown_entries),
    }
