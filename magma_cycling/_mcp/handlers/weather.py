"""Weather handlers — wrap magma_cycling_tools.weather lib pour exposition MCP.

Pattern : lazy imports de ``magma_cycling_tools.weather`` à l'intérieur des
handlers, pas au top-level — la lib peut ne pas être installée en CI tools-only
ni dans un dev env minimal, on évite ainsi un ImportError au boot du serveur
MCP. En prod container, la lib est installée via ``pip install
git+https://...magma-cycling-tools.git@main`` (cf docker/Dockerfile).

Politique vigilance orange/rouge (cf note d'archi
``/Users/Shared/NOTE-ARCHI-integration-meteo-magma-cycling.md`` §3) : ces
handlers retournent les données brutes + ``max_color`` calculé. La décision
de bascule indoor (orange = flag décision, rouge = auto-switch) est faite par
le Coach IA / CD, pas par le handler lui-même (cf spec PoC Junior §1
« Claude reste seul décisionnaire »).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from magma_cycling._mcp._utils import mcp_response, suppress_stdout_stderr

if TYPE_CHECKING:
    from mcp.types import TextContent

logger = logging.getLogger(__name__)

__all__ = [
    "handle_get_rain_next_hour",
    "handle_get_vigilance",
    "handle_get_weather_along_route",
    "handle_get_weather_for_session",
]


def _freshness_minutes(reference_dt: datetime | None) -> float | None:
    """Compute minutes elapsed between reference_dt and now (UTC).

    Used to surface data age to the coach LLM so it can weight stale
    forecasts vs server time without recomputing client-side.
    """
    if reference_dt is None:
        return None
    if reference_dt.tzinfo is None:
        reference_dt = reference_dt.replace(tzinfo=UTC)
    delta = datetime.now(UTC) - reference_dt
    return round(delta.total_seconds() / 60.0, 1)


def _missing_circuit_error_payload(reason: str, session_id: str | None = None) -> dict:
    """Build a structured escalation payload when a circuit lookup fails."""
    payload = {
        "status": "missing_circuit",
        "reason": reason,
        "action_required": (
            "Le handler ne fait pas de fallback silencieux. Le Coach IA doit "
            "soit demander à Stéphane d'attacher un circuit terrain à la "
            "session, soit utiliser get-weather-along-route avec un circuit "
            "connu, soit get-rain-next-hour avec coordonnées explicites."
        ),
    }
    if session_id is not None:
        payload["session_id"] = session_id
    return payload


async def handle_get_weather_for_session(args: dict) -> list[TextContent]:
    """Weather forecast for an outdoor session's terrain circuit (10 sample points).

    Loads the session by session_id, checks it is outdoor and has a
    ``terrain_circuit_id``. Escalates if circuit missing (no silent fallback,
    cf spec PoC Junior §6 rule 1). Otherwise samples 10 points along the route
    and forecasts each at its estimated pass-through timestamp.
    """
    session_id = args["session_id"]

    with suppress_stdout_stderr():
        # NOTE: catalog circuits resolution (terrain_circuit_id → coords) is a
        # follow-up scope. For PoC handler this branch returns a structured
        # "not_implemented_yet" payload, leaving room for the future plumbing
        # (mining circuits from Intervals.icu history, cf note d'archi §1.ter
        # chantier 1).
        return mcp_response(
            {
                "status": "not_implemented_yet",
                "handler": "get-weather-for-session",
                "session_id": session_id,
                "reason": (
                    "Resolution session → terrain_circuit_id → GPS coords pas "
                    "encore branchée. Dépend du chantier mining circuits "
                    "depuis Intervals.icu history (cf note d'archi §1.ter)."
                ),
                "interim_workaround": (
                    "Utiliser get-weather-along-route avec un circuit_id "
                    "explicite, ou get-rain-next-hour avec lat/lon."
                ),
            }
        )


async def handle_get_weather_along_route(args: dict) -> list[TextContent]:
    """Weather forecast along a circuit at N=10 sample points."""
    circuit_id = args["circuit_id"]
    start_time_str = args["start_time"]
    avg_speed_kmh = args.get("avg_speed_kmh", 25.0)

    with suppress_stdout_stderr():
        # Idem : circuit_id → coords pas branché pour PoC handler.
        return mcp_response(
            {
                "status": "not_implemented_yet",
                "handler": "get-weather-along-route",
                "circuit_id": circuit_id,
                "start_time": start_time_str,
                "avg_speed_kmh": avg_speed_kmh,
                "reason": (
                    "Resolution circuit_id → TerrainCircuit (waypoints GPS) pas "
                    "encore branchée. Dépend du chantier mining circuits depuis "
                    "Intervals.icu history (cf note d'archi §1.ter)."
                ),
                "interim_workaround": (
                    "Utiliser get-rain-next-hour avec lat/lon des waypoints "
                    "connus du circuit, ou get-vigilance avec le département "
                    "traversé. La composition timestamp passage + segments "
                    "viendra avec la milestone circuit resolution."
                ),
            }
        )


async def handle_get_rain_next_hour(args: dict) -> list[TextContent]:
    """Rain forecast for the next 60 minutes (5-min steps) at a GPS point."""
    lat = args["lat"]
    lon = args["lon"]

    with suppress_stdout_stderr():
        from magma_cycling_tools.weather import get_weather_provider

        try:
            provider = get_weather_provider()
            rain = provider.get_rain_next_hour(lat=lat, lon=lon)
        except Exception as e:  # noqa: BLE001 — surface to caller as structured
            logger.warning("get_rain_next_hour failed: %s", e)
            return mcp_response(
                {
                    "status": "provider_error",
                    "handler": "get-rain-next-hour",
                    "error": str(e),
                    "lat": lat,
                    "lon": lon,
                },
                provider_info={
                    "name": provider.provider_name if "provider" in locals() else "unknown",
                },
            )

        return mcp_response(
            {
                "status": "ok",
                "handler": "get-rain-next-hour",
                "data": rain.model_dump(mode="json"),
                "freshness_minutes": _freshness_minutes(rain.update_time),
                "query": {"lat": lat, "lon": lon},
            },
            provider_info={"name": provider.provider_name},
        )


async def handle_get_vigilance(args: dict) -> list[TextContent]:
    """Vigilance Météo-France bulletin for a French department code."""
    departement = args["departement"]

    with suppress_stdout_stderr():
        from magma_cycling_tools.weather import get_weather_provider

        try:
            provider = get_weather_provider()
            bulletin = provider.get_vigilance(departement=departement)
        except Exception as e:  # noqa: BLE001
            logger.warning("get_vigilance failed for dept %s: %s", departement, e)
            return mcp_response(
                {
                    "status": "provider_error",
                    "handler": "get-vigilance",
                    "error": str(e),
                    "departement": departement,
                },
                provider_info={
                    "name": provider.provider_name if "provider" in locals() else "unknown",
                },
            )

        data = bulletin.model_dump(mode="json")
        # Recommended action surfaced to coach LLM (decision stays with CD, cf
        # spec PoC Junior §1).
        max_color = data.get("max_color", "vert")
        recommended_action = {
            "rouge": "bascule_indoor_recommandee_avec_confirmation",
            "orange": "flag_pour_decision_humaine",
            "jaune": "info_a_presenter_sans_action",
            "vert": "aucune_action",
        }.get(max_color, "aucune_action")

        return mcp_response(
            {
                "status": "ok",
                "handler": "get-vigilance",
                "data": data,
                "recommended_action": recommended_action,
                "freshness_minutes": _freshness_minutes(bulletin.fetched_at),
                "query": {"departement": departement},
            },
            provider_info={"name": provider.provider_name},
        )
