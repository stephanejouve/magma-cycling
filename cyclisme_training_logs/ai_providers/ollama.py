#!/usr/bin/env python3
"""
Ollama local LLM integration.

Provider local LLMs via Ollama server.
100% gratuit, privacy-first, pas de rate limits.

Examples:
    Use Ollama::

        from src.ai.ollama import OllamaAnalyzer

        analyzer = OllamaAnalyzer(
            host="http://localhost:11434",
            model="llama3.1:70b"
        )
        analysis = analyzer.analyze_session(prompt)

Author: Claude Code
Created: 2025-12-09
"""

import logging

import requests

from .base import AIAnalyzer, AIProvider

logger = logging.getLogger(__name__)


class WorkflowError(Exception):
    """Workflow error for AI provider operations."""

    pass


class OllamaAnalyzer(AIAnalyzer):
    """Ollama local LLM provider.

    Run LLMs locally via Ollama server. Free, private, unlimited.

    Attributes:
        provider: AIProvider.OLLAMA
        model: Ollama model name (llama3.1, mistral, etc.)
        host: Ollama server URL

    Examples:
        >>> analyzer = OllamaAnalyzer(
        ...     host="http://localhost:11434",
        ...     model="llama3.1:70b"
        ... )
        >>> analysis = analyzer.analyze_session(prompt)

    Notes:
        - Coût: $0 (run locally)
        - Privacy: 100% local, no data sent externally
        - Models: llama3.1, mistral, codellama, etc.
        - Requires: Ollama server running
        - Install: https://ollama.ai
    """

    POPULAR_MODELS = {
        "llama3.1:70b": "Llama 3.1 70B (best quality)",
        "llama3.1:8b": "Llama 3.1 8B (fast, good)",
        "mistral:7b": "Mistral 7B (balanced)",
        "codellama:13b": "CodeLlama 13B (code-focused)",
    }

    def __init__(self, host: str = "http://localhost:11434", model: str = "mistral:7b"):
        """Initialize Ollama analyzer.

        Args:
            host: Ollama server URL
            model: Ollama model name

        Examples:
            >>> analyzer = OllamaAnalyzer()
            >>> analyzer = OllamaAnalyzer(model="mistral:7b")
        """
        super().__init__()
        self.provider = AIProvider.OLLAMA
        self.model = model
        self.host = host
        self.api_url = f"{host}/api/generate"

        logger.info(f"OllamaAnalyzer initialized with model {model} at {host}")

    def analyze_session(self, prompt: str, dataset: dict | None = None) -> str:
        """Analyze session using Ollama local LLM.

        Args:
            prompt: Structured session analysis prompt
            dataset: Optional session dataset (unused)

        Returns:
            AI-generated analysis markdown

        Raises:
            WorkflowError: Si Ollama server inaccessible

        Examples:
            >>> analysis = analyzer.analyze_session(prompt)
            >>> "# Analyse" in analysis
            True

        Notes:
            - Timeout: 600s (10min for slow local models)
            - No rate limits
            - No API costs
        """
        logger.info(f"Sending prompt to Ollama ({len(prompt)} chars, model: {self.model})")

        try:
            # Call Ollama API (10min timeout for slow local models)
            response = requests.post(
                self.api_url,
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=600,
            )

            response.raise_for_status()
            result = response.json()
            analysis = result.get("response", "")

            logger.info(f"Received analysis from Ollama ({len(analysis)} chars)")

            return analysis

        except requests.exceptions.ConnectionError:
            error_msg = (
                f"Cannot connect to Ollama server at {self.host}. "
                "Make sure Ollama is running: https://ollama.ai"
            )
            logger.error(error_msg)
            raise WorkflowError(error_msg) from None

        except Exception as e:
            logger.error(f"Ollama API call failed: {e}")
            raise WorkflowError(f"Failed to analyze session with Ollama: {e}") from e

    def get_provider_info(self) -> dict:
        """Get Ollama provider info.

        Returns:
            Dict avec provider details

        Examples:
            >>> info = analyzer.get_provider_info()
            >>> print(info['cost_input'])
            '$0.00 (local)'
        """
        return {
            "provider": "ollama",
            "model": self.model,
            "host": self.host,
            "status": "ready" if self.validate_config() else "server_offline",
            "cost_input": "$0.00 (local)",
            "cost_output": "$0.00 (local)",
            "requires_api_key": False,
            "privacy": "100% local",
            "note": "Free, unlimited, private 🔒",
        }

    def validate_config(self) -> bool:
        """Validate Ollama server is running.

        Returns:
            True si serveur accessible

        Examples:
            >>> is_valid = analyzer.validate_config()
            >>> print(is_valid)
            True

        Notes:
            - Test connexion serveur
            - Timeout 5s
        """
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
