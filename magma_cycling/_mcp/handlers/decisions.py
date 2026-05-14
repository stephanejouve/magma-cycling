"""Decision log handlers (PR8 plan iso-config — record-decision MCP tool)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from magma_cycling._mcp._utils import mcp_response
from magma_cycling.decisions import DecisionRecord, record_decision

if TYPE_CHECKING:
    from mcp.types import TextContent

__all__ = ["handle_record_decision"]


async def handle_record_decision(args: dict) -> list[TextContent]:
    """Validate + persist a strategic decision in the go-forward log."""
    try:
        record = DecisionRecord.model_validate(args)
    except Exception as exc:  # noqa: BLE001 — surface pydantic ValidationError as-is
        return mcp_response(
            {
                "error": f"invalid decision payload: {exc}",
                "args": args,
            }
        )

    try:
        target = record_decision(record)
    except OSError as exc:
        return mcp_response(
            {
                "error": f"failed to write decision file: {exc}",
                "args": args,
            }
        )

    return mcp_response(
        {
            "success": True,
            "path": str(target),
            "week_id": record.week_id,
            "category": record.category.value,
            "impact_horizon": record.impact_horizon.value,
        }
    )
