"""MCP schema for terrain circuit and workout adaptation tools."""

from mcp.types import Tool


def get_tools() -> list[Tool]:
    """Return terrain tool schemas."""
    return [
        Tool(
            name="extract-terrain-circuit",
            description=(
                "Extrait le profil terrain (segments par km, denivele, pentes, "
                "braquets observes) depuis une activite passee. "
                "Sauvegarde optionnelle en YAML pour reutilisation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": ("ID de l'activite source (ex: i131572602)"),
                    },
                    "save": {
                        "type": "boolean",
                        "description": ("Sauvegarder le circuit en YAML (defaut: true)"),
                        "default": True,
                    },
                    "name": {
                        "type": "string",
                        "description": "Nom du circuit (optionnel, ecrase le nom auto-genere)",
                    },
                },
                "required": ["activity_id"],
            },
        ),
        Tool(
            name="adapt-workout-to-terrain",
            description=(
                "Adapte un workout structure a un circuit terrain. "
                "Ajuste puissance, cadence et braquet par segment km "
                "selon le profil de pente. Utilise la biomecanique Grappe "
                "pour la cadence optimale."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "workout": {
                        "type": ["object", "string"],
                        "description": (
                            "Workout a adapter. Soit un dict avec 'phases' "
                            "(liste de {duration_min, power_pct}), soit une "
                            "notation simple (ex: '10min@65% + 3x10min@88%')"
                        ),
                    },
                    "ftp_watts": {
                        "type": "integer",
                        "description": "FTP de l'athlete en watts",
                        "minimum": 50,
                    },
                    "circuit_id": {
                        "type": "string",
                        "description": (
                            "ID d'un circuit sauvegarde (ex: TC_i131572602). "
                            "Mutuellement exclusif avec activity_id."
                        ),
                    },
                    "activity_id": {
                        "type": "string",
                        "description": (
                            "ID d'activite pour extraction a la volee. "
                            "Mutuellement exclusif avec circuit_id."
                        ),
                    },
                    "athlete_weight_kg": {
                        "type": "number",
                        "description": "Poids de l'athlete en kg (defaut: 70)",
                        "default": 70.0,
                    },
                    "profil_fibres": {
                        "type": "string",
                        "description": "Profil fibres musculaires",
                        "enum": ["explosif", "mixte", "endurant"],
                        "default": "mixte",
                    },
                    "workout_name": {
                        "type": "string",
                        "description": "Nom du workout (defaut: Workout)",
                        "default": "Workout",
                    },
                    "original_tss": {
                        "type": "integer",
                        "description": "TSS original pour calcul delta",
                        "default": 0,
                    },
                },
                "required": ["workout", "ftp_watts"],
            },
        ),
        Tool(
            name="list-terrain-circuits",
            description=(
                "Liste les circuits terrain sauvegardes. "
                "Retourne id, nom, distance et denivele de chaque circuit."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="evaluate-outdoor-execution",
            description=(
                "Evalue l'execution d'une sortie outdoor vs la prescription "
                "terrain-adaptee. Compare segment par segment cadence et braquet "
                "(pas puissance — le terrain la force mecaniquement). "
                "Produit un score de conformite et des recommandations."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": "ID de l'activite realisee a evaluer",
                    },
                    "adapted_workout": {
                        "type": "object",
                        "description": (
                            "Prescription AdaptedWorkout (resultat de adapt-workout-to-terrain). "
                            "Si omis, fournir circuit_id + workout + ftp_watts pour generer."
                        ),
                    },
                    "circuit_id": {
                        "type": "string",
                        "description": (
                            "ID du circuit (ex: TC_i131572602). "
                            "Utilise pour generer la prescription si adapted_workout omis."
                        ),
                    },
                    "workout": {
                        "type": ["object", "string"],
                        "description": (
                            "Workout a adapter (si adapted_workout omis). "
                            "Meme format que adapt-workout-to-terrain."
                        ),
                    },
                    "ftp_watts": {
                        "type": "integer",
                        "description": (
                            "FTP de l'athlete en watts (requis si adapted_workout omis)"
                        ),
                        "minimum": 50,
                    },
                },
                "required": ["activity_id"],
            },
        ),
    ]
