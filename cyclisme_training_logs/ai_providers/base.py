#!/usr/bin/env python3
"""
Base classes and enums for AI analysis providers.

Définit interface abstraite pour intégration multi-providers AI
(Clipboard, Claude API, OpenAI, Mistral AI, Ollama).

Examples:
    Implement custom provider::

        from src.ai.base import AIAnalyzer

        class CustomAnalyzer(AIAnalyzer):
            def analyze_session(self, prompt: str) -> str:
                # Custom implementation
                return analysis_result

Author: Claude Code
Created: 2025-12-09.
"""
from abc import ABC, abstractmethod
from enum import Enum


class AIProvider(Enum):
    """Supported AI analysis providers.

    Attributes:
        CLIPBOARD: Manual copy/paste workflow (no API, free)
        CLAUDE: Claude API (Anthropic) - sonnet-4
        OPENAI: OpenAI GPT-4 Turbo
        MISTRAL: Mistral AI API (best price/performance)
        OLLAMA: Local LLM server (free, privacy)

    Examples:
        >>> provider = AIProvider.CLIPBOARD
        >>> provider.value
        'clipboard'.
    """

    CLIPBOARD = "clipboard"
    CLAUDE = "claude_api"
    OPENAI = "openai"
    MISTRAL = "mistral_api"
    OLLAMA = "ollama"


class AIAnalyzer(ABC):
    """Abstract base class for AI analysis providers.

    Toutes les implémentations AI (Clipboard, Claude API, etc.)
    doivent hériter de cette classe et implémenter analyze_session().

    Attributes:
        provider: Type de provider (AIProvider enum)
        model: Nom du modèle utilisé (optionnel)

    Examples:
        >>> analyzer = ClipboardAnalyzer()
        >>> result = analyzer.analyze_session(prompt)
        'Analysis copied to clipboard'.
    """

    def __init__(self):
        """Initialize AI analyzer base."""
        self.provider: AIProvider | None = None

        self.model: str | None = None

    @abstractmethod
    def analyze_session(self, prompt: str, dataset: dict | None = None) -> str:
        """Analyze session with AI provider.

        Args:
            prompt: Structured prompt markdown for AI analysis
            dataset: Optional session dataset for context

        Returns:
            AI-generated analysis as markdown string

        Raises:
            NotImplementedError: Si méthode non implémentée

        Examples:
            >>> result = analyzer.analyze_session(prompt)
            >>> print(result[:100])
            '# Session Analysis...'

        Notes:
            - Clipboard provider: copie prompt, retourne instructions
            - API providers: envoient prompt, retournent réponse
            - Ollama: envoie à serveur local, retourne réponse
        """
        raise NotImplementedError("Subclass must implement analyze_session()")

    def get_provider_info(self) -> dict:
        """Get provider information.

        Returns:
            Dict avec provider name, model, et status

        Examples:
            >>> info = analyzer.get_provider_info()
            >>> print(info['provider'])
            'clipboard'.
        """
        return {
            "provider": self.provider.value if self.provider else "unknown",
            "model": self.model or "default",
            "status": "ready",
        }

    def validate_config(self) -> bool:
        """Validate provider configuration.

        Returns:
            True si configuration valide, False sinon

        Examples:
            >>> is_valid = analyzer.validate_config()
            >>> print(is_valid)
            True

        Notes:
            - Clipboard: toujours valide (pas de config)
            - API providers: vérifient api_key présente.
        """
        return True  # Override in subclasses if needed
