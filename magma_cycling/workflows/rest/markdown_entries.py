"""Markdown entry generation for rest days, skipped and cancelled sessions."""

from datetime import datetime

from magma_cycling.config import get_logger

logger = get_logger(__name__)


def generate_rest_day_entry(
    session_data: dict,
    metrics_pre: dict,
    metrics_post: dict,
    athlete_feedback: dict | None = None,
) -> str:
    """
    Génère bloc markdown pour jour de repos planifié.

    Args:
        session_data: Config session (id, date, raison)
        metrics_pre: CTL/ATL/TSB pré-repos
        metrics_post: CTL/ATL/TSB post-repos (stables)
        athlete_feedback: Sommeil, VFC, FC repos, ressenti (optionnel)

    Returns:
        Bloc markdown formaté selon template repos.
    """
    # Extraire données session

    session_id = session_data["session_id"]
    session_type = session_data["type"]
    session_name = session_data["name"]
    date_str = datetime.strptime(session_data["date"], "%Y-%m-%d").strftime("%d/%m/%Y")
    rest_reason = session_data.get("rest_reason", "Repos planifié")
    physio_notes = session_data.get("physiological_notes", "")

    # Métriques pré/post
    from magma_cycling.utils.metrics import extract_wellness_metrics

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
    markdown = f"""### {session_id}-{session_type}-{session_name}.

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

---.
"""
    return markdown


def generate_skipped_session_entry(
    session_data: dict, metrics_pre: dict, reason: str | None = None
) -> str:
    """
    Génère bloc markdown pour séance planifiée mais sautée.

    Args:
        session_data: Config session (id, date, nom, TSS prévu, etc.)
        metrics_pre: CTL/ATL/TSB pré-séance
        reason: Raison du saut (optionnel)

    Returns:
        Bloc markdown formaté selon template séance sautée.
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
    except Exception:
        formatted_date = date_str
        day_of_week = "N/A"

    # TSS et durée prévus
    planned_tss = session_data.get("tss_planned", session_data.get("planned_tss", 0))
    planned_duration = session_data.get("duration_planned", session_data.get("planned_duration", 0))
    planned_duration_min = planned_duration // 60 if planned_duration > 0 else 0

    # Raison du saut
    skip_reason = reason or session_data.get("skip_reason", "Raison non documentée")

    # Métriques pré-séance
    from magma_cycling.utils.metrics import extract_wellness_metrics

    metrics_pre_values = extract_wellness_metrics(metrics_pre)
    # Display as N/A if metrics are not available (0 values from empty wellness data)
    ctl_pre = metrics_pre_values["ctl"] if metrics_pre else "N/A"
    atl_pre = metrics_pre_values["atl"] if metrics_pre else "N/A"
    tsb_pre = metrics_pre_values["tsb"] if metrics_pre else "N/A"

    # Contexte additionnel
    days_ago = session_data.get("days_ago", 0)

    # Construire markdown
    markdown = f"""### {session_id} - {session_name} [SAUTÉE].

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

---.
"""
    return markdown


def generate_cancelled_session_entry(
    session_data: dict, metrics_pre: dict, reason: str, impact_notes: str | None = None
) -> str:
    """
    Génère bloc markdown pour séance annulée/reportée.

    Args:
        session_data: Config session (id, date, TSS prévu)
        metrics_pre: CTL/ATL/TSB pré-séance
        reason: Raison annulation (obligatoire)
        impact_notes: Notes sur l'impact planning (optionnel)

    Returns:
        Bloc markdown formaté selon template annulation.
    """
    # Extraire données session

    session_id = session_data["session_id"]
    session_type = session_data["type"]
    session_name = session_data["name"]
    version = session_data.get("version", "V001")
    date_str = datetime.strptime(session_data["date"], "%Y-%m-%d").strftime("%d/%m/%Y")
    tss_planned = session_data.get("tss_planned", 0)

    # Métriques pré
    from magma_cycling.utils.metrics import extract_wellness_metrics

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

---.
"""
    return markdown
