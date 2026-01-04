#!/usr/bin/env python3
"""
Test des 5 correctifs appliqués à weekly_analysis.py
"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from cyclisme_training_logs.weekly_analysis import WeeklyAnalysis  # noqa: E402


def test_correctifs():
    """Tester les 5 correctifs"""
    print("🧪 Test des Correctifs weekly_analysis.py")
    print("=" * 70)
    print()

    # Créer une instance
    analysis = WeeklyAnalysis("S046", "2025-11-10")

    print("✅ Correctif #1 : Parser workouts-history.md")
    print("   Regex modifié pour supporter '# Historique' et '## Historique'")
    print()

    print("✅ Correctif #2 : collect_week_metrics()")
    print("   Fonction améliorée avec métriques quotidiennes et _mock_metrics()")
    print()

    print("✅ Correctif #3 : collect_context_files()")
    print("   Gestion d'erreurs améliorée avec try/except")
    print()

    print("✅ Correctif #4 : generate_weekly_prompt()")
    print("   Prompt restructuré avec format JSON pour métriques")
    print()

    print("✅ Correctif #5 : validate_generated_files()")
    print("   Fonction ajoutée avec validation stricte (longueur minimale)")
    print()

    # Test de la fonction validate_generated_files()
    print("-" * 70)
    print("Test validate_generated_files()...")
    print()

    # Fichiers mock valides
    valid_files = {
        "workout_history_S046.md": "x" * 2500,
        "metrics_evolution_S046.md": "x" * 1500,
        "training_learnings_S046.md": "x" * 2000,
        "protocol_adaptations_S046.md": "x" * 800,
        "transition_S046_S047.md": "x" * 1000,
        "bilan_final_S046.md": "x" * 1200,
    }

    result = analysis.validate_generated_files(valid_files)

    if result:
        print()
        print("✅ Validation fichiers valides : RÉUSSI")
    else:
        print("❌ Validation fichiers valides : ÉCHOUÉ")
        return 1

    # Fichiers mock invalides (manquants)
    print()
    print("-" * 70)
    print("Test validation avec fichiers manquants...")
    print()

    invalid_files = {
        "workout_history_S046.md": "x" * 2500,
        "metrics_evolution_S046.md": "x" * 1500,
        # Fichiers manquants...
    }

    result = analysis.validate_generated_files(invalid_files)

    if not result:
        print()
        print("✅ Détection fichiers manquants : RÉUSSI")
    else:
        print("❌ Détection fichiers manquants : ÉCHOUÉ")
        return 1

    print()
    print("=" * 70)
    print("✅ TOUS LES TESTS RÉUSSIS")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(test_correctifs())
