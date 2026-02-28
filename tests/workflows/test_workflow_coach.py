"""
Tests for workflow_coach.py - WorkflowCoach orchestrator.

Sprint R8: Phase 1 - Core Logic Tests (Parsing & Formatting)
Target: 30 tests covering core business logic
Coverage goal: 10% → 50% (+40%)

Test Categories:
- Parsing & Formatting (8 tests)
- Planning Modifications (10 tests)
- Initialization (5 tests)
- Gap Detection Logic (7 tests)
"""

import json
from datetime import date
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest
import requests

from magma_cycling.workflow_coach import WorkflowCoach


class TestParsingAndFormatting:
    """Test parsing and formatting methods (pure functions)."""

    def test_parse_ai_modifications_valid_json_markdown(self):
        """Test parse_ai_modifications with valid JSON in markdown."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        ai_response = """
Here are the modifications:

```json
{
  "modifications": [
    {"action": "lighten", "date": "2025-12-18", "percentage": 10},
    {"action": "skip", "date": "2025-12-19"}
  ]
}
```
"""
        modifications = coach.parse_ai_modifications(ai_response)

        assert len(modifications) == 2
        assert modifications[0]["action"] == "lighten"
        assert modifications[0]["date"] == "2025-12-18"
        assert modifications[0]["percentage"] == 10
        assert modifications[1]["action"] == "skip"
        assert modifications[1]["date"] == "2025-12-19"

    def test_parse_ai_modifications_valid_json_plain(self):
        """Test parse_ai_modifications with plain JSON (no markdown)."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        ai_response = '{"modifications": [{"action": "skip", "date": "2025-12-20"}]}'

        modifications = coach.parse_ai_modifications(ai_response)

        assert len(modifications) == 1
        assert modifications[0]["action"] == "skip"
        assert modifications[0]["date"] == "2025-12-20"

    def test_parse_ai_modifications_empty_response(self):
        """Test parse_ai_modifications with empty response."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        modifications = coach.parse_ai_modifications("")
        assert modifications == []

        modifications = coach.parse_ai_modifications("   ")
        assert modifications == []

    def test_parse_ai_modifications_no_json(self):
        """Test parse_ai_modifications with no JSON found."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        ai_response = "No modifications needed. Everything looks good."

        modifications = coach.parse_ai_modifications(ai_response)
        assert modifications == []

    def test_parse_ai_modifications_invalid_json(self):
        """Test parse_ai_modifications with malformed JSON."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        ai_response = """
```json
{
  "modifications": [
    {"action": "lighten", "date": "2025-12-18"
  ]
}
```
"""
        modifications = coach.parse_ai_modifications(ai_response)
        assert modifications == []

    def test_format_remaining_sessions_compact_empty(self):
        """Test format_remaining_sessions_compact with empty list."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        result = coach.format_remaining_sessions_compact([])
        assert result == ""

    def test_format_remaining_sessions_compact_multiple(self):
        """Test format_remaining_sessions_compact with multiple sessions."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        sessions = [
            {
                "date": "2025-12-18",
                "session_id": "S072-03",
                "name": "Tempo",
                "type": "TEMPO",
                "version": "V001",
                "tss_planned": 75,
            },
            {
                "date": "2025-12-19",
                "session_id": "S072-04",
                "name": "Recovery",
                "type": "RECOVERY",
                "version": "V001",
                "tss_planned": 30,
            },
            {
                "date": "2025-12-20",
                "session_id": "S072-05",
                "name": "Repos",
                "type": "REST",
                "status": "rest_day",
            },
        ]

        result = coach.format_remaining_sessions_compact(sessions)

        assert "PLANNING RESTANT (3 séances)" in result
        assert "2025-12-18: S072-03-TEMPO-Tempo-V001 (75 TSS)" in result
        assert "2025-12-19: S072-04-RECOVERY-Recovery-V001 (30 TSS)" in result
        assert "2025-12-20: REPOS" in result

    @patch("magma_cycling.workflow_coach.get_data_config")
    @patch("builtins.open", new_callable=mock_open)
    def test_extract_day_number_success(self, mock_file, mock_config):
        """Test _extract_day_number extracts correct day number."""
        # Mock config
        mock_config_obj = Mock()
        mock_config_obj.week_planning_dir = Path("/fake/path")
        mock_config.return_value = mock_config_obj

        # Mock planning file content
        planning_data = {"start_date": "2025-12-15", "week_id": "S072"}
        mock_file.return_value.read.return_value = json.dumps(planning_data)
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(planning_data)

        # Create coach and mock json.load
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        with patch("json.load", return_value=planning_data):
            day_number = coach._extract_day_number("2025-12-18", "S072")

        # 2025-12-18 is 3 days after 2025-12-15, so day_number = 4
        assert day_number == 4


class TestInitialization:
    """Test initialization and setup methods."""

    def test_init_default_params(self):
        """Test __init__ with default parameters."""
        coach = WorkflowCoach()

        assert coach.skip_feedback is False
        assert coach.skip_git is False
        assert coach.activity_id is None
        assert coach.week_id is None
        assert coach.servo_mode is False
        assert coach.auto_mode is False
        assert coach.project_root == Path.cwd()

    def test_init_skip_flags(self):
        """Test __init__ with skip flags enabled."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        assert coach.skip_feedback is True
        assert coach.skip_git is True

    def test_init_servo_mode(self):
        """Test __init__ with servo mode enabled."""
        with patch.object(WorkflowCoach, "load_workout_templates", return_value={"template1": {}}):
            coach = WorkflowCoach(servo_mode=True)

            assert coach.servo_mode is True
            assert coach.workout_templates == {"template1": {}}

    @patch("magma_cycling.config.get_intervals_config")
    @patch("magma_cycling.config.load_json_config", return_value=None)
    @patch("pathlib.Path.exists", return_value=False)
    @patch.dict(
        "os.environ",
        {"VITE_INTERVALS_ATHLETE_ID": "i123", "VITE_INTERVALS_API_KEY": "key123"},
        clear=True,
    )
    def test_load_credentials_from_env(self, mock_exists, mock_load_json, mock_get_config):
        """Test load_credentials loads from environment variables."""
        # Mock IntervalsConfig to return test credentials
        mock_intervals_config = Mock()
        mock_intervals_config.is_configured.return_value = True
        mock_intervals_config.athlete_id = "i123"
        mock_intervals_config.api_key = "key123"
        mock_get_config.return_value = mock_intervals_config

        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        athlete_id, api_key = coach.load_credentials()

        assert athlete_id == "i123"
        assert api_key == "key123"

    @patch("magma_cycling.config.load_json_config", return_value=None)
    @patch("magma_cycling.config.get_intervals_config")
    def test_load_credentials_missing(self, mock_get_config, mock_load_json):
        """Test load_credentials returns None when credentials missing."""
        # Mock IntervalsConfig as not configured
        mock_intervals_config = Mock()
        mock_intervals_config.is_configured.return_value = False
        mock_get_config.return_value = mock_intervals_config

        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        result = coach.load_credentials()

        assert result == (None, None)


class TestPlanningModifications:
    """Test planning modification methods."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Mock Control Tower to use tmp_path for planning."""
        from magma_cycling.planning.control_tower import planning_tower

        # Save original path
        original_planning_dir = planning_tower.planning_dir

        # Override with tmp_path
        planning_tower.planning_dir = tmp_path
        planning_tower.backup_system.planning_dir = tmp_path

        # Create required files for DataRepoConfig validation
        workouts_history = tmp_path / "workouts-history.md"
        workouts_history.touch()

        yield tmp_path

        # Restore original path
        planning_tower.planning_dir = original_planning_dir
        planning_tower.backup_system.planning_dir = original_planning_dir

    @pytest.fixture
    def temp_planning_file(self, tmp_path, mock_config):
        """Create temporary planning file for tests."""
        planning_data = {
            "week_id": "S072",
            "start_date": "2025-12-15",
            "end_date": "2025-12-21",
            "created_at": "2025-12-01T20:00:00Z",
            "last_updated": "2025-12-01T20:00:00Z",
            "version": 1,
            "athlete_id": "iXXXXXX",
            "tss_target": 350,
            "planned_sessions": [
                {
                    "session_id": "S072-03",
                    "date": "2025-12-18",
                    "name": "Tempo",
                    "type": "TEMPO",
                    "version": "V001",
                    "tss_planned": 75,
                    "duration_min": 60,
                    "description": "Original tempo session",
                    "status": "planned",
                    "intervals_id": None,
                    "description_hash": None,
                }
            ],
        }

        planning_file = tmp_path / "week_planning_S072.json"
        with open(planning_file, "w", encoding="utf-8") as f:
            json.dump(planning_data, f, indent=2)

        return planning_file

    def test_update_planning_json_success(self, temp_planning_file, tmp_path, mock_config):
        """Test _update_planning_json updates planning file successfully."""
        from magma_cycling.planning.models import WeeklyPlan

        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        new_workout = {
            "code": "S072-03-RECOVERY-Easy",
            "type": "RECOVERY",
            "tss": 50,
            "description": "Lightened recovery session",
        }

        result = coach._update_planning_json(
            week_id="S072",
            date="2025-12-18",
            new_workout=new_workout,
            old_workout="S072-03-TEMPO-Tempo",
            reason="Fatigue detected",
        )

        assert result is True

        # Verify file was updated with Pydantic
        plan = WeeklyPlan.from_json(temp_planning_file)
        assert plan.planned_sessions[0].session_type == "RECOVERY"
        assert plan.planned_sessions[0].tss_planned == 50
        assert "Lightened recovery session" in plan.planned_sessions[0].description

    @patch("magma_cycling.workflow_coach.get_data_config")
    @patch("builtins.open", side_effect=FileNotFoundError())
    def test_update_planning_json_file_not_found(self, mock_file, mock_config):
        """Test _update_planning_json handles missing planning file."""
        mock_config_obj = Mock()
        mock_config_obj.week_planning_dir = Path("/fake/path")
        mock_config.return_value = mock_config_obj

        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        result = coach._update_planning_json(
            week_id="S099",
            date="2025-12-18",
            new_workout={"code": "test", "type": "TEST", "tss": 50, "description": "Test"},
            old_workout="old",
            reason="test",
        )

        assert result is False

    @patch("builtins.print")
    def test_apply_planning_modifications_empty(self, mock_print):
        """Test apply_planning_modifications with empty list."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        coach.apply_planning_modifications([], "S072")

        # Should print "Planning maintenu tel quel"
        mock_print.assert_called_once()
        assert "Planning maintenu tel quel" in str(mock_print.call_args)

    @patch("builtins.print")
    def test_apply_planning_modifications_unknown_action(self, mock_print):
        """Test apply_planning_modifications with unknown action."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        modifications = [{"action": "unknown_action", "date": "2025-12-18"}]

        coach.apply_planning_modifications(modifications, "S072")

        # Should handle unknown action gracefully
        assert mock_print.called

    def test_compute_gaps_signature_simple(self):
        """Test _compute_gaps_signature with simple gaps data."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        gaps_data = {
            "unanalyzed": [{"id": "i12345678"}, {"id": "i87654321"}],
            "skipped": [],
            "rest_days": [],
            "cancelled": [],
        }

        signature = coach._compute_gaps_signature(gaps_data)

        # Signature should be MD5 hash (32 hex characters)
        assert isinstance(signature, str)
        assert len(signature) == 32

    def test_compute_gaps_signature_all_types(self):
        """Test _compute_gaps_signature with all gap types."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        gaps_data = {
            "unanalyzed": [{"id": "i12345678"}],
            "skipped": [{"planned_name": "S072-03 - Tempo", "planned_date": "2025-12-18"}],
            "rest_days": [{"session_id": "S072-07", "date": "2025-12-22"}],
            "cancelled": [{"session_id": "S072-02", "date": "2025-12-17"}],
        }

        signature = coach._compute_gaps_signature(gaps_data)

        assert isinstance(signature, str)
        assert len(signature) == 32

        # Different data should produce different signature
        gaps_data2 = {
            "unanalyzed": [{"id": "i99999999"}],
            "skipped": [],
            "rest_days": [],
            "cancelled": [],
        }

        signature2 = coach._compute_gaps_signature(gaps_data2)
        assert signature != signature2


class TestGapDetectionLogic:
    """Test gap detection and filtering methods."""

    @patch("pathlib.Path.exists", return_value=False)
    def test_detect_unanalyzed_activities_no_config(self, mock_exists):
        """Test _detect_unanalyzed_activities returns None when config missing."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        state = Mock()

        result = coach._detect_unanalyzed_activities(state, "2025-12-01", "2025-12-31")

        assert result is None

    @patch("pathlib.Path.exists", return_value=True)
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"athlete_id": "i123", "api_key": "key123"}',
    )
    @patch("requests.Session")
    def test_detect_unanalyzed_activities_success(self, mock_session, mock_file, mock_exists):
        """Test _detect_unanalyzed_activities fetches and filters activities."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = [
            {"id": "i12345", "start_date_local": "2025-12-20T10:00:00"},
            {"id": "i67890", "start_date_local": "2025-12-19T10:00:00"},
        ]
        mock_session_instance = mock_session.return_value
        mock_session_instance.get.return_value = mock_response

        # Mock state filtering
        state = Mock()
        state.get_unanalyzed_activities.return_value = [
            {"id": "i12345", "start_date_local": "2025-12-20T10:00:00"}
        ]

        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        result = coach._detect_unanalyzed_activities(state, "2025-12-01", "2025-12-31")

        assert result is not None
        assert len(result) == 1
        assert result[0]["id"] == "i12345"

    @patch("pathlib.Path.exists", return_value=True)
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"athlete_id": "i123", "api_key": "key123"}',
    )
    @patch("requests.Session")
    def test_detect_unanalyzed_activities_api_error(self, mock_session, mock_file, mock_exists):
        """Test _detect_unanalyzed_activities handles API errors."""
        # Mock API error
        mock_session_instance = mock_session.return_value
        mock_session_instance.get.side_effect = requests.exceptions.RequestException("API Error")

        state = Mock()
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        result = coach._detect_unanalyzed_activities(state, "2025-12-01", "2025-12-31")

        assert result is None

    def test_filter_documented_sessions_empty(self):
        """Test _filter_documented_sessions with empty list."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        state = Mock()

        result = coach._filter_documented_sessions([], state, "skipped")

        assert result == []

    def test_filter_documented_sessions_skipped(self):
        """Test _filter_documented_sessions filters skipped sessions."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        state = Mock()

        # Mock: first session is documented, second is not
        state.is_special_session_documented.side_effect = [True, False]

        sessions = [
            {"planned_name": "S072-03 - Tempo", "planned_date": "2025-12-18"},
            {"planned_name": "S072-05 - Recovery", "planned_date": "2025-12-20"},
        ]

        result = coach._filter_documented_sessions(sessions, state, "skipped")

        # Should only return the second session (not documented)
        assert len(result) == 1
        assert result[0]["planned_name"] == "S072-05 - Recovery"

    def test_filter_documented_sessions_rest(self):
        """Test _filter_documented_sessions filters rest days."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        state = Mock()

        # Mock: first rest is documented, second is not
        state.is_special_session_documented.side_effect = [True, False]

        sessions = [
            {"session_id": "S072-07", "date": "2025-12-22"},
            {"session_id": "S073-01", "date": "2025-12-23"},
        ]

        result = coach._filter_documented_sessions(sessions, state, "rest")

        assert len(result) == 1
        assert result[0]["session_id"] == "S073-01"

    def test_filter_documented_sessions_all_documented(self):
        """Test _filter_documented_sessions when all sessions already documented."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        state = Mock()

        # Mock: all sessions documented
        state.is_special_session_documented.return_value = True

        sessions = [
            {"session_id": "S072-01", "date": "2025-12-15"},
            {"session_id": "S072-02", "date": "2025-12-16"},
        ]

        result = coach._filter_documented_sessions(sessions, state, "cancelled")

        assert result == []


class TestFeedbackCollection:
    """Test feedback collection methods."""

    def test_validate_feedback_collection_skip_flag(self):
        """Test _validate_feedback_collection respects skip_feedback flag."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.unanalyzed_activities = [{"id": "i12345"}]

        should_collect, skip_reason = coach._validate_feedback_collection()

        assert should_collect is False
        assert skip_reason == "skipped_by_flag"

    def test_validate_feedback_collection_no_gaps(self):
        """Test _validate_feedback_collection when no gaps detected."""
        coach = WorkflowCoach(skip_feedback=False, skip_git=True)
        coach.unanalyzed_activities = []

        should_collect, skip_reason = coach._validate_feedback_collection()

        assert should_collect is False
        assert skip_reason == "no_gaps"

    def test_validate_feedback_collection_should_collect(self):
        """Test _validate_feedback_collection when feedback should be collected."""
        coach = WorkflowCoach(skip_feedback=False, skip_git=True)
        coach.unanalyzed_activities = [{"id": "i12345"}]

        should_collect, skip_reason = coach._validate_feedback_collection()

        assert should_collect is True
        assert skip_reason is None

    @patch.object(WorkflowCoach, "load_credentials", return_value=("i123", "key123"))
    def test_prepare_feedback_context_success(self, mock_load_creds):
        """Test _prepare_feedback_context with valid credentials and activity."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.unanalyzed_activities = [
            {
                "id": "i12345",
                "name": "Morning Ride",
                "start_date_local": "2025-12-20T08:00:00",
            }
        ]

        activity, athlete_id, api_key = coach._prepare_feedback_context()

        assert activity is not None
        assert activity["id"] == "i12345"
        assert athlete_id == "i123"
        assert api_key == "key123"

    @patch.object(WorkflowCoach, "load_credentials", return_value=(None, None))
    def test_prepare_feedback_context_no_credentials(self, mock_load_creds):
        """Test _prepare_feedback_context when credentials missing."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.unanalyzed_activities = [{"id": "i12345"}]

        activity, athlete_id, api_key = coach._prepare_feedback_context()

        assert activity is None
        assert athlete_id == ""
        assert api_key == ""

    @patch("subprocess.run")
    def test_execute_feedback_collection_with_activity(self, mock_subprocess):
        """Test _execute_feedback_collection with activity context."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        activity = {
            "name": "Morning Ride",
            "start_date_local": "2025-12-20T08:00:00",
            "moving_time": 3600,
            "icu_training_load": 75,
            "icu_intensity": 105,
        }

        returncode = coach._execute_feedback_collection(activity, "full")

        assert returncode == 0
        assert mock_subprocess.called
        # Verify subprocess called with correct args
        call_args = mock_subprocess.call_args[0][0]
        assert "--activity-name" in call_args
        assert "Morning Ride" in call_args

    @patch("subprocess.run")
    def test_execute_feedback_collection_quick_mode(self, mock_subprocess):
        """Test _execute_feedback_collection with quick mode."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        returncode = coach._execute_feedback_collection(None, "quick")

        assert returncode == 0
        # Verify --quick flag present
        call_args = mock_subprocess.call_args[0][0]
        assert "--quick" in call_args

    @patch("builtins.input", side_effect=["7h30", "85", "65", "48"])
    def test_collect_rest_feedback_valid(self, mock_input):
        """Test _collect_rest_feedback with valid input."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        session_data = {
            "session_id": "S072-07",
            "date": "2025-12-22",
            "name": "Repos actif",
        }

        feedback = coach._collect_rest_feedback(session_data)

        assert feedback["sleep_duration"] == "7h30"
        assert feedback["sleep_score"] == 85
        assert feedback["hrv"] == 65
        assert feedback["resting_hr"] == 48


class TestMarkdownGeneration:
    """Test markdown generation and export methods."""

    @patch("builtins.print")
    def test_preview_markdowns_single(self, mock_print):
        """Test _preview_markdowns displays single markdown."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        markdowns = [("2025-12-20", "# Morning Ride\n\nGreat session today!")]

        coach._preview_markdowns(markdowns)

        assert mock_print.called
        # Should print preview header
        call_args_str = str(mock_print.call_args_list)
        assert "PREVIEW" in call_args_str or "Morning Ride" in call_args_str

    @patch("subprocess.Popen")
    def test_copy_to_clipboard_success(self, mock_popen):
        """Test _copy_to_clipboard copies markdown successfully."""
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"", b"")
        mock_popen.return_value = mock_process

        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        markdowns = [("2025-12-20", "# Test markdown")]

        result = coach._copy_to_clipboard(markdowns)

        assert result is True
        assert mock_popen.called

    @patch("subprocess.Popen", side_effect=Exception("Copy failed"))
    def test_copy_to_clipboard_failure(self, mock_popen):
        """Test _copy_to_clipboard handles copy failure."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        markdowns = [("2025-12-20", "# Test markdown")]

        result = coach._copy_to_clipboard(markdowns)

        assert result is False

    def test_detect_session_type_from_markdown_normal(self):
        """Test _detect_session_type_from_markdown returns None for normal workout."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        markdown = "# S072-03 - Morning Tempo\n\nGreat tempo session."

        session_type = coach._detect_session_type_from_markdown(markdown)

        # Normal workouts return None (not "workout")
        assert session_type is None

    def test_detect_session_type_from_markdown_rest(self):
        """Test _detect_session_type_from_markdown detects rest day."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        markdown = "# REPOS - 2025-12-22\n\n[REPOS]"

        session_type = coach._detect_session_type_from_markdown(markdown)

        assert session_type == "rest"

    def test_detect_session_type_from_markdown_cancelled(self):
        """Test _detect_session_type_from_markdown detects cancelled."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        markdown = "# S072-02 - [ANNULÉE]\n\nSession cancelled due to fatigue."

        session_type = coach._detect_session_type_from_markdown(markdown)

        assert session_type == "cancelled"


class TestUIHelpers:
    """Test UI helper methods."""

    @patch("os.system")
    def test_clear_screen(self, mock_system):
        """Test clear_screen calls os.system with clear."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        coach.clear_screen()

        assert mock_system.called
        # Should call with 'clear' on Unix or 'cls' on Windows
        call_arg = mock_system.call_args[0][0]
        assert call_arg in ["clear", "cls"]

    @patch("builtins.print")
    def test_print_header(self, mock_print):
        """Test print_header prints formatted header."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        coach.print_header("Test Title", "Test Subtitle")

        assert mock_print.called
        # Should print title
        call_args_str = str(mock_print.call_args_list)
        assert "Test Title" in call_args_str

    @patch("builtins.print")
    def test_print_separator(self, mock_print):
        """Test print_separator prints line."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        coach.print_separator()

        assert mock_print.called

    @patch("builtins.input", return_value="")
    def test_wait_user(self, mock_input):
        """Test wait_user waits for enter key."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        coach.wait_user("Press enter to continue")

        assert mock_input.called


class TestAnalysisPreparation:
    """Test analysis preparation methods."""

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_step_3_prepare_analysis_clipboard_mode(self, mock_print, mock_subprocess):
        """Test step_3_prepare_analysis with clipboard mode."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.current_provider = "clipboard"

        # Mock subprocess for prepare_analysis and pbpaste
        mock_subprocess.side_effect = [
            Mock(returncode=0),  # prepare_analysis success
            Mock(stdout="- **Nom** : Test Activity\nPrompt content here", returncode=0),  # pbpaste
        ]

        with patch.object(coach, "wait_user"):
            coach.step_3_prepare_analysis()

        assert coach.activity_name == "Test Activity"
        assert mock_subprocess.call_count == 2

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_step_3_prepare_analysis_with_activity_id(self, mock_print, mock_subprocess):
        """Test step_3_prepare_analysis includes activity_id in command."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.current_provider = "clipboard"
        coach.activity_id = "12345"

        mock_subprocess.side_effect = [
            Mock(returncode=0),
            Mock(stdout="- **Nom** : Activity\nPrompt", returncode=0),
        ]

        with patch.object(coach, "wait_user"):
            coach.step_3_prepare_analysis()

        # Verify activity_id was passed to prepare_analysis
        first_call_args = mock_subprocess.call_args_list[0][0][0]
        assert "--activity-id" in first_call_args
        assert "12345" in first_call_args

    @patch("subprocess.run")
    @patch("sys.exit", side_effect=SystemExit)
    @patch("builtins.print")
    def test_step_3_prepare_analysis_error_handling(self, mock_print, mock_exit, mock_subprocess):
        """Test step_3_prepare_analysis handles subprocess errors."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.current_provider = "clipboard"

        # prepare_analysis fails
        mock_subprocess.return_value = Mock(returncode=1)

        # Should exit on error
        try:
            coach.step_3_prepare_analysis()
        except SystemExit:
            pass

        assert mock_exit.called
        mock_exit.assert_called_with(1)

    @patch("builtins.input", return_value="070")
    def test_detect_week_id_user_input(self, mock_input):
        """Test _detect_week_id prompts user when week_id not set."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        week_id = coach._detect_week_id()

        assert week_id == "S070"
        assert mock_input.called

    def test_detect_week_id_already_set(self):
        """Test _detect_week_id uses existing week_id when available."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.week_id = "S065"

        week_id = coach._detect_week_id()

        assert week_id == "S065"

    @patch("builtins.input", return_value="S072")
    def test_detect_week_id_adds_prefix(self, mock_input):
        """Test _detect_week_id handles input with S prefix."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        week_id = coach._detect_week_id()

        assert week_id == "S072"

    @patch("magma_cycling.workflow_coach.get_data_config")
    def test_check_planning_available_exists(self, mock_config):
        """Test _check_planning_available when planning file exists."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.week_id = "S070"

        mock_planning_dir = Mock()
        mock_planning_file = Mock()
        mock_planning_file.exists.return_value = True
        mock_planning_dir.__truediv__ = Mock(return_value=mock_planning_file)

        mock_config.return_value.week_planning_dir = mock_planning_dir

        result = coach._check_planning_available()

        assert result is True

    @patch("magma_cycling.workflow_coach.get_data_config")
    def test_check_planning_available_missing(self, mock_config):
        """Test _check_planning_available when planning file is missing."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.week_id = "S070"

        mock_planning_dir = Mock()
        mock_planning_file = Mock()
        mock_planning_file.exists.return_value = False
        mock_planning_dir.__truediv__ = Mock(return_value=mock_planning_file)

        mock_config.return_value.week_planning_dir = mock_planning_dir

        result = coach._check_planning_available()

        assert result is False

    @patch("builtins.input", side_effect=["X", "Y", "F"])
    @patch("builtins.print")
    def test_ask_fallback_consent_validates_input(self, mock_print, mock_input):
        """Test _ask_fallback_consent validates and retries on invalid input."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        choice = coach._ask_fallback_consent(
            failed_provider="openai", next_provider="anthropic", error_msg="API timeout"
        )

        assert choice == "F"
        assert mock_input.call_count == 3  # Two invalid, one valid

    @patch("builtins.input", return_value="C")
    def test_ask_fallback_consent_clipboard_choice(self, mock_input):
        """Test _ask_fallback_consent accepts clipboard choice."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        choice = coach._ask_fallback_consent(
            failed_provider="openai", next_provider="anthropic", error_msg="API error"
        )

        assert choice == "C"

    @patch("builtins.input", return_value="Q")
    def test_ask_fallback_consent_quit_choice(self, mock_input):
        """Test _ask_fallback_consent accepts quit choice."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        choice = coach._ask_fallback_consent(
            failed_provider="openai", next_provider="anthropic", error_msg="API error"
        )

        assert choice == "Q"


class TestSpecialSessions:
    """Test special sessions handling methods."""

    @patch("magma_cycling.workflow_coach.generate_rest_day_entry")
    @patch("builtins.input", return_value="0")  # Mock menu choice
    @patch("builtins.print")
    def test_show_special_sessions_with_rest_days(self, mock_print, mock_input, mock_generate):
        """Test _show_special_sessions generates rest day markdowns."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.reconciliation = {
            "rest_days": [{"session_id": "S070-01", "name": "Repos", "date": "2026-01-05"}],
            "cancelled": [],
        }

        mock_generate.return_value = "# Repos markdown"

        with patch.object(coach, "_collect_rest_feedback", return_value={"feedback": "Good rest"}):
            with patch.object(coach, "_preview_markdowns"):
                result = coach._show_special_sessions()

        assert mock_generate.called
        call_args = mock_generate.call_args
        assert call_args[1]["session_data"]["session_id"] == "S070-01"
        assert result == "exit_workflow"

    @patch("magma_cycling.workflow_coach.generate_cancelled_session_entry")
    @patch("builtins.input", return_value="0")  # Mock menu choice
    @patch("builtins.print")
    def test_show_special_sessions_with_cancelled(self, mock_print, mock_input, mock_generate):
        """Test _show_special_sessions generates cancelled session markdowns."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.reconciliation = {
            "rest_days": [],
            "cancelled": [
                {
                    "session_id": "S070-02",
                    "name": "Cancelled",
                    "date": "2026-01-06",
                    "cancellation_reason": "Weather",
                }
            ],
        }

        mock_generate.return_value = "# Cancelled markdown"

        with patch.object(coach, "_preview_markdowns"):
            result = coach._show_special_sessions()

        assert mock_generate.called
        call_args = mock_generate.call_args
        assert call_args[1]["session_data"]["session_id"] == "S070-02"
        assert call_args[1]["reason"] == "Weather"
        assert result == "exit_workflow"

    @patch("builtins.print")
    def test_show_special_sessions_empty(self, mock_print):
        """Test _show_special_sessions with no special sessions."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.reconciliation = {"rest_days": [], "cancelled": []}

        coach._show_special_sessions()

        # Should print warning about no special sessions
        call_args_str = str(mock_print.call_args_list)
        assert "Aucune session spéciale" in call_args_str

    def test_show_special_sessions_no_reconciliation(self):
        """Test _show_special_sessions returns early without reconciliation."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.reconciliation = None

        result = coach._show_special_sessions()

        # Should return None early
        assert result is None

    @patch("builtins.print")
    def test_handle_rest_cancellations_no_reconciliation(self, mock_print):
        """Test _handle_rest_cancellations with no reconciliation."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.reconciliation = None

        with patch.object(coach, "wait_user"):
            result = coach._handle_rest_cancellations()

        assert result == "exit"

    @patch("builtins.print")
    def test_handle_rest_cancellations_returns_exit(self, mock_print):
        """Test _handle_rest_cancellations returns exit after processing."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.reconciliation = {"rest_days": [], "cancelled": []}

        with patch.object(coach, "_show_special_sessions", return_value="done"):
            result = coach._handle_rest_cancellations()

        assert result == "exit"

    @patch("builtins.print")
    def test_handle_rest_cancellations_returns_continue(self, mock_print):
        """Test _handle_rest_cancellations returns continue for AI enrichment."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.reconciliation = {"rest_days": [], "cancelled": []}

        with patch.object(coach, "_show_special_sessions", return_value="continue_workflow"):
            result = coach._handle_rest_cancellations()

        assert result == "continue"

    @patch("builtins.print")
    def test_handle_skipped_sessions_empty(self, mock_print):
        """Test _handle_skipped_sessions with empty list."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        with patch.object(coach, "wait_user"):
            result = coach._handle_skipped_sessions([])

        assert result == "exit"

    @patch("builtins.print")
    def test_handle_skipped_sessions_single(self, mock_print):
        """Test _handle_skipped_sessions with single session."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        skipped = [{"planned_name": "S070-01 - Endurance", "planned_date": "2026-01-05"}]

        with patch.object(coach, "_generate_skipped_markdown", return_value="# Skipped"):
            with patch.object(coach, "_preview_markdowns"):
                with patch.object(coach, "_insert_to_history"):
                    with patch(
                        "builtins.input", side_effect=["fatigue", "2", "o"]
                    ):  # reason + menu + confirm
                        result = coach._handle_skipped_sessions(skipped)

        assert result == "exit"

    @patch("builtins.print")
    def test_handle_skipped_sessions_multiple(self, mock_print):
        """Test _handle_skipped_sessions with multiple sessions."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        skipped = [
            {"planned_name": "S070-01 - Endurance", "planned_date": "2026-01-05"},
            {"planned_name": "S070-02 - Intervals", "planned_date": "2026-01-06"},
        ]

        with patch.object(coach, "_generate_skipped_markdown", return_value="# Skipped"):
            with patch.object(coach, "_preview_markdowns"):
                with patch.object(coach, "_insert_to_history"):
                    with patch(
                        "builtins.input", side_effect=["météo", "emploi du temps", "2", "o"]
                    ):  # 2 reasons + menu + confirm
                        result = coach._handle_skipped_sessions(skipped)

        assert result == "exit"

    @patch("builtins.print")
    def test_handle_skipped_sessions_default_reason(self, mock_print):
        """Test _handle_skipped_sessions uses default reason when empty."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        skipped = [{"planned_name": "S070-01", "planned_date": "2026-01-05"}]

        markdown_calls = []

        def capture_markdown_call(session, reason):
            markdown_calls.append(reason)
            return "# Skipped"

        with patch.object(coach, "_generate_skipped_markdown", side_effect=capture_markdown_call):
            with patch.object(coach, "_preview_markdowns"):
                with patch.object(coach, "_insert_to_history"):
                    with patch(
                        "builtins.input", side_effect=["", "2", "o"]
                    ):  # empty reason + menu + confirm
                        result = coach._handle_skipped_sessions(skipped)

        # Should use "Non spécifié" as default
        assert "Non spécifié" in markdown_calls
        assert result == "exit"

    @patch("builtins.print")
    def test_handle_batch_all_in_development(self, mock_print):
        """Test _handle_batch_all shows development message."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        with patch.object(coach, "wait_user"):
            result = coach._handle_batch_all()

        assert result == "exit"
        # Should mention it's in development
        call_args_str = str(mock_print.call_args_list)
        assert "développement" in call_args_str.lower()


class TestIntervalsAPI:
    """Test Intervals.icu API integration methods."""

    def test_get_workout_id_intervals_success(self):
        """Test _get_workout_id_intervals finds workout ID."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        # Mock API client (Sprint R9.B Phase 2 - centralized API)
        mock_client = Mock()
        mock_client.get_events.return_value = [
            {"id": "12345", "category": "WORKOUT", "date": "2026-01-05"},
            {"id": "67890", "category": "NOTE", "date": "2026-01-05"},
        ]

        with patch.object(coach, "_get_api", return_value=mock_client):
            workout_id = coach._get_workout_id_intervals("2026-01-05")

        assert workout_id == "12345"
        mock_client.get_events.assert_called_once_with(oldest="2026-01-05", newest="2026-01-05")

    def test_get_workout_id_intervals_not_found(self):
        """Test _get_workout_id_intervals when no workout exists."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        # Mock API client (Sprint R9.B Phase 2 - centralized API)
        mock_client = Mock()
        mock_client.get_events.return_value = [
            {"id": "67890", "category": "NOTE", "date": "2026-01-05"}
        ]

        with patch.object(coach, "_get_api", return_value=mock_client):
            workout_id = coach._get_workout_id_intervals("2026-01-05")

        assert workout_id is None

    @patch("builtins.print")
    def test_get_workout_id_intervals_no_credentials(self, mock_print):
        """Test _get_workout_id_intervals with missing credentials."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        # Mock _get_api to raise ValueError (Sprint R9.B Phase 2 - centralized API)
        with patch.object(coach, "_get_api", side_effect=ValueError("Credentials not configured")):
            workout_id = coach._get_workout_id_intervals("2026-01-05")

        assert workout_id is None

    def test_delete_workout_intervals_success(self):
        """Test _delete_workout_intervals succeeds."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        # Mock API client (Sprint R9.B Phase 2 - centralized API)
        mock_client = Mock()
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_client.session.delete.return_value = mock_response
        mock_client.BASE_URL = "https://intervals.icu/api/v1"
        mock_client.athlete_id = "athlete123"

        with patch.object(coach, "_get_api", return_value=mock_client):
            result = coach._delete_workout_intervals("workout789")

        assert result is True
        mock_client.session.delete.assert_called_once()

    @patch("builtins.print")
    def test_delete_workout_intervals_error(self, mock_print):
        """Test _delete_workout_intervals handles errors."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        # Mock API client with error (Sprint R9.B Phase 2 - centralized API)
        mock_client = Mock()
        mock_client.session.delete.side_effect = Exception("API error")
        mock_client.BASE_URL = "https://intervals.icu/api/v1"
        mock_client.athlete_id = "athlete123"

        with patch.object(coach, "_get_api", return_value=mock_client):
            result = coach._delete_workout_intervals("workout789")

        assert result is False

    def test_upload_workout_intervals_success(self):
        """Test _upload_workout_intervals succeeds."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        # Mock API client (Sprint R9.B Phase 2 - centralized API)
        mock_client = Mock()
        mock_client.create_event.return_value = {"id": "new_workout_123"}

        with patch.object(coach, "_get_api", return_value=mock_client):
            result = coach._upload_workout_intervals(
                date="2026-01-05", code="S070-03-REC-V001", structure="2x20 @ Z3"
            )

        assert result is True
        mock_client.create_event.assert_called_once()
        call_args = mock_client.create_event.call_args[0][0]
        assert call_args["category"] == "WORKOUT"
        assert call_args["name"] == "S070-03-REC-V001"
        assert call_args["description"] == "2x20 @ Z3"

    @patch("builtins.print")
    def test_upload_workout_intervals_invalid_format(self, mock_print):
        """Test _upload_workout_intervals with API error."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        # Mock API client with error (Sprint R9.B Phase 2 - centralized API)
        mock_client = Mock()
        mock_client.create_event.side_effect = Exception("Invalid format")

        with patch.object(coach, "_get_api", return_value=mock_client):
            result = coach._upload_workout_intervals(
                date="2026-01-05", code="S070-03", structure="invalid"
            )

        assert result is False

    @patch("magma_cycling.workflow_coach.get_data_config")
    @patch("requests.post")
    def test_post_analysis_to_intervals_success(self, mock_post, mock_config):
        """Test _post_analysis_to_intervals posts successfully."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.activity_id = "act123"
        coach.analysis_result = "Great workout! Power was consistent throughout the intervals. Good recovery between sets."

        mock_config_obj = Mock()
        mock_config_obj.get.side_effect = lambda key: {
            "athlete_id": "athlete123",
            "api_key": "key456",
        }.get(key)
        mock_config.return_value = mock_config_obj

        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = coach._post_analysis_to_intervals()

        assert result is True
        assert mock_post.called
        call_args = mock_post.call_args
        assert "act123" in call_args[0][0]  # URL contains activity_id
        assert "Great workout" in call_args[1]["json"]["note"]

    @patch("magma_cycling.workflow_coach.get_data_config")
    @patch("requests.post")
    def test_post_analysis_to_intervals_no_activity_id(self, mock_post, mock_config):
        """Test _post_analysis_to_intervals without activity_id."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.activity_id = None

        result = coach._post_analysis_to_intervals()

        assert result is False
        assert not mock_post.called

    @patch("magma_cycling.workflow_coach.get_data_config")
    @patch("requests.post")
    def test_post_analysis_to_intervals_error(self, mock_post, mock_config):
        """Test _post_analysis_to_intervals handles API errors."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.activity_id = "act123"
        coach.analysis_result = "Analysis text here with enough content to pass the length check requirement of 50 characters."

        mock_config_obj = Mock()
        mock_config_obj.get.side_effect = lambda key: {
            "athlete_id": "athlete123",
            "api_key": "key456",
        }.get(key)
        mock_config.return_value = mock_config_obj

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        mock_post.return_value = mock_response

        result = coach._post_analysis_to_intervals()

        assert result is False


class TestCredentialsLoadingAdvanced:
    """Test load_credentials with config file scenarios."""

    @patch("pathlib.Path.exists", return_value=True)
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"athlete_id": "i999", "api_key": "secret999"}',
    )
    @patch("json.load")
    def test_load_credentials_from_config_file(self, mock_json_load, mock_file, mock_exists):
        """Test load_credentials loads from config file when it exists."""
        # Mock json.load to return config data
        mock_json_load.return_value = {"athlete_id": "i999", "api_key": "secret999"}

        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        athlete_id, api_key = coach.load_credentials()

        assert athlete_id == "i999"
        assert api_key == "secret999"

    @patch("magma_cycling.config.get_intervals_config")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data='{"invalid": "data"}')
    @patch("json.load")
    @patch.dict(
        "os.environ",
        {"VITE_INTERVALS_ATHLETE_ID": "i123", "VITE_INTERVALS_API_KEY": "key123"},
        clear=True,
    )
    def test_load_credentials_config_file_missing_keys(
        self, mock_json_load, mock_file, mock_exists, mock_get_config
    ):
        """Test load_credentials falls back to env when config file has missing keys."""
        # Config file exists but doesn't have required keys
        mock_json_load.return_value = {"invalid": "data"}

        # Mock IntervalsConfig to return test credentials
        mock_intervals_config = Mock()
        mock_intervals_config.is_configured.return_value = True
        mock_intervals_config.athlete_id = "i123"
        mock_intervals_config.api_key = "key123"
        mock_get_config.return_value = mock_intervals_config

        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        athlete_id, api_key = coach.load_credentials()

        # Should fall back to env vars
        assert athlete_id == "i123"
        assert api_key == "key123"

    @patch("magma_cycling.config.load_json_config", return_value=None)
    @patch("magma_cycling.config.get_intervals_config")
    def test_load_credentials_config_file_read_error(self, mock_get_config, mock_load_json):
        """Test load_credentials handles config file read errors."""
        # load_json_config returns None on error (logs warning internally)
        # Mock IntervalsConfig to return env var credentials
        mock_intervals_config = Mock()
        mock_intervals_config.is_configured.return_value = True
        mock_intervals_config.athlete_id = "i456"
        mock_intervals_config.api_key = "key456"
        mock_get_config.return_value = mock_intervals_config

        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        athlete_id, api_key = coach.load_credentials()

        # Should fall back to env vars from centralized config
        assert athlete_id == "i456"
        assert api_key == "key456"


class TestWorkoutTemplatesLoading:
    """Test load_workout_templates method."""

    def test_load_workout_templates_directory_not_exists(self):
        """Test load_workout_templates when templates directory doesn't exist."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, servo_mode=True)

        # Should return empty dict (actual directory might exist, but method handles gracefully)
        assert isinstance(coach.workout_templates, dict)

    @patch("pathlib.Path.glob")
    @patch("pathlib.Path.exists", return_value=True)
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"id": "recovery_30", "name": "Recovery 30min", "tss": 30}',
    )
    @patch("json.load")
    @patch("builtins.print")
    def test_load_workout_templates_success(
        self, mock_print, mock_json_load, mock_file, mock_exists, mock_glob
    ):
        """Test load_workout_templates successfully loads templates."""
        # Mock template file
        mock_template_path = Mock()
        mock_template_path.name = "recovery_30.json"
        mock_glob.return_value = [mock_template_path]

        mock_json_load.return_value = {
            "id": "recovery_30",
            "name": "Recovery 30min",
            "tss": 30,
        }

        # Need to mock Path.exists for specific paths
        def exists_side_effect():
            # Return True for templates_dir check
            return True

        with patch("pathlib.Path.exists", side_effect=exists_side_effect):
            coach = WorkflowCoach(skip_feedback=True, skip_git=True, servo_mode=True)

        # Verify template was loaded
        assert "recovery_30" in coach.workout_templates
        assert coach.workout_templates["recovery_30"]["name"] == "Recovery 30min"

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.glob")
    @patch("builtins.open", side_effect=Exception("JSON parse error"))
    @patch("builtins.print")
    def test_load_workout_templates_json_error(self, mock_print, mock_file, mock_glob, mock_exists):
        """Test load_workout_templates handles JSON parsing errors."""
        # Mock template file that will cause error
        mock_template_path = Mock()
        mock_template_path.name = "invalid.json"
        mock_glob.return_value = [mock_template_path]

        coach = WorkflowCoach(skip_feedback=True, skip_git=True, servo_mode=True)

        # Should handle error gracefully and return empty dict
        assert coach.workout_templates == {}
        # Check error message was printed
        assert any("Erreur" in str(call) for call in mock_print.call_args_list)


class TestRemainingSessionsLoading:
    """Test load_remaining_sessions method."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Mock Control Tower to use tmp_path for planning."""
        from magma_cycling.planning.control_tower import planning_tower

        # Save original path
        original_planning_dir = planning_tower.planning_dir

        # Override with tmp_path
        planning_tower.planning_dir = tmp_path
        planning_tower.backup_system.planning_dir = tmp_path

        # Create required files for DataRepoConfig validation
        workouts_history = tmp_path / "workouts-history.md"
        workouts_history.touch()

        yield tmp_path

        # Restore original path
        planning_tower.planning_dir = original_planning_dir
        planning_tower.backup_system.planning_dir = original_planning_dir

    @patch("builtins.print")
    def test_load_remaining_sessions_file_not_found(self, mock_print, tmp_path, mock_config):
        """Test load_remaining_sessions when planning file doesn't exist."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        remaining = coach.load_remaining_sessions("S099")

        assert remaining == []
        # Should print warning
        assert mock_print.called

    @patch("magma_cycling.workflow_coach.datetime")
    def test_load_remaining_sessions_success(self, mock_dt, tmp_path, mock_config):
        """Test load_remaining_sessions successfully loads future sessions."""

        # Fix "today" to a known Wednesday so dates never expire
        # 2026-02-25 is a Wednesday; week: Mon 2026-02-23 → Sun 2026-03-01
        fixed_today = date(2026, 2, 25)
        mock_dt.now.return_value.date.return_value = fixed_today

        week_start = date(2026, 2, 23)  # Monday
        week_end = date(2026, 3, 1)  # Sunday
        past_date = "2026-02-24"  # Tuesday  – before fixed_today
        future_date = "2026-02-27"  # Friday   – after fixed_today

        planning_data = {
            "week_id": "S072",
            "start_date": week_start.strftime("%Y-%m-%d"),
            "end_date": week_end.strftime("%Y-%m-%d"),
            "created_at": "2025-12-01T20:00:00Z",
            "last_updated": "2025-12-01T20:00:00Z",
            "version": 1,
            "athlete_id": "iXXXXXX",
            "tss_target": 350,
            "planned_sessions": [
                {
                    "session_id": "S072-01",
                    "date": past_date,
                    "name": "Past",
                    "type": "TEMPO",
                    "version": "V001",
                    "tss_planned": 60,
                    "duration_min": 60,
                    "description": "Past session",
                    "status": "completed",
                    "intervals_id": None,
                    "description_hash": None,
                },
                {
                    "session_id": "S072-03",
                    "date": future_date,
                    "name": "Future",
                    "type": "VO2",
                    "version": "V001",
                    "tss_planned": 75,
                    "duration_min": 65,
                    "description": "Future session",
                    "status": "planned",
                    "intervals_id": None,
                    "description_hash": None,
                },
            ],
        }

        planning_file = tmp_path / "week_planning_S072.json"
        with open(planning_file, "w", encoding="utf-8") as f:
            json.dump(planning_data, f, indent=2)

        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        remaining = coach.load_remaining_sessions("S072")

        # Should only return the future session
        assert len(remaining) == 1
        assert remaining[0]["date"] == future_date
        assert remaining[0]["name"] == "Future"

    @patch("magma_cycling.workflow_coach.get_data_config")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", side_effect=Exception("Read error"))
    @patch("builtins.print")
    def test_load_remaining_sessions_read_error(
        self, mock_print, mock_file, mock_exists, mock_config
    ):
        """Test load_remaining_sessions handles file read errors."""
        mock_config_obj = Mock()
        mock_config_obj.week_planning_dir = Path("/fake/path")
        mock_config.return_value = mock_config_obj

        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        remaining = coach.load_remaining_sessions("S072")

        assert remaining == []
        # Should print error message


class TestSummarizeDetectedGaps:
    """Test WorkflowCoach._display_gaps_summary — pure display function."""

    def test_empty_gaps_returns_zero(self, capsys):
        """No gaps → prints message and returns 0."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        gaps_data = {"unanalyzed": [], "skipped": [], "rest_days": [], "cancelled": []}
        result = coach._display_gaps_summary(gaps_data)
        assert result == 0
        assert "Aucun gap" in capsys.readouterr().out

    def test_with_unanalyzed_activities(self, capsys):
        """Unanalyzed activities shown, returns count."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        gaps_data = {
            "unanalyzed": [
                {
                    "start_date_local": "2026-02-23T18:00:00",
                    "name": "S082-01-END-EnduranceBase-V001",
                }
            ],
            "skipped": [],
            "rest_days": [],
            "cancelled": [],
        }
        result = coach._display_gaps_summary(gaps_data)
        assert result == 1

    def test_with_more_than_3_unanalyzed(self, capsys):
        """More than 3 unanalyzed → shows '+N autres' truncation."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        activities = [
            {"start_date_local": f"2026-02-2{i}T18:00:00", "name": f"Séance {i}"} for i in range(5)
        ]
        gaps_data = {
            "unanalyzed": activities,
            "skipped": [],
            "rest_days": [],
            "cancelled": [],
        }
        result = coach._display_gaps_summary(gaps_data)
        assert result == 5
        assert "autres" in capsys.readouterr().out

    def test_with_rest_days(self, capsys):
        """Rest days listed."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        gaps_data = {
            "unanalyzed": [],
            "skipped": [],
            "rest_days": [
                {"date": "2026-02-23", "session_id": "S082-07", "rest_reason": "Repos planifié"}
            ],
            "cancelled": [],
        }
        result = coach._display_gaps_summary(gaps_data)
        assert result == 1

    def test_with_cancelled_sessions(self, capsys):
        """Cancelled sessions listed."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        gaps_data = {
            "unanalyzed": [],
            "skipped": [],
            "rest_days": [],
            "cancelled": [
                {
                    "date": "2026-02-22",
                    "session_id": "S082-06",
                    "cancellation_reason": "Maladie",
                }
            ],
        }
        result = coach._display_gaps_summary(gaps_data)
        assert result == 1

    def test_with_skipped_sessions(self, capsys):
        """Skipped sessions listed."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        gaps_data = {
            "unanalyzed": [],
            "skipped": [
                {
                    "planned_date": "2026-02-21",
                    "planned_name": "Tempo Progression",
                    "planned_tss": 68,
                    "days_ago": 2,
                }
            ],
            "rest_days": [],
            "cancelled": [],
        }
        result = coach._display_gaps_summary(gaps_data)
        assert result == 1

    def test_total_is_sum_of_all_types(self, capsys):
        """Total = unanalyzed + skipped + rest_days + cancelled."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        gaps_data = {
            "unanalyzed": [{"start_date_local": "2026-02-23T18:00:00", "name": "S1"}],
            "skipped": [
                {
                    "planned_date": "2026-02-22",
                    "planned_name": "S2",
                    "planned_tss": 50,
                    "days_ago": 1,
                }
            ],
            "rest_days": [{"date": "2026-02-21", "session_id": "R1", "rest_reason": "Repos"}],
            "cancelled": [
                {"date": "2026-02-20", "session_id": "C1", "cancellation_reason": "Annulé"}
            ],
        }
        result = coach._display_gaps_summary(gaps_data)
        assert result == 4


class TestPromptUserChoiceAutoMode:
    """Test WorkflowCoach._prompt_user_choice in auto_mode."""

    def test_executed_only_auto_returns_single(self):
        """auto_mode with executed activities → 'single_executed'."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, auto_mode=True)
        gaps_data = {
            "unanalyzed": [{"start_date_local": "2026-02-23T18:00:00", "name": "S1"}],
            "skipped": [],
            "rest_days": [],
            "cancelled": [],
        }
        result = coach._prompt_user_choice(gaps_data)
        assert result == "single_executed"

    def test_rest_only_auto_returns_batch_rest(self):
        """auto_mode with only rest days → no option [1], returns 'exit'."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, auto_mode=True)
        gaps_data = {
            "unanalyzed": [],
            "skipped": [],
            "rest_days": [{"date": "2026-02-22", "session_id": "R1", "rest_reason": "Repos"}],
            "cancelled": [],
        }
        result = coach._prompt_user_choice(gaps_data)
        # auto_mode picks "1" which maps to batch_rest_cancelled (first option built)
        assert result in ("batch_rest_cancelled", "exit")

    def test_skipped_only_auto(self):
        """auto_mode with only skipped → option [1] maps to batch_skipped."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, auto_mode=True)
        gaps_data = {
            "unanalyzed": [],
            "skipped": [
                {
                    "planned_date": "2026-02-22",
                    "planned_name": "Séance sautée",
                    "planned_tss": 50,
                    "days_ago": 1,
                }
            ],
            "rest_days": [],
            "cancelled": [],
        }
        result = coach._prompt_user_choice(gaps_data)
        # Option [1] maps to batch_skipped when only skipped
        assert result in ("batch_skipped", "exit")

    def test_mixed_auto_has_batch_all_option(self):
        """auto_mode with executed + rest → 'single_executed' (first option)."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, auto_mode=True)
        gaps_data = {
            "unanalyzed": [{"start_date_local": "2026-02-23T18:00:00", "name": "S1"}],
            "skipped": [],
            "rest_days": [{"date": "2026-02-22", "session_id": "R1", "rest_reason": "Repos"}],
            "cancelled": [],
        }
        result = coach._prompt_user_choice(gaps_data)
        assert result == "single_executed"


class TestWorkflowCoachInit:
    """Test __init__ branches not yet covered."""

    def test_init_with_explicit_provider(self):
        """Explicit valid provider specified → used directly."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, provider="clipboard")
        assert coach.current_provider == "clipboard"

    def test_init_auto_mode_flag_stored(self):
        """auto_mode=True stored on instance."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, auto_mode=True)
        assert coach.auto_mode is True


class TestApplyLightenAutoMode:
    """Test WorkflowCoach._apply_lighten in auto/non-interactive mode."""

    @pytest.fixture
    def coach_with_templates(self):
        """WorkflowCoach with auto_mode=True and a fake workout template."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, auto_mode=True)
        coach.workout_templates = {
            "RECUP_COURTE": {
                "name": "Récupération Courte",
                "tss": 25,
                "duration_minutes": 45,
                "type": "RECUP",
                "description": "Récupération active courte",
                "workout_code_pattern": "{week_id}-{day_num}-REC-RecuperationCourte-V001",
                "intervals_icu_format": {},
            }
        }
        return coach

    def test_auto_mode_stores_recommendation(self, coach_with_templates):
        """In auto_mode, _apply_lighten stores recommendation without applying."""
        mod = {
            "template_id": "RECUP_COURTE",
            "target_date": "2026-02-25",
            "reason": "Fatigue élevée",
            "current_workout": {"code": "S082-03-INT-SweetSpot-V001"},
        }
        coach_with_templates._apply_lighten(mod, week_id="S082")

        assert hasattr(coach_with_templates, "_servo_recommendations")
        assert len(coach_with_templates._servo_recommendations) == 1
        rec = coach_with_templates._servo_recommendations[0]
        assert rec["date"] == "2026-02-25"
        assert rec["template"] == "Récupération Courte"
        assert rec["tss"] == 25
        assert rec["status"] == "pending_manual_application"

    def test_auto_mode_accumulates_recommendations(self, coach_with_templates):
        """Multiple _apply_lighten calls accumulate recommendations."""
        mod = {
            "template_id": "RECUP_COURTE",
            "target_date": "2026-02-25",
            "reason": "Fatigue",
            "current_workout": {},
        }
        coach_with_templates._apply_lighten(mod, week_id="S082")
        coach_with_templates._apply_lighten(mod, week_id="S082")

        assert len(coach_with_templates._servo_recommendations) == 2

    def test_unknown_template_no_crash(self, coach_with_templates):
        """Unknown template_id → returns early without crashing."""
        mod = {
            "template_id": "TEMPLATE_INEXISTANT",
            "target_date": "2026-02-25",
            "reason": "Test",
            "current_workout": {},
        }
        coach_with_templates._apply_lighten(mod, week_id="S082")
        # No _servo_recommendations created (early return)
        assert not hasattr(coach_with_templates, "_servo_recommendations")


class TestInitFallback:
    """Test WorkflowCoach.__init__ fallback when get_data_config raises FileNotFoundError."""

    def test_config_not_found_uses_legacy_fallback(self):
        """When get_data_config raises FileNotFoundError, falls back to project_root/logs."""
        with patch("magma_cycling.config.get_data_config") as mock_config:
            mock_config.side_effect = FileNotFoundError("config not found")
            coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        assert coach.config is None
        assert coach.data_repo_path.name == "logs"


class TestGetApiMethod:
    """Test WorkflowCoach._get_api() lazy initialization."""

    def test_get_api_creates_client_on_first_call(self):
        """_get_api() creates API client when self.api is None."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        mock_api = Mock()
        with patch("magma_cycling.config.create_intervals_client", return_value=mock_api):
            result = coach._get_api()
        assert result is mock_api
        assert coach.api is mock_api

    def test_get_api_reuses_existing_client(self):
        """_get_api() returns existing api without recreating it."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        existing_api = Mock()
        coach.api = existing_api
        result = coach._get_api()
        assert result is existing_api

    def test_get_api_raises_value_error_on_missing_credentials(self):
        """_get_api() raises ValueError when credentials not configured."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        with patch(
            "magma_cycling.config.create_intervals_client",
            side_effect=ValueError("credentials not found"),
        ):
            with pytest.raises(ValueError):
                coach._get_api()


class TestLoadWorkoutTemplatesEdgeCases:
    """Test load_workout_templates edge cases."""

    def test_missing_templates_dir_returns_empty(self, tmp_path):
        """Returns empty dict when templates dir does not exist."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.project_root = tmp_path  # No data/workout_templates subdir
        result = coach.load_workout_templates()
        assert result == {}

    def test_existing_empty_dir_returns_empty(self, tmp_path):
        """Returns empty dict when templates dir exists but has no JSON files."""
        templates_dir = tmp_path / "data" / "workout_templates"
        templates_dir.mkdir(parents=True)
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.project_root = tmp_path
        result = coach.load_workout_templates()
        assert result == {}


class TestUpdatePlanningJsonErrors:
    """Test _update_planning_json error paths."""

    def test_session_not_found_returns_false(self):
        """Returns False when no session matches the given date."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        mock_plan = Mock()
        mock_plan.planned_sessions = []
        with patch("magma_cycling.workflow_coach.planning_tower") as mock_tower:
            mock_tower.modify_week.return_value.__enter__ = Mock(return_value=mock_plan)
            mock_tower.modify_week.return_value.__exit__ = Mock(return_value=False)
            result = coach._update_planning_json(
                week_id="S082",
                date="2026-02-25",
                new_workout={"code": "X", "type": "RECUP", "tss": 25, "description": "Test"},
                old_workout="old",
                reason="test",
            )
        assert result is False

    def test_file_not_found_returns_false(self):
        """Returns False when planning file does not exist."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        with patch("magma_cycling.workflow_coach.planning_tower") as mock_tower:
            mock_tower.modify_week.side_effect = FileNotFoundError("no file")
            result = coach._update_planning_json(
                week_id="S999",
                date="2026-02-25",
                new_workout={"code": "X", "type": "RECUP", "tss": 25, "description": "Test"},
                old_workout="old",
                reason="test",
            )
        assert result is False

    def test_generic_exception_returns_false(self):
        """Returns False on unexpected exception."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        with patch("magma_cycling.workflow_coach.planning_tower") as mock_tower:
            mock_tower.modify_week.side_effect = RuntimeError("unexpected")
            result = coach._update_planning_json(
                week_id="S082",
                date="2026-02-25",
                new_workout={"code": "X", "type": "RECUP", "tss": 25, "description": "Test"},
                old_workout="old",
                reason="test",
            )
        assert result is False


class TestDetectSkippedSessionsException:
    """Test _detect_skipped_sessions exception path."""

    def test_exception_returns_none(self):
        """Returns None when PlannedSessionsChecker raises an exception."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        with patch(
            "magma_cycling.workflow_coach.PlannedSessionsChecker",
            side_effect=Exception("API error"),
        ):
            result = coach._detect_skipped_sessions(
                athlete_id="AT1", api_key="key", oldest_date="2026-02-17", newest_date="2026-02-24"
            )
        assert result is None


class TestDetectRestCancelledNoWeekId:
    """Test _detect_rest_and_cancelled_sessions with no week_id."""

    def test_no_week_id_returns_empty_lists(self):
        """Returns ([], []) immediately when week_id is not set."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.week_id = None
        rest, cancelled = coach._detect_rest_and_cancelled_sessions()
        assert rest == []
        assert cancelled == []

    def test_week_id_set_planning_file_missing_returns_empty(self, tmp_path):
        """Returns ([], []) when planning file does not exist."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.week_id = "S999"
        mock_cfg = Mock()
        mock_cfg.week_planning_dir = tmp_path  # No planning file here
        with patch("magma_cycling.workflow_coach.get_data_config", return_value=mock_cfg):
            rest, cancelled = coach._detect_rest_and_cancelled_sessions()
        assert rest == []
        assert cancelled == []


class TestGenerateSkippedMarkdownFormat:
    """Test _generate_skipped_markdown session_id extraction."""

    def test_planned_name_without_space_dash_separator(self):
        """planned_name without ' - ' uses split('-') fallback."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        skipped = {
            "planned_name": "S082-05-TEC-TechniqueCadence-V001",
            "planned_date": "2026-02-20",
        }
        markdown = coach._generate_skipped_markdown(skipped, "fatigue")
        assert "S082-05" in markdown

    def test_planned_name_with_space_dash_separator(self):
        """planned_name with ' - ' uses split(' - ')[0]."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        skipped = {"planned_name": "S082-05 - Technique Cadence", "planned_date": "2026-02-20"}
        markdown = coach._generate_skipped_markdown(skipped, "fatigue")
        assert "S082-05" in markdown


class TestStep1bWithActivityId:
    """Test step_1b_detect_all_gaps early return when activity_id is set."""

    def test_activity_id_returns_single_executed(self):
        """When activity_id is set, returns ('single_executed', empty_gaps) immediately."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, activity_id="i12345")
        choice, gaps_data = coach.step_1b_detect_all_gaps()
        assert choice == "single_executed"
        assert gaps_data == {"unanalyzed": [], "skipped": [], "rest_days": [], "cancelled": []}


class TestRunMethod:
    """Test WorkflowCoach.run() with mocked steps — covers main loop branches."""

    def test_run_exits_immediately_on_exit_choice(self):
        """run() exits cleanly when step_1b returns 'exit' on first call."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, auto_mode=True)
        gaps_data = {"unanalyzed": [], "skipped": [], "rest_days": [], "cancelled": []}
        with (
            patch.object(coach, "step_1_welcome"),
            patch.object(coach, "step_1b_detect_all_gaps", return_value=("exit", gaps_data)),
        ):
            coach.run()  # Must complete without raising

    def test_run_breaks_on_unknown_choice(self):
        """run() breaks safely on unrecognised choice."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, auto_mode=True)
        gaps_data = {"unanalyzed": [], "skipped": [], "rest_days": [], "cancelled": []}
        with (
            patch.object(coach, "step_1_welcome"),
            patch.object(coach, "step_1b_detect_all_gaps", return_value=("unknown_xyz", gaps_data)),
        ):
            coach.run()

    def test_run_single_executed_then_exit(self):
        """run() processes single_executed branch then exits on next iteration."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, auto_mode=True)
        gaps_data = {
            "unanalyzed": [{"id": "act1", "start_date_local": "2026-02-24T10:00:00"}],
            "skipped": [],
            "rest_days": [],
            "cancelled": [],
        }
        empty_gaps = {"unanalyzed": [], "skipped": [], "rest_days": [], "cancelled": []}
        call_count = 0

        def mock_step_1b():
            nonlocal call_count
            call_count += 1
            return ("single_executed", gaps_data) if call_count == 1 else ("exit", empty_gaps)

        with (
            patch.object(coach, "step_1_welcome"),
            patch.object(coach, "step_1b_detect_all_gaps", side_effect=mock_step_1b),
            patch.object(coach, "step_2_collect_feedback"),
            patch.object(coach, "step_3_prepare_analysis"),
            patch.object(coach, "step_4_paste_prompt"),
            patch.object(coach, "step_4b_display_analysis"),
            patch.object(coach, "step_5_validate_analysis"),
            patch.object(coach, "step_6_insert_analysis"),
            patch.object(coach, "step_7_git_commit"),
            patch.object(coach, "show_summary"),
        ):
            coach.run()

        assert call_count == 2

    def test_run_same_gaps_twice_breaks_with_all_treated_message(self, capsys):
        """run() breaks when two consecutive gap signatures are identical."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, auto_mode=True)
        gaps_data = {
            "unanalyzed": [{"id": "act1", "start_date_local": "2026-02-24T10:00:00"}],
            "skipped": [],
            "rest_days": [],
            "cancelled": [],
        }
        call_count = 0

        def mock_step_1b():
            nonlocal call_count
            call_count += 1
            # Always return same non-empty gaps → same signature → break
            return ("single_executed", gaps_data) if call_count == 1 else ("exit", gaps_data)

        with (
            patch.object(coach, "step_1_welcome"),
            patch.object(coach, "step_1b_detect_all_gaps", side_effect=mock_step_1b),
            patch.object(coach, "step_2_collect_feedback"),
            patch.object(coach, "step_3_prepare_analysis"),
            patch.object(coach, "step_4_paste_prompt"),
            patch.object(coach, "step_4b_display_analysis"),
            patch.object(coach, "step_5_validate_analysis"),
            patch.object(coach, "step_6_insert_analysis"),
            patch.object(coach, "step_7_git_commit"),
            patch.object(coach, "show_summary"),
        ):
            coach.run()

        captured = capsys.readouterr()
        assert "TOUS LES GAPS TRAITÉS" in captured.out

    def test_run_batch_rest_cancelled_exit(self):
        """run() processes batch_rest_cancelled branch when _handle_rest_cancellations returns 'exit'."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, auto_mode=True)
        gaps_data = {
            "unanalyzed": [],
            "skipped": [],
            "rest_days": [{"session_id": "S082-R1", "date": "2026-02-24"}],
            "cancelled": [],
        }
        empty_gaps = {"unanalyzed": [], "skipped": [], "rest_days": [], "cancelled": []}
        call_count = 0

        def mock_step_1b():
            nonlocal call_count
            call_count += 1
            return ("batch_rest_cancelled", gaps_data) if call_count == 1 else ("exit", empty_gaps)

        with (
            patch.object(coach, "step_1_welcome"),
            patch.object(coach, "step_1b_detect_all_gaps", side_effect=mock_step_1b),
            patch.object(coach, "_handle_rest_cancellations", return_value="exit"),
        ):
            coach.run()

        assert call_count == 2

    def test_run_batch_skipped_exit(self):
        """run() processes batch_skipped branch when _handle_skipped_sessions returns 'exit'."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, auto_mode=True)
        gaps_data = {
            "unanalyzed": [],
            "skipped": [{"planned_name": "S082-05 - TEC", "planned_date": "2026-02-20"}],
            "rest_days": [],
            "cancelled": [],
        }
        empty_gaps = {"unanalyzed": [], "skipped": [], "rest_days": [], "cancelled": []}
        call_count = 0

        def mock_step_1b():
            nonlocal call_count
            call_count += 1
            return ("batch_skipped", gaps_data) if call_count == 1 else ("exit", empty_gaps)

        with (
            patch.object(coach, "step_1_welcome"),
            patch.object(coach, "step_1b_detect_all_gaps", side_effect=mock_step_1b),
            patch.object(coach, "_handle_skipped_sessions", return_value="exit"),
        ):
            coach.run()

        assert call_count == 2

    def test_run_batch_rest_cancelled_continue(self):
        """run() processes batch_rest_cancelled 'continue' branch (enrichissement IA)."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, auto_mode=True)
        gaps_data = {
            "unanalyzed": [],
            "skipped": [],
            "rest_days": [{"session_id": "S082-R1", "date": "2026-02-24"}],
            "cancelled": [],
        }
        empty_gaps = {"unanalyzed": [], "skipped": [], "rest_days": [], "cancelled": []}
        call_count = 0

        def mock_step_1b():
            nonlocal call_count
            call_count += 1
            return ("batch_rest_cancelled", gaps_data) if call_count == 1 else ("exit", empty_gaps)

        with (
            patch.object(coach, "step_1_welcome"),
            patch.object(coach, "step_1b_detect_all_gaps", side_effect=mock_step_1b),
            patch.object(coach, "_handle_rest_cancellations", return_value="continue"),
            patch.object(coach, "step_4b_display_analysis"),
            patch.object(coach, "step_5_validate_analysis"),
            patch.object(coach, "step_6_insert_analysis"),
            patch.object(coach, "step_7_git_commit"),
            patch.object(coach, "show_summary"),
        ):
            coach.run()

        assert call_count == 2

    def test_run_batch_skipped_continue(self):
        """run() processes batch_skipped 'continue' branch (enrichissement IA)."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, auto_mode=True)
        gaps_data = {
            "unanalyzed": [],
            "skipped": [{"planned_name": "S082-05 - TEC", "planned_date": "2026-02-20"}],
            "rest_days": [],
            "cancelled": [],
        }
        empty_gaps = {"unanalyzed": [], "skipped": [], "rest_days": [], "cancelled": []}
        call_count = 0

        def mock_step_1b():
            nonlocal call_count
            call_count += 1
            return ("batch_skipped", gaps_data) if call_count == 1 else ("exit", empty_gaps)

        with (
            patch.object(coach, "step_1_welcome"),
            patch.object(coach, "step_1b_detect_all_gaps", side_effect=mock_step_1b),
            patch.object(coach, "_handle_skipped_sessions", return_value="continue"),
            patch.object(coach, "step_4b_display_analysis"),
            patch.object(coach, "step_5_validate_analysis"),
            patch.object(coach, "step_6_insert_analysis"),
            patch.object(coach, "step_7_git_commit"),
            patch.object(coach, "show_summary"),
        ):
            coach.run()

        assert call_count == 2

    def test_run_batch_all_calls_handle_batch_all(self):
        """run() calls _handle_batch_all on 'batch_all' choice."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, auto_mode=True)
        gaps_data = {"unanalyzed": [], "skipped": [], "rest_days": [], "cancelled": []}
        empty_gaps = {"unanalyzed": [], "skipped": [], "rest_days": [], "cancelled": []}
        call_count = 0

        def mock_step_1b():
            nonlocal call_count
            call_count += 1
            return ("batch_all", gaps_data) if call_count == 1 else ("exit", empty_gaps)

        mock_batch_all = Mock()
        with (
            patch.object(coach, "step_1_welcome"),
            patch.object(coach, "step_1b_detect_all_gaps", side_effect=mock_step_1b),
            patch.object(coach, "_handle_batch_all", mock_batch_all),
        ):
            coach.run()

        mock_batch_all.assert_called_once()

    def test_run_batch_rest_cancelled_exit_without_skip_git(self):
        """run() calls _optional_git_commit in batch_rest_cancelled 'exit' when skip_git=False."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=False, auto_mode=True)
        gaps_data = {
            "unanalyzed": [],
            "skipped": [],
            "rest_days": [{"session_id": "S082-R1", "date": "2026-02-24"}],
            "cancelled": [],
        }
        empty_gaps = {"unanalyzed": [], "skipped": [], "rest_days": [], "cancelled": []}
        call_count = 0

        def mock_step_1b():
            nonlocal call_count
            call_count += 1
            return ("batch_rest_cancelled", gaps_data) if call_count == 1 else ("exit", empty_gaps)

        mock_git = Mock()
        with (
            patch.object(coach, "step_1_welcome"),
            patch.object(coach, "step_1b_detect_all_gaps", side_effect=mock_step_1b),
            patch.object(coach, "_handle_rest_cancellations", return_value="exit"),
            patch.object(coach, "_optional_git_commit", mock_git),
        ):
            coach.run()

        mock_git.assert_called_once()

    def test_run_batch_skipped_exit_without_skip_git(self):
        """run() calls _optional_git_commit in batch_skipped 'exit' when skip_git=False."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=False, auto_mode=True)
        gaps_data = {
            "unanalyzed": [],
            "skipped": [{"planned_name": "S082-05 - TEC", "planned_date": "2026-02-20"}],
            "rest_days": [],
            "cancelled": [],
        }
        empty_gaps = {"unanalyzed": [], "skipped": [], "rest_days": [], "cancelled": []}
        call_count = 0

        def mock_step_1b():
            nonlocal call_count
            call_count += 1
            return ("batch_skipped", gaps_data) if call_count == 1 else ("exit", empty_gaps)

        mock_git = Mock()
        with (
            patch.object(coach, "step_1_welcome"),
            patch.object(coach, "step_1b_detect_all_gaps", side_effect=mock_step_1b),
            patch.object(coach, "_handle_skipped_sessions", return_value="exit"),
            patch.object(coach, "_optional_git_commit", mock_git),
        ):
            coach.run()

        mock_git.assert_called_once()

    def test_run_unexpected_exception_calls_sys_exit(self):
        """run() catches unexpected exceptions and calls sys.exit(1)."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, auto_mode=True)
        with (
            patch.object(coach, "step_1_welcome"),
            patch.object(coach, "step_1b_detect_all_gaps", side_effect=RuntimeError("boom")),
            pytest.raises(SystemExit) as exc_info,
        ):
            coach.run()
        assert exc_info.value.code == 1

    def test_run_keyboard_interrupt_calls_sys_exit(self):
        """run() catches KeyboardInterrupt and calls sys.exit(0)."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, auto_mode=True)
        with (
            patch.object(coach, "step_1_welcome"),
            patch.object(coach, "step_1b_detect_all_gaps", side_effect=KeyboardInterrupt),
            pytest.raises(SystemExit) as exc_info,
        ):
            coach.run()
        assert exc_info.value.code == 0

    def test_run_single_executed_servo_mode(self):
        """run() calls step_6b_servo_control when servo_mode is True."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, auto_mode=True, servo_mode=True)
        coach.workout_templates = {}
        gaps_data = {
            "unanalyzed": [{"id": "act1", "start_date_local": "2026-02-24T10:00:00"}],
            "skipped": [],
            "rest_days": [],
            "cancelled": [],
        }
        empty_gaps = {"unanalyzed": [], "skipped": [], "rest_days": [], "cancelled": []}
        call_count = 0

        def mock_step_1b():
            nonlocal call_count
            call_count += 1
            return ("single_executed", gaps_data) if call_count == 1 else ("exit", empty_gaps)

        mock_servo = Mock()
        with (
            patch.object(coach, "step_1_welcome"),
            patch.object(coach, "step_1b_detect_all_gaps", side_effect=mock_step_1b),
            patch.object(coach, "step_2_collect_feedback"),
            patch.object(coach, "step_3_prepare_analysis"),
            patch.object(coach, "step_4_paste_prompt"),
            patch.object(coach, "step_4b_display_analysis"),
            patch.object(coach, "step_5_validate_analysis"),
            patch.object(coach, "step_6_insert_analysis"),
            patch.object(coach, "step_6b_servo_control", mock_servo),
            patch.object(coach, "step_7_git_commit"),
            patch.object(coach, "show_summary"),
        ):
            coach.run()

        mock_servo.assert_called_once()


class TestStep1Welcome:
    """Test WorkflowCoach.step_1_welcome — output behavior in auto_mode."""

    def test_step_1_welcome_auto_mode_skips_wait(self, capsys):
        """In auto_mode, wait_user is skipped (no blocking input call)."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, auto_mode=True)
        # Should not block on input
        coach.step_1_welcome()
        # Just verify it completes without error (auto_mode skips input())
