"""Tests for PIDCorrectionMixin."""

from unittest.mock import MagicMock, patch

from magma_cycling.intelligence.training_intelligence import TrainingIntelligence
from magma_cycling.workflows.pid_eval.pid_correction import PIDCorrectionMixin


class StubPID(PIDCorrectionMixin):
    """Stub class to test PIDCorrectionMixin."""

    def __init__(self):
        """Initialize stub with fresh TrainingIntelligence."""
        self.intelligence = TrainingIntelligence()


def _make_metrics():
    return {
        "adherence_rate": 0.90,
        "avg_cardiovascular_coupling": 0.06,
        "tss_completion_rate": 0.92,
    }


class TestEvaluatePIDCorrection:
    """Tests for evaluate_pid_correction."""

    @patch("magma_cycling.workflows.pid_eval.pid_correction.DiscretePIDController")
    @patch(
        "magma_cycling.workflows.pid_eval.pid_correction"
        ".compute_discrete_pid_gains_from_intelligence"
    )
    def test_returns_expected_keys(self, mock_gains, mock_controller_class):
        """Result dict contains expected keys."""
        mock_gains.return_value = {"kp": 0.1, "ki": 0.01, "kd": 0.02}
        mock_instance = MagicMock()
        mock_instance.compute_cycle_correction_enhanced.return_value = {
            "error": -10.0,
            "tss_per_week_adjusted": 320,
            "validation": {"validated": True, "confidence": "HIGH", "red_flags": []},
            "recommendation": "Increase TSS slightly",
        }
        mock_controller_class.return_value = mock_instance

        stub = StubPID()
        result = stub.evaluate_pid_correction(210.0, 6, _make_metrics())

        assert "error" in result
        assert "tss_per_week_adjusted" in result
        assert "validation" in result
        assert "recommendation" in result

    @patch("magma_cycling.workflows.pid_eval.pid_correction.DiscretePIDController")
    @patch(
        "magma_cycling.workflows.pid_eval.pid_correction"
        ".compute_discrete_pid_gains_from_intelligence"
    )
    def test_uses_adaptive_gains(self, mock_gains, mock_controller_class):
        """Controller created with adaptive gains from intelligence."""
        mock_gains.return_value = {"kp": 0.15, "ki": 0.02, "kd": 0.03}
        mock_instance = MagicMock()
        mock_instance.compute_cycle_correction_enhanced.return_value = {
            "error": 0,
            "tss_per_week_adjusted": 300,
            "validation": {"validated": True, "confidence": "HIGH", "red_flags": []},
            "recommendation": "Maintain",
        }
        mock_controller_class.return_value = mock_instance

        stub = StubPID()
        stub.evaluate_pid_correction(220.0, 6, _make_metrics())

        mock_controller_class.assert_called_once()
        call_kwargs = mock_controller_class.call_args[1]
        assert call_kwargs["kp"] == 0.15
        assert call_kwargs["ki"] == 0.02

    @patch("magma_cycling.workflows.pid_eval.pid_correction.DiscretePIDController")
    @patch(
        "magma_cycling.workflows.pid_eval.pid_correction"
        ".compute_discrete_pid_gains_from_intelligence"
    )
    def test_passes_metrics_to_correction(self, mock_gains, mock_controller_class):
        """Metrics forwarded to compute_cycle_correction_enhanced."""
        mock_gains.return_value = {"kp": 0.1, "ki": 0.01, "kd": 0.02}
        mock_instance = MagicMock()
        mock_instance.compute_cycle_correction_enhanced.return_value = {
            "error": 0,
            "tss_per_week_adjusted": 300,
            "validation": {"validated": True, "confidence": "HIGH", "red_flags": []},
            "recommendation": "OK",
        }
        mock_controller_class.return_value = mock_instance

        metrics = _make_metrics()
        stub = StubPID()
        stub.evaluate_pid_correction(220.0, 6, metrics)

        call_kwargs = mock_instance.compute_cycle_correction_enhanced.call_args[1]
        assert call_kwargs["adherence_rate"] == 0.90
        assert call_kwargs["measured_ftp"] == 220.0

    @patch("magma_cycling.workflows.pid_eval.pid_correction.DiscretePIDController")
    @patch(
        "magma_cycling.workflows.pid_eval.pid_correction"
        ".compute_discrete_pid_gains_from_intelligence"
    )
    def test_fallback_setpoint_when_no_profile(self, mock_gains, mock_controller_class):
        """When AthleteProfile fails, setpoint falls back to measured_ftp."""
        mock_gains.return_value = {"kp": 0.1, "ki": 0.01, "kd": 0.02}
        mock_instance = MagicMock()
        mock_instance.compute_cycle_correction_enhanced.return_value = {
            "error": 0,
            "tss_per_week_adjusted": 300,
            "validation": {"validated": True, "confidence": "HIGH", "red_flags": []},
            "recommendation": "OK",
        }
        mock_controller_class.return_value = mock_instance

        stub = StubPID()
        # AthleteProfile is imported lazily inside the method via
        # "from magma_cycling.config import AthleteProfile"
        # so we patch at the source module
        with patch(
            "magma_cycling.config.AthleteProfile",
        ) as mock_ap:
            mock_ap.from_env.side_effect = Exception("no env")
            stub.evaluate_pid_correction(215.0, 6, _make_metrics())

        call_kwargs = mock_controller_class.call_args[1]
        assert call_kwargs["setpoint"] == 215.0

    @patch("magma_cycling.workflows.pid_eval.pid_correction.DiscretePIDController")
    @patch(
        "magma_cycling.workflows.pid_eval.pid_correction"
        ".compute_discrete_pid_gains_from_intelligence"
    )
    def test_red_flags_printed(self, mock_gains, mock_controller_class, capsys):
        """Red flags from validation are printed."""
        mock_gains.return_value = {"kp": 0.1, "ki": 0.01, "kd": 0.02}
        mock_instance = MagicMock()
        mock_instance.compute_cycle_correction_enhanced.return_value = {
            "error": -50.0,
            "tss_per_week_adjusted": 400,
            "validation": {
                "validated": False,
                "confidence": "LOW",
                "red_flags": ["FTP drop too large"],
            },
            "recommendation": "Investigate",
        }
        mock_controller_class.return_value = mock_instance

        stub = StubPID()
        stub.evaluate_pid_correction(180.0, 6, _make_metrics())

        captured = capsys.readouterr()
        assert "Red Flags" in captured.out
        assert "FTP drop too large" in captured.out
