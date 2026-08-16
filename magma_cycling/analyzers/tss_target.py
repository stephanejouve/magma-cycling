"""BT-039 : utilitaire de calcul de la cible TSS active pour l'adhérence.

Distinction sémantique entre 2 grandeurs :

- **Cible initiale** (``week["tss_target"]``) : ce qui était planifié en
  début de semaine, avant les aléas. Représente l'intention. Conservée
  telle quelle (jamais modifiée par ce module).
- **Cible active** : cumul des sessions restées à faire (statut
  ``pending``, ``planned``, ``uploaded``, ``in_progress``), après
  annulations (``rest_day``, ``skipped``, ``cancelled``). Représente
  la référence d'adhérence.

Contexte : audit 2026-08-16 (Coach AI + Leader) a mis en évidence que
54 % des semaines depuis mars 2026 avaient une cible surestimée par
inclusion de sessions annulées avec ``tss_planned`` non-nul. 2272 TSS
cumulés fantômes ≈ 7-10 semaines complètes.

Fix côté consommateur d'adhérence (voie A) : cette fonction calcule
la cible active à la volée depuis ``planned_sessions``, sans altérer
le champ stocké ``tss_target``. Substitution ciblée uniquement dans
les 3 consommateurs adhérence rétro (monthly stats, monthly reporting,
weekly analysis handler). Les autres consommateurs (PID, planning
validation, rich profile) continuent d'utiliser la cible initiale
volontairement.
"""

from __future__ import annotations

from typing import Any

#: Statuts considérés comme « annulés » — leurs ``tss_planned`` sont
#: exclus du calcul de la cible active. Les autres statuts (pending,
#: planned, uploaded, in_progress, completed, modified, replaced)
#: contribuent au cumul actif.
CANCELLED_STATUSES: frozenset[str] = frozenset({"rest_day", "skipped", "cancelled"})


def compute_active_tss_target(week: Any) -> int:
    """Retourne le cumul TSS des sessions actives d'une semaine.

    « Actives » = tout statut hors :data:`CANCELLED_STATUSES`. Représente
    la cible réelle d'adhérence après annulations, distincte du champ
    stocké ``week["tss_target"]`` (intention initiale, conservée).

    Args:
        week: Dict issu de JSON (avec clé ``planned_sessions``) ou objet
            :class:`WeeklyPlan` (attribut ``planned_sessions``). La
            fonction gère les 2 formats pour compatibilité entre les
            consommateurs (monthly stats charge en dict, weekly handler
            manipule des modèles).

    Returns:
        Cumul entier des ``tss_planned`` des sessions actives. ``0`` si
        aucune session active (semaine 100 % annulée) — les callers
        d'adhérence doivent protéger la division par zéro avant
        d'afficher un ratio.

    Example:
        >>> week = {"planned_sessions": [
        ...     {"status": "completed", "tss_planned": 50},
        ...     {"status": "rest_day", "tss_planned": 72},
        ...     {"status": "skipped", "tss_planned": 30},
        ...     {"status": "planned", "tss_planned": 40},
        ... ]}
        >>> compute_active_tss_target(week)
        90
    """
    # Support dict et objet — extraire la liste de sessions
    if isinstance(week, dict):
        sessions = week.get("planned_sessions", [])
    else:
        sessions = getattr(week, "planned_sessions", [])

    total = 0
    for session in sessions:
        # Support dict et objet Pydantic — extraire status + tss_planned
        if isinstance(session, dict):
            status = session.get("status")
            tss = session.get("tss_planned", 0) or 0
        else:
            status = getattr(session, "status", None)
            tss = getattr(session, "tss_planned", 0) or 0
        if status in CANCELLED_STATUSES:
            continue
        total += tss
    return total
