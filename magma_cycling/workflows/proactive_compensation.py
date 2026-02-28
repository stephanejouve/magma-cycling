#!/usr/bin/env python3
"""
Proactive TSS Compensation Module.

Module de compensation TSS proactive pour gérer les déficits hebdomadaires
causés par des séances sautées. Implémente le terme Intégral du PID discrete controller.

Architecture:
    - Détection automatique des séances sautées (vs planifiées)
    - Calcul du déficit TSS hebdomadaire
    - Collecte de contexte complet (métriques, météo, séances restantes)
    - Génération de recommandations AI avec 6 stratégies
    - Intégration dans daily-sync (mode non-interactif)

Author: Claude Code
Created: 2026-01-29 (Sprint S080)
Updated: 2026-01-29 (Fix: Parse cancelled notes TSS)
"""

import json
import logging
import re
from datetime import date, timedelta
from typing import Any

from magma_cycling.api.intervals_client import IntervalsClient

logger = logging.getLogger(__name__)


def _parse_event_planned_tss(event: dict) -> float:
    r"""
    Parse le TSS prévu depuis la description d'un événement (workout ou note).

    Le TSS est stocké dans la description au format: "(XXXmin, YYY TSS)".
    Fonctionne pour WORKOUT et NOTE.

    Args:
        event: Événement Intervals.icu

    Returns:
        TSS prévu extrait de la description, ou 0 si non trouvé

    Examples:
        >>> event = {"description": "Endurance Base (75min, 56 TSS)\\n\\nWarmup..."}
        >>> _parse_event_planned_tss(event)
        56.0
    """
    description = event.get("description", "")

    # Pattern: "(60min, 60 TSS)" ou "(90min, 85 TSS)"
    match = re.search(r"\((\d+)min, (\d+) TSS\)", description)

    if match:
        return float(match.group(2))

    return 0.0


def _parse_cancelled_notes_tss(events: list[dict]) -> float:
    r"""
    Parse les notes de séances annulées/sautées/remplacées pour extraire TSS perdu.

    Quand update-session remplace une séance par une note, le TSS original est
    sauvegardé dans la description de la note au format "(XXXmin, YYY TSS)".
    Cette fonction parse ces notes pour récupérer le TSS perdu.

    Args:
        events: Liste d'événements Intervals.icu (incluant notes)

    Returns:
        Total TSS perdu des séances annulées/sautées/remplacées

    Examples:
        >>> events = [
        ...     {
        ...         "category": "NOTE",
        ...         "name": "[ANNULÉE] SS030-Ride-Sweet Spot 2x10-v1",
        ...         "description": "❌ SÉANCE ANNULÉE\n...\n(60min, 60 TSS)"
        ...     }
        ... ]
        >>> _parse_cancelled_notes_tss(events)
        60.0

    Notes:
        - Détecte notes avec tags: [ANNULÉE], [SAUTÉE], [REMPLACÉE]
        - Regex: r'\((\d+)min, (\d+) TSS\)' dans description
        - Ignore notes sans TSS parsable
    """
    lost_tss = 0.0
    cancelled_tags = ["[ANNULÉE]", "[SAUTÉE]", "[REMPLACÉE]"]

    for event in events:
        # Filtrer uniquement les notes avec tags cancelled
        if event.get("category") != "NOTE":
            continue

        event_name = event.get("name", "")
        if not any(tag in event_name for tag in cancelled_tags):
            continue

        # Parser TSS depuis description
        description = event.get("description", "")

        # Pattern: "(60min, 60 TSS)" ou "(90min, 85 TSS)"
        match = re.search(r"\((\d+)min, (\d+) TSS\)", description)

        if match:
            tss = float(match.group(2))
            lost_tss += tss
            logger.debug(f"  Parsed cancelled note: {event_name[:50]}... → {tss} TSS")
        else:
            logger.warning(f"  Could not parse TSS from note: {event_name}")

    if lost_tss > 0:
        logger.info(f"  TSS perdu (notes annulées) : {lost_tss:.0f}")

    return lost_tss


def evaluate_weekly_deficit(
    week_id: str,
    check_date: date,
    client: IntervalsClient,
    threshold_tss: int = 50,
) -> dict[str, Any] | None:
    """
    Évalue le déficit TSS hebdomadaire et décide intervention.

    Détecte séances planifiées non exécutées et calcule le déficit TSS cumulé.
    Déclenche collecte de contexte si déficit > seuil.

    Args:
        week_id: Identifiant semaine (ex: "S078")
        check_date: Date de vérification (généralement aujourd'hui)
        client: Client IntervalsClient configuré
        threshold_tss: Seuil déficit pour déclencher compensation (défaut: 50)

    Returns:
        Dict avec déficit et contexte si intervention nécessaire, None sinon

    Examples:
        >>> from magma_cycling.api.intervals_client import IntervalsClient
        >>> client = IntervalsClient(athlete_id="i123456", api_key="...")
        >>> result = evaluate_weekly_deficit("S078", date(2026, 1, 30), client)
        >>> if result:
        ...     print(f"Déficit: {result['deficit']} TSS")

    Notes:
        - Filtre événements passés (< check_date) pour calcul déficit
        - Compare planning vs activités complétées
        - Retourne None si déficit < threshold_tss (pas d'intervention)
    """
    try:
        from magma_cycling.workflows.end_of_week import calculate_week_start_date

        # 1. Calculer dates semaine
        week_start = calculate_week_start_date(week_id)
        week_end = week_start + timedelta(days=6)

        logger.info(f"Évaluation déficit TSS - Semaine {week_id} ({week_start} → {week_end})")

        # 2. Charger planning semaine depuis Intervals.icu (tous événements)
        # GET /api/v1/athlete/{id}/events?oldest={week_start}&newest={week_end}
        all_events = client.get_events(oldest=week_start.isoformat(), newest=week_end.isoformat())

        # Séparer workouts et notes
        planned_workouts = [e for e in all_events if e.get("category") == "WORKOUT"]
        notes = [e for e in all_events if e.get("category") == "NOTE"]

        logger.debug(f"  Planning: {len(planned_workouts)} séances planifiées")
        logger.debug(f"  Notes: {len(notes)} notes (possibles annulations)")

        # 3. Charger activités complétées
        # GET /api/v1/athlete/{id}/activities?oldest={week_start}&newest={check_date}
        completed_activities = client.get_activities(
            oldest=week_start.isoformat(), newest=check_date.isoformat()
        )

        logger.debug(f"  Complétées: {len(completed_activities)} activités")

        # 4. Calculer déficit
        # 4a. TSS planifié = parser TOUS les événements passés (workouts + notes)
        # depuis leurs descriptions "(XXmin, YY TSS)"
        past_events = [
            e
            for e in all_events
            if date.fromisoformat(e["start_date_local"].split("T")[0]) < check_date
        ]

        planned_tss = 0.0
        for event in past_events:
            event_tss = _parse_event_planned_tss(event)
            if event_tss > 0:
                planned_tss += event_tss
                event_date = event["start_date_local"][:10]
                event_name = event["name"][:40]
                logger.debug(
                    f"  {event_date} | {event['category']:8} | {event_tss:3.0f} TSS | {event_name}"
                )

        # 4b. TSS complété
        completed_tss = sum(a.get("icu_training_load", 0) for a in completed_activities)

        # 4c. Calculer déficit
        deficit = planned_tss - completed_tss

        logger.info(f"  TSS planifié (total jours passés): {planned_tss:.0f}")
        logger.info(f"  TSS complété: {completed_tss:.0f}")
        logger.info(f"  Déficit brut: {deficit:.0f} TSS")

        # 5. Décision intervention
        # Un déficit positif signifie: planned > completed (vrai manque)
        # Un déficit négatif signifie: completed > planned (surplus, pas de compensation)
        if deficit <= 0:
            logger.info(f"  ✅ Surplus TSS ({-deficit:.0f}) ou équilibre - Pas d'intervention")
            return None

        if deficit < threshold_tss:
            logger.info(
                f"  ✅ Déficit ({deficit:.0f} TSS) < seuil ({threshold_tss} TSS) - Pas d'intervention"
            )
            return None

        logger.info(
            f"  ⚠️  Déficit ({deficit:.0f} TSS) > seuil ({threshold_tss} TSS) - Intervention nécessaire"
        )

        # 6. Collecter contexte complet
        context = _collect_compensation_context(
            week_id=week_id,
            check_date=check_date,
            deficit=deficit,
            planned_events=all_events,  # Passer tous événements (workouts + notes)
            completed_activities=completed_activities,
            client=client,
        )

        return context

    except Exception as e:
        logger.error(f"Erreur évaluation déficit: {e}", exc_info=True)
        return None


def _collect_compensation_context(
    week_id: str,
    check_date: date,
    deficit: float,
    planned_events: list[dict],
    completed_activities: list[dict],
    client: IntervalsClient,
) -> dict[str, Any]:
    """
    Collecte contexte complet pour décision compensation.

    Agrège toutes les données nécessaires pour génération prompt AI :
    - Séances annulées avec raisons
    - Séances restantes semaine
    - Métriques athlète (TSB, sommeil, HRV)
    - Jours repos disponibles
    - Séances convertibles indoor→outdoor
    - Météo (mock pour version initiale)

    Args:
        week_id: Identifiant semaine
        check_date: Date de vérification
        deficit: Déficit TSS calculé
        planned_events: Événements planifiés depuis Intervals.icu
        completed_activities: Activités complétées
        client: Client IntervalsClient

    Returns:
        Dict avec contexte complet pour AI prompt

    Examples:
        >>> context = _collect_compensation_context(...)
        >>> print(context.keys())
        dict_keys(['deficit', 'deficit_pct', 'cancelled_sessions', 'remaining_sessions', ...])

    Notes:
        - Météo actuellement mockée (TODO: intégrer API météo réelle)
        - Raisons annulations analysées depuis notes/wellness si disponibles
    """
    logger.debug("Collecte contexte compensation...")

    # Filtrer workouts uniquement (exclure notes)
    workouts_only = [e for e in planned_events if e.get("category") == "WORKOUT"]

    # 1. Séances restantes cette semaine
    remaining_sessions = [
        e
        for e in workouts_only
        if date.fromisoformat(e["start_date_local"].split("T")[0]) >= check_date
    ]

    logger.debug(f"  Séances restantes: {len(remaining_sessions)}")

    # 2. Raisons annulations (analyse activités manquantes)
    cancelled_sessions = _identify_cancelled_sessions(
        workouts_only, completed_activities, check_date
    )

    logger.debug(f"  Séances annulées: {len(cancelled_sessions)}")

    # 3. Métriques athlète actuelles
    # GET /api/v1/athlete/{id}/wellness (date la plus récente)
    try:
        # Get wellness for check_date (or most recent before)
        wellness_data = {}
        for i in range(3):  # Try up to 3 days back
            wellness_date = check_date - timedelta(days=i)
            wellness = client.get_wellness(wellness_date.isoformat())
            if wellness:
                # wellness peut être dict ou list[dict]
                if isinstance(wellness, list):
                    wellness_data = wellness[0] if wellness else {}
                else:
                    wellness_data = wellness
                logger.debug(f"  Wellness récupéré: {wellness_date}")
                break

        # Extract metrics (avec fallback si wellness vide)
        # Note: .get("key", 0) returns None when key exists with null value,
        # so we use `or 0` to guard against both missing and null values.
        athlete_state = {
            "tsb": (
                (wellness_data.get("ctl") or 0) - (wellness_data.get("atl") or 0)
                if wellness_data
                else 0
            ),
            "sleep_hours": (wellness_data.get("sleepSecs") or 0) / 3600 if wellness_data else 0,
            "hrv": (wellness_data.get("hrv") or 0) if wellness_data else 0,
            "rpe": (wellness_data.get("rpe") or 0) if wellness_data else 0,
            "weight": (wellness_data.get("weight") or 0) if wellness_data else 0,
        }

        logger.debug(f"  TSB: {athlete_state['tsb']:+.1f}")
        logger.debug(f"  Sommeil: {athlete_state['sleep_hours']:.1f}h")

    except Exception as e:
        logger.warning(f"  Erreur récupération wellness: {e}")
        athlete_state = {
            "tsb": 0,
            "sleep_hours": 0,
            "hrv": 0,
            "rpe": 0,
            "weight": 0,
        }

    # 4. Jours repos disponibles
    rest_days = _identify_available_rest_days(remaining_sessions, check_date)

    logger.debug(f"  Jours repos: {rest_days}")

    # 5. Séances convertibles indoor→outdoor
    indoor_sessions = [
        s
        for s in remaining_sessions
        if s.get("indoor", False) or "indoor" in s.get("name", "").lower()
    ]

    logger.debug(f"  Séances indoor convertibles: {len(indoor_sessions)}")

    # 6. Météo semaine (API externe ou estimation)
    weather = _get_weather_forecast(check_date)

    # 7. Calculer jours restants jusqu'à fin semaine (dimanche)
    days_until_sunday = (6 - check_date.weekday()) % 7

    # 8. Calculer déficit en pourcentage
    # Inclure TSS workouts + TSS perdu (notes annulées)
    workouts_tss = sum(e.get("load", 0) for e in workouts_only)
    lost_tss = _parse_cancelled_notes_tss(planned_events)
    total_planned_tss = workouts_tss + lost_tss
    deficit_pct = (deficit / total_planned_tss * 100) if total_planned_tss > 0 else 0

    context = {
        "deficit": deficit,
        "deficit_pct": deficit_pct,
        "cancelled_sessions": cancelled_sessions,
        "remaining_sessions": remaining_sessions,
        "days_remaining": days_until_sunday,
        "athlete_state": athlete_state,
        "rest_days": rest_days,
        "indoor_sessions": indoor_sessions,
        "weather": weather,
        "week_id": week_id,
        "check_date": check_date.isoformat(),
    }

    logger.info("  ✅ Contexte collecté avec succès")
    return context


def _identify_cancelled_sessions(
    planned: list[dict], completed: list[dict], check_date: date
) -> list[dict]:
    """
    Identifie séances planifiées non exécutées.

    Compare planning vs activités complétées pour détecter séances manquantes.

    Args:
        planned: Événements planifiés Intervals.icu
        completed: Activités complétées
        check_date: Date de vérification

    Returns:
        Liste des séances annulées avec date, nom, TSS, type

    Examples:
        >>> cancelled = _identify_cancelled_sessions(planned, completed, date(2026, 1, 30))
        >>> len(cancelled)
        2
        >>> cancelled[0]['tss']
        60.0
    """
    # Extraire dates des activités complétées
    completed_dates = {date.fromisoformat(a["start_date_local"].split("T")[0]) for a in completed}

    cancelled = []
    for event in planned:
        event_date_str = event["start_date_local"].split("T")[0]
        event_date = date.fromisoformat(event_date_str)

        # Séance planifiée dans le passé mais non exécutée
        if event_date < check_date and event_date not in completed_dates:
            cancelled.append(
                {
                    "date": event_date.isoformat(),
                    "name": event.get("name", "Unnamed"),
                    "tss": event.get("load", 0),
                    "type": event.get("type", "unknown"),
                }
            )

    return cancelled


def _identify_available_rest_days(
    remaining_sessions: list[dict], check_date: date
) -> list[dict[str, any]]:
    """
    Identifie jours repos prévus dans séances restantes.

    Analyse planning restant pour détecter jours sans séance prévue.

    Args:
        remaining_sessions: Séances restantes cette semaine
        check_date: Date actuelle

    Returns:
        Liste de dicts avec infos complètes sur jours repos:
        - day_name: Nom du jour (ex: "Dimanche")
        - date: Date ISO (ex: "2026-02-01")
        - weekday: Numéro jour semaine (0=lundi, 6=dimanche)

    Examples:
        >>> rest_days = _identify_available_rest_days(remaining_sessions, date(2026, 1, 30))
        >>> rest_days
        [{'day_name': 'Dimanche', 'date': '2026-02-01', 'weekday': 6}]

    Notes:
        - Ne considère que les jours entre check_date et dimanche
        - Format français (Lundi, Mardi, ...)
    """
    # Extraire jours prévus (weekday: 0=lundi, 6=dimanche)
    planned_weekdays = set()
    for session in remaining_sessions:
        session_date_str = session["start_date_local"].split("T")[0]
        session_date = date.fromisoformat(session_date_str)
        planned_weekdays.add(session_date.weekday())

    # Jours restants jusqu'à dimanche (inclus)
    current_weekday = check_date.weekday()
    # Si on est dimanche (6), on veut quand même considérer dimanche
    if current_weekday == 6:
        remaining_weekdays = {6}
    else:
        remaining_weekdays = set(range(current_weekday + 1, 7))  # Demain jusqu'à dimanche

    # Jours repos = jours restants sans séance prévue
    rest_weekdays = remaining_weekdays - planned_weekdays

    day_names = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

    # Construire liste avec infos complètes
    rest_days = []
    for weekday in sorted(rest_weekdays):
        # Calculer la date correspondante
        days_ahead = weekday - current_weekday
        if days_ahead <= 0:
            days_ahead += 7  # Semaine prochaine
        rest_date = check_date + timedelta(days=days_ahead)

        rest_days.append(
            {
                "day_name": day_names[weekday],
                "date": rest_date.isoformat(),
                "weekday": weekday,
            }
        )

    return rest_days


def _get_weather_forecast(check_date: date) -> dict[str, Any]:
    """
    Récupère prévisions météo semaine.

    Version initiale simplifiée (mock).
    TODO: Intégrer API météo réelle (OpenWeatherMap, etc.)

    Args:
        check_date: Date de référence

    Returns:
        Dict avec prévisions météo mockées

    Examples:
        >>> weather = _get_weather_forecast(date(2026, 1, 30))
        >>> weather['avg_temp_celsius']
        10

    Notes:
        - Mock data actuellement (valeurs fixes)
        - Température favorable outdoor: >5°C
    """
    # TODO: Intégrer API météo réelle
    return {
        "avg_temp_celsius": 10,
        "precipitation_mm": 5,
        "suitable_outdoor": True,
        "note": "Mock data - TODO: real API integration",
    }


def generate_compensation_prompt(context: dict[str, Any]) -> str:
    """
    Génère prompt AI pour recommandations compensation.

    Construit prompt formaté avec contexte complet pour décision AI.
    Inclut 6 stratégies disponibles et format réponse JSON attendu.

    Args:
        context: Contexte complet depuis _collect_compensation_context()

    Returns:
        Prompt formaté pour AI provider

    Examples:
        >>> prompt = generate_compensation_prompt(context)
        >>> "Déficit hebdomadaire" in prompt
        True
        >>> "6 Stratégies Disponibles" in prompt
        True

    Notes:
        - Format JSON strict pour parsing
        - Inclut tous les contextes nécessaires à décision
        - Demande justification explicite
    """
    # Extraire données clés
    deficit = context["deficit"]
    deficit_pct = context["deficit_pct"]
    cancelled = context["cancelled_sessions"]
    remaining = context["remaining_sessions"]
    days_left = context["days_remaining"]
    athlete = context["athlete_state"]
    rest_days = context["rest_days"]
    indoor = context["indoor_sessions"]
    weather = context["weather"]

    # Formater raisons annulations
    if cancelled:
        cancellation_reasons = "\n".join(
            [f"  - {s['date']}: {s['name']} ({s['tss']:.0f} TSS)" for s in cancelled]
        )
    else:
        cancellation_reasons = "  Aucune séance annulée"

    # Formater séances restantes
    if remaining:
        remaining_workouts = "\n".join(
            [
                f"  - {s['start_date_local'].split('T')[0]}: {s['name']} ({s.get('load', 0):.0f} TSS)"
                for s in remaining
            ]
        )
    else:
        remaining_workouts = "  Aucune séance restante"

    # Formater les métriques athlète (gérer les None)
    sleep_str = f"{athlete['sleep_hours']:.1f}" if athlete["sleep_hours"] is not None else "N/A"
    hrv_str = f"{athlete['hrv']:.0f}" if athlete["hrv"] is not None else "N/A"
    rpe_str = f"{athlete['rpe']:.1f}" if athlete["rpe"] is not None else "N/A"

    # Construire prompt
    prompt = f"""# Compensation TSS Proactive

## Situation Actuelle

**Déficit hebdomadaire:** -{deficit:.0f} TSS ({deficit_pct:.1f}% du planning)

**Séances annulées:**
{cancellation_reasons}

**Séances restantes (jours restants: {days_left}):**
{remaining_workouts}

**Jours repos disponibles:** {', '.join([f"{r['day_name']} ({r['date']})" for r in rest_days]) if rest_days else 'Aucun'}

## Métriques Athlète

- **TSB (Form):** {athlete['tsb']:+.1f}
- **Sommeil:** {sleep_str}h
- **HRV:** {hrv_str}
- **RPE récent:** {rpe_str}/10

## Contexte Météo

- **Température moyenne:** {weather['avg_temp_celsius']}°C
- **Précipitations:** {weather['precipitation_mm']}mm
- **Outdoor favorable:** {'Oui' if weather['suitable_outdoor'] else 'Non'}

## Séances Convertibles Indoor→Outdoor

{len(indoor)} séances indoor identifiées (gain +15-25% TSS si conversion outdoor)

---

## MÉTHODOLOGIE ENTRAÎNEMENT (PEAKS COACHING / HUNTER ALLEN)

### Principes Fondamentaux
- **Méthode Traditionnelle** (distribution équilibrée) > Polarisée pour Masters 50+
- **Sweet-Spot (88-93% FTP)** = zone optimale développement FTP ("biggest bang for your buck")
- **CTL Masters 50+**: Maintenir 90% du max, éviter drops >10 points
- **Adaptation physiologique**: 6-8 semaines délai avant effet mesurable
- **"Testing is training"**: Tests intégrables dans semaines normales, pas bloquer semaines entières

### Distribution Intensité Recommandée (Budget 8-12h/semaine)
- **Récupération**: 10%
- **Endurance (56-75% FTP)**: 25%
- **Tempo (76-91% FTP)**: 35% ← ZONE PRINCIPALE
- **Sweet-Spot (88-93% FTP)**: Inclus dans Tempo ci-dessus, prioriser en phase reconstruction
- **FTP (94-105%)**: 15%
- **VO2 max (106-120%)**: 10%
- **Anaérobie + Neuro (>120%)**: 5%

### Gestion CTL Âge 50+
- FTP 220W → CTL minimum 55-65
- FTP 240W → CTL minimum 65-75
- FTP 260W → CTL minimum 70-80
- **Alerte si drop >10 points en 4 semaines** (récupération lente âge 50+)
- **Semaines récup**: Tous les 3 semaines maximum (Masters 50+)

### Validation Séances
- **Tempo/Sweet-Spot**: Découplage cardio <7.5% requis
- **VO2/AC**: TSB >+5 et sommeil >7h minimum
- **Éviter "junk miles"**: Toute séance doit avoir zone(s) cible précise(s)
- **Discipline outdoor**: Si >2 échecs surcharge IF, basculer indoor pour cette zone

---

## Mission

Proposer une stratégie de compensation **réaliste et intelligente** pour récupérer le déficit de -{deficit:.0f} TSS, en respectant les principes méthodologiques ci-dessus.

## 6 Stratégies Disponibles

1. **Intensifier séances existantes** (+10-20 TSS/séance)
2. **Ajouter séance courte** (+30-40 TSS)
3. **Convertir indoor → outdoor** (+15-25% TSS même durée)
4. **Utiliser jour repos** (+40-80 TSS si TSB >+5 requis)
5. **Compensation partielle + report** (si trop tard)
6. **Accepter déficit** (si fatigue détectée)

## Format Réponse (JSON uniquement)

```json
{{
  "strategy": "combined|single",
  "actions": [
    {{
      "type": "intensify|add_short|convert_outdoor|use_rest_day|partial_report|accept_deficit",
      "session": "Nom séance cible",
      "from_tss": 50,
      "to_tss": 65,
      "gain": 15,
      "rationale": "Courte justification"
    }}
  ],
  "total_compensated": 60,
  "conditions_required": ["Météo >5°C", "TSB >+5"],
  "overall_rationale": "Justification globale stratégie choisie (2-3 phrases)"
}}
```

**Important:** Répondre UNIQUEMENT avec le JSON, sans texte avant/après.
"""

    return prompt


def parse_ai_compensation_response(response: str) -> dict[str, Any] | None:
    """
    Parse la réponse AI (JSON attendu).

    Extrait et valide structure JSON depuis réponse AI.
    Gère nettoyage markdown backticks si présents.

    Args:
        response: Réponse brute de l'AI provider

    Returns:
        Dict avec actions de compensation, ou None si parsing échoue

    Examples:
        >>> response = '{"strategy": "combined", "actions": [...], "total_compensated": 60}'
        >>> data = parse_ai_compensation_response(response)
        >>> data['strategy']
        'combined'

    Notes:
        - Accepte JSON avec ou sans markdown backticks
        - Validation structure minimale (strategy, actions, total_compensated)
        - Logs détaillés en cas d'échec parsing
    """
    try:
        # Nettoyer réponse (enlever markdown backticks si présents)
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Parser JSON
        data = json.loads(cleaned)

        # Validation structure minimale
        required_keys = ["strategy", "actions", "total_compensated"]
        if not all(k in data for k in required_keys):
            raise ValueError(f"Missing required keys: {required_keys}")

        # Validation actions
        for action in data["actions"]:
            if "type" not in action or "gain" not in action:
                raise ValueError(f"Invalid action structure: {action}")

        logger.info("✅ AI response parsed successfully")
        return data

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"❌ Failed to parse AI response: {e}")
        logger.debug(f"Raw response: {response[:200]}...")
        return None


def format_compensation_section(context: dict[str, Any], recommendations: dict[str, Any]) -> str:
    """
    Formate section compensation pour email daily report.

    Génère section markdown/HTML formatée pour intégration dans email quotidien.
    Présente déficit, stratégie, actions, et conditions requises.

    Args:
        context: Contexte déficit depuis evaluate_weekly_deficit()
        recommendations: Recommandations parsées depuis AI

    Returns:
        Section formatée (markdown) pour email

    Examples:
        >>> section = format_compensation_section(context, recommendations)
        >>> "Compensation TSS Proactive" in section
        True
        >>> "Stratégie Recommandée" in section
        True

    Notes:
        - Format cohérent avec daily report existant
        - Inclut avertissement non-application automatique
        - Suggère validation manuelle
    """
    deficit = context["deficit"]
    week_id = context["week_id"]
    days_left = context["days_remaining"]

    section = f"""
## 🎯 Compensation TSS Proactive

**Semaine {week_id} - Déficit détecté: {deficit:.0f} TSS**

**Jours restants:** {days_left}

### Stratégie Recommandée: {recommendations['strategy'].upper()}

"""

    # Lister actions
    for i, action in enumerate(recommendations["actions"], 1):
        action_type = action["type"].replace("_", " ").title()
        gain = action["gain"]
        rationale = action.get("rationale", "N/A")

        section += f"""
**Action {i}: {action_type}**
- Séance: {action.get('session', 'N/A')}
- Gain: +{gain} TSS
- Justification: {rationale}
"""

    # Total compensation
    total = recommendations["total_compensated"]
    remaining_deficit = deficit - total

    # Format remaining deficit with proper sign handling
    if remaining_deficit > 0:
        deficit_display = f"{remaining_deficit:.0f} TSS restant"
    elif remaining_deficit < 0:
        deficit_display = f"Sur-compensation de {-remaining_deficit:.0f} TSS"
    else:
        deficit_display = "Déficit comblé ✅"

    section += f"""
---

**Compensation totale:** +{total} TSS
**Déficit résiduel:** {deficit_display}

**Justification globale:**
{recommendations.get('overall_rationale', 'N/A')}

**Conditions requises:**
{', '.join(recommendations.get('conditions_required', []))}

---

⚠️  **Note:** Recommandations non appliquées automatiquement.
Valider et ajuster manuellement selon ressenti.
"""

    return section
