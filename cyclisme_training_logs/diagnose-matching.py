#!/usr/bin/env python3
"""Script de diagnostic pour comprendre pourquoi le matching échoue."""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ajouter le répertoire scripts au path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from cyclisme_training_logs.planned_sessions_checker import (  # noqa: E402
    PlannedSessionsChecker,
)


def load_credentials():
    """Load credentials depuis .intervals_config.json."""
    config_path = Path.home() / ".intervals_config.json"

    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
    return config["athlete_id"], config["api_key"]


def diagnose():
    """Diagnostic détaillé du matching."""
    print("\n" + "=" * 70)

    print("  DIAGNOSTIC DÉTAILLÉ MATCHING WORKOUTS ↔ ACTIVITÉS")
    print("=" * 70)

    # Charger credentials
    athlete_id, api_key = load_credentials()
    print(f"\n✅ Athlete: {athlete_id}")

    # Période : 7 derniers jours
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)

    print(f"📅 Période : {start_date} → {end_date}\n")

    # Initialiser checker
    checker = PlannedSessionsChecker(athlete_id, api_key)

    # Récupérer workouts planifiés
    print("🔍 Récupération workouts planifiés...")
    all_events = checker.api.get_events(oldest=start_date.isoformat(), newest=end_date.isoformat())
    # Filtrer uniquement les workouts
    workouts = [e for e in all_events if e.get("category") == "WORKOUT"]
    print(f"   → {len(workouts)} workouts trouvés\n")

    # Récupérer activités
    print("🔍 Récupération activités réalisées...")
    activities = checker.api.get_activities(
        oldest=start_date.isoformat(), newest=end_date.isoformat()
    )
    print(f"   → {len(activities)} activités trouvées\n")

    print("=" * 70)
    print("ANALYSE DÉTAILLÉE PAR WORKOUT")
    print("=" * 70)

    # Analyser chaque workout
    for i, workout in enumerate(workouts, 1):
        workout_date = workout["start_date_local"][:10]
        workout_name = workout.get("name", "Sans nom")
        workout_id = workout.get("id", "N/A")

        print(f"\n[{i}] {workout_date} - {workout_name}")
        print(f"    ID workout: {workout_id}")

        # Extraire code séance
        workout_code = None
        if "-" in workout_name:
            parts = workout_name.split("-")
            if len(parts) >= 2:
                workout_code = f"{parts[0]}-{parts[1]}"

        if workout_code:
            print(f"    Code extrait: {workout_code}")

        # Chercher activités ce jour-là
        activities_same_day = [a for a in activities if a["start_date_local"][:10] == workout_date]

        print(f"\n    Activités le {workout_date}: {len(activities_same_day)}")

        if not activities_same_day:
            print("    ❌ Aucune activité ce jour → SKIPPED")
            continue

        # Afficher détails de chaque activité
        for j, activity in enumerate(activities_same_day, 1):
            activity_name = activity.get("name", "Sans nom")
            activity_id = activity.get("id")
            activity_time = activity["start_date_local"][11:16]

            print(f"\n    Activité {j}:")
            print(f"      Nom: {activity_name}")
            print(f"      ID: {activity_id}")
            print(f"      Heure: {activity_time}")

            # Tester les critères de matching
            match_tests = []

            # Test 1: Code séance
            if workout_code and workout_code in activity_name.upper():
                match_tests.append("✅ Code séance présent")
            else:
                match_tests.append(f"❌ Code '{workout_code}' absent du nom")

            # Test 2: Nom workout dans activité
            if workout_name.upper() in activity_name.upper():
                match_tests.append("✅ Nom workout dans activité")
            else:
                match_tests.append("❌ Nom workout absent")

            # Test 3: Nom activité dans workout
            if activity_name.upper() in workout_name.upper():
                match_tests.append("✅ Nom activité dans workout")
            else:
                match_tests.append("❌ Nom activité absent")

            # Afficher résultats tests
            print("\n      Tests de matching:")
            for test in match_tests:
                print(f"        {test}")

            # Verdict
            if any("✅" in t for t in match_tests):
                print("\n      ✅ MATCH TROUVÉ")
            else:
                print("\n      ❌ AUCUN MATCH")

        # Vérifier si workout a été matchée
        matched = checker._find_matching_activity(workout, activities_same_day, tolerance_hours=6)

        if matched:
            print(f"\n    ✅ RÉSULTAT FINAL: Activité {matched.get('id')} matchée")
        else:
            print("\n    ❌ RÉSULTAT FINAL: Aucune activité matchée → SKIPPED")

    print("\n" + "=" * 70)
    print("FIN DIAGNOSTIC")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    diagnose()
