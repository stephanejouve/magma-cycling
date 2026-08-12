"""Getter partagé pour les libellés d'affichage des métriques d'entraînement.

BT-022 : découplage calcul / affichage. Les libellés vivent dans
`magma_cycling/config/metric_labels.yaml`, factorisés pour permettre un
renommage à la demande (marques déposées TSS/NP/IF appartenant désormais
à Garmin/TrainingPeaks) sans toucher aux templates rapports ni aux
prompts LLM.

Usage nominal ::

    from magma_cycling.utils.metric_labels import get_label

    label = get_label("tss")              # → "TSS"
    label = get_label("normalized_power") # → "Puissance normalisée"
    label = get_label("tss", locale="en") # → "TSS"

Fallback safe si la clé n'existe pas ou si le YAML est absent : la clé
technique est retournée telle quelle et un warning est loggé. Aucune
exception ne remonte — le rendu utilisateur peut légèrement dégrader
mais jamais planter.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_LOCALE = "fr"
_LABELS_FILE = Path(__file__).parent.parent / "config" / "metric_labels.yaml"


@lru_cache(maxsize=1)
def _load_labels() -> dict[str, dict[str, str]]:
    """Charge le YAML des libellés une seule fois par processus (cache lru).

    Cache invalidable via `_load_labels.cache_clear()` pour les tests.
    """
    if not _LABELS_FILE.exists():
        logger.warning(
            "metric_labels.yaml introuvable à %s — fallback sur clés techniques",
            _LABELS_FILE,
        )
        return {}
    try:
        with _LABELS_FILE.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            logger.warning("metric_labels.yaml n'est pas un dict racine — fallback clés techniques")
            return {}
        return data
    except (yaml.YAMLError, OSError) as exc:
        logger.warning("metric_labels.yaml illisible (%s) — fallback clés techniques", exc)
        return {}


def get_label(key: str, locale: str = _DEFAULT_LOCALE, form: str = "long") -> str:
    """Retourne le libellé d'affichage pour une métrique.

    Args:
        key: Clé technique (ex. "tss", "normalized_power", "intensity_factor").
        locale: Locale cible ("fr" par défaut, "en" supporté).
        form: "long" (défaut, colonne principale du YAML) ou "short"
            (forme compacte pour dashboards / tableaux).

    Returns:
        Le libellé d'affichage. En cas d'absence de la clé ou du champ,
        retourne la clé technique telle quelle (fallback safe) et
        log un warning.
    """
    labels = _load_labels()
    entry = labels.get(key)
    if entry is None:
        logger.warning("get_label: clé inconnue %r (fallback vers la clé technique)", key)
        return key

    if form == "short" and "short" in entry:
        return entry["short"]

    value = entry.get(locale)
    if value is None:
        # Fallback vers la locale par défaut si la locale demandée manque.
        value = entry.get(_DEFAULT_LOCALE)
    if value is None:
        logger.warning(
            "get_label: entrée %r sans locale %r ni fallback %r — retour clé",
            key,
            locale,
            _DEFAULT_LOCALE,
        )
        return key
    return value


def get_description(key: str) -> str | None:
    """Retourne la glose explicative d'une métrique si documentée.

    Utile pour des tooltips ou pour enrichir des prompts LLM sans forcer
    l'utilisation d'une marque déposée dans les libellés courants.
    """
    entry = _load_labels().get(key)
    if entry is None:
        return None
    return entry.get("description")
