"""
Configuration module for data repository paths.

Allows separation of code (cyclisme-training-logs) from athlete data (training-logs).
"""

import os
from pathlib import Path
from typing import Optional


class DataRepoConfig:
    """Configuration for external data repository paths."""

    def __init__(self, data_repo_path: Optional[Path] = None):
        """
        Initialize data repository configuration.

        Args:
            data_repo_path: Path to external data repository.
                           If None, will try TRAINING_DATA_REPO env var,
                           then default to ~/training-logs

        Raises:
            FileNotFoundError: If data repository path doesn't exist
        """
        if data_repo_path is None:
            # Try env var first
            env_path = os.getenv('TRAINING_DATA_REPO')
            if env_path:
                data_repo_path = Path(env_path).expanduser()
            else:
                # Default to ~/training-logs
                data_repo_path = Path.home() / 'training-logs'

        self.data_repo_path = Path(data_repo_path).resolve()

        # Validate path exists
        if not self.data_repo_path.exists():
            raise FileNotFoundError(
                f"Data repo not found: {self.data_repo_path}\n"
                f"Set TRAINING_DATA_REPO env var or clone:\n"
                f"  git clone https://github.com/stephanejouve/training-logs.git ~/training-logs"
            )

    @property
    def workouts_history_path(self) -> Path:
        """Path to workouts-history.md in data repo."""
        return self.data_repo_path / 'workouts-history.md'

    @property
    def bilans_dir(self) -> Path:
        """Path to bilans/ directory in data repo."""
        return self.data_repo_path / 'bilans'

    @property
    def data_dir(self) -> Path:
        """Path to data/ directory in data repo."""
        return self.data_repo_path / 'data'

    @property
    def week_planning_dir(self) -> Path:
        """Path to data/week_planning/ directory in data repo."""
        return self.data_dir / 'week_planning'

    @property
    def workout_templates_dir(self) -> Path:
        """Path to data/workout_templates/ directory in data repo."""
        return self.data_dir / 'workout_templates'

    @property
    def workflow_state_path(self) -> Path:
        """Path to .workflow_state.json in data repo."""
        return self.data_repo_path / '.workflow_state.json'

    def ensure_directories(self):
        """Create required directories if they don't exist."""
        self.bilans_dir.mkdir(parents=True, exist_ok=True)
        self.week_planning_dir.mkdir(parents=True, exist_ok=True)
        self.workout_templates_dir.mkdir(parents=True, exist_ok=True)

    def validate(self) -> bool:
        """
        Validate data repository structure.

        Returns:
            True if all required files/dirs exist

        Raises:
            FileNotFoundError: If critical files missing
        """
        # Check workouts-history.md exists
        if not self.workouts_history_path.exists():
            raise FileNotFoundError(
                f"workouts-history.md not found in data repo: {self.data_repo_path}\n"
                f"Create it with: touch {self.workouts_history_path}"
            )

        # Ensure directories exist
        self.ensure_directories()

        return True


# Global config instance
_global_config: Optional[DataRepoConfig] = None


def get_data_config() -> DataRepoConfig:
    """
    Get or create global data repository configuration.

    Returns:
        DataRepoConfig instance

    Raises:
        FileNotFoundError: If data repository not found
    """
    global _global_config

    if _global_config is None:
        _global_config = DataRepoConfig()
        _global_config.validate()

    return _global_config


def set_data_config(config: Optional[DataRepoConfig]):
    """
    Set global data repository configuration.

    Useful for testing with temporary paths.

    Args:
        config: DataRepoConfig instance or None to reset
    """
    global _global_config
    _global_config = config


def reset_data_config():
    """Reset global configuration (mainly for testing)."""
    global _global_config
    _global_config = None
