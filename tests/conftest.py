"""
Pytest configuration and fixtures.

Uses pytest_collection_modifyitems hook to patch data repo BEFORE test collection.
This ensures mocks are active when test modules are imported.
"""

import json
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

# Global patches - activated before test collection
_data_repo_patches = []
_mock_data_config = None


def pytest_configure(config):
    """
    Configure pytest - runs BEFORE test collection.

    Set up mocks BEFORE any test modules are imported.
    This prevents FileNotFoundError when importing modules like planning_tower.
    """
    global _data_repo_patches, _mock_data_config

    # Create temporary directory for mocks
    import tempfile

    tmp_dir = Path(tempfile.mkdtemp())

    # Create mock data_repo structure with REAL Path objects
    data_repo_path = tmp_dir / "data"
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
    config_json_path = data_repo_path / ".config.json"
    config_data = {
        "week_references": [
            {"week_id": "S001", "start_date": "2024-08-05"},
            {"week_id": "S075", "start_date": "2026-01-05"},
        ]
    }
    config_json_path.write_text(json.dumps(config_data, indent=2), encoding="utf-8")

    # Create mock config object with REAL Path attributes
    _mock_data_config = Mock()
    _mock_data_config.data_repo_path = data_repo_path
    _mock_data_config.bilans_dir = bilans_dir
    _mock_data_config.data_dir = data_dir
    _mock_data_config.week_planning_dir = planning_dir
    _mock_data_config.workout_templates_dir = templates_dir
    _mock_data_config.workouts_history_path = workouts_history_path
    _mock_data_config.workflow_state_path = data_repo_path / ".workflow_state.json"
    _mock_data_config.context_path = data_repo_path / "context"

    # Mock calculate_week_start_date
    def mock_calculate_week_start_date(week_id: str) -> date:
        week_num = int(week_id[1:])
        reference = date(2024, 8, 5)
        return reference + timedelta(weeks=week_num - 1)

    # Start all patches BEFORE test collection
    patches = [
        patch(
            "cyclisme_training_logs.config.config_base.get_data_config",
            return_value=_mock_data_config,
        ),
        patch(
            "cyclisme_training_logs.config.get_data_config",
            return_value=_mock_data_config,
        ),
        patch(
            "cyclisme_training_logs.workflows.end_of_week.get_data_config",
            return_value=_mock_data_config,
        ),
        patch(
            "cyclisme_training_logs.weekly_analysis.get_data_config",
            return_value=_mock_data_config,
        ),
        patch(
            "cyclisme_training_logs.workflows.end_of_week.calculate_week_start_date",
            side_effect=mock_calculate_week_start_date,
        ),
        patch(
            "cyclisme_training_logs.workflows.proactive_compensation.calculate_week_start_date",
            side_effect=mock_calculate_week_start_date,
        ),
    ]

    # Start all patches
    for p in patches:
        p.start()
        _data_repo_patches.append(p)


def pytest_unconfigure(config):
    """Stop all patches after tests complete."""
    global _data_repo_patches
    for p in _data_repo_patches:
        p.stop()
