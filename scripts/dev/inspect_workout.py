#!/usr/bin/env python3
"""Script pour récupérer un workout existant et voir sa structure."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from prepare_analysis import IntervalsAPI  # noqa: E402


def inspect_existing_workout():
    """Retrieve un workout existant pour voir la structure."""
    # Charger credentials

    config_path = Path.home() / ".intervals_config.json"
    with open(config_path) as f:
        config = json.load(f)

    IntervalsAPI(athlete_id=config.get("athlete_id"), api_key=config.get("api_key"))

    # Récupérer événements du mois
    print("📥 Récupération des événements existants...")

    # Utiliser la méthode get_events (à vérifier qu'elle existe)
    # Sinon faire un appel direct
    import base64

    import requests

    athlete_id = config.get("athlete_id")
    api_key = config.get("api_key")

    url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/events"
    params = {"oldest": "2025-01-01", "newest": "2025-12-31"}

    credentials = f"API_KEY:{api_key}"
    auth_token = base64.b64encode(credentials.encode()).decode()

    headers = {"Authorization": f"Basic {auth_token}"}

    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()

    events = response.json()

    # Trouver un workout
    workouts = [e for e in events if e.get("category") == "WORKOUT"]

    if not workouts:
        print("⚠️  Aucun workout trouvé")
        print("\n💡 Solution : Crée un workout manuellement sur Intervals.icu")
        print("   Puis relance ce script pour voir sa structure")
        return

    print(f"\n✅ {len(workouts)} workout(s) trouvé(s)\n")
    print("=" * 70)
    print("STRUCTURE D'UN WORKOUT EXISTANT")
    print("=" * 70)

    # Afficher le premier workout
    workout = workouts[0]
    print(json.dumps(workout, indent=2, ensure_ascii=False))

    print("\n" + "=" * 70)
    print("CHAMPS IMPORTANTS")
    print("=" * 70)

    for key in ["category", "type", "name", "description", "start_date_local", "workout_doc"]:
        if key in workout:
            print(f"{key}: {workout[key]}")


if __name__ == "__main__":
    inspect_existing_workout()
