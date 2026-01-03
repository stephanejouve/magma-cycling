import requests

athlete_id = "i151223"
api_key = "420dlwmr1rxqfb73z19iq0ime"

session = requests.Session()
session.auth = ("API_KEY", api_key)

# Tester différents paramètres
params_sets = [
    {"oldest": "2025-11-14", "newest": "2025-11-14"},
    {"oldest": "2025-11-14", "newest": "2025-11-14", "exclude_empty": "true"},
    {"oldest": "2025-11-14", "newest": "2025-11-14", "type": "VirtualRide"},
    {"oldest": "2025-11-14", "newest": "2025-11-14", "type": "Ride"},
]

for params in params_sets:
    print(f"\n=== TEST AVEC {params} ===")
    response = session.get(
        f"https://intervals.icu/api/v1/athlete/{athlete_id}/activities", params=params
    )
    activities = response.json()
    print(f"Nombre activités: {len(activities)}")
    for act in activities:
        print(f"  - {act.get('name', 'Sans nom')}: {act.get('moving_time', 0)//60}min")
