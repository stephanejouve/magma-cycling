#!/usr/bin/env python3
"""
OpenAI API integration.

OpenAI GPT-4 provider pour analyse séance.
Plus cher mais excellent qualité.

Author: Claude Code
Created: 2025-12-09.
"""
import logging

from openai import OpenAI

from .base import AIAnalyzer, AIProvider

logger = logging.getLogger(__name__)


class WorkflowError(Exception):
    """Workflow error for AI provider operations."""

    pass


class OpenAIAnalyzer(AIAnalyzer):
    """OpenAI GPT-4 provider.

    Attributes:
        provider: AIProvider.OPENAI
        model: GPT model name
        client: OpenAI API client

    Notes:
        - Coût: ~$10/1M input, $30/1M output
        - Qualité: excellente
        - Context: 128k tokens
    """

    MODELS = {
        "gpt-4-turbo": "GPT-4 Turbo (recommended)",
        "gpt-4": "GPT-4 (legacy)",
        "gpt-3.5-turbo": "GPT-3.5 (cheaper)",
    }

    def __init__(self, api_key: str, model: str = "gpt-4-turbo"):
        """Initialize OpenAI analyzer."""
        super().__init__()

        self.provider = AIProvider.OPENAI
        self.model: str = model

        if not api_key:
            raise WorkflowError("OpenAI API key required")

        try:
            self.client = OpenAI(api_key=api_key)
            logger.info(f"OpenAIAnalyzer initialized with model {model}")
        except Exception as e:
            raise WorkflowError(f"Failed to initialize OpenAI client: {e}") from e

    def analyze_session(
        self, prompt: str, dataset: dict | None = None, *, system_prompt: str | None = None
    ) -> str:
        """Analyze session using OpenAI API.

        Args:
            prompt: Structured session analysis prompt
            dataset: Optional session dataset (unused)
            system_prompt: Optional system-level prompt added as a
                ``{"role": "system"}`` message before the user message.
        """
        logger.info(f"Sending prompt to OpenAI API ({len(prompt)} chars)")

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = self.client.chat.completions.create(model=self.model, messages=messages)

            analysis = response.choices[0].message.content
            if analysis is None:
                raise WorkflowError("OpenAI returned empty response")

            logger.info(f"Received analysis from OpenAI ({len(analysis)} chars)")
            return analysis

        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise WorkflowError(f"Failed to analyze session with OpenAI: {e}") from e

    def get_provider_info(self) -> dict:
        """Get OpenAI provider info."""
        return {
            "provider": "openai",
            "model": self.model,
            "status": "ready",
            "cost_input": "$10.00/1M tokens",
            "cost_output": "$30.00/1M tokens",
            "requires_api_key": True,
            "context_window": "128k tokens",
        }

    def validate_config(self) -> bool:
        """Validate OpenAI configuration."""
        return self.client is not None
