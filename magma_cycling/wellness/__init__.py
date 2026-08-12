"""Wellness archive helpers (plan iso-config PR2 + PR2bis, AC2 self-contained).

Public API:
    - resolve_wellness_dir() — standalone path resolver (no DataRepoConfig)
    - wellness_archive_path(date) — single-day file path
    - archive_wellness_day(date, payload) — atomic write
    - wellness_archive_exists(date) — idempotent check (used by backfill)
    - read_wellness_day(date) — single-day read (BT-023, cache fallback)
    - read_wellness_range(oldest, newest) — range read (BT-023)
    - archive_wellness_payload(payload) — best-effort write-through cache (BT-023)
"""

from __future__ import annotations

from magma_cycling.wellness.archive import (
    archive_wellness_day,
    archive_wellness_payload,
    read_wellness_day,
    read_wellness_range,
    resolve_wellness_dir,
    wellness_archive_exists,
    wellness_archive_path,
)

__all__ = [
    "archive_wellness_day",
    "archive_wellness_payload",
    "read_wellness_day",
    "read_wellness_range",
    "resolve_wellness_dir",
    "wellness_archive_exists",
    "wellness_archive_path",
]
