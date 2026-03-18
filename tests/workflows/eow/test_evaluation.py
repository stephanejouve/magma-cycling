"""Tests for workflows.eow.evaluation module.

Tests EvaluationMixin : _step1b_pid_evaluation, _step1c_monthly_analysis_if_month_end.
Uses sys.modules injection for locally-imported modules.
"""

import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from magma_cycling.workflows.eow.evaluation import EvaluationMixin


class StubEowWorkflow(EvaluationMixin):
    """Stub providing required attributes for EvaluationMixin."""

    def __init__(
        self,
        *,
        dry_run=False,
        completed_start_date=date(2026, 2, 24),
        completed_end_date=date(2026, 3, 1),
        next_start_date=date(2026, 3, 2),
        provider="claude",
        reports_dir=None,
    ):
        self.dry_run = dry_run
        self.completed_start_date = completed_start_date
        self.completed_end_date = completed_end_date
        self.next_start_date = next_start_date
        self.provider = provider
        self.reports_dir = reports_dir or Path("/tmp")


class TestStep1bPidEvaluation:
    """Tests for _step1b_pid_evaluation()."""

    def test_dry_run_returns_true(self):
        wf = StubEowWorkflow(dry_run=True)
        assert wf._step1b_pid_evaluation() is True

    def test_success(self):
        mock_evaluator = MagicMock()
        mock_evaluator.run_daily_evaluation.return_value = {}

        mock_module = MagicMock()
        mock_module.PIDDailyEvaluator.return_value = mock_evaluator

        with patch.dict(sys.modules, {"magma_cycling.scripts.pid_daily_evaluation": mock_module}):
            wf = StubEowWorkflow(dry_run=False)
            result = wf._step1b_pid_evaluation()

        assert result is True
        mock_evaluator.run_daily_evaluation.assert_called_once_with(days_back=7)

    def test_with_test_recommendation(self):
        mock_evaluator = MagicMock()
        mock_evaluator.run_daily_evaluation.return_value = {
            "test_recommendation": {
                "status": "RECOMMENDED",
                "message": "Test FTP recommended",
                "timing": "Next week",
                "weeks_since_test": 8.0,
                "tsb": 12.5,
            }
        }

        mock_module = MagicMock()
        mock_module.PIDDailyEvaluator.return_value = mock_evaluator

        with patch.dict(sys.modules, {"magma_cycling.scripts.pid_daily_evaluation": mock_module}):
            wf = StubEowWorkflow(dry_run=False)
            result = wf._step1b_pid_evaluation()
        assert result is True

    def test_exception_non_blocking(self):
        mock_module = MagicMock()
        mock_module.PIDDailyEvaluator.side_effect = Exception("Import error")

        with patch.dict(sys.modules, {"magma_cycling.scripts.pid_daily_evaluation": mock_module}):
            wf = StubEowWorkflow(dry_run=False)
            result = wf._step1b_pid_evaluation()
        # Non-blocking: returns True even on error
        assert result is True


class TestStep1cMonthlyAnalysis:
    """Tests for _step1c_monthly_analysis_if_month_end()."""

    def test_no_month_transition_skips(self):
        """When completed week and next week are same month, skip."""
        wf = StubEowWorkflow(
            completed_start_date=date(2026, 3, 9),
            next_start_date=date(2026, 3, 16),
        )
        result = wf._step1c_monthly_analysis_if_month_end()
        assert result is True

    def test_month_transition_detected_dry_run(self):
        """Dry run with month transition returns True."""
        wf = StubEowWorkflow(
            dry_run=True,
            completed_start_date=date(2026, 2, 24),
            next_start_date=date(2026, 3, 2),
        )
        result = wf._step1c_monthly_analysis_if_month_end()
        assert result is True

    def test_month_transition_generates_report(self, tmp_path):
        mock_analyzer = MagicMock()
        mock_analyzer.run.return_value = "# Monthly Report\nContent here"

        mock_module = MagicMock()
        mock_module.MonthlyAnalyzer.return_value = mock_analyzer

        with patch.dict(sys.modules, {"magma_cycling.monthly_analysis": mock_module}):
            wf = StubEowWorkflow(
                dry_run=False,
                completed_start_date=date(2026, 2, 24),
                next_start_date=date(2026, 3, 2),
                reports_dir=tmp_path,
            )
            result = wf._step1c_monthly_analysis_if_month_end()

        assert result is True
        report_file = tmp_path / "monthly_report_2026-02.md"
        assert report_file.exists()
        assert "Monthly Report" in report_file.read_text()

    def test_empty_report_returns_true(self, tmp_path):
        mock_analyzer = MagicMock()
        mock_analyzer.run.return_value = None

        mock_module = MagicMock()
        mock_module.MonthlyAnalyzer.return_value = mock_analyzer

        with patch.dict(sys.modules, {"magma_cycling.monthly_analysis": mock_module}):
            wf = StubEowWorkflow(
                dry_run=False,
                completed_start_date=date(2026, 2, 24),
                next_start_date=date(2026, 3, 2),
                reports_dir=tmp_path,
            )
            result = wf._step1c_monthly_analysis_if_month_end()
        assert result is True

    def test_exception_non_blocking(self, tmp_path):
        mock_module = MagicMock()
        mock_module.MonthlyAnalyzer.side_effect = Exception("Analyzer error")

        with patch.dict(sys.modules, {"magma_cycling.monthly_analysis": mock_module}):
            wf = StubEowWorkflow(
                dry_run=False,
                completed_start_date=date(2026, 2, 24),
                next_start_date=date(2026, 3, 2),
                reports_dir=tmp_path,
            )
            result = wf._step1c_monthly_analysis_if_month_end()
        # Non-blocking
        assert result is True

    def test_provider_passed_to_analyzer(self, tmp_path):
        mock_analyzer = MagicMock()
        mock_analyzer.run.return_value = "Report"

        mock_module = MagicMock()
        mock_module.MonthlyAnalyzer.return_value = mock_analyzer

        with patch.dict(sys.modules, {"magma_cycling.monthly_analysis": mock_module}):
            wf = StubEowWorkflow(
                dry_run=False,
                completed_start_date=date(2026, 2, 24),
                next_start_date=date(2026, 3, 2),
                reports_dir=tmp_path,
                provider="mistral",
            )
            wf._step1c_monthly_analysis_if_month_end()

        mock_module.MonthlyAnalyzer.assert_called_once_with(
            month="2026-02", provider="mistral", no_ai=False
        )

    def test_clipboard_provider_sets_no_ai(self, tmp_path):
        mock_analyzer = MagicMock()
        mock_analyzer.run.return_value = "Report"

        mock_module = MagicMock()
        mock_module.MonthlyAnalyzer.return_value = mock_analyzer

        with patch.dict(sys.modules, {"magma_cycling.monthly_analysis": mock_module}):
            wf = StubEowWorkflow(
                dry_run=False,
                completed_start_date=date(2026, 2, 24),
                next_start_date=date(2026, 3, 2),
                reports_dir=tmp_path,
                provider="clipboard",
            )
            wf._step1c_monthly_analysis_if_month_end()

        mock_module.MonthlyAnalyzer.assert_called_once_with(
            month="2026-02", provider="clipboard", no_ai=True
        )
