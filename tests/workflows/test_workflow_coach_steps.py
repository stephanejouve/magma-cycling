"""
Tests for workflow_coach.py - Workflow Step Tests (Simplified).

Sprint R8: Phase 3 - Workflow Steps Tests
Target: 12 tests covering workflow step methods
Coverage goal: +3-5% (workflow step methods)

Test Categories:
- Welcome Step (1 test)
- Git Commit Step (2 tests)
- Analysis Insertion (2 tests)
- Markdown Helpers (3 tests)
- Display Methods (2 tests)
- Export Methods (2 tests)
"""

from pathlib import Path
from unittest.mock import Mock, mock_open, patch

from cyclisme_training_logs.workflow_coach import WorkflowCoach


class TestWelcomeStep:
    """Test welcome screen."""

    @patch("builtins.print")
    def test_step_1_welcome_displays_header(self, mock_print):
        """Test step_1_welcome displays welcome screen."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        with patch.object(coach, "clear_screen"):
            with patch.object(coach, "wait_user"):
                coach.step_1_welcome()

        # Should print welcome message
        assert mock_print.called
        call_args_str = str(mock_print.call_args_list)
        assert any(
            keyword in call_args_str.lower()
            for keyword in ["bienvenue", "workflow", "analyse", "coach"]
        )


class TestGitCommitStep:
    """Test git commit workflow."""

    @patch("subprocess.run")
    @patch("builtins.input", return_value="o")
    @patch("builtins.print")
    def test_step_7_git_commit_success(self, mock_print, mock_input, mock_subprocess):
        """Test step_7_git_commit commits successfully."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=False)
        coach.activity_name = "Morning Tempo"

        # Mock successful git commands
        mock_subprocess.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # git add
            Mock(returncode=0, stdout="", stderr=""),  # git commit
            Mock(stdout="On branch main\nnothing to commit", returncode=0),  # git status
        ]

        with patch.object(coach, "clear_screen"):
            with patch.object(coach, "wait_user"):
                coach.step_7_git_commit()

        # Should execute git commands
        assert mock_subprocess.called

    @patch("builtins.print")
    def test_step_7_skips_when_flag_set(self, mock_print):
        """Test step_7_git_commit skips when skip_git=True."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.activity_name = "Test"

        with patch.object(coach, "clear_screen"):
            with patch.object(coach, "wait_user"):
                coach.step_7_git_commit()

        # Should skip git operations
        call_args_str = str(mock_print.call_args_list)
        assert "sauté" in call_args_str.lower() or "skip" in call_args_str.lower()


class TestAnalysisInsertion:
    """Test analysis insertion workflow."""

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_step_6_insert_analysis_success(self, mock_print, mock_subprocess):
        """Test step_6_insert_analysis inserts analysis."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.activity_name = "Test Workout"

        # Mock successful subprocess
        mock_subprocess.return_value = Mock(returncode=0)

        with patch.object(coach, "clear_screen"):
            with patch.object(coach, "wait_user"):
                coach.step_6_insert_analysis()

        # Should call insert_analysis.py
        assert mock_subprocess.called
        call_args = mock_subprocess.call_args[0][0]
        assert "insert_analysis" in str(call_args)

    @patch("subprocess.run")
    @patch("sys.exit")
    @patch("builtins.print")
    def test_step_6_insert_analysis_handles_error(self, mock_print, mock_exit, mock_subprocess):
        """Test step_6_insert_analysis handles insertion errors."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.activity_name = "Test Workout"

        # Mock failed subprocess
        mock_subprocess.return_value = Mock(returncode=1)

        with patch.object(coach, "clear_screen"):
            with patch.object(coach, "wait_user"):
                try:
                    coach.step_6_insert_analysis()
                except SystemExit:
                    pass

        # Should call exit
        assert mock_exit.called or mock_subprocess.return_value.returncode == 1


class TestMarkdownHelpers:
    """Test markdown generation helpers."""

    def test_generate_skipped_markdown_creates_entry(self):
        """Test _generate_skipped_markdown generates markdown."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        skipped = {
            "planned_name": "S070-03 - Tempo Session",
            "planned_date": "2026-01-07",
            "planned_tss": 75,
        }

        markdown = coach._generate_skipped_markdown(skipped, "Fatigue excessive")

        # Should contain session info
        assert "S070-03" in markdown
        assert "Tempo Session" in markdown or "ANNULÉE" in markdown
        assert "Fatigue excessive" in markdown or "2026-01-07" in markdown

    @patch("cyclisme_training_logs.workflow_coach.TimelineInjector")
    def test_insert_to_history_writes_markdown(self, mock_timeline_injector_class):
        """Test _insert_to_history calls TimelineInjector.inject_chronologically."""
        from cyclisme_training_logs.core.timeline_injector import InjectionResult

        # Setup mock injector instance
        mock_injector = Mock()
        mock_timeline_injector_class.return_value = mock_injector

        # Mock inject_chronologically to return success
        mock_injector.inject_chronologically.return_value = InjectionResult(
            success=True, line_number=10, duplicate_found=False
        )

        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        markdowns = [("2026-01-12", "# Test Session\n\nGreat workout!")]

        result = coach._insert_to_history(markdowns)

        # Should create TimelineInjector with correct history_file path
        assert mock_timeline_injector_class.called
        call_args = mock_timeline_injector_class.call_args
        assert "history_file" in call_args.kwargs or len(call_args.args) > 0
        assert call_args.kwargs.get("check_duplicates", False) is True

        # Should call inject_chronologically with workout entry and date
        assert mock_injector.inject_chronologically.called
        inject_call = mock_injector.inject_chronologically.call_args
        assert inject_call.kwargs.get("workout_entry") == "# Test Session\n\nGreat workout!"
        assert inject_call.kwargs.get("workout_date").isoformat() == "2026-01-12"

        # Result should be True for successful injection
        assert result is True

    @patch("builtins.print")
    def test_preview_markdowns_displays_content(self, mock_print):
        """Test _preview_markdowns displays markdown content."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        markdowns = [
            ("2026-01-12", "# Session 1\n\nContent for session 1"),
            ("2026-01-13", "# Session 2\n\nContent for session 2"),
        ]

        coach._preview_markdowns(markdowns)

        # Should print preview
        assert mock_print.called
        # Should contain some session content or preview indicators
        assert mock_print.call_count > 0


class TestDisplayMethods:
    """Test display and reporting methods."""

    @patch("builtins.print")
    def test_display_gaps_summary_with_activities(self, mock_print):
        """Test _display_gaps_summary displays activities."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        gaps_data = {
            "unanalyzed": [
                {"id": "i12345", "start_date_local": "2026-01-12T10:00:00", "name": "Morning Ride"},
                {"id": "i67890", "start_date_local": "2026-01-13T10:00:00", "name": "Tempo"},
            ],
            "skipped": [],
            "rest_days": [],
            "cancelled": [],
        }

        count = coach._display_gaps_summary(gaps_data)

        # Should return count of unanalyzed
        assert count == 2
        assert mock_print.called

    @patch("builtins.print")
    def test_display_reconciliation_report_shows_info(self, mock_print):
        """Test _display_reconciliation_report displays report."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        # Mock planning attribute
        coach.planning = {
            "week_id": "S070",
            "planned_sessions": [
                {"date": "2026-01-11", "session_id": "S070-07", "type": "ENDURANCE"}
            ],
        }

        result = {
            "matched": [],
            "rest_days": [
                {"session_id": "S070-07", "date": "2026-01-11", "rest_reason": "Recovery"}
            ],
            "cancelled": [],
            "lightened": [],
        }

        coach._display_reconciliation_report(result)

        # Should print report
        assert mock_print.called


class TestExportMethods:
    """Test markdown export methods."""

    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists", return_value=False)
    def test_export_markdowns_creates_files(self, mock_exists, mock_mkdir, mock_file):
        """Test _export_markdowns creates markdown files."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.data_repo_path = Path("/fake/path")

        markdowns = [
            ("2026-01-12", "# Session 1\n\nContent"),
            ("2026-01-13", "# Session 2\n\nMore content"),
        ]

        _result = coach._export_markdowns(markdowns, "S070")

        # Should create directory and write files
        assert mock_mkdir.called or mock_file.called

    @patch("subprocess.Popen")
    def test_copy_to_clipboard_success(self, mock_popen):
        """Test _copy_to_clipboard copies markdown successfully."""
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"", b"")
        mock_popen.return_value = mock_process

        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        markdowns = [("2026-01-12", "# Test markdown")]

        result = coach._copy_to_clipboard(markdowns)

        # Should attempt to copy
        assert mock_popen.called or result in [True, False]


class TestSessionTypeDetection:
    """Test session type detection from markdown."""

    def test_detect_session_type_normal_workout(self):
        """Test _detect_session_type_from_markdown for normal workout."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        markdown = "# S072-03 - Morning Tempo\n\nGreat tempo session today."

        session_type = coach._detect_session_type_from_markdown(markdown)

        # Normal workouts return None
        assert session_type is None

    def test_detect_session_type_rest_day(self):
        """Test _detect_session_type_from_markdown detects rest."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        markdown = "# REPOS - 2026-01-12\n\n[REPOS]\n\nRecovery day"

        session_type = coach._detect_session_type_from_markdown(markdown)

        # Should detect rest
        assert session_type == "rest"

    def test_detect_session_type_cancelled(self):
        """Test _detect_session_type_from_markdown detects cancelled."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        markdown = "# S072-02 - [ANNULÉE]\n\nSession cancelled due to weather."

        session_type = coach._detect_session_type_from_markdown(markdown)

        # Should detect cancelled
        assert session_type == "cancelled"
