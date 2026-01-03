#!/usr/bin/env python3
"""Debug structure réponse API Intervals.icu"""

import json
import os
import sys
from pathlib import Path

# Add project to path
project_root = Path.home() / "cyclisme-training-logs"
sys.path.insert(0, str(project_root))

# Charger .env si variables absentes
if not os.getenv("VITE_INTERVALS_ATHLETE_ID"):
    env_file = project_root / ".env"
    if env_file.exists():
        print(f"📁 Chargement {env_file}")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value
                    print(f"   ✅ {key} chargé")
    else:
        print(f"❌ Fichier .env non trouvé: {env_file}")
        sys.exit(1)

from cyclisme_training_logs.sync_intervals import IntervalsAPI  # noqa: E402


def main():
    # Init API
    athlete_id = os.getenv("VITE_INTERVALS_ATHLETE_ID")
    api_key = os.getenv("VITE_INTERVALS_API_KEY")

    if not athlete_id or not api_key:
        print("❌ Variables VITE_INTERVALS_* non définies même après chargement .env")
        return

    print("\n🔑 Config API:")
    print(f"   Athlete ID: {athlete_id}")
    print(f"   API Key: {api_key[:10]}...{api_key[-4:]}")

    api = IntervalsAPI(athlete_id, api_key)

    print("\n" + "=" * 70)
    print("TEST 1: get_activities (liste basique)")
    print("=" * 70)

    try:
        activities = api.get_activities(oldest="2024-08-01", newest="2024-08-03")

        print(f"\n✅ Retourné: {len(activities)} activités")

        if activities:
            activity = activities[0]
            activity_id = activity.get("id")

            print(f"\n📋 Première activité (ID: {activity_id}):")
            print(f"   Type: {type(activity)}")
            print(f"   Nombre clés: {len(activity.keys())}")
            print(f"   Clés disponibles: {list(activity.keys())}")

            # Dump JSON complet première activité
            print("\n📄 JSON COMPLET première activité:")
            print(json.dumps(activity, indent=2, default=str)[:2000])  # Premier 2000 chars

            print("\n" + "=" * 70)
            print("TEST 2: get_activity (détails)")
            print("=" * 70)

            try:
                detailed = api.get_activity(str(activity_id))

                print(f"\n✅ Détails activité {activity_id} récupérés")
                print(f"   Type: {type(detailed)}")
                print(f"   Nombre clés: {len(detailed.keys())}")
                print(f"   Clés disponibles: {list(detailed.keys())}")

                # Dump JSON complet
                print("\n📄 JSON COMPLET activité détaillée:")
                print(json.dumps(detailed, indent=2, default=str)[:3000])  # Premier 3000 chars

                # Rechercher champs critiques
                print("\n🔍 RECHERCHE CHAMPS CRITIQUES:")

                critical_fields = [
                    "moving_time",
                    "elapsed_time",
                    "duration",
                    "icu_training_load",
                    "training_load",
                    "tss",
                    "icu_average_watts",
                    "average_watts",
                    "avg_watts",
                    "power",
                    "icu_intensity",
                    "intensity",
                    "if",
                    "icu_weighted_avg_watts",
                    "weighted_avg_watts",
                    "np",
                ]

                found = {}
                for field in critical_fields:
                    value = detailed.get(field)
                    if value is not None:
                        found[field] = value

                if found:
                    print(f"\n✅ Champs trouvés ({len(found)}):")
                    for k, v in found.items():
                        print(f"   {k}: {v}")
                else:
                    print("\n❌ AUCUN champ critique trouvé !")
                    print(f"\n📋 TOUTES les clés présentes ({len(detailed.keys())}):")
                    for i, key in enumerate(detailed.keys()):
                        print(f"   {i+1}. {key}: {detailed[key]}")
                        if i >= 30:  # Limiter à 30 premières clés
                            print(f"   ... ({len(detailed.keys()) - 30} autres clés)")
                            break

            except Exception as e:
                print(f"\n❌ Erreur get_activity: {type(e).__name__}: {e}")
                import traceback

                traceback.print_exc()
        else:
            print("❌ Aucune activité trouvée dans la période")

    except Exception as e:
        print(f"\n❌ Erreur get_activities: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 70)
    print("FIN DEBUG")
    print("=" * 70)


if __name__ == "__main__":
    main()
