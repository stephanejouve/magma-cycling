#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mistral AI API integration.

Provider Mistral AI avec meilleur rapport qualité/prix pour
analyse séance cyclisme (3x moins cher que Claude).

Examples:
    Use Mistral API::

        from src.ai.mistral_api import MistralAPIAnalyzer

        analyzer = MistralAPIAnalyzer(
            api_key="...",
            model="mistral-large-latest"
        )
        analysis = analyzer.analyze_session(prompt)

Author: Claude Code
Created: 2025-12-09
"""

import logging
from typing import Optional
from mistralai.client import MistralClient

from .base import AIAnalyzer, AIProvider


logger = logging.getLogger(__name__)


class WorkflowError(Exception):
    """Workflow error for AI provider operations."""
    pass


class MistralAPIAnalyzer(AIAnalyzer):
    """Mistral AI API provider for cost-effective analysis.

    Meilleur rapport qualité/prix pour analyse séance.
    Mistral Large: $2/1M input, $6/1M output (3x cheaper than Claude).

    Attributes:
        provider: AIProvider.MISTRAL
        model: Mistral model name
        client: Mistral API client

    Examples:
        >>> analyzer = MistralAPIAnalyzer(api_key="...")
        >>> analysis = analyzer.analyze_session(prompt)
        >>> print(analysis[:100])
        '# Analyse Séance...'

    Notes:
        - Coût: ~$2/1M input tokens, $6/1M output tokens
        - Qualité: comparable GPT-4
        - Context: 32k tokens
        - Excellent rapport qualité/prix 🎯
    """

    # Supported models (2025)
    MODELS = {
        "mistral-large-latest": "Large (best performance, $2/1M)",
        "mistral-medium-latest": "Medium (balanced, $1.5/1M)",
        "mistral-small-latest": "Small (fast, $0.5/1M)",
        "open-mistral-7b": "7B (free tier, basic)"
    }

    def __init__(
        self,
        api_key: str,
        model: str = "mistral-large-latest",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        timeout: int = 60
    ):
        """Initialize Mistral API analyzer.

        Args:
            api_key: Mistral API key
            model: Mistral model name
            temperature: Sampling temperature (0.0-1.0, default: 0.7)
            max_tokens: Max tokens in response (default: 4000)
            timeout: Request timeout in seconds (default: 60)

        Raises:
            WorkflowError: Si API key invalide

        Examples:
            >>> analyzer = MistralAPIAnalyzer(
            ...     api_key="xxx",
            ...     model="mistral-large-latest",
            ...     temperature=0.7
            ... )

        Notes:
            - Endpoint: https://api.mistral.ai/v1/chat/completions
            - Auth: Bearer token (automatic via SDK)
            - Temperature: 0.7 optimal pour analyse cyclisme
        """
        super().__init__()
        self.provider = AIProvider.MISTRAL
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        if not api_key:
            raise WorkflowError("Mistral API key required")

        try:
            self.client = MistralClient(api_key=api_key)
            logger.info(
                f"MistralAPIAnalyzer initialized: model={model}, "
                f"temperature={temperature}, max_tokens={max_tokens}"
            )
        except Exception as e:
            raise WorkflowError(f"Failed to initialize Mistral API client: {e}") from e

    def analyze_session(self, prompt: str, dataset: Optional[dict] = None) -> str:
        """Analyze session using Mistral API.

        Args:
            prompt: Structured session analysis prompt
            dataset: Optional session dataset (unused)

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
            - Rate limit: 100 req/min
            - Context: 32k tokens
        """
        logger.info(
            f"Sending prompt to Mistral API ({len(prompt)} chars, "
            f"model={self.model}, temperature={self.temperature})"
        )

        try:
            # Call Mistral API with parameters
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            # Extract analysis text
            analysis = response.choices[0].message.content
            logger.info(
                f"Received analysis from Mistral ({len(analysis)} chars, "
                f"tokens: ~{len(analysis)//4})"
            )

            return analysis

        except Exception as e:
            logger.error(f"Mistral API call failed: {e}")
            raise WorkflowError(f"Failed to analyze session with Mistral API: {e}") from e

    def get_provider_info(self) -> dict:
        """Get Mistral API provider info.

        Returns:
            Dict avec provider details

        Examples:
            >>> info = analyzer.get_provider_info()
            >>> print(info['cost_input'])
            '$2.00/1M tokens'
        """
        return {
            'provider': 'mistral_api',
            'model': self.model,
            'status': 'ready',
            'cost_input': '$2.00/1M tokens',
            'cost_output': '$6.00/1M tokens',
            'requires_api_key': True,
            'context_window': '32k tokens',
            'note': 'Best price/performance ratio 🎯'
        }

    def validate_config(self) -> bool:
        """Validate Mistral API configuration.

        Returns:
            True si config valide

        Examples:
            >>> is_valid = analyzer.validate_config()
            >>> print(is_valid)
            True
        """
        return self.client is not None
