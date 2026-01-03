#!/usr/bin/env python3
"""Debug structure réponse API Intervals.icu"""

import json
import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path.home() / "cyclisme-training-logs"))

from cyclisme_training_logs.sync_intervals import IntervalsAPI  # noqa: E402


def main():
    # Init API
    athlete_id = os.getenv("VITE_INTERVALS_ATHLETE_ID")
    api_key = os.getenv("VITE_INTERVALS_API_KEY")

    if not athlete_id or not api_key:
        print("❌ Variables VITE_INTERVALS_* non définies")
        return

    print("🔑 Config API:")
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
            print(f"   Clés disponibles: {list(activity.keys())[:10]}...")

            # Dump JSON complet première activité
            print("\n📄 JSON COMPLET première activité:")
            print(json.dumps(activity, indent=2, default=str)[:1000])  # Premier 1000 chars

            print("\n" + "=" * 70)
            print("TEST 2: get_activity (détails)")
            print("=" * 70)

            try:
                detailed = api.get_activity(str(activity_id))

                print(f"\n✅ Détails activité {activity_id} récupérés")
                print(f"   Type: {type(detailed)}")
                print(f"   Clés disponibles: {list(detailed.keys())[:10]}...")

                # Dump JSON complet
                print("\n📄 JSON COMPLET activité détaillée:")
                print(json.dumps(detailed, indent=2, default=str)[:1500])  # Premier 1500 chars

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
                    print("\n✅ Champs trouvés:")
                    for k, v in found.items():
                        print(f"   {k}: {v}")
                else:
                    print("\n❌ AUCUN champ critique trouvé !")
                    print(f"   Clés présentes: {list(detailed.keys())}")

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
