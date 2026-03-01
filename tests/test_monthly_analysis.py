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
