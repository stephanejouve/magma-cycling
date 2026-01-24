"""Debug script for inspecting all API fields."""

import json
import os
from datetime import datetime, timedelta

import requests

athlete_id = os.getenv("INTERVALS_ATHLETE_ID", "i151223")
api_key = os.getenv("INTERVALS_API_KEY", "420dlwmr1rxqfb73z19iq0ime")

session = requests.Session()
session.auth = ("API_KEY", api_key)

# Get recent activities (last 30 days)
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

print("🔍 Récupération des activités récentes...")
activities_response = session.get(
    f"https://intervals.icu/api/v1/athlete/{athlete_id}/activities",
    params={
        "oldest": start_date.strftime("%Y-%m-%d"),
        "newest": end_date.strftime("%Y-%m-%d"),
    },
)

if activities_response.status_code != 200:
    print(f"❌ Erreur récupération activités: {activities_response.status_code}")
    exit(1)

activities = activities_response.json()
if not activities:
    print("❌ Aucune activité trouvée")
    exit(1)

# Get the most recent activity
latest_activity = activities[0]
activity_id = latest_activity["id"]
activity_name = latest_activity.get("name", "Sans nom")
activity_date = latest_activity.get("start_date_local", "Date inconnue")

print("📊 Activité la plus récente:")
print(f"   ID: {activity_id}")
print(f"   Nom: {activity_name}")
print(f"   Date: {activity_date}")
print()

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
