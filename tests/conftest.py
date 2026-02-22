"""
Pytest configuration and fixtures for MCP tests.

Provides global fixtures to mock data repo configuration,
preventing FileNotFoundError on CI where data repo doesn't exist.
"""

from unittest.mock import Mock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_data_repo_for_planning_tower(monkeypatch, tmp_path):
    """
    Auto-use fixture to mock get_data_config for all tests.

    This prevents FileNotFoundError when importing modules that create
    planning_tower global instance (which calls get_data_config).

    Applied automatically to all tests.
    """
    mock_data_config = Mock()
    mock_data_config.week_planning_dir = tmp_path / "planning"
    mock_data_config.week_planning_dir.mkdir(parents=True, exist_ok=True)

    # Add data_repo_path for daily_sync and other modules
    mock_data_config.data_repo_path = tmp_path / "data"
    mock_data_config.data_repo_path.mkdir(parents=True, exist_ok=True)

    # Mock get_data_config in ALL import locations
    # Patch where it's defined (config_base) AND where it's imported (config, end_of_week, etc.)
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
    ):
        yield mock_data_config
