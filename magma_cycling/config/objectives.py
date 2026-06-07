"""Priority training objective stored in the athlete YAML.

Hosts :class:`PriorityObjective` (event-style training goal with target date)
and the ``priority_objective`` read/write helpers backing the
``update-athlete-profile`` MCP handler dispatch (see
``magma_cycling/_mcp/handlers/athlete.py``).

The data lives in the athlete YAML resolved by
:func:`magma_cycling.config.data_repo.resolve_athlete_yaml_path` — the
**user-local** YAML, never the bundle. The bundle stays generic/template.

Migration noop: if ``priority_objective`` is absent from the YAML,
:func:`load_priority_objective` returns ``None``.
"""

from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from magma_cycling.config.data_repo import resolve_athlete_yaml_path

logger = logging.getLogger(__name__)


class PriorityObjective(BaseModel):
    """A priority training objective with a target date.

    Mirrors the ``TrainingObjective`` dataclass in ``planning_manager`` but
    typed as a pydantic model so it can be validated at the MCP boundary.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, description="Event or objective name")
    type: str = Field(min_length=1, description="granfondo, race, ftp_test, ...")
    target_date: date = Field(description="Target date (YYYY-MM-DD)")
    priority: str = Field(default="A", description="A, B, C")
    distance_km: float | None = Field(default=None, gt=0, description="Optional distance")
    notes: str | None = Field(default=None, description="Free-form notes")


def _atomic_write_yaml(path: Path, data: dict) -> None:
    """Atomic YAML write via tmp + replace, preserves perms via 0o600."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, default_flow_style=False, sort_keys=False, allow_unicode=True)
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except yaml.YAMLError:
        logger.exception("Failed to parse %s", path)
        return {}
    return data if isinstance(data, dict) else {}


def load_priority_objective(path: Path | None = None) -> PriorityObjective | None:
    """Read ``athlete.priority_objective`` from the user YAML."""
    yaml_path = path or resolve_athlete_yaml_path()
    data = _read_yaml(yaml_path)
    raw = (data.get("athlete") or {}).get("priority_objective")
    if not raw:
        return None
    try:
        return PriorityObjective.model_validate(raw)
    except Exception:
        logger.exception("Invalid priority_objective in %s, ignoring", yaml_path)
        return None


def save_priority_objective(obj: PriorityObjective, path: Path | None = None) -> Path:
    """Persist ``obj`` under ``athlete.priority_objective`` in the user YAML.

    Reads the existing YAML (or starts from an empty skeleton), updates the
    ``athlete.priority_objective`` key, and writes back atomically. Bundle is
    never touched — only the resolved user file. Returns the path written.
    """
    yaml_path = path or resolve_athlete_yaml_path()
    data = _read_yaml(yaml_path)
    athlete = data.get("athlete")
    if not isinstance(athlete, dict):
        athlete = {}
        data["athlete"] = athlete
    payload = obj.model_dump(mode="json", exclude_none=True)
    athlete["priority_objective"] = payload
    _atomic_write_yaml(yaml_path, data)
    return yaml_path


def clear_priority_objective(path: Path | None = None) -> Path | None:
    """Remove ``athlete.priority_objective`` from the user YAML if present.

    Returns the path modified, or ``None`` if the YAML did not exist or had
    no priority objective set.
    """
    yaml_path = path or resolve_athlete_yaml_path()
    if not yaml_path.exists():
        return None
    data = _read_yaml(yaml_path)
    athlete = data.get("athlete")
    if not isinstance(athlete, dict) or "priority_objective" not in athlete:
        return None
    athlete.pop("priority_objective", None)
    _atomic_write_yaml(yaml_path, data)
    return yaml_path
