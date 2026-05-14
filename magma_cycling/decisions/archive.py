"""Decision log archive (PR8 plan iso-config — go-forward strategic decisions).

Storage: ``<TRAINING_DATA_ROOT>/data/decisions/decision-SXXX-NN.md``
(shared cross-writers — decisions are per-athlete).

One markdown file per decision with YAML front-matter for structured
metadata. Coach IA P3 §4.2 will refine the schema; this PR ships a
minimal viable shape that can be extended without breaking existing
files.

Granularity (per spec §9 plan iso-config): **strategic only, ≤10/month**.
- Target change (CTL, FTP, mesocycle objective)
- Modal switch (indoor↔outdoor, gear)
- Post-incident athlete rebalance (injury, work load, travel)
- Post-bilan adaptation with impact ≥ S+1
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from magma_cycling.config.data_repo import DECISIONS_SUBDIR, _resolve_root_from_env

logger = logging.getLogger(__name__)

_WEEK_ID_RE = re.compile(r"^S\d{3}$")
_DECISION_FILE_RE = re.compile(r"^decision-(S\d{3})-(\d{2,})\.md$")


class DecisionCategory(str, Enum):
    """Strategic decision categories (per spec §9 plan iso-config)."""

    TARGET_CHANGE = "target_change"
    MODAL_SWITCH = "modal_switch"
    POST_INCIDENT = "post_incident"
    POST_BILAN = "post_bilan"


class ImpactHorizon(str, Enum):
    """Horizon de l'impact attendu (must be ≥ S+1 per spec §9)."""

    S_PLUS_1 = "S+1"
    S_PLUS_2 = "S+2"
    S_PLUS_3 = "S+3"
    MESOCYCLE = "mesocycle"
    MACROCYCLE = "macrocycle"


class DecisionRecord(BaseModel):
    """One strategic decision entry, Pydantic-validated before write."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    week_id: str = Field(description="Week identifier like 'S093'")
    title: str = Field(min_length=1, max_length=200)
    category: DecisionCategory
    description: str = Field(min_length=1)
    impact_horizon: ImpactHorizon
    references: list[str] = Field(
        default_factory=list,
        description="Optional refs (other decision IDs, bilan files, session IDs)",
    )
    recorded_at: datetime | None = Field(
        default=None,
        description="Auto-stamped at write time when None",
    )

    @field_validator("week_id")
    @classmethod
    def _check_week_id(cls, v: str) -> str:
        if not _WEEK_ID_RE.match(v):
            raise ValueError(f"week_id must be 'S' + 3 digits, got {v!r}")
        return v

    @field_validator("recorded_at")
    @classmethod
    def _check_tz_aware(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return None
        if v.tzinfo is None:
            raise ValueError("recorded_at must be timezone-aware")
        return v


def resolve_decisions_dir() -> Path:
    """Resolve ``<TRAINING_DATA_ROOT>/data/decisions/`` without DataRepoConfig.

    Falls back to ``~/data/decisions`` when no env is set (dev local).
    """
    root = _resolve_root_from_env()
    if root is not None:
        return root / DECISIONS_SUBDIR
    return Path.home() / "data" / "decisions"


def decision_archive_path(week_id: str, seq: int) -> Path:
    """Path du fichier d'une décision donnée.

    Args:
        week_id: ``S\\d{3}`` (ex. ``S094``).
        seq: numéro de séquence dans la semaine, ≥ 1.
    """
    if not _WEEK_ID_RE.match(week_id):
        raise ValueError(f"week_id must be 'S' + 3 digits, got {week_id!r}")
    if seq < 1:
        raise ValueError(f"seq must be >= 1, got {seq}")
    return resolve_decisions_dir() / f"decision-{week_id}-{seq:02d}.md"


def next_decision_seq(week_id: str) -> int:
    """Return the next ``NN`` sequence available for ``week_id``."""
    if not _WEEK_ID_RE.match(week_id):
        raise ValueError(f"week_id must be 'S' + 3 digits, got {week_id!r}")
    base = resolve_decisions_dir()
    if not base.is_dir():
        return 1
    used: set[int] = set()
    for entry in base.iterdir():
        m = _DECISION_FILE_RE.match(entry.name)
        if m and m.group(1) == week_id:
            used.add(int(m.group(2)))
    if not used:
        return 1
    return max(used) + 1


def _render_markdown(record: DecisionRecord) -> str:
    """Render the decision file content: YAML front-matter + body."""
    front = {
        "week_id": record.week_id,
        "title": record.title,
        "category": record.category.value,
        "impact_horizon": record.impact_horizon.value,
        "recorded_at": (record.recorded_at or datetime.now(tz=timezone.utc)).isoformat(),
        "references": list(record.references),
    }
    front_yaml = yaml.safe_dump(
        front, default_flow_style=False, sort_keys=False, allow_unicode=True
    )
    return f"---\n{front_yaml}---\n\n# {record.title}\n\n{record.description}\n"


def record_decision(record: DecisionRecord) -> Path:
    """Persist a decision atomically, return the file path written.

    The sequence number ``NN`` is computed at write time (next available),
    so callers don't need to track it. Atomic via tmp + replace.
    """
    seq = next_decision_seq(record.week_id)
    target = decision_archive_path(record.week_id, seq)
    target.parent.mkdir(parents=True, exist_ok=True)
    content = _render_markdown(record)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.chmod(tmp, 0o644)
    tmp.replace(target)
    logger.info("decision recorded: %s", target)
    return target
