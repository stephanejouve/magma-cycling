"""
Pytest configuration and fixtures.

Provides optional fixtures - NOT applied automatically.
Tests must request fixtures explicitly to avoid conflicts.
"""

import json
from datetime import date, timedelta
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def mock_data_repo(tmp_path):
    """
    Optional fixture to mock get_data_config and create mock data repo structure.

    Usage in tests:
        def test_something(mock_data_repo):
            # Data repo mocks are active
            ...

    This fixture:
    - Creates real Path objects for all data repo directories
    - Mocks get_data_config() in all import locations
    - Mocks calculate_week_start_date() for week calculations
    - Creates workouts-history.md and .config.json files

    NOT applied automatically - prevents breaking existing tests.
    """
    # Create mock data_repo structure with REAL Path objects (not Mocks)
    # This prevents "TypeError: unsupported operand type(s) for /: 'Mock' and 'str'"
    data_repo_path = tmp_path / "data"
    data_repo_path.mkdir(parents=True, exist_ok=True)

    # Create all required directories
    bilans_dir = data_repo_path / "bilans"
    bilans_dir.mkdir(parents=True, exist_ok=True)

    data_dir = data_repo_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    planning_dir = data_dir / "week_planning"
    planning_dir.mkdir(parents=True, exist_ok=True)

    templates_dir = data_dir / "workout_templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    # Create workouts-history.md file
    workouts_history_path = data_repo_path / "workouts-history.md"
    workouts_history_path.write_text("# Historique des séances\n", encoding="utf-8")

    # Create .config.json for get_week_config()
    # Use S001 = 2024-08-05 as reference (Monday)
    config_json_path = data_repo_path / ".config.json"
    config_data = {
        "week_references": [
            {"week_id": "S001", "start_date": "2024-08-05"},
            {"week_id": "S075", "start_date": "2026-01-05"},
        ]
    }
    config_json_path.write_text(json.dumps(config_data, indent=2), encoding="utf-8")

    # Create mock config object with REAL Path attributes
    mock_data_config = Mock()
    mock_data_config.data_repo_path = data_repo_path
    mock_data_config.bilans_dir = bilans_dir
    mock_data_config.data_dir = data_dir
    mock_data_config.week_planning_dir = planning_dir
    mock_data_config.workout_templates_dir = templates_dir
    mock_data_config.workouts_history_path = workouts_history_path
    mock_data_config.workflow_state_path = data_repo_path / ".workflow_state.json"
    mock_data_config.context_path = data_repo_path / "context"

    # Mock calculate_week_start_date for tests that use week_id
    def mock_calculate_week_start_date(week_id: str) -> date:
        """Mock implementation for testing."""
        # Extract week number (S078 -> 78)
        week_num = int(week_id[1:])
        # S001 = 2024-08-05 (Monday)
        reference = date(2024, 8, 5)
        # Calculate based on week offset
        return reference + timedelta(weeks=week_num - 1)

    # Mock get_data_config in ALL import locations
    # Patch where it's defined (config_base) AND where it's imported
    with (
        patch(
            "cyclisme_training_logs.config.config_base.get_data_config",
            return_value=mock_data_config,
        ),
        patch(
            "cyclisme_training_logs.config.get_data_config",
            return_value=mock_data_config,
        ),
        patch(
            "cyclisme_training_logs.workflows.end_of_week.get_data_config",
            return_value=mock_data_config,
        ),
        patch(
            "cyclisme_training_logs.weekly_analysis.get_data_config",
            return_value=mock_data_config,
        ),
        patch(
            "cyclisme_training_logs.workflows.end_of_week.calculate_week_start_date",
            side_effect=mock_calculate_week_start_date,
        ),
        patch(
            "cyclisme_training_logs.workflows.proactive_compensation.calculate_week_start_date",
            side_effect=mock_calculate_week_start_date,
        ),
    ):
        yield mock_data_config
