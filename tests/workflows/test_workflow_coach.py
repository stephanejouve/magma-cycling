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
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import requests

from cyclisme_training_logs.workflow_coach import WorkflowCoach


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

    @patch("cyclisme_training_logs.workflow_coach.get_data_config")
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

    @patch("pathlib.Path.exists", return_value=False)
    @patch.dict(
        "os.environ", {"VITE_INTERVALS_ATHLETE_ID": "i123", "VITE_INTERVALS_API_KEY": "key123"}
    )
    def test_load_credentials_from_env(self, mock_exists):
        """Test load_credentials loads from environment variables."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        athlete_id, api_key = coach.load_credentials()

        assert athlete_id == "i123"
        assert api_key == "key123"

    @patch.dict("os.environ", {}, clear=True)
    @patch("pathlib.Path.exists", return_value=False)
    def test_load_credentials_missing(self, mock_exists):
        """Test load_credentials returns None when credentials missing."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        result = coach.load_credentials()

        assert result == (None, None)


class TestPlanningModifications:
    """Test planning modification methods."""

    @patch("cyclisme_training_logs.workflow_coach.get_data_config")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("json.dump")
    def test_update_planning_json_success(self, mock_dump, mock_json_load, mock_file, mock_config):
        """Test _update_planning_json updates planning file successfully."""
        # Mock config
        mock_config_obj = Mock()
        mock_config_obj.week_planning_dir = Path("/fake/path")
        mock_config.return_value = mock_config_obj

        # Mock planning data
        planning_data = {
            "week_id": "S072",
            "start_date": "2025-12-15",
            "planned_sessions": [
                {
                    "date": "2025-12-18",
                    "session_id": "S072-03",
                    "name": "Tempo",
                    "type": "TEMPO",
                    "tss_planned": 75,
                    "description": "Original tempo session",
                }
            ],
            "version": 1,
        }
        mock_json_load.return_value = planning_data

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
        # Verify json.dump was called (file was written)
        assert mock_dump.called

    @patch("cyclisme_training_logs.workflow_coach.get_data_config")
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
