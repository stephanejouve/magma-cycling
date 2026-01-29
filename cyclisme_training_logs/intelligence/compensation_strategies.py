#!/usr/bin/env python3
"""
Compensation Strategies Module.

Module définissant les 6 stratégies de compensation TSS pour gérer
les déficits hebdomadaires. Utilisé par le mode proactif du système intelligence.

Stratégies disponibles:
    1. INTENSIFY - Intensifier séances existantes (+10-20 TSS)
    2. ADD_SHORT - Ajouter séance courte (+30-40 TSS)
    3. CONVERT_OUTDOOR - Convertir indoor → outdoor (+15-25% TSS)
    4. USE_REST_DAY - Utiliser jour repos (+40-80 TSS, TSB >+5 requis)
    5. PARTIAL_REPORT - Compensation partielle + report semaine suivante
    6. ACCEPT_DEFICIT - Accepter déficit (si fatigue détectée)

Author: Claude Code
Created: 2026-01-29 (Sprint S080)
"""

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CompensationStrategy(Enum):
    """
    6 stratégies de compensation TSS.

    Énumération des stratégies disponibles pour compenser déficits TSS hebdomadaires.
    Chaque stratégie a des conditions d'application spécifiques basées sur métriques athlète.

    Examples:
        >>> strategy = CompensationStrategy.INTENSIFY
        >>> strategy.value
        'intensify'
        >>> CompensationStrategy.USE_REST_DAY
        <CompensationStrategy.USE_REST_DAY: 'use_rest_day'>
    """

    INTENSIFY = "intensify"  # Intensifier séances existantes
    ADD_SHORT = "add_short"  # Ajouter séance courte
    CONVERT_OUTDOOR = "convert_outdoor"  # Indoor → Outdoor
    USE_REST_DAY = "use_rest_day"  # Utiliser jour repos
    PARTIAL_REPORT = "partial_report"  # Compensation partielle + report
    ACCEPT_DEFICIT = "accept_deficit"  # Accepter déficit (fatigue)


class CompensationAction:
    """
    Représente une action de compensation TSS.

    Encapsule détails d'une action recommandée : stratégie, séance cible,
    gain TSS, conditions requises, et justification.

    Attributes:
        strategy: Type de stratégie (CompensationStrategy)
        target_session: Nom de la séance cible
        tss_gain: Gain TSS attendu
        conditions: Liste conditions requises (ex: ["TSB >+5", "Météo >5°C"])
        rationale: Justification de l'action

    Examples:
        >>> action = CompensationAction(
        ...     strategy=CompensationStrategy.INTENSIFY,
        ...     target_session="Mercredi SS",
        ...     tss_gain=15,
        ...     conditions=["Forme OK"],
        ...     rationale="Déficit léger, forme excellente"
        ... )
        >>> action.to_dict()
        {'strategy': 'intensify', 'target_session': 'Mercredi SS', ...}
    """

    def __init__(
        self,
        strategy: CompensationStrategy,
        target_session: str,
        tss_gain: float,
        conditions: list[str],
        rationale: str,
    ):
        """
        Initialize compensation action.

        Args:
            strategy: Type de stratégie (CompensationStrategy enum)
            target_session: Nom de la séance cible
            tss_gain: Gain TSS attendu (positif)
            conditions: Liste conditions requises pour appliquer action
            rationale: Justification courte de l'action (1-2 phrases)
        """
        self.strategy = strategy
        self.target_session = target_session
        self.tss_gain = tss_gain
        self.conditions = conditions
        self.rationale = rationale

    def to_dict(self) -> dict[str, Any]:
        """
        Sérialise en dict pour AI parsing.

        Returns:
            Dict avec tous attributs sérialisés

        Examples:
            >>> action.to_dict()
            {'strategy': 'intensify', 'target_session': 'Mercredi SS', 'tss_gain': 15, ...}
        """
        return {
            "strategy": self.strategy.value,
            "target_session": self.target_session,
            "tss_gain": self.tss_gain,
            "conditions": self.conditions,
            "rationale": self.rationale,
        }


def get_strategy_matrix() -> dict[str, dict[str, Any]]:
    """
    Matrice de décision pour sélection stratégies.

    Définit règles de décision basées sur contexte athlète (TSB, jours restants, sommeil).
    Chaque situation mappe vers stratégies recommandées avec priorité.

    Returns:
        Dict avec situations → {conditions, strategies, priority}

    Examples:
        >>> matrix = get_strategy_matrix()
        >>> matrix['excellent_form_many_days']['strategies']
        [<CompensationStrategy.INTENSIFY>, <CompensationStrategy.CONVERT_OUTDOOR>, ...]

    Notes:
        - Priorité 1 = Situation idéale (forme excellente)
        - Priorité 4 = Situation limite (trop tard, fatigue)
        - Conditions format: (operator, value) ex: (">", 5)
    """
    return {
        "excellent_form_many_days": {
            "description": "Forme excellente, plusieurs jours restants",
            "conditions": {
                "tsb_min": 5,  # TSB > +5
                "days_remaining_min": 3,  # ≥ 3 jours
                "sleep_hours_min": 7,  # > 7h
            },
            "strategies": [
                CompensationStrategy.INTENSIFY,
                CompensationStrategy.CONVERT_OUTDOOR,
                CompensationStrategy.USE_REST_DAY,
            ],
            "priority": 1,
        },
        "good_form_few_days": {
            "description": "Forme correcte, peu de jours restants",
            "conditions": {
                "tsb_min": 0,  # TSB > 0
                "days_remaining_max": 2,  # 1-2 jours
                "sleep_hours_min": 6.5,  # > 6.5h
            },
            "strategies": [
                CompensationStrategy.INTENSIFY,
                CompensationStrategy.ADD_SHORT,
            ],
            "priority": 2,
        },
        "low_form_or_fatigue": {
            "description": "Forme basse ou fatigue détectée",
            "conditions": {
                "tsb_max": 0,  # TSB < 0
                "sleep_hours_max": 6,  # < 6h
            },
            "strategies": [
                CompensationStrategy.ACCEPT_DEFICIT,
            ],
            "priority": 3,
        },
        "too_late_in_week": {
            "description": "Trop tard dans la semaine",
            "conditions": {
                "days_remaining_max": 0,  # 0 jour restant
            },
            "strategies": [
                CompensationStrategy.PARTIAL_REPORT,
            ],
            "priority": 4,
        },
        "weather_favorable_indoor": {
            "description": "Météo favorable avec séances indoor",
            "conditions": {
                "suitable_outdoor": True,
                "indoor_sessions_min": 1,  # ≥ 1 séance indoor
                "tsb_min": 0,  # Forme OK
            },
            "strategies": [
                CompensationStrategy.CONVERT_OUTDOOR,
            ],
            "priority": 2,
        },
    }


def select_strategies(context: dict[str, Any]) -> list[CompensationStrategy]:
    """
    Sélectionne stratégies appropriées selon contexte.

    Analyse contexte athlète et semaine pour recommander stratégies applicables.
    Utilise matrice de décision pour mapper situations → stratégies.

    Args:
        context: Contexte complet depuis evaluate_weekly_deficit()
            Attendu: tsb, days_remaining, sleep_hours, indoor_sessions, weather

    Returns:
        Liste stratégies recommandées (ordre priorité décroissante)

    Examples:
        >>> context = {
        ...     "athlete_state": {"tsb": 8, "sleep_hours": 7.5},
        ...     "days_remaining": 4,
        ...     "indoor_sessions": [{"name": "SS"}],
        ...     "weather": {"suitable_outdoor": True}
        ... }
        >>> strategies = select_strategies(context)
        >>> CompensationStrategy.INTENSIFY in strategies
        True

    Notes:
        - Retourne liste vide si aucune stratégie applicable
        - Plusieurs stratégies peuvent être retournées (combinaison)
        - Ordre = priorité (1 = meilleur, 4 = dernier recours)
    """
    matrix = get_strategy_matrix()
    athlete = context.get("athlete_state", {})
    days_remaining = context.get("days_remaining", 0)
    indoor_sessions = context.get("indoor_sessions", [])
    weather = context.get("weather", {})

    # Extract metrics
    tsb = athlete.get("tsb", 0)
    sleep_hours = athlete.get("sleep_hours", 0)
    suitable_outdoor = weather.get("suitable_outdoor", False)

    applicable_strategies = []
    matched_situations = []

    # Check each situation in matrix
    for situation_name, situation_data in matrix.items():
        conditions = situation_data["conditions"]
        matches = True

        # Check TSB conditions
        if "tsb_min" in conditions and tsb < conditions["tsb_min"]:
            matches = False
        if "tsb_max" in conditions and tsb > conditions["tsb_max"]:
            matches = False

        # Check days remaining
        if "days_remaining_min" in conditions and days_remaining < conditions["days_remaining_min"]:
            matches = False
        if "days_remaining_max" in conditions and days_remaining > conditions["days_remaining_max"]:
            matches = False

        # Check sleep hours
        if "sleep_hours_min" in conditions and sleep_hours < conditions["sleep_hours_min"]:
            matches = False
        if "sleep_hours_max" in conditions and sleep_hours > conditions["sleep_hours_max"]:
            matches = False

        # Check weather/outdoor
        if "suitable_outdoor" in conditions and not suitable_outdoor:
            matches = False

        # Check indoor sessions availability
        if "indoor_sessions_min" in conditions:
            if len(indoor_sessions) < conditions["indoor_sessions_min"]:
                matches = False

        if matches:
            matched_situations.append(
                {
                    "name": situation_name,
                    "priority": situation_data["priority"],
                    "strategies": situation_data["strategies"],
                }
            )
            logger.debug(f"  ✓ Situation matched: {situation_name}")

    # Sort by priority and collect strategies
    matched_situations.sort(key=lambda x: x["priority"])

    for situation in matched_situations:
        for strategy in situation["strategies"]:
            if strategy not in applicable_strategies:
                applicable_strategies.append(strategy)

    logger.info(f"Selected strategies: {[s.value for s in applicable_strategies]}")

    return applicable_strategies
