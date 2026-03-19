"""Tests for DailySync.__init__ and DailySync.run() orchestration.

Covers init branches (AI enabled/disabled, providers available/absent)
and run() control flow (activities, AI analysis, servo, compensation,
CTL, planning, email).
"""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

MODULE = "magma_cycling.daily_sync"


def _patch_init_deps():
    """Return patches dict for DailySync.__init__ dependencies."""
    return {
        f"{MODULE}.create_intervals_client": MagicMock(),
        f"{MODULE}.ActivityTracker": MagicMock(),
    }


@pytest.fixture
def tmp_reports(tmp_path):
    """Provide a temporary reports directory."""
    return tmp_path / "reports"


@pytest.fixture
def mock_sync(tmp_reports):
    """Create a DailySync with all deps mocked, AI disabled."""
    with (
        patch(f"{MODULE}.create_intervals_client") as mock_client_factory,
        patch(f"{MODULE}.ActivityTracker"),
    ):
        from magma_cycling.daily_sync import DailySync

        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        sync = DailySync(
            tracking_file=Path("/tmp/tracking.json"),
            reports_dir=tmp_reports,
            enable_ai_analysis=False,
            enable_auto_servo=False,
            verbose=False,
        )
        sync.client = mock_client
        yield sync


# ─── __init__ ────────────────────────────────────────────────────────


class TestDailySyncInit:
    """Tests for DailySync.__init__ with AI configuration."""

    def test_init_without_ai(self, tmp_reports):
        with (
            patch(f"{MODULE}.create_intervals_client"),
            patch(f"{MODULE}.ActivityTracker"),
        ):
            from magma_cycling.daily_sync import DailySync

            sync = DailySync(
                tracking_file=Path("/tmp/t.json"),
                reports_dir=tmp_reports,
                enable_ai_analysis=False,
            )
            assert sync.ai_analyzer is None
            assert sync.prompt_generator is None
            assert sync.history_manager is None

    def test_init_with_ai_provider_available(self, tmp_reports):
        with (
            patch(f"{MODULE}.create_intervals_client"),
            patch(f"{MODULE}.ActivityTracker"),
            patch(f"{MODULE}.get_ai_config") as mock_ai_cfg,
            patch(f"{MODULE}.AIProviderFactory") as mock_factory,
            patch(f"{MODULE}.PromptGenerator"),
            patch(f"{MODULE}.WorkoutHistoryManager"),
        ):
            from magma_cycling.daily_sync import DailySync

            cfg = MagicMock()
            cfg.get_available_providers.return_value = ["openai", "anthropic"]
            cfg.default_provider = "anthropic"
            cfg.get_provider_config.return_value = {"api_key": "test"}
            mock_ai_cfg.return_value = cfg
            mock_factory.create.return_value = MagicMock()

            sync = DailySync(
                tracking_file=Path("/tmp/t.json"),
                reports_dir=tmp_reports,
                enable_ai_analysis=True,
            )
            assert sync.ai_analyzer is not None
            assert sync.enable_ai_analysis is True
            mock_factory.create.assert_called_once_with("anthropic", {"api_key": "test"})

    def test_init_with_ai_no_providers(self, tmp_reports):
        with (
            patch(f"{MODULE}.create_intervals_client"),
            patch(f"{MODULE}.ActivityTracker"),
            patch(f"{MODULE}.get_ai_config") as mock_ai_cfg,
        ):
            from magma_cycling.daily_sync import DailySync

            cfg = MagicMock()
            cfg.get_available_providers.return_value = []
            mock_ai_cfg.return_value = cfg

            sync = DailySync(
                tracking_file=Path("/tmp/t.json"),
                reports_dir=tmp_reports,
                enable_ai_analysis=True,
            )
            assert sync.ai_analyzer is None
            assert sync.enable_ai_analysis is False  # Disabled due to no providers

    def test_init_with_ai_default_not_available(self, tmp_reports):
        with (
            patch(f"{MODULE}.create_intervals_client"),
            patch(f"{MODULE}.ActivityTracker"),
            patch(f"{MODULE}.get_ai_config") as mock_ai_cfg,
            patch(f"{MODULE}.AIProviderFactory") as mock_factory,
            patch(f"{MODULE}.PromptGenerator"),
            patch(f"{MODULE}.WorkoutHistoryManager"),
        ):
            from magma_cycling.daily_sync import DailySync

            cfg = MagicMock()
            cfg.get_available_providers.return_value = ["openai"]
            cfg.default_provider = "anthropic"  # Not in available list
            cfg.get_provider_config.return_value = {"api_key": "k"}
            mock_ai_cfg.return_value = cfg
            mock_factory.create.return_value = MagicMock()

            DailySync(
                tracking_file=Path("/tmp/t.json"),
                reports_dir=tmp_reports,
                enable_ai_analysis=True,
            )
            # Falls back to first available provider
            mock_factory.create.assert_called_once_with("openai", {"api_key": "k"})

    def test_reports_dir_created(self, tmp_path):
        reports = tmp_path / "deep" / "nested" / "reports"
        with (
            patch(f"{MODULE}.create_intervals_client"),
            patch(f"{MODULE}.ActivityTracker"),
        ):
            from magma_cycling.daily_sync import DailySync

            DailySync(
                tracking_file=Path("/tmp/t.json"),
                reports_dir=reports,
            )
            assert reports.exists()


# ─── run() orchestration ─────────────────────────────────────────────


class TestRunBasic:
    """Tests for DailySync.run() basic flow."""

    def test_run_no_activities(self, mock_sync):
        mock_sync.check_activities = MagicMock(return_value=([], []))
        mock_sync.generate_report = MagicMock(return_value=Path("/tmp/report.md"))

        mock_sync.run(check_date=date(2026, 3, 19))

        mock_sync.check_activities.assert_called_once_with(date(2026, 3, 19))
        mock_sync.generate_report.assert_called_once()

    def test_run_marks_new_activities_as_analyzed(self, mock_sync):
        activity = {"id": "i123", "name": "Z2 Ride"}
        mock_sync.check_activities = MagicMock(return_value=([activity], [activity]))
        mock_sync.update_completed_sessions = MagicMock()
        mock_sync.generate_report = MagicMock(return_value=Path("/tmp/r.md"))

        mock_sync.run(check_date=date(2026, 3, 19))

        mock_sync.tracker.mark_analyzed.assert_called_once()

    def test_run_updates_completed_sessions(self, mock_sync):
        completed = [{"id": "i456", "name": "SST"}]
        mock_sync.check_activities = MagicMock(return_value=([], completed))
        mock_sync.update_completed_sessions = MagicMock()
        mock_sync.generate_report = MagicMock(return_value=Path("/tmp/r.md"))

        mock_sync.run(check_date=date(2026, 3, 19))

        mock_sync.update_completed_sessions.assert_called_once_with(completed)

    def test_run_no_update_when_no_completed(self, mock_sync):
        mock_sync.check_activities = MagicMock(return_value=([], []))
        mock_sync.update_completed_sessions = MagicMock()
        mock_sync.generate_report = MagicMock(return_value=Path("/tmp/r.md"))

        mock_sync.run(check_date=date(2026, 3, 19))

        mock_sync.update_completed_sessions.assert_not_called()


class TestRunAIAnalysis:
    """Tests for run() AI analysis branch."""

    def test_ai_analysis_called_for_new_activities(self, mock_sync):
        activity = {"id": "i789", "name": "VO2"}
        mock_sync.enable_ai_analysis = True
        mock_sync.check_activities = MagicMock(return_value=([activity], []))
        mock_sync.analyze_activity = MagicMock(return_value="AI result")
        mock_sync.generate_report = MagicMock(return_value=Path("/tmp/r.md"))

        mock_sync.run(check_date=date(2026, 3, 19))

        mock_sync.analyze_activity.assert_called_once_with(activity)

    def test_ai_analysis_skipped_when_no_new_activities(self, mock_sync):
        mock_sync.enable_ai_analysis = True
        mock_sync.check_activities = MagicMock(return_value=([], []))
        mock_sync.analyze_activity = MagicMock()
        mock_sync.generate_report = MagicMock(return_value=Path("/tmp/r.md"))

        mock_sync.run(check_date=date(2026, 3, 19))

        mock_sync.analyze_activity.assert_not_called()


class TestRunServo:
    """Tests for run() auto-servo branch."""

    def test_servo_triggered_when_conditions_met(self, mock_sync):
        activity = {"id": "i111", "name": "TMP", "start_date_local": "2026-03-19T10:00:00"}
        mock_sync.enable_ai_analysis = True
        mock_sync.enable_auto_servo = True
        mock_sync.check_activities = MagicMock(return_value=([activity], []))
        mock_sync.analyze_activity = MagicMock(return_value="analysis")
        mock_sync.client.get_wellness.return_value = [{"ctl": 50}]
        mock_sync.extract_metrics_from_activity = MagicMock(return_value={"decoupling": 10})
        mock_sync.should_trigger_servo = MagicMock(return_value=(True, ["High decoupling"]))
        mock_sync.run_servo_adjustment = MagicMock(return_value={"adjusted": True})
        mock_sync.generate_report = MagicMock(return_value=Path("/tmp/r.md"))

        mock_sync.run(check_date=date(2026, 3, 19), week_id="S085")

        mock_sync.run_servo_adjustment.assert_called_once()

    def test_servo_not_triggered_when_no_signals(self, mock_sync):
        activity = {"id": "i111", "name": "Z2", "start_date_local": "2026-03-19T10:00:00"}
        mock_sync.enable_ai_analysis = True
        mock_sync.enable_auto_servo = True
        mock_sync.check_activities = MagicMock(return_value=([activity], []))
        mock_sync.analyze_activity = MagicMock(return_value=None)
        mock_sync.client.get_wellness.return_value = [{"ctl": 50}]
        mock_sync.extract_metrics_from_activity = MagicMock(return_value={})
        mock_sync.should_trigger_servo = MagicMock(return_value=(False, []))
        mock_sync.generate_report = MagicMock(return_value=Path("/tmp/r.md"))

        mock_sync.run_servo_adjustment = MagicMock()
        mock_sync.run(check_date=date(2026, 3, 19), week_id="S085")

        mock_sync.run_servo_adjustment.assert_not_called()

    def test_servo_skipped_without_week_id(self, mock_sync):
        activity = {"id": "i111", "name": "TMP", "start_date_local": "2026-03-19T10:00:00"}
        mock_sync.enable_ai_analysis = True
        mock_sync.enable_auto_servo = True
        mock_sync.check_activities = MagicMock(return_value=([activity], []))
        mock_sync.analyze_activity = MagicMock(return_value="analysis")
        mock_sync.extract_metrics_from_activity = MagicMock()
        mock_sync.generate_report = MagicMock(return_value=Path("/tmp/r.md"))

        mock_sync.run(check_date=date(2026, 3, 19))  # No week_id

        mock_sync.extract_metrics_from_activity.assert_not_called()


class TestRunCompensation:
    """Tests for run() TSS compensation branch."""

    def test_compensation_evaluated_with_week_and_ai(self, mock_sync):
        mock_sync.enable_ai_analysis = True
        mock_sync.ai_analyzer = MagicMock()
        mock_sync.ai_analyzer.analyze_session.return_value = "AI response"
        mock_sync.check_activities = MagicMock(return_value=([], []))
        mock_sync.generate_report = MagicMock(return_value=Path("/tmp/r.md"))

        with (
            patch(f"{MODULE}.evaluate_weekly_deficit") as mock_deficit,
            patch(f"{MODULE}.generate_compensation_prompt") as mock_prompt,
            patch(f"{MODULE}.parse_ai_compensation_response") as mock_parse,
        ):
            mock_deficit.return_value = {
                "deficit": 120,
                "days_remaining": 3,
                "week_id": "S085",
            }
            mock_prompt.return_value = "prompt text"
            mock_parse.return_value = {
                "strategy": "Redistribute",
                "total_compensated": 120,
            }

            mock_sync.run(check_date=date(2026, 3, 19), week_id="S085")

            mock_deficit.assert_called_once()
            mock_parse.assert_called_once_with("AI response")

    def test_compensation_skipped_when_deficit_below_threshold(self, mock_sync):
        mock_sync.enable_ai_analysis = True
        mock_sync.check_activities = MagicMock(return_value=([], []))
        mock_sync.generate_report = MagicMock(return_value=Path("/tmp/r.md"))

        with patch(f"{MODULE}.evaluate_weekly_deficit", return_value=None):
            mock_sync.run(check_date=date(2026, 3, 19), week_id="S085")


class TestRunCTLAnalysis:
    """Tests for run() CTL analysis branch."""

    def test_ctl_analysis_called_when_ai_enabled(self, mock_sync):
        mock_sync.enable_ai_analysis = True
        mock_sync.check_activities = MagicMock(return_value=([], []))
        mock_sync.analyze_ctl_peaks = MagicMock(return_value={"alerts": ["CTL low"]})
        mock_sync.generate_report = MagicMock(return_value=Path("/tmp/r.md"))

        mock_sync.run(check_date=date(2026, 3, 19))

        mock_sync.analyze_ctl_peaks.assert_called_once_with(check_date=date(2026, 3, 19))

    def test_ctl_not_called_when_ai_disabled(self, mock_sync):
        mock_sync.enable_ai_analysis = False
        mock_sync.check_activities = MagicMock(return_value=([], []))
        mock_sync.analyze_ctl_peaks = MagicMock()
        mock_sync.generate_report = MagicMock(return_value=Path("/tmp/r.md"))

        mock_sync.run(check_date=date(2026, 3, 19))

        mock_sync.analyze_ctl_peaks.assert_not_called()


class TestRunPlanningAndEmail:
    """Tests for run() planning changes and email branches."""

    def test_planning_checked_with_week_and_start_date(self, mock_sync):
        mock_sync.check_activities = MagicMock(return_value=([], []))
        mock_sync.check_planning_changes = MagicMock(
            return_value={"status": "no_changes", "diff": None}
        )
        mock_sync.generate_report = MagicMock(return_value=Path("/tmp/r.md"))

        mock_sync.run(
            check_date=date(2026, 3, 19),
            week_id="S085",
            start_date=date(2026, 3, 16),
        )

        mock_sync.check_planning_changes.assert_called_once_with(
            "S085", date(2026, 3, 16), date(2026, 3, 22)
        )

    def test_planning_not_checked_without_start_date(self, mock_sync):
        mock_sync.check_activities = MagicMock(return_value=([], []))
        mock_sync.check_planning_changes = MagicMock()
        mock_sync.generate_report = MagicMock(return_value=Path("/tmp/r.md"))

        mock_sync.run(check_date=date(2026, 3, 19), week_id="S085")

        mock_sync.check_planning_changes.assert_not_called()

    def test_email_sent_when_requested(self, mock_sync):
        mock_sync.check_activities = MagicMock(return_value=([], []))
        mock_sync.generate_report = MagicMock(return_value=Path("/tmp/r.md"))
        mock_sync.send_email = MagicMock(return_value=True)

        mock_sync.run(check_date=date(2026, 3, 19), send_email=True)

        mock_sync.send_email.assert_called_once_with(Path("/tmp/r.md"), date(2026, 3, 19))

    def test_email_not_sent_by_default(self, mock_sync):
        mock_sync.check_activities = MagicMock(return_value=([], []))
        mock_sync.generate_report = MagicMock(return_value=Path("/tmp/r.md"))
        mock_sync.send_email = MagicMock()

        mock_sync.run(check_date=date(2026, 3, 19))

        mock_sync.send_email.assert_not_called()

    def test_email_failure_does_not_crash(self, mock_sync):
        mock_sync.check_activities = MagicMock(return_value=([], []))
        mock_sync.generate_report = MagicMock(return_value=Path("/tmp/r.md"))
        mock_sync.send_email = MagicMock(return_value=False)

        # Should not raise
        mock_sync.run(check_date=date(2026, 3, 19), send_email=True)
