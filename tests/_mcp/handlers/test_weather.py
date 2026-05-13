"""Tests for _mcp/handlers/weather.py (wrap magma_cycling_tools.weather)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip(
    "magma_cycling_tools",
    reason="magma-cycling-tools optional dep; installed via Dockerfile in prod, "
    "skip in CI dev minimal",
)

from magma_cycling._mcp.handlers.weather import (  # noqa: E402
    handle_get_rain_next_hour,
    handle_get_vigilance,
    handle_get_weather_along_route,
    handle_get_weather_for_session,
)


class TestToolSchemasExposed:
    """Verify the 4 weather tools are wired in the MCP server."""

    def test_tools_in_tool_handlers(self):
        from magma_cycling.mcp_server import TOOL_HANDLERS

        assert "get-weather-for-session" in TOOL_HANDLERS
        assert "get-weather-along-route" in TOOL_HANDLERS
        assert "get-rain-next-hour" in TOOL_HANDLERS
        assert "get-vigilance" in TOOL_HANDLERS

    def test_schemas_emitted_by_list_tools(self):
        from magma_cycling._mcp.schemas import weather as schemas_weather

        names = [t.name for t in schemas_weather.get_tools()]
        assert sorted(names) == [
            "get-rain-next-hour",
            "get-vigilance",
            "get-weather-along-route",
            "get-weather-for-session",
        ]


class TestGetRainNextHour:
    """handle_get_rain_next_hour wraps provider.get_rain_next_hour."""

    @pytest.mark.asyncio
    async def test_happy_path_returns_data_with_metadata(self):
        from magma_cycling_tools.weather import RainForecast, RainIntensity, RainSlot

        fake_rain = RainForecast(
            lat=45.7,
            lon=3.4,
            update_time=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
            slots=[
                RainSlot(minutes_from_now=0, intensity=RainIntensity.SEC, intensity_code=1),
                RainSlot(
                    minutes_from_now=5,
                    intensity=RainIntensity.PLUIE_FAIBLE,
                    intensity_code=2,
                ),
            ],
        )

        fake_provider = MagicMock()
        fake_provider.provider_name = "meteofrance_community"
        fake_provider.get_rain_next_hour.return_value = fake_rain

        with patch(
            "magma_cycling_tools.weather.get_weather_provider",
            return_value=fake_provider,
        ):
            result = await handle_get_rain_next_hour({"lat": 45.7, "lon": 3.4})

        data = json.loads(result[0].text)
        assert data["status"] == "ok"
        assert data["handler"] == "get-rain-next-hour"
        assert "data" in data
        assert data["query"]["lat"] == 45.7
        assert data["query"]["lon"] == 3.4
        assert data["_metadata"]["provider"]["name"] == "meteofrance_community"
        assert "response_timestamp" in data["_metadata"]
        assert "freshness_minutes" in data
        assert isinstance(data["freshness_minutes"], int | float)

    @pytest.mark.asyncio
    async def test_provider_error_surfaces_structured(self):
        fake_provider = MagicMock()
        fake_provider.provider_name = "meteofrance_community"
        fake_provider.get_rain_next_hour.side_effect = RuntimeError("API down")

        with patch(
            "magma_cycling_tools.weather.get_weather_provider",
            return_value=fake_provider,
        ):
            result = await handle_get_rain_next_hour({"lat": 45.7, "lon": 3.4})

        data = json.loads(result[0].text)
        assert data["status"] == "provider_error"
        assert "API down" in data["error"]


class TestGetVigilance:
    """handle_get_vigilance wraps provider.get_vigilance + adds recommended_action."""

    def _fake_bulletin(self, max_color: str):
        from magma_cycling_tools.weather import VigilanceBulletin, VigilanceColor

        return VigilanceBulletin(
            departement="63",
            max_color=VigilanceColor(max_color),
            phenomena=[],
            fetched_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "max_color,expected_action",
        [
            ("vert", "aucune_action"),
            ("jaune", "info_a_presenter_sans_action"),
            ("orange", "flag_pour_decision_humaine"),
            ("rouge", "bascule_indoor_recommandee_avec_confirmation"),
        ],
    )
    async def test_recommended_action_per_color(self, max_color, expected_action):
        fake_provider = MagicMock()
        fake_provider.provider_name = "meteofrance_community"
        fake_provider.get_vigilance.return_value = self._fake_bulletin(max_color)

        with patch(
            "magma_cycling_tools.weather.get_weather_provider",
            return_value=fake_provider,
        ):
            result = await handle_get_vigilance({"departement": "63"})

        data = json.loads(result[0].text)
        assert data["status"] == "ok"
        assert data["recommended_action"] == expected_action
        assert data["data"]["max_color"] == max_color
        assert "freshness_minutes" in data
        assert isinstance(data["freshness_minutes"], int | float)


class TestStubHandlers:
    """handlers get-weather-for-session + get-weather-along-route stubs (circuit resolution pending)."""

    @pytest.mark.asyncio
    async def test_get_weather_for_session_returns_stub(self):
        result = await handle_get_weather_for_session({"session_id": "S093-04"})
        data = json.loads(result[0].text)
        assert data["status"] == "not_implemented_yet"
        assert data["session_id"] == "S093-04"
        assert "interim_workaround" in data

    @pytest.mark.asyncio
    async def test_get_weather_along_route_returns_stub(self):
        result = await handle_get_weather_along_route(
            {
                "circuit_id": "chataigneraie-56km",
                "start_time": "2026-05-17T14:00:00+02:00",
            }
        )
        data = json.loads(result[0].text)
        assert data["status"] == "not_implemented_yet"
        assert data["circuit_id"] == "chataigneraie-56km"
        assert "interim_workaround" in data
        assert "get-rain-next-hour" in data["interim_workaround"]
