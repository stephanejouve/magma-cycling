"""Wellness raw archive (1 file per day) under training-logs/data/wellness/.

PR2 plan iso-config (AC2 self-contained): the daily-sync extension archives
the raw Intervals.icu wellness payload (sleep, HRV, weight, readiness +
CTL/ATL/TSB) on every run. PR2bis adds the standalone ``backfill-wellness``
CLI that fills 90 days of history retroactively.

Storage path: ``<TRAINING_DATA_ROOT>/data/wellness/YYYY-MM-DD.json``
(shared cross-writers — wellness is per-athlete, not per-writer).
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from magma_cycling.config.data_repo import (
    WELLNESS_SUBDIR,
    _resolve_root_from_env,
)

logger = logging.getLogger(__name__)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def resolve_wellness_dir() -> Path:
    """Resolve the wellness archive directory without instantiating DataRepoConfig.

    Priority:
      1. ``TRAINING_DATA_ROOT`` (or legacy ``TRAINING_DATA_REPO``) →
         ``<root>/data/wellness/``
      2. Fallback ``~/data/wellness/`` (dev local sans env, comportement
         pré-PR2 pour ne pas crasher si le caller n'a pas configuré l'env).
    """
    root = _resolve_root_from_env()
    if root is not None:
        return root / WELLNESS_SUBDIR
    return Path.home() / "data" / "wellness"


def wellness_archive_path(date_str: str) -> Path:
    """Path du fichier d'archive d'une journée donnée.

    Args:
        date_str: ISO 8601 date ``YYYY-MM-DD``.

    Raises:
        ValueError: si ``date_str`` n'est pas un ISO 8601 ``YYYY-MM-DD`` valide.
    """
    if not _DATE_RE.match(date_str):
        raise ValueError(f"date_str must be YYYY-MM-DD, got {date_str!r}")
    return resolve_wellness_dir() / f"{date_str}.json"


def wellness_archive_exists(date_str: str) -> bool:
    """``True`` si l'archive d'une journée existe déjà sur disque.

    Utilisé par :mod:`magma_cycling.scripts.backfill_wellness` pour éviter
    le re-write idempotent (skip-existing par défaut).
    """
    return wellness_archive_path(date_str).is_file()


def archive_wellness_day(date_str: str, payload: dict[str, Any]) -> Path:
    """Write the daily wellness payload atomically.

    Args:
        date_str: ISO 8601 ``YYYY-MM-DD`` — drives the filename.
        payload: Raw Intervals.icu wellness dict (must include ``id`` field
            equal to ``date_str`` for cross-check).

    Returns:
        The final path written.

    Raises:
        ValueError: if ``date_str`` malformed or ``payload['id']`` mismatches.
    """
    target = wellness_archive_path(date_str)
    payload_id = payload.get("id")
    if payload_id and payload_id != date_str:
        raise ValueError(f"payload['id']={payload_id!r} mismatches date_str={date_str!r}")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
    os.chmod(tmp, 0o644)
    tmp.replace(target)
    logger.info("wellness archived: %s (%d bytes)", target, target.stat().st_size)
    return target
