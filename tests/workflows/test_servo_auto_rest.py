"""Tests for auto rest_day application in daily-sync servo evaluation."""

import json
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.planning.models import WeeklyPlan
from magma_cycling.update_session_status import STATUSES_TO_DELETE, sync_with_intervals


@pytest.fixture
def planning_data():
    """Sample planning data with sessions."""
    return {
        "week_id": "S999",
        "start_date": "2026-03-02",
        "end_date": "2026-03-08",
        "created_at": "2026-02-01T20:00:00Z",
        "last_updated": "2026-02-01T20:00:00Z",
        "version": 1,
        "athlete_id": "iXXXXXX",
        "tss_target": 350,
        "planned_sessions": [
            {
                "session_id": "S999-01",
                "date": "2026-03-02",
                "name": "Endurance",
                "type": "END",
                "version": "V001",
                "tss_planned": 50,
                "duration_min": 60,
                "description": "Endurance Z2",
                "status": "planned",
                "intervals_id": None,
                "description_hash": None,
            },
            {
                "session_id": "S999-02",
                "date": "2026-03-03",
                "name": "Interval",
                "type": "INT",
                "version": "V001",
                "tss_planned": 70,
                "duration_min": 65,
                "description": "Sweet Spot 3x10",
                "status": "planned",
                "intervals_id": 12345,
                "description_hash": None,
            },
        ],
    }


@pytest.fixture
def mock_control_tower(tmp_path, planning_data):
    """Mock Control Tower to use tmp_path for planning."""
    from magma_cycling.planning.control_tower import planning_tower

    original_planning_dir = planning_tower.planning_dir
    planning_tower.planning_dir = tmp_path
    planning_tower.backup_system.planning_dir = tmp_path

    planning_file = tmp_path / "week_planning_S999.json"
    with open(planning_file, "w", encoding="utf-8") as f:
        json.dump(planning_data, f, indent=2)

    yield tmp_path

    planning_tower.planning_dir = original_planning_dir
    planning_tower.backup_system.planning_dir = original_planning_dir


class TestAutoRestDayApplication:
    """Test daily-sync auto-applies rest_day."""

    @patch("magma_cycling.config.create_intervals_client")
    @patch("magma_cycling.update_session_status.sync_with_intervals")
    def test_auto_rest_day_updates_planning(self, mock_sync, mock_client, mock_control_tower):
        """Test _apply_auto_rest_day updates planning JSON."""
        from magma_cycling.workflows.sync.servo_evaluation import (
            ServoEvaluationMixin,
        )

        mock_sync.return_value = True
        mock_client.return_value = MagicMock()

        mixin = ServoEvaluationMixin()
        mod = {
            "action": "rest_day",
            "target_date": "2026-03-03",
            "current_workout": "S999-02-INT-Interval-V001",
            "reason": "TSB -22, sommeil 4.8h",
        }

        mixin._apply_auto_rest_day(mod, "S999")

        # Verify planning JSON updated
        planning_file = mock_control_tower / "week_planning_S999.json"
        plan = WeeklyPlan.from_json(planning_file)
        session = plan.planned_sessions[1]
        assert session.status == "rest_day"
        assert session.skip_reason == "TSB -22, sommeil 4.8h"

        # Verify sync called with correct params
        mock_sync.assert_called_once()
        call_kwargs = mock_sync.call_args[1]
        assert call_kwargs["new_status"] == "rest_day"
        assert call_kwargs["session_id"] == "S999-02"
        assert call_kwargs["session_date"] == "2026-03-03"

    @patch("magma_cycling.config.create_intervals_client")
    @patch("magma_cycling.update_session_status.sync_with_intervals")
    def test_auto_rest_day_session_not_found(self, mock_sync, mock_client, mock_control_tower):
        """Test _apply_auto_rest_day handles missing session gracefully."""
        from magma_cycling.workflows.sync.servo_evaluation import (
            ServoEvaluationMixin,
        )

        mixin = ServoEvaluationMixin()
        mod = {
            "action": "rest_day",
            "target_date": "2026-03-09",
            "current_workout": "S999-99",
            "reason": "Fatigue",
        }

        # Should not raise
        mixin._apply_auto_rest_day(mod, "S999")

        # Sync should not be called (session not found)
        mock_sync.assert_not_called()

    @patch("magma_cycling.config.create_intervals_client")
    @patch("magma_cycling.update_session_status.sync_with_intervals")
    def test_cancel_treated_as_rest_day(self, mock_sync, mock_client, mock_control_tower):
        """Test that cancel action is treated same as rest_day."""
        from magma_cycling.workflows.sync.servo_evaluation import (
            ServoEvaluationMixin,
        )

        mock_sync.return_value = True
        mock_client.return_value = MagicMock()

        mixin = ServoEvaluationMixin()
        mod = {
            "action": "cancel",
            "target_date": "2026-03-03",
            "current_workout": "S999-02",
            "reason": "Blessure",
        }

        mixin._apply_auto_rest_day(mod, "S999")

        # Planning should be updated with rest_day status
        planning_file = mock_control_tower / "week_planning_S999.json"
        plan = WeeklyPlan.from_json(planning_file)
        session = plan.planned_sessions[1]
        assert session.status == "rest_day"


class TestBT036GuardTerminalStatus:
    """BT-036 : auto rest_day doit refuser d'écraser un status terminal
    (completed, skipped, cancelled, uploaded, replaced, modified) —
    respect des décisions user/agent explicites.

    Incident du 2026-08-15 : Coach AI avait écrit S106-06 = completed
    avec bilan complet à 12:15 UTC, le cron daily-sync 21:30 UTC a
    rétrogradé en rest_day (règle Sommeil aveugle) → perte de données.
    """

    @pytest.fixture
    def planning_data_with_various_statuses(self):
        """Planning avec des sessions à statuts variés pour couvrir tous
        les cas overwritable vs protégé."""
        return {
            "week_id": "S999",
            "start_date": "2026-03-02",
            "end_date": "2026-03-08",
            "created_at": "2026-02-01T20:00:00Z",
            "last_updated": "2026-02-01T20:00:00Z",
            "version": 1,
            "athlete_id": "iXXXXXX",
            "tss_target": 350,
            "planned_sessions": [
                {
                    "session_id": "S999-01",
                    "date": "2026-03-02",
                    "name": "Endurance",
                    "type": "END",
                    "version": "V001",
                    "tss_planned": 50,
                    "duration_min": 60,
                    "description": "Endurance Z2",
                    "status": "planned",  # OVERWRITABLE
                },
                {
                    "session_id": "S999-02",
                    "date": "2026-03-03",
                    "name": "Bilan Coach AI",
                    "type": "END",
                    "version": "V001",
                    "tss_planned": 40,
                    "duration_min": 45,
                    "description": "Session avec bilan",
                    "status": "completed",  # PROTECTED (cas S106-06 réel)
                },
                {
                    "session_id": "S999-03",
                    "date": "2026-03-04",
                    "name": "Repos user",
                    "type": "END",
                    "version": "V001",
                    "tss_planned": 0,
                    "duration_min": 0,
                    "description": "Skip décidé par user",
                    "status": "skipped",  # PROTECTED
                    "skip_reason": "User a décidé de skip",
                },
                {
                    "session_id": "S999-04",
                    "date": "2026-03-05",
                    "name": "Interval",
                    "type": "INT",
                    "version": "V001",
                    "tss_planned": 70,
                    "duration_min": 65,
                    "description": "Sweet Spot 3x10",
                    "status": "uploaded",  # PROTECTED (envoyé, user va faire)
                },
            ],
        }

    @pytest.fixture
    def mock_ct_various_statuses(self, tmp_path, planning_data_with_various_statuses):
        from magma_cycling.planning.control_tower import planning_tower

        original = planning_tower.planning_dir
        planning_tower.planning_dir = tmp_path
        planning_tower.backup_system.planning_dir = tmp_path
        planning_file = tmp_path / "week_planning_S999.json"
        with open(planning_file, "w", encoding="utf-8") as f:
            json.dump(planning_data_with_various_statuses, f, indent=2)
        yield tmp_path
        planning_tower.planning_dir = original
        planning_tower.backup_system.planning_dir = original

    @patch("magma_cycling.config.create_intervals_client")
    @patch("magma_cycling.update_session_status.sync_with_intervals")
    def test_auto_rest_day_skips_completed_session(
        self, mock_sync, mock_client, mock_ct_various_statuses, caplog
    ):
        """Le cas exact du bug S106-06 : session completed ne doit PAS
        être écrasée par auto rest_day."""
        import logging

        from magma_cycling.workflows.sync.servo_evaluation import (
            ServoEvaluationMixin,
        )

        mixin = ServoEvaluationMixin()
        mod = {
            "action": "rest_day",
            "target_date": "2026-03-03",  # cible S999-02
            "current_workout": "S999-02-END-Bilan-V001",
            "reason": "Sommeil 5.0h (seuil critique < 7h), prioriser récupération",
        }

        with caplog.at_level(
            logging.WARNING, logger="magma_cycling.workflows.sync.servo_evaluation"
        ):
            mixin._apply_auto_rest_day(mod, "S999")

        # Session completed doit rester intacte
        planning_file = mock_ct_various_statuses / "week_planning_S999.json"
        plan = WeeklyPlan.from_json(planning_file)
        completed_session = next(s for s in plan.planned_sessions if s.session_id == "S999-02")
        assert (
            completed_session.status == "completed"
        ), "Session completed écrasée à tort par auto rest_day"

        # Warning BT-036 émis
        warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
        assert any(
            "BT-036" in r.message and "skipped" in r.message.lower() for r in warning_records
        ), f"Expected BT-036 warning, got: {[r.message for r in warning_records]}"

        # Sync Intervals.icu PAS appelée (skip complet)
        mock_sync.assert_not_called()

    @patch("magma_cycling.config.create_intervals_client")
    @patch("magma_cycling.update_session_status.sync_with_intervals")
    def test_auto_rest_day_skips_skipped_session(
        self, mock_sync, mock_client, mock_ct_various_statuses
    ):
        """Session skipped (user a explicitement skippé) → protégée."""
        from magma_cycling.workflows.sync.servo_evaluation import (
            ServoEvaluationMixin,
        )

        mixin = ServoEvaluationMixin()
        mod = {
            "action": "rest_day",
            "target_date": "2026-03-04",
            "current_workout": "S999-03",
            "reason": "Sommeil insuffisant",
        }
        mixin._apply_auto_rest_day(mod, "S999")

        planning_file = mock_ct_various_statuses / "week_planning_S999.json"
        plan = WeeklyPlan.from_json(planning_file)
        session = next(s for s in plan.planned_sessions if s.session_id == "S999-03")
        assert session.status == "skipped"
        mock_sync.assert_not_called()

    @patch("magma_cycling.config.create_intervals_client")
    @patch("magma_cycling.update_session_status.sync_with_intervals")
    def test_auto_rest_day_skips_uploaded_session(
        self, mock_sync, mock_client, mock_ct_various_statuses
    ):
        """Session uploaded (envoyée à Intervals, user va la faire) → protégée."""
        from magma_cycling.workflows.sync.servo_evaluation import (
            ServoEvaluationMixin,
        )

        mixin = ServoEvaluationMixin()
        mod = {
            "action": "rest_day",
            "target_date": "2026-03-05",
            "current_workout": "S999-04",
            "reason": "TSB -15",
        }
        mixin._apply_auto_rest_day(mod, "S999")

        planning_file = mock_ct_various_statuses / "week_planning_S999.json"
        plan = WeeklyPlan.from_json(planning_file)
        session = next(s for s in plan.planned_sessions if s.session_id == "S999-04")
        assert session.status == "uploaded"
        mock_sync.assert_not_called()

    @patch("magma_cycling.config.create_intervals_client")
    @patch("magma_cycling.update_session_status.sync_with_intervals")
    def test_auto_rest_day_still_overrides_planned_session(
        self, mock_sync, mock_client, mock_ct_various_statuses
    ):
        """Non-régression : session planned (statut overwritable) doit
        toujours être overwritable par auto rest_day (comportement historique
        préservé — le bug BT-036 ne bloque QUE les statuts terminaux)."""
        from magma_cycling.workflows.sync.servo_evaluation import (
            ServoEvaluationMixin,
        )

        mock_sync.return_value = True
        mock_client.return_value = MagicMock()

        mixin = ServoEvaluationMixin()
        mod = {
            "action": "rest_day",
            "target_date": "2026-03-02",  # cible S999-planned
            "current_workout": "S999-planned",
            "reason": "TSB -20, fatigue",
        }
        mixin._apply_auto_rest_day(mod, "S999")

        planning_file = mock_ct_various_statuses / "week_planning_S999.json"
        plan = WeeklyPlan.from_json(planning_file)
        session = next(s for s in plan.planned_sessions if s.session_id == "S999-01")
        assert session.status == "rest_day", "Session planned devrait rester overwritable"

    def test_overwritable_statuses_whitelist_explicit(self):
        """Sanity : la whitelist doit rester exactement `{pending, planned, rest_day}`.
        Toute évolution doit être consciente et documentée."""
        from magma_cycling.workflows.sync.servo_evaluation import ServoEvaluationMixin

        assert ServoEvaluationMixin.AUTO_REST_DAY_OVERWRITABLE_STATUSES == {
            "pending",
            "planned",
            "rest_day",
        }


class TestBT037ExcludeZeroTssFromAutoRestDay:
    """BT-037 : les sessions à charge nulle (``tss_planned=0``, typique
    des protocoles KIN de kiné, INJ off-bike, rehab) doivent être exclues
    du path auto rest_day — la règle de charge (TSB + sommeil) n'a pas
    vocation à annuler un protocole prescrit hors charge.

    Cas prod S106-07 (2026-08-16) : KIN planned rétrogradé rest_day
    par le cron, malgré tss_planned=0. Fonctionnellement faux : le kiné
    voyait des séances marquées « repos » alors que le protocole était
    à faire.
    """

    @pytest.fixture
    def planning_data_kin_and_normal(self):
        """Mix KIN (tss=0) + session cyclisme normale (tss>0) pour couvrir
        BT-037 vs non-régression."""
        return {
            "week_id": "S999",
            "start_date": "2026-03-02",
            "end_date": "2026-03-08",
            "created_at": "2026-02-01T20:00:00Z",
            "last_updated": "2026-02-01T20:00:00Z",
            "version": 1,
            "athlete_id": "iXXXXXX",
            "tss_target": 350,
            "planned_sessions": [
                {
                    "session_id": "S999-01",
                    "date": "2026-03-02",
                    "name": "KIN Protocole Achille",
                    "type": "KIN",
                    "version": "V001",
                    "tss_planned": 0,  # BT-037 : charge nulle
                    "duration_min": 30,
                    "description": "Protocole kiné prescrit",
                    "status": "planned",  # overwritable status (BT-036 laisserait passer)
                },
                {
                    "session_id": "S999-02",
                    "date": "2026-03-03",
                    "name": "INJ Off-bike",
                    "type": "INJ",
                    "version": "V001",
                    "tss_planned": 0,  # BT-037
                    "duration_min": 45,
                    "description": "Marche récup",
                    "status": "planned",
                },
                {
                    "session_id": "S999-03",
                    "date": "2026-03-04",
                    "name": "Endurance Z2",
                    "type": "END",
                    "version": "V001",
                    "tss_planned": 50,  # charge normale → doit rester overwritable
                    "duration_min": 60,
                    "description": "Endurance",
                    "status": "planned",
                },
            ],
        }

    @pytest.fixture
    def mock_ct_kin(self, tmp_path, planning_data_kin_and_normal):
        from magma_cycling.planning.control_tower import planning_tower

        original = planning_tower.planning_dir
        planning_tower.planning_dir = tmp_path
        planning_tower.backup_system.planning_dir = tmp_path
        planning_file = tmp_path / "week_planning_S999.json"
        with open(planning_file, "w", encoding="utf-8") as f:
            json.dump(planning_data_kin_and_normal, f, indent=2)
        yield tmp_path
        planning_tower.planning_dir = original
        planning_tower.backup_system.planning_dir = original

    @patch("magma_cycling.config.create_intervals_client")
    @patch("magma_cycling.update_session_status.sync_with_intervals")
    def test_auto_rest_day_skips_kin_zero_tss_session(
        self, mock_sync, mock_client, mock_ct_kin, caplog
    ):
        """Reproduit S106-07 : KIN planned tss=0 → skip + warning BT-037."""
        import logging

        from magma_cycling.workflows.sync.servo_evaluation import (
            ServoEvaluationMixin,
        )

        mixin = ServoEvaluationMixin()
        mod = {
            "action": "rest_day",
            "target_date": "2026-03-02",  # cible S999-01 KIN
            "current_workout": "S999-01-KIN-Protocole-V001",
            "reason": "Sommeil 5.0h (seuil critique < 7h)",
        }

        with caplog.at_level(
            logging.WARNING, logger="magma_cycling.workflows.sync.servo_evaluation"
        ):
            mixin._apply_auto_rest_day(mod, "S999")

        planning_file = mock_ct_kin / "week_planning_S999.json"
        plan = WeeklyPlan.from_json(planning_file)
        kin_session = next(s for s in plan.planned_sessions if s.session_id == "S999-01")
        assert kin_session.status == "planned", "KIN session écrasée à tort par auto rest_day"

        warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
        assert any(
            "BT-037" in r.message and "charge nulle" in r.message for r in warning_records
        ), f"Expected BT-037 warning, got: {[r.message for r in warning_records]}"

        mock_sync.assert_not_called()

    @patch("magma_cycling.config.create_intervals_client")
    @patch("magma_cycling.update_session_status.sync_with_intervals")
    def test_auto_rest_day_skips_inj_zero_tss_session(self, mock_sync, mock_client, mock_ct_kin):
        """INJ (off-bike) tss=0 → skip BT-037 aussi (générique tss=0, pas juste KIN)."""
        from magma_cycling.workflows.sync.servo_evaluation import (
            ServoEvaluationMixin,
        )

        mixin = ServoEvaluationMixin()
        mod = {
            "action": "rest_day",
            "target_date": "2026-03-03",  # cible S999-02 INJ
            "current_workout": "S999-02-INJ-Marche-V001",
            "reason": "TSB -15",
        }
        mixin._apply_auto_rest_day(mod, "S999")

        planning_file = mock_ct_kin / "week_planning_S999.json"
        plan = WeeklyPlan.from_json(planning_file)
        inj_session = next(s for s in plan.planned_sessions if s.session_id == "S999-02")
        assert inj_session.status == "planned"
        mock_sync.assert_not_called()

    @patch("magma_cycling.config.create_intervals_client")
    @patch("magma_cycling.update_session_status.sync_with_intervals")
    def test_auto_rest_day_still_overrides_normal_charge_session(
        self, mock_sync, mock_client, mock_ct_kin
    ):
        """Non-régression : session END avec tss=50 (charge normale)
        planned + trigger → override normal (comportement historique)."""
        from magma_cycling.workflows.sync.servo_evaluation import (
            ServoEvaluationMixin,
        )

        mock_sync.return_value = True
        mock_client.return_value = MagicMock()

        mixin = ServoEvaluationMixin()
        mod = {
            "action": "rest_day",
            "target_date": "2026-03-04",  # cible S999-03 END tss=50
            "current_workout": "S999-03-END-Endurance-V001",
            "reason": "TSB -20",
        }
        mixin._apply_auto_rest_day(mod, "S999")

        planning_file = mock_ct_kin / "week_planning_S999.json"
        plan = WeeklyPlan.from_json(planning_file)
        session = next(s for s in plan.planned_sessions if s.session_id == "S999-03")
        assert session.status == "rest_day", "Session à charge normale devrait rester overwritable"


class TestBT036AddendumRunCoherenceMultiEtapes:
    """BT-036 addendum : cohérence de vue entre étapes d'un même run daily-sync.

    Défaut structurel identifié par Coach AI dans l'audit S100-05 :

        20:01:10 — daily-sync marque completed depuis Intervals.icu
        20:01:39 — même run auto rest_day évalue et écrase en rest_day
        29 secondes d'écart, MÊME run daily-sync.

    « Deux étapes d'une même exécution n'ont pas la même vue de l'état. »
    Le fix BT-036 (guard status terminal) ferme le symptôme. Cet addendum
    teste le pattern structurel : le pre-check ``planning_tower.read_week()``
    dans ``_apply_auto_rest_day`` doit re-loader depuis le fichier, donc
    voir les modifications faites par l'étape précédente du même run
    (mark completed).

    Sans ce comportement, une TNR qui vérifie uniquement « auto rest_day
    ne rétrograde pas un completed pré-existant » passerait à côté du cas
    où completed vient d'être écrit dans le même run.
    """

    @pytest.fixture
    def planning_data_planned_session_with_intervals_id(self):
        """Semaine avec 1 session planned + intervals_id (candidate mark
        completed par étape 1 daily-sync)."""
        return {
            "week_id": "S999",
            "start_date": "2026-03-02",
            "end_date": "2026-03-08",
            "created_at": "2026-02-01T20:00:00Z",
            "last_updated": "2026-02-01T20:00:00Z",
            "version": 1,
            "athlete_id": "iXXXXXX",
            "tss_target": 200,
            "planned_sessions": [
                {
                    "session_id": "S999-05",
                    "date": "2026-03-06",
                    "name": "OpenersReproSt100_05",
                    "type": "END",
                    "version": "V001",
                    "tss_planned": 15,
                    "duration_min": 22,
                    "description": "Repro cas prod S100-05 openers veille de course",
                    "status": "planned",  # état initial pré-étape 1 du run
                    "intervals_id": 119167962,
                },
            ],
        }

    @pytest.fixture
    def mock_ct_multi_etapes(self, tmp_path, planning_data_planned_session_with_intervals_id):
        from magma_cycling.planning.control_tower import planning_tower

        original = planning_tower.planning_dir
        planning_tower.planning_dir = tmp_path
        planning_tower.backup_system.planning_dir = tmp_path
        planning_file = tmp_path / "week_planning_S999.json"
        with open(planning_file, "w", encoding="utf-8") as f:
            json.dump(planning_data_planned_session_with_intervals_id, f, indent=2)
        yield tmp_path
        planning_tower.planning_dir = original
        planning_tower.backup_system.planning_dir = original

    @patch("magma_cycling.config.create_intervals_client")
    @patch("magma_cycling.update_session_status.sync_with_intervals")
    def test_run_coherence_mark_completed_then_auto_rest_day_same_run(
        self, mock_sync, mock_client, mock_ct_multi_etapes, caplog
    ):
        """Reproduction structurelle du cas prod S100-05 :

        Étape 1 (mark completed) écrit ``status=completed`` dans le fichier.
        Étape 2 (auto rest_day) évalue immédiatement après, pre-check
        ``read_week()`` doit voir completed frais et skip (guard BT-036).

        C'est le comportement que le pre-check re-load fresh est censé
        garantir. Sans re-load, l'étape 2 travaillerait sur une vue en
        mémoire pre-étape 1 (status=planned) et écraserait sans détecter
        le completed juste écrit.
        """
        import logging

        from magma_cycling.planning.control_tower import planning_tower
        from magma_cycling.planning.models import WeeklyPlan
        from magma_cycling.workflows.sync.servo_evaluation import (
            ServoEvaluationMixin,
        )

        # === ÉTAPE 1 (simule mark completed from Intervals) ===
        # Écriture directe via planning_tower.modify_week (le path que
        # ``daily-sync`` utilise pour marquer completed en début de run).
        with planning_tower.modify_week(
            "S999",
            requesting_script="test-mark-completed-step1",
            reason="Test BT-036 addendum : mark completed step 1 of daily-sync run",
        ) as plan:
            for s in plan.planned_sessions:
                if s.session_id == "S999-05":
                    s.status = "completed"
                    break

        # Sanity : le fichier a bien été modifié on disk
        planning_file = mock_ct_multi_etapes / "week_planning_S999.json"
        plan_after_step1 = WeeklyPlan.from_json(planning_file)
        assert (
            next(s for s in plan_after_step1.planned_sessions if s.session_id == "S999-05").status
            == "completed"
        ), "Étape 1 (mark completed) doit avoir modifié le fichier avant étape 2"

        # === ÉTAPE 2 (auto rest_day evaluator, même run) ===
        # Le pre-check BT-036 fait read_week() qui re-load depuis le
        # fichier — doit voir le completed écrit par étape 1.
        mixin = ServoEvaluationMixin()
        mod = {
            "action": "rest_day",
            "target_date": "2026-03-06",  # même date que S999-05
            "current_workout": "S999-05-END-OpenersReproS100_05-V001",
            "reason": "Sommeil 5.5h + découplage -11% (repro trigger S100-05 réel)",
        }
        with caplog.at_level(
            logging.WARNING, logger="magma_cycling.workflows.sync.servo_evaluation"
        ):
            mixin._apply_auto_rest_day(mod, "S999")

        # === ASSERT structurel ===
        # Le pre-check read_week fresh doit avoir vu completed → skip.
        # Si le pre-check lisait une vue stale (status=planned initial),
        # il aurait laissé passer et écrasé en rest_day.
        plan_final = WeeklyPlan.from_json(planning_file)
        session = next(s for s in plan_final.planned_sessions if s.session_id == "S999-05")
        assert session.status == "completed", (
            "BT-036 addendum : le pre-check read_week doit avoir vu le "
            "completed écrit par l'étape précédente du même run. Sans cette "
            "cohérence de vue, l'étape 2 aurait écrasé en rest_day. "
            f"Actual status: {session.status}"
        )
        # Warning BT-036 émis (preuve que le pre-check a fait son travail)
        warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
        assert any(
            "BT-036" in r.message and "skipped" in r.message.lower() for r in warning_records
        ), (
            f"Expected BT-036 skip warning proving pre-check saw fresh completed, "
            f"got: {[r.message for r in warning_records]}"
        )
        # Sync Intervals.icu pas appelée (skip complet)
        mock_sync.assert_not_called()


class TestSyncIntervalsRestDay:
    """Test sync_with_intervals handles rest_day status."""

    def test_rest_day_in_statuses_to_delete(self):
        """Test rest_day is in STATUSES_TO_DELETE."""
        assert "rest_day" in STATUSES_TO_DELETE

    def test_sync_rest_day_converts_to_note(self):
        """Test rest_day converts event to NOTE with [REPOS] tag."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {
                "id": 42,
                "name": "S999-02-INT-Interval-V001",
                "category": "WORKOUT",
                "description": "Sweet Spot 3x10",
            }
        ]
        mock_client.update_event.return_value = True

        result = sync_with_intervals(
            client=mock_client,
            session_id="S999-02",
            session_date="2026-03-03",
            new_status="rest_day",
            reason="TSB -22, sommeil 4.8h",
        )

        assert result is True
        mock_client.update_event.assert_called_once()
        call_args = mock_client.update_event.call_args
        update_data = call_args[0][1]
        assert update_data["name"] == "[REPOS] S999-02-INT-Interval-V001"
        assert update_data["category"] == "NOTE"
        assert "😴 SÉANCE REPOS" in update_data["description"]
        assert "TSB -22, sommeil 4.8h" in update_data["description"]

    def test_sync_rest_day_creates_note_when_no_event(self):
        """Test rest_day creates NOTE when no event exists."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = []
        mock_client.create_event.return_value = {"id": 99}

        session_info = {
            "name": "Interval",
            "type": "INT",
            "version": "V001",
            "description": "Sweet Spot 3x10",
            "tss_planned": 70,
            "duration_min": 65,
        }

        result = sync_with_intervals(
            client=mock_client,
            session_id="S999-02",
            session_date="2026-03-03",
            new_status="rest_day",
            reason="Fatigue accumulée",
            session_info=session_info,
        )

        assert result is True
        mock_client.create_event.assert_called_once()
        call_args = mock_client.create_event.call_args
        event_data = call_args[0][0]
        assert event_data["name"] == "[REPOS] S999-02-INT-Interval-V001"
        assert event_data["category"] == "NOTE"
        assert "😴 SÉANCE REPOS" in event_data["description"]

    def test_sync_rest_day_skips_already_tagged(self):
        """Test rest_day skips event already tagged [REPOS]."""
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {
                "id": 42,
                "name": "[REPOS] S999-02-INT-Interval-V001",
                "category": "NOTE",
                "description": "Already repos",
            }
        ]

        result = sync_with_intervals(
            client=mock_client,
            session_id="S999-02",
            session_date="2026-03-03",
            new_status="rest_day",
        )

        assert result is True
        mock_client.update_event.assert_not_called()
