#!/usr/bin/env python3
"""
test_p0_fixes.py - Tests de validation des corrections P0 critiques.
"""
import pytest

from cyclisme_training_logs.rest_and_cancellations import (
    VALID_STATUSES,
    reconcile_planned_vs_actual,
)


def test_p0_fix1_modified_status_valid():
    """P0 Fix #1: Vérifier que 'modified' est dans VALID_STATUSES."""
    assert "modified" in VALID_STATUSES, "'modified' devrait être un statut valide"

    assert "completed" in VALID_STATUSES
    assert "cancelled" in VALID_STATUSES
    assert "rest_day" in VALID_STATUSES
    assert "replaced" in VALID_STATUSES
    assert "skipped" in VALID_STATUSES


def test_p0_fix3_auto_reclassification_persistence():
    """P0 Fix #3: Vérifier que l'auto-reclassification modifie l'original."""
    # Créer planning avec session marquée completed mais sans activité

    week_planning = {
        "week_id": "S999",
        "start_date": "2025-12-01",
        "end_date": "2025-12-07",
        "planned_sessions": [
            {
                "session_id": "S999-01",
                "date": "2025-12-01",
                "name": "Test",
                "type": "END",
                "status": "completed",  # Marquée completed
                "tss_planned": 50,
            }
        ],
    }

    # Aucune activité pour cette date
    activities = []

    # Exécuter réconciliation
    result = reconcile_planned_vs_actual(week_planning, activities)

    # Vérifier que la session a été reclassée comme skipped
    assert len(result["skipped"]) == 1
    skipped_session = result["skipped"][0]
    assert skipped_session["status"] == "skipped"
    assert "skip_reason" in skipped_session

    # CRITIQUE: Vérifier que l'original a été modifié (pas une copie)
    original_session = week_planning["planned_sessions"][0]
    assert (
        original_session["status"] == "skipped"
    ), "La session originale devrait être modifiée (persistence)"
    assert original_session["skip_reason"] == "Planifiée completed mais activité introuvable"


def test_validation_with_modified_status():
    """Verify que validate_week_planning accepte status='modified'."""
    from cyclisme_training_logs.rest_and_cancellations import validate_week_planning

    planning_with_modified = {
        "week_id": "S999",
        "start_date": "2025-12-01",
        "end_date": "2025-12-07",
        "planned_sessions": [
            {
                "session_id": "S999-01",
                "date": "2025-12-01",
                "name": "Test",
                "type": "END",
                "status": "modified",  # Devrait être accepté maintenant
                "tss_planned": 50,
            }
        ],
    }

    # Ne devrait pas lever d'exception
    try:
        validate_week_planning(planning_with_modified)
        validation_passed = True
    except ValueError:
        validation_passed = False

    assert validation_passed, "Le statut 'modified' devrait être valide"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
