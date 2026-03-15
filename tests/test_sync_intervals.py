"""
Tests for sync_intervals tool.

Tests the Intervals.icu sync functionality including:
- WorkoutLogger initialization
- Workout entry formatting
- History file updates
- Metrics file updates
- Configuration loading
- CLI entry point

Author: Claude Sonnet 4.5
Created: 2026-02-19
"""

from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.sync_intervals import WorkoutLogger


class TestWorkoutLoggerInit:
    """Test WorkoutLogger initialization."""

    def test_init_with_data_config(self, tmp_path):
        """Test initialization using data repo config."""
        with patch("magma_cycling.config.get_data_config") as mock_config:
            mock_config.return_value = MagicMock(
                data_repo_path=tmp_path,
                workouts_history_path=tmp_path / "workouts-history.md",
            )

            logger = WorkoutLogger()

            assert logger.logs_dir == tmp_path
            assert logger.workouts_file == tmp_path / "workouts-history.md"

    def test_init_with_explicit_logs_dir(self, tmp_path):
        """Test initialization with explicit logs directory."""
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        logger = WorkoutLogger(logs_dir=logs_dir)

        assert logger.logs_dir == logs_dir
        assert logger.workouts_file == logs_dir / "workouts-history.md"
        assert logger.metrics_file == logs_dir / "metrics-evolution.md"

    def test_init_fallback_to_default(self):
        """Test fallback to default logs directory when config fails."""
        with patch(
            "magma_cycling.config.get_data_config",
            side_effect=FileNotFoundError,
        ):
            logger = WorkoutLogger()

            # Should fallback to cwd/logs
            assert logger.logs_dir.name == "logs"
            assert logger.workouts_file.name == "workouts-history.md"


class TestFormatWorkoutEntry:
    """Test format_workout_entry method."""

    @pytest.fixture
    def logger(self, tmp_path):
        """Create logger for testing."""
        return WorkoutLogger(logs_dir=tmp_path)

    def test_format_workout_entry_basic(self, logger):
        """Test basic workout entry formatting."""
        activity = {
            "start_date_local": "2026-03-02T10:00:00",
            "name": "Endurance Douce",
            "type": "Ride",
            "moving_time": 3600,  # 60 minutes
            "icu_training_load": 50,
            "icu_intensity": 60,  # 0.60
            "icu_average_watts": 150,
            "icu_weighted_avg_watts": 160,  # NP
            "average_cadence": 90,
            "average_heartrate": 130,
            "max_heartrate": 150,
        }

        wellness_pre = {"ctl": 65, "atl": 55, "tsb": 10}
        wellness_post = {"ctl": 66, "atl": 56, "tsb": 10}

        entry = logger.format_workout_entry(activity, wellness_pre, wellness_post)

        assert "Endurance Douce" in entry
        assert "02/03/2026" in entry
        assert "60min" in entry
        assert "50" in entry  # TSS
        assert "0.60" in entry  # IF
        assert "150W" in entry  # Average power
        assert "160W" in entry  # NP
        assert "90rpm" in entry
        assert "130bpm" in entry
        assert "CTL : 65" in entry
        assert "CTL : 66" in entry

    def test_format_workout_entry_with_decoupling(self, logger):
        """Test formatting with decoupling data."""
        activity = {
            "start_date_local": "2026-03-02T10:00:00",
            "name": "Test Workout",
            "moving_time": 3600,
            "icu_training_load": 50,
            "icu_intensity": 60,
            "icu_average_watts": 150,
            "icu_weighted_avg_watts": 160,
            "average_cadence": 90,
            "average_heartrate": 130,
            "decoupling": 3.5,  # 3.5% decoupling
        }

        wellness_pre = {"ctl": 65, "atl": 55, "tsb": 10}
        wellness_post = {"ctl": 66, "atl": 56, "tsb": 10}

        entry = logger.format_workout_entry(activity, wellness_pre, wellness_post)

        assert "3.5%" in entry  # Decoupling percentage

    def test_format_workout_entry_without_decoupling(self, logger):
        """Test formatting without decoupling data."""
        activity = {
            "start_date_local": "2026-03-02T10:00:00",
            "name": "Test Workout",
            "moving_time": 3600,
            "icu_training_load": 50,
            "icu_intensity": 60,
            "icu_average_watts": 150,
            "icu_weighted_avg_watts": 160,
            "average_cadence": 90,
            "average_heartrate": 130,
        }

        wellness_pre = {"ctl": 65, "atl": 55, "tsb": 10}
        wellness_post = {"ctl": 66, "atl": 56, "tsb": 10}

        entry = logger.format_workout_entry(activity, wellness_pre, wellness_post)

        assert "N/A" in entry  # No decoupling data


class TestUpdateWorkoutsHistory:
    """Test update_workouts_history method."""

    @pytest.fixture
    def logger(self, tmp_path):
        """Create logger with temp directory."""
        return WorkoutLogger(logs_dir=tmp_path)

    def test_update_workouts_history_new_file(self, logger):
        """Test creating new workouts history file."""
        activities = [
            {
                "start_date_local": "2026-03-02T10:00:00",
                "name": "Test Workout",
                "moving_time": 3600,
                "icu_training_load": 50,
                "icu_intensity": 60,
                "icu_average_watts": 150,
                "icu_weighted_avg_watts": 160,
                "average_cadence": 90,
                "average_heartrate": 130,
            }
        ]

        wellness_data = [{"id": "2026-03-02", "ctl": 65, "atl": 55, "tsb": 10}]

        logger.update_workouts_history(activities, wellness_data)

        # Verify file was created
        assert logger.workouts_file.exists()

        # Read content
        content = logger.workouts_file.read_text()
        assert "Test Workout" in content
        assert "Historique des Entraînements" in content

    def test_update_workouts_history_existing_file(self, logger):
        """Test updating existing workouts history file."""
        # Create existing file
        logger.workouts_file.parent.mkdir(parents=True, exist_ok=True)
        logger.workouts_file.write_text(
            "# Historique des Entraînements\n\n## Historique\n\nOld content"
        )

        activities = [
            {
                "start_date_local": "2026-03-02T10:00:00",
                "name": "New Workout",
                "moving_time": 3600,
                "icu_training_load": 50,
                "icu_intensity": 60,
                "icu_average_watts": 150,
                "icu_weighted_avg_watts": 160,
                "average_cadence": 90,
                "average_heartrate": 130,
            }
        ]

        wellness_data = [{"id": "2026-03-02", "ctl": 65, "atl": 55, "tsb": 10}]

        logger.update_workouts_history(activities, wellness_data)

        # Verify content updated
        content = logger.workouts_file.read_text()
        assert "New Workout" in content
        assert "Old content" in content

    def test_update_workouts_history_multiple_activities(self, logger):
        """Test updating with multiple activities."""
        activities = [
            {
                "start_date_local": "2026-03-02T10:00:00",
                "name": "Workout 1",
                "moving_time": 3600,
                "icu_training_load": 50,
                "icu_intensity": 60,
                "icu_average_watts": 150,
                "icu_weighted_avg_watts": 160,
                "average_cadence": 90,
                "average_heartrate": 130,
            },
            {
                "start_date_local": "2026-03-03T10:00:00",
                "name": "Workout 2",
                "moving_time": 4200,
                "icu_training_load": 70,
                "icu_intensity": 75,
                "icu_average_watts": 180,
                "icu_weighted_avg_watts": 190,
                "average_cadence": 95,
                "average_heartrate": 145,
            },
        ]

        wellness_data = [
            {"id": "2026-03-02", "ctl": 65, "atl": 55, "tsb": 10},
            {"id": "2026-03-03", "ctl": 66, "atl": 56, "tsb": 10},
        ]

        logger.update_workouts_history(activities, wellness_data)

        content = logger.workouts_file.read_text()
        assert "Workout 1" in content
        assert "Workout 2" in content


class TestUpdateMetricsEvolution:
    """Test update_metrics_evolution method."""

    @pytest.fixture
    def logger(self, tmp_path):
        """Create logger with temp directory."""
        return WorkoutLogger(logs_dir=tmp_path)

    def test_update_metrics_evolution_creates_summary(self, logger):
        """Test metrics evolution summary creation."""
        athlete_data = {
            "ftp": 250,
            "weight": 75.0,
        }

        wellness_data = [{"id": "2026-03-02", "ctl": 65.5, "atl": 55.2, "tsb": 10.3}]

        logger.update_metrics_evolution(athlete_data, wellness_data)

        # Verify summary file created
        summary_file = logger.logs_dir / "metrics_sync_summary.md"
        assert summary_file.exists()

        # Read content
        content = summary_file.read_text()
        assert "250W" in content  # FTP
        assert "75.0kg" in content  # Weight
        assert "3.33 W/kg" in content  # FTP/kg
        assert "66" in content  # CTL (65.5 rounded up)
        assert "55" in content  # ATL
        assert "10" in content  # TSB

    def test_update_metrics_evolution_handles_none_ftp(self, logger):
        """Test handling when FTP is None."""
        athlete_data = {
            "ftp": None,
            "weight": 75.0,
        }

        wellness_data = [{"id": "2026-03-02", "ctl": 65.5, "atl": 55.2, "tsb": 10.3}]

        logger.update_metrics_evolution(athlete_data, wellness_data)

        summary_file = logger.logs_dir / "metrics_sync_summary.md"
        content = summary_file.read_text()
        assert "220W" in content  # Default FTP

    def test_update_metrics_evolution_handles_none_weight(self, logger):
        """Test handling when weight is None."""
        athlete_data = {
            "ftp": 250,
            "weight": None,
        }

        wellness_data = [{"id": "2026-03-02", "ctl": 65.5, "atl": 55.2, "tsb": 10.3}]

        logger.update_metrics_evolution(athlete_data, wellness_data)

        summary_file = logger.logs_dir / "metrics_sync_summary.md"
        content = summary_file.read_text()
        assert "83.8kg" in content  # Default weight


class TestMainFunction:
    """Test main CLI function."""

    @patch("magma_cycling.sync_intervals.IntervalsClient")
    @patch("magma_cycling.sync_intervals.WorkoutLogger")
    @patch("sys.argv", ["sync-intervals", "--athlete-id", "iXXXXXX", "--api-key", "test_key"])
    def test_main_with_cli_args(self, mock_logger_class, mock_client_class):
        """Test main function with CLI arguments."""
        from magma_cycling.sync_intervals import main

        # Mock API responses
        mock_api = MagicMock()
        mock_api.athlete_id = "iXXXXXX"
        mock_api.get_athlete.return_value = {"ftp": 250, "weight": 75.0}
        mock_api.get_wellness.return_value = [{"id": "2026-03-02", "ctl": 65, "atl": 55, "tsb": 10}]
        mock_api.get_activities.return_value = [
            {
                "start_date_local": "2026-03-02T10:00:00",
                "name": "Test Workout",
                "moving_time": 3600,
                "icu_training_load": 50,
                "icu_intensity": 60,
                "icu_average_watts": 150,
                "icu_weighted_avg_watts": 160,
                "average_cadence": 90,
                "average_heartrate": 130,
            }
        ]
        mock_client_class.return_value = mock_api

        # Mock logger
        mock_logger = MagicMock()
        mock_logger_class.return_value = mock_logger

        # Run main (@cli_main wraps with sys.exit)
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

        # Verify API was initialized with CLI args
        mock_client_class.assert_called_once_with(athlete_id="iXXXXXX", api_key="test_key")

        # Verify data was fetched
        mock_api.get_athlete.assert_called_once()
        mock_api.get_wellness.assert_called_once()
        mock_api.get_activities.assert_called_once()

        # Verify logger methods called
        mock_logger.update_workouts_history.assert_called_once()
        mock_logger.update_metrics_evolution.assert_called_once()

    @patch("magma_cycling.sync_intervals.create_intervals_client")
    @patch("magma_cycling.sync_intervals.WorkoutLogger")
    @patch("sys.argv", ["sync-intervals"])
    def test_main_with_centralized_config(self, mock_logger_class, mock_create_client):
        """Test main function uses create_intervals_client() when no CLI args."""
        from magma_cycling.sync_intervals import main

        # Mock API via factory
        mock_api = MagicMock()
        mock_api.athlete_id = "iXXXXXX"
        mock_api.get_athlete.return_value = {"ftp": 250, "weight": 75.0}
        mock_api.get_wellness.return_value = []
        mock_api.get_activities.return_value = []
        mock_create_client.return_value = mock_api

        # Mock logger
        mock_logger = MagicMock()
        mock_logger_class.return_value = mock_logger

        # Run main (@cli_main wraps with sys.exit)
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

        # Verify factory was used
        mock_create_client.assert_called_once()
