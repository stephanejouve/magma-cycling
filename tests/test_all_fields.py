import requests
import json

athlete_id = "i151223"
api_key = "420dlwmr1rxqfb73z19iq0ime"

session = requests.Session()
session.auth = ("API_KEY", api_key)

activity_id = "i107093941" #lle de 17:42 (la plus ancienne)

print(f"=== TOUS LES CHAMPS DE L'ACTIVITÉ {activity_id} ===\n")

response = session.get(f"https://intervals.icu/api/v1/activity/{activity_id}")

if response.status_code == 200:
    activity = response.json()
    
    # Afficher TOUT le JSON brut
    print(json.dumps(activity, indent=2))
    
    print(f"\n\n=== NOMBRE DE CHAMPS ===")
    print(f"Total: {len(activity)} champs")
else:
    print(f"Erreur {response.status_code}: {response.text}")
