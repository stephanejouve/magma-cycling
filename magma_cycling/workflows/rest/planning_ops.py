"""Week planning loading and validation operations."""

from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from magma_cycling.config import get_logger
from magma_cycling.planning.control_tower import planning_tower
from magma_cycling.planning.models import WeeklyPlan

logger = get_logger(__name__)

VALID_STATUSES = [
    "planned",
    "completed",
    "cancelled",
    "rest_day",
    "replaced",
    "skipped",
    "modified",
]
VALID_TYPES = ["END", "INT", "FTP", "SPR", "CLM", "REC", "FOR", "CAD", "TEC", "MIX", "PDC", "TST"]


def load_week_planning(week_id: str, planning_dir: Path | None = None) -> WeeklyPlan:
    """
    Charge la configuration hebdomadaire avec protection Pydantic.

    Migration Note (2026-02-20):
        Fonction migrée vers Control Tower (read-only access).
        - Utilise planning_tower.read_week() au lieu de WeeklyPlan.from_json()
        - Validation automatique par Pydantic
        - Protection anti-shallow copy
        - Type hints pour IntelliSense
        - Backward compatibility: Les appelants doivent accéder via .planned_sessions
        - planning_dir parameter deprecated (Control Tower uses config)

    Args:
        week_id: Identifiant semaine (ex: "S070")
        planning_dir: Répertoire contenant les plannings (DEPRECATED - ignored)

    Returns:
        WeeklyPlan: Instance Pydantic validée avec protection anti-aliasing

    Raises:
        FileNotFoundError: Si fichier planning absent
        ValidationError: Si format JSON invalide ou données incohérentes

    Examples:
        >>> plan = load_week_planning("S080")
        >>> print(f"Week {plan.week_id}: {len(plan.planned_sessions)} sessions")
        >>> for session in plan.planned_sessions:
        ...     print(f"  {session.session_id}: {session.status}")
    """
    if planning_dir is not None:
        logger.warning(
            "planning_dir parameter is deprecated and ignored. "
            "Control Tower uses data repo config."
        )

    try:
        # 🚦 READ-ONLY ACCESS via Control Tower (no backup needed)
        plan = planning_tower.read_week(week_id)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Planning non trouvé pour {week_id}\n"
            f"Créer le fichier ou utiliser le mode standard (sans planning)"
        )
    except ValidationError as e:
        raise ValueError(f"Planning invalide (erreur de validation): {e}") from e

    logger.info(f"Planning chargé: {week_id} ({len(plan.planned_sessions)} sessions)")
    return plan


def validate_week_planning(planning: dict | WeeklyPlan) -> bool:
    """
    Validate structure et cohérence planning hebdomadaire.

    Migration Note (2026-02-08):
        - Accepte maintenant dict OU WeeklyPlan (backward compatibility)
        - Si WeeklyPlan: validation déjà faite par Pydantic, retourne True directement
        - Si dict: validation manuelle (legacy support)

    Checks (pour dict seulement):
    - Champs obligatoires présents
    - Statuts valides
    - Dates cohérentes (semaine 7 jours)
    - Raisons présentes si cancelled
    - Pas de doublons session_id

    Args:
        planning: Dict OU WeeklyPlan du planning à valider

    Returns:
        True si valide, False sinon.

    Examples:
        >>> plan = load_week_planning("S080")  # WeeklyPlan
        >>> validate_week_planning(plan)  # True (déjà validé)
        True

        >>> raw_dict = json.load(open("plan.json"))
        >>> validate_week_planning(raw_dict)  # Validation manuelle
        True
    """
    # ✅ Si c'est déjà un WeeklyPlan, Pydantic l'a déjà validé
    if isinstance(planning, WeeklyPlan):
        logger.debug(f"Planning {planning.week_id} déjà validé par Pydantic")
        return True

    # Fallback: duck-typing check for WeeklyPlan-like objects
    if hasattr(type(planning), "model_fields") and hasattr(planning, "planned_sessions"):
        return True

    # ❌ Legacy: validation manuelle pour dict
    logger.warning("Validation manuelle d'un dict (legacy). Recommandé: utiliser WeeklyPlan")

    # Champs obligatoires
    required_fields = ["week_id", "start_date", "end_date", "planned_sessions"]
    for field in required_fields:
        if field not in planning:
            logger.error(f"Champ obligatoire manquant: {field}")
            return False

    # Valider les sessions
    sessions = planning["planned_sessions"]
    session_ids = set()

    for session in sessions:
        # Champs obligatoires session
        session_required = ["session_id", "date", "type", "name", "status"]
        for field in session_required:
            if field not in session:
                logger.error(f"Session {session.get('session_id', '?')}: champ manquant {field}")
                return False

        # Valider statut
        status = session["status"]
        if status not in VALID_STATUSES:
            logger.error(
                f"Session {session['session_id']}: statut invalide '{status}' "
                f"(valides: {VALID_STATUSES})"
            )
            return False

        # Valider raison pour cancelled
        if status == "cancelled" and "cancellation_reason" not in session:
            logger.error(f"Session {session['session_id']}: raison obligatoire pour cancelled")
            return False

        # Valider raison pour skipped
        if status == "skipped" and "skip_reason" not in session:
            logger.error(f"Session {session['session_id']}: raison obligatoire pour skipped")
            return False

        # Valider type
        session_type = session["type"]
        if session_type not in VALID_TYPES:
            logger.warning(
                f"Session {session['session_id']}: type '{session_type}' non standard "
                f"(standards: {VALID_TYPES})"
            )

        # Vérifier doublons
        sid = session["session_id"]
        if sid in session_ids:
            logger.error(f"Session ID dupliqué: {sid}")
            return False
        session_ids.add(sid)

        # Valider format date
        try:
            datetime.strptime(session["date"], "%Y-%m-%d")
        except ValueError:
            logger.error(f"Session {sid}: format date invalide (attendu YYYY-MM-DD)")
            return False

    # Valider cohérence dates semaine
    try:
        start = datetime.strptime(planning["start_date"], "%Y-%m-%d")
        end = datetime.strptime(planning["end_date"], "%Y-%m-%d")
        delta = (end - start).days

        if delta != 6:
            logger.warning(f"Semaine non standard: {delta + 1} jours (attendu 7)")
    except ValueError as e:
        logger.error(f"Format date invalide: {e}")
        return False

    logger.info("✓ Planning validé")
    return True
