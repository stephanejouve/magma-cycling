"""
Configuration modules for athlete profile, training thresholds, and logging.

This package consolidates:
- Original config_base.py: Data repository and AI providers configuration
- athlete_profile.py: Athlete characteristics (Sprint R2)
- thresholds.py: Training load thresholds (Sprint R2)
- logging_config.py: Logging configuration (Quick Wins).
"""

# Original config functions and classes (from config_base.py)

# New Sprint R2 modules
from cyclisme_training_logs.config.athlete_profile import AthleteProfile
from cyclisme_training_logs.config.config_base import (
    AIProvidersConfig,
    DataRepoConfig,
    IntervalsConfig,
    get_ai_config,
    get_data_config,
    get_intervals_config,
    reset_ai_config,
    reset_data_config,
    reset_intervals_config,
    set_data_config,
)

# Logging configuration (Quick Wins)
from cyclisme_training_logs.config.logging_config import get_logger, set_log_level, setup_logging
from cyclisme_training_logs.config.thresholds import TrainingThresholds

__all__ = [
    # Original config
    "DataRepoConfig",
    "AIProvidersConfig",
    "IntervalsConfig",
    "get_data_config",
    "set_data_config",
    "reset_data_config",
    "get_ai_config",
    "reset_ai_config",
    "get_intervals_config",
    "reset_intervals_config",
    # Sprint R2 additions
    "AthleteProfile",
    "TrainingThresholds",
    # Logging
    "setup_logging",
    "get_logger",
    "set_log_level",
]
