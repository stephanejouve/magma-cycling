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
        self.default_provider = os.getenv('DEFAULT_AI_PROVIDER', 'clipboard')
        self.enable_fallback = os.getenv('ENABLE_AI_FALLBACK', 'true').lower() == 'true'
        self.fallback_priority = ['claude_api', 'mistral_api', 'openai', 'ollama', 'clipboard']

        # Provider-specific configs
        self._configs = {
            'clipboard': {},
            'claude_api': {
                'claude_api_key': os.getenv('CLAUDE_API_KEY'),
                'claude_model': os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-20250514')
            },
            'mistral_api': {
                'mistral_api_key': os.getenv('MISTRAL_API_KEY'),
                'mistral_model': os.getenv('MISTRAL_MODEL', 'mistral-large-latest')
            },
            'openai': {
                'openai_api_key': os.getenv('OPENAI_API_KEY'),
                'openai_model': os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')
            },
            'ollama': {
                'ollama_base_url': os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
                'ollama_model': os.getenv('OLLAMA_MODEL', 'mistral:7b')
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

        config = self._configs.get(provider, {})
        api_key_field = f'{provider}_api_key'
        return bool(config.get(api_key_field))

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
