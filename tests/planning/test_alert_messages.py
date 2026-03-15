"""Tests for planning.alert_messages module.

Tests fonctions pures de formatage d'alertes CTL, distribution, qualité test.
"""

from datetime import date

from magma_cycling.planning.alert_messages import (
    CTLAlertData,
    DistributionAlertData,
    TestQualityAlertData,
    format_ctl_alert,
    format_distribution_alert,
    format_test_quality_alert,
    generate_ctl_drop_alert,
    generate_distribution_alert,
    generate_test_quality_alert_1min,
)


class TestFormatCTLAlert:
    """Tests for format_ctl_alert()."""

    def test_contains_alert_header(self):
        data = CTLAlertData(
            ctl_current=41.8,
            ctl_required=70,
            ctl_deficit=28.2,
            ctl_drop=15,
            drop_weeks=4,
            ftp_target=260,
            athlete_age=54,
            weeks_phase1=11,
            ctl_intermediate=55,
            tss_weekly=350,
            recovery_frequency=2,
            total_weeks=16,
        )
        result = format_ctl_alert(data)
        assert "ALERTE CTL CRITIQUE" in result

    def test_contains_ctl_values(self):
        data = CTLAlertData(
            ctl_current=41.8,
            ctl_required=70,
            ctl_deficit=28.2,
            ctl_drop=15,
            drop_weeks=4,
            ftp_target=260,
            athlete_age=54,
            weeks_phase1=11,
            ctl_intermediate=55,
            tss_weekly=350,
            recovery_frequency=2,
            total_weeks=16,
        )
        result = format_ctl_alert(data)
        assert "41.8" in result
        assert "70" in result
        assert "28.2" in result

    def test_contains_ftp_target(self):
        data = CTLAlertData(
            ctl_current=50.0,
            ctl_required=80,
            ctl_deficit=30.0,
            ctl_drop=10,
            drop_weeks=3,
            ftp_target=280,
            athlete_age=45,
            weeks_phase1=12,
            ctl_intermediate=65,
            tss_weekly=400,
            recovery_frequency=3,
            total_weeks=20,
        )
        result = format_ctl_alert(data)
        assert "280W" in result

    def test_contains_plan_details(self):
        data = CTLAlertData(
            ctl_current=41.8,
            ctl_required=70,
            ctl_deficit=28.2,
            ctl_drop=15,
            drop_weeks=4,
            ftp_target=260,
            athlete_age=54,
            weeks_phase1=11,
            ctl_intermediate=55,
            tss_weekly=350,
            recovery_frequency=2,
            total_weeks=16,
        )
        result = format_ctl_alert(data)
        assert "PLAN RECONSTRUCTION" in result
        assert "350 TSS" in result
        assert "Tempo" in result


class TestFormatDistributionAlert:
    """Tests for format_distribution_alert()."""

    def test_contains_header(self):
        data = DistributionAlertData(
            current_distribution={"VO2": 0.25, "FTP": 0.30, "Tempo": 0.15},
            issue_description="Trop d'intensité haute",
            quote_hunter_allen="Traditional method...",
        )
        result = format_distribution_alert(data)
        assert "DISTRIBUTION INTENSITÉ" in result

    def test_contains_zones(self):
        data = DistributionAlertData(
            current_distribution={"VO2": 0.25, "FTP": 0.30, "Tempo": 0.15},
            issue_description="Trop d'intensité haute",
            quote_hunter_allen="Traditional method...",
        )
        result = format_distribution_alert(data)
        assert "VO2" in result
        assert "FTP" in result
        assert "Tempo" in result

    def test_contains_recommendation(self):
        data = DistributionAlertData(
            current_distribution={"Endurance": 0.50},
            issue_description="Distribution non optimale",
            quote_hunter_allen="Quote test",
        )
        result = format_distribution_alert(data)
        assert "Distribution recommandée" in result
        assert "Quote test" in result

    def test_zones_sorted_by_percentage_desc(self):
        data = DistributionAlertData(
            current_distribution={"Endurance": 0.10, "VO2": 0.50, "Tempo": 0.30},
            issue_description="Test",
            quote_hunter_allen="Test",
        )
        result = format_distribution_alert(data)
        vo2_pos = result.index("VO2")
        tempo_pos = result.index("Tempo")
        endurance_pos = result.index("- Endurance: 10%")
        assert vo2_pos < tempo_pos < endurance_pos


class TestFormatTestQualityAlert:
    """Tests for format_test_quality_alert()."""

    def test_1min_test(self):
        data = TestQualityAlertData(
            test_type="1min",
            power_result=425,
            issue_description="plateau dernières 30s",
            retest_date_recommendation=date(2026, 2, 21),
        )
        result = format_test_quality_alert(data)
        assert "TEST 1 MINUTE" in result
        assert "425W" in result
        assert "21/02/2026" in result
        assert "Échauffement 20min" in result

    def test_5min_test(self):
        data = TestQualityAlertData(
            test_type="5min",
            power_result=310,
            issue_description="chute brutale",
            retest_date_recommendation=date(2026, 3, 1),
        )
        result = format_test_quality_alert(data)
        assert "TEST 5 MINUTES" in result
        assert "310W" in result
        assert "Dérive progressive" in result

    def test_20min_test(self):
        data = TestQualityAlertData(
            test_type="20min",
            power_result=250,
            issue_description="pacing trop agressif",
            retest_date_recommendation=date(2026, 3, 15),
        )
        result = format_test_quality_alert(data)
        assert "TEST FTP 20 MINUTES" in result
        assert "250W" in result
        assert "FTP = 95%" in result

    def test_unknown_test_type(self):
        data = TestQualityAlertData(
            test_type="3min",
            power_result=350,
            issue_description="test custom",
            retest_date_recommendation=date(2026, 4, 1),
        )
        result = format_test_quality_alert(data)
        assert "TEST 3MIN" in result


class TestGenerateCTLDropAlert:
    """Tests for generate_ctl_drop_alert()."""

    def test_masters_significant_drop(self):
        alert = generate_ctl_drop_alert(
            ctl_current=41.8,
            ctl_previous=56.8,
            weeks_between=4,
            ftp_current=220,
            ftp_target=260,
            athlete_age=54,
            ctl_minimum_for_ftp=70,
        )
        assert alert is not None
        assert "ALERTE" in alert

    def test_no_alert_when_above_minimum(self):
        alert = generate_ctl_drop_alert(
            ctl_current=75,
            ctl_previous=78,
            weeks_between=4,
            ftp_current=250,
            ftp_target=260,
            athlete_age=54,
            ctl_minimum_for_ftp=70,
        )
        assert alert is None

    def test_alert_below_minimum_young_athlete(self):
        alert = generate_ctl_drop_alert(
            ctl_current=40,
            ctl_previous=45,
            weeks_between=4,
            ftp_current=220,
            ftp_target=280,
            athlete_age=30,
            ctl_minimum_for_ftp=70,
        )
        assert alert is not None

    def test_recovery_frequency_masters(self):
        alert = generate_ctl_drop_alert(
            ctl_current=41.8,
            ctl_previous=56.8,
            weeks_between=4,
            ftp_current=220,
            ftp_target=260,
            athlete_age=54,
            ctl_minimum_for_ftp=70,
        )
        assert "Tous les 2 semaines" in alert

    def test_no_alert_small_drop_above_minimum(self):
        alert = generate_ctl_drop_alert(
            ctl_current=80,
            ctl_previous=85,
            weeks_between=4,
            ftp_current=250,
            ftp_target=260,
            athlete_age=54,
            ctl_minimum_for_ftp=70,
        )
        assert alert is None


class TestGenerateDistributionAlert:
    """Tests for generate_distribution_alert()."""

    def test_too_much_vo2_reconstruction(self):
        dist = {"VO2": 0.30, "FTP": 0.25, "Tempo": 0.10, "Endurance": 0.25}
        alert = generate_distribution_alert(dist, "RECONSTRUCTION_BASE")
        assert alert is not None
        assert "Tempo" in alert

    def test_balanced_distribution_no_alert(self):
        dist = {"VO2": 0.10, "FTP": 0.15, "Tempo": 0.35, "Sweet-Spot": 0.20, "Endurance": 0.20}
        alert = generate_distribution_alert(dist, "RECONSTRUCTION_BASE")
        assert alert is None

    def test_unknown_phase_returns_none(self):
        dist = {"VO2": 0.50}
        alert = generate_distribution_alert(dist, "UNKNOWN_PHASE")
        assert alert is None

    def test_consolidation_phase(self):
        dist = {"Sweet-Spot": 0.05, "Tempo": 0.10, "FTP": 0.40}
        alert = generate_distribution_alert(dist, "CONSOLIDATION")
        assert alert is not None

    def test_development_ftp_phase(self):
        dist = {"FTP": 0.01, "VO2": 0.01, "Sweet-Spot": 0.01}
        alert = generate_distribution_alert(dist, "DEVELOPMENT_FTP")
        assert alert is not None


class TestGenerateTestQualityAlert1min:
    """Tests for generate_test_quality_alert_1min()."""

    def test_plateau_triggers_alert(self):
        alert = generate_test_quality_alert_1min(
            power_avg=425,
            power_30s_first=430,
            power_30s_second=420,
        )
        assert alert is not None
        assert "plateau" in alert

    def test_correct_execution_no_alert(self):
        alert = generate_test_quality_alert_1min(
            power_avg=400,
            power_30s_first=450,
            power_30s_second=350,
        )
        assert alert is None

    def test_excessive_drop_triggers_alert(self):
        alert = generate_test_quality_alert_1min(
            power_avg=400,
            power_30s_first=500,
            power_30s_second=300,
        )
        assert alert is not None
        assert "chute excessive" in alert

    def test_custom_retest_weeks(self):
        alert = generate_test_quality_alert_1min(
            power_avg=425,
            power_30s_first=430,
            power_30s_second=420,
            retest_weeks=2,
        )
        assert alert is not None
        assert "Retest recommandé" in alert
