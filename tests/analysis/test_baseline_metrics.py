"""Tests for analysis.baseline.metrics module.

Tests MetricsMixin : validate_data_quality, calculate_tss_metrics,
analyze_tsb_trajectory, calculate_cv_coupling_metrics.
(calculate_adherence_metrics needs PatternAnalysisMixin — tested separately.)
"""

from datetime import date

import pytest

from magma_cycling.analysis.baseline.metrics import MetricsMixin


class StubAnalyzer(MetricsMixin):
    """Stub providing required attributes for MetricsMixin."""

    def __init__(
        self,
        *,
        start_date=date(2026, 1, 27),
        end_date=date(2026, 2, 9),
        adherence_data=None,
        wellness_data=None,
        activities_data=None,
        events_data=None,
        cv_coupling_values=None,
        skipped_sessions=None,
        replaced_sessions=None,
        cancelled_sessions=None,
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.duration_days = (end_date - start_date).days + 1
        self.adherence_data = adherence_data or []
        self.wellness_data = wellness_data or []
        self.activities_data = activities_data or []
        self.events_data = events_data or []
        self.cv_coupling_values = cv_coupling_values or []
        self.skipped_sessions = skipped_sessions or []
        self.replaced_sessions = replaced_sessions or []
        self.cancelled_sessions = cancelled_sessions or []


class TestValidateDataQuality:
    """Tests for validate_data_quality()."""

    def test_empty_data_low_score(self):
        analyzer = StubAnalyzer()
        quality = analyzer.validate_data_quality()
        assert quality["score"] <= 50
        assert quality["grade"] == "D"

    def test_full_adherence_completeness(self):
        # 14 days of data for 14-day period
        adherence = (
            [{"date": f"2026-02-{i:02d}", "adherence_rate": 0.9} for i in range(1, 10)]
            + [{"date": f"2026-01-{i:02d}", "adherence_rate": 0.9} for i in range(27, 32)]
            + [
                {"date": "2026-02-09", "adherence_rate": 0.9},
            ]
        )
        analyzer = StubAnalyzer(adherence_data=adherence)
        quality = analyzer.validate_data_quality()
        assert quality["completeness"]["adherence"] > 0.5

    def test_gaps_detected(self):
        # Only 1 day of data for 14-day period → many gaps
        adherence = [{"date": "2026-01-27", "adherence_rate": 0.9}]
        analyzer = StubAnalyzer(adherence_data=adherence)
        quality = analyzer.validate_data_quality()
        assert len(quality["gaps"]) > 0

    def test_negative_adherence_anomaly(self):
        adherence = [{"date": "2026-01-27", "adherence_rate": -0.5}]
        analyzer = StubAnalyzer(adherence_data=adherence)
        quality = analyzer.validate_data_quality()
        assert len(quality["anomalies"]) == 1
        assert quality["anomalies"][0]["type"] == "negative_adherence"

    def test_no_anomalies_clean_data(self):
        adherence = [{"date": "2026-01-27", "adherence_rate": 0.85}]
        analyzer = StubAnalyzer(adherence_data=adherence)
        quality = analyzer.validate_data_quality()
        assert len(quality["anomalies"]) == 0

    def test_grade_a_high_score(self):
        # Full adherence + wellness + cv_coupling for high score
        days = 14
        adherence = [
            {
                "date": f"2026-0{1 if i < 5 else 2}-{(27 + i) if i < 5 else (i - 4):02d}",
                "adherence_rate": 0.9,
            }
            for i in range(days)
        ]
        wellness = [{"id": f"2026-02-{i:02d}"} for i in range(1, 10)]
        analyzer = StubAnalyzer(
            adherence_data=adherence,
            wellness_data=wellness,
            cv_coupling_values=[0.03, 0.04],
        )
        quality = analyzer.validate_data_quality()
        assert quality["score"] >= 80

    def test_wellness_completeness(self):
        wellness = [{"id": f"2026-02-{i:02d}"} for i in range(1, 8)]
        analyzer = StubAnalyzer(wellness_data=wellness)
        quality = analyzer.validate_data_quality()
        assert quality["completeness"]["wellness"] == pytest.approx(7 / 14, abs=0.01)


class TestCalculateTssMetrics:
    """Tests for calculate_tss_metrics()."""

    def test_empty_data(self):
        analyzer = StubAnalyzer()
        metrics = analyzer.calculate_tss_metrics()
        assert metrics["planned_total"] == 0
        assert metrics["actual_total"] == 0
        assert metrics["completion_rate"] == 0

    def test_planned_and_actual(self):
        events = [
            {"icu_training_load": 50},
            {"icu_training_load": 70},
        ]
        activities = [
            {"icu_training_load": 45},
            {"icu_training_load": 65},
        ]
        analyzer = StubAnalyzer(events_data=events, activities_data=activities)
        metrics = analyzer.calculate_tss_metrics()
        assert metrics["planned_total"] == 120
        assert metrics["actual_total"] == 110
        assert metrics["completion_rate"] == pytest.approx(110 / 120, abs=0.01)

    def test_none_training_load_handled(self):
        events = [{"icu_training_load": None}, {"icu_training_load": 50}]
        activities = [{"icu_training_load": None}]
        analyzer = StubAnalyzer(events_data=events, activities_data=activities)
        metrics = analyzer.calculate_tss_metrics()
        assert metrics["planned_total"] == 50
        assert metrics["actual_total"] == 0

    def test_avg_daily(self):
        events = [{"icu_training_load": 140}]
        activities = [{"icu_training_load": 140}]
        analyzer = StubAnalyzer(events_data=events, activities_data=activities)
        metrics = analyzer.calculate_tss_metrics()
        assert metrics["avg_daily_planned"] == pytest.approx(140 / 14, abs=0.1)


class TestAnalyzeTsbTrajectory:
    """Tests for analyze_tsb_trajectory()."""

    def test_empty_wellness(self):
        analyzer = StubAnalyzer()
        result = analyzer.analyze_tsb_trajectory()
        assert result == {}

    def test_single_day(self):
        wellness = [{"id": "2026-01-27", "tsb": 5.0, "ctl": 40.0, "atl": 35.0}]
        analyzer = StubAnalyzer(wellness_data=wellness)
        result = analyzer.analyze_tsb_trajectory()
        assert result["start_tsb"] == 5.0
        assert result["end_tsb"] == 5.0
        assert result["start_ctl"] == 40.0

    def test_trajectory_multiple_days(self):
        wellness = [
            {"id": "2026-01-27", "tsb": 10.0, "ctl": 38.0, "atl": 28.0},
            {"id": "2026-01-28", "tsb": 5.0, "ctl": 39.0, "atl": 34.0},
            {"id": "2026-01-29", "tsb": -2.0, "ctl": 40.0, "atl": 42.0},
        ]
        analyzer = StubAnalyzer(wellness_data=wellness)
        result = analyzer.analyze_tsb_trajectory()
        assert result["start_tsb"] == 10.0
        assert result["end_tsb"] == -2.0
        assert result["avg_tsb"] == pytest.approx((10 + 5 - 2) / 3, abs=0.1)
        assert len(result["trajectory"]) == 3

    def test_sorted_by_date(self):
        wellness = [
            {"id": "2026-01-29", "tsb": -2.0, "ctl": 40.0, "atl": 42.0},
            {"id": "2026-01-27", "tsb": 10.0, "ctl": 38.0, "atl": 28.0},
        ]
        analyzer = StubAnalyzer(wellness_data=wellness)
        result = analyzer.analyze_tsb_trajectory()
        # Should be sorted by id (date)
        assert result["start_tsb"] == 10.0
        assert result["end_tsb"] == -2.0


class TestCalculateCvCouplingMetrics:
    """Tests for calculate_cv_coupling_metrics()."""

    def test_no_data(self):
        analyzer = StubAnalyzer()
        result = analyzer.calculate_cv_coupling_metrics()
        assert result["quality"] == "NO_DATA"
        assert result["count"] == 0

    def test_excellent_quality(self):
        analyzer = StubAnalyzer(cv_coupling_values=[0.015, 0.020, 0.018])
        result = analyzer.calculate_cv_coupling_metrics()
        assert result["quality"] == "EXCELLENT"
        assert result["count"] == 3

    def test_good_quality(self):
        analyzer = StubAnalyzer(cv_coupling_values=[0.035, 0.040, 0.038])
        result = analyzer.calculate_cv_coupling_metrics()
        assert result["quality"] == "GOOD"

    def test_acceptable_quality(self):
        analyzer = StubAnalyzer(cv_coupling_values=[0.060, 0.065])
        result = analyzer.calculate_cv_coupling_metrics()
        assert result["quality"] == "ACCEPTABLE"

    def test_poor_quality(self):
        analyzer = StubAnalyzer(cv_coupling_values=[0.08, 0.09, 0.10])
        result = analyzer.calculate_cv_coupling_metrics()
        assert result["quality"] == "POOR"

    def test_avg_calculation(self):
        values = [0.02, 0.04, 0.06]
        analyzer = StubAnalyzer(cv_coupling_values=values)
        result = analyzer.calculate_cv_coupling_metrics()
        assert result["avg"] == pytest.approx(0.04, abs=0.001)
