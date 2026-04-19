"""Context handoff snapshot model.

A HandoffSnapshot captures the conversational soft-state that is lost when an MCP
session ends: pending decisions, open questions, user mood, next actions. The MCP
server writes one file per snapshot under {training_logs}/handoff/ and the next
session reads the latest non-consumed one to recover context.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HandoffSnapshot(BaseModel):
    """One saved conversation handoff between MCP sessions."""

    created_at: datetime = Field(description="When the snapshot was written.")
    decisions_pending: list[str] = Field(
        default_factory=list,
        description="Open decisions not yet committed to planning or calendar.",
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="Questions left unanswered in the prior session.",
    )
    user_mood: str = Field(
        default="",
        description="Athlete's momentary state (fatigue, motivation, constraints).",
    )
    next_actions: list[str] = Field(
        default_factory=list,
        description="Follow-up TODOs for the next conversation.",
    )
    referenced_files: list[str] = Field(
        default_factory=list,
        description="Paths to artefacts evoked in the conversation (screenshots, FIT, etc.).",
    )
    consumed: bool = Field(
        default=False,
        description="True once read by context-handoff-resume; prevents double-injection.",
    )
