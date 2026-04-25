"""Context handoff handlers — save/resume conversational context between MCP sessions."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from magma_cycling._mcp._utils import mcp_response
from magma_cycling.models.handoff import HandoffSnapshot
from magma_cycling.utils.safe_io import safe_read_text, safe_write_text

if TYPE_CHECKING:
    from mcp.types import TextContent

__all__ = ["handle_context_handoff_save", "handle_context_handoff_resume"]

logger = logging.getLogger(__name__)


def _handoff_dir() -> Path:
    """Return the handoff directory, creating it if needed."""
    from magma_cycling.config import get_data_config

    directory = get_data_config().handoff_dir
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _write_snapshot(snapshot: HandoffSnapshot, handoff_dir: Path) -> Path:
    """Serialize snapshot to handoff_dir/YYYY-MM-DD-HHMM.json and return the path.

    On same-minute collision, falls back to second-precision filename.
    """
    filename = snapshot.created_at.strftime("%Y-%m-%d-%H%M") + ".json"
    path = handoff_dir / filename
    if path.exists():
        path = handoff_dir / (snapshot.created_at.strftime("%Y-%m-%d-%H%M%S") + ".json")
    safe_write_text(path, snapshot.model_dump_json(indent=2) + "\n")
    return path


def _latest_unconsumed(handoff_dir: Path) -> tuple[Path, HandoffSnapshot] | None:
    """Return (path, snapshot) of the most-recent non-consumed snapshot, or None."""
    if not handoff_dir.exists():
        return None
    candidates: list[tuple[Path, HandoffSnapshot]] = []
    for path in handoff_dir.glob("*.json"):
        try:
            snap = HandoffSnapshot.model_validate_json(safe_read_text(path))
        except Exception as exc:
            logger.warning("Skipping invalid handoff file %s: %s", path, exc)
            continue
        if snap.consumed:
            continue
        candidates.append((path, snap))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[1].created_at, reverse=True)
    return candidates[0]


async def handle_context_handoff_save(args: dict) -> list[TextContent]:
    """Save a snapshot of conversational context to the training data repo."""
    snapshot = HandoffSnapshot(
        created_at=datetime.now(),
        decisions_pending=args.get("decisions_pending") or [],
        open_questions=args.get("open_questions") or [],
        user_mood=args.get("user_mood") or "",
        next_actions=args.get("next_actions") or [],
        referenced_files=args.get("referenced_files") or [],
    )
    handoff_dir = _handoff_dir()
    path = _write_snapshot(snapshot, handoff_dir)
    logger.info("Handoff snapshot written to %s", path)
    return mcp_response(
        {
            "status": "saved",
            "path": str(path),
            "created_at": snapshot.created_at.isoformat(),
            "summary": {
                "decisions_pending": len(snapshot.decisions_pending),
                "open_questions": len(snapshot.open_questions),
                "next_actions": len(snapshot.next_actions),
                "referenced_files": len(snapshot.referenced_files),
                "has_user_mood": bool(snapshot.user_mood),
            },
        }
    )


async def handle_context_handoff_resume(args: dict) -> list[TextContent]:
    """Load latest non-consumed handoff and return it; mark consumed unless peek."""
    peek = bool(args.get("peek", False))
    handoff_dir = _handoff_dir()
    found = _latest_unconsumed(handoff_dir)
    if found is None:
        return mcp_response({"status": "empty", "snapshot": None})
    path, snapshot = found
    if not peek:
        snapshot.consumed = True
        safe_write_text(path, snapshot.model_dump_json(indent=2) + "\n")
    return mcp_response(
        {
            "status": "resumed" if not peek else "peeked",
            "path": str(path),
            "snapshot": snapshot.model_dump(mode="json"),
        }
    )
