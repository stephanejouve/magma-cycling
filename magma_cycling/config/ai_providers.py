"""AI providers configuration.

Manages configuration for multiple AI providers (clipboard, Claude API,
Mistral AI, OpenAI, Ollama) with auto-detection and fallback chain.
"""

import os


class AIProvidersConfig:
    """Configuration for AI providers.

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
        self.default_provider = os.getenv("DEFAULT_AI_PROVIDER", "clipboard")
        self.enable_fallback = os.getenv("ENABLE_AI_FALLBACK", "true").lower() == "true"
        self.fallback_priority = ["claude_api", "mistral_api", "openai", "ollama", "clipboard"]

        # Mistral AI
        self.mistral_api_key = os.getenv("MISTRAL_API_KEY")
        self.mistral_model = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
        self.mistral_temperature = float(os.getenv("MISTRAL_TEMPERATURE", "0.7"))
        self.mistral_max_tokens = int(os.getenv("MISTRAL_MAX_TOKENS", "4000"))
        self.mistral_timeout = int(os.getenv("MISTRAL_TIMEOUT", "60"))

        # Claude API (Anthropic)
        self.claude_api_key = os.getenv("CLAUDE_API_KEY")
        self.claude_model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

        # OpenAI
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")

        # Ollama (local LLMs)
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "mistral:7b")

        # Provider-specific configs (for backward compatibility with factory)
        self._configs = {
            "clipboard": {},
            "claude_api": {
                "claude_api_key": self.claude_api_key,
                "claude_model": self.claude_model,
            },
            "mistral_api": {
                "mistral_api_key": self.mistral_api_key,
                "mistral_model": self.mistral_model,
                "mistral_temperature": self.mistral_temperature,
                "mistral_max_tokens": self.mistral_max_tokens,
                "mistral_timeout": self.mistral_timeout,
            },
            "openai": {"openai_api_key": self.openai_api_key, "openai_model": self.openai_model},
            "ollama": {"ollama_base_url": self.ollama_base_url, "ollama_model": self.ollama_model},
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
            False  # If CLAUDE_API_KEY not set.
        """
        if provider == "clipboard":
            return True
        if provider == "ollama":
            return True

        if provider == "claude_api":
            return bool(self.claude_api_key)
        elif provider == "mistral_api":
            return bool(self.mistral_api_key)
        elif provider == "openai":
            return bool(self.openai_api_key)

        return False

    def get_available_providers(self) -> list[str]:
        """Return list of configured providers in priority order.

        Returns:
            List of provider names that are configured

        Examples:
            >>> config = get_ai_config()
            >>> config.get_available_providers()
            ['claude_api', 'mistral_api', 'clipboard'].
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
            'claude-sonnet-4-20250514'.
        """
        return self._configs.get(provider, {})

    def get_fallback_chain(self) -> list[str]:
        """Get fallback chain based on priority and availability.

        Returns:
            List of providers in fallback order

        Examples:
            >>> config = get_ai_config()
            >>> config.get_fallback_chain()
            ['claude_api', 'mistral_api', 'ollama', 'clipboard'].
        """
        if not self.enable_fallback:
            return [self.default_provider]
        return self.get_available_providers()


# Global AI config instance
_ai_config_instance: AIProvidersConfig | None = None


def get_ai_config() -> AIProvidersConfig:
    """Get singleton instance of AI providers config.

    Returns:
        AIProvidersConfig instance

    Examples:
        >>> config = get_ai_config()
        >>> print(config.default_provider)
        'clipboard'.
    """
    global _ai_config_instance

    if _ai_config_instance is None:
        _ai_config_instance = AIProvidersConfig()
    return _ai_config_instance


def reset_ai_config():
    """Reset AI config singleton (useful for tests).

    Examples:
        >>> reset_ai_config()
        >>> config = get_ai_config()  # Creates new instance.
    """
    global _ai_config_instance
    _ai_config_instance = None
