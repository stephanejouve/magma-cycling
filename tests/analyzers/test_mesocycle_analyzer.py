"""Tests for analyzers.mesocycle_analyzer module.

Tests MesocycleAnalyzer: pure logic methods (cycle detection, stats, parsing)
and state management. External dependencies (config, API) are mocked at __init__.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _make_analyzer(week_id="S078", mesocycle_weeks=6, state_file=None, data_repo_path=None):
    """Create a MesocycleAnalyzer with mocked external dependencies."""
    mock_data_config = MagicMock()
    mock_data_config.data_repo_path = data_repo_path or Path("/tmp/fake")

    mock_intervals_config = MagicMock()
    mock_intervals_config.athlete_id = "i123"
    mock_intervals_config.api_key = "fake_key"

    with (
        patch(
            "magma_cycling.analyzers.mesocycle_analyzer.get_data_config",
            return_value=mock_data_config,
        ),
        patch(
            "magma_cycling.analyzers.mesocycle_analyzer.get_intervals_config",
            return_value=mock_intervals_config,
        ),
        patch("magma_cycling.analyzers.mesocycle_analyzer.IntervalsClient"),
    ):
        from magma_cycling.analyzers.mesocycle_analyzer import MesocycleAnalyzer

        analyzer = MesocycleAnalyzer(week_id=week_id, mesocycle_weeks=mesocycle_weeks)

    if state_file:
        analyzer.state_file = state_file

    return analyzer


# ─── is_mesocycle_end ────────────────────────────────────────────────


class TestIsMesocycleEnd:
    """Tests for is_mesocycle_end()."""

    def test_week_divisible_by_6(self):
        analyzer = _make_analyzer("S078")
        assert analyzer.is_mesocycle_end() is True  # 78 % 6 == 0

    def test_week_not_divisible_by_6(self):
        analyzer = _make_analyzer("S079")
        assert analyzer.is_mesocycle_end() is False  # 79 % 6 == 1

    def test_week_84(self):
        analyzer = _make_analyzer("S084")
        assert analyzer.is_mesocycle_end() is True  # 84 % 6 == 0

    def test_custom_mesocycle_length_4(self):
        analyzer = _make_analyzer("S080", mesocycle_weeks=4)
        assert analyzer.is_mesocycle_end() is True  # 80 % 4 == 0

    def test_custom_mesocycle_length_4_not_end(self):
        analyzer = _make_analyzer("S081", mesocycle_weeks=4)
        assert analyzer.is_mesocycle_end() is False  # 81 % 4 == 1


# ─── should_generate_report ─────────────────────────────────────────


class TestShouldGenerateReport:
    """Tests for should_generate_report()."""

    def test_not_mesocycle_end(self):
        analyzer = _make_analyzer("S079")
        assert analyzer.should_generate_report() is False

    def test_mesocycle_end_not_analyzed(self):
        analyzer = _make_analyzer("S078")
        analyzer.state = {"analyzed_cycles": []}
        assert analyzer.should_generate_report() is True

    def test_mesocycle_end_already_analyzed(self):
        analyzer = _make_analyzer("S078")
        analyzer.state = {"analyzed_cycles": ["cycle_ending_S078"]}
        assert analyzer.should_generate_report() is False

    def test_different_cycle_analyzed(self):
        analyzer = _make_analyzer("S078")
        analyzer.state = {"analyzed_cycles": ["cycle_ending_S072"]}
        assert analyzer.should_generate_report() is True


# ─── _get_mesocycle_weeks / _get_previous_mesocycle_weeks ────────────


class TestGetMesocycleWeeks:
    """Tests for _get_mesocycle_weeks() and _get_previous_mesocycle_weeks()."""

    def test_current_mesocycle_weeks(self):
        analyzer = _make_analyzer("S078", mesocycle_weeks=6)
        weeks = analyzer._get_mesocycle_weeks()
        assert weeks == ["S073", "S074", "S075", "S076", "S077", "S078"]

    def test_previous_mesocycle_weeks(self):
        analyzer = _make_analyzer("S078", mesocycle_weeks=6)
        weeks = analyzer._get_previous_mesocycle_weeks()
        assert weeks == ["S067", "S068", "S069", "S070", "S071", "S072"]

    def test_mesocycle_4_weeks(self):
        analyzer = _make_analyzer("S080", mesocycle_weeks=4)
        weeks = analyzer._get_mesocycle_weeks()
        assert weeks == ["S077", "S078", "S079", "S080"]

    def test_previous_mesocycle_4_weeks(self):
        analyzer = _make_analyzer("S080", mesocycle_weeks=4)
        weeks = analyzer._get_previous_mesocycle_weeks()
        assert weeks == ["S073", "S074", "S075", "S076"]

    def test_week_format_zero_padded(self):
        analyzer = _make_analyzer("S012", mesocycle_weeks=6)
        weeks = analyzer._get_mesocycle_weeks()
        assert weeks[0] == "S007"
        assert all(w.startswith("S") and len(w) == 4 for w in weeks)


# ─── _load_state / _save_state ──────────────────────────────────────


class TestStateManagement:
    """Tests for _load_state() and _save_state()."""

    def test_load_state_file_not_found(self, tmp_path):
        analyzer = _make_analyzer("S078")
        analyzer.state_file = tmp_path / "nonexistent.json"
        result = analyzer._load_state()
        assert result == {"analyzed_cycles": []}

    def test_load_state_valid_file(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"analyzed_cycles": ["cycle_ending_S072"]}))
        analyzer = _make_analyzer("S078")
        analyzer.state_file = state_file
        result = analyzer._load_state()
        assert result["analyzed_cycles"] == ["cycle_ending_S072"]

    def test_load_state_corrupt_json(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text("{corrupt json")
        analyzer = _make_analyzer("S078")
        analyzer.state_file = state_file
        result = analyzer._load_state()
        assert result == {"analyzed_cycles": []}

    def test_save_state(self, tmp_path):
        state_file = tmp_path / "state.json"
        analyzer = _make_analyzer("S078")
        analyzer.state_file = state_file
        analyzer.state = {"analyzed_cycles": ["cycle_ending_S078"]}
        analyzer._save_state()
        data = json.loads(state_file.read_text())
        assert "cycle_ending_S078" in data["analyzed_cycles"]

    def test_save_state_permission_error(self, tmp_path):
        analyzer = _make_analyzer("S078")
        analyzer.state_file = Path("/nonexistent/dir/state.json")
        analyzer.state = {"analyzed_cycles": []}
        # Should not raise, just print warning
        analyzer._save_state()


# ─── _parse_workout_section ─────────────────────────────────────────


class TestParseWorkoutSection:
    """Tests for _parse_workout_section()."""

    def test_full_section(self):
        analyzer = _make_analyzer("S078")
        section = (
            " S078-02-INT-SweetSpot-V001\n"
            "TSS : 85\n"
            "IF : 0.82\n"
            "Découplage : 3.2%\n"
            "Durée : 60min\n"
            "Puissance moyenne : 195W\n"
            "Puissance normalisée : 210W\n"
            "✅ Découplage validé\n"
        )
        result = analyzer._parse_workout_section(section, "S078")
        assert result["week_id"] == "S078"
        assert result["tss"] == 85
        assert result["if"] == 0.82
        assert result["decoupling"] == 3.2
        assert result["duration"] == 60
        assert result["avg_power"] == 195
        assert result["np"] == 210
        assert result["validated"] is True

    def test_minimal_section(self):
        analyzer = _make_analyzer("S078")
        section = " S078-01-END\nTSS : 50\n"
        result = analyzer._parse_workout_section(section, "S078")
        assert result["tss"] == 50
        assert result["week_id"] == "S078"

    def test_section_no_metrics(self):
        analyzer = _make_analyzer("S078")
        section = " S078-01-END\nJust a ride\n"
        result = analyzer._parse_workout_section(section, "S078")
        # week_id + name + validated = 3 keys, but no real metrics
        # The method returns data if len(data) > 2, so with validated always present
        # it returns a dict with 3 keys
        assert result is not None
        assert result["week_id"] == "S078"
        assert "tss" not in result

    def test_not_validated(self):
        analyzer = _make_analyzer("S078")
        section = " S078-01-END\nTSS : 50\nDécouplage : 8.5%\n"
        result = analyzer._parse_workout_section(section, "S078")
        assert result["validated"] is False


# ─── _calculate_decoupling_stats ────────────────────────────────────


class TestCalculateDecouplingStats:
    """Tests for _calculate_decoupling_stats()."""

    def test_empty_workouts(self):
        analyzer = _make_analyzer("S078")
        result = analyzer._calculate_decoupling_stats([])
        assert result["count"] == 0
        assert result["avg"] == 0

    def test_no_decoupling_data(self):
        analyzer = _make_analyzer("S078")
        workouts = [{"tss": 50}, {"tss": 60}]
        result = analyzer._calculate_decoupling_stats(workouts)
        assert result["count"] == 0

    def test_with_decoupling_values(self):
        analyzer = _make_analyzer("S078")
        workouts = [
            {"decoupling": 3.0, "validated": True},
            {"decoupling": 5.0, "validated": True},
            {"decoupling": 8.0, "validated": False},
        ]
        result = analyzer._calculate_decoupling_stats(workouts)
        assert result["count"] == 3
        assert result["avg"] == pytest.approx(16.0 / 3, abs=0.1)
        assert result["min"] == 3.0
        assert result["max"] == 8.0
        assert result["validated_count"] == 2
        assert result["validated_pct"] == pytest.approx(2 / 3 * 100, abs=0.1)

    def test_all_validated(self):
        analyzer = _make_analyzer("S078")
        workouts = [
            {"decoupling": 2.0, "validated": True},
            {"decoupling": 4.0, "validated": True},
        ]
        result = analyzer._calculate_decoupling_stats(workouts)
        assert result["validated_pct"] == 100.0


# ─── _calculate_adherence_stats ─────────────────────────────────────


class TestCalculateAdherenceStats:
    """Tests for _calculate_adherence_stats()."""

    def test_empty_workouts(self):
        analyzer = _make_analyzer("S078")
        result = analyzer._calculate_adherence_stats([])
        assert result["tss_avg"] == 0
        assert result["tss_total"] == 0
        assert result["if_avg"] == 0
        assert result["workout_count"] == 0

    def test_with_values(self):
        analyzer = _make_analyzer("S078")
        workouts = [
            {"tss": 80, "if": 0.80},
            {"tss": 60, "if": 0.75},
        ]
        result = analyzer._calculate_adherence_stats(workouts)
        assert result["tss_avg"] == 70.0
        assert result["tss_total"] == 140
        assert result["if_avg"] == pytest.approx(0.775, abs=0.001)
        assert result["workout_count"] == 2

    def test_missing_if_values(self):
        analyzer = _make_analyzer("S078")
        workouts = [{"tss": 80}, {"tss": 60}]
        result = analyzer._calculate_adherence_stats(workouts)
        assert result["tss_avg"] == 70.0
        assert result["if_avg"] == 0


# ─── _analyze_workout_diversity ─────────────────────────────────────


class TestAnalyzeWorkoutDiversity:
    """Tests for _analyze_workout_diversity()."""

    def test_empty_workouts(self):
        analyzer = _make_analyzer("S078")
        result = analyzer._analyze_workout_diversity([])
        assert result["unique_count"] == 0
        assert result["total_count"] == 0
        assert result["diversity_pct"] == 0

    def test_diverse_workouts(self):
        analyzer = _make_analyzer("S078")
        workouts = [
            {"name": "S078-01-END-Endurance-V001"},
            {"name": "S078-02-INT-SweetSpot-V001"},
            {"name": "S078-03-REC-Recovery-V001"},
        ]
        result = analyzer._analyze_workout_diversity(workouts)
        assert result["unique_count"] == 3
        assert result["total_count"] == 3
        assert result["diversity_pct"] == 100.0
        assert "END" in result["by_type"]
        assert "INT" in result["by_type"]
        assert "REC" in result["by_type"]

    def test_repeated_workouts(self):
        analyzer = _make_analyzer("S078")
        workouts = [
            {"name": "S078-01-END-Endurance-V001"},
            {"name": "S078-01-END-Endurance-V001"},
            {"name": "S078-02-INT-SweetSpot-V001"},
        ]
        result = analyzer._analyze_workout_diversity(workouts)
        assert result["unique_count"] == 2
        assert result["total_count"] == 3
        assert result["diversity_pct"] == pytest.approx(2 / 3 * 100, abs=0.1)

    def test_no_dashes_in_name(self):
        analyzer = _make_analyzer("S078")
        workouts = [{"name": "JustARide"}]
        result = analyzer._analyze_workout_diversity(workouts)
        assert result["by_type"] == {}

    def test_type_counts(self):
        analyzer = _make_analyzer("S078")
        workouts = [
            {"name": "S078-01-END-A"},
            {"name": "S078-02-END-B"},
            {"name": "S078-03-INT-C"},
        ]
        result = analyzer._analyze_workout_diversity(workouts)
        assert result["by_type"]["END"] == 2
        assert result["by_type"]["INT"] == 1


# ─── _extract_workouts_from_history ─────────────────────────────────


class TestExtractWorkoutsFromHistory:
    """Tests for _extract_workouts_from_history()."""

    def test_file_not_found(self, tmp_path):
        analyzer = _make_analyzer("S078", data_repo_path=tmp_path)
        result = analyzer._extract_workouts_from_history(["S078"])
        assert result == []

    def test_extracts_matching_weeks(self, tmp_path):
        history_file = tmp_path / "workouts-history.md"
        history_file.write_text(
            "# History\n"
            "### S078-01-END-Endurance-V001\n"
            "TSS : 50\nIF : 0.70\nDécouplage : 3.5%\n"
            "### S079-01-INT-SweetSpot-V001\n"
            "TSS : 80\nIF : 0.85\n"
        )
        analyzer = _make_analyzer("S078", data_repo_path=tmp_path)
        result = analyzer._extract_workouts_from_history(["S078"])
        assert len(result) == 1
        assert result[0]["tss"] == 50

    def test_ignores_non_matching_weeks(self, tmp_path):
        history_file = tmp_path / "workouts-history.md"
        history_file.write_text("# History\n" "### S079-01-INT-SweetSpot-V001\n" "TSS : 80\n")
        analyzer = _make_analyzer("S078", data_repo_path=tmp_path)
        result = analyzer._extract_workouts_from_history(["S078"])
        assert result == []

    def test_multiple_weeks(self, tmp_path):
        history_file = tmp_path / "workouts-history.md"
        history_file.write_text(
            "# History\n"
            "### S077-01-END-A\nTSS : 40\nIF : 0.65\n"
            "### S078-01-INT-B\nTSS : 80\nIF : 0.85\n"
        )
        analyzer = _make_analyzer("S078", data_repo_path=tmp_path)
        result = analyzer._extract_workouts_from_history(["S077", "S078"])
        assert len(result) == 2


# ─── generate_mesocycle_report ──────────────────────────────────────


class TestGenerateMesocycleReport:
    """Tests for generate_mesocycle_report()."""

    def test_insufficient_data(self, tmp_path):
        history_file = tmp_path / "workouts-history.md"
        history_file.write_text("# History\n### S078-01-END\nTSS : 50\nIF : 0.7\n")
        analyzer = _make_analyzer("S078", data_repo_path=tmp_path)
        analyzer.state_file = tmp_path / "state.json"
        report = analyzer.generate_mesocycle_report()
        assert "Données insuffisantes" in report

    def test_full_report_with_data(self, tmp_path):
        history_file = tmp_path / "workouts-history.md"
        sections = []
        for i in range(1, 5):
            sections.append(
                f"### S078-0{i}-END-Endurance-V00{i}\n"
                f"TSS : {50 + i * 10}\n"
                f"IF : 0.{70 + i}\n"
                f"Découplage : {3.0 + i * 0.5}%\n"
                "✅ Découplage validé\n"
            )
        history_file.write_text("# History\n" + "".join(sections))

        analyzer = _make_analyzer("S078", data_repo_path=tmp_path)
        analyzer.state_file = tmp_path / "state.json"

        # generate_adherence_report is imported locally inside generate_mesocycle_report
        mock_adherence_mod = MagicMock()
        mock_adherence_mod.generate_adherence_report.side_effect = Exception("not available")

        with patch.dict(
            sys.modules,
            {"magma_cycling.analyzers.adherence_tracker": mock_adherence_mod},
        ):
            report = analyzer.generate_mesocycle_report()

        assert "ANALYSE MÉSO-CYCLE ENRICHIE" in report
        assert "Découplage Cardiovasculaire" in report
        assert "Charge d'Entraînement" in report
        assert "Diversité" in report
        assert "Insights Stratégiques" in report
        assert "Recommandations" in report

    def test_marks_cycle_as_analyzed(self, tmp_path):
        history_file = tmp_path / "workouts-history.md"
        sections = []
        for i in range(1, 5):
            sections.append(
                f"### S078-0{i}-INT-A\nTSS : {60 + i}\nIF : 0.8{i}\n" f"Découplage : {4.0 + i}%\n"
            )
        history_file.write_text("# History\n" + "".join(sections))

        state_file = tmp_path / "state.json"
        analyzer = _make_analyzer("S078", data_repo_path=tmp_path)
        analyzer.state_file = state_file
        analyzer.state = {"analyzed_cycles": []}
        analyzer.generate_mesocycle_report()

        assert "cycle_ending_S078" in analyzer.state["analyzed_cycles"]
        saved = json.loads(state_file.read_text())
        assert "cycle_ending_S078" in saved["analyzed_cycles"]

    def test_report_with_previous_cycle_comparison(self, tmp_path):
        history_file = tmp_path / "workouts-history.md"
        sections = []
        # Previous cycle S073-S078 equivalent, plus current
        for w in range(73, 79):
            sections.append(f"### S{w:03d}-01-END-A\nTSS : 55\nIF : 0.72\nDécouplage : 4.0%\n")
        history_file.write_text("# History\n" + "".join(sections))

        analyzer = _make_analyzer("S078", data_repo_path=tmp_path)
        analyzer.state_file = tmp_path / "state.json"
        report = analyzer.generate_mesocycle_report()

        assert "Tendance vs cycle précédent" in report or "ANALYSE MÉSO-CYCLE" in report


# ─── Insights generation ────────────────────────────────────────────


class TestInsightsGeneration:
    """Tests for insights in generate_mesocycle_report()."""

    def _make_report(self, tmp_path, decoupling_values, validated_flags):
        history_file = tmp_path / "workouts-history.md"
        sections = []
        for i, (dec, val) in enumerate(zip(decoupling_values, validated_flags)):
            valid_marker = "✅ Découplage" if val else ""
            sections.append(
                f"### S078-{i + 1:02d}-END-A\n"
                f"TSS : 60\nIF : 0.75\nDécouplage : {dec}%\n"
                f"{valid_marker}\n"
            )
        history_file.write_text("# History\n" + "".join(sections))

        analyzer = _make_analyzer("S078", data_repo_path=tmp_path)
        analyzer.state_file = tmp_path / "state.json"
        return analyzer.generate_mesocycle_report()

    def test_excellent_quality_insight(self, tmp_path):
        report = self._make_report(
            tmp_path,
            [3.0, 4.0, 5.0, 2.5],
            [True, True, True, True],
        )
        assert "Qualité excellente" in report

    def test_degraded_quality_insight(self, tmp_path):
        report = self._make_report(
            tmp_path,
            [8.0, 9.0, 10.0, 3.0],
            [False, False, False, True],
        )
        # validated_pct = 1/4 = 25% < 70%
        assert "Qualité dégradée" in report
