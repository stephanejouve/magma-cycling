"""Tests for outdoor discipline monitoring module."""

from datetime import date

import pytest

from magma_cycling.planning.outdoor_discipline import (
    DisciplineStatus,
    EnvironmentRecommendation,
    analyze_zone_history,
    calculate_if_deviation,
    check_discipline,
    generate_discipline_report,
)


class TestCalculateIfDeviation:
    """Tests for IF deviation calculation."""

    def test_overload(self):
        """Positive deviation = overload."""
        result = calculate_if_deviation(0.85, 0.75)
        assert result == pytest.approx(13.33, abs=0.01)

    def test_underload(self):
        """Negative deviation = underload."""
        result = calculate_if_deviation(0.70, 0.75)
        assert result == pytest.approx(-6.67, abs=0.01)

    def test_exact_match(self):
        """No deviation."""
        result = calculate_if_deviation(0.80, 0.80)
        assert result == 0.0

    def test_if_planned_zero(self):
        """Division by zero protection."""
        result = calculate_if_deviation(0.85, 0.0)
        assert result == 0.0

    def test_small_deviation(self):
        """Small deviation within tolerance."""
        result = calculate_if_deviation(0.82, 0.80)
        assert result == pytest.approx(2.5, abs=0.01)


class TestCheckDiscipline:
    """Tests for single discipline check."""

    def test_success_within_5_percent(self):
        """IF deviation <5% → SUCCESS."""
        check = check_discipline("Tempo ride", date(2026, 3, 1), "Tempo", "outdoor", 0.80, 0.82)
        assert check.status == DisciplineStatus.SUCCESS
        assert "Discipline respectée" in check.message

    def test_warning_between_5_and_10(self):
        """IF deviation 5-10% → WARNING."""
        check = check_discipline(
            "Sweet Spot", date(2026, 3, 1), "Sweet-Spot", "outdoor", 0.80, 0.87
        )
        assert check.status == DisciplineStatus.WARNING
        assert "Discipline limite" in check.message

    def test_failure_over_10_percent(self):
        """IF deviation >10% → FAILURE."""
        check = check_discipline("VO2 intervals", date(2026, 3, 1), "VO2", "outdoor", 0.90, 1.02)
        assert check.status == DisciplineStatus.FAILURE
        assert "Échec discipline" in check.message

    def test_underload_warning(self):
        """IF deviation <-10% → WARNING (sous-intensité)."""
        check = check_discipline("FTP test", date(2026, 3, 1), "FTP", "outdoor", 0.95, 0.80)
        assert check.status == DisciplineStatus.WARNING
        assert "Sous-intensité" in check.message

    def test_deviation_stored_in_result(self):
        """Deviation percentage stored in result."""
        check = check_discipline("Test", date(2026, 3, 1), "Tempo", "outdoor", 0.80, 0.90)
        assert check.if_deviation_percent == pytest.approx(12.5, abs=0.01)


class TestAnalyzeZoneHistory:
    """Tests for zone history analysis."""

    def _make_check(self, status, environment="outdoor"):
        """Create a DisciplineCheck for testing."""
        return check_discipline(
            "Test",
            date(2026, 3, 1),
            "VO2",
            environment,
            0.90,
            1.05 if status == DisciplineStatus.FAILURE else 0.91,
        )

    def test_no_failures_outdoor_ok(self):
        """0 failures → OUTDOOR_OK."""
        checks = [self._make_check(DisciplineStatus.SUCCESS)]
        history = analyze_zone_history("VO2", checks)
        assert history.environment_recommendation == EnvironmentRecommendation.OUTDOOR_OK

    def test_one_failure_indoor_preferred(self):
        """1 failure → INDOOR_PREFERRED."""
        checks = [self._make_check(DisciplineStatus.FAILURE)]
        history = analyze_zone_history("VO2", checks)
        assert history.environment_recommendation == EnvironmentRecommendation.INDOOR_PREFERRED

    def test_two_failures_indoor_required(self):
        """2+ failures → INDOOR_REQUIRED."""
        checks = [
            self._make_check(DisciplineStatus.FAILURE),
            self._make_check(DisciplineStatus.FAILURE),
        ]
        history = analyze_zone_history("VO2", checks)
        assert history.environment_recommendation == EnvironmentRecommendation.INDOOR_REQUIRED

    def test_no_outdoor_checks(self):
        """No outdoor checks → OUTDOOR_OK."""
        history = analyze_zone_history("VO2", [])
        assert history.environment_recommendation == EnvironmentRecommendation.OUTDOOR_OK
        assert history.total_outdoor_workouts == 0

    def test_indoor_checks_ignored(self):
        """Indoor checks not counted as outdoor failures."""
        checks = [
            self._make_check(DisciplineStatus.FAILURE, environment="indoor"),
            self._make_check(DisciplineStatus.FAILURE, environment="indoor"),
        ]
        history = analyze_zone_history("VO2", checks)
        assert history.environment_recommendation == EnvironmentRecommendation.OUTDOOR_OK
        assert history.failure_count == 0

    def test_custom_failure_threshold(self):
        """Custom threshold applies."""
        checks = [self._make_check(DisciplineStatus.FAILURE)]
        history = analyze_zone_history("VO2", checks, failure_threshold=1)
        assert history.environment_recommendation == EnvironmentRecommendation.INDOOR_REQUIRED


class TestGenerateDisciplineReport:
    """Tests for discipline report generation."""

    def test_success_no_alert(self):
        """Success → no alert message."""
        check = check_discipline("Tempo", date(2026, 3, 1), "Tempo", "outdoor", 0.80, 0.82)
        report = generate_discipline_report(check)
        assert report.alert_message is None
        assert report.overall_recommendation == EnvironmentRecommendation.OUTDOOR_OK

    def test_failure_has_alert(self):
        """Failure → alert message present."""
        check = check_discipline("VO2", date(2026, 3, 1), "VO2", "outdoor", 0.90, 1.05)
        report = generate_discipline_report(check)
        assert report.alert_message is not None
        assert "ÉCHEC DISCIPLINE" in report.alert_message

    def test_failure_with_history_indoor_required(self):
        """Failure + repeated history → INDOOR_REQUIRED with alert."""
        check = check_discipline("VO2", date(2026, 3, 1), "VO2", "outdoor", 0.90, 1.05)
        history = analyze_zone_history("VO2", [check, check])
        report = generate_discipline_report(check, history)
        assert report.overall_recommendation == EnvironmentRecommendation.INDOOR_REQUIRED
        assert "ALERTE DISCIPLINE OUTDOOR" in report.alert_message
        assert report.recovery_period_months == 3

    def test_warning_has_alert(self):
        """Warning → alert message with surveillance."""
        check = check_discipline("SS", date(2026, 3, 1), "Sweet-Spot", "outdoor", 0.80, 0.87)
        report = generate_discipline_report(check)
        assert report.alert_message is not None
        assert "LIMITE" in report.alert_message
