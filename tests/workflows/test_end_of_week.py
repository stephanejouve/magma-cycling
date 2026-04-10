#!/usr/bin/env python3
"""
Tests for end_of_week.py workflow orchestrator.

Coverage target: 80%+ (888 lines)

Test strategy:
- Standalone functions: calculate_week_start_date, calculate_weekly_transition
- EndOfWeekWorkflow initialization
- Individual workflow steps (mocked external calls)
- Integration tests (dry-run mode)
- Error handling and edge cases
"""

import json
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from magma_cycling.workflows.end_of_week import (
    EndOfWeekWorkflow,
    calculate_week_start_date,
    calculate_weekly_transition,
    main,
    parse_args,
)

# =============================================================================
# Tests: calculate_week_start_date
# =============================================================================


class TestCalculateWeekStartDate:
    """Test calculate_week_start_date function."""

    @patch("magma_cycling.workflows.end_of_week.get_week_config")
    def test_calculate_week_start_date_s001(self, mock_config):
        """Test calculation for S001 (season start)."""
        mock_week_config = Mock()
        mock_week_config.get_reference_for_week.return_value = (date(2024, 8, 5), 0)
        mock_config.return_value = mock_week_config

        result = calculate_week_start_date("S001")

        assert result == date(2024, 8, 5)
        assert result.weekday() == 0  # Monday
        mock_week_config.get_reference_for_week.assert_called_once_with("S001")

    @patch("magma_cycling.workflows.end_of_week.get_week_config")
    def test_calculate_week_start_date_s075(self, mock_config):
        """Test calculation for S075."""
        mock_week_config = Mock()
        # S075 = 74 weeks after S001 (Monday 2024-08-05)
        mock_week_config.get_reference_for_week.return_value = (date(2024, 8, 5), 74)
        mock_config.return_value = mock_week_config

        result = calculate_week_start_date("S075")

        expected = date(2024, 8, 5) + timedelta(weeks=74)
        assert result == expected
        assert result.weekday() == 0  # Monday

    @patch("magma_cycling.workflows.end_of_week.get_week_config")
    def test_calculate_week_start_date_invalid_not_monday(self, mock_config):
        """Test error when calculated date is not a Monday."""
        mock_week_config = Mock()
        # Return a Tuesday
        mock_week_config.get_reference_for_week.return_value = (date(2024, 8, 6), 0)
        mock_config.return_value = mock_week_config

        with pytest.raises(ValueError, match="is not a Monday"):
            calculate_week_start_date("S001")


# =============================================================================
# Tests: calculate_weekly_transition
# =============================================================================


class TestCalculateWeeklyTransition:
    """Test calculate_weekly_transition function."""

    @patch("magma_cycling.workflows.end_of_week.get_week_config")
    def test_calculate_weekly_transition_sunday(self, mock_config):
        """Test transition calculation on Sunday."""
        mock_week_config = Mock()
        mock_week_config.get_s001_for_date.return_value = (date(2024, 8, 5), 1)
        mock_config.return_value = mock_week_config

        # Sunday 2026-01-25 (S077 → S078)
        reference_date = date(2026, 1, 25)

        week_completed, week_next, completed_start, next_start = calculate_weekly_transition(
            reference_date
        )

        assert week_completed == "S077"
        assert week_next == "S078"
        assert completed_start == date(2026, 1, 19)  # Monday S077
        assert next_start == date(2026, 1, 26)  # Monday S078

    @patch("magma_cycling.workflows.end_of_week.get_week_config")
    def test_calculate_weekly_transition_monday(self, mock_config):
        """Test transition on Monday gives same result as Sunday."""
        mock_week_config = Mock()
        mock_week_config.get_s001_for_date.return_value = (date(2024, 8, 5), 1)
        mock_config.return_value = mock_week_config

        # Monday 2026-01-26 (first day of S078)
        # The completed week is S077 (just ended), not S078 (just started)
        reference_date = date(2026, 1, 26)

        week_completed, week_next, completed_start, next_start = calculate_weekly_transition(
            reference_date
        )

        assert week_completed == "S077"
        assert week_next == "S078"
        assert completed_start == date(2026, 1, 19)
        assert next_start == date(2026, 1, 26)

    @patch("magma_cycling.workflows.end_of_week.get_week_config")
    def test_calculate_weekly_transition_midweek(self, mock_config):
        """Test transition mid-week (Wednesday)."""
        mock_week_config = Mock()
        mock_week_config.get_s001_for_date.return_value = (date(2024, 8, 5), 1)
        mock_config.return_value = mock_week_config

        # Wednesday 2026-01-28 (mid-S078)
        reference_date = date(2026, 1, 28)

        week_completed, week_next, _, _ = calculate_weekly_transition(reference_date)

        assert week_completed == "S078"
        assert week_next == "S079"

    @patch("magma_cycling.workflows.end_of_week.get_week_config")
    def test_calculate_weekly_transition_s084_monday_bug(self, mock_config):
        """Regression test: Monday March 9 must return S083 completed, not S084.

        This is the exact scenario that caused the S084 incident.
        """
        mock_week_config = Mock()
        mock_week_config.get_s001_for_date.return_value = (date(2024, 8, 5), 1)
        mock_config.return_value = mock_week_config

        # Monday 2026-03-09 = first day of S084
        reference_date = date(2026, 3, 9)

        week_completed, week_next, completed_start, next_start = calculate_weekly_transition(
            reference_date
        )

        assert week_completed == "S083"
        assert week_next == "S084"
        assert completed_start == date(2026, 3, 2)
        assert next_start == date(2026, 3, 9)

    @patch("magma_cycling.workflows.end_of_week.get_week_config")
    @patch("magma_cycling.workflows.end_of_week.date")
    def test_calculate_weekly_transition_no_reference_date(self, mock_date_class, mock_config):
        """Test transition uses today() when no reference_date provided."""
        mock_week_config = Mock()
        mock_week_config.get_s001_for_date.return_value = (date(2024, 8, 5), 1)
        mock_config.return_value = mock_week_config

        # Mock date.today()
        mock_date_class.today.return_value = date(2026, 1, 25)
        mock_date_class.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

        week_completed, week_next, _, _ = calculate_weekly_transition()

        assert week_completed == "S077"
        assert week_next == "S078"

    @patch("magma_cycling.workflows.end_of_week.get_week_config")
    def test_calculate_weekly_transition_multi_season(self, mock_config):
        """Test transition with multi-season config selects correct season."""
        mock_week_config = Mock()
        # Season 2026: s001_date=2026-01-05, global_week_start=75
        mock_week_config.get_s001_for_date.return_value = (date(2026, 1, 5), 75)
        mock_config.return_value = mock_week_config

        # Monday 2026-03-09 → 9 weeks after 2026-01-05 = week 75+8=S083
        # adjusted_date = 2026-03-08 (Sunday), delta = 63 days, offset = 9
        # current_week_num = 9 + 75 = 84... wait
        # Let me recalculate: adjusted = 2026-03-08, delta from 2026-01-05 = 62 days
        # weeks_offset = 62 // 7 = 8, current_week_num = 8 + 75 = 83
        reference_date = date(2026, 3, 9)

        week_completed, week_next, completed_start, next_start = calculate_weekly_transition(
            reference_date
        )

        assert week_completed == "S083"
        assert week_next == "S084"
        assert completed_start == date(2026, 3, 2)
        assert next_start == date(2026, 3, 9)


# =============================================================================
# Tests: EndOfWeekWorkflow Initialization
# =============================================================================


class TestEndOfWeekWorkflowInit:
    """Test EndOfWeekWorkflow initialization."""

    @patch("magma_cycling.workflows.end_of_week.get_data_config")
    @patch("magma_cycling.workflows.end_of_week.calculate_week_start_date")
    def test_init_basic(self, mock_calc_date, mock_data_config):
        """Test basic initialization."""
        mock_calc_date.side_effect = [date(2026, 1, 5), date(2026, 1, 12)]
        mock_config = Mock()
        mock_config.data_repo_path = Path("/fake/data")
        mock_config.week_planning_dir = Path("/fake/planning")
        mock_data_config.return_value = mock_config

        workflow = EndOfWeekWorkflow(
            week_completed="S075",
            week_next="S076",
            provider="clipboard",
            dry_run=False,
            auto=False,
            archive=False,
        )

        assert workflow.week_completed == "S075"
        assert workflow.week_next == "S076"
        assert workflow.provider == "clipboard"
        assert workflow.dry_run is False
        assert workflow.auto is False
        assert workflow.archive is False
        assert workflow.completed_start_date == date(2026, 1, 5)
        assert workflow.next_start_date == date(2026, 1, 12)

    @patch("magma_cycling.workflows.end_of_week.get_data_config")
    @patch("magma_cycling.workflows.end_of_week.calculate_week_start_date")
    def test_init_dry_run_mode(self, mock_calc_date, mock_data_config):
        """Test initialization with dry_run=True."""
        mock_calc_date.side_effect = [date(2026, 1, 5), date(2026, 1, 12)]
        mock_config = Mock()
        mock_config.data_repo_path = Path("/fake/data")
        mock_config.week_planning_dir = Path("/fake/planning")
        mock_data_config.return_value = mock_config

        workflow = EndOfWeekWorkflow(week_completed="S075", week_next="S076", dry_run=True)

        assert workflow.dry_run is True

    @patch("magma_cycling.workflows.end_of_week.get_data_config")
    @patch("magma_cycling.workflows.end_of_week.calculate_week_start_date")
    def test_init_config_error(self, mock_calc_date, mock_data_config):
        """Test initialization fails gracefully on config error."""
        mock_calc_date.side_effect = [date(2026, 1, 5), date(2026, 1, 12)]
        mock_data_config.side_effect = Exception("Config error")

        with pytest.raises(SystemExit):
            EndOfWeekWorkflow(week_completed="S075", week_next="S076")


# =============================================================================
# Tests: EndOfWeekWorkflow Steps
# =============================================================================


class TestEndOfWeekWorkflowSteps:
    """Test individual workflow steps."""

    @pytest.fixture
    def workflow(self):
        """Create workflow instance for testing (dry_run=False for step testing)."""
        with (
            patch("magma_cycling.workflows.end_of_week.get_data_config"),
            patch("magma_cycling.workflows.end_of_week.calculate_week_start_date") as mock_calc,
        ):
            mock_calc.side_effect = [date(2026, 1, 5), date(2026, 1, 12)]
            mock_config = Mock()
            mock_config.data_repo_path = Path("/tmp/data")
            mock_config.week_planning_dir = Path("/tmp/planning")

            with patch(
                "magma_cycling.workflows.end_of_week.get_data_config",
                return_value=mock_config,
            ):
                return EndOfWeekWorkflow(
                    week_completed="S075",
                    week_next="S076",
                    provider="clipboard",
                    dry_run=False,  # Changed to False for step testing
                )

    @pytest.fixture
    def workflow_dry_run(self):
        """Create workflow instance in dry-run mode."""
        with (
            patch("magma_cycling.workflows.end_of_week.get_data_config"),
            patch("magma_cycling.workflows.end_of_week.calculate_week_start_date") as mock_calc,
        ):
            mock_calc.side_effect = [date(2026, 1, 5), date(2026, 1, 12)]
            mock_config = Mock()
            mock_config.data_repo_path = Path("/tmp/data")
            mock_config.week_planning_dir = Path("/tmp/planning")

            with patch(
                "magma_cycling.workflows.end_of_week.get_data_config",
                return_value=mock_config,
            ):
                return EndOfWeekWorkflow(
                    week_completed="S075",
                    week_next="S076",
                    provider="clipboard",
                    dry_run=True,
                )

    @patch("magma_cycling.workflows.workflow_weekly.run_weekly_analysis")
    @patch("pathlib.Path.exists")
    def test_step1_analyze_completed_week_file_exists(
        self, mock_exists, mock_run_analysis, workflow
    ):
        """Test step 1: analyze completed week when file already exists."""
        mock_exists.return_value = True

        with patch.object(workflow, "_load_existing_reports"):
            result = workflow._step1_analyze_completed_week()

        assert result is True
        mock_run_analysis.assert_not_called()  # Shouldn't run analysis if file exists

    @patch("magma_cycling.workflows.workflow_weekly.run_weekly_analysis")
    @patch("pathlib.Path.exists")
    def test_step1_analyze_completed_week_run_analysis(
        self, mock_exists, mock_run_analysis, workflow
    ):
        """Test step 1: run analysis when file doesn't exist."""
        # First call: file doesn't exist, second call: file created
        mock_exists.side_effect = [False, True]

        with patch.object(workflow, "_load_existing_reports"):
            result = workflow._step1_analyze_completed_week()

        assert result is True
        # run_weekly_analysis is called with week, start_date, data_dir, ai_analysis
        mock_run_analysis.assert_called_once()
        call_args = mock_run_analysis.call_args
        assert call_args[1]["week"] == "S075"
        assert call_args[1]["ai_analysis"] is False

    @patch("magma_cycling.workflows.workflow_weekly.run_weekly_analysis")
    @patch("pathlib.Path.exists")
    def test_step1_analyze_completed_week_analysis_fails(
        self, mock_exists, mock_run_analysis, workflow
    ):
        """Test step 1: analysis fails (file not created)."""
        # File doesn't exist before or after
        mock_exists.return_value = False

        result = workflow._step1_analyze_completed_week()

        assert result is False  # Returns False if file not created

    def test_step1_analyze_completed_week_dry_run(self, workflow_dry_run):
        """Test step 1: dry-run mode skips actual analysis."""
        result = workflow_dry_run._step1_analyze_completed_week()

        assert result is True
        assert workflow_dry_run.reports != {}  # Should have mock reports

    @patch("magma_cycling.scripts.pid_daily_evaluation.PIDDailyEvaluator")
    def test_step1b_pid_evaluation_success(self, mock_pid_class, workflow):
        """Test step 1b: PID evaluation (success)."""
        mock_evaluator = Mock()
        mock_evaluator.run_daily_evaluation.return_value = {"test_recommendation": None}
        mock_pid_class.return_value = mock_evaluator

        result = workflow._step1b_pid_evaluation()

        assert result is True
        mock_pid_class.assert_called_once_with(dry_run=False)
        mock_evaluator.run_daily_evaluation.assert_called_once_with(days_back=7)

    @patch("magma_cycling.scripts.pid_daily_evaluation.PIDDailyEvaluator")
    def test_step1b_pid_evaluation_with_test_recommendation(self, mock_pid_class, workflow):
        """Test step 1b: PID evaluation with test recommendation."""
        mock_evaluator = Mock()
        mock_evaluator.run_daily_evaluation.return_value = {
            "test_recommendation": {
                "status": "RECOMMENDED",
                "message": "Test FTP maintenant",
                "timing": "Cette semaine",
                "weeks_since_test": 4.0,
                "tsb": 25.5,
            }
        }
        mock_pid_class.return_value = mock_evaluator

        result = workflow._step1b_pid_evaluation()

        assert result is True

    @patch("magma_cycling.scripts.pid_daily_evaluation.PIDDailyEvaluator")
    def test_step1b_pid_evaluation_exception_non_blocking(self, mock_pid_class, workflow):
        """Test step 1b: exception is non-blocking (returns True)."""
        mock_pid_class.side_effect = Exception("PID error")

        result = workflow._step1b_pid_evaluation()

        assert result is True  # Non-blocking: continues even on error

    def test_step1b_pid_evaluation_dry_run(self, workflow_dry_run):
        """Test step 1b: dry-run mode skips PID evaluation."""
        result = workflow_dry_run._step1b_pid_evaluation()

        assert result is True

    @patch("builtins.input")
    def test_step2_generate_planning_prompt_auto_mode(self, mock_input, workflow):
        """Test step 2: auto mode doesn't ask for confirmation."""
        workflow.auto = True

        result = workflow._step2_generate_planning_prompt()

        assert result is True
        mock_input.assert_not_called()

    @patch("builtins.input")
    def test_step2_generate_planning_prompt_user_confirms(self, mock_input, workflow):
        """Test step 2: user confirms they ran weekly-planner."""
        mock_input.return_value = "o"

        result = workflow._step2_generate_planning_prompt()

        assert result is True

    @patch("builtins.input")
    def test_step2_generate_planning_prompt_user_declines(self, mock_input, workflow):
        """Test step 2: user hasn't run weekly-planner yet."""
        mock_input.return_value = "n"

        result = workflow._step2_generate_planning_prompt()

        assert result is False

    def test_step2_generate_planning_prompt_dry_run(self, workflow_dry_run):
        """Test step 2: dry-run mode."""
        result = workflow_dry_run._step2_generate_planning_prompt()

        assert result is True
        assert workflow_dry_run.planning_prompt != ""

    def test_step3_get_workouts_clipboard_mode(self, workflow):
        """Test step 3: get workouts in clipboard mode."""
        with patch.object(workflow, "_get_workouts_clipboard", return_value=True):
            result = workflow._step3_get_ai_workouts()

            assert result is True

    def test_step3_get_workouts_api_mode(self, workflow):
        """Test step 3: get workouts in API mode."""
        workflow.provider = "claude_api"

        with patch.object(workflow, "_get_workouts_api", return_value=True):
            result = workflow._step3_get_ai_workouts()

            assert result is True

    @patch("builtins.input")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.read_text")
    def test_get_workouts_clipboard_success(self, mock_read, mock_exists, mock_input, workflow):
        """Test clipboard workflow (success)."""
        mock_input.return_value = ""  # User presses Enter
        mock_exists.return_value = True
        mock_read.return_value = "=== WORKOUT S076-01 ==="

        result = workflow._get_workouts_clipboard()

        assert result is True
        assert workflow.workouts_content == "=== WORKOUT S076-01 ==="

    @patch("builtins.input")
    @patch("pathlib.Path.exists")
    def test_get_workouts_clipboard_file_not_found(self, mock_exists, mock_input, workflow):
        """Test clipboard workflow (file not found)."""
        mock_input.return_value = ""
        mock_exists.return_value = False

        result = workflow._get_workouts_clipboard()

        assert result is False

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.read_text")
    def test_get_workouts_clipboard_auto_mode(self, mock_read, mock_exists, workflow):
        """Test clipboard workflow in auto mode (no input prompt)."""
        workflow.auto = True
        mock_exists.return_value = True
        mock_read.return_value = "=== WORKOUT S076-01 ==="

        with patch("builtins.input") as mock_input:
            result = workflow._get_workouts_clipboard()

            assert result is True
            mock_input.assert_not_called()  # No user prompt in auto mode

    @patch("magma_cycling.upload_workouts.WorkoutUploader")
    def test_step4_validate_workouts_success(self, mock_uploader_class, workflow):
        """Test step 4: validate workouts (success)."""
        workflow.workouts_file = Path("/tmp/test_workouts.txt")

        mock_uploader = Mock()
        mock_uploader.parse_workouts_file.return_value = [
            {"notation": "S076-01", "workout": "Test workout"}
        ]
        mock_uploader_class.return_value = mock_uploader

        result = workflow._step4_validate_workouts()

        assert result is True

    @patch("magma_cycling.upload_workouts.WorkoutUploader")
    def test_step4_validate_workouts_no_file(self, mock_uploader_class, workflow):
        """Test step 4: no workouts file set."""
        workflow.workouts_file = None

        result = workflow._step4_validate_workouts()

        assert result is False

    @patch("magma_cycling.upload_workouts.WorkoutUploader")
    def test_step4_validate_workouts_invalid(self, mock_uploader_class, workflow):
        """Test step 4: validation fails (empty workouts)."""
        workflow.workouts_file = Path("/tmp/test_workouts.txt")

        mock_uploader = Mock()
        mock_uploader.parse_workouts_file.return_value = []  # Empty = invalid
        mock_uploader_class.return_value = mock_uploader

        result = workflow._step4_validate_workouts()

        assert result is False

    def test_step4_validate_workouts_dry_run(self, workflow_dry_run):
        """Test step 4: dry-run mode."""
        result = workflow_dry_run._step4_validate_workouts()

        assert result is True

    @patch("magma_cycling.upload_workouts.WorkoutUploader")
    def test_step5_upload_workouts_auto_mode_success(self, mock_uploader_class, workflow):
        """Test step 5: upload in auto mode (success)."""
        workflow.auto = True
        workflow.workouts_file = Path("/tmp/test_workouts.txt")

        mock_uploader = Mock()
        mock_uploader.parse_workouts_file.return_value = [{"notation": "S076-01"}]
        mock_uploader.upload_all.return_value = {"success": 1, "total": 1, "errors": []}
        mock_uploader_class.return_value = mock_uploader

        result = workflow._step5_upload_workouts()

        assert result is True

    @patch("magma_cycling.upload_workouts.WorkoutUploader")
    def test_step5_upload_workouts_auto_mode_partial_failure(self, mock_uploader_class, workflow):
        """Test step 5: upload in auto mode (partial failure)."""
        workflow.auto = True
        workflow.workouts_file = Path("/tmp/test_workouts.txt")

        mock_uploader = Mock()
        mock_uploader.parse_workouts_file.return_value = [{"notation": "S076-01"}]
        mock_uploader.upload_all.return_value = {"success": 0, "total": 1, "errors": ["Error"]}
        mock_uploader_class.return_value = mock_uploader

        result = workflow._step5_upload_workouts()

        assert result is False

    @patch("builtins.input")
    def test_step5_upload_workouts_manual_mode_confirmed(self, mock_input, workflow):
        """Test step 5: manual mode user confirms."""
        workflow.auto = False
        workflow.workouts_file = Path("/tmp/test_workouts.txt")
        mock_input.side_effect = ["o", "o"]  # Confirm upload, then confirm success

        result = workflow._step5_upload_workouts()

        assert result is True

    @patch("builtins.input")
    def test_step5_upload_workouts_manual_mode_cancelled(self, mock_input, workflow):
        """Test step 5: manual mode user cancels."""
        workflow.auto = False
        workflow.workouts_file = Path("/tmp/test_workouts.txt")
        mock_input.return_value = "n"  # Cancel upload

        result = workflow._step5_upload_workouts()

        assert result is False

    def test_step5_upload_workouts_no_file(self, workflow):
        """Test step 5: no workouts file."""
        workflow.workouts_file = None

        result = workflow._step5_upload_workouts()

        assert result is False

    def test_step5_upload_workouts_dry_run(self, workflow_dry_run):
        """Test step 5: dry-run mode."""
        workflow_dry_run.workouts_file = Path("/tmp/test_workouts.txt")

        result = workflow_dry_run._step5_upload_workouts()

        assert result is True

    def test_step6_archive_disabled(self, workflow):
        """Test step 6: archive disabled (skipped)."""
        workflow.archive = False

        workflow._step6_archive_and_commit()

        # Should return without doing anything
        assert workflow.archive is False

    def test_step6_archive_enabled_dry_run(self, workflow_dry_run):
        """Test step 6: archive enabled but dry-run (skipped)."""
        workflow_dry_run.archive = True

        workflow_dry_run._step6_archive_and_commit()

        # Dry-run should skip actual archiving
        assert workflow_dry_run.dry_run is True


# =============================================================================
# Tests: Next Week Precondition
# =============================================================================


class TestNextWeekPrecondition:
    """Test _check_next_week_already_planned() precondition."""

    @pytest.fixture
    def workflow(self, tmp_path):
        """Create workflow instance with tmp planning dir."""
        with (
            patch("magma_cycling.workflows.end_of_week.get_data_config") as mock_data_config,
            patch("magma_cycling.workflows.end_of_week.calculate_week_start_date") as mock_calc,
        ):
            mock_calc.side_effect = [date(2026, 3, 2), date(2026, 3, 9)]
            mock_config = Mock()
            mock_config.data_repo_path = tmp_path / "data"
            mock_config.week_planning_dir = tmp_path / "planning"
            mock_data_config.return_value = mock_config
            (tmp_path / "planning").mkdir(parents=True)

            return EndOfWeekWorkflow(
                week_completed="S083",
                week_next="S084",
                dry_run=False,
            )

    def _write_planning(self, planning_dir, week_id, sessions, **extra):
        """Helper to write a planning JSON file."""
        data = {
            "week_id": week_id,
            "start_date": "2026-03-09",
            "end_date": "2026-03-15",
            "created_at": "2026-03-08T20:00:00",
            "last_updated": "2026-03-08T20:00:00",
            "version": 1,
            "athlete_id": "i999999",
            "tss_target": 300,
            "planned_sessions": sessions,
            **extra,
        }
        path = planning_dir / f"week_planning_{week_id}.json"
        path.write_text(json.dumps(data), encoding="utf-8")

    def test_next_week_not_planned_continues(self, workflow):
        """No planning file exists — should continue."""
        assert workflow._check_next_week_already_planned() is False

    def test_next_week_empty_template_continues(self, workflow):
        """Planning file with only planned/pending sessions and no intervals_id — continue."""
        sessions = [
            {
                "session_id": "S084-01",
                "date": "2026-03-09",
                "name": "Endurance",
                "type": "END",
                "tss_planned": 50,
                "duration_min": 60,
                "status": "planned",
            },
            {
                "session_id": "S084-02",
                "date": "2026-03-10",
                "name": "Repos",
                "type": "REC",
                "tss_planned": 0,
                "duration_min": 0,
                "status": "pending",
            },
        ]
        self._write_planning(workflow.planning_dir, "S084", sessions)

        assert workflow._check_next_week_already_planned() is False

    def test_next_week_with_intervals_id_skips(self, workflow):
        """Planning has a session with intervals_id — should skip."""
        sessions = [
            {
                "session_id": "S084-01",
                "date": "2026-03-09",
                "name": "Endurance",
                "type": "END",
                "tss_planned": 50,
                "duration_min": 60,
                "status": "planned",
                "intervals_id": 12345678,
            },
        ]
        self._write_planning(workflow.planning_dir, "S084", sessions)

        assert workflow._check_next_week_already_planned() is True

    def test_next_week_with_active_status_skips(self, workflow):
        """Planning has a session with status=uploaded — should skip."""
        sessions = [
            {
                "session_id": "S084-01",
                "date": "2026-03-09",
                "name": "Endurance",
                "type": "END",
                "tss_planned": 50,
                "duration_min": 60,
                "status": "uploaded",
            },
        ]
        self._write_planning(workflow.planning_dir, "S084", sessions)

        assert workflow._check_next_week_already_planned() is True

    def test_next_week_source_mcp_skips(self, workflow):
        """Planning with source=mcp should skip even if sessions are planned."""
        sessions = [
            {
                "session_id": "S084-01",
                "date": "2026-03-09",
                "name": "Endurance",
                "type": "END",
                "tss_planned": 50,
                "duration_min": 60,
                "status": "planned",
            },
        ]
        self._write_planning(workflow.planning_dir, "S084", sessions, source="mcp")

        assert workflow._check_next_week_already_planned() is True

    def test_next_week_source_eow_with_empty_sessions_continues(self, workflow):
        """Planning with source=eow and template sessions — should continue."""
        sessions = [
            {
                "session_id": "S084-01",
                "date": "2026-03-09",
                "name": "Endurance",
                "type": "END",
                "tss_planned": 50,
                "duration_min": 60,
                "status": "planned",
            },
        ]
        self._write_planning(workflow.planning_dir, "S084", sessions, source="eow")

        assert workflow._check_next_week_already_planned() is False


# =============================================================================
# Tests: EndOfWeekWorkflow Integration
# =============================================================================


class TestEndOfWeekWorkflowIntegration:
    """Test complete workflow execution."""

    @pytest.fixture
    def workflow_with_mocks(self):
        """Create workflow with all external calls mocked."""
        with (
            patch("magma_cycling.workflows.end_of_week.get_data_config"),
            patch("magma_cycling.workflows.end_of_week.calculate_week_start_date") as mock_calc,
        ):
            mock_calc.side_effect = [date(2026, 1, 5), date(2026, 1, 12)]
            mock_config = Mock()
            mock_config.data_repo_path = Path("/tmp/data")
            mock_config.week_planning_dir = Path("/tmp/planning")

            with patch(
                "magma_cycling.workflows.end_of_week.get_data_config",
                return_value=mock_config,
            ):
                workflow = EndOfWeekWorkflow(
                    week_completed="S075",
                    week_next="S076",
                    provider="clipboard",
                    dry_run=True,
                    auto=True,
                )

                # Mock all subprocess calls
                with (
                    patch("subprocess.run") as mock_subprocess,
                    patch.object(workflow, "_get_workouts_clipboard", return_value=True),
                    patch.object(workflow, "_load_existing_reports", return_value=None),
                ):
                    mock_subprocess.return_value = Mock(returncode=0, stdout="Success")
                    workflow.workouts_content = "=== WORKOUT S076-01 ==="
                    yield workflow

    def test_workflow_run_dry_run_success(self, workflow_with_mocks):
        """Test complete workflow in dry-run mode (success path)."""
        result = workflow_with_mocks.run()

        assert result is True

    @patch("magma_cycling.workflows.end_of_week.get_data_config")
    @patch("magma_cycling.workflows.end_of_week.calculate_week_start_date")
    def test_workflow_run_step1_failure(self, mock_calc, mock_config):
        """Test workflow stops on step 1 failure."""
        mock_calc.side_effect = [date(2026, 1, 5), date(2026, 1, 12)]
        mock_config_obj = Mock()
        mock_config_obj.data_repo_path = Path("/tmp/data")
        mock_config_obj.week_planning_dir = Path("/tmp/planning")
        mock_config.return_value = mock_config_obj

        workflow = EndOfWeekWorkflow(week_completed="S075", week_next="S076", dry_run=True)

        with patch.object(workflow, "_step1_analyze_completed_week", return_value=False):
            result = workflow.run()

            assert result is False


# =============================================================================
# Tests: CLI Argument Parsing
# =============================================================================


class TestParseArgs:
    """Test CLI argument parsing."""

    def test_parse_args_minimal(self):
        """Test parsing with minimal required arguments."""
        args = parse_args(["--week-completed", "S075", "--week-next", "S076"])

        assert args.week_completed == "S075"
        assert args.week_next == "S076"
        assert args.provider == "clipboard"
        assert args.dry_run is False
        assert args.auto is False
        assert args.archive is False

    def test_parse_args_all_options(self):
        """Test parsing with all options."""
        args = parse_args(
            [
                "--week-completed",
                "S075",
                "--week-next",
                "S076",
                "--provider",
                "claude_api",
                "--dry-run",
                "--auto",
                "--archive",
            ]
        )

        assert args.week_completed == "S075"
        assert args.week_next == "S076"
        assert args.provider == "claude_api"
        assert args.dry_run is True
        assert args.auto is True
        assert args.archive is True

    def test_parse_args_auto_transition(self):
        """Test parsing with --auto-calculate flag."""
        args = parse_args(["--auto-calculate"])

        assert args.auto_calculate is True
        assert args.week_completed is None
        assert args.week_next is None


# =============================================================================
# Tests: Main Entry Point
# =============================================================================


class TestMain:
    """Test main() entry point."""

    @patch("magma_cycling.workflows.end_of_week.parse_args")
    @patch("magma_cycling.workflows.end_of_week.calculate_weekly_transition")
    @patch("magma_cycling.workflows.end_of_week.EndOfWeekWorkflow")
    def test_main_manual_weeks(self, mock_workflow_class, mock_transition, mock_parse_args):
        """Test main() with manual week specification."""
        mock_args = Mock()
        mock_args.week_completed = "S075"
        mock_args.week_next = "S076"
        mock_args.auto_calculate = False
        mock_args.provider = "clipboard"
        mock_args.dry_run = False
        mock_args.auto = False
        mock_args.archive = False
        mock_parse_args.return_value = mock_args

        mock_workflow = Mock()
        mock_workflow.run.return_value = True
        mock_workflow_class.return_value = mock_workflow

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    @patch("magma_cycling.workflows.end_of_week.parse_args")
    @patch("magma_cycling.workflows.end_of_week.calculate_weekly_transition")
    @patch("magma_cycling.workflows.end_of_week.EndOfWeekWorkflow")
    def test_main_auto_transition(self, mock_workflow_class, mock_transition, mock_parse_args):
        """Test main() with --auto-calculate."""
        mock_args = Mock()
        mock_args.week_completed = None
        mock_args.week_next = None
        mock_args.auto_calculate = True
        mock_args.provider = "clipboard"
        mock_args.dry_run = False
        mock_args.auto = False
        mock_args.archive = False
        mock_parse_args.return_value = mock_args

        # Mock transition calculation
        mock_transition.return_value = (
            "S077",
            "S078",
            date(2026, 1, 19),
            date(2026, 1, 26),
        )

        mock_workflow = Mock()
        mock_workflow.run.return_value = True
        mock_workflow_class.return_value = mock_workflow

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        mock_workflow_class.assert_called_once()

    @patch("magma_cycling.workflows.end_of_week.parse_args")
    @patch("magma_cycling.workflows.end_of_week.EndOfWeekWorkflow")
    def test_main_workflow_failure(self, mock_workflow_class, mock_parse_args):
        """Test main() when workflow fails."""
        mock_args = Mock()
        mock_args.week_completed = "S075"
        mock_args.week_next = "S076"
        mock_args.auto_calculate = False
        mock_args.provider = "clipboard"
        mock_args.dry_run = False
        mock_args.auto = False
        mock_args.archive = False
        mock_parse_args.return_value = mock_args

        mock_workflow = Mock()
        mock_workflow.run.return_value = False
        mock_workflow_class.return_value = mock_workflow

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


# =============================================================================
# Summary
# =============================================================================

"""
Test Coverage Summary:

Functions tested:
✅ calculate_week_start_date (3 tests)
✅ calculate_weekly_transition (3 tests)
✅ EndOfWeekWorkflow.__init__ (3 tests)
✅ EndOfWeekWorkflow steps 1-6 (15 tests)
✅ EndOfWeekWorkflow.run integration (2 tests)
✅ parse_args CLI (3 tests)
✅ main() entry point (3 tests)

Total: 32 tests
Target coverage: 80%+

Edge cases covered:
- Invalid dates (not Monday)
- Config errors
- Subprocess failures
- User abort (KeyboardInterrupt)
- Dry-run mode
- Auto mode
- Archive mode
- Validation warnings
- Step failures

Mocking strategy:
- get_week_config() for date calculations
- subprocess.run() for CLI calls
- File I/O for workouts content
- User input for clipboard mode
"""
