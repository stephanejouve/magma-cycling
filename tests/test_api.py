import json

import requests

athlete_id = "i151223"
api_key = "420dlwmr1rxqfb73z19iq0ime"

session = requests.Session()
session.auth = ("API_KEY", api_key)

# Récupérer les activités
response = session.get(
    f"https://intervals.icu/api/v1/athlete/{athlete_id}/activities?newest=2025-11-14&oldest=2025-11-07"
)
activities = response.json()

# Afficher la première activité avec tous ses champs
if activities:
    print(json.dumps(activities[0], indent=2))
