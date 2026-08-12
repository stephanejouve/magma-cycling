"""Cold archive of Intervals.icu activity streams (BT-025).

Chaque activité est stockée en JSON gzip sous
``training-logs/data/streams/YYYY/MM/<activity_id>.json.gz``, partitionné
par heure LOCALE de l'activité (pas UTC — cf. Q-K, le container prod
tourne en UTC, hériter de son now() plache les activités de fin de
soirée sur le mauvais mois à la bascule).

Le partitionnement est **explicite** dans le code : le caller passe un
``datetime`` naive local (comme retourné par Intervals.icu dans
``start_date_local``), on ne dérive jamais du fuseau système.

Pattern miroir de ``magma_cycling/wellness/archive.py`` (BT-023) — même
principes atomic write, best-effort logging, fallback safe.
"""

from __future__ import annotations

import gzip
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from magma_cycling.config.data_repo import _resolve_root_from_env

logger = logging.getLogger(__name__)

#: Sous-dossier (relatif à la racine training-logs) qui héberge les streams.
#: Shared cross-writers — les streams sont un fait per-athlète, pas per-writer.
STREAMS_SUBDIR = "data/streams"


def resolve_streams_dir() -> Path:
    """Path racine du dossier d'archive streams.

    Priorité :
      1. ``TRAINING_DATA_ROOT`` (ou legacy ``TRAINING_DATA_REPO``) →
         ``<root>/data/streams/``
      2. Fallback ``~/data/streams/`` (dev local sans env, comportement
         pré-BT-025 pour ne pas crasher si le caller n'a pas configuré).
    """
    root = _resolve_root_from_env()
    if root is not None:
        return root / STREAMS_SUBDIR
    return Path.home() / "data" / "streams"


def partition_from_local_dt(dt_local: datetime) -> str:
    """Retourne le segment de path ``YYYY/MM`` depuis un datetime naive local.

    Q-K : NE PAS utiliser ``datetime.now()`` ou ``datetime.utcnow()`` —
    passer explicitement le ``start_date_local`` de l'activité pour que
    la partition corresponde à l'heure locale de l'athlète,
    indépendamment de la TZ du container qui exécute l'archivage.

    Args:
        dt_local: datetime naive représentant l'heure locale de l'activité
            (comme retourné par Intervals.icu dans ``start_date_local``).

    Returns:
        Segment de path ``YYYY/MM`` (ex. ``"2026/08"``).
    """
    return f"{dt_local.year:04d}/{dt_local.month:02d}"


def streams_archive_path(activity_id: str, dt_local: datetime) -> Path:
    """Path absolu du fichier d'archive streams pour une activité.

    Args:
        activity_id: ID Intervals.icu (ex. ``"i107424849"`` ou ``"107424849"``).
        dt_local: datetime naive local (voir partition_from_local_dt).

    Returns:
        Path ``<root>/data/streams/YYYY/MM/<activity_id>.json.gz``.
    """
    partition = partition_from_local_dt(dt_local)
    return resolve_streams_dir() / partition / f"{activity_id}.json.gz"


def streams_archive_exists(activity_id: str) -> bool:
    """Test d'existence via le manifest (pas via stat disque).

    Idempotent : le backfill saute une activité si elle est indexée dans
    le manifest — pas besoin de reconstruire le path physique (qui
    demanderait de connaître le dt_local a priori).
    """
    from magma_cycling.streams.manifest import load_manifest

    manifest = load_manifest()
    return activity_id in manifest.get("activities", {})


def archive_activity_streams(
    activity_id: str,
    streams: list[dict[str, Any]] | dict[str, Any],
    *,
    start_date_local: str,
    start_date_utc: str | None = None,
    duration_sec: int | None = None,
    sport_type: str | None = None,
    session_id: str | None = None,
) -> Path:
    """Archive les streams d'une activité (gzip atomic + manifest update).

    Idempotent : si l'archive existe déjà pour cet ``activity_id``, elle
    est écrasée (utile pour --force et pour recalculer le checksum).

    Args:
        activity_id: ID Intervals.icu.
        streams: Payload retourné par ``IntervalsClient.get_activity_streams``.
            Peut être une liste (shape API standard) ou un dict.
        start_date_local: ISO 8601 naive local (ex. ``"2026-08-10T20:30:00"``).
            Utilisé pour la partition ``YYYY/MM``. Q-K : passer la valeur
            de l'API Intervals.icu, PAS convertir depuis un UTC via TZ
            container.
        start_date_utc: Optionnel, ISO 8601 UTC (``"...Z"``). Stocké
            dans le manifest pour audit croisé.
        duration_sec: Durée en secondes, stockée dans le manifest.
        sport_type: Ex. ``"Ride"``, ``"Run"`` — stocké dans le manifest.
        session_id: Session local liée (ex. ``"S106-02"``) si connue,
            None sinon.

    Returns:
        Path absolu du fichier gzip écrit.

    Raises:
        ValueError: si ``start_date_local`` n'est pas parsable en ISO 8601.
        OSError: si l'écriture disque échoue (permission, disque plein).
    """
    from magma_cycling.streams.manifest import (
        add_manifest_entry,
        compute_sha256,
        load_manifest,
        save_manifest,
    )

    try:
        dt_local = datetime.fromisoformat(start_date_local.replace("Z", ""))
    except ValueError as exc:
        raise ValueError(f"start_date_local must be ISO 8601, got {start_date_local!r}") from exc

    target = streams_archive_path(activity_id, dt_local)
    target.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(streams, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    tmp = target.with_suffix(target.suffix + ".tmp")
    with gzip.open(tmp, "wb") as fh:
        fh.write(payload)
    os.chmod(tmp, 0o644)
    tmp.replace(target)

    checksum = compute_sha256(target)
    # BT-025 : force forward-slash pour portabilité cross-OS du manifest.
    # Un manifest écrit sur Windows doit rester lisible sur Ubuntu/macOS
    # (et vice versa) — l'archive git training-logs est partagée entre
    # les 3 environnements. as_posix() garantit le séparateur "/" quelle
    # que soit la plateforme, contrairement à str(Path) qui hérite du sep OS.
    rel_path = target.relative_to(resolve_streams_dir()).as_posix()

    manifest = load_manifest()
    add_manifest_entry(
        manifest,
        activity_id=activity_id,
        start_date_local=start_date_local,
        start_date_utc=start_date_utc,
        duration_sec=duration_sec,
        sport_type=sport_type,
        session_id=session_id,
        path=rel_path,
        checksum_sha256=checksum,
    )
    save_manifest(manifest)

    logger.info(
        "streams archived: %s (%d bytes gzip, sha256=%s)",
        target,
        target.stat().st_size,
        checksum[:12],
    )
    return target


def read_activity_streams(activity_id: str) -> list[dict[str, Any]] | dict[str, Any] | None:
    """Lit et décompresse l'archive streams d'une activité.

    Retourne None si l'activité n'est pas indexée dans le manifest, ou
    si le fichier gzip est absent/corrompu (log warning). Comportement
    aligné sur ``wellness.read_wellness_day`` pour cohérence UX du
    fallback read-through client.

    Args:
        activity_id: ID Intervals.icu.

    Returns:
        Streams parsées (list ou dict selon shape origine), ou None.
    """
    from magma_cycling.streams.manifest import load_manifest

    manifest = load_manifest()
    entry = manifest.get("activities", {}).get(activity_id)
    if entry is None:
        return None

    file_path = resolve_streams_dir() / entry["path"]
    if not file_path.is_file():
        logger.warning(
            "streams manifest references %s but file missing at %s", activity_id, file_path
        )
        return None

    try:
        with gzip.open(file_path, "rb") as fh:
            return json.loads(fh.read().decode("utf-8"))
    except (OSError, gzip.BadGzipFile, json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning("streams archive corrupted at %s (%s) — treating as absent", file_path, exc)
        return None
