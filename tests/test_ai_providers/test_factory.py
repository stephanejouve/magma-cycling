#!/usr/bin/env python3
"""
Tests for AI Provider Factory.

Tests AIProviderFactory for dynamic provider creation.
"""
import pytest

from cyclisme_training_logs.ai_providers.base import AIAnalyzer, AIProvider
from cyclisme_training_logs.ai_providers.claude_api import ClaudeAPIAnalyzer
from cyclisme_training_logs.ai_providers.clipboard import ClipboardAnalyzer
from cyclisme_training_logs.ai_providers.factory import AIProviderFactory, ConfigError
from cyclisme_training_logs.ai_providers.mistral_api import MistralAPIAnalyzer
from cyclisme_training_logs.ai_providers.ollama import OllamaAnalyzer
from cyclisme_training_logs.ai_providers.openai_api import OpenAIAnalyzer


class TestAIProviderFactory:
    """Tests for AIProviderFactory."""

    def test_create_clipboard_analyzer(self):
        """Test that factory creates ClipboardAnalyzer."""
        analyzer = AIProviderFactory.create("clipboard", {})

        assert isinstance(analyzer, ClipboardAnalyzer)
        assert isinstance(analyzer, AIAnalyzer)
        assert analyzer.provider == AIProvider.CLIPBOARD

    def test_create_clipboard_case_insensitive(self):
        """Test that provider name is case-insensitive."""
        analyzer1 = AIProviderFactory.create("CLIPBOARD", {})

        analyzer2 = AIProviderFactory.create("ClipBoard", {})
        analyzer3 = AIProviderFactory.create("clipboard", {})

        assert all(isinstance(a, ClipboardAnalyzer) for a in [analyzer1, analyzer2, analyzer3])

    def test_create_clipboard_whitespace_trimmed(self):
        """Test that whitespace is trimmed from provider name."""
        analyzer = AIProviderFactory.create("  clipboard  ", {})

        assert isinstance(analyzer, ClipboardAnalyzer)

    def test_create_claude_analyzer_with_key(self):
        """Test that factory creates ClaudeAPIAnalyzer with valid key."""
        config = {
            "claude_api_key": "sk-ant-test-key-123",
            "claude_model": "claude-sonnet-4-20250514",
        }

        analyzer = AIProviderFactory.create("claude_api", config)

        assert isinstance(analyzer, ClaudeAPIAnalyzer)
        assert analyzer.provider == AIProvider.CLAUDE
        assert analyzer.model == "claude-sonnet-4-20250514"

    def test_create_claude_analyzer_missing_key(self):
        """Test that factory raises ConfigError when Claude API key missing."""
        config = {}

        with pytest.raises(ConfigError) as excinfo:
            AIProviderFactory.create("claude_api", config)

        assert "Claude API key required" in str(excinfo.value)

    def test_create_claude_analyzer_default_model(self):
        """Test that Claude analyzer uses default model when not specified."""
        config = {"claude_api_key": "sk-ant-test-key"}

        analyzer = AIProviderFactory.create("claude_api", config)

        assert analyzer.model == "claude-sonnet-4-20250514"

    def test_create_mistral_analyzer_with_key(self):
        """Test that factory creates MistralAPIAnalyzer with valid key."""
        config = {"mistral_api_key": "test-mistral-key", "mistral_model": "mistral-large-latest"}

        analyzer = AIProviderFactory.create("mistral_api", config)

        assert isinstance(analyzer, MistralAPIAnalyzer)
        assert analyzer.provider == AIProvider.MISTRAL
        assert analyzer.model == "mistral-large-latest"

    def test_create_mistral_analyzer_missing_key(self):
        """Test that factory raises ConfigError when Mistral API key missing."""
        config = {}

        with pytest.raises(ConfigError) as excinfo:
            AIProviderFactory.create("mistral_api", config)

        assert "Mistral API key required" in str(excinfo.value)

    def test_create_openai_analyzer_with_key(self):
        """Test that factory creates OpenAIAnalyzer with valid key."""
        config = {"openai_api_key": "test-openai-key", "openai_model": "gpt-4-turbo"}

        analyzer = AIProviderFactory.create("openai", config)

        assert isinstance(analyzer, OpenAIAnalyzer)
        assert analyzer.provider == AIProvider.OPENAI
        assert analyzer.model == "gpt-4-turbo"

    def test_create_openai_analyzer_missing_key(self):
        """Test that factory raises ConfigError when OpenAI API key missing."""
        config = {}

        with pytest.raises(ConfigError) as excinfo:
            AIProviderFactory.create("openai", config)

        assert "OpenAI API key required" in str(excinfo.value)

    def test_create_ollama_analyzer(self):
        """Test that factory creates OllamaAnalyzer."""
        config = {"ollama_host": "http://localhost:11434", "ollama_model": "mistral:7b"}

        analyzer = AIProviderFactory.create("ollama", config)

        assert isinstance(analyzer, OllamaAnalyzer)
        assert analyzer.provider == AIProvider.OLLAMA
        assert analyzer.model == "mistral:7b"
        assert analyzer.host == "http://localhost:11434"

    def test_create_ollama_analyzer_default_config(self):
        """Test that Ollama uses default config when not specified."""
        config = {}

        analyzer = AIProviderFactory.create("ollama", config)

        assert analyzer.model == "mistral:7b"
        assert analyzer.host == "http://localhost:11434"

    def test_create_invalid_provider_raises_error(self):
        """Test that invalid provider name raises ConfigError."""
        with pytest.raises(ConfigError) as excinfo:
            AIProviderFactory.create("invalid_provider", {})

        assert "Unknown AI provider" in str(excinfo.value)
        assert "invalid_provider" in str(excinfo.value)

    def test_get_available_providers_returns_dict(self):
        """Test that get_available_providers returns dict."""
        providers = AIProviderFactory.get_available_providers()

        assert isinstance(providers, dict)
        assert len(providers) == 5

    def test_get_available_providers_has_all_providers(self):
        """Test that all 5 providers are in available providers."""
        providers = AIProviderFactory.get_available_providers()

        expected = ["clipboard", "claude_api", "mistral_api", "openai", "ollama"]
        for provider in expected:
            assert provider in providers

    def test_get_available_providers_has_descriptions(self):
        """Test that each provider has a description."""
        providers = AIProviderFactory.get_available_providers()

        for _provider, description in providers.items():
            assert isinstance(description, str)
            assert len(description) > 0

    def test_validate_provider_config_clipboard_always_valid(self):
        """Test that clipboard config is always valid."""
        is_valid, message = AIProviderFactory.validate_provider_config("clipboard", {})

        assert is_valid is True
        assert "ready" in message.lower() or "valid" in message.lower()

    def test_validate_provider_config_claude_with_key(self):
        """Test that Claude config is valid with API key."""
        config = {"claude_api_key": "sk-ant-test-key"}

        is_valid, message = AIProviderFactory.validate_provider_config("claude_api", config)

        assert is_valid is True
        assert "valid" in message.lower()

    def test_validate_provider_config_claude_without_key(self):
        """Test that Claude config is invalid without API key."""
        config = {}

        is_valid, message = AIProviderFactory.validate_provider_config("claude_api", config)

        assert is_valid is False
        assert "missing" in message.lower()

    def test_validate_provider_config_mistral_with_key(self):
        """Test that Mistral config is valid with API key."""
        config = {"mistral_api_key": "test-key"}

        is_valid, message = AIProviderFactory.validate_provider_config("mistral_api", config)

        assert is_valid is True

    def test_validate_provider_config_mistral_without_key(self):
        """Test that Mistral config is invalid without API key."""
        config = {}

        is_valid, message = AIProviderFactory.validate_provider_config("mistral_api", config)

        assert is_valid is False
        assert "MISTRAL_API_KEY" in message

    def test_validate_provider_config_openai_with_key(self):
        """Test that OpenAI config is valid with API key."""
        config = {"openai_api_key": "test-key"}

        is_valid, message = AIProviderFactory.validate_provider_config("openai", config)

        assert is_valid is True

    def test_validate_provider_config_openai_without_key(self):
        """Test that OpenAI config is invalid without API key."""
        config = {}

        is_valid, message = AIProviderFactory.validate_provider_config("openai", config)

        assert is_valid is False
        assert "OPENAI_API_KEY" in message

    def test_validate_provider_config_ollama_always_valid(self):
        """Test that Ollama config is always valid (local server)."""
        config = {}

        is_valid, message = AIProviderFactory.validate_provider_config("ollama", config)

        assert is_valid is True
        assert "valid" in message.lower()

    def test_validate_provider_config_unknown_provider(self):
        """Test that unknown provider returns invalid."""
        is_valid, message = AIProviderFactory.validate_provider_config("unknown", {})

        assert is_valid is False
        assert "unknown" in message.lower()
