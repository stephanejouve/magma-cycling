"""
Configuration centrale pour séparation code/données
Module de configuration gérant la séparation entre code (cyclisme-training-logs)
et données athlète (training-logs externe). Configure les chemins vers le dépôt
de données externe via variable d'environnement TRAINING_DATA_REPO, avec fallback
vers ~/training-logs par défaut.

Examples:
    Command-line usage::

        # Configuration via variable d'environnement
        export TRAINING_DATA_REPO=~/training-logs
        poetry run workflow-coach

    Programmatic usage::

        from cyclisme_training_logs.config import get_data_config

        # Récupération configuration (singleton)
        config = get_data_config()

        # Accès aux chemins configurés
        data_path = config.data_repo_path
        workouts_path = config.workouts_history_path
        context_path = config.context_path

        print(f"Data repo: {data_path}")
        print(f"Workouts: {workouts_path}")

    Advanced usage::

        from cyclisme_training_logs.config import DataRepoConfig, reset_data_config

        # Configuration personnalisée pour tests
        custom_config = DataRepoConfig(data_repo_path="/tmp/test-data")

        # Reset singleton (utile pour tests)
        reset_data_config()

Author: Claude Code
Created: 2024-12-23
Updated: 2025-12-26 (Added Gartner TIME tags)

Metadata:
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: I
    Status: Production
    Priority: P0
    Version: v2
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


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

        # Duplicate detection settings (paranoid mode for backfill testing)
        self.paranoid_duplicate_check = True   # Check après chaque insertion
        self.auto_fix_duplicates = False       # Auto-suppression ou erreur (fail-fast)
        self.duplicate_check_window = 50        # Lignes à scanner (optimisation)

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


# ============================================================================
# AI Providers Configuration
# ============================================================================

class AIProvidersConfig:
    """Configuration for AI providers.

    Manages configuration for multiple AI providers (clipboard, Claude API,
    Mistral AI, OpenAI, Ollama) with auto-detection and fallback chain.

    Attributes:
        default_provider: Default provider if not specified (from env or 'clipboard')
        enable_fallback: Whether to fallback to next provider on failure
        fallback_priority: Priority order for provider fallback chain

    Examples:
        >>> config = get_ai_config()
        >>> providers = config.get_available_providers()
        >>> print(providers)
        ['claude_api', 'mistral_api', 'clipboard']
    """

    def __init__(self):
        """Initialize AI providers configuration from environment variables."""
        # General settings
        self.default_provider = os.getenv('DEFAULT_AI_PROVIDER', 'clipboard')
        self.enable_fallback = os.getenv('ENABLE_AI_FALLBACK', 'true').lower() == 'true'
        self.fallback_priority = ['claude_api', 'mistral_api', 'openai', 'ollama', 'clipboard']

        # Mistral AI - Direct attributes for easy access
        self.mistral_api_key = os.getenv('MISTRAL_API_KEY')
        self.mistral_model = os.getenv('MISTRAL_MODEL', 'mistral-large-latest')
        self.mistral_temperature = float(os.getenv('MISTRAL_TEMPERATURE', '0.7'))
        self.mistral_max_tokens = int(os.getenv('MISTRAL_MAX_TOKENS', '4000'))
        self.mistral_timeout = int(os.getenv('MISTRAL_TIMEOUT', '60'))

        # Claude API (Anthropic) - Direct attributes
        self.claude_api_key = os.getenv('CLAUDE_API_KEY')
        self.claude_model = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-20250514')

        # OpenAI - Direct attributes
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')

        # Ollama (local LLMs) - Direct attributes
        self.ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'mistral:7b')

        # Provider-specific configs (for backward compatibility with factory)
        self._configs = {
            'clipboard': {},
            'claude_api': {
                'claude_api_key': self.claude_api_key,
                'claude_model': self.claude_model
            },
            'mistral_api': {
                'mistral_api_key': self.mistral_api_key,
                'mistral_model': self.mistral_model,
                'mistral_temperature': self.mistral_temperature,
                'mistral_max_tokens': self.mistral_max_tokens,
                'mistral_timeout': self.mistral_timeout
            },
            'openai': {
                'openai_api_key': self.openai_api_key,
                'openai_model': self.openai_model
            },
            'ollama': {
                'ollama_base_url': self.ollama_base_url,
                'ollama_model': self.ollama_model
            }
        }

    def is_provider_configured(self, provider: str) -> bool:
        """Check if provider has valid configuration.

        Args:
            provider: Provider name (clipboard, claude_api, etc.)

        Returns:
            True if provider is configured and ready to use

        Examples:
            >>> config = get_ai_config()
            >>> config.is_provider_configured('clipboard')
            True
            >>> config.is_provider_configured('claude_api')
            False  # If CLAUDE_API_KEY not set
        """
        if provider == 'clipboard':
            return True  # Always available
        if provider == 'ollama':
            return True  # Assume localhost available

        # Check API key from direct attributes
        if provider == 'claude_api':
            return bool(self.claude_api_key)
        elif provider == 'mistral_api':
            return bool(self.mistral_api_key)
        elif provider == 'openai':
            return bool(self.openai_api_key)

        return False

    def get_available_providers(self) -> list[str]:
        """Return list of configured providers in priority order.

        Returns:
            List of provider names that are configured

        Examples:
            >>> config = get_ai_config()
            >>> config.get_available_providers()
            ['claude_api', 'mistral_api', 'clipboard']
        """
        available = []
        for provider in self.fallback_priority:
            if self.is_provider_configured(provider):
                available.append(provider)
        return available

    def get_provider_config(self, provider: str) -> dict:
        """Get configuration dict for specific provider.

        Args:
            provider: Provider name

        Returns:
            Configuration dictionary for the provider

        Examples:
            >>> config = get_ai_config()
            >>> cfg = config.get_provider_config('claude_api')
            >>> print(cfg.get('claude_model'))
            'claude-sonnet-4-20250514'
        """
        return self._configs.get(provider, {})

    def get_fallback_chain(self) -> list[str]:
        """Get fallback chain based on priority and availability.

        Returns:
            List of providers in fallback order

        Examples:
            >>> config = get_ai_config()
            >>> config.get_fallback_chain()
            ['claude_api', 'mistral_api', 'ollama', 'clipboard']
        """
        if not self.enable_fallback:
            return [self.default_provider]
        return self.get_available_providers()


# Global AI config instance
_ai_config_instance: Optional[AIProvidersConfig] = None


def get_ai_config() -> AIProvidersConfig:
    """Get singleton instance of AI providers config.

    Returns:
        AIProvidersConfig instance

    Examples:
        >>> config = get_ai_config()
        >>> print(config.default_provider)
        'clipboard'
    """
    global _ai_config_instance
    if _ai_config_instance is None:
        _ai_config_instance = AIProvidersConfig()
    return _ai_config_instance


def reset_ai_config():
    """Reset AI config singleton (useful for tests).

    Examples:
        >>> reset_ai_config()
        >>> config = get_ai_config()  # Creates new instance
    """
    global _ai_config_instance
    _ai_config_instance = None


# ============================================================================
# Intervals.icu API Configuration
# ============================================================================

class IntervalsConfig:
    """Configuration for Intervals.icu API.

    Manages athlete ID and API key for Intervals.icu integration.
    Uses VITE_ prefix for React compatibility.

    Attributes:
        athlete_id: Intervals.icu athlete ID (format: i123456)
        api_key: Intervals.icu API key
        base_url: API base URL (default: https://intervals.icu/api/v1)

    Examples:
        >>> config = get_intervals_config()
        >>> print(config.athlete_id)
        'i151223'
        >>> print(config.is_configured())
        True
    """

    def __init__(self):
        """Initialize Intervals.icu configuration from environment variables."""
        # Read from VITE_ prefixed variables (React compatibility)
        self.athlete_id = os.getenv('VITE_INTERVALS_ATHLETE_ID')
        self.api_key = os.getenv('VITE_INTERVALS_API_KEY')
        self.base_url = os.getenv('VITE_INTERVALS_BASE_URL', 'https://intervals.icu/api/v1')

    def is_configured(self) -> bool:
        """Check if Intervals.icu API is properly configured.

        Returns:
            True if both athlete_id and api_key are set

        Examples:
            >>> config = get_intervals_config()
            >>> if config.is_configured():
            ...     # Use API
            ...     pass
            ... else:
            ...     # Fallback mode
            ...     pass
        """
        return bool(self.athlete_id and self.api_key)

    def get_headers(self) -> dict:
        """Get authentication headers for Intervals.icu API.

        Returns:
            Dict with Authorization header using Basic auth

        Examples:
            >>> config = get_intervals_config()
            >>> headers = config.get_headers()
            >>> # Use with requests
            >>> import requests
            >>> response = requests.get(url, headers=headers)
        """
        if not self.is_configured():
            raise ValueError("Intervals.icu API not configured")

        import base64
        auth_string = f"API_KEY:{self.api_key}"
        auth_bytes = auth_string.encode('ascii')
        base64_bytes = base64.b64encode(auth_bytes)
        base64_string = base64_bytes.decode('ascii')

        return {
            'Authorization': f'Basic {base64_string}',
            'Content-Type': 'application/json'
        }


# Global Intervals config instance
_intervals_config_instance: Optional[IntervalsConfig] = None


def get_intervals_config() -> IntervalsConfig:
    """Get singleton instance of Intervals.icu config.

    Returns:
        IntervalsConfig instance

    Examples:
        >>> config = get_intervals_config()
        >>> print(config.athlete_id)
        'i151223'
    """
    global _intervals_config_instance
    if _intervals_config_instance is None:
        _intervals_config_instance = IntervalsConfig()
    return _intervals_config_instance


def reset_intervals_config():
    """Reset Intervals config singleton (useful for tests).

    Examples:
        >>> reset_intervals_config()
        >>> config = get_intervals_config()  # Creates new instance
    """
    global _intervals_config_instance
    _intervals_config_instance = None


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Data repo config
    'DataRepoConfig',
    'get_data_config',
    'set_data_config',
    'reset_data_config',
    # AI providers config
    'AIProvidersConfig',
    'get_ai_config',
    'reset_ai_config',
    # Intervals.icu config
    'IntervalsConfig',
    'get_intervals_config',
    'reset_intervals_config',
]
