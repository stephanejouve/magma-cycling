#!/usr/bin/env python3
"""
Script de test pour la méthode create_event().
"""
import json
import sys
from pathlib import Path

from magma_cycling.api.intervals_client import IntervalsClient


def test_create_event():
    """Tester create_event avec différents formats."""
    print("🧪 Test de la méthode create_event()")

    print("=" * 70)
    print()

    # Charger credentials
    config_path = Path.home() / ".intervals_config.json"
    if not config_path.exists():
        print("❌ Config non trouvée : ~/.intervals_config.json")
        return 1

    with open(config_path) as f:
        config = json.load(f)

    api = IntervalsClient(athlete_id=config.get("athlete_id"), api_key=config.get("api_key"))

    print("✅ API connectée")
    print()

    # Test 1 : Format minimal
    print("📋 Test 1 : Format minimal")
    print("-" * 70)

    test_workout_1 = {
        "category": "WORKOUT",
        "name": "Test Simple",
        "description": "Warmup 10min\nMain set 20min\nCooldown 10min",
        "start_date_local": "2025-12-01",
    }

    print(f"Données : {json.dumps(test_workout_1, indent=2)}")
    print()

    result = api.create_event(test_workout_1)

    if result:
        print(f"✅ Test 1 RÉUSSI : ID={result.get('id')}")
    else:
        print("❌ Test 1 ÉCHOUÉ")

    print()
    print("=" * 70)

    # Test 2 : Format avec heure
    print("📋 Test 2 : Format avec heure")
    print("-" * 70)

    test_workout_2 = {
        "category": "WORKOUT",
        "name": "Test Avec Heure",
        "description": "Warmup 10min\nMain set 20min\nCooldown 10min",
        "start_date_local": "2025-12-02T08:00:00",
    }

    print(f"Données : {json.dumps(test_workout_2, indent=2)}")
    print()

    result = api.create_event(test_workout_2)

    if result:
        print(f"✅ Test 2 RÉUSSI : ID={result.get('id')}")
    else:
        print("❌ Test 2 ÉCHOUÉ")

    print()
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(test_create_event())
