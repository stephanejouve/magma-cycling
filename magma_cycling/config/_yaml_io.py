"""Shared YAML I/O primitives for user-scoped configuration files.

Used by ``geo`` (home_location) and ``objectives`` (priority_objective) — and
any future portable field stored in the user athlete YAML.

Security posture:
- Writes go through ``atomic_write_yaml`` which uses ``os.open`` with explicit
  ``0o600`` mode at creation time (no TOCTOU window between ``open`` and
  ``chmod``), ``fsync`` before atomic ``replace``, and a PID-tagged temp name
  so concurrent writes from the same user do not collide.
- Parent directory is created with ``0o700`` when absent (existing dirs are
  left alone — responsibility delegated upstream).
- Reads silently fall back to ``{}`` on missing / malformed YAML and log a
  short ``warning`` (no traceback) so the file contents are not echoed.

Platform note: POSIX file permission modes (0o600, 0o700) are **not
enforced on Windows** — the OS ignores the ``mode`` argument of ``os.open``
and ``Path.mkdir``. On Windows hosts, user data confidentiality relies on
NTFS ACLs (out of scope here). The hardening applied in this module
protects macOS and Linux deployments fully; Windows hardening would be a
separate workstream (see INFRA-001 for the existing skip convention).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def read_yaml(path: Path) -> dict:
    """Read a YAML file, returning {} for missing / malformed / non-dict roots.

    Logs a short warning (no traceback) on parse errors — the malformed
    payload is not echoed.
    """
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except yaml.YAMLError:
        logger.warning("YAML at %s is malformed; ignoring", path)
        return {}
    return data if isinstance(data, dict) else {}


def atomic_write_yaml(path: Path, data: dict) -> None:
    """Atomic YAML write to ``path`` with 0o600 perms set at creation time.

    Sequence:
    1. ``mkdir`` parent with mode 0o700 if it does not exist (no-op if already
       present — caller owns existing perms).
    2. ``os.open`` a PID-tagged temp file with ``O_WRONLY|O_CREAT|O_TRUNC|
       O_EXCL`` and mode 0o600 (perms applied atomically at creation).
    3. Write + ``fsync`` to flush data + metadata to disk.
    4. ``os.replace`` for atomic crash-safe substitution.
    5. Cleanup the temp file in ``finally`` if replace did not run.
    """
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_suffix(f"{path.suffix}.tmp.{os.getpid()}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_EXCL
    fd = os.open(tmp, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh, default_flow_style=False, sort_keys=False, allow_unicode=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
