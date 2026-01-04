#!/usr/bin/env python3
"""
Test du parser de réponse Claude pour weekly_analysis.py

Ce script teste le parsing d'une réponse Claude simulée.
"""
from cyclisme_training_logs.weekly_analysis import WeeklyAnalysis


def test_parser():
    """Tester le parser avec une réponse simulée"""
    # Créer une instance (les dates n'ont pas d'importance pour ce test)

    analysis = WeeklyAnalysis("S001", "2024-01-01")

    # Réponse simulée de Claude
    mock_response = """
Voici les 6 fichiers du rapport hebdomadaire :

### FILE: workout_history_S001.md
# Historique des Séances - S001

Contenu du fichier 1...

### FILE: metrics_evolution_S001.md
# Évolution des Métriques - S001

Contenu du fichier 2...

### FILE: training_learnings_S001.md
# Découvertes et Apprentissages - S001

Contenu du fichier 3...

### FILE: protocol_adaptations_S001.md
# Adaptations Protocoles - S001

Contenu du fichier 4...

### FILE: transition_S001_S002.md
# Transition S001 → S002

Contenu du fichier 5...

### FILE: bilan_final_S001.md
# Bilan Final - S001

Contenu du fichier 6...
"""
    print("🧪 Test du parser de réponse Claude")

    print("=" * 70)
    print()

    # Parser la réponse
    files = analysis.parse_claude_response(mock_response)

    # Vérifications
    print(f"✅ Fichiers extraits : {len(files)}")
    print()

    expected_files = [
        "workout_history_S001.md",
        "metrics_evolution_S001.md",
        "training_learnings_S001.md",
        "protocol_adaptations_S001.md",
        "transition_S001_S002.md",
        "bilan_final_S001.md",
    ]

    for expected in expected_files:
        if expected in files:
            content = files[expected]
            print(f"✅ {expected}")
            print(f"   Longueur : {len(content)} caractères")
            print(f"   Preview : {content[:60]}...")
        else:
            print(f"❌ {expected} - MANQUANT")
        print()

    # Validation finale
    if len(files) == 6:
        print("=" * 70)
        print("✅ TEST RÉUSSI : Tous les fichiers ont été extraits correctement")
        print("=" * 70)
        return 0
    else:
        print("=" * 70)
        print(f"❌ TEST ÉCHOUÉ : {len(files)}/6 fichiers extraits")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(test_parser())
