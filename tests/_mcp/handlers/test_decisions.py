"""Tests for the record-decision MCP handler (PR8 plan iso-config)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from magma_cycling._mcp.handlers.decisions import handle_record_decision
from magma_cycling._mcp.schemas import decisions as schemas_decisions
from magma_cycling.config.data_repo import DECISIONS_SUBDIR, LEGACY_ROOT_ENV, ROOT_ENV


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for v in (ROOT_ENV, LEGACY_ROOT_ENV):
        monkeypatch.delenv(v, raising=False)


def _payload(result: list) -> dict:
    assert result and len(result) == 1
    return json.loads(result[0].text)


class TestSchema:
    def test_tool_exposed(self):
        names = [t.name for t in schemas_decisions.get_tools()]
        assert names == ["record-decision"]

    def test_required_fields(self):
        tool = schemas_decisions.get_tools()[0]
        assert sorted(tool.inputSchema["required"]) == [
            "category",
            "description",
            "impact_horizon",
            "title",
            "week_id",
        ]

    def test_registered_in_tool_handlers(self):
        from magma_cycling.mcp_server import TOOL_HANDLERS

        assert "record-decision" in TOOL_HANDLERS


class TestHandler:
    @pytest.mark.asyncio
    async def test_record_writes_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        result = await handle_record_decision(
            {
                "week_id": "S094",
                "title": "Bascule indoor",
                "category": "modal_switch",
                "description": "Météo orage prévue, bascule indoor pour S+1",
                "impact_horizon": "S+1",
                "references": [],
            }
        )
        body = _payload(result)
        assert body["success"] is True
        assert body["week_id"] == "S094"
        assert body["category"] == "modal_switch"
        target = Path(body["path"])
        assert target.exists()
        assert target.parent == tmp_path / DECISIONS_SUBDIR
        assert target.name == "decision-S094-01.md"

    @pytest.mark.asyncio
    async def test_sequence_increments(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        common = {
            "week_id": "S094",
            "category": "post_bilan",
            "description": "d",
            "impact_horizon": "S+1",
        }
        await handle_record_decision({"title": "d1", **common})
        result = await handle_record_decision({"title": "d2", **common})
        body = _payload(result)
        assert Path(body["path"]).name == "decision-S094-02.md"

    @pytest.mark.asyncio
    async def test_invalid_payload_returns_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        # Missing required field 'description'
        result = await handle_record_decision(
            {
                "week_id": "S094",
                "title": "t",
                "category": "target_change",
                "impact_horizon": "S+1",
            }
        )
        body = _payload(result)
        assert "error" in body
        assert "invalid decision payload" in body["error"]

    @pytest.mark.asyncio
    async def test_invalid_week_id_returns_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        result = await handle_record_decision(
            {
                "week_id": "94",
                "title": "t",
                "category": "target_change",
                "description": "d",
                "impact_horizon": "S+1",
            }
        )
        body = _payload(result)
        assert "error" in body
