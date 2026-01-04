"""Debug script for inspecting all API fields."""

import json

import requests

athlete_id = "i151223"
api_key = "REDACTED_INTERVALS_KEY"

session = requests.Session()
session.auth = ("API_KEY", api_key)

activity_id = "i107093941"  # lle de 17:42 (la plus ancienne)

print(f"=== TOUS LES CHAMPS DE L'ACTIVITÉ {activity_id} ===\n")

response = session.get(f"https://intervals.icu/api/v1/activity/{activity_id}")

if response.status_code == 200:
    activity = response.json()

    # Afficher TOUT le JSON brut
    print(json.dumps(activity, indent=2))

    print("\n\n=== NOMBRE DE CHAMPS ===")
    print(f"Total: {len(activity)} champs")
else:
    print(f"Erreur {response.status_code}: {response.text}")
