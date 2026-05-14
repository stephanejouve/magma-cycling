"""Decision log helpers (plan iso-config PR8 go-forward strategic decisions).

Public API:
    - DecisionCategory, ImpactHorizon (enums)
    - DecisionRecord (Pydantic v2 model)
    - resolve_decisions_dir() — standalone path resolver
    - decision_archive_path(week_id, seq) — single-file path
    - next_decision_seq(week_id) — find the next NN sequence for the week
    - record_decision(payload) — validate + atomic write + return path
"""

from __future__ import annotations

from magma_cycling.decisions.archive import (
    DecisionCategory,
    DecisionRecord,
    ImpactHorizon,
    decision_archive_path,
    next_decision_seq,
    record_decision,
    resolve_decisions_dir,
)

__all__ = [
    "DecisionCategory",
    "DecisionRecord",
    "ImpactHorizon",
    "decision_archive_path",
    "next_decision_seq",
    "record_decision",
    "resolve_decisions_dir",
]
