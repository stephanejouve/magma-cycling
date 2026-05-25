"""Tests for MCP current-time handler (PR8ter iso-config AC6 levier 2/3)."""

import json
import re
from datetime import datetime, timezone

import pytest

from magma_cycling._mcp.handlers.current_time import handle_current_time


@pytest.mark.asyncio
class TestCurrentTimeHandler:
    """Tests for handle_current_time."""

    async def test_returns_all_expected_fields(self):
        """Handler returns every field required by AC6 spec."""
        result = await handle_current_time({})
        data = json.loads(result[0].text)

        required_fields = {
            "server_time_utc",
            "server_time_local",
            "tz",
            "today_iso",
            "day_of_week_fr",
            "day_of_week_num",
            "iso_year_week",
            "hour_of_day",
            "is_weekend",
        }
        assert required_fields.issubset(data.keys())

    async def test_server_time_utc_is_valid_iso8601(self):
        """server_time_utc is ISO 8601 in UTC."""
        result = await handle_current_time({})
        data = json.loads(result[0].text)

        parsed = datetime.fromisoformat(data["server_time_utc"])
        assert parsed.tzinfo is not None
        assert parsed.utcoffset() == timezone.utc.utcoffset(parsed)

    async def test_server_time_local_is_valid_iso8601_with_offset(self):
        """server_time_local includes timezone offset."""
        result = await handle_current_time({})
        data = json.loads(result[0].text)

        parsed = datetime.fromisoformat(data["server_time_local"])
        assert parsed.tzinfo is not None

    async def test_today_iso_format(self):
        """today_iso matches YYYY-MM-DD pattern."""
        result = await handle_current_time({})
        data = json.loads(result[0].text)

        assert re.match(r"^\d{4}-\d{2}-\d{2}$", data["today_iso"])

    async def test_iso_year_week_format(self):
        """iso_year_week matches YYYY-Www pattern."""
        result = await handle_current_time({})
        data = json.loads(result[0].text)

        assert re.match(r"^\d{4}-W\d{2}$", data["iso_year_week"])

    async def test_day_of_week_fr_is_french(self):
        """day_of_week_fr is one of seven French day names."""
        valid_days = {
            "lundi",
            "mardi",
            "mercredi",
            "jeudi",
            "vendredi",
            "samedi",
            "dimanche",
        }
        result = await handle_current_time({})
        data = json.loads(result[0].text)

        assert data["day_of_week_fr"] in valid_days

    async def test_day_of_week_num_range(self):
        """day_of_week_num is 0..6 (0=lundi convention Python)."""
        result = await handle_current_time({})
        data = json.loads(result[0].text)

        assert 0 <= data["day_of_week_num"] <= 6

    async def test_is_weekend_matches_day_of_week_num(self):
        """is_weekend = True iff day_of_week_num in {5, 6}."""
        result = await handle_current_time({})
        data = json.loads(result[0].text)

        assert data["is_weekend"] == (data["day_of_week_num"] >= 5)

    async def test_hour_of_day_range(self):
        """hour_of_day is 0..23."""
        result = await handle_current_time({})
        data = json.loads(result[0].text)

        assert 0 <= data["hour_of_day"] <= 23

    async def test_utc_and_local_represent_same_instant(self):
        """server_time_utc and server_time_local are the same wall-clock moment."""
        result = await handle_current_time({})
        data = json.loads(result[0].text)

        utc_dt = datetime.fromisoformat(data["server_time_utc"])
        local_dt = datetime.fromisoformat(data["server_time_local"])

        delta = abs((utc_dt - local_dt).total_seconds())
        assert delta < 1.5

    async def test_today_iso_matches_local_date(self):
        """today_iso is the date component of server_time_local."""
        result = await handle_current_time({})
        data = json.loads(result[0].text)

        local_dt = datetime.fromisoformat(data["server_time_local"])
        assert data["today_iso"] == local_dt.date().isoformat()

    async def test_args_dict_is_ignored(self):
        """Handler ignores any input arguments (no input schema beyond {})."""
        result_empty = await handle_current_time({})
        result_with_args = await handle_current_time({"unexpected": "field"})

        data_empty = json.loads(result_empty[0].text)
        data_with_args = json.loads(result_with_args[0].text)

        assert data_empty.keys() == data_with_args.keys()

    async def test_response_includes_mcp_metadata(self):
        """mcp_response wrapper injects _metadata (sanity check)."""
        result = await handle_current_time({})
        data = json.loads(result[0].text)

        assert "_metadata" in data


@pytest.mark.asyncio
class TestCurrentTimeRegistration:
    """Tests for current-time tool registration in MCP server."""

    async def test_tool_is_in_tool_handlers(self):
        """current-time is registered in TOOL_HANDLERS dispatch."""
        from magma_cycling.mcp_server import TOOL_HANDLERS

        assert "current-time" in TOOL_HANDLERS
        assert TOOL_HANDLERS["current-time"] is handle_current_time

    async def test_tool_schema_is_listed(self):
        """current-time tool schema is included in list_tools()."""
        from magma_cycling._mcp.schemas import current_time as _s_ct

        tools = _s_ct.get_tools()
        assert len(tools) == 1
        assert tools[0].name == "current-time"
