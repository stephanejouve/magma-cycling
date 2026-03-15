"""Configuration centrale — re-exports pour rétrocompatibilité.

Ce module re-exporte toutes les classes et fonctions depuis les modules
spécialisés. Les imports existants (`from magma_cycling.config.config_base import X`)
continuent de fonctionner.

Les modules source sont:
- data_repo.py: DataRepoConfig, chemins data repository
- ai_providers.py: AIProvidersConfig, providers AI
- intervals.py: IntervalsConfig, API Intervals.icu
- week_reference.py: WeekReferenceConfig, numérotation semaines
- email_config.py: EmailConfig, notifications Brevo
- withings_config.py: WithingsConfig, API Withings
"""

from magma_cycling.config.ai_providers import (  # noqa: F401
    AIProvidersConfig,
    get_ai_config,
    reset_ai_config,
)
from magma_cycling.config.data_repo import (  # noqa: F401
    DataRepoConfig,
    get_data_config,
    load_json_config,
    reset_data_config,
    set_data_config,
)
from magma_cycling.config.email_config import (  # noqa: F401
    EmailConfig,
    get_email_config,
    reset_email_config,
)
from magma_cycling.config.intervals import (  # noqa: F401
    IntervalsConfig,
    create_intervals_client,
    get_intervals_config,
    reset_intervals_config,
)
from magma_cycling.config.week_reference import (  # noqa: F401
    WeekReferenceConfig,
    get_week_config,
    reset_week_config,
)
from magma_cycling.config.withings_config import (  # noqa: F401
    WithingsConfig,
    create_health_provider,
    create_withings_client,
    get_withings_config,
    reset_withings_config,
)

__all__ = [
    "DataRepoConfig",
    "get_data_config",
    "set_data_config",
    "reset_data_config",
    "AIProvidersConfig",
    "get_ai_config",
    "reset_ai_config",
    "IntervalsConfig",
    "get_intervals_config",
    "reset_intervals_config",
    "create_intervals_client",
    "WeekReferenceConfig",
    "get_week_config",
    "reset_week_config",
    "EmailConfig",
    "get_email_config",
    "reset_email_config",
    "WithingsConfig",
    "get_withings_config",
    "reset_withings_config",
    "create_withings_client",
    "create_health_provider",
    "load_json_config",
]
