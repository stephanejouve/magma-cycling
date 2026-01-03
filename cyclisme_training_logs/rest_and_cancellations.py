#!/usr/bin/env python3
"""
Track rest days and canceled sessions with impact analysis.
Suivi jours de repos et séances annulées avec analyse impact sur métriques
forme (CTL/ATL/TSB). Documentation raisons cancellation et recommandations
adaptations planning.

Examples:
    Log rest day::

        from cyclisme_training_logs.rest_and_cancellations import log_rest

        # Logger repos programmé
        log_rest(
            date="2025-01-12",
            reason="Recovery week",
            planned=True
        )

    Log canceled session::

        # Logger séance annulée
        log_cancellation(
            date="2025-01-10",
            session_id="S073-04",
            reason="Fatigue excessive",
            reschedule=True
        )

    Analyze impact on metrics::

        # Calculer impact sur TSB
        impact = analyze_rest_impact(
            rest_dates=["2025-01-12", "2025-01-13"],
            current_ctl=65,
            current_atl=58
        )

        print(f"TSB après repos: {impact['tsb_after']}")

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

import json
import logging
from datetime import datetime
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTES
# ============================================================================

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


# ============================================================================
# PRE-SESSION VETO CHECK (Sprint R2.1 - P0 CRITICAL)
# ============================================================================


def check_pre_session_veto(
    wellness_data: dict, athlete_profile: dict, session_intensity: float | None = None
) -> dict:
    """Check if session should be vetoed due to overtraining risk (CRITICAL safety).

    This function implements VETO logic to protect master athletes from
    overtraining. It should be called BEFORE any high-intensity session
    (>85% FTP) to determine if the session should be cancelled.

    VETO Triggers (Master Athlete):
        - TSB < -25 (critical fatigue)
        - ATL/CTL ratio > 1.8 (acute overload)
        - Sleep < 5.5h (insufficient recovery)
        - Sleep < 6h + TSB < -15 (combined stress)

    Args:
        wellness_data: Wellness metrics from Intervals.icu containing:
            - ctl: Chronic Training Load (fitness)
            - atl: Acute Training Load (fatigue)
            - tsb: Training Stress Balance (form)
            - sleep_hours: Hours of sleep (optional)
        athlete_profile: Athlete characteristics:
            - age: Athlete age
            - category: 'junior', 'senior', or 'master'
            - sleep_dependent: True if performance highly sleep-dependent
        session_intensity: Optional session intensity (% FTP) for context

    Returns:
        Dict with keys:
            - cancel: True if session should be cancelled (VETO)
            - risk_level: 'low', 'medium', 'high', or 'critical'
            - recommendation: Detailed recommendation text
            - factors: List of VETO factors triggered
            - veto: Boolean (same as cancel, for backward compatibility)

    Examples:
        >>> # Check before high-intensity session
        >>> wellness = api.get_wellness(oldest=date, newest=date)[0]
        >>> profile = AthleteProfile.from_env()
        >>> result = check_pre_session_veto(wellness, profile.dict(), 95.0)
        >>> if result['cancel']:
        ...     log_cancellation(date, reason=result['recommendation'])
        ...     print(f"VETO: {result['factors']}")

        >>> # Normal session (no VETO)
        >>> wellness = {'ctl': 65, 'atl': 60, 'tsb': 5, 'sleep_hours': 7.5}
        >>> profile = {'age': 54, 'category': 'master'}
        >>> result = check_pre_session_veto(wellness, profile)
        >>> result['cancel']
        False

        >>> # VETO triggered (critical TSB)
        >>> wellness = {'ctl': 65, 'atl': 95, 'tsb': -30, 'sleep_hours': 7}
        >>> result = check_pre_session_veto(wellness, profile)
        >>> result['cancel']
        True
        >>> result['factors']
        ['TSB < -25 (critical fatigue)']

    Notes:
        - VETO logic calibrated for master athletes (50+ years)
        - For senior athletes, thresholds can be adjusted in detect_overtraining_risk()
        - If wellness data incomplete, function returns conservative recommendation
        - Sleep hours optional but strongly recommended for accurate assessment

    See Also:
        - detect_overtraining_risk() in utils/metrics_advanced.py (core logic)
        - generate_cancelled_session_entry() for logging cancelled sessions
        - VETO_PROTOCOL.md for detailed protocol documentation

    Version:
        Added: Sprint R2.1 (2026-01-01)
        Priority: P0 (CRITICAL - athlete safety)
    """
    from cyclisme_training_logs.utils.metrics_advanced import detect_overtraining_risk

    # Extract metrics from wellness data
    ctl = wellness_data.get("ctl", 0)
    atl = wellness_data.get("atl", 0)
    tsb = wellness_data.get("tsb")

    # Calculate TSB if not provided
    if tsb is None and ctl > 0:
        tsb = ctl - atl
    elif tsb is None:
        tsb = 0

    sleep_hours = wellness_data.get("sleep_hours")

    # Call VETO detection (Sprint R2.1)
    risk_result = detect_overtraining_risk(
        ctl=ctl, atl=atl, tsb=tsb, sleep_hours=sleep_hours, profile=athlete_profile
    )

    # Build result with additional context
    result = {
        "cancel": risk_result["veto"],
        "veto": risk_result["veto"],  # Backward compatibility
        "risk_level": risk_result["risk_level"],
        "recommendation": risk_result["recommendation"],
        "factors": risk_result["factors"],
    }

    # Add session intensity context if provided
    if session_intensity and risk_result["veto"]:
        logger.warning(f"⚠️  VETO: Session cancelled (intensity={session_intensity:.0f}% FTP)")
        logger.warning(f"Factors: {', '.join(risk_result['factors'])}")
        result["session_intensity"] = session_intensity

    return result


# ============================================================================
# CHARGEMENT ET VALIDATION DU PLANNING
# ============================================================================


def load_week_planning(week_id: str, planning_dir: Path | None = None) -> dict:
    """
    Charge la configuration hebdomadaire depuis week_planning.json

    Args:
        week_id: Identifiant semaine (ex: "S070")
        planning_dir: Répertoire contenant les plannings (legacy, use data repo config)

    Returns:
        Dict contenant sessions planifiées avec statuts

    Raises:
        FileNotFoundError: Si fichier planning absent
        ValueError: Si format JSON invalide
    """
    if planning_dir is None:
        # Use data repo config if available
        from cyclisme_training_logs.config import get_data_config

        try:
            config = get_data_config()
            planning_dir = config.week_planning_dir
        except FileNotFoundError:
            # Fallback to legacy path
            planning_dir = Path.cwd() / "data" / "week_planning"

    planning_file = planning_dir / f"week_planning_{week_id}.json"

    if not planning_file.exists():
        raise FileNotFoundError(
            f"Planning non trouvé: {planning_file}\n"
            f"Créer le fichier ou utiliser le mode standard (sans planning)"
        )

    try:
        with open(planning_file, encoding="utf-8") as f:
            planning = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Format JSON invalide: {e}")

    # Validation basique
    if not validate_week_planning(planning):
        raise ValueError("Planning invalide (vérifier la structure)")

    logger.info(f"Planning chargé: {week_id} ({len(planning['planned_sessions'])} sessions)")
    return planning


def validate_week_planning(planning: dict) -> bool:
    """
    Valide structure et cohérence planning hebdomadaire

    Checks:
    - Champs obligatoires présents
    - Statuts valides
    - Dates cohérentes (semaine 7 jours)
    - Raisons présentes si cancelled
    - Pas de doublons session_id

    Args:
        planning: Dict du planning à valider

    Returns:
        True si valide, False sinon
    """
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


# ============================================================================
# GÉNÉRATION MARKDOWN REPOS PLANIFIÉ
# ============================================================================


def generate_rest_day_entry(
    session_data: dict,
    metrics_pre: dict,
    metrics_post: dict,
    athlete_feedback: dict | None = None,
) -> str:
    """
    Génère bloc markdown pour jour de repos planifié

    Args:
        session_data: Config session (id, date, raison)
        metrics_pre: CTL/ATL/TSB pré-repos
        metrics_post: CTL/ATL/TSB post-repos (stables)
        athlete_feedback: Sommeil, VFC, FC repos, ressenti (optionnel)

    Returns:
        Bloc markdown formaté selon template repos
    """
    # Extraire données session
    session_id = session_data["session_id"]
    session_type = session_data["type"]
    session_name = session_data["name"]
    date_str = datetime.strptime(session_data["date"], "%Y-%m-%d").strftime("%d/%m/%Y")
    rest_reason = session_data.get("rest_reason", "Repos planifié")
    physio_notes = session_data.get("physiological_notes", "")

    # Métriques pré/post
    from cyclisme_training_logs.utils.metrics import extract_wellness_metrics

    metrics_pre_values = extract_wellness_metrics(metrics_pre)
    metrics_post_values = extract_wellness_metrics(metrics_post)

    ctl_pre = metrics_pre_values["ctl"]
    atl_pre = metrics_pre_values["atl"]
    tsb_pre = metrics_pre_values["tsb"]

    ctl_post = metrics_post_values["ctl"]
    atl_post = metrics_post_values["atl"]
    tsb_post = metrics_post_values["tsb"]

    # Feedback athlète
    sleep_duration = "N/A"
    sleep_score = "N/A"
    hrv = "N/A"
    resting_hr = "N/A"

    if athlete_feedback:
        sleep_duration = athlete_feedback.get("sleep_duration", "N/A")
        sleep_score = athlete_feedback.get("sleep_score", "N/A")
        hrv = athlete_feedback.get("hrv", "N/A")
        resting_hr = athlete_feedback.get("resting_hr", "N/A")

    # Construire markdown
    markdown = f"""### {session_id}-{session_type}-{session_name}
Date : {date_str}

#### Métriques Pré-séance
- CTL : {ctl_pre}
- ATL : {atl_pre}
- TSB : {int(tsb_pre):+d}
- Sommeil : {sleep_duration} (score {sleep_score}, VFC {hrv}ms)
- FC repos : {resting_hr} bpm

#### Exécution
- Durée : 0min (repos complet planifié)
- IF : N/A
- TSS : 0
- Puissance moyenne : N/A
- Puissance normalisée : N/A
- Cadence moyenne : N/A
- FC moyenne : N/A
- Découplage : N/A

#### Exécution Technique
{rest_reason}

{physio_notes if physio_notes else ''}

**Contexte repos :**
- TSS nul, métriques maintenues (CTL/ATL/TSB stables)
- Consolidation des adaptations physiologiques des séances précédentes
- Récupération prioritaire selon protocole établi

#### Charge d'Entraînement
**Impact TSS=0 sur la charge :**
- CTL stable (maintien de la fitness chronique)
- ATL en légère décroissance (réduction fatigue)
- TSB stable ou légère amélioration (amélioration forme disponible)

Le repos planifié permet une récupération complète sans impact négatif sur la fitness établie.

#### Validation Objectifs
- ✅ Repos complet respecté (0 min activité)
- ✅ Récupération physiologique optimisée
- ✅ Maintien métriques forme (CTL/ATL/TSB stables)

#### Points d'Attention
- Repos planifié respecté selon protocole
- Métriques stables confirmant la stratégie de récupération
- Conditions optimales pour la prochaine séance

#### Recommandations Progression
1. **Séance suivante** : Conditions optimales après repos complet, TSB favorable
2. **Planification** : Maintenir protocole repos régulier pour adaptation durable
3. **Surveillance** : Vérifier qualité sommeil et HRV pour confirmer récupération

#### Métriques Post-séance
- CTL : {ctl_post} (stable)
- ATL : {atl_post} (stable)
- TSB : {int(tsb_post):+d} (stable)

---
"""

    return markdown


def generate_skipped_session_entry(
    session_data: dict, metrics_pre: dict, reason: str | None = None
) -> str:
    """
    Génère bloc markdown pour séance planifiée mais sautée

    Args:
        session_data: Config session (id, date, nom, TSS prévu, etc.)
        metrics_pre: CTL/ATL/TSB pré-séance
        reason: Raison du saut (optionnel)

    Returns:
        Bloc markdown formaté selon template séance sautée
    """
    # Extraire données session
    session_id = session_data.get("session_id", "N/A")
    session_name = session_data.get("name", session_data.get("planned_name", "Séance"))
    date_str = session_data.get("date", session_data.get("planned_date", ""))

    # Formatter date
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%d/%m/%Y")
        day_of_week = date_obj.strftime("%A")
    except:
        formatted_date = date_str
        day_of_week = "N/A"

    # TSS et durée prévus
    planned_tss = session_data.get("tss_planned", session_data.get("planned_tss", 0))
    planned_duration = session_data.get("duration_planned", session_data.get("planned_duration", 0))
    planned_duration_min = planned_duration // 60 if planned_duration > 0 else 0

    # Raison du saut
    skip_reason = reason or session_data.get("skip_reason", "Raison non documentée")

    # Métriques pré-séance
    from cyclisme_training_logs.utils.metrics import extract_wellness_metrics

    metrics_pre_values = extract_wellness_metrics(metrics_pre)
    # Display as N/A if metrics are not available (0 values from empty wellness data)
    ctl_pre = metrics_pre_values["ctl"] if metrics_pre else "N/A"
    atl_pre = metrics_pre_values["atl"] if metrics_pre else "N/A"
    tsb_pre = metrics_pre_values["tsb"] if metrics_pre else "N/A"

    # Contexte additionnel
    days_ago = session_data.get("days_ago", 0)

    # Construire markdown
    markdown = f"""### {session_id} - {session_name} [SAUTÉE]
Date : {formatted_date} ({day_of_week})

#### Métriques Pré-séance
- CTL : {ctl_pre}
- ATL : {atl_pre}
- TSB : {tsb_pre}

#### Séance Planifiée
- Charge prévue : {planned_tss} TSS
- Durée prévue : {planned_duration_min} min
- Type : {session_data.get('type', 'N/A')}

#### Statut
- ⏭️ **SÉANCE SAUTÉE**
- Non exécutée (il y a {days_ago} jour{'s' if days_ago > 1 else ''})
- Raison : {skip_reason}

#### Impact sur Métriques
- TSS non réalisé : -{planned_tss}
- CTL : Aucun changement (séance non effectuée)
- ATL : Diminution naturelle du à l'absence de charge
- TSB : Amélioration probable (récupération passive)

#### Recommandations Coach
- Évaluer raison du saut
- Ajuster planning semaine si nécessaire
- Vérifier cohérence avec objectifs CTL visé
- Considérer report si séance critique
- Documenter pattern si saut récurrent

#### Notes
Séance planifiée non exécutée. Impact sur progression hebdomadaire à évaluer.

---
"""
    return markdown


# ============================================================================
# GÉNÉRATION MARKDOWN SÉANCE ANNULÉE
# ============================================================================


def generate_cancelled_session_entry(
    session_data: dict, metrics_pre: dict, reason: str, impact_notes: str | None = None
) -> str:
    """
    Génère bloc markdown pour séance annulée/reportée

    Args:
        session_data: Config session (id, date, TSS prévu)
        metrics_pre: CTL/ATL/TSB pré-séance
        reason: Raison annulation (obligatoire)
        impact_notes: Notes sur l'impact planning (optionnel)

    Returns:
        Bloc markdown formaté selon template annulation
    """
    # Extraire données session
    session_id = session_data["session_id"]
    session_type = session_data["type"]
    session_name = session_data["name"]
    version = session_data.get("version", "V001")
    date_str = datetime.strptime(session_data["date"], "%Y-%m-%d").strftime("%d/%m/%Y")
    tss_planned = session_data.get("tss_planned", 0)

    # Métriques pré
    from cyclisme_training_logs.utils.metrics import extract_wellness_metrics

    metrics_pre_values = extract_wellness_metrics(metrics_pre)
    ctl_pre = metrics_pre_values["ctl"]
    atl_pre = metrics_pre_values["atl"]
    tsb_pre = metrics_pre_values["tsb"]

    # Feedback athlète (si disponible)
    sleep_info = ""
    if "sleep_duration" in metrics_pre:
        sleep_duration = metrics_pre.get("sleep_duration", "N/A")
        sleep_score = metrics_pre.get("sleep_score", "N/A")
        sleep_info = f"- Sommeil : {sleep_duration} (score {sleep_score})\n"

    # Impact planning
    if impact_notes is None:
        impact_notes = session_data.get("impact_notes", "Impact à évaluer")

    # Construire markdown
    markdown = f"""### {session_id}-{session_type}-{session_name}-{version}
Date : {date_str}

#### Métriques Pré-séance
- CTL : {ctl_pre}
- ATL : {atl_pre}
- TSB : {int(tsb_pre):+d}
{sleep_info}
#### Exécution
- Durée : 0min (séance non réalisée)
- IF : N/A
- TSS : 0 (prévu {tss_planned})
- Raison annulation : {reason}

#### Impact Planning
{impact_notes}

**Conséquences :**
- TSS nul, métriques maintenues (CTL/ATL/TSB {ctl_pre}/{atl_pre}/{int(tsb_pre):+d})
- Repos involontaire maintient ou améliore TSB
- Nécessité de réévaluer progression semaine

#### Validation Objectifs
- ❌ Séance non exécutée (annulation)
- ⚠️ Interruption progression planifiée
- ℹ️ Impact à intégrer dans planification suivante

#### Points d'Attention
- Résoudre cause annulation avant prochaine séance
- Adapter planning si nécessaire (report, remplacement, ajustement charge)
- Surveiller impact cumulé si annulations multiples

#### Recommandations
1. **Avant prochaine séance** : S'assurer que la cause d'annulation est résolue
2. **Planification** : Évaluer nécessité de report ou ajustement charge semaine
3. **Progression** : Maintenir cohérence objectifs malgré interruption

#### Métriques Post-séance
- CTL : {ctl_pre} (inchangé)
- ATL : {atl_pre} (inchangé)
- TSB : {int(tsb_pre):+d} (inchangé)

---
"""

    return markdown


# ============================================================================
# RÉCONCILIATION PLANNING VS ACTIVITÉS
# ============================================================================


def reconcile_planned_vs_actual(
    week_planning: dict, intervals_activities: list[dict]
) -> dict[str, list]:
    """
    Compare planning hebdomadaire vs activités réelles Intervals.icu

    Args:
        week_planning: Planning semaine depuis JSON
        intervals_activities: Activités récupérées API

    Returns:
        Dict avec:
        - 'matched': Sessions planifiées + exécutées
        - 'rest_days': Repos planifiés
        - 'cancelled': Séances annulées
        - 'unplanned': Activités non planifiées
    """
    result = {"matched": [], "rest_days": [], "cancelled": [], "skipped": [], "unplanned": []}

    # Index activités par date
    activities_by_date = {}
    for activity in intervals_activities:
        date = activity["start_date_local"][:10]  # YYYY-MM-DD
        if date not in activities_by_date:
            activities_by_date[date] = []
        activities_by_date[date].append(activity)

    # Traiter chaque session planifiée
    planned_dates = set()
    for session in week_planning["planned_sessions"]:
        session_date = session["date"]
        planned_dates.add(session_date)
        status = session["status"]

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
                    session_id = session["session_id"].upper()
                    session_name = session["name"].upper()

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
                    f"Session {session['session_id']} marquée completed "
                    f"mais aucune activité trouvée le {session_date} "
                    f"→ Reclassée comme SKIPPED"
                )
                # Marquer comme sautée avec contexte (modification directe pour persistence)
                session["status"] = "skipped"
                session["skip_reason"] = "Planifiée completed mais activité introuvable"
                result["skipped"].append(session)

    # Activités restantes = non planifiées
    for _, activities in activities_by_date.items():
        for activity in activities:
            # Toute activité restante est non planifiée
            result["unplanned"].append(activity)

    # Log résumé
    logger.info("=" * 70)
    logger.info(f"Réconciliation {week_planning['week_id']}")
    logger.info("=" * 70)
    logger.info(f"Sessions planifiées : {len(week_planning['planned_sessions'])}")
    logger.info(f"Sessions exécutées : {len(result['matched'])}")
    logger.info(f"Repos planifiés : {len(result['rest_days'])}")
    logger.info(f"Séances annulées : {len(result['cancelled'])}")
    logger.info(f"Séances sautées : {len(result['skipped'])}")
    logger.info(f"Activités non planifiées : {len(result['unplanned'])}")
    logger.info("=" * 70)

    return result


# ============================================================================
# WORKFLOW PRINCIPAL AVEC GESTION REPOS
# ============================================================================


def process_week_with_rest_handling(
    week_id: str,
    start_date: str,
    end_date: str,
    athlete_id: str,
    api_key: str,
    planning_dir: Path | None = None,
    output_file: Path | None = None,
) -> dict:
    """
    Workflow complet avec gestion repos/annulations

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
        athlete_id: ID athlète Intervals.icu
        api_key: Clé API Intervals.icu
        planning_dir: Répertoire plannings (optionnel)
        output_file: Fichier sortie markdown (optionnel)

    Returns:
        Dict avec résumé réconciliation et chemins fichiers générés
    """
    from cyclisme_training_logs.api.intervals_client import IntervalsClient

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

    # 2. Récupérer activités Intervals.icu
    api = IntervalsClient(athlete_id=athlete_id, api_key=api_key)
    activities = api.get_activities(oldest=start_date, newest=end_date)
    logger.info(f"Activités récupérées : {len(activities)}")

    # 3. Réconcilier
    reconciliation = reconcile_planned_vs_actual(planning, activities)

    # 4. Générer entrées markdown
    markdown_entries = []

    # Traiter par ordre chronologique
    all_sessions = sorted(planning["planned_sessions"], key=lambda x: x["date"])

    for session in all_sessions:
        status = session["status"]

        # Récupérer métriques (simulation pour l'exemple)
        # En production, récupérer depuis API Intervals.icu wellness
        metrics_pre = {"ctl": 50, "atl": 35, "tsb": 15, "sleep_duration": "7h00", "sleep_score": 75}
        metrics_post = {"ctl": 50, "atl": 35, "tsb": 15}

        if status == "rest_day":
            entry = generate_rest_day_entry(
                session_data=session,
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
            logger.info(f"✓ Repos : {session['session_id']}")

        elif status == "cancelled":
            entry = generate_cancelled_session_entry(
                session_data=session, metrics_pre=metrics_pre, reason=session["cancellation_reason"]
            )
            markdown_entries.append(entry)
            logger.info(f"✗ Annulée : {session['session_id']}")

        elif status == "skipped":
            # Nouvelle gestion séances sautées
            entry = generate_skipped_session_entry(
                session_data=session,
                metrics_pre=metrics_pre,
                reason=session.get("skip_reason", "Séance planifiée non exécutée"),
            )
            markdown_entries.append(entry)
            logger.info(f"⏭️  Sautée : {session['session_id']}")

        elif status == "completed":
            # Chercher dans les matched
            matched = next(
                (
                    m
                    for m in reconciliation["matched"]
                    if m["session"]["session_id"] == session["session_id"]
                ),
                None,
            )
            if matched:
                logger.info(f"✓ Exécutée : {session['session_id']}")
                # Ici intégration avec analyse standard (à implémenter)
                # Pour l'instant, on log juste
            else:
                logger.warning(
                    f"⚠ Session {session['session_id']} marquée completed "
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
    tss_completed = sum(m["session"].get("tss_planned", 0) for m in reconciliation["matched"])
    tss_planned = sum(s.get("tss_planned", 0) for s in all_sessions if s["status"] != "rest_day")
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
