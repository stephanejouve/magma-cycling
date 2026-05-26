"""Tests for ``magma_cycling.workflows.eow.analysis`` (PR3 iso-config AC3).

Focused on the ``ai_analysis=True`` propagation through
``_step1_analyze_completed_week`` to ``run_weekly_analysis``.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from magma_cycling.workflows.eow.analysis import AnalysisMixin


class StubEowWorkflow(AnalysisMixin):
    """Stub providing the attributes ``_step1_analyze_completed_week`` reads."""

    def __init__(
        self,
        *,
        dry_run: bool = False,
        week_completed: str = "S099",
        completed_start_date: date = date(2026, 5, 18),
        data_dir: Path | None = None,
        reports_dir: Path | None = None,
    ) -> None:
        self.dry_run = dry_run
        self.week_completed = week_completed
        self.completed_start_date = completed_start_date
        self.data_dir = data_dir or Path("/tmp/magma-eow-test-data")
        self.reports_dir = reports_dir or Path("/tmp/magma-eow-test-reports")
        self.reports: dict[str, str] = {}

    def _load_existing_reports(self) -> None:  # pragma: no cover - stub only
        self.reports = {"bilan_final": "stub"}


class TestAiAnalysisPropagated:
    """Ensure ai_analysis=True is forwarded to run_weekly_analysis (PR3 AC3)."""

    def test_ai_analysis_true_forwarded(self, tmp_path: Path) -> None:
        reports_dir = tmp_path / "reports"
        (reports_dir / "S099").mkdir(parents=True)

        wf = StubEowWorkflow(
            week_completed="S099",
            data_dir=tmp_path / "data",
            reports_dir=reports_dir,
        )

        fake_module = MagicMock()
        # After our patched run_weekly_analysis returns, the bilan file must
        # exist so _step1 takes the success branch.
        bilan_path = reports_dir / "S099" / "bilan_final_s099.md"

        def fake_run(*, week, start_date, data_dir, ai_analysis) -> None:
            bilan_path.write_text("# bilan\n", encoding="utf-8")

        fake_module.run_weekly_analysis = MagicMock(side_effect=fake_run)

        with patch.dict(
            sys.modules,
            {"magma_cycling.workflows.workflow_weekly": fake_module},
        ):
            assert wf._step1_analyze_completed_week() is True

        fake_module.run_weekly_analysis.assert_called_once_with(
            week="S099",
            start_date=wf.completed_start_date,
            data_dir=wf.data_dir,
            ai_analysis=True,
        )

    def test_existing_bilan_skips_run(self, tmp_path: Path) -> None:
        reports_dir = tmp_path / "reports"
        week_dir = reports_dir / "S099"
        week_dir.mkdir(parents=True)
        (week_dir / "bilan_final_s099.md").write_text("existing", encoding="utf-8")

        wf = StubEowWorkflow(
            week_completed="S099",
            data_dir=tmp_path / "data",
            reports_dir=reports_dir,
        )

        fake_module = MagicMock()
        with patch.dict(
            sys.modules,
            {"magma_cycling.workflows.workflow_weekly": fake_module},
        ):
            assert wf._step1_analyze_completed_week() is True

        fake_module.run_weekly_analysis.assert_not_called()
