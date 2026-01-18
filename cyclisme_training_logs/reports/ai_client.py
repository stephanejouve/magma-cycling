"""AI Client for report generation.

Provides abstraction for multiple AI providers (Claude, OpenAI, etc.)

Author: Claude Code (Sprint R10 MVP - Day 2)
Created: 2026-01-18
"""

import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class AIClientError(Exception):
    """Exception raised for AI client errors."""

    pass


class AIClient(ABC):
    """Abstract base class for AI clients.

    Provides interface for AI-powered report generation
    with support for multiple providers.
    """

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 4096) -> str:
        """Generate text from prompt.

        Args:
            prompt: Input prompt for generation
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text

        Raises:
            AIClientError: If generation fails
        """
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if client is properly configured.

        Returns:
            True if configured, False otherwise
        """
        pass


class ClaudeClient(AIClient):
    """Claude AI client using Anthropic API.

    Uses Claude Sonnet 4.5 for high-quality report generation.

    Attributes:
        api_key: Anthropic API key
        model: Model identifier (default: claude-sonnet-4-5-20250929)
        max_retries: Maximum retry attempts (default: 3)

    Examples:
        >>> client = ClaudeClient()
        >>> if client.is_configured():
        ...     report = client.generate("Generate report...")
    """

    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_retries: int = 3,
    ):
        """Initialize Claude client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Model identifier (defaults to claude-sonnet-4-5-20250929)
            max_retries: Maximum retry attempts for failed requests

        Raises:
            AIClientError: If anthropic package not installed
        """
        try:
            import anthropic
        except ImportError as e:
            raise AIClientError(
                "anthropic package not installed. " "Install with: pip install anthropic"
            ) from e

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model or self.DEFAULT_MODEL
        self.max_retries = max_retries
        self._client = None

        if self.api_key:
            self._client = anthropic.Anthropic(api_key=self.api_key)
            logger.info(f"ClaudeClient initialized with model: {self.model}")
        else:
            logger.warning(
                "ClaudeClient initialized without API key. "
                "Set ANTHROPIC_API_KEY environment variable."
            )

    def is_configured(self) -> bool:
        """Check if client is properly configured.

        Returns:
            True if API key is set, False otherwise
        """
        return self.api_key is not None and self._client is not None

    def generate(self, prompt: str, max_tokens: int = 4096) -> str:
        """Generate text from prompt using Claude.

        Implements exponential backoff retry logic for rate limits.

        Args:
            prompt: Input prompt for generation
            max_tokens: Maximum tokens to generate (default: 4096)

        Returns:
            Generated text

        Raises:
            AIClientError: If not configured or generation fails after retries

        Examples:
            >>> client = ClaudeClient()
            >>> report = client.generate("Write a cycling report...")
            >>> len(report) > 0
            True
        """
        if not self.is_configured():
            raise AIClientError(
                "ClaudeClient not configured. Set ANTHROPIC_API_KEY environment variable."
            )

        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Generating report with Claude (attempt {attempt + 1}/{self.max_retries})"
                )

                response = self._client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )

                # Extract text from response
                if response.content and len(response.content) > 0:
                    generated_text = response.content[0].text
                    logger.info(f"Successfully generated {len(generated_text)} characters")
                    return generated_text
                else:
                    raise AIClientError("Empty response from Claude API")

            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed: {error_msg}")

                # Check if it's a rate limit error
                if "rate_limit" in error_msg.lower() or "429" in error_msg:
                    if attempt < self.max_retries - 1:
                        # Exponential backoff: 2^attempt seconds
                        wait_time = 2 ** (attempt + 1)
                        logger.info(f"Rate limited. Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue

                # If last attempt or non-recoverable error, raise
                if attempt == self.max_retries - 1:
                    raise AIClientError(
                        f"Failed to generate report after {self.max_retries} attempts: {error_msg}"
                    ) from e

        raise AIClientError(f"Failed to generate report after {self.max_retries} attempts")


class OpenAIClient(AIClient):
    """OpenAI client for report generation.

    Fallback option using GPT-4 or similar models.

    Note: Implementation stub for future extension.
    """

    def __init__(self, api_key: str | None = None, model: str = "gpt-4-turbo"):
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model identifier (default: gpt-4-turbo)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model

    def is_configured(self) -> bool:
        """Check if client is properly configured."""
        return self.api_key is not None

    def generate(self, prompt: str, max_tokens: int = 4096) -> str:
        """Generate text from prompt using OpenAI.

        Args:
            prompt: Input prompt for generation
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text

        Raises:
            AIClientError: Not implemented yet
        """
        raise NotImplementedError("OpenAIClient not yet implemented (Day 3)")


def create_ai_client(provider: str = "claude", **kwargs: Any) -> AIClient:
    """Factory function to create AI client.

    Args:
        provider: Provider name ("claude", "openai", etc.)
        **kwargs: Additional arguments passed to client constructor

    Returns:
        Configured AI client instance

    Raises:
        ValueError: If provider is unknown
        AIClientError: If client creation fails

    Examples:
        >>> client = create_ai_client("claude")
        >>> client.is_configured()
        True
    """
    providers = {
        "claude": ClaudeClient,
        "openai": OpenAIClient,
    }

    if provider not in providers:
        raise ValueError(
            f"Unknown AI provider: {provider}. " f"Supported providers: {list(providers.keys())}"
        )

    client_class = providers[provider]
    return client_class(**kwargs)
