"""
AI providers factory for multi-provider analysis support.
Factory pattern pour support multi-providers IA (Claude, Mistral, OpenAI,
Gemini, Ollama). Fournit interface unifiée pour analyses workouts avec
fallback automatique entre providers.

Examples:
    Get AI provider::

        from cyclisme_training_logs.ai_providers import get_provider

        # Provider par défaut (Claude)
        provider = get_provider()

        # Provider spécifique
        mistral = get_provider('mistral')
        openai = get_provider('openai')

    Analyze with fallback::

        # Essayer Claude, fallback Mistral
        providers = ['claude', 'mistral']

        for provider_name in providers:
            try:
                provider = get_provider(provider_name)
                analysis = provider.analyze(workout_data)
                break
            except Exception as e:
                print(f"{provider_name} failed: {e}")
                continue

    List available providers::

        from cyclisme_training_logs.ai_providers import list_providers

        providers = list_providers()
        print(f"Available: {', '.join(providers)}")

Author: Claude Code
Created: 2024-11-XX
Updated: 2025-12-26 (Standardization Prompt 3 Priority 2)

Metadata:
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: I
    Status: Production
    Priority: P2
    Version: v2
"""
from .base import AIAnalyzer, AIProvider
from .factory import AIProviderFactory

__all__ = ["AIProvider", "AIAnalyzer", "AIProviderFactory"]
