"""Weather tool schemas (4 handlers wrappant magma_cycling_tools.weather)."""

from mcp.types import Tool


def get_tools() -> list[Tool]:
    """Return weather tool schemas."""
    return [
        Tool(
            name="get-weather-for-session",
            description=(
                "Récupère la prévision météo le long du circuit d'une session "
                "outdoor planifiée. Charge la session via session_id, vérifie "
                "qu'elle est outdoor + a un terrain_circuit_id, échantillonne "
                "N=10 points équidistants en km, et appelle le provider pour "
                "chaque point au timestamp de passage estimé. "
                "Si la session n'est pas outdoor → return data=null + message "
                "explicite (pas d'erreur). Si terrain_circuit_id manquant → "
                "escalade structurée (pas de fallback). "
                "Cf ADR /Users/Shared/NOTE-ARCHI-integration-meteo-magma-cycling.md."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID (ex: S093-04)",
                        "pattern": r"^S\d{3}-\d{2}[a-z]?$",
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="get-weather-along-route",
            description=(
                "Récupère la prévision météo le long d'un circuit donné, sans "
                "dépendance à une session. Utile pour exploration (ex: étudier "
                "la météo d'un circuit candidat avant planification). "
                "Échantillonne N=10 points équidistants en km, estime le "
                "timestamp de passage à partir de start_time + avg_speed_kmh."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "circuit_id": {
                        "type": "string",
                        "description": "Identifiant du circuit terrain",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Datetime de départ ISO 8601 (tz-aware, défaut Europe/Paris)",
                    },
                    "avg_speed_kmh": {
                        "type": "number",
                        "description": "Vitesse moyenne attendue en km/h (défaut 25.0)",
                        "default": 25.0,
                        "minimum": 5.0,
                        "maximum": 60.0,
                    },
                },
                "required": ["circuit_id", "start_time"],
            },
        ),
        Tool(
            name="get-rain-next-hour",
            description=(
                "Récupère la prévision de pluie sur les 60 prochaines minutes "
                "(pas de 5 min) pour un point géographique. Utile pour décision "
                "de départ imminent. Si la zone n'est pas couverte par la lib "
                "(certaines régions rurales), retourne un statut explicite."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "lat": {
                        "type": "number",
                        "description": "Latitude WGS84 (degrés décimaux)",
                        "minimum": -90.0,
                        "maximum": 90.0,
                    },
                    "lon": {
                        "type": "number",
                        "description": "Longitude WGS84 (degrés décimaux)",
                        "minimum": -180.0,
                        "maximum": 180.0,
                    },
                },
                "required": ["lat", "lon"],
            },
        ),
        Tool(
            name="get-vigilance",
            description=(
                "Récupère le bulletin Vigilance Météo-France pour un département "
                "français. Retourne max_color (vert/jaune/orange/rouge) calculé "
                "sur tous les phénomènes du département + détail par "
                "phénomène (vent/pluie/orages/neige/canicule/grand_froid/"
                "avalanches/vagues_submersion/crues). "
                "Politique recommandée côté Coach IA (cf note d'archi §3) : "
                "rouge → bascule indoor automatique (avec confirmation Stéphane), "
                "orange → flag pour décision, vert/jaune → info présentée."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "departement": {
                        "type": "string",
                        "description": (
                            "Code département français (ex: '63' Puy-de-Dôme). "
                            "2 caractères pour la métropole, 2A/2B pour la Corse, "
                            "3 caractères pour DOM (971-976)."
                        ),
                        "pattern": r"^(0[1-9]|[1-8][0-9]|9[0-5]|2[AB]|97[1-6])$",
                    },
                },
                "required": ["departement"],
            },
        ),
    ]
