import requests
import json

athlete_id = "i151223"
api_key = "420dlwmr1rxqfb73z19iq0ime"

session = requests.Session()
session.auth = ("API_KEY", api_key)

# Récupérer TOUTES les activités du 14/11
response = session.get(
    f"https://intervals.icu/api/v1/athlete/{athlete_id}/activities",
    params={
        'oldest': '2025-11-14',
        'newest': '2025-11-14'
    }
)

activities = response.json()

print(f"=== ACTIVITÉS DU 14/11/2025 ===")
print(f"Nombre d'activités trouvées : {len(activities)}\n")

for i, activity in enumerate(activities, 1):
    print(f"--- SÉANCE #{i} ---")
    print(f"ID: {activity.get('id')}")
    print(f"Nom: {activity.get('name', 'Sans nom')}")
    print(f"Heure: {activity.get('start_date_local', 'N/A')}")
    print(f"Type: {activity.get('type', 'N/A')}")
    print(f"Durée: {activity.get('moving_time', 0) // 60}min")
    print(f"TSS: {activity.get('icu_training_load', 0)}")
    print(f"Puissance moy: {activity.get('icu_average_watts', 0)}W")
    print(f"Puissance NP: {activity.get('icu_weighted_avg_watts', 0)}W")
    print(f"FC moy: {activity.get('average_heartrate', 0)}bpm")
    print()
