"""Context handoff tool schemas — save/resume conversational state across MCP sessions."""

from mcp.types import Tool


def get_tools() -> list[Tool]:
    """Return context handoff tool schemas."""
    return [
        Tool(
            name="context-handoff-save",
            description=(
                "Save a snapshot of non-persisted conversational context "
                "(pending decisions, open questions, user mood, next actions, "
                "referenced files) to the training data repo so the NEXT session "
                "can resume from it. Use at the end of a long conversation before "
                "closing the session. Written under {training_logs}/handoff/."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "decisions_pending": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Decisions still open at session end.",
                        "default": [],
                    },
                    "open_questions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Questions left unanswered in this session.",
                        "default": [],
                    },
                    "user_mood": {
                        "type": "string",
                        "description": "Athlete's momentary state (one short paragraph).",
                        "default": "",
                    },
                    "next_actions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "TODOs to pick up in the next session.",
                        "default": [],
                    },
                    "referenced_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Paths to artefacts (screenshots, FIT exports, etc.).",
                        "default": [],
                    },
                },
            },
        ),
        Tool(
            name="context-handoff-resume",
            description=(
                "Load the latest non-consumed context-handoff snapshot from the "
                "training data repo and return it. Marks the snapshot as consumed to "
                "prevent double-injection. Use at the START of a new session to "
                "recover conversational context that would otherwise be lost."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "peek": {
                        "type": "boolean",
                        "description": "If true, do not mark the snapshot as consumed.",
                        "default": False,
                    },
                },
            },
        ),
    ]
