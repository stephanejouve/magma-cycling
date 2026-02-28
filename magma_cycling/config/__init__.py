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
from magma_cycling.config.athlete_profile import AthleteProfile
from magma_cycling.config.config_base import (
    AIProvidersConfig,
    DataRepoConfig,
    EmailConfig,
    IntervalsConfig,
    WeekReferenceConfig,
    WithingsConfig,
    create_health_provider,
    create_intervals_client,
    create_withings_client,
    get_ai_config,
    get_data_config,
    get_email_config,
    get_intervals_config,
    get_week_config,
    get_withings_config,
    load_json_config,
    reset_ai_config,
    reset_data_config,
    reset_email_config,
    reset_intervals_config,
    reset_week_config,
    reset_withings_config,
    set_data_config,
)

# Logging configuration (Quick Wins)
from magma_cycling.config.logging_config import (
    get_logger,
    set_log_level,
    setup_logging,
)
from magma_cycling.config.thresholds import TrainingThresholds

__all__ = [
    # Original config
    "DataRepoConfig",
    "AIProvidersConfig",
    "IntervalsConfig",
    "WeekReferenceConfig",
    "EmailConfig",
    "WithingsConfig",
    "get_data_config",
    "set_data_config",
    "reset_data_config",
    "get_ai_config",
    "reset_ai_config",
    "get_intervals_config",
    "reset_intervals_config",
    "get_week_config",
    "reset_week_config",
    "get_email_config",
    "reset_email_config",
    "get_withings_config",
    "reset_withings_config",
    # DRY helpers
    "create_intervals_client",
    "create_withings_client",
    "create_health_provider",
    "load_json_config",
    # Sprint R2 additions
    "AthleteProfile",
    "TrainingThresholds",
    # Logging
    "setup_logging",
    "get_logger",
    "set_log_level",
]
