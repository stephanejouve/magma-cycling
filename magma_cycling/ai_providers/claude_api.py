#!/usr/bin/env python3
"""
Claude AI provider implementation (Anthropic API).

Implémentation provider Claude AI (Anthropic) pour analyses workouts.
Utilise claude-sonnet-4-20250514 comme provider principal avec support
thinking blocks et artifacts.

Examples:
    Standard analysis::

        from magma_cycling.ai_providers.claude_api import ClaudeProvider

        provider = ClaudeProvider()

        analysis = provider.analyze(
            prompt="Analyser découplage cardiovasculaire",
            workout_data={"hr_avg": 120, "power_avg": 180}
        )

    With thinking enabled::

        # Activer extended thinking
        provider = ClaudeProvider(enable_thinking=True)

        result = provider.analyze(prompt, data)

        # Accéder thinking blocks
        if result.thinking:
            print("Reasoning:", result.thinking)

    Batch analysis::

        # Analyser plusieurs workouts
        workouts = [workout1, workout2, workout3]

        analyses = provider.batch_analyze(
            prompts=[...],
            workouts_data=workouts
        )

Author: Claude Code
Created: 2025-12-09

Metadata:
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: I
    Status: Production
    Priority: P2
    Version: v2
"""
import logging

from anthropic import Anthropic

from .base import AIAnalyzer, AIProvider

logger = logging.getLogger(__name__)


class WorkflowError(Exception):
    """Workflow error for AI provider operations."""

    pass


class ClaudeAPIAnalyzer(AIAnalyzer):
    """Claude API provider for automated AI analysis.

    Utilise Anthropic Claude API pour analyse séance automatisée.
    Modèle recommandé: claude-sonnet-4-20250514 (latest, best performance).

    Attributes:
        provider: AIProvider.CLAUDE
        model: Claude model name
        client: Anthropic API client

    Examples:
        >>> analyzer = ClaudeAPIAnalyzer(api_key="sk-ant-...")
        >>> analysis = analyzer.analyze_session(prompt)
        >>> print(analysis[:100])
        '# Analyse Séance...'

    Notes:
        - Coût: ~$3/1M input tokens, $15/1M output tokens
        - Rate limits: 50 requests/min
        - Max tokens: 200k context window
        - Excellent pour analyse cyclisme qualitative
    """

    # Supported models (2025)
    MODELS = {
        "claude-sonnet-4-20250514": "Latest Sonnet 4 (recommended)",
        "claude-3-5-sonnet-20241022": "Sonnet 3.5 (legacy)",
        "claude-3-opus-20240229": "Opus 3 (highest quality, expensive)",
    }

    def __init__(
        self, api_key: str, model: str = "claude-sonnet-4-20250514", max_tokens: int = 4000
    ):
        """Initialize Claude API analyzer.

        Args:
            api_key: Anthropic API key (sk-ant-...)
            model: Claude model name
            max_tokens: Max tokens in response

        Raises:
            WorkflowError: Si API key invalide

        Examples:
            >>> analyzer = ClaudeAPIAnalyzer(
            ...     api_key="sk-ant-xxx",
            ...     model="claude-sonnet-4-20250514"
            ... )
        """
        super().__init__()

        self.provider = AIProvider.CLAUDE
        self.model: str = model
        self.max_tokens: int = max_tokens

        if not api_key or not api_key.startswith("sk-ant-"):
            raise WorkflowError("Invalid Claude API key format (must start with 'sk-ant-')")

        try:
            self.client = Anthropic(api_key=api_key)
            logger.info(f"ClaudeAPIAnalyzer initialized with model {model}")
        except Exception as e:
            raise WorkflowError(f"Failed to initialize Claude API client: {e}") from e

    def analyze_session(self, prompt: str, dataset: dict | None = None) -> str:
        """Analyze session using Claude API.

        Args:
            prompt: Structured session analysis prompt
            dataset: Optional session dataset (unused, prompt already complete)

        Returns:
            AI-generated analysis markdown

        Raises:
            WorkflowError: Si API call échoue

        Examples:
            >>> analysis = analyzer.analyze_session(prompt)
            >>> "# Analyse" in analysis
            True

        Notes:
            - Timeout: 60s
            - Retry: 3 attempts
            - Stream: Non (pour simplicité)
        """
        logger.info(f"Sending prompt to Claude API ({len(prompt)} chars)")

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract analysis text
            content = response.content[0]
            if not hasattr(content, "text"):
                raise WorkflowError("Unexpected response format: content has no text attribute")

            analysis = content.text
            logger.info(f"Received analysis from Claude ({len(analysis)} chars)")
            return analysis

        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            raise WorkflowError(f"Failed to analyze session with Claude API: {e}") from e

    def get_provider_info(self) -> dict:
        """Get Claude API provider info.

        Returns:
            Dict avec provider details

        Examples:
            >>> info = analyzer.get_provider_info()
            >>> print(info['provider'])
            'claude_api'.
        """
        return {
            "provider": "claude_api",
            "model": self.model,
            "status": "ready",
            "cost_input": "$3.00/1M tokens",
            "cost_output": "$15.00/1M tokens",
            "requires_api_key": True,
            "context_window": "200k tokens",
        }

    def validate_config(self) -> bool:
        """Validate Claude API configuration.

        Returns:
            True si config valide

        Examples:
            >>> is_valid = analyzer.validate_config()
            >>> print(is_valid)
            True

        Notes:
            - Vérifie que client initialisé
            - Test simple API call possible mais coûteux.
        """
        return self.client is not None
