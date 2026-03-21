"""Admin handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from magma_cycling._mcp._utils import mcp_response, suppress_stdout_stderr

if TYPE_CHECKING:
    from mcp.types import TextContent

__all__ = [
    "handle_reload_server",
    "handle_system_info",
]


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

        # AI providers (list configured ones)
        ai_info: list[str] = []
        try:
            from magma_cycling.ai_providers.factory import AIProviderFactory

            for provider_name in ("claude_api", "mistral_api", "ollama"):
                try:
                    analyzer = AIProviderFactory.create(provider_name)
                    if analyzer.validate_config():
                        ai_info.append(provider_name)
                except Exception:
                    pass
        except Exception:
            pass

        # Tool count
        try:
            from magma_cycling._mcp.schemas import admin as _s_admin
            from magma_cycling._mcp.schemas import analysis as _s_analysis
            from magma_cycling._mcp.schemas import athlete as _s_athlete
            from magma_cycling._mcp.schemas import catalog as _s_catalog
            from magma_cycling._mcp.schemas import health as _s_health
            from magma_cycling._mcp.schemas import planning as _s_planning
            from magma_cycling._mcp.schemas import remote as _s_remote
            from magma_cycling._mcp.schemas import rest as _s_rest
            from magma_cycling._mcp.schemas import sessions as _s_sessions
            from magma_cycling._mcp.schemas import workouts as _s_workouts

            tool_count = sum(
                len(mod.get_tools())
                for mod in (
                    _s_planning,
                    _s_sessions,
                    _s_workouts,
                    _s_remote,
                    _s_athlete,
                    _s_analysis,
                    _s_admin,
                    _s_catalog,
                    _s_health,
                    _s_rest,
                )
            )
        except Exception:
            tool_count = -1

        result = {
            "health": health_info,
            "calendar": calendar_info,
            "ai_providers": ai_info,
            "tool_count": tool_count,
        }

    return mcp_response(result)
