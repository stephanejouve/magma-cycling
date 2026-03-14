"""MCP schema for workout catalog tool."""

from mcp.types import Tool


def get_tools() -> list[Tool]:
    """Return workout catalog tool schemas."""
    return [
        Tool(
            name="list-workout-catalog",
            description=(
                "Consulte le catalogue de workouts structures. "
                "Retourne des suggestions de seances avec structure complete "
                "(blocs, duree, intensite) pour inspiration et variete. "
                "Filtrable par type, duree, TSS et pattern structurel."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Type de seance: END, INT, FTP, REC, SPR, CLM, MIX",
                        "enum": ["END", "INT", "FTP", "REC", "SPR", "CLM", "MIX"],
                    },
                    "duration_min": {
                        "type": "integer",
                        "description": "Duree cible en minutes (tolerance ±15min)",
                        "minimum": 10,
                        "maximum": 180,
                    },
                    "tss_target": {
                        "type": "integer",
                        "description": "TSS cible (tolerance ±10)",
                        "minimum": 0,
                        "maximum": 500,
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Pattern structurel",
                        "enum": [
                            "pyramide",
                            "over-under",
                            "progressif",
                            "blocs-repetes",
                            "libre",
                        ],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Nombre max de resultats (defaut: 5)",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 5,
                    },
                },
                "required": [],
            },
        ),
    ]
