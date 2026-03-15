"""Integration tests for PIDDailyEvaluator facade."""

from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.scripts.pid_daily_evaluation import PIDDailyEvaluator


@pytest.fixture()
def evaluator(tmp_path):
    """Create evaluator with mocked API and temp paths."""
    with patch("magma_cycling.scripts.pid_daily_evaluation.get_intervals_config") as mock_config:
        mock_config.return_value = MagicMock(athlete_id="i123", api_key="key")
        with patch("magma_cycling.scripts.pid_daily_evaluation.IntervalsClient"):
            ev = PIDDailyEvaluator(
                adherence_file=tmp_path / "adherence.jsonl",
                workouts_history=tmp_path / "reports",
                evaluation_log=tmp_path / "eval.jsonl",
                intelligence_file=tmp_path / "intelligence.json",
                dry_run=True,
            )
    return ev


class TestPIDDailyEvaluatorInit:
    """Tests for PIDDailyEvaluator initialization."""

    def test_creates_new_intelligence(self, evaluator):
        """Fresh evaluator has empty intelligence."""
        assert len(evaluator.intelligence.learnings) == 0
        assert len(evaluator.intelligence.patterns) == 0

    def test_dry_run_flag(self, evaluator):
        """Dry-run flag is stored."""
        assert evaluator.dry_run is True

    def test_has_all_mixin_methods(self, evaluator):
        """Evaluator exposes all mixin methods."""
        assert hasattr(evaluator, "load_adherence_data")
        assert hasattr(evaluator, "extract_cardiovascular_coupling")
        assert hasattr(evaluator, "calculate_tss_completion")
        assert hasattr(evaluator, "calculate_cycle_metrics")
        assert hasattr(evaluator, "create_intelligence_learnings")
        assert hasattr(evaluator, "evaluate_pid_correction")
        assert hasattr(evaluator, "check_test_opportunity")
        assert hasattr(evaluator, "monitor_ctl_progression_vs_peaks")
        assert hasattr(evaluator, "log_evaluation")
        assert hasattr(evaluator, "save_intelligence")


class TestRunDailyEvaluation:
    """Tests for run_daily_evaluation facade."""

    def test_daily_returns_success(self, evaluator):
        """Daily evaluation returns SUCCESS status."""
        evaluator.client.get_events.return_value = []
        evaluator.client.get_activities.return_value = []
        evaluator.client.get_wellness.return_value = []

        # Mock adherence file with no data
        evaluator.adherence_file.parent.mkdir(parents=True, exist_ok=True)
        evaluator.adherence_file.write_text("")

        result = evaluator.run_daily_evaluation(days_back=7)

        assert result["status"] == "SUCCESS"
        assert "metrics" in result
        assert "test_recommendation" in result
        assert "ctl_monitoring" in result

    def test_daily_metrics_structure(self, evaluator):
        """Daily evaluation produces expected metrics keys."""
        evaluator.client.get_events.return_value = []
        evaluator.client.get_activities.return_value = []
        evaluator.client.get_wellness.return_value = []
        evaluator.adherence_file.parent.mkdir(parents=True, exist_ok=True)
        evaluator.adherence_file.write_text("")

        result = evaluator.run_daily_evaluation(days_back=7)
        metrics = result["metrics"]

        assert "adherence_rate" in metrics
        assert "avg_cardiovascular_coupling" in metrics
        assert "tss_completion_rate" in metrics


class TestRunCycleEvaluation:
    """Tests for run_cycle_evaluation facade."""

    @patch("magma_cycling.workflows.pid_eval.pid_correction.DiscretePIDController")
    @patch(
        "magma_cycling.workflows.pid_eval.pid_correction"
        ".compute_discrete_pid_gains_from_intelligence"
    )
    def test_cycle_returns_success(self, mock_gains, mock_controller, evaluator):
        """Cycle evaluation returns SUCCESS status."""
        mock_gains.return_value = {"kp": 0.1, "ki": 0.01, "kd": 0.02}
        mock_instance = MagicMock()
        mock_instance.compute_cycle_correction_enhanced.return_value = {
            "error": -5.0,
            "tss_per_week_adjusted": 310,
            "validation": {"validated": True, "confidence": "HIGH", "red_flags": []},
            "recommendation": "Slight increase",
        }
        mock_controller.return_value = mock_instance

        evaluator.client.get_events.return_value = []
        evaluator.client.get_activities.return_value = []
        evaluator.client.get_wellness.return_value = []
        evaluator.adherence_file.parent.mkdir(parents=True, exist_ok=True)
        evaluator.adherence_file.write_text("")

        result = evaluator.run_cycle_evaluation(measured_ftp=210.0, cycle_duration_weeks=6)

        assert result["status"] == "SUCCESS"
        assert "pid_correction" in result
        assert result["pid_correction"]["tss_per_week_adjusted"] == 310

    @patch("magma_cycling.workflows.pid_eval.pid_correction.DiscretePIDController")
    @patch(
        "magma_cycling.workflows.pid_eval.pid_correction"
        ".compute_discrete_pid_gains_from_intelligence"
    )
    def test_cycle_creates_learnings(self, mock_gains, mock_controller, evaluator):
        """Cycle evaluation creates intelligence learnings."""
        mock_gains.return_value = {"kp": 0.1, "ki": 0.01, "kd": 0.02}
        mock_instance = MagicMock()
        mock_instance.compute_cycle_correction_enhanced.return_value = {
            "error": 0,
            "tss_per_week_adjusted": 300,
            "validation": {"validated": True, "confidence": "HIGH", "red_flags": []},
            "recommendation": "Maintain",
        }
        mock_controller.return_value = mock_instance

        evaluator.client.get_events.return_value = []
        evaluator.client.get_activities.return_value = []
        evaluator.client.get_wellness.return_value = []
        evaluator.adherence_file.parent.mkdir(parents=True, exist_ok=True)
        evaluator.adherence_file.write_text("")

        evaluator.run_cycle_evaluation(measured_ftp=220.0)

        assert len(evaluator.intelligence.learnings) == 3


class TestMainCLI:
    """Tests for main() CLI entry point."""

    @patch("magma_cycling.scripts.pid_daily_evaluation.PIDDailyEvaluator")
    def test_cycle_complete_without_ftp_returns_error(self, mock_evaluator, capsys):
        """--cycle-complete without --measured-ftp prints error."""
        from magma_cycling.scripts.pid_daily_evaluation import main

        with patch("sys.argv", ["pid-daily-evaluation", "--cycle-complete"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
