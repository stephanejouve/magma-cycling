"""Decision log tool schemas (PR8 plan iso-config)."""

from mcp.types import Tool

_CATEGORIES = ["target_change", "modal_switch", "post_incident", "post_bilan"]
_HORIZONS = ["S+1", "S+2", "S+3", "mesocycle", "macrocycle"]


def get_tools() -> list[Tool]:
    """Return decision log tool schemas."""
    return [
        Tool(
            name="record-decision",
            description=(
                "Record a strategic training decision (target change, modal switch, "
                "post-incident, post-bilan adaptation with impact ≥ S+1) in the "
                "go-forward decision log. Granularity: strategic only, ≤ 10/month — "
                "session swaps do NOT belong here. One markdown file is written per "
                "decision under <TRAINING_DATA_ROOT>/data/decisions/decision-SXXX-NN.md."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "pattern": "^S\\d{3}$",
                        "description": "Week identifier, e.g. 'S094'.",
                    },
                    "title": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 200,
                        "description": "Short headline (one-line summary).",
                    },
                    "category": {
                        "type": "string",
                        "enum": _CATEGORIES,
                        "description": (
                            "target_change | modal_switch | post_incident | post_bilan"
                        ),
                    },
                    "description": {
                        "type": "string",
                        "minLength": 1,
                        "description": "Rationale + context (markdown allowed).",
                    },
                    "impact_horizon": {
                        "type": "string",
                        "enum": _HORIZONS,
                        "description": "Earliest horizon impacted (must be ≥ S+1).",
                    },
                    "references": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional cross-refs (other decision IDs, bilan files, " "session IDs)."
                        ),
                        "default": [],
                    },
                },
                "required": ["week_id", "title", "category", "description", "impact_horizon"],
                "additionalProperties": False,
            },
        ),
    ]
