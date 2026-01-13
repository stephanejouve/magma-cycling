"""Tests complets pour upload_workouts.py.

Tests couvrent WorkoutUploader classe et fonctions utilitaires
pour upload workouts vers Intervals.icu.
"""

from datetime import datetime
from unittest.mock import Mock, mock_open, patch

import pytest

from cyclisme_training_logs.upload_workouts import WorkoutUploader, calculate_week_start_date


class TestCalculateWeekStartDate:
    """Tests for calculate_week_start_date() function."""

    @patch("cyclisme_training_logs.config.get_week_config")
    def test_calculate_week_start_date_s075(self, mock_config):
        """Test S075 calculates to 2026-01-05 (Monday)."""
        # Given: S075 with reference config
        from datetime import date

        mock_week_config = Mock()
        mock_week_config.get_reference_for_week.return_value = (
            date(2024, 8, 5),  # S001 reference
            74,  # S075 = S001 + 74 weeks
        )
        mock_config.return_value = mock_week_config

        # When: Calculating week start date
        result = calculate_week_start_date("S075")

        # Then: Returns 2026-01-05 (Monday)
        assert result == datetime(2026, 1, 5, 0, 0)
        assert result.weekday() == 0  # Monday

    @patch("cyclisme_training_logs.config.get_week_config")
    def test_calculate_week_start_date_s001_reference(self, mock_config):
        """Test S001 returns reference date."""
        # Given: S001 (reference week)
        from datetime import date

        mock_week_config = Mock()
        mock_week_config.get_reference_for_week.return_value = (
            date(2024, 8, 5),  # S001 reference
            0,  # S001 itself, 0 offset
        )
        mock_config.return_value = mock_week_config

        # When: Calculating
        result = calculate_week_start_date("S001")

        # Then: Returns reference date
        assert result == datetime(2024, 8, 5, 0, 0)
        assert result.weekday() == 0  # Monday

    @patch("cyclisme_training_logs.config.get_week_config")
    def test_calculate_week_start_date_validates_monday(self, mock_config):
        """Test raises error if calculated date is not Monday."""
        # Given: Invalid reference (not Monday)
        from datetime import date

        mock_week_config = Mock()
        mock_week_config.get_reference_for_week.return_value = (
            date(2024, 8, 6),  # Tuesday (invalid)
            0,
        )
        mock_config.return_value = mock_week_config

        # When/Then: Raises ValueError
        with pytest.raises(ValueError, match="not a Monday"):
            calculate_week_start_date("S001")


class TestWorkoutUploaderInit:
    """Tests for WorkoutUploader initialization."""

    @patch("cyclisme_training_logs.upload_workouts.IntervalsClient")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"athlete_id": "i151223", "api_key": "test_key"}',
    )
    @patch("pathlib.Path.exists", return_value=True)
    def test_init_with_config_file(self, mock_exists, mock_file, mock_client):
        """Test init with .intervals_config.json."""
        # Given: Config file exists
        week_num = "S075"
        start_date = datetime(2026, 1, 5)

        # When: Creating uploader
        uploader = WorkoutUploader(week_num, start_date)

        # Then: API initialized with config
        assert uploader.week_number == "S075"
        assert uploader.start_date == start_date
        assert uploader.api is not None
        mock_client.assert_called_once_with("i151223", "test_key")

    @patch("cyclisme_training_logs.upload_workouts.IntervalsClient")
    @patch("pathlib.Path.exists", return_value=False)
    @patch.dict(
        "os.environ", {"VITE_INTERVALS_ATHLETE_ID": "i151223", "VITE_INTERVALS_API_KEY": "test_key"}
    )
    def test_init_with_env_vars(self, mock_exists, mock_client):
        """Test init with environment variables."""
        # Given: Config file doesn't exist, env vars set
        week_num = "S076"
        start_date = datetime(2026, 1, 12)

        # When: Creating uploader
        uploader = WorkoutUploader(week_num, start_date)

        # Then: API initialized with env vars
        assert uploader.week_number == "S076"
        mock_client.assert_called_once_with("i151223", "test_key")

    @patch("pathlib.Path.exists", return_value=False)
    @patch.dict("os.environ", {}, clear=True)
    def test_init_without_credentials_exits(self, mock_exists):
        """Test init without credentials exits."""
        # Given: No config file, no env vars
        week_num = "S075"
        start_date = datetime(2026, 1, 5)

        # When/Then: Exits with error
        with pytest.raises(SystemExit):
            WorkoutUploader(week_num, start_date)


class TestValidateWorkoutNotation:
    """Tests for validate_workout_notation() method."""

    @patch("cyclisme_training_logs.upload_workouts.IntervalsClient")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"athlete_id": "i151223", "api_key": "test_key"}',
    )
    @patch("pathlib.Path.exists", return_value=True)
    def test_validate_workout_notation_valid(self, mock_exists, mock_file, mock_client):
        """Test validation of correctly formatted workout."""
        # Given: Valid workout
        uploader = WorkoutUploader("S075", datetime(2026, 1, 5))
        workout = {
            "name": "S075-01-REC-RecuperationActive-V001",
            "description": """Recuperation Active (45min, 25 TSS)

Warmup
- 10m ramp 45-60% 85rpm

Main set
- 25m 58-62% 85rpm

Cooldown
- 10m ramp 60-45% 85rpm""",
        }

        # When: Validating
        warnings = uploader.validate_workout_notation(workout)

        # Then: No warnings
        assert len(warnings) == 0

    @patch("cyclisme_training_logs.upload_workouts.IntervalsClient")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"athlete_id": "i151223", "api_key": "test_key"}',
    )
    @patch("pathlib.Path.exists", return_value=True)
    def test_validate_bad_repetition_notation(self, mock_exists, mock_file, mock_client):
        """Test detects bad repetition notation (3x [...])."""
        # Given: Workout with bad notation
        uploader = WorkoutUploader("S075", datetime(2026, 1, 5))
        workout = {
            "name": "S075-02-INT-SweetSpot",
            "description": """Sweet Spot (60min, 72 TSS)

Main set
3x [
- 9m 88% 90rpm
- 4m 62% 85rpm
]""",
        }

        # When: Validating
        warnings = uploader.validate_workout_notation(workout)

        # Then: Warning about bad notation
        assert len(warnings) > 0
        assert "3x [...]" in warnings[0]
        assert "Main set: 3x" in warnings[0]

    @patch("cyclisme_training_logs.upload_workouts.IntervalsClient")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"athlete_id": "i151223", "api_key": "test_key"}',
    )
    @patch("pathlib.Path.exists", return_value=True)
    def test_validate_rest_day_skips_warmup_cooldown(self, mock_exists, mock_file, mock_client):
        """Test rest day (REPOS) skips warmup/cooldown validation."""
        # Given: Rest day workout
        uploader = WorkoutUploader("S075", datetime(2026, 1, 5))
        workout = {"name": "S075-07-REPOS", "description": "REPOS COMPLET - Aucune activite"}

        # When: Validating
        warnings = uploader.validate_workout_notation(workout)

        # Then: No warmup/cooldown warnings (REPOS skipped)
        warmup_warnings = [w for w in warnings if "WARMUP" in w.upper()]
        cooldown_warnings = [w for w in warnings if "COOLDOWN" in w.upper()]
        assert len(warmup_warnings) == 0
        assert len(cooldown_warnings) == 0


class TestParseWorkoutsFile:
    """Tests for parse_workouts_file() method."""

    @patch("cyclisme_training_logs.upload_workouts.IntervalsClient")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"athlete_id": "i151223", "api_key": "test_key"}',
    )
    @patch("pathlib.Path.exists", return_value=True)
    def test_parse_workouts_file_single_workout(
        self, mock_exists, mock_file, mock_client, tmp_path
    ):
        """Test parsing file with single workout."""
        # Given: File with one workout
        uploader = WorkoutUploader("S075", datetime(2026, 1, 5))

        workout_content = """=== WORKOUT S075-01-REC-RecuperationActive-V001 ===

Recuperation Active (45min, 25 TSS)

Warmup
- 10m ramp 45-60% 85rpm

Main set
- 25m 58-62% 85rpm

Cooldown
- 10m ramp 60-45% 85rpm

=== FIN WORKOUT ==="""

        # Create temp file
        test_file = tmp_path / "test.txt"
        test_file.write_text(workout_content, encoding="utf-8")

        # When: Parsing
        workouts = uploader.parse_workouts_file(test_file)

        # Then: One workout parsed
        assert len(workouts) == 1
        assert workouts[0]["name"] == "S075-01-REC-RecuperationActive-V001"
        assert "Warmup" in workouts[0]["description"]
        assert "Main set" in workouts[0]["description"]
        assert "Cooldown" in workouts[0]["description"]

    @patch("cyclisme_training_logs.upload_workouts.IntervalsClient")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"athlete_id": "i151223", "api_key": "test_key"}',
    )
    @patch("pathlib.Path.exists", return_value=True)
    def test_parse_workouts_file_multiple_workouts(
        self, mock_exists, mock_file, mock_client, tmp_path
    ):
        """Test parsing file with multiple workouts."""
        # Given: File with 3 workouts
        uploader = WorkoutUploader("S075", datetime(2026, 1, 5))

        workout_content = """=== WORKOUT S075-01-REC ===
Recuperation (30min, 20 TSS)
Warmup
- 10m 50% 85rpm
Main set
- 10m 60% 85rpm
Cooldown
- 10m 50% 85rpm
=== FIN WORKOUT ===

=== WORKOUT S075-02-END ===
Endurance (60min, 45 TSS)
Warmup
- 10m 50-65% 85rpm
Main set
- 40m 70% 88rpm
Cooldown
- 10m 65-50% 85rpm
=== FIN WORKOUT ===

=== WORKOUT S075-07-REPOS ===
REPOS COMPLET - Aucune activite
=== FIN WORKOUT ==="""

        # Create temp file
        test_file = tmp_path / "test.txt"
        test_file.write_text(workout_content, encoding="utf-8")

        # When: Parsing
        workouts = uploader.parse_workouts_file(test_file)

        # Then: Three workouts parsed
        assert len(workouts) == 3
        assert workouts[0]["name"] == "S075-01-REC"
        assert workouts[1]["name"] == "S075-02-END"
        assert workouts[2]["name"] == "S075-07-REPOS"

    @patch("cyclisme_training_logs.upload_workouts.IntervalsClient")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"athlete_id": "i151223", "api_key": "test_key"}',
    )
    @patch("pathlib.Path.exists", return_value=True)
    def test_parse_workouts_file_extracts_tss(self, mock_exists, mock_file, mock_client, tmp_path):
        """Test parsing extracts TSS from description."""
        # Given: Workout with TSS in description
        uploader = WorkoutUploader("S075", datetime(2026, 1, 5))

        workout_content = """=== WORKOUT S075-01-REC ===
Recuperation (45min, 25 TSS)

Warmup
- 10m 50% 85rpm

Main set
- 25m 60% 85rpm

Cooldown
- 10m 50% 85rpm
=== FIN WORKOUT ==="""

        # Create temp file
        test_file = tmp_path / "test.txt"
        test_file.write_text(workout_content, encoding="utf-8")

        # When: Parsing
        workouts = uploader.parse_workouts_file(test_file)

        # Then: TSS extracted
        assert len(workouts) == 1
        assert "25 TSS" in workouts[0]["description"]


class TestUploadWorkout:
    """Tests for upload_workout() method."""

    @patch("cyclisme_training_logs.upload_workouts.IntervalsClient")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"athlete_id": "i151223", "api_key": "test_key"}',
    )
    @patch("pathlib.Path.exists", return_value=True)
    def test_upload_workout_success(self, mock_exists, mock_file, mock_client_class):
        """Test successful workout upload."""
        # Given: Uploader with mocked API
        mock_api_instance = Mock()
        mock_api_instance.create_event.return_value = {"id": "123"}
        mock_client_class.return_value = mock_api_instance

        uploader = WorkoutUploader("S075", datetime(2026, 1, 5))
        workout = {
            "name": "S075-01-REC",
            "description": "Recuperation (30min, 20 TSS)\nMain set\n- 10m 60% 85rpm",
            "date": "2026-01-05",  # Required by upload_workout
        }

        # When: Uploading
        success = uploader.upload_workout(workout)

        # Then: Returns True
        assert success is True
        mock_api_instance.create_event.assert_called_once()

    @patch("cyclisme_training_logs.upload_workouts.IntervalsClient")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"athlete_id": "i151223", "api_key": "test_key"}',
    )
    @patch("pathlib.Path.exists", return_value=True)
    def test_upload_workout_api_failure(self, mock_exists, mock_file, mock_client_class):
        """Test workout upload handles API failure."""
        # Given: API raises exception
        mock_api_instance = Mock()
        mock_api_instance.create_event.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_api_instance

        uploader = WorkoutUploader("S075", datetime(2026, 1, 5))
        workout = {"name": "S075-01-REC", "description": "Recuperation", "date": "2026-01-05"}

        # When: Uploading
        success = uploader.upload_workout(workout)

        # Then: Returns False (graceful failure)
        assert success is False


class TestUploadAll:
    """Tests for upload_all() method."""

    @patch("cyclisme_training_logs.upload_workouts.IntervalsClient")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"athlete_id": "i151223", "api_key": "test_key"}',
    )
    @patch("pathlib.Path.exists", return_value=True)
    def test_upload_all_dry_run(self, mock_exists, mock_file, mock_client):
        """Test dry-run mode doesn't upload."""
        # Given: Uploader with workouts
        uploader = WorkoutUploader("S075", datetime(2026, 1, 5))
        workouts = [
            {
                "name": "S075-01-REC",
                "description": "Recuperation",
                "day": 1,
                "date": "2026-01-05",
                "filename": "S075-01-REC",
            },
            {
                "name": "S075-02-END",
                "description": "Endurance",
                "day": 2,
                "date": "2026-01-06",
                "filename": "S075-02-END",
            },
        ]

        # When: Uploading in dry-run mode
        result = uploader.upload_all(workouts, dry_run=True)

        # Then: No actual uploads
        assert result["success"] == 2  # Dry run counts as success
        assert result["failed"] == 0
        # API create_event should not be called in dry-run
        uploader.api.create_event.assert_not_called()

    @patch("cyclisme_training_logs.upload_workouts.IntervalsClient")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"athlete_id": "i151223", "api_key": "test_key"}',
    )
    @patch("pathlib.Path.exists", return_value=True)
    def test_upload_all_success(self, mock_exists, mock_file, mock_client_class):
        """Test batch upload all workouts."""
        # Given: Uploader with mocked API
        mock_api_instance = Mock()
        mock_api_instance.create_event.return_value = {"id": "123"}
        mock_client_class.return_value = mock_api_instance

        uploader = WorkoutUploader("S075", datetime(2026, 1, 5))
        workouts = [
            {
                "name": "S075-01-REC",
                "description": "Recuperation",
                "day": 1,
                "date": "2026-01-05",
                "filename": "S075-01-REC",
            },
            {
                "name": "S075-02-END",
                "description": "Endurance",
                "day": 2,
                "date": "2026-01-06",
                "filename": "S075-02-END",
            },
        ]

        # When: Uploading (not dry-run)
        result = uploader.upload_all(workouts, dry_run=False)

        # Then: All uploaded
        assert result["success"] == 2
        assert result["failed"] == 0
        assert mock_api_instance.create_event.call_count == 2

    @patch("cyclisme_training_logs.upload_workouts.IntervalsClient")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"athlete_id": "i151223", "api_key": "test_key"}',
    )
    @patch("pathlib.Path.exists", return_value=True)
    def test_upload_all_partial_failure(self, mock_exists, mock_file, mock_client_class):
        """Test batch upload with some failures."""
        # Given: API fails on second upload
        mock_api_instance = Mock()
        mock_api_instance.create_event.side_effect = [
            {"id": "123"},  # First success
            Exception("API Error"),  # Second fails
            {"id": "125"},  # Third success
        ]
        mock_client_class.return_value = mock_api_instance

        uploader = WorkoutUploader("S075", datetime(2026, 1, 5))
        workouts = [
            {
                "name": "S075-01-REC",
                "description": "Recuperation",
                "day": 1,
                "date": "2026-01-05",
                "filename": "S075-01-REC",
            },
            {
                "name": "S075-02-END",
                "description": "Endurance",
                "day": 2,
                "date": "2026-01-06",
                "filename": "S075-02-END",
            },
            {
                "name": "S075-03-INT",
                "description": "Intervals",
                "day": 3,
                "date": "2026-01-07",
                "filename": "S075-03-INT",
            },
        ]

        # When: Uploading
        result = uploader.upload_all(workouts, dry_run=False)

        # Then: Partial success
        assert result["success"] == 2
        assert result["failed"] == 1


class TestIntegrationUploadWorkflow:
    """Integration tests for complete upload workflow."""

    @patch("cyclisme_training_logs.upload_workouts.IntervalsClient")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"athlete_id": "i151223", "api_key": "test_key"}',
    )
    @patch("pathlib.Path.exists", return_value=True)
    def test_full_workflow_parse_validate_upload(
        self, mock_exists, mock_file, mock_client_class, tmp_path
    ):
        """Test complete workflow: parse → validate → upload."""
        # Given: Mock API and workout file
        mock_api_instance = Mock()
        mock_api_instance.create_event.return_value = {"id": "123"}
        mock_client_class.return_value = mock_api_instance

        uploader = WorkoutUploader("S076", datetime(2026, 1, 12))

        workout_content = """=== WORKOUT S076-01-REC-RecuperationActive-V001 ===
Recuperation Active (45min, 25 TSS)
Warmup
- 10m ramp 45-60% 85rpm
Main set
- 25m 58-62% 85rpm
Cooldown
- 10m ramp 60-45% 85rpm
=== FIN WORKOUT ==="""

        # Create temp file
        test_file = tmp_path / "S076_workouts.txt"
        test_file.write_text(workout_content, encoding="utf-8")

        # When: Complete workflow
        # Parse
        workouts = uploader.parse_workouts_file(test_file)

        # Validate
        all_warnings = []
        for workout in workouts:
            warnings = uploader.validate_workout_notation(workout)
            all_warnings.extend(warnings)

        # Upload
        result = uploader.upload_all(workouts, dry_run=False)

        # Then: Workflow succeeds
        assert len(workouts) == 1
        assert len(all_warnings) == 0  # No validation warnings
        assert result["success"] == 1
        assert result["failed"] == 0
        mock_api_instance.create_event.assert_called_once()
