"""Manifest index for the cold streams archive (BT-025).

Rend la restauration index-driven (pas arbo-driven) et l'export
idempotent sans avoir à statter chaque fichier sur disque.

Structure du manifest.json (versionné) ::

    {
      "version": "1.0",
      "generated_at": "2026-08-12T15:55:44Z",
      "activities": {
        "i123456": {
          "activity_id": "i123456",
          "start_date_local": "2026-08-10T20:30:00",
          "start_date_utc": "2026-08-10T18:30:00Z",
          "duration_sec": 3600,
          "sport_type": "Ride",
          "session_id": "S106-02",
          "path": "2026/08/i123456.json.gz",
          "checksum_sha256": "abc...",
          "exported_at": "2026-08-12T15:00:00Z"
        },
        ...
      }
    }
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MANIFEST_VERSION = "1.0"
MANIFEST_FILENAME = "manifest.json"


def manifest_path() -> Path:
    """Path absolu du manifest.json (au niveau racine du répertoire streams)."""
    from magma_cycling.streams.archive import resolve_streams_dir

    return resolve_streams_dir() / MANIFEST_FILENAME


def load_manifest() -> dict[str, Any]:
    """Charge le manifest depuis disque, ou retourne un manifest vide neuf.

    Fallback safe sur JSON corrompu : log warning + retour manifest vide,
    l'appelant reconstruira les entries à l'export suivant.
    """
    path = manifest_path()
    if not path.is_file():
        return _empty_manifest()
    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("streams manifest corrupted at %s (%s) — starting fresh", path, exc)
        return _empty_manifest()

    if not isinstance(data, dict) or "activities" not in data:
        logger.warning("streams manifest schema invalid at %s — starting fresh", path)
        return _empty_manifest()
    return data


def _empty_manifest() -> dict[str, Any]:
    return {
        "version": MANIFEST_VERSION,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "activities": {},
    }


def save_manifest(manifest: dict[str, Any]) -> Path:
    """Écrit le manifest atomiquement (tmp + rename), pretty JSON UTF-8."""
    manifest["generated_at"] = (
        datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
    target = manifest_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2, sort_keys=True)
    os.chmod(tmp, 0o644)
    tmp.replace(target)
    return target


def add_manifest_entry(
    manifest: dict[str, Any],
    *,
    activity_id: str,
    start_date_local: str,
    start_date_utc: str | None,
    duration_sec: int | None,
    sport_type: str | None,
    session_id: str | None,
    path: str,
    checksum_sha256: str,
) -> dict[str, Any]:
    """Ajoute (ou remplace) une entry pour ``activity_id`` dans le manifest.

    Mutation in-place du dict manifest. L'appelant reste responsable de
    ``save_manifest`` pour persister. Idempotent : rewrite d'une même entry
    (ex. --force) écrase l'ancienne avec le nouveau checksum/exported_at.
    """
    manifest.setdefault("activities", {})[activity_id] = {
        "activity_id": activity_id,
        "start_date_local": start_date_local,
        "start_date_utc": start_date_utc,
        "duration_sec": duration_sec,
        "sport_type": sport_type,
        "session_id": session_id,
        "path": path,
        "checksum_sha256": checksum_sha256,
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    return manifest


def compute_sha256(file_path: Path) -> str:
    """SHA-256 hex digest d'un fichier (lecture streaming 64 KB)."""
    h = hashlib.sha256()
    with file_path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_checksum(
    manifest: dict[str, Any], activity_id: str, streams_dir: Path | None = None
) -> bool:
    """Vérifie que le fichier archivé matche le checksum du manifest.

    Retourne False si l'entry est absente OU si le fichier manque OU si
    le checksum diverge. Utilisé par le runbook restauration pour
    valider l'intégrité de l'archive après clone git.
    """
    entry = manifest.get("activities", {}).get(activity_id)
    if entry is None:
        return False
    if streams_dir is None:
        from magma_cycling.streams.archive import resolve_streams_dir

        streams_dir = resolve_streams_dir()
    file_path = streams_dir / entry["path"]
    if not file_path.is_file():
        return False
    return compute_sha256(file_path) == entry["checksum_sha256"]
