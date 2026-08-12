"""Cold archive of Intervals.icu activity streams (BT-025, Axe 2 rang 2b).

Souveraineté des données longue durée : chaque activité (watts, HR,
cadence, altitude, etc.) est exportée en JSON gzip vers
``training-logs/data/streams/YYYY/MM/<activity_id>.json.gz``, indexée par
un ``manifest.json`` qui rend la restauration index-driven et l'export
idempotent sans stat disque.

Public API:
    - resolve_streams_dir() — path resolver (env override + fallback)
    - partition_from_local_dt(dt_local) — YYYY/MM depuis un datetime
      naive local (Q-K : jamais dérivé de la TZ container)
    - streams_archive_path(activity_id, dt_local) — full path .json.gz
    - streams_archive_exists(activity_id) — check idempotent via manifest
    - archive_activity_streams(activity_id, streams, metadata) — write
      atomic gzip + manifest update
    - read_activity_streams(activity_id) — read + decompress
    - manifest helpers (load_manifest, save_manifest, add_manifest_entry)
"""

from __future__ import annotations

from magma_cycling.streams.archive import (
    archive_activity_streams,
    partition_from_local_dt,
    read_activity_streams,
    resolve_streams_dir,
    streams_archive_exists,
    streams_archive_path,
)
from magma_cycling.streams.manifest import (
    add_manifest_entry,
    compute_sha256,
    load_manifest,
    manifest_path,
    save_manifest,
    verify_checksum,
)

__all__ = [
    "add_manifest_entry",
    "archive_activity_streams",
    "compute_sha256",
    "load_manifest",
    "manifest_path",
    "partition_from_local_dt",
    "read_activity_streams",
    "resolve_streams_dir",
    "save_manifest",
    "streams_archive_exists",
    "streams_archive_path",
    "verify_checksum",
]
