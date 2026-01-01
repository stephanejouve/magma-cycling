"""
Configuration modules for athlete profile and training thresholds.

This package consolidates:
- Original config_base.py: Data repository and AI providers configuration
- athlete_profile.py: Athlete characteristics (Sprint R2)
- thresholds.py: Training load thresholds (Sprint R2)
"""

# Original config functions and classes (from config_base.py)
from cyclisme_training_logs.config.config_base import (
    DataRepoConfig,
    AIProvidersConfig,
    IntervalsConfig,
    get_data_config,
    set_data_config,
    reset_data_config,
    get_ai_config,
    reset_ai_config,
    get_intervals_config,
    reset_intervals_config,
)

# New Sprint R2 modules
from cyclisme_training_logs.config.athlete_profile import AthleteProfile
from cyclisme_training_logs.config.thresholds import TrainingThresholds

__all__ = [
    # Original config
    'DataRepoConfig',
    'AIProvidersConfig',
    'IntervalsConfig',
    'get_data_config',
    'set_data_config',
    'reset_data_config',
    'get_ai_config',
    'reset_ai_config',
    'get_intervals_config',
    'reset_intervals_config',
    # Sprint R2 additions
    'AthleteProfile',
    'TrainingThresholds',
]
