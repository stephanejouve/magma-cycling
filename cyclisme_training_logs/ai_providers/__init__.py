"""AI Providers for multi-IA analysis support.

This module provides a factory pattern for creating AI analyzer instances
from multiple providers (Clipboard, Claude API, Mistral AI, OpenAI, Ollama).

Examples:
    Create analyzer from factory::

        from cyclisme_training_logs.ai_providers import AIProviderFactory
        from cyclisme_training_logs.config import get_ai_config

        # Get configuration
        config = get_ai_config()

        # Create clipboard analyzer (default, no API required)
        analyzer = AIProviderFactory.create('clipboard', {})

        # Create Claude API analyzer (requires API key)
        claude_config = config.get_provider_config('claude_api')
        analyzer = AIProviderFactory.create('claude_api', claude_config)

Author: Claude Code
Created: 2025-12-25
"""

from .base import AIProvider, AIAnalyzer
from .factory import AIProviderFactory

__all__ = ['AIProvider', 'AIAnalyzer', 'AIProviderFactory']
