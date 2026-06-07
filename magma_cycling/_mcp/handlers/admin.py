"""Admin handlers."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from magma_cycling._mcp._utils import mcp_response, suppress_stdout_stderr

if TYPE_CHECKING:
    from mcp.types import TextContent

logger = logging.getLogger(__name__)

__all__ = [
    "handle_reload_server",
    "handle_report_config_file_state",
    "handle_system_info",
]


_SELF_REPORT_DISCLAIMER = (
    "Reports the current sha256 and permissions of bundled + user YAML "
    "config files as seen by the running container. Not an external "
    "integrity attestation — a compromised container could mis-report. "
    "For external verification, inspect image overlay layers directly "
    "(docker cp / image diff from host)."
)


async def handle_reload_server(args: dict) -> list[TextContent]:
    """Reload MCP server modules (dev tool for hot reload without restarting Claude Desktop)."""
    import importlib
    import sys

    try:
        # List of modules to reload (in dependency order)
        modules_to_reload = [
            "magma_cycling.config",
            "magma_cycling.planning.models",
            "magma_cycling.planning.control_tower",
            "magma_cycling.daily_sync",
            "magma_cycling.weekly_planner",
            # Add other modules as needed
        ]

        reloaded = []
        failed = []

        for module_name in modules_to_reload:
            try:
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                    reloaded.append(module_name)
            except Exception as e:
                failed.append({"module": module_name, "error": str(e)})

        result = {
            "success": len(failed) == 0,
            "reloaded_count": len(reloaded),
            "reloaded_modules": reloaded,
            "failed": failed,
            "message": (
                f"✅ Reloaded {len(reloaded)} modules"
                if len(failed) == 0
                else f"⚠️ Reloaded {len(reloaded)} modules, {len(failed)} failed"
            ),
            "note": "MCP server handlers NOT reloaded (requires watchdog auto-restart or manual restart)",
        }

        return mcp_response(result)

    except Exception as e:
        return mcp_response(
            {
                "error": f"Reload failed: {str(e)}",
                "message": "⚠️ Module reload error - may need full restart",
            }
        )


def _file_state(path: Path) -> dict:
    """Return self-reported state (exists, size, perms_octal, sha256) for one path.

    Pure read-only — no side effect, no mutation. Hashes the file content
    in 8 KiB chunks (memory-bounded for large files). Missing file is not
    an error, returns ``{"exists": False}`` so callers can degrade gracefully.
    """
    state: dict = {"path": str(path), "exists": path.exists()}
    if not state["exists"]:
        return state
    try:
        st = path.stat()
        state["size_bytes"] = st.st_size
        state["perms_octal"] = oct(st.st_mode & 0o777)[2:].zfill(3)
        sha = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                sha.update(chunk)
        state["sha256"] = sha.hexdigest()
    except OSError as exc:
        state["error"] = f"stat/read failed: {exc}"
    return state


def _parent_dir_state(path: Path) -> dict:
    """Return self-reported state of the parent directory (perms only)."""
    parent = path.parent
    info: dict = {"path": str(parent), "exists": parent.exists()}
    if not info["exists"]:
        return info
    try:
        info["perms_octal"] = oct(parent.stat().st_mode & 0o777)[2:].zfill(3)
    except OSError as exc:
        info["error"] = f"stat failed: {exc}"
    return info


async def handle_report_config_file_state(args: dict) -> list[TextContent]:
    """Report self-reported state of bundled + user YAML config files.

    See :data:`_SELF_REPORT_DISCLAIMER` for the boundary of what this tool
    can attest to. In short: this is what the running container *sees*, not
    an external integrity check.

    Input:
      - ``scope``: ``"bundle"`` | ``"user_yaml"`` | ``"both"`` (default ``"both"``)

    Output (per scope):
      - ``bundle.{path, exists, size_bytes, perms_octal, sha256}``
      - ``user_yaml.{path, exists, size_bytes, perms_octal, sha256, parent_dir.{path, exists, perms_octal}}``
    """
    from magma_cycling.config.athlete_context import BUNDLE_ATHLETE_YAML
    from magma_cycling.config.data_repo import resolve_athlete_yaml_path

    scope = args.get("scope", "both")
    if scope not in ("bundle", "user_yaml", "both"):
        return mcp_response(
            {
                "error": f"invalid scope {scope!r}, expected one of: bundle, user_yaml, both",
            }
        )

    result: dict = {"self_reported": True, "note": _SELF_REPORT_DISCLAIMER}

    if scope in ("bundle", "both"):
        result["bundle"] = _file_state(BUNDLE_ATHLETE_YAML)

    if scope in ("user_yaml", "both"):
        try:
            user_path = resolve_athlete_yaml_path()
        except Exception as exc:
            result["user_yaml"] = {"error": f"resolve_athlete_yaml_path() failed: {exc}"}
        else:
            user_state = _file_state(user_path)
            user_state["parent_dir"] = _parent_dir_state(user_path)
            result["user_yaml"] = user_state

    return mcp_response(result)


async def handle_system_info(args: dict) -> list[TextContent]:
    """Return active providers and system metadata."""
    with suppress_stdout_stderr():
        from magma_cycling.health import create_health_provider

        # Health provider
        try:
            health_provider = create_health_provider()
            health_info = health_provider.get_provider_info()
        except Exception as e:
            health_info = {"provider": "unavailable", "status": "error", "error": str(e)}

        # Calendar provider
        try:
            from magma_cycling.config import create_intervals_client

            calendar_client = create_intervals_client()
            calendar_info = calendar_client.get_provider_info()
        except Exception as e:
            calendar_info = {"provider": "unavailable", "status": "error", "error": str(e)}

        # AI providers (list configured ones).
        #
        # Bug d'origine : l'ancienne implémentation appelait
        # ``AIProviderFactory.create(provider_name)`` avec **un seul argument**
        # alors que la signature exige ``(provider: str, config: dict)``. Chaque
        # itération levait ``TypeError: create() missing 1 required positional
        # argument: 'config'`` qui était avalée par le ``except Exception: pass``
        # silencieux — d'où ``ai_providers: []`` constant alors que Mistral est
        # démontrablement actif en prod (``daily-sync`` 27/04 écrit
        # ``ai_provider: MistralAPIAnalyzer``, ``get-coach-analysis`` produit
        # des analyses Mistral).
        #
        # Fix : utiliser ``AIConfig.get_available_providers()`` qui retourne
        # directement la liste des providers configurés (mêmes paths que
        # ``daily_sync.py:150-155`` qui fonctionne en prod). Plus de probe via
        # Factory à 1 arg manquant, plus de TypeError silenced.
        ai_info: list[str] = []
        try:
            from magma_cycling.config import get_ai_config

            ai_info = get_ai_config().get_available_providers()
        except Exception as e:
            logger.warning("ai_provider discovery failed: %s", e)

        # Tool count — single source of truth = TOOL_HANDLERS (qu'on dispatche
        # en runtime). L'ancienne implémentation re-listait 10 schemas et
        # oubliait `terrain` (4) + `handoff` (2), retournant 54 au lieu de 60.
        # Avec TOOL_HANDLERS on a une garantie : ce que system-info compte
        # est ce que le serveur peut réellement exécuter.
        try:
            from magma_cycling.mcp_server import TOOL_HANDLERS

            tool_count = len(TOOL_HANDLERS)
        except Exception:
            tool_count = -1

        # Version et data repo info — utiles pour TNR post-déploiement.
        try:
            from magma_cycling import __version__ as version
        except Exception:
            version = "unknown"

        data_repo_path: str | None = None
        data_repo_health_ok = False
        try:
            from magma_cycling.config import get_data_config

            cfg = get_data_config()
            data_repo_path = str(cfg.data_repo_path)
            data_repo_health_ok = (
                cfg.data_repo_path.exists() and (cfg.data_repo_path / ".git").exists()
            )
        except Exception as e:
            logger.warning("data_repo discovery failed: %s", e)

        result = {
            "version": version,
            "health": health_info,
            "calendar": calendar_info,
            "ai_providers": ai_info,
            "tool_count": tool_count,
            "data_repo_path": data_repo_path,
            "data_repo_health_ok": data_repo_health_ok,
        }

    return mcp_response(result)
