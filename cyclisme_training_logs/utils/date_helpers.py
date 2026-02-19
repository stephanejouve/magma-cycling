"""
Date calculation utilities for training planning.

Extracted from workflow_coach.py to improve testability and reusability.

Author: Claude Sonnet 4.5
Created: 2026-02-19
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_day_number(date_str: str, week_id: str, planning_dir: Path) -> int:
    """Extrait numéro jour (1-7) depuis date pour une semaine donnée.

    Args:
        date_str: Date au format "YYYY-MM-DD" (ex: "2025-12-18")
        week_id: ID semaine (ex: "S072")
        planning_dir: Répertoire contenant les fichiers week_planning_*.json

    Returns:
        int: Numéro jour 1-7 (lundi=1, dimanche=7), ou 1 en cas d'erreur

    Examples:
        >>> # Assuming planning file exists with start_date="2025-12-15" (Monday)
        >>> planning_dir = Path("/tmp/planning")
        >>> extract_day_number("2025-12-15", "S072", planning_dir)
        1

        >>> # Wednesday of same week
        >>> extract_day_number("2025-12-17", "S072", planning_dir)
        3

        >>> # Sunday of same week
        >>> extract_day_number("2025-12-21", "S072", planning_dir)
        7

    Note:
        Si le fichier de planning n'existe pas ou est invalide, retourne 1 (fallback).
    """
    planning_file = planning_dir / f"week_planning_{week_id}.json"

    try:
        with open(planning_file, encoding="utf-8") as f:
            planning = json.load(f)

        start_date = datetime.strptime(planning["start_date"], "%Y-%m-%d").date()
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        delta = (target_date - start_date).days
        day_number = delta + 1  # Jour 1-7

        logger.debug(
            f"Extracted day number {day_number} for {date_str} in week {week_id} "
            f"(start: {start_date})"
        )

        return day_number

    except FileNotFoundError:
        logger.warning(f"Planning file not found: {planning_file}")
        return 1  # Fallback
    except KeyError as e:
        logger.warning(f"Missing key in planning file: {e}")
        return 1  # Fallback
    except ValueError as e:
        logger.warning(f"Invalid date format: {e}")
        return 1  # Fallback
    except Exception as e:
        logger.error(f"Unexpected error extracting day_number: {e}")
        return 1  # Fallback
