"""Tests for _mcp/handlers/athlete.py — focus on home_location dispatch (MCT-XXX-0)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from magma_cycling._mcp.handlers.athlete import (
    handle_get_athlete_profile,
    handle_update_athlete_profile,
)
from magma_cycling._mcp.schemas import athlete as athlete_schema


@pytest.fixture
def isolated_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect get_athlete_yaml_path to a temp file for isolation."""
    yaml_path = tmp_path / "athlete.yaml"
    # Both the geo module and athlete_context import the resolver — patch it
    # at the source so every caller redirects.
    monkeypatch.setattr(
        "magma_cycling.config.geo.get_athlete_yaml_path",
        lambda: yaml_path,
    )
    return yaml_path


def _payload(result: list) -> dict:
    """Decode the JSON body of an MCP TextContent response."""
    assert result and len(result) == 1
    return json.loads(result[0].text)


class TestSchema:
    def test_home_location_in_input_schema(self):
        tools = {t.name: t for t in athlete_schema.get_tools()}
        update = tools["update-athlete-profile"]
        props = update.inputSchema["properties"]["updates"]["properties"]
        assert "home_location" in props
        loc_schema = props["home_location"]
        assert loc_schema["properties"]["lat"]["minimum"] == -90
        assert loc_schema["properties"]["lon"]["maximum"] == 180
        assert "label" in loc_schema["properties"]
        assert loc_schema["required"] == ["lat", "lon"]


class TestUpdateHomeLocation:
    @pytest.mark.asyncio
    async def test_home_location_writes_yaml_only(self, isolated_yaml: Path):
        # No Intervals.icu client patch: handler must not call it when the
        # payload contains only local fields.
        result = await handle_update_athlete_profile(
            {"updates": {"home_location": {"lat": 45.69, "lon": 3.34, "label": "Chas"}}}
        )
        body = _payload(result)
        assert body["success"] is True
        assert body["updated_fields"] == ["home_location"]
        assert body["current_values"]["home_location"] == {
            "lat": 45.69,
            "lon": 3.34,
            "label": "Chas",
        }
        # YAML persisted
        data = yaml.safe_load(isolated_yaml.read_text(encoding="utf-8"))
        assert data["athlete"]["home_location"]["lat"] == 45.69

    @pytest.mark.asyncio
    async def test_remote_only_does_not_touch_yaml(self, isolated_yaml: Path):
        fake_client = MagicMock()
        fake_client.update_athlete.return_value = {"icu_weight": 84.0, "ftp": 230}
        with patch("magma_cycling.config.create_intervals_client", return_value=fake_client):
            result = await handle_update_athlete_profile({"updates": {"ftp": 230, "weight": 84.0}})
        body = _payload(result)
        assert body["success"] is True
        assert sorted(body["updated_fields"]) == ["ftp", "weight"]
        assert not isolated_yaml.exists()  # local YAML untouched
        fake_client.update_athlete.assert_called_once_with({"ftp": 230, "weight": 84.0})

    @pytest.mark.asyncio
    async def test_mixed_payload_dispatches_both(self, isolated_yaml: Path):
        fake_client = MagicMock()
        fake_client.update_athlete.return_value = {"ftp": 230}
        with patch("magma_cycling.config.create_intervals_client", return_value=fake_client):
            result = await handle_update_athlete_profile(
                {
                    "updates": {
                        "ftp": 230,
                        "home_location": {"lat": 45.69, "lon": 3.34},
                    }
                }
            )
        body = _payload(result)
        assert body["success"] is True
        assert set(body["updated_fields"]) == {"home_location", "ftp"}
        # Remote got only ftp, not home_location
        fake_client.update_athlete.assert_called_once_with({"ftp": 230})
        # YAML has the location
        data = yaml.safe_load(isolated_yaml.read_text(encoding="utf-8"))
        assert data["athlete"]["home_location"] == {"lat": 45.69, "lon": 3.34}

    @pytest.mark.asyncio
    async def test_invalid_home_location_returns_error(self, isolated_yaml: Path):
        result = await handle_update_athlete_profile(
            {"updates": {"home_location": {"lat": 200, "lon": 0}}}
        )
        body = _payload(result)
        assert "error" in body
        assert not isolated_yaml.exists()


class TestGetHomeLocation:
    @pytest.mark.asyncio
    async def test_get_returns_none_when_yaml_absent(self, isolated_yaml: Path):
        fake_client = MagicMock()
        fake_client.get_athlete.return_value = {
            "name": "Test",
            "sportSettings": [{"types": ["Ride"], "ftp": 230}],
            "icu_weight": 84.0,
        }
        with patch("magma_cycling.config.create_intervals_client", return_value=fake_client):
            result = await handle_get_athlete_profile({})
        body = _payload(result)
        assert body["home_location"] is None
        assert body["ftp"] == 230  # remote part still works

    @pytest.mark.asyncio
    async def test_get_returns_saved_home_location(self, isolated_yaml: Path):
        isolated_yaml.write_text(
            "athlete:\n  home_location:\n    lat: 45.69\n    lon: 3.34\n    label: Chas\n",
            encoding="utf-8",
        )
        fake_client = MagicMock()
        fake_client.get_athlete.return_value = {
            "name": "Test",
            "sportSettings": [{"types": ["Ride"], "ftp": 230}],
        }
        with patch("magma_cycling.config.create_intervals_client", return_value=fake_client):
            result = await handle_get_athlete_profile({})
        body = _payload(result)
        assert body["home_location"] == {"lat": 45.69, "lon": 3.34, "label": "Chas"}
