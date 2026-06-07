"""Geographic primitives for the athlete profile (MCT-XXX-0).

Hosts :class:`GeoPoint` (lat/lon + optional label) and the
``home_location`` read/write helpers backing the ``update-athlete-profile``
MCP handler dispatch (see ``magma_cycling/_mcp/handlers/athlete.py``).

The data lives in the athlete YAML resolved by
:func:`magma_cycling.config.data_repo.resolve_athlete_yaml_path` (PR5
plan iso-config). Priority: ``ATHLETE_CONFIG_PATH`` env override →
``<TRAINING_DATA_ROOT>/config/athlete.yaml`` (cible portable PR5) →
``paths.get_athlete_yaml_path()`` (legacy user config dir) → bundle
fallback handled separately by ``athlete_context.load_athlete_context``.

Migration noop : if ``home_location`` is absent from the YAML,
:func:`load_home_location` returns ``None``. The caller surfaces this as
``NEEDS_LOCATION`` (MCT-XXX-1) on first invocation.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from magma_cycling.config._yaml_io import atomic_write_yaml, read_yaml
from magma_cycling.config.data_repo import resolve_athlete_yaml_path

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


def load_home_location(path: Path | None = None) -> GeoPoint | None:
    """Read ``athlete.home_location`` from the YAML.

    Returns ``None`` when the YAML is absent or the key is missing
    (migration-noop semantics for pre-MCT-XXX-0 configs).
    """
    yaml_path = path or resolve_athlete_yaml_path()
    data = read_yaml(yaml_path)
    raw = (data.get("athlete") or {}).get("home_location")
    if not raw:
        return None
    try:
        return GeoPoint.model_validate(raw)
    except Exception:
        logger.warning("home_location in %s failed pydantic validation; ignoring", yaml_path)
        return None


def save_home_location(location: GeoPoint, path: Path | None = None) -> Path:
    """Persist ``location`` under ``athlete.home_location`` in the YAML.

    Reads the existing YAML (or starts from an empty skeleton), updates the
    ``athlete.home_location`` key, and writes back atomically. Returns the
    resolved path written.
    """
    yaml_path = path or resolve_athlete_yaml_path()
    data = read_yaml(yaml_path)
    athlete = data.get("athlete")
    if not isinstance(athlete, dict):
        athlete = {}
        data["athlete"] = athlete
    athlete["home_location"] = location.model_dump(exclude_none=True)
    atomic_write_yaml(yaml_path, data)
    return yaml_path
