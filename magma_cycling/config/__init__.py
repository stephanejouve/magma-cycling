"""Configuration modules for athlete profile, training thresholds, and logging.

This package consolidates:
- data_repo.py: Data repository paths configuration
- ai_providers.py: AI providers configuration
- intervals.py: Intervals.icu API configuration
- week_reference.py: Week numbering reference
- email_config.py: Email notifications (Brevo)
- withings_config.py: Withings health data
- athlete_profile.py: Athlete characteristics (Sprint R2)
- thresholds.py: Training load thresholds (Sprint R2)
- logging_config.py: Logging configuration (Quick Wins)
"""

# AI providers
from magma_cycling.config.ai_providers import (
    AIProvidersConfig,
    get_ai_config,
    reset_ai_config,
)

# Athlete context for AI prompts
from magma_cycling.config.athlete_context import load_athlete_context

# Athlete profile (Sprint R2)
from magma_cycling.config.athlete_profile import AthleteProfile

# Data repository
from magma_cycling.config.data_repo import (
    DataRepoConfig,
    get_data_config,
    load_json_config,
    reset_data_config,
    set_data_config,
)

# Email (Brevo)
from magma_cycling.config.email_config import (
    EmailConfig,
    get_email_config,
    reset_email_config,
)

# Intervals.icu
from magma_cycling.config.intervals import (
    IntervalsConfig,
    create_intervals_client,
    get_intervals_config,
    reset_intervals_config,
)

# Logging configuration (Quick Wins)
from magma_cycling.config.logging_config import (
    get_logger,
    set_log_level,
    setup_logging,
    setup_mcp_logging,
)

# Training thresholds (Sprint R2)
from magma_cycling.config.thresholds import TrainingThresholds

# Week reference
from magma_cycling.config.week_reference import (
    WeekReferenceConfig,
    get_week_config,
    reset_week_config,
)

# Withings
from magma_cycling.config.withings_config import (
    WithingsConfig,
    create_health_provider,
    create_withings_client,
    get_withings_config,
    reset_withings_config,
)

__all__ = [
    # Data repo config
    "DataRepoConfig",
    "get_data_config",
    "set_data_config",
    "reset_data_config",
    # AI providers config
    "AIProvidersConfig",
    "get_ai_config",
    "reset_ai_config",
    # Intervals.icu config
    "IntervalsConfig",
    "get_intervals_config",
    "reset_intervals_config",
    "create_intervals_client",
    # Withings config
    "WithingsConfig",
    "get_withings_config",
    "reset_withings_config",
    "create_withings_client",
    # Health provider
    "create_health_provider",
    # Week reference config
    "WeekReferenceConfig",
    "get_week_config",
    "reset_week_config",
    # Email config (Brevo)
    "EmailConfig",
    "get_email_config",
    "reset_email_config",
    # Athlete context
    "load_athlete_context",
    # Sprint R2 additions
    "AthleteProfile",
    "TrainingThresholds",
    # Logging
    "setup_logging",
    "setup_mcp_logging",
    "get_logger",
    "set_log_level",
    # Utilities
    "load_json_config",
]
