"""YAML persistence for terrain circuits."""

import logging
from pathlib import Path

import yaml

from magma_cycling.config.data_repo import get_data_config
from magma_cycling.terrain.models import TerrainCircuit

logger = logging.getLogger(__name__)


def get_terrain_circuits_dir() -> Path:
    """Return the terrain circuits storage directory.

    Returns:
        Path to ~/training-logs/data/terrain_circuits/.
    """
    config = get_data_config()
    return config.terrain_circuits_dir


def save_circuit(circuit: TerrainCircuit) -> Path:
    """Save a terrain circuit as YAML.

    Args:
        circuit: TerrainCircuit to persist.

    Returns:
        Path to the saved YAML file.
    """
    circuits_dir = get_terrain_circuits_dir()
    circuits_dir.mkdir(parents=True, exist_ok=True)

    filepath = circuits_dir / f"{circuit.circuit_id}.yaml"
    data = circuit.model_dump(mode="json")

    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    logger.info("Saved terrain circuit to %s", filepath)
    return filepath


def load_circuit(circuit_id: str) -> TerrainCircuit | None:
    """Load a terrain circuit from YAML.

    Args:
        circuit_id: Circuit ID (e.g. 'TC_i131572602').

    Returns:
        TerrainCircuit or None if not found.
    """
    circuits_dir = get_terrain_circuits_dir()
    filepath = circuits_dir / f"{circuit_id}.yaml"

    if not filepath.exists():
        return None

    with open(filepath, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return TerrainCircuit.model_validate(data)


def list_circuits() -> list[dict]:
    """List all saved terrain circuits.

    Returns:
        List of dicts with id, name, distance, elevation for each circuit.
    """
    circuits_dir = get_terrain_circuits_dir()
    if not circuits_dir.exists():
        return []

    results = []
    for filepath in sorted(circuits_dir.glob("TC_*.yaml")):
        try:
            with open(filepath, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            results.append(
                {
                    "id": data.get("circuit_id", filepath.stem),
                    "name": data.get("name", ""),
                    "distance_km": data.get("total_distance_km", 0),
                    "elevation_gain_m": data.get("total_elevation_gain_m", 0),
                }
            )
        except Exception as e:
            logger.warning("Failed to read %s: %s", filepath, e)

    return results
