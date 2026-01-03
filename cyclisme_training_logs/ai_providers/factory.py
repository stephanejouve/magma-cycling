#!/usr/bin/env python3
"""
AI Analyzer Factory for provider selection.

Factory pattern pour créer instances AI analyzers
basé sur configuration provider.

Examples:
    Create analyzer from config::

        from src.ai.factory import AIAnalyzerFactory

        # Clipboard (default)
        analyzer = AIAnalyzerFactory.create('clipboard', {})

        # Claude API
        analyzer = AIAnalyzerFactory.create('claude_api', {
            'claude_api_key': 'sk-ant-...',
            'claude_model': 'claude-sonnet-4-20250514'
        })

        # Mistral API (best price/performance)
        analyzer = AIAnalyzerFactory.create('mistral_api', {
            'mistral_api_key': '...',
            'mistral_model': 'mistral-large-latest'
        })

Author: Claude Code
Created: 2025-12-09
"""

import logging
from typing import Any

from .base import AIAnalyzer, AIProvider
from .claude_api import ClaudeAPIAnalyzer
from .clipboard import ClipboardAnalyzer
from .mistral_api import MistralAPIAnalyzer
from .ollama import OllamaAnalyzer
from .openai_api import OpenAIAnalyzer


class ConfigError(Exception):
    """Configuration error for AI providers."""

    pass


logger = logging.getLogger(__name__)


class AIProviderFactory:
    """Factory for creating AI analyzer instances.

    Pattern factory pour sélection provider AI basé sur config.
    Supporte 5 providers: clipboard, claude_api, openai, mistral_api, ollama.

    Examples:
        >>> # Clipboard (default, no API key)
        >>> analyzer = AIAnalyzerFactory.create('clipboard', {})

        >>> # Claude API
        >>> analyzer = AIAnalyzerFactory.create('claude_api', {
        ...     'claude_api_key': 'sk-ant-...'
        ... })

        >>> # Mistral (best value)
        >>> analyzer = AIAnalyzerFactory.create('mistral_api', {
        ...     'mistral_api_key': '...'
        ... })

    Notes:
        - clipboard: Default, no config needed
        - API providers: Require api_key in config
        - ollama: Requires local server running
    """

    @staticmethod
    def create(provider: str, config: dict[str, Any]) -> AIAnalyzer:
        """Create AI analyzer instance from provider name and config.

        Args:
            provider: Provider name (clipboard, claude_api, openai, mistral_api, ollama)
            config: Configuration dict avec API keys et options

        Returns:
            AIAnalyzer instance configurée

        Raises:
            ConfigError: Si provider inconnu ou config invalide

        Examples:
            >>> # Clipboard (immediate use, no API)
            >>> analyzer = AIAnalyzerFactory.create('clipboard', {})

            >>> # Claude API
            >>> analyzer = AIAnalyzerFactory.create('claude_api', {
            ...     'claude_api_key': 'sk-ant-xxx',
            ...     'claude_model': 'claude-sonnet-4-20250514'
            ... })

            >>> # Mistral (recommended value)
            >>> analyzer = AIAnalyzerFactory.create('mistral_api', {
            ...     'mistral_api_key': 'xxx',
            ...     'mistral_model': 'mistral-large-latest'
            ... })

            >>> # OpenAI
            >>> analyzer = AIAnalyzerFactory.create('openai', {
            ...     'openai_api_key': 'sk-xxx'
            ... })

            >>> # Ollama (local, free)
            >>> analyzer = AIAnalyzerFactory.create('ollama', {
            ...     'ollama_host': 'http://localhost:11434',
            ...     'ollama_model': 'mistral:7b'
            ... })

        Notes:
            - Provider names case-insensitive
            - Config keys avec prefix provider name
            - Default models si non spécifiés
        """
        # Normalize provider name
        provider = provider.lower().strip()

        logger.info(f"Creating AI analyzer for provider: {provider}")

        # Validate provider exists
        try:
            provider_enum = AIProvider(provider)
        except ValueError:
            valid_providers = [p.value for p in AIProvider]
            raise ConfigError(
                f"Unknown AI provider: {provider}. "
                f"Valid providers: {', '.join(valid_providers)}"
            )

        # === CLIPBOARD (Priority - No API) ===
        if provider_enum == AIProvider.CLIPBOARD:
            logger.info("Creating ClipboardAnalyzer (manual workflow)")
            return ClipboardAnalyzer()

        # === CLAUDE API ===
        elif provider_enum == AIProvider.CLAUDE:
            api_key = config.get("claude_api_key")
            if not api_key:
                raise ConfigError(
                    "Claude API key required. " "Set CLAUDE_API_KEY in .env or pass in config."
                )

            model = config.get("claude_model", "claude-sonnet-4-20250514")
            max_tokens = config.get("claude_max_tokens", 4000)

            logger.info(f"Creating ClaudeAPIAnalyzer (model: {model})")
            return ClaudeAPIAnalyzer(api_key=api_key, model=model, max_tokens=max_tokens)

        # === MISTRAL API (Recommended Value) ===
        elif provider_enum == AIProvider.MISTRAL:
            api_key = config.get("mistral_api_key")
            if not api_key:
                raise ConfigError(
                    "Mistral API key required. " "Set MISTRAL_API_KEY in .env or pass in config."
                )

            model = config.get("mistral_model", "mistral-large-latest")
            temperature = config.get("mistral_temperature", 0.7)
            max_tokens = config.get("mistral_max_tokens", 4000)
            timeout = config.get("mistral_timeout", 60)

            logger.info(f"Creating MistralAPIAnalyzer (model: {model}, temperature: {temperature})")
            return MistralAPIAnalyzer(
                api_key=api_key,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )

        # === OPENAI ===
        elif provider_enum == AIProvider.OPENAI:
            api_key = config.get("openai_api_key")
            if not api_key:
                raise ConfigError(
                    "OpenAI API key required. " "Set OPENAI_API_KEY in .env or pass in config."
                )

            model = config.get("openai_model", "gpt-4-turbo")

            logger.info(f"Creating OpenAIAnalyzer (model: {model})")
            return OpenAIAnalyzer(api_key=api_key, model=model)

        # === OLLAMA (Local) ===
        elif provider_enum == AIProvider.OLLAMA:
            host = config.get("ollama_host", "http://localhost:11434")
            model = config.get("ollama_model", "mistral:7b")

            logger.info(f"Creating OllamaAnalyzer (model: {model}, host: {host})")
            return OllamaAnalyzer(host=host, model=model)

        else:
            # Should never reach here due to enum validation above
            raise ConfigError(f"Provider not implemented: {provider}")

    @staticmethod
    def get_available_providers() -> dict[str, str]:
        """Get dict of available providers with descriptions.

        Returns:
            Dict {provider_name: description}

        Examples:
            >>> providers = AIAnalyzerFactory.get_available_providers()
            >>> print(providers['clipboard'])
            'Manual copy/paste (free, no API)'
        """
        return {
            "clipboard": "Manual copy/paste (free, no API) - Default",
            "claude_api": "Claude Sonnet 4 ($3/1M in, $15/1M out)",
            "mistral_api": "Mistral Large ($2/1M in, $6/1M out) - Best value 🎯",
            "openai": "OpenAI GPT-4 Turbo ($10/1M in, $30/1M out)",
            "ollama": "Local LLMs (free, unlimited, private) 🔒",
        }

    @staticmethod
    def validate_provider_config(provider: str, config: dict[str, Any]) -> tuple[bool, str]:
        """Validate config for specific provider.

        Args:
            provider: Provider name
            config: Configuration dict

        Returns:
            Tuple (is_valid, message)

        Examples:
            >>> is_valid, msg = AIAnalyzerFactory.validate_provider_config(
            ...     'claude_api',
            ...     {'claude_api_key': 'sk-ant-xxx'}
            ... )
            >>> print(is_valid)
            True
        """
        provider = provider.lower().strip()

        # Clipboard always valid
        if provider == "clipboard":
            return True, "Clipboard ready (no config needed)"

        # Claude API
        if provider == "claude_api":
            if not config.get("claude_api_key"):
                return False, "CLAUDE_API_KEY missing in config"
            return True, "Claude API config valid"

        # Mistral API
        if provider == "mistral_api":
            if not config.get("mistral_api_key"):
                return False, "MISTRAL_API_KEY missing in config"
            return True, "Mistral API config valid"

        # OpenAI
        if provider == "openai":
            if not config.get("openai_api_key"):
                return False, "OPENAI_API_KEY missing in config"
            return True, "OpenAI API config valid"

        # Ollama
        if provider == "ollama":
            # Ollama needs no API key, just server running
            return True, "Ollama config valid (check server running)"

        return False, f"Unknown provider: {provider}"
