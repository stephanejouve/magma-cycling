"""BT-039 : tests de la fonction utilitaire ``compute_active_tss_target``."""

from __future__ import annotations

import pytest

from magma_cycling.analyzers.tss_target import (
    CANCELLED_STATUSES,
    compute_active_tss_target,
)


class TestCancelledStatusesSanity:
    """La whitelist des statuts « annulés » doit rester exactement
    {rest_day, skipped, cancelled}. Toute évolution consciente et documentée."""

    def test_cancelled_statuses_set(self):
        assert CANCELLED_STATUSES == frozenset({"rest_day", "skipped", "cancelled"})


class TestComputeActiveTssTargetOnDicts:
    """Tests avec l'entrée format dict (issue de JSON)."""

    def test_all_sessions_active(self):
        week = {
            "planned_sessions": [
                {"status": "planned", "tss_planned": 50},
                {"status": "completed", "tss_planned": 100},
            ]
        }
        assert compute_active_tss_target(week) == 150

    def test_excludes_rest_day(self):
        week = {
            "planned_sessions": [
                {"status": "planned", "tss_planned": 50},
                {"status": "rest_day", "tss_planned": 72},  # exclu
            ]
        }
        assert compute_active_tss_target(week) == 50

    def test_excludes_skipped(self):
        week = {
            "planned_sessions": [
                {"status": "completed", "tss_planned": 40},
                {"status": "skipped", "tss_planned": 30},  # exclu
            ]
        }
        assert compute_active_tss_target(week) == 40

    def test_excludes_cancelled(self):
        week = {
            "planned_sessions": [
                {"status": "planned", "tss_planned": 60},
                {"status": "cancelled", "tss_planned": 80},  # exclu
            ]
        }
        assert compute_active_tss_target(week) == 60

    def test_empty_planned_sessions(self):
        assert compute_active_tss_target({"planned_sessions": []}) == 0

    def test_missing_planned_sessions_key(self):
        assert compute_active_tss_target({}) == 0

    def test_all_sessions_cancelled(self):
        """Semaine 100 % annulée → cible active = 0 (les callers doivent
        protéger la division par zéro sur ce cas)."""
        week = {
            "planned_sessions": [
                {"status": "rest_day", "tss_planned": 50},
                {"status": "skipped", "tss_planned": 60},
                {"status": "cancelled", "tss_planned": 40},
            ]
        }
        assert compute_active_tss_target(week) == 0

    def test_missing_tss_planned_defaults_to_zero(self):
        week = {
            "planned_sessions": [
                {"status": "planned"},  # pas de tss_planned
                {"status": "completed", "tss_planned": 30},
            ]
        }
        assert compute_active_tss_target(week) == 30

    def test_none_tss_planned_defaults_to_zero(self):
        """``tss_planned=None`` ne doit pas crasher (ex. JSON parsé avec
        null explicite)."""
        week = {
            "planned_sessions": [
                {"status": "planned", "tss_planned": None},
                {"status": "completed", "tss_planned": 30},
            ]
        }
        assert compute_active_tss_target(week) == 30

    def test_covers_kin_zero_tss_scenario(self):
        """KIN/INJ tss=0 planned : compte pour 0 (actif mais sans charge).
        Cohérent avec BT-037 (auto rest_day exclut tss=0 aussi)."""
        week = {
            "planned_sessions": [
                {"status": "planned", "tss_planned": 0},  # KIN
                {"status": "planned", "tss_planned": 0},  # INJ
                {"status": "completed", "tss_planned": 50},
            ]
        }
        assert compute_active_tss_target(week) == 50


class TestComputeActiveTssTargetOnObjects:
    """Tests avec entrée objet (WeeklyPlan / Session Pydantic)."""

    def test_object_with_attribute_access(self):
        """Support des objets exposant ``planned_sessions`` en attribut
        (ex. WeeklyPlan Pydantic)."""

        class FakeSession:
            def __init__(self, status, tss):
                self.status = status
                self.tss_planned = tss

        class FakeWeek:
            planned_sessions = [
                FakeSession("planned", 40),
                FakeSession("rest_day", 100),  # exclu
                FakeSession("completed", 60),
            ]

        assert compute_active_tss_target(FakeWeek()) == 100


class TestReproductionAuditCases:
    """Reproduction des cas prod identifiés dans l'audit 2026-08-16."""

    @pytest.mark.parametrize(
        "week_id,initial,expected_active,expected_ghost",
        [
            ("S100", 286, 226, 60),  # 72 rest_day + 18 skipped -1 marge
            ("S094", 400, 68, 332),  # +332 ghost audit
            ("S092", 300, 85, 215),  # +215 ghost audit
        ],
    )
    def test_reproduction_audit_ghost_tss(self, week_id, initial, expected_active, expected_ghost):
        """Simule les valeurs cumulées de l'audit prod pour vérifier
        que la fonction produit bien la cible active corrigée."""
        # Fixture minimaliste : 1 session active + 1 session fantôme
        # portant la charge ghost
        week = {
            "week_id": week_id,
            "tss_target": initial,  # stocké intention
            "planned_sessions": [
                {"status": "completed", "tss_planned": expected_active},
                {"status": "skipped", "tss_planned": expected_ghost},
            ],
        }
        assert compute_active_tss_target(week) == expected_active
