"""Geographic primitives for the athlete profile (MCT-XXX-0).

Hosts :class:`GeoPoint` (lat/lon + optional label) and the
``home_location`` read/write helpers backing the ``update-athlete-profile``
MCP handler dispatch (see ``magma_cycling/_mcp/handlers/athlete.py``).

The data lives in the athlete YAML resolved by
:func:`magma_cycling.paths.get_athlete_yaml_path`. Today that's the user
config dir (``~/.config/magma-cycling/athlete_context.yaml`` in a bundle,
project root in dev). The plan iso-config PR5 (sprint S094) will move the
file to ``training-logs/config/athlete.yaml`` racine; only the path
resolution changes — the schema and helpers stay.

Migration noop : if ``home_location`` is absent from the YAML,
:func:`load_home_location` returns ``None``. The caller surfaces this as
``NEEDS_LOCATION`` (MCT-XXX-1) on first invocation.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from magma_cycling.paths import get_athlete_yaml_path

logger = logging.getLogger(__name__)


class GeoPoint(BaseModel):
    """One geographic point: latitude, longitude, optional human label."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    lat: float = Field(ge=-90, le=90, description="Latitude in decimal degrees")
    lon: float = Field(ge=-180, le=180, description="Longitude in decimal degrees")
    label: str | None = Field(
        default=None,
        description="Optional human label (e.g. 'Chas', 'Domicile')",
    )


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


def load_home_location(path: Path | None = None) -> GeoPoint | None:
    """Read ``athlete.home_location`` from the YAML.

    Returns ``None`` when the YAML is absent or the key is missing
    (migration-noop semantics for pre-MCT-XXX-0 configs).
    """
    yaml_path = path or get_athlete_yaml_path()
    data = _read_yaml(yaml_path)
    raw = (data.get("athlete") or {}).get("home_location")
    if not raw:
        return None
    try:
        return GeoPoint.model_validate(raw)
    except Exception:
        logger.exception("Invalid home_location in %s, ignoring", yaml_path)
        return None


def save_home_location(location: GeoPoint, path: Path | None = None) -> Path:
    """Persist ``location`` under ``athlete.home_location`` in the YAML.

    Reads the existing YAML (or starts from an empty skeleton), updates the
    ``athlete.home_location`` key, and writes back atomically. Returns the
    resolved path written.
    """
    yaml_path = path or get_athlete_yaml_path()
    data = _read_yaml(yaml_path)
    athlete = data.get("athlete")
    if not isinstance(athlete, dict):
        athlete = {}
        data["athlete"] = athlete
    athlete["home_location"] = location.model_dump(exclude_none=True)
    _atomic_write_yaml(yaml_path, data)
    return yaml_path
