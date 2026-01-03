"""
Tests for data repository configuration module.
"""

from pathlib import Path

import pytest

from cyclisme_training_logs.config import (
    DataRepoConfig,
    get_data_config,
    reset_data_config,
    set_data_config,
)


@pytest.fixture
def temp_data_repo(tmp_path):
    """Create temporary data repository for tests."""
    test_repo = tmp_path / "training-logs"
    test_repo.mkdir()

    # Create required structure
    (test_repo / "workouts-history.md").touch()
    (test_repo / "bilans").mkdir()
    (test_repo / "data").mkdir()

    return test_repo


@pytest.fixture(autouse=True)
def reset_config():
    """Reset global config before/after each test."""
    reset_data_config()
    yield
    reset_data_config()


def test_config_with_explicit_path(temp_data_repo):
    """Test DataRepoConfig with explicit path."""
    config = DataRepoConfig(data_repo_path=temp_data_repo)

    assert config.data_repo_path == temp_data_repo
    assert config.workouts_history_path == temp_data_repo / "workouts-history.md"
    assert config.bilans_dir == temp_data_repo / "bilans"
    assert config.data_dir == temp_data_repo / "data"


def test_config_with_env_var(temp_data_repo, monkeypatch):
    """Test DataRepoConfig with TRAINING_DATA_REPO env var."""
    monkeypatch.setenv("TRAINING_DATA_REPO", str(temp_data_repo))

    config = DataRepoConfig()

    assert config.data_repo_path == temp_data_repo
    assert config.workouts_history_path.exists()


def test_config_nonexistent_path():
    """Test DataRepoConfig raises error for nonexistent path."""
    nonexistent = Path("/nonexistent/training-logs")

    with pytest.raises(FileNotFoundError) as exc_info:
        DataRepoConfig(data_repo_path=nonexistent)

    assert "Data repo not found" in str(exc_info.value)
    assert str(nonexistent) in str(exc_info.value)


def test_config_missing_workouts_history(temp_data_repo):
    """Test validate() raises error if workouts-history.md missing."""
    # Remove workouts-history.md
    (temp_data_repo / "workouts-history.md").unlink()

    config = DataRepoConfig(data_repo_path=temp_data_repo)

    with pytest.raises(FileNotFoundError) as exc_info:
        config.validate()

    assert "workouts-history.md not found" in str(exc_info.value)


def test_config_ensure_directories(temp_data_repo):
    """Test ensure_directories creates missing dirs."""
    config = DataRepoConfig(data_repo_path=temp_data_repo)

    # Remove directories
    import shutil

    shutil.rmtree(temp_data_repo / "data")

    # Should recreate them
    config.ensure_directories()

    assert config.week_planning_dir.exists()
    assert config.workout_templates_dir.exists()
    assert config.bilans_dir.exists()


def test_get_data_config_singleton(temp_data_repo):
    """Test get_data_config returns singleton instance."""
    set_data_config(DataRepoConfig(data_repo_path=temp_data_repo))

    config1 = get_data_config()
    config2 = get_data_config()

    assert config1 is config2


def test_set_and_reset_config(temp_data_repo):
    """Test set_data_config and reset_data_config."""
    config = DataRepoConfig(data_repo_path=temp_data_repo)
    set_data_config(config)

    retrieved = get_data_config()
    assert retrieved is config

    reset_data_config()

    # After reset, get_data_config should try to create new instance
    # (will fail without valid default path, which is expected)


def test_config_all_paths(temp_data_repo):
    """Test all path properties return correct values."""
    config = DataRepoConfig(data_repo_path=temp_data_repo)

    # Test all path properties
    assert config.workouts_history_path == temp_data_repo / "workouts-history.md"
    assert config.bilans_dir == temp_data_repo / "bilans"
    assert config.data_dir == temp_data_repo / "data"
    assert config.week_planning_dir == temp_data_repo / "data" / "week_planning"
    assert config.workout_templates_dir == temp_data_repo / "data" / "workout_templates"
    assert config.workflow_state_path == temp_data_repo / ".workflow_state.json"
