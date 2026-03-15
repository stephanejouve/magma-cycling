"""Tests for ReconciliationMixin — _display_reconciliation_report and reconcile_week."""

from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.workflows.coach.reconciliation import ReconciliationMixin

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def reconciliation_result():
    """Sample reconciliation result dict."""
    return {
        "matched": [
            {
                "session": {"session_id": "S999-01", "date": "2026-03-02"},
                "activity": {"id": "a1"},
            },
        ],
        "rest_days": [
            {"session_id": "S999-03", "date": "2026-03-04"},
        ],
        "cancelled": [
            {
                "session_id": "S999-05",
                "date": "2026-03-06",
                "cancellation_reason": "Blessure genou droit",
            },
        ],
        "skipped": [],
        "unplanned": [],
    }


@pytest.fixture
def mixin_with_planning():
    """ReconciliationMixin with planning attribute set."""
    mixin = ReconciliationMixin()
    mixin.planning = {
        "planned_sessions": [
            {"session_id": "S999-01"},
            {"session_id": "S999-02"},
            {"session_id": "S999-03"},
            {"session_id": "S999-04"},
            {"session_id": "S999-05"},
        ],
    }
    return mixin


# ---------------------------------------------------------------------------
# _display_reconciliation_report
# ---------------------------------------------------------------------------


class TestDisplayReconciliationReport:
    """Tests for _display_reconciliation_report output."""

    def test_displays_session_counts(self, mixin_with_planning, reconciliation_result, capsys):
        """Prints counts for matched, rest_days, cancelled."""
        mixin_with_planning._display_reconciliation_report(reconciliation_result)

        out = capsys.readouterr().out
        assert "Sessions planifiées" in out
        assert "Sessions exécutées" in out
        assert "Repos planifiés" in out
        assert "Séances annulées" in out

    def test_displays_matched_sessions(self, mixin_with_planning, reconciliation_result, capsys):
        """Lists matched sessions by session_id."""
        mixin_with_planning._display_reconciliation_report(reconciliation_result)

        out = capsys.readouterr().out
        assert "S999-01" in out
        assert "2026-03-02" in out

    def test_displays_cancelled_with_reason(
        self, mixin_with_planning, reconciliation_result, capsys
    ):
        """Lists cancelled sessions with truncated reason."""
        mixin_with_planning._display_reconciliation_report(reconciliation_result)

        out = capsys.readouterr().out
        assert "S999-05" in out
        assert "Blessure" in out

    def test_displays_unplanned_activities(self, mixin_with_planning, capsys):
        """Shows unplanned activities when present."""
        result = {
            "matched": [],
            "rest_days": [],
            "cancelled": [],
            "unplanned": [
                {"name": "Morning Run", "start_date_local": "2026-03-05T07:00:00"},
            ],
        }

        mixin_with_planning._display_reconciliation_report(result)

        out = capsys.readouterr().out
        assert "non planifiées" in out
        assert "Morning Run" in out

    def test_no_unplanned_section_when_empty(
        self, mixin_with_planning, reconciliation_result, capsys
    ):
        """No unplanned section when list is empty."""
        mixin_with_planning._display_reconciliation_report(reconciliation_result)

        out = capsys.readouterr().out
        assert "non planifiées" not in out


# ---------------------------------------------------------------------------
# reconcile_week
# ---------------------------------------------------------------------------


class TestReconcileWeek:
    """Tests for reconcile_week workflow."""

    def test_returns_early_on_api_error(self, capsys):
        """Returns early when _get_api raises ValueError."""
        mixin = ReconciliationMixin()
        mixin.clear_screen = MagicMock()
        mixin.print_header = MagicMock()
        mixin._get_api = MagicMock(side_effect=ValueError("No credentials"))

        mixin.reconcile_week("S999")

        out = capsys.readouterr().out
        assert "Credentials" in out

    @patch("magma_cycling.workflows.coach.reconciliation.load_week_planning")
    def test_returns_early_on_missing_planning(self, mock_load, capsys):
        """Returns early when planning file not found."""
        mock_load.side_effect = FileNotFoundError("not found")

        mixin = ReconciliationMixin()
        mixin.clear_screen = MagicMock()
        mixin.print_header = MagicMock()
        mixin._get_api = MagicMock(return_value=MagicMock())

        with patch("magma_cycling.workflows.coach.reconciliation.get_data_config") as mock_config:
            mock_config.return_value = MagicMock(week_planning_dir="/tmp/fake")
            mixin.reconcile_week("S999")

        out = capsys.readouterr().out
        assert "non trouvé" in out

    @patch("magma_cycling.workflows.coach.reconciliation.reconcile_planned_vs_actual")
    @patch("magma_cycling.workflows.coach.reconciliation.load_week_planning")
    @patch("magma_cycling.workflows.coach.reconciliation.get_data_config")
    def test_displays_summary_no_skipped(self, mock_config, mock_load, mock_reconcile, capsys):
        """Shows summary when no skipped sessions (no interactive prompts)."""
        mock_config.return_value = MagicMock(week_planning_dir="/tmp/fake")

        planning = MagicMock()
        planning.start_date = "2026-03-02"
        planning.end_date = "2026-03-08"
        planning.planned_sessions = []
        mock_load.return_value = planning

        api = MagicMock()
        api.get_activities.return_value = []

        mock_reconcile.return_value = {
            "matched": [],
            "skipped": [],
            "cancelled": [],
            "rest_days": [{"session_id": "S999-03", "date": "2026-03-04", "name": "Repos"}],
        }

        mixin = ReconciliationMixin()
        mixin.clear_screen = MagicMock()
        mixin.print_header = MagicMock()
        mixin._get_api = MagicMock(return_value=api)

        mixin.reconcile_week("S999")

        out = capsys.readouterr().out
        assert "RÉCONCILIATION" in out
        assert "Repos planifiés" in out
        assert "TERMINÉE" in out
