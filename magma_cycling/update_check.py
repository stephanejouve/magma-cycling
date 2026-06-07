"""Best-effort update-availability probe at MCP server startup.

Polls the GitHub Releases API once per ``CACHE_TTL_SECONDS`` and compares the
running ``__version__`` with the latest published tag. The result is cached on
disk so that subsequent startups do not hit the network until the TTL expires.

Designed so that **every failure mode is silent and non-blocking** : the MCP
server must boot exactly the same whether an update exists, the network is
down, the GitHub API is rate-limited, or the user opted out. The only side
effect is one optional ``stderr`` line at boot when an update is detected.

Opt-out hooks :

* ``MAGMA_NO_UPDATE_CHECK=1`` env var.
* ``--no-update-check`` CLI flag (handled by the caller).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

import requests

from magma_cycling import __version__

logger = logging.getLogger(__name__)

GITHUB_LATEST_URL = "https://api.github.com/repos/stephanejouve/magma-cycling/releases/latest"
DEFAULT_TIMEOUT_SECONDS = 2.0
CACHE_TTL_SECONDS = 86400  # 24 h
ENV_OPT_OUT = "MAGMA_NO_UPDATE_CHECK"


def _cache_path() -> Path:
    home = Path.home()
    return home / ".cache" / "magma-cycling" / "update_check.json"


def _normalise_tag(raw: str) -> str:
    """Strip a leading ``v`` so ``v3.51.1`` and ``3.51.1`` compare equal."""
    return raw.lstrip("v")


def _read_cache() -> dict | None:
    path = _cache_path()
    if not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _write_cache(latest_tag: str, html_url: str) -> None:
    path = _cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(
                {"checked_at": time.time(), "latest_tag": latest_tag, "url": html_url},
                f,
            )
    except OSError:
        # Cache write is purely an optimisation, never fatal.
        pass


def check_for_updates(
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    cache_ttl: int = CACHE_TTL_SECONDS,
    current_version: str | None = None,
) -> str | None:
    """Return an update URL if a newer release exists, else ``None``.

    Args:
        timeout: requests timeout in seconds. Kept short so MCP boot stays snappy.
        cache_ttl: how long to trust a previous lookup (seconds).
        current_version: override for the running version (tests only).

    Returns:
        ``str`` URL of the release page when an update is detected, else
        ``None``. **Never raises** — any error path returns ``None``.
    """
    if os.environ.get(ENV_OPT_OUT, "").strip() in {"1", "true", "yes"}:
        return None

    running = _normalise_tag(current_version or __version__)

    cached = _read_cache()
    now = time.time()
    if cached and (now - float(cached.get("checked_at", 0))) < cache_ttl:
        latest = _normalise_tag(str(cached.get("latest_tag", "")))
        url = str(cached.get("url", ""))
        return url if (latest and url and latest != running) else None

    try:
        resp = requests.get(
            GITHUB_LATEST_URL,
            timeout=timeout,
            headers={"Accept": "application/vnd.github+json"},
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError, json.JSONDecodeError):
        # Silent failure — never block boot or surface noise.
        logger.debug("update_check probe failed silently", exc_info=True)
        return None

    latest_raw = str(data.get("tag_name", ""))
    latest = _normalise_tag(latest_raw)
    html_url = str(data.get("html_url", ""))
    if not latest or not html_url:
        return None

    _write_cache(latest_raw, html_url)
    return html_url if latest != running else None


def announce_update_if_any() -> None:
    """Print one stderr line if an update is available. Safe to call at boot."""
    try:
        url = check_for_updates()
    except Exception:
        # Triple-safety belt — the helper already swallows but we never let
        # update-check crash the server.
        return
    if not url:
        return
    print(f"📢 Update disponible — télécharger : {url}", file=sys.stderr, flush=True)
