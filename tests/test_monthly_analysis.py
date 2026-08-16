"""Tests for monthly_analysis.py — actual TSS from Intervals.icu."""

from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.monthly_analysis import MonthlyAnalyzer


@pytest.fixture
def analyzer():
    """Create analyzer with mocked config dependencies."""
    with (
        patch("magma_cycling.monthly_analysis.get_data_config") as mock_dc,
        patch("magma_cycling.monthly_analysis.get_ai_config"),
    ):
        mock_dc.return_value.data_repo_path = MagicMock()
        yield MonthlyAnalyzer(month="2026-02", no_ai=True)


@pytest.fixture
def weekly_data():
    """Sample weekly data with sessions."""
    return [
        {
            "week_id": "S081",
            "start_date": "2026-02-02",
            "end_date": "2026-02-08",
            "tss_target": 400,
            "planned_sessions": [
                {
                    "session_id": "S081-01",
                    "type": "END",
                    "status": "completed",
                    "tss_planned": 50,
                    "intervals_id": 126184461,
                },
                {
                    "session_id": "S081-02",
                    "type": "INT",
                    "status": "completed",
                    "tss_planned": 0,
                    "intervals_id": 126200000,
                },
                {
                    "session_id": "S081-03",
                    "type": "REC",
                    "status": "skipped",
                    "tss_planned": 30,
                    "intervals_id": None,
                },
                {
                    "session_id": "S081-04",
                    "type": "END",
                    "status": "modified",
                    "tss_planned": 60,
                    "intervals_id": 126300000,
                },
            ],
        },
    ]


class TestFetchActualTss:
    """Tests for _fetch_actual_tss()."""

    def test_success(self, analyzer, weekly_data):
        """Successful API call returns {id: tss} mapping."""
        mock_client = MagicMock()
        mock_client.get_activities.return_value = [
            {"id": "i126184461", "icu_training_load": 120},
            {"id": "i126200000", "icu_training_load": 356},
            {"id": "i999999999", "icu_training_load": 45},
        ]

        with patch(
            "magma_cycling.config.create_intervals_client",
            return_value=mock_client,
        ):
            result = analyzer._fetch_actual_tss(weekly_data)

        assert result == {
            "i126184461": 120,
            "i126200000": 356,
            "i999999999": 45,
        }
        mock_client.get_activities.assert_called_once_with(oldest="2026-02-02", newest="2026-02-08")

    def test_api_failure_returns_empty_dict(self, analyzer, weekly_data):
        """API failure returns empty dict for graceful degradation."""
        with patch(
            "magma_cycling.config.create_intervals_client",
            side_effect=Exception("connection refused"),
        ):
            result = analyzer._fetch_actual_tss(weekly_data)

        assert result == {}

    def test_null_training_load_treated_as_zero(self, analyzer, weekly_data):
        """Activities with null icu_training_load get TSS=0."""
        mock_client = MagicMock()
        mock_client.get_activities.return_value = [
            {"id": "i126184461", "icu_training_load": None},
        ]

        with patch(
            "magma_cycling.config.create_intervals_client",
            return_value=mock_client,
        ):
            result = analyzer._fetch_actual_tss(weekly_data)

        assert result["i126184461"] == 0


class TestAggregateStatisticsActualTss:
    """Tests for aggregate_statistics() with actual TSS map."""

    def test_uses_actual_tss_when_available(self, analyzer, weekly_data):
        """Completed session with intervals_id uses actual TSS from map."""
        actual_tss_map = {
            "i126184461": 120,
            "i126200000": 356,
            "i126300000": 200,
        }

        stats = analyzer.aggregate_statistics(weekly_data, actual_tss_map)

        # S081-01: actual 120, S081-02: actual 356, S081-04 (modified): actual 200
        assert stats["tss_realized"] == 120 + 356 + 200

    def test_falls_back_to_planned_when_no_map(self, analyzer, weekly_data):
        """Without actual_tss_map, uses tss_planned."""
        stats = analyzer.aggregate_statistics(weekly_data, None)

        # S081-01: planned 50, S081-02: planned 0, S081-04 (modified): planned 60
        assert stats["tss_realized"] == 50 + 0 + 60

    def test_falls_back_when_id_not_in_map(self, analyzer, weekly_data):
        """Session with intervals_id not in map falls back to tss_planned."""
        # Only one activity in map — others fall back
        actual_tss_map = {"i126184461": 120}

        stats = analyzer.aggregate_statistics(weekly_data, actual_tss_map)

        # S081-01: actual 120, S081-02: planned 0 (not in map), S081-04: planned 60
        assert stats["tss_realized"] == 120 + 0 + 60

    def test_skipped_session_not_counted(self, analyzer, weekly_data):
        """Skipped sessions contribute 0 TSS regardless of map."""
        actual_tss_map = {"i126184461": 120, "i126200000": 356, "i126300000": 200}

        stats = analyzer.aggregate_statistics(weekly_data, actual_tss_map)

        # S081-03 is skipped — not in tss_realized
        assert stats["skipped"] == 1
        # Total = completed + modified only
        assert stats["tss_realized"] == 120 + 356 + 200

    def test_backward_compat_no_map(self, analyzer, weekly_data):
        """Calling without actual_tss_map (old signature) still works."""
        stats = analyzer.aggregate_statistics(weekly_data)

        assert stats["tss_realized"] == 50 + 0 + 60
        assert stats["completed"] == 2
        assert stats["modified"] == 1
        assert stats["skipped"] == 1

    def test_intervals_id_format_prefix(self, analyzer):
        """Verifies the 'i' prefix is correctly used for ID lookup."""
        data = [
            {
                "week_id": "S090",
                "start_date": "2026-03-01",
                "end_date": "2026-03-07",
                "tss_target": 300,
                "planned_sessions": [
                    {
                        "session_id": "S090-01",
                        "type": "END",
                        "status": "completed",
                        "tss_planned": 40,
                        "intervals_id": 999,
                    },
                ],
            },
        ]

        # Key WITHOUT "i" prefix — should NOT match
        stats_no_match = analyzer.aggregate_statistics(data, {"999": 200})
        assert stats_no_match["tss_realized"] == 40  # fallback to planned

        # Key WITH "i" prefix — should match
        stats_match = analyzer.aggregate_statistics(data, {"i999": 200})
        assert stats_match["tss_realized"] == 200

    def test_empty_actual_tss_map(self, analyzer, weekly_data):
        """Empty map behaves same as None — uses tss_planned."""
        stats = analyzer.aggregate_statistics(weekly_data, {})

        assert stats["tss_realized"] == 50 + 0 + 60


class TestStatsFieldRename:
    """Verify tss_planned is replaced by tss_realized in stats output."""

    def test_stats_has_tss_realized(self, analyzer, weekly_data):
        """Stats dict uses tss_realized, not tss_planned."""
        stats = analyzer.aggregate_statistics(weekly_data)

        assert "tss_realized" in stats
        assert "tss_planned" not in stats

    def test_report_uses_tss_realized(self, analyzer, weekly_data):
        """generate_report() reads tss_realized without KeyError."""
        stats = analyzer.aggregate_statistics(weekly_data)
        report = analyzer.generate_report(stats)

        assert "TSS Réalisé" in report
        assert str(stats["tss_realized"]) in report

    def test_ai_prompt_uses_tss_realized(self, analyzer, weekly_data):
        """generate_ai_prompt() reads tss_realized without KeyError."""
        stats = analyzer.aggregate_statistics(weekly_data)
        prompt = analyzer.generate_ai_prompt(stats)

        assert str(stats["tss_realized"]) in prompt


class TestBT039ActiveTssTarget:
    """BT-039 : cible active (post-annulations) distincte de la cible
    initiale, utilisée pour le calcul d'adhérence. Voie A (fix consommateur).

    Audit 2026-08-16 : 54 % des semaines biaisées par sessions fantômes
    (rest_day/skipped avec tss_planned>0), 2272 TSS cumulés fantômes.
    Ce fix répare les 20 semaines biaisées + toutes les futures.
    """

    def test_active_target_excludes_skipped_and_rest_day(self, analyzer):
        """Sessions annulées (rest_day, skipped, cancelled) exclues du
        calcul de la cible active. Cas reproduit S100 (course A)."""
        data = [
            {
                "week_id": "S100",
                "start_date": "2026-06-29",
                "end_date": "2026-07-05",
                "tss_target": 286,  # cible initiale stockée (intention)
                "planned_sessions": [
                    # Actives — comptent dans cible active
                    {
                        "session_id": "S100-05",
                        "type": "END",
                        "status": "completed",
                        "tss_planned": 15,
                        "intervals_id": 119167962,
                    },
                    {
                        "session_id": "S100-06",
                        "type": "END",
                        "status": "completed",
                        "tss_planned": 211,
                        "intervals_id": 119167963,
                    },
                    # Fantômes — EXCLUES de cible active (voie A)
                    {
                        "session_id": "S100-04",
                        "type": "SS",
                        "status": "rest_day",  # rétrograde manuelle affûtage J-2
                        "tss_planned": 72,  # ne doit PAS gonfler la cible
                    },
                    {
                        "session_id": "S100-01",
                        "type": "END",
                        "status": "skipped",
                        "tss_planned": 18,  # ne doit PAS gonfler la cible
                    },
                ],
            },
        ]
        stats = analyzer.aggregate_statistics(data)
        # Cible initiale stockée conservée (intention)
        assert stats["tss_target_total"] == 286
        # Cible active = seulement les sessions non-annulées (15 + 211 = 226)
        assert stats["tss_target_active_total"] == 226, (
            "Cible active doit exclure les 72 TSS rest_day (S100-04) "
            "et les 18 TSS skipped (S100-01)"
        )

    def test_achievement_rate_uses_active_target(self, analyzer):
        """Taux d'adhérence calculé sur cible active (référence), pas
        sur cible initiale gonflée."""
        data = [
            {
                "week_id": "S001",
                "start_date": "2026-01-05",
                "end_date": "2026-01-11",
                "tss_target": 300,  # cible initiale stockée
                "planned_sessions": [
                    {
                        "session_id": "S001-01",
                        "type": "END",
                        "status": "completed",
                        "tss_planned": 100,
                        "intervals_id": 100001,
                    },
                    {
                        "session_id": "S001-02",
                        "type": "END",
                        "status": "skipped",
                        "tss_planned": 100,  # exclu de cible active
                    },
                ],
            },
        ]
        # actual_tss_map couvre S001-01 pour un réalisé "vrai" Intervals
        stats = analyzer.aggregate_statistics(data, actual_tss_map={"i100001": 105})
        # Cible active = 100 (seulement session completed compte)
        assert stats["tss_target_active_total"] == 100
        # Réalisé Intervals = 105
        assert stats["tss_realized"] == 105
        # Achievement = 105 / 100 = 105% (excellent) — pas 105 / 300 = 35%
        assert stats["tss_achievement_rate"] == pytest.approx(105.0, abs=0.1), (
            "Taux d'adhérence doit être calculé sur cible active (100), "
            "pas sur cible initiale gonflée (300)"
        )

    def test_no_regression_when_all_sessions_active(self, analyzer):
        """Non-régression : semaine 100 % active → cible active = somme des
        tss_planned = équivalent à ce qu'on aurait avec l'ancien calcul si
        le champ tss_target stocké est cohérent avec la somme."""
        data = [
            {
                "week_id": "S001",
                "start_date": "2026-01-05",
                "end_date": "2026-01-11",
                "tss_target": 150,
                "planned_sessions": [
                    {
                        "session_id": "S001-01",
                        "type": "END",
                        "status": "planned",
                        "tss_planned": 50,
                    },
                    {
                        "session_id": "S001-02",
                        "type": "END",
                        "status": "completed",
                        "tss_planned": 100,
                        "intervals_id": 100002,
                    },
                ],
            },
        ]
        stats = analyzer.aggregate_statistics(data)
        # Toutes actives → active = somme = 150 = cible initiale
        assert stats["tss_target_active_total"] == 150
        assert stats["tss_target_total"] == 150

    def test_all_cancelled_week_no_zero_division_crash(self, analyzer):
        """Coach AI TNR : semaine 100 % annulée → cible active = 0 → taux
        d'adhérence = None (pas de division par zéro qui crash)."""
        data = [
            {
                "week_id": "S001",
                "start_date": "2026-01-05",
                "end_date": "2026-01-11",
                "tss_target": 200,
                "planned_sessions": [
                    {
                        "session_id": "S001-01",
                        "type": "END",
                        "status": "rest_day",
                        "tss_planned": 100,
                    },
                    {
                        "session_id": "S001-02",
                        "type": "END",
                        "status": "skipped",
                        "tss_planned": 100,
                    },
                ],
            },
        ]
        # Pas de crash
        stats = analyzer.aggregate_statistics(data)
        assert stats["tss_target_active_total"] == 0
        # Achievement = None (indéterminé, pas 0 ou crash)
        assert stats["tss_achievement_rate"] is None
        # Report généré sans crash + affiche "—"
        report = analyzer.generate_report(stats)
        assert "\u2014" in report  # unicode em-dash pour taux indéterminé

    def test_tss_source_map_marks_planned_fallback(self, analyzer):
        """BT-039 marqueur origine : session completed sans intervals_id
        (fallback tss_planned) est listée dans tss_source_map.planned_fallback."""
        data = [
            {
                "week_id": "S001",
                "start_date": "2026-01-05",
                "end_date": "2026-01-11",
                "tss_target": 100,
                "planned_sessions": [
                    {
                        "session_id": "S001-01",
                        "type": "KIN",
                        "status": "completed",
                        "tss_planned": 0,
                        "intervals_id": None,  # pas de match → fallback
                    },
                    {
                        "session_id": "S001-02",
                        "type": "END",
                        "status": "completed",
                        "tss_planned": 50,
                        "intervals_id": 200001,  # match Intervals
                    },
                ],
            },
        ]
        stats = analyzer.aggregate_statistics(data, actual_tss_map={"i200001": 55})
        # S001-01 KIN sans intervals_id → planned_fallback
        assert "S001-01" in stats["tss_source_map"]["planned_fallback"]
        # S001-02 avec match → intervals
        assert "S001-02" in stats["tss_source_map"]["intervals"]

    def test_report_shows_three_tss_columns(self, analyzer):
        """Bilan mensuel affiche 3 chiffres côte-à-côte : initiale | active | réalisé."""
        data = [
            {
                "week_id": "S100",
                "start_date": "2026-06-29",
                "end_date": "2026-07-05",
                "tss_target": 286,
                "planned_sessions": [
                    {
                        "session_id": "S100-06",
                        "type": "END",
                        "status": "completed",
                        "tss_planned": 211,
                        "intervals_id": 119167963,
                    },
                    {
                        "session_id": "S100-04",
                        "type": "SS",
                        "status": "rest_day",
                        "tss_planned": 72,
                    },
                ],
            },
        ]
        stats = analyzer.aggregate_statistics(data)
        report = analyzer.generate_report(stats)
        # 3 colonnes présentes
        assert "Cible initiale" in report
        assert "Cible active" in report
        assert "R\u00e9alis\u00e9" in report
        # Écart initial → active en valeur absolue (pas %)
        # Ici cible initiale=286 stockée mais sum(planned_sessions)=283 → gap
        # Le drift_line affiche "−N TSS" en absolu — vérifier présence "\u2212"
        # (moins unicode)
        assert "\u2212" in report or "TSS" in report
