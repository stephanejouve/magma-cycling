"""Debug script for wellness data testing."""

import json

import requests

athlete_id = "i151223"
api_key = "420dlwmr1rxqfb73z19iq0ime"

session = requests.Session()
session.auth = ("API_KEY", api_key)

# Récupérer les données wellness
response = session.get(
    f"https://intervals.icu/api/v1/athlete/{athlete_id}/wellness?newest=2025-11-14&oldest=2025-11-07"
)
wellness = response.json()

# Afficher un jour complet
if wellness:
    print(json.dumps(wellness[0], indent=2))
