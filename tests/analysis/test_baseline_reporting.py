"""Tests for analysis.baseline.reporting module.

Tests ReportingMixin : generate_json_output, generate_markdown_report, _format_markdown_report.
"""

import json
from datetime import date

from magma_cycling.analysis.baseline.reporting import ReportingMixin


class StubAnalyzer(ReportingMixin):
    """Stub providing required attributes for ReportingMixin."""

    def __init__(self, output_dir):
        self.output_dir = output_dir


def _make_results(
    *,
    adherence_rate=0.85,
    tss_planned=500,
    tss_actual=450,
    tsb_start=5.0,
    tsb_end=-3.0,
    cv_avg=0.04,
    quality_score=85,
):
    """Build a minimal results dict for reporting tests."""
    return {
        "metadata": {
            "period_start": "2026-01-27",
            "period_end": "2026-02-09",
            "duration_days": 14,
            "version": "1.0.0",
        },
        "quality": {
            "score": quality_score,
            "grade": "B",
            "completeness": {"adherence": 0.9, "wellness": 0.8, "activities": 10},
            "gaps": [],
            "anomalies": [],
        },
        "adherence": {
            "rate": adherence_rate,
            "completed": 10,
            "planned": 12,
            "skipped": 1,
            "replaced": 1,
            "cancelled": 0,
            "skipped_details": [
                {"date": "2026-02-03", "name": "S077-01", "reason": "Fatigue"},
            ],
            "replaced_details": [],
            "cancelled_details": [],
            "day_patterns": {
                "Monday": {"planned": 2, "completed": 2},
                "Wednesday": {"planned": 2, "completed": 1},
            },
            "skip_reasons_analysis": {"total": 0, "categories": {}, "distribution": {}},
            "day_patterns_analysis": {
                "high_risk_days": [],
                "recommendations": [],
            },
            "workout_type_patterns_analysis": {
                "high_risk_types": [],
                "recommendations": [],
            },
        },
        "tss": {
            "planned_total": tss_planned,
            "actual_total": tss_actual,
            "completion_rate": tss_actual / tss_planned if tss_planned else 0,
            "avg_daily_planned": tss_planned / 14,
            "avg_daily_actual": tss_actual / 14,
        },
        "tsb": {
            "start_tsb": tsb_start,
            "end_tsb": tsb_end,
            "avg_tsb": (tsb_start + tsb_end) / 2,
            "start_ctl": 40.0,
            "end_ctl": 42.0,
            "start_atl": 35.0,
            "end_atl": 45.0,
        },
        "cardiovascular_coupling": {
            "avg": cv_avg,
            "count": 5,
            "quality": "GOOD",
        },
    }


class TestGenerateJsonOutput:
    """Tests for generate_json_output()."""

    def test_creates_json_file(self, tmp_path):
        analyzer = StubAnalyzer(output_dir=tmp_path)
        results = _make_results()
        path = analyzer.generate_json_output(results)
        assert path.exists()
        assert path.name == "baseline_preliminary.json"

    def test_json_content_valid(self, tmp_path):
        analyzer = StubAnalyzer(output_dir=tmp_path)
        results = _make_results()
        path = analyzer.generate_json_output(results)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["metadata"]["duration_days"] == 14

    def test_json_default_str_serialization(self, tmp_path):
        analyzer = StubAnalyzer(output_dir=tmp_path)
        results = _make_results()
        results["metadata"]["some_date"] = date(2026, 1, 27)
        path = analyzer.generate_json_output(results)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["metadata"]["some_date"] == "2026-01-27"


class TestGenerateMarkdownReport:
    """Tests for generate_markdown_report()."""

    def test_creates_markdown_file(self, tmp_path):
        analyzer = StubAnalyzer(output_dir=tmp_path)
        results = _make_results()
        path = analyzer.generate_markdown_report(results)
        assert path.exists()
        assert path.suffix == ".md"

    def test_markdown_contains_title(self, tmp_path):
        analyzer = StubAnalyzer(output_dir=tmp_path)
        results = _make_results()
        path = analyzer.generate_markdown_report(results)
        content = path.read_text(encoding="utf-8")
        assert "# Rapport Baseline" in content


class TestFormatMarkdownReport:
    """Tests for _format_markdown_report()."""

    def test_contains_period_section(self, tmp_path):
        analyzer = StubAnalyzer(output_dir=tmp_path)
        results = _make_results()
        report = analyzer._format_markdown_report(results)
        assert "Période Analysée" in report
        assert "2026-01-27" in report

    def test_contains_adherence_section(self, tmp_path):
        analyzer = StubAnalyzer(output_dir=tmp_path)
        results = _make_results()
        report = analyzer._format_markdown_report(results)
        assert "Synthèse Adhérence" in report
        assert "85.0%" in report

    def test_contains_tss_section(self, tmp_path):
        analyzer = StubAnalyzer(output_dir=tmp_path)
        results = _make_results()
        report = analyzer._format_markdown_report(results)
        assert "Charge Entraînement" in report
        assert "500" in report

    def test_contains_tsb_section(self, tmp_path):
        analyzer = StubAnalyzer(output_dir=tmp_path)
        results = _make_results()
        report = analyzer._format_markdown_report(results)
        assert "Evolution Fitness" in report

    def test_contains_cv_section(self, tmp_path):
        analyzer = StubAnalyzer(output_dir=tmp_path)
        results = _make_results()
        report = analyzer._format_markdown_report(results)
        assert "Qualité Cardiovasculaire" in report

    def test_contains_quality_section(self, tmp_path):
        analyzer = StubAnalyzer(output_dir=tmp_path)
        results = _make_results()
        report = analyzer._format_markdown_report(results)
        assert "Qualité Données" in report
        assert "85/100" in report

    def test_overcharge_warning(self, tmp_path):
        analyzer = StubAnalyzer(output_dir=tmp_path)
        results = _make_results(tss_planned=400, tss_actual=500)
        report = analyzer._format_markdown_report(results)
        assert "Sur-charge" in report

    def test_undercharge_warning(self, tmp_path):
        analyzer = StubAnalyzer(output_dir=tmp_path)
        results = _make_results(tss_planned=500, tss_actual=350)
        report = analyzer._format_markdown_report(results)
        assert "Sous-charge" in report

    def test_optimal_charge(self, tmp_path):
        analyzer = StubAnalyzer(output_dir=tmp_path)
        results = _make_results(tss_planned=500, tss_actual=490)
        report = analyzer._format_markdown_report(results)
        assert "optimale" in report

    def test_skipped_details_in_report(self, tmp_path):
        analyzer = StubAnalyzer(output_dir=tmp_path)
        results = _make_results()
        report = analyzer._format_markdown_report(results)
        assert "Séances Sautées" in report
        assert "Fatigue" in report

    def test_no_skipped_shows_clean(self, tmp_path):
        analyzer = StubAnalyzer(output_dir=tmp_path)
        results = _make_results()
        results["adherence"]["skipped_details"] = []
        results["adherence"]["replaced_details"] = []
        results["adherence"]["cancelled_details"] = []
        report = analyzer._format_markdown_report(results)
        assert "Aucune séance manquée" in report

    def test_high_tsb_excellent_form(self, tmp_path):
        analyzer = StubAnalyzer(output_dir=tmp_path)
        results = _make_results(tsb_end=15.0)
        results["tsb"]["end_tsb"] = 15.0
        report = analyzer._format_markdown_report(results)
        assert "excellente" in report

    def test_negative_tsb_fatigue(self, tmp_path):
        analyzer = StubAnalyzer(output_dir=tmp_path)
        results = _make_results(tsb_end=-10.0)
        results["tsb"]["end_tsb"] = -10.0
        report = analyzer._format_markdown_report(results)
        assert "Fatigue" in report

    def test_insights_section(self, tmp_path):
        analyzer = StubAnalyzer(output_dir=tmp_path)
        results = _make_results()
        report = analyzer._format_markdown_report(results)
        assert "Insights" in report

    def test_day_patterns_table(self, tmp_path):
        analyzer = StubAnalyzer(output_dir=tmp_path)
        results = _make_results()
        report = analyzer._format_markdown_report(results)
        assert "Monday" in report
        assert "Wednesday" in report
