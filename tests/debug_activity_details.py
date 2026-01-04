"""Debug script for activity details inspection."""

import requests

athlete_id = "i151223"
api_key = "REDACTED_INTERVALS_KEY"

session = requests.Session()
session.auth = ("API_KEY", api_key)

# IDs des activités du test précédent
activity_ids = [16457592483, 16457456654]

for activity_id in activity_ids:
    print(f"\n=== DÉTAILS ACTIVITÉ {activity_id} ===")

    # Endpoint détaillé
    response = session.get(f"https://intervals.icu/api/v1/activity/{activity_id}")

    if response.status_code == 200:
        activity = response.json()

        print(f"Nom: {activity.get('name', 'Sans nom')}")
        print(f"Type: {activity.get('type', 'N/A')}")
        print(f"Durée: {activity.get('moving_time', 0) // 60}min")
        print(f"TSS: {activity.get('icu_training_load', 0)}")
        print(f"Puissance moy: {activity.get('icu_average_watts', 0)}W")
        print(f"Puissance NP: {activity.get('icu_weighted_avg_watts', 0)}W")
        print(f"FC moy: {activity.get('average_heartrate', 0)}bpm")

        # Afficher TOUS les champs disponibles
        print("\n--- TOUS LES CHAMPS ---")
        for key in sorted(activity.keys()):
            if "power" in key.lower() or "watts" in key.lower():
                print(f"{key}: {activity[key]}")
    else:
        print(f"Erreur {response.status_code}")
