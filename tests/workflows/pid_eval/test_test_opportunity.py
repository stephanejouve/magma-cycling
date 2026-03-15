"""Tests for TestOpportunityMixin."""

from datetime import date
from unittest.mock import MagicMock, patch

from magma_cycling.workflows.pid_eval.test_opportunity import TestOpportunityMixin


class StubTestOpp(TestOpportunityMixin):
    """Stub class to test TestOpportunityMixin."""

    def __init__(self, client):
        """Initialize stub with mock client."""
        self.client = client


class TestCheckTestOpportunity:
    """Tests for check_test_opportunity."""

    def test_ready_when_overdue_and_form_ready(self):
        """READY status when test overdue + TSB >= 5 + CTL >= 40."""
        client = MagicMock()
        client.get_wellness.return_value = [{"tsb": 10, "ctl": 55}]
        client.get_activities.return_value = []  # no recent tests → 16 weeks
        stub = StubTestOpp(client)
        result = stub.check_test_opportunity()
        assert result is not None
        assert result["status"] == "READY"

    def test_needs_taper_when_form_neutral(self):
        """NEEDS_TAPER when test overdue + form neutral (-5 to 5)."""
        client = MagicMock()
        client.get_wellness.return_value = [{"tsb": 2, "ctl": 55}]
        client.get_activities.return_value = []
        stub = StubTestOpp(client)
        result = stub.check_test_opportunity()
        assert result is not None
        assert result["status"] == "NEEDS_TAPER"

    def test_overdue_low_fitness(self):
        """OVERDUE_LOW_FITNESS when test overdue but low CTL."""
        client = MagicMock()
        client.get_wellness.return_value = [{"tsb": -10, "ctl": 30}]
        client.get_activities.return_value = []
        stub = StubTestOpp(client)
        result = stub.check_test_opportunity()
        assert result is not None
        assert result["status"] == "OVERDUE_LOW_FITNESS"

    def test_none_when_not_overdue(self):
        """None when last test was recent (< 6 weeks)."""
        client = MagicMock()
        client.get_wellness.return_value = [{"tsb": 10, "ctl": 55}]
        # Recent test-like activity (high IF, 45min)
        client.get_activities.return_value = [
            {
                "icu_intensity": 0.95,
                "moving_time": 2700,  # 45 min
                "start_date_local": date.today().isoformat(),
            }
        ]
        stub = StubTestOpp(client)
        result = stub.check_test_opportunity()
        assert result is None

    def test_none_when_no_wellness(self):
        """None when wellness data unavailable."""
        client = MagicMock()
        client.get_wellness.return_value = []
        stub = StubTestOpp(client)
        result = stub.check_test_opportunity()
        assert result is None

    def test_none_when_wellness_api_fails(self):
        """None when wellness API raises exception."""
        client = MagicMock()
        client.get_wellness.side_effect = Exception("API error")
        stub = StubTestOpp(client)
        result = stub.check_test_opportunity()
        assert result is None


class TestMonitorCTLProgressionVsPeaks:
    """Tests for monitor_ctl_progression_vs_peaks (basic cases)."""

    def _run_monitor(self, ctl):
        """Helper to run monitor with given CTL."""
        client = MagicMock()
        client.get_wellness.return_value = [{"ctl": ctl, "atl": 50, "tsb": 5}]

        mock_profile = MagicMock()
        mock_profile.ftp = 220
        mock_profile.ftp_target = 260
        mock_profile.age = 54

        mock_phase_rec = MagicMock()
        mock_phase_rec.phase.value = "base"
        mock_phase_rec.weekly_tss_load = 300
        mock_phase_rec.weekly_tss_recovery = 200

        stub = StubTestOpp(client)
        # Patch lazy imports at their source modules
        with (
            patch("magma_cycling.config.athlete_profile.AthleteProfile") as mock_profile_class,
            patch("magma_cycling.planning.peaks_phases.determine_training_phase") as mock_phase,
        ):
            mock_profile_class.from_env.return_value = mock_profile
            mock_phase.return_value = mock_phase_rec
            return stub.monitor_ctl_progression_vs_peaks()

    def test_critical_status_low_ctl(self):
        """CTL < 50 returns CRITICAL status."""
        result = self._run_monitor(40)
        assert result is not None
        assert result["status"] == "CRITICAL"

    def test_optimal_status_high_ctl(self):
        """High CTL returns OPTIMAL status."""
        result = self._run_monitor(75)
        assert result is not None
        assert result["status"] == "OPTIMAL"

    def test_returns_none_on_error(self):
        """Returns None when API fails."""
        client = MagicMock()
        client.get_wellness.side_effect = Exception("fail")
        stub = StubTestOpp(client)
        result = stub.monitor_ctl_progression_vs_peaks()
        assert result is None

    def test_returns_none_no_wellness(self):
        """Returns None when no wellness data."""
        client = MagicMock()
        client.get_wellness.return_value = []
        stub = StubTestOpp(client)
        result = stub.monitor_ctl_progression_vs_peaks()
        assert result is None
