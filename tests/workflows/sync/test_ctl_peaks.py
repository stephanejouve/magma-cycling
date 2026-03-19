"""Tests for CTLPeaksMixin — CTL/ATL/TSB analysis using Peaks Coaching principles."""

import json
from datetime import date
from unittest.mock import MagicMock, patch

from magma_cycling.workflows.sync.ctl_peaks import CTLPeaksMixin


class StubSync(CTLPeaksMixin):
    """Stub class to test CTLPeaksMixin in isolation."""

    def __init__(self, client=None):
        self.client = client or MagicMock()


def _make_wellness(ctl=45.0, atl=50.0, tsb=-5.0):
    """Helper to create wellness data dict."""
    return {"ctl": ctl, "atl": atl, "tsb": tsb}


def _mock_athlete_profile(ftp=220, ftp_target=260):
    """Helper to create a mock AthleteProfile."""
    profile = MagicMock()
    profile.ftp = ftp
    profile.ftp_target = ftp_target
    return profile


class TestNoWellnessData:
    """Tests for early returns when wellness data is missing."""

    @patch("magma_cycling.workflows.sync.ctl_peaks.AthleteProfile.from_env")
    def test_no_wellness_data_returns_none(self, mock_profile):
        """Return None when get_wellness returns empty list."""
        mock_profile.return_value = _mock_athlete_profile()
        mock_client = MagicMock()
        mock_client.get_wellness.return_value = []

        stub = StubSync(client=mock_client)
        result = stub.analyze_ctl_peaks(check_date=date(2026, 3, 10))

        assert result is None

    @patch("magma_cycling.workflows.sync.ctl_peaks.AthleteProfile.from_env")
    def test_empty_wellness_list_returns_none(self, mock_profile):
        """Return None when wellness list has None last element (safety check)."""
        mock_profile.return_value = _mock_athlete_profile()
        mock_client = MagicMock()
        # List is non-empty but last element is None (edge case)
        mock_client.get_wellness.return_value = [None]

        stub = StubSync(client=mock_client)
        result = stub.analyze_ctl_peaks(check_date=date(2026, 3, 10))

        assert result is None


class TestBasicAnalysis:
    """Tests for basic CTL/ATL/TSB analysis without PID integration issues."""

    @patch("magma_cycling.workflows.sync.ctl_peaks.compute_integrated_correction")
    @patch("magma_cycling.workflows.sync.ctl_peaks.determine_training_phase")
    @patch("magma_cycling.workflows.sync.ctl_peaks.AthleteProfile.from_env")
    def test_basic_analysis_returns_dict(self, mock_profile, mock_phase, mock_pid):
        """Verify result dict structure with all expected keys."""
        mock_profile.return_value = _mock_athlete_profile(ftp=220, ftp_target=260)
        mock_phase.return_value = MagicMock(ctl_target=75.0, weeks_to_rebuild=12)
        mock_pid.return_value = MagicMock(
            tss_per_week=380,
            mode=MagicMock(value="pid_constrained"),
            confidence="medium",
            override_active=False,
            pid_delta=10,
            peaks_suggestion=370,
        )

        mock_client = MagicMock()
        mock_client.get_wellness.return_value = [_make_wellness(ctl=55.0, atl=60.0, tsb=-5.0)]

        stub = StubSync(client=mock_client)
        result = stub.analyze_ctl_peaks(check_date=date(2026, 3, 10))

        assert result is not None
        assert result["ctl_current"] == 55.0
        assert result["atl_current"] == 60.0
        assert result["tsb_current"] == -5.0
        assert result["ftp_current"] == 220
        assert result["ftp_target"] == 260
        assert "ctl_minimum_for_ftp" in result
        assert "ctl_optimal_for_ftp" in result
        assert "alerts" in result
        assert "recommendations" in result
        assert "phase_recommendation" in result
        assert "pid_peaks_recommendation" in result

    @patch("magma_cycling.workflows.sync.ctl_peaks.compute_integrated_correction")
    @patch("magma_cycling.workflows.sync.ctl_peaks.determine_training_phase")
    @patch("magma_cycling.workflows.sync.ctl_peaks.AthleteProfile.from_env")
    def test_training_phase_included(self, mock_profile, mock_phase, mock_pid):
        """Verify phase_recommendation is included in result."""
        mock_profile.return_value = _mock_athlete_profile(ftp=220, ftp_target=260)
        phase_rec = MagicMock(ctl_target=75.0, weeks_to_rebuild=12)
        mock_phase.return_value = phase_rec
        mock_pid.return_value = MagicMock(
            tss_per_week=380,
            mode=MagicMock(value="pid_constrained"),
            confidence="medium",
            override_active=False,
            pid_delta=10,
            peaks_suggestion=370,
        )

        mock_client = MagicMock()
        mock_client.get_wellness.return_value = [_make_wellness(ctl=60.0)]

        stub = StubSync(client=mock_client)
        result = stub.analyze_ctl_peaks(check_date=date(2026, 3, 10))

        assert result["phase_recommendation"] is phase_rec

    @patch("magma_cycling.workflows.sync.ctl_peaks.compute_integrated_correction")
    @patch("magma_cycling.workflows.sync.ctl_peaks.determine_training_phase")
    @patch("magma_cycling.workflows.sync.ctl_peaks.AthleteProfile.from_env")
    def test_ctl_below_minimum_generates_alerts(self, mock_profile, mock_phase, mock_pid):
        """CTL below minimum for FTP should generate alerts and recommendations."""
        mock_profile.return_value = _mock_athlete_profile(ftp=220, ftp_target=260)
        mock_phase.return_value = MagicMock(ctl_target=75.0, weeks_to_rebuild=12)
        mock_pid.return_value = MagicMock(
            tss_per_week=370,
            mode=MagicMock(value="peaks_override"),
            confidence="high",
            override_active=True,
            pid_delta=None,
            peaks_suggestion=370,
        )

        # CTL minimum for FTP 220 = (220/220)*55 = 55
        # Set CTL well below minimum
        mock_client = MagicMock()
        mock_client.get_wellness.return_value = [_make_wellness(ctl=40.0)]

        stub = StubSync(client=mock_client)
        result = stub.analyze_ctl_peaks(check_date=date(2026, 3, 10))

        assert len(result["alerts"]) > 0
        assert any("CTL critique" in a for a in result["alerts"])
        assert len(result["recommendations"]) > 0

    @patch("magma_cycling.workflows.sync.ctl_peaks.compute_integrated_correction")
    @patch("magma_cycling.workflows.sync.ctl_peaks.determine_training_phase")
    @patch("magma_cycling.workflows.sync.ctl_peaks.AthleteProfile.from_env")
    def test_negative_tsb_generates_recovery_alert(self, mock_profile, mock_phase, mock_pid):
        """TSB < -15 should trigger fatigue alert."""
        mock_profile.return_value = _mock_athlete_profile(ftp=220, ftp_target=260)
        mock_phase.return_value = MagicMock(ctl_target=75.0, weeks_to_rebuild=12)
        mock_pid.return_value = MagicMock(
            tss_per_week=350,
            mode=MagicMock(value="pid_constrained"),
            confidence="medium",
            override_active=False,
            pid_delta=5,
            peaks_suggestion=345,
        )

        mock_client = MagicMock()
        mock_client.get_wellness.return_value = [_make_wellness(ctl=70.0, atl=90.0, tsb=-20.0)]

        stub = StubSync(client=mock_client)
        result = stub.analyze_ctl_peaks(check_date=date(2026, 3, 10))

        assert any("TSB critique" in a for a in result["alerts"])
        assert any("récupération" in r for r in result["recommendations"])

    @patch("magma_cycling.workflows.sync.ctl_peaks.compute_integrated_correction")
    @patch("magma_cycling.workflows.sync.ctl_peaks.determine_training_phase")
    @patch("magma_cycling.workflows.sync.ctl_peaks.AthleteProfile.from_env")
    def test_high_tsb_generates_deconditioning_alert(self, mock_profile, mock_phase, mock_pid):
        """TSB > +15 should trigger deconditioning alert."""
        mock_profile.return_value = _mock_athlete_profile(ftp=220, ftp_target=260)
        mock_phase.return_value = MagicMock(ctl_target=75.0, weeks_to_rebuild=12)
        mock_pid.return_value = MagicMock(
            tss_per_week=400,
            mode=MagicMock(value="pid_constrained"),
            confidence="medium",
            override_active=False,
            pid_delta=10,
            peaks_suggestion=390,
        )

        mock_client = MagicMock()
        mock_client.get_wellness.return_value = [_make_wellness(ctl=55.0, atl=35.0, tsb=20.0)]

        stub = StubSync(client=mock_client)
        result = stub.analyze_ctl_peaks(check_date=date(2026, 3, 10))

        assert any("TSB élevé" in a for a in result["alerts"])
        assert any("Augmenter" in r for r in result["recommendations"])

    @patch("magma_cycling.workflows.sync.ctl_peaks.compute_integrated_correction")
    @patch("magma_cycling.workflows.sync.ctl_peaks.determine_training_phase")
    @patch("magma_cycling.workflows.sync.ctl_peaks.AthleteProfile.from_env")
    def test_suboptimal_ctl_alert(self, mock_profile, mock_phase, mock_pid):
        """CTL between minimum and 85% of target generates suboptimal alert."""
        mock_profile.return_value = _mock_athlete_profile(ftp=220, ftp_target=260)
        # ctl_target = 75, 85% = 63.75
        # ctl_minimum = (220/220)*55 = 55
        # Set CTL at 58 → above minimum (55), below 85% of target (63.75)
        mock_phase.return_value = MagicMock(ctl_target=75.0, weeks_to_rebuild=12)
        mock_pid.return_value = MagicMock(
            tss_per_week=370,
            mode=MagicMock(value="pid_constrained"),
            confidence="medium",
            override_active=False,
            pid_delta=5,
            peaks_suggestion=365,
        )

        mock_client = MagicMock()
        mock_client.get_wellness.return_value = [_make_wellness(ctl=58.0, tsb=0.0)]

        stub = StubSync(client=mock_client)
        result = stub.analyze_ctl_peaks(check_date=date(2026, 3, 10))

        assert any("sous-optimal" in a for a in result["alerts"])


class TestPIDState:
    """Tests for PID state file loading."""

    @patch("magma_cycling.workflows.sync.ctl_peaks.compute_integrated_correction")
    @patch("magma_cycling.workflows.sync.ctl_peaks.determine_training_phase")
    @patch("magma_cycling.workflows.sync.ctl_peaks.AthleteProfile.from_env")
    def test_pid_state_file_not_found(self, mock_profile, mock_phase, mock_pid, tmp_path):
        """Analysis succeeds when PID state file does not exist."""
        mock_profile.return_value = _mock_athlete_profile()
        mock_phase.return_value = MagicMock(ctl_target=75.0, weeks_to_rebuild=12)
        mock_pid.return_value = MagicMock(
            tss_per_week=380,
            mode=MagicMock(value="pid_constrained"),
            confidence="medium",
            override_active=False,
            pid_delta=10,
            peaks_suggestion=370,
        )

        mock_client = MagicMock()
        mock_client.get_wellness.return_value = [_make_wellness(ctl=60.0)]

        stub = StubSync(client=mock_client)
        # Use a non-existent path for PID state
        with patch(
            "magma_cycling.workflows.sync.ctl_peaks.Path",
            wraps=type(tmp_path / "nonexistent"),
        ):
            result = stub.analyze_ctl_peaks(check_date=date(2026, 3, 10))

        assert result is not None

    @patch("magma_cycling.workflows.sync.ctl_peaks.compute_integrated_correction")
    @patch("magma_cycling.workflows.sync.ctl_peaks.determine_training_phase")
    @patch("magma_cycling.workflows.sync.ctl_peaks.AthleteProfile.from_env")
    def test_pid_state_file_loaded(self, mock_profile, mock_phase, mock_pid, tmp_path):
        """PID state is restored from JSON file when it exists."""
        mock_profile.return_value = _mock_athlete_profile()
        mock_phase.return_value = MagicMock(ctl_target=75.0, weeks_to_rebuild=12)
        mock_pid.return_value = MagicMock(
            tss_per_week=380,
            mode=MagicMock(value="pid_constrained"),
            confidence="medium",
            override_active=False,
            pid_delta=10,
            peaks_suggestion=370,
        )

        # Create state file
        state_file = tmp_path / "sprint_r10_pid_initialization.json"
        state_data = {
            "pid_state": {
                "integral": 1.5,
                "prev_error": 20.0,
                "prev_ftp": 210,
                "cycle_count": 3,
            }
        }
        state_file.write_text(json.dumps(state_data))

        mock_client = MagicMock()
        mock_client.get_wellness.return_value = [_make_wellness(ctl=60.0)]

        stub = StubSync(client=mock_client)
        with patch(
            "magma_cycling.workflows.sync.ctl_peaks.Path",
            return_value=state_file,
        ):
            result = stub.analyze_ctl_peaks(check_date=date(2026, 3, 10))

        assert result is not None

    @patch("magma_cycling.workflows.sync.ctl_peaks.compute_integrated_correction")
    @patch("magma_cycling.workflows.sync.ctl_peaks.determine_training_phase")
    @patch("magma_cycling.workflows.sync.ctl_peaks.AthleteProfile.from_env")
    def test_pid_state_corrupt_json(self, mock_profile, mock_phase, mock_pid, tmp_path):
        """Corrupt PID state file is handled gracefully."""
        mock_profile.return_value = _mock_athlete_profile()
        mock_phase.return_value = MagicMock(ctl_target=75.0, weeks_to_rebuild=12)
        mock_pid.return_value = MagicMock(
            tss_per_week=380,
            mode=MagicMock(value="pid_constrained"),
            confidence="medium",
            override_active=False,
            pid_delta=10,
            peaks_suggestion=370,
        )

        # Create corrupt state file
        state_file = tmp_path / "sprint_r10_pid_initialization.json"
        state_file.write_text("{invalid json")

        mock_client = MagicMock()
        mock_client.get_wellness.return_value = [_make_wellness(ctl=60.0)]

        stub = StubSync(client=mock_client)
        with patch(
            "magma_cycling.workflows.sync.ctl_peaks.Path",
            return_value=state_file,
        ):
            result = stub.analyze_ctl_peaks(check_date=date(2026, 3, 10))

        assert result is not None


class TestPIDIntegration:
    """Tests for PID + Peaks integrated recommendation."""

    @patch("magma_cycling.workflows.sync.ctl_peaks.compute_integrated_correction")
    @patch("magma_cycling.workflows.sync.ctl_peaks.determine_training_phase")
    @patch("magma_cycling.workflows.sync.ctl_peaks.AthleteProfile.from_env")
    def test_integrated_correction_success(self, mock_profile, mock_phase, mock_pid):
        """Successful PID+Peaks integration returns recommendation in result."""
        mock_profile.return_value = _mock_athlete_profile()
        mock_phase.return_value = MagicMock(ctl_target=75.0, weeks_to_rebuild=12)
        pid_rec = MagicMock(
            tss_per_week=380,
            mode=MagicMock(value="pid_constrained"),
            confidence="high",
            override_active=False,
            pid_delta=15,
            peaks_suggestion=365,
        )
        mock_pid.return_value = pid_rec

        mock_client = MagicMock()
        mock_client.get_wellness.return_value = [_make_wellness(ctl=60.0)]

        stub = StubSync(client=mock_client)
        result = stub.analyze_ctl_peaks(check_date=date(2026, 3, 10))

        assert result["pid_peaks_recommendation"] is pid_rec

    @patch("magma_cycling.workflows.sync.ctl_peaks.compute_integrated_correction")
    @patch("magma_cycling.workflows.sync.ctl_peaks.determine_training_phase")
    @patch("magma_cycling.workflows.sync.ctl_peaks.AthleteProfile.from_env")
    def test_integrated_correction_exception(self, mock_profile, mock_phase, mock_pid):
        """Exception in compute_integrated_correction sets pid_peaks_recommendation to None."""
        mock_profile.return_value = _mock_athlete_profile()
        mock_phase.return_value = MagicMock(ctl_target=75.0, weeks_to_rebuild=12)
        mock_pid.side_effect = RuntimeError("PID computation failed")

        mock_client = MagicMock()
        mock_client.get_wellness.return_value = [_make_wellness(ctl=60.0)]

        stub = StubSync(client=mock_client)
        result = stub.analyze_ctl_peaks(check_date=date(2026, 3, 10))

        assert result is not None
        assert result["pid_peaks_recommendation"] is None


class TestExceptionHandling:
    """Tests for top-level exception handling."""

    @patch("magma_cycling.workflows.sync.ctl_peaks.AthleteProfile.from_env")
    def test_athlete_profile_error_returns_none(self, mock_profile):
        """Return None when AthleteProfile.from_env() raises."""
        mock_profile.side_effect = RuntimeError("Missing env vars")

        stub = StubSync(client=MagicMock())
        result = stub.analyze_ctl_peaks(check_date=date(2026, 3, 10))

        assert result is None
