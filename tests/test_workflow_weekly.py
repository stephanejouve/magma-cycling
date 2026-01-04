"""
Tests for WeeklyWorkflow.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Author: Claude Code
Created: 2025-12-26
"""
from datetime import date
from unittest.mock import Mock, patch

import pytest

from cyclisme_training_logs.workflows.workflow_weekly import (
    WeeklyWorkflow,
    get_current_week_info,
    run_weekly_analysis,
)


def test_get_current_week_info():
    """Test calcul semaine courante.

    Examples:
        Basic week calculation::

            from cyclisme_training_logs.workflows.workflow_weekly import get_current_week_info
            from datetime import date

            week, start_date = get_current_week_info()

            assert week.startswith('S')
            assert isinstance(start_date, date)
            assert start_date.weekday() == 0  # Monday

        Verify week number format::

            week, start_date = get_current_week_info()

            # Week format is S + 3 digits
            assert len(week) == 4
            assert week[0] == 'S'
            assert week[1:].isdigit()
    """
    week, start_date = get_current_week_info()

    assert week.startswith("S")
    assert len(week) == 4
    assert week[1:].isdigit()
    assert isinstance(start_date, date)
    assert start_date.weekday() == 0  # Lundi


def test_get_current_week_monday_calculation():
    """Test calcul du lundi de la semaine courante.

    Examples:
        When today is Wednesday::

            # If today is 2025-01-08 (Wednesday)
            week, start_date = get_current_week_info()

            # Monday should be 2025-01-06
            assert start_date <= date.today()
            assert start_date.weekday() == 0

        When today is Monday::

            # If today is 2025-01-06 (Monday)
            week, start_date = get_current_week_info()

            # Monday should be today
            if date.today().weekday() == 0:
                assert start_date == date.today()
    """
    week, start_date = get_current_week_info()

    # Verify Monday is in the past or today
    assert start_date <= date.today()

    # Verify it's at most 6 days before today
    days_diff = (date.today() - start_date).days
    assert 0 <= days_diff <= 6


@pytest.fixture
def mock_data_dir(tmp_path):
    """Create temporary data directory for tests.

    Examples:
        Use fixture in test::

            def test_with_temp_dir(mock_data_dir):
                workflow = WeeklyWorkflow(
                    week="S073",
                    start_date=date(2025, 1, 6),
                    data_dir=mock_data_dir
                )
                assert workflow.data_dir == mock_data_dir

        Verify directory structure::

            def test_directory_structure(mock_data_dir):
                # Fixture creates base directory
                assert mock_data_dir.exists()
                assert mock_data_dir.is_dir()
    """
    return tmp_path


def test_weekly_workflow_initialization(mock_data_dir):
    """Test initialisation WeeklyWorkflow.

    Examples:
        Initialize with explicit parameters::

            from cyclisme_training_logs.workflows.workflow_weekly import WeeklyWorkflow
            from datetime import date
            from pathlib import Path

            workflow = WeeklyWorkflow(
                week="S073",
                start_date=date(2025, 1, 6),
                data_dir=Path("/tmp/test"),
                ai_analysis=True
            )

            assert workflow.week == "S073"
            assert workflow.start_date == date(2025, 1, 6)
            assert workflow.ai_analysis is True

        Initialize with defaults::

            workflow = WeeklyWorkflow(
                week="S073",
                start_date=date(2025, 1, 6)
            )

            # Data dir auto-detected
            assert workflow.data_dir is not None
            # AI analysis disabled by default
            assert workflow.ai_analysis is False
    """
    workflow = WeeklyWorkflow(
        week="S073", start_date=date(2025, 1, 6), data_dir=mock_data_dir, ai_analysis=False
    )

    assert workflow.week == "S073"
    assert workflow.start_date == date(2025, 1, 6)
    assert workflow.data_dir == mock_data_dir
    assert workflow.ai_analysis is False


@patch("cyclisme_training_logs.workflows.workflow_weekly.WeeklyAggregator")
@patch("cyclisme_training_logs.workflows.workflow_weekly.WeeklyAnalyzer")
def test_weekly_workflow_run(mock_analyzer_class, mock_aggregator_class, mock_data_dir):
    """Test exécution workflow complet.

    Examples:
        Mock workflow execution::

            from unittest.mock import patch, Mock

            with patch('cyclisme_training_logs.workflows.workflow_weekly.WeeklyAggregator') as mock_agg:
                with patch('cyclisme_training_logs.workflows.workflow_weekly.WeeklyAnalyzer') as mock_ana:
                    # Setup mocks
                    mock_agg_instance = Mock()
                    mock_agg.return_value = mock_agg_instance

                    workflow = WeeklyWorkflow(week="S073", start_date=date(2025, 1, 6))
                    reports = workflow.run()

                    # Verify aggregator called
                    assert mock_agg.called

        Verify pipeline execution::

            # Workflow executes 3 steps:
            # 1. Aggregation
            # 2. Analysis
            # 3. Save reports

            reports = workflow.run()

            assert 'workout_history' in reports
            assert len(reports) == 6
    """
    # Setup mock aggregator
    mock_aggregator = Mock()
    mock_aggregator_class.return_value = mock_aggregator

    mock_result = Mock()
    mock_result.success = True
    mock_result.data = {
        "processed": {
            "summary": {},
            "workouts": [],
            "metrics_evolution": {},
            "learnings": [],
            "protocol_adaptations": [],
            "transition": {},
            "compliance": {},
        }
    }
    mock_aggregator.aggregate.return_value = mock_result

    # Setup mock analyzer
    mock_analyzer = Mock()
    mock_analyzer_class.return_value = mock_analyzer

    mock_reports = {
        "workout_history": "# Workout History",
        "metrics_evolution": "# Metrics",
        "training_learnings": "# Learnings",
        "protocol_adaptations": "# Adaptations",
        "transition": "# Transition",
        "bilan_final": "# Bilan",
    }
    mock_analyzer.generate_all_reports.return_value = mock_reports
    mock_analyzer.save_reports = Mock()

    # Execute workflow
    workflow = WeeklyWorkflow(
        week="S073", start_date=date(2025, 1, 6), data_dir=mock_data_dir, ai_analysis=False
    )

    reports = workflow.run()

    # Verify aggregator called
    mock_aggregator_class.assert_called_once()
    mock_aggregator.aggregate.assert_called_once()

    # Verify analyzer called
    mock_analyzer_class.assert_called_once()
    mock_analyzer.generate_all_reports.assert_called_once()
    mock_analyzer.save_reports.assert_called_once()

    # Verify reports returned
    assert len(reports) == 6
    assert "workout_history" in reports


@patch("cyclisme_training_logs.workflows.workflow_weekly.WeeklyAggregator")
def test_weekly_workflow_aggregation_failure(mock_aggregator_class, mock_data_dir):
    """Test gestion échec aggregation.

    Examples:
        Handle aggregation failure::

            from unittest.mock import Mock

            mock_result = Mock()
            mock_result.success = False
            mock_result.errors = ['API error']

            mock_aggregator.aggregate.return_value = mock_result

            with pytest.raises(RuntimeError, match="aggregation failed"):
                workflow.run()

        Error propagation::

            # Workflow should raise RuntimeError
            # and not continue to analysis step

            try:
                workflow.run()
            except RuntimeError as e:
                assert "aggregation" in str(e).lower()
    """
    # Setup mock aggregator with failure
    mock_aggregator = Mock()
    mock_aggregator_class.return_value = mock_aggregator

    mock_result = Mock()
    mock_result.success = False
    mock_result.errors = ["API connection failed"]
    mock_aggregator.aggregate.return_value = mock_result

    workflow = WeeklyWorkflow(week="S073", start_date=date(2025, 1, 6), data_dir=mock_data_dir)

    with pytest.raises(RuntimeError, match="aggregation failed"):
        workflow.run()


@patch("subprocess.run")
@patch("cyclisme_training_logs.workflows.workflow_weekly.WeeklyAggregator")
@patch("cyclisme_training_logs.workflows.workflow_weekly.WeeklyAnalyzer")
def test_weekly_workflow_ai_analysis(
    mock_analyzer_class, mock_aggregator_class, mock_subprocess, mock_data_dir
):
    """Test AI analysis via clipboard.

    Examples:
        Enable AI analysis::

            workflow = WeeklyWorkflow(
                week="S073",
                start_date=date(2025, 1, 6),
                ai_analysis=True
            )

            reports = workflow.run()

            # Clipboard should be called
            assert subprocess.run.called

        Verify clipboard content::

            # Combined reports copied to clipboard
            # with separator between sections

            subprocess.run.assert_called_once()
            call_args = subprocess.run.call_args
            assert call_args[0][0] == ['pbcopy']
    """
    # Setup mocks
    mock_aggregator = Mock()
    mock_aggregator_class.return_value = mock_aggregator

    mock_result = Mock()
    mock_result.success = True
    mock_result.data = {
        "processed": {
            "summary": {},
            "workouts": [],
            "metrics_evolution": {},
            "learnings": [],
            "protocol_adaptations": [],
            "transition": {},
            "compliance": {},
        }
    }
    mock_aggregator.aggregate.return_value = mock_result

    mock_analyzer = Mock()
    mock_analyzer_class.return_value = mock_analyzer

    mock_reports = {"workout_history": "# History", "bilan_final": "# Bilan"}
    mock_analyzer.generate_all_reports.return_value = mock_reports
    mock_analyzer.save_reports = Mock()

    # Execute workflow with AI analysis
    workflow = WeeklyWorkflow(
        week="S073", start_date=date(2025, 1, 6), data_dir=mock_data_dir, ai_analysis=True
    )

    workflow.run()

    # Verify subprocess called for clipboard
    mock_subprocess.assert_called_once()
    call_args = mock_subprocess.call_args
    assert call_args[0][0] == ["pbcopy"]


@patch("cyclisme_training_logs.workflows.workflow_weekly.WeeklyWorkflow")
def test_run_weekly_analysis_utility(mock_workflow_class, mock_data_dir):
    """Test fonction utilitaire run_weekly_analysis.

    Examples:
        Use utility function::

            from cyclisme_training_logs.workflows.workflow_weekly import run_weekly_analysis
            from datetime import date

            reports = run_weekly_analysis(
                week="S073",
                start_date=date(2025, 1, 6),
                data_dir=Path("/tmp/test")
            )

            assert len(reports) == 6

        With AI analysis enabled::

            reports = run_weekly_analysis(
                week="S073",
                start_date=date(2025, 1, 6),
                ai_analysis=True
            )

            # Workflow created with ai_analysis=True
            assert reports is not None
    """
    # Setup mock workflow
    mock_workflow = Mock()
    mock_workflow_class.return_value = mock_workflow

    mock_reports = {"workout_history": "# History", "bilan_final": "# Bilan"}
    mock_workflow.run.return_value = mock_reports

    # Call utility function
    reports = run_weekly_analysis(
        week="S073", start_date=date(2025, 1, 6), data_dir=mock_data_dir, ai_analysis=False
    )

    # Verify workflow created correctly
    mock_workflow_class.assert_called_once_with(
        week="S073", start_date=date(2025, 1, 6), data_dir=mock_data_dir, ai_analysis=False
    )

    # Verify run called
    mock_workflow.run.assert_called_once()

    # Verify reports returned
    assert reports == mock_reports


def test_week_number_format():
    """Test format numéro semaine.

    Examples:
        Week number formatting::

            week, start_date = get_current_week_info()

            # Format: S + 3 digits zero-padded
            assert week[0] == 'S'
            assert len(week) == 4

            # Week 1 → S001
            # Week 52 → S052

        Parse week number::

            week = "S073"
            week_num = int(week[1:])

            assert week_num == 73
            assert 1 <= week_num <= 53
    """
    week, start_date = get_current_week_info()

    # Format verification
    assert week[0] == "S"
    assert len(week) == 4
    assert week[1:].isdigit()

    # Parse and verify range
    week_num = int(week[1:])
    assert 1 <= week_num <= 53


@patch("cyclisme_training_logs.workflows.workflow_weekly.WeeklyWorkflow")
def test_workflow_without_data_dir(mock_workflow_class):
    """Test workflow sans data_dir (auto-detect).

    Examples:
        Auto-detect data directory::

            workflow = WeeklyWorkflow(
                week="S073",
                start_date=date(2025, 1, 6)
                # data_dir not specified
            )

            # Should attempt to load from config
            assert workflow.data_dir is not None

        Fallback to default::

            # If config fails, fallback to ~/training-logs
            from pathlib import Path

            default_dir = Path.home() / 'training-logs'
            # Workflow should handle gracefully
    """
    mock_workflow = Mock()
    mock_workflow_class.return_value = mock_workflow

    # Call utility without data_dir
    run_weekly_analysis(week="S073", start_date=date(2025, 1, 6), data_dir=None)  # Auto-detect

    # Verify workflow created with None (triggers auto-detect)
    call_args = mock_workflow_class.call_args
    assert call_args[1]["data_dir"] is None
