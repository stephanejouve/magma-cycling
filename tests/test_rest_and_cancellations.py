#!/usr/bin/env python3
"""
test_rest_and_cancellations.py - Tests unitaires pour le module rest_and_cancellations

Usage:
    python3 -m pytest cyclisme_training_logs/test_rest_and_cancellations.py -v
    python3 cyclisme_training_logs/test_rest_and_cancellations.py  # Run sans pytest
"""

import json
import tempfile
from pathlib import Path

# Import du module à tester
from cyclisme_training_logs.rest_and_cancellations import (
    generate_cancelled_session_entry,
    generate_rest_day_entry,
    load_week_planning,
    reconcile_planned_vs_actual,
    validate_week_planning,
)

# ============================================================================
# HELPERS
# ============================================================================


def create_test_planning(week_id="S070", with_cancellation=True, with_rest=True):
    """Crée un planning de test"""
    planning = {
        "week_id": week_id,
        "start_date": "2025-12-02",
        "end_date": "2025-12-08",
        "athlete_id": "i151223",
        "tss_target": 255,
        "planned_sessions": [],
    }

    # Session completed
    planning["planned_sessions"].append(
        {
            "session_id": f"{week_id}-01",
            "date": "2025-12-02",
            "type": "END",
            "name": "EnduranceBase",
            "version": "V001",
            "duration_min": 60,
            "tss_planned": 45,
            "status": "completed",
        }
    )

    # Session cancelled
    if with_cancellation:
        planning["planned_sessions"].append(
            {
                "session_id": f"{week_id}-02",
                "date": "2025-12-03",
                "type": "END",
                "name": "EnduranceProgressive",
                "version": "V001",
                "duration_min": 65,
                "tss_planned": 48,
                "status": "cancelled",
                "cancellation_reason": "Problème technique matériel",
            }
        )

    # Rest day
    if with_rest:
        planning["planned_sessions"].append(
            {
                "session_id": f"{week_id}-03",
                "date": "2025-12-04",
                "type": "REC",
                "name": "ReposObligatoire",
                "version": "V001",
                "duration_min": 0,
                "tss_planned": 0,
                "status": "rest_day",
                "rest_reason": "Protocole repos dimanche",
            }
        )

    return planning


# ============================================================================
# TESTS CHARGEMENT ET VALIDATION
# ============================================================================


def test_load_valid_planning():
    """Test chargement planning valide"""
    print("\n[TEST] Chargement planning valide...")

    # Créer un planning temporaire
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        planning_data = create_test_planning()

        # Écrire le fichier
        planning_file = tmpdir_path / "week_planning_S070.json"
        with open(planning_file, "w", encoding="utf-8") as f:
            json.dump(planning_data, f, indent=2)

        # Charger
        planning = load_week_planning("S070", planning_dir=tmpdir_path)

        assert planning["week_id"] == "S070"
        assert len(planning["planned_sessions"]) == 3
        print("✓ Planning chargé correctement")


def test_load_missing_planning():
    """Test gestion planning absent"""
    print("\n[TEST] Gestion planning absent...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        try:
            load_week_planning("S999", planning_dir=tmpdir_path)
            assert False, "Devrait lever FileNotFoundError"
        except FileNotFoundError as e:
            assert "Planning non trouvé" in str(e)
            print("✓ FileNotFoundError levée correctement")


def test_validate_planning_valid():
    """Test validation planning valide"""
    print("\n[TEST] Validation planning valide...")

    planning = create_test_planning()
    assert validate_week_planning(planning) == True
    print("✓ Planning validé")


def test_validate_planning_missing_field():
    """Test validation planning avec champ manquant"""
    print("\n[TEST] Validation planning avec champ manquant...")

    planning = create_test_planning()
    del planning["week_id"]  # Retirer champ obligatoire

    assert validate_week_planning(planning) == False
    print("✓ Planning invalide détecté (champ manquant)")


def test_validate_planning_invalid_status():
    """Test validation planning avec statut invalide"""
    print("\n[TEST] Validation planning avec statut invalide...")

    planning = create_test_planning()
    planning["planned_sessions"][0]["status"] = "invalid_status"

    assert validate_week_planning(planning) == False
    print("✓ Statut invalide détecté")


def test_validate_planning_missing_cancellation_reason():
    """Test validation raison manquante séance annulée"""
    print("\n[TEST] Validation raison manquante séance annulée...")

    planning = create_test_planning()
    # Retirer la raison d'annulation
    for session in planning["planned_sessions"]:
        if session["status"] == "cancelled":
            del session["cancellation_reason"]

    assert validate_week_planning(planning) == False
    print("✓ Raison manquante détectée")


def test_validate_planning_duplicate_session_id():
    """Test validation doublons session_id"""
    print("\n[TEST] Validation doublons session_id...")

    planning = create_test_planning()
    # Dupliquer un ID
    planning["planned_sessions"].append(planning["planned_sessions"][0].copy())

    assert validate_week_planning(planning) == False
    print("✓ Doublon détecté")


# ============================================================================
# TESTS GÉNÉRATION MARKDOWN
# ============================================================================


def test_generate_rest_day_markdown():
    """Test génération markdown repos planifié"""
    print("\n[TEST] Génération markdown repos planifié...")

    session = {
        "session_id": "S070-07",
        "date": "2025-12-08",
        "type": "REC",
        "name": "ReposObligatoire",
        "rest_reason": "Protocole repos dimanche obligatoire",
        "physiological_notes": "Récupération complète",
    }

    metrics_pre = {"ctl": 50, "atl": 35, "tsb": 15}
    metrics_post = {"ctl": 50, "atl": 35, "tsb": 15}
    feedback = {"sleep_duration": "6h12min", "sleep_score": 78, "hrv": 66, "resting_hr": 44}

    markdown = generate_rest_day_entry(session, metrics_pre, metrics_post, feedback)

    # Vérifications
    assert "S070-07-REC-ReposObligatoire" in markdown
    assert "TSS : 0" in markdown
    assert "repos complet planifié" in markdown
    assert "6h12min" in markdown
    assert "score 78" in markdown
    assert "VFC 66ms" in markdown
    assert "CTL : 50" in markdown
    assert "Protocole repos dimanche obligatoire" in markdown

    print("✓ Markdown repos généré correctement")
    print(f"  Longueur : {len(markdown)} caractères")


def test_generate_cancelled_session_markdown():
    """Test génération markdown séance annulée"""
    print("\n[TEST] Génération markdown séance annulée...")

    session = {
        "session_id": "S070-04",
        "date": "2025-12-05",
        "type": "END",
        "name": "EnduranceProgressive",
        "version": "V001",
        "tss_planned": 48,
        "cancellation_reason": "Problème technique matériel",
        "impact_notes": "TSS nul, repos involontaire",
    }

    metrics_pre = {"ctl": 51, "atl": 33, "tsb": 17, "sleep_duration": "7h29min", "sleep_score": 65}

    markdown = generate_cancelled_session_entry(
        session, metrics_pre, reason=session["cancellation_reason"]
    )

    # Vérifications
    assert "S070-04-END-EnduranceProgressive-V001" in markdown
    assert "TSS : 0 (prévu 48)" in markdown
    assert "Problème technique matériel" in markdown
    assert "séance non réalisée" in markdown
    assert "CTL : 51" in markdown
    assert "7h29min" in markdown
    assert "❌ Séance non exécutée" in markdown

    print("✓ Markdown annulation généré correctement")
    print(f"  Longueur : {len(markdown)} caractères")


# ============================================================================
# TESTS RÉCONCILIATION
# ============================================================================


def test_reconcile_planned_actual():
    """Test réconciliation planning vs activités"""
    print("\n[TEST] Réconciliation planning vs activités...")

    planning = create_test_planning()

    # Créer des activités de test
    activities = [
        {
            "id": "i123456",
            "start_date_local": "2025-12-02T08:00:00",
            "name": "S070-01 EnduranceBase",
        }
    ]

    result = reconcile_planned_vs_actual(planning, activities)

    # Vérifications
    assert len(result["matched"]) == 1
    assert len(result["cancelled"]) == 1
    assert len(result["rest_days"]) == 1
    assert len(result["unplanned"]) == 0

    print("✓ Réconciliation correcte")
    print(f"  Matched: {len(result['matched'])}")
    print(f"  Cancelled: {len(result['cancelled'])}")
    print(f"  Rest days: {len(result['rest_days'])}")


def test_reconcile_with_unplanned_activity():
    """Test réconciliation avec activité non planifiée"""
    print("\n[TEST] Réconciliation avec activité non planifiée...")

    planning = create_test_planning(with_cancellation=False, with_rest=False)

    activities = [
        {
            "id": "i123456",
            "start_date_local": "2025-12-02T08:00:00",
            "name": "S070-01 EnduranceBase",
        },
        {
            "id": "i123457",
            "start_date_local": "2025-12-05T10:00:00",
            "name": "Sortie non planifiée",
        },
    ]

    result = reconcile_planned_vs_actual(planning, activities)

    assert len(result["matched"]) == 1
    assert len(result["unplanned"]) == 1

    print("✓ Activité non planifiée détectée")


def test_reconcile_multiple_activities_same_day():
    """Test réconciliation plusieurs activités même jour"""
    print("\n[TEST] Réconciliation plusieurs activités même jour...")

    planning = {
        "week_id": "S070",
        "start_date": "2025-12-02",
        "end_date": "2025-12-08",
        "planned_sessions": [
            {
                "session_id": "S070-01",
                "date": "2025-12-02",
                "type": "END",
                "name": "Matin",
                "status": "completed",
                "tss_planned": 45,
            }
        ],
    }

    activities = [
        {"id": "i123456", "start_date_local": "2025-12-02T08:00:00", "name": "S070-01 Matin"},
        {"id": "i123457", "start_date_local": "2025-12-02T18:00:00", "name": "Session soir"},
    ]

    result = reconcile_planned_vs_actual(planning, activities)

    assert len(result["matched"]) == 1
    assert len(result["unplanned"]) == 1

    print("✓ Multiples activités même jour gérées")


# ============================================================================
# TESTS EDGE CASES
# ============================================================================


def test_generate_rest_day_without_feedback():
    """Test génération repos sans feedback athlète"""
    print("\n[TEST] Génération repos sans feedback athlète...")

    session = {
        "session_id": "S070-07",
        "date": "2025-12-08",
        "type": "REC",
        "name": "ReposObligatoire",
    }

    metrics_pre = {"ctl": 50, "atl": 35, "tsb": 15}
    metrics_post = {"ctl": 50, "atl": 35, "tsb": 15}

    markdown = generate_rest_day_entry(session, metrics_pre, metrics_post, None)

    assert "N/A" in markdown  # Feedback non disponible
    print("✓ Repos sans feedback généré (N/A)")


def test_cancelled_session_without_impact_notes():
    """Test génération annulation sans impact_notes"""
    print("\n[TEST] Génération annulation sans impact_notes...")

    session = {
        "session_id": "S070-04",
        "date": "2025-12-05",
        "type": "END",
        "name": "EnduranceProgressive",
        "version": "V001",
        "tss_planned": 48,
    }

    metrics_pre = {"ctl": 51, "atl": 33, "tsb": 17}

    markdown = generate_cancelled_session_entry(session, metrics_pre, reason="Test annulation")

    assert "Test annulation" in markdown
    print("✓ Annulation sans impact_notes générée")


# ============================================================================
# RUNNER PRINCIPAL (pour exécution sans pytest)
# ============================================================================


def run_all_tests():
    """Exécute tous les tests"""
    print("\n" + "=" * 70)
    print("TESTS REST AND CANCELLATIONS MODULE")
    print("=" * 70)

    tests = [
        test_load_valid_planning,
        test_load_missing_planning,
        test_validate_planning_valid,
        test_validate_planning_missing_field,
        test_validate_planning_invalid_status,
        test_validate_planning_missing_cancellation_reason,
        test_validate_planning_duplicate_session_id,
        test_generate_rest_day_markdown,
        test_generate_cancelled_session_markdown,
        test_reconcile_planned_actual,
        test_reconcile_with_unplanned_activity,
        test_reconcile_multiple_activities_same_day,
        test_generate_rest_day_without_feedback,
        test_cancelled_session_without_impact_notes,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"✗ ÉCHEC: {test.__name__}")
            print(f"  Erreur: {e}")
        except Exception as e:
            failed += 1
            print(f"✗ ERREUR: {test.__name__}")
            print(f"  Exception: {e}")

    print("\n" + "=" * 70)
    print(f"RÉSULTATS: {passed} réussis, {failed} échoués")
    print("=" * 70 + "\n")

    return failed == 0


if __name__ == "__main__":
    import sys

    success = run_all_tests()
    sys.exit(0 if success else 1)
