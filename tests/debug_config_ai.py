#!/usr/bin/env python3
"""
Tests for AI Providers Configuration.

Tests AIProvidersConfig singleton and configuration management.
"""

import os
from unittest.mock import patch

from cyclisme_training_logs.config import AIProvidersConfig, get_ai_config, reset_ai_config


class TestAIProvidersConfig:
    """Tests for AIProvidersConfig class."""

    def setup_method(self):
        """Reset config singleton before each test."""
        reset_ai_config()

    def teardown_method(self):
        """Reset config singleton after each test."""
        reset_ai_config()

    def test_initialization(self):
        """Test that AIProvidersConfig initializes correctly."""
        config = AIProvidersConfig()

        assert config is not None
        assert hasattr(config, "default_provider")
        assert hasattr(config, "enable_fallback")
        assert hasattr(config, "fallback_priority")

    def test_default_provider_is_clipboard(self):
        """Test that default provider is clipboard."""
        with patch.dict(os.environ, {}, clear=True):
            config = AIProvidersConfig()

            assert config.default_provider == "clipboard"

    def test_default_provider_from_env(self):
        """Test that default provider can be set from environment."""
        with patch.dict(os.environ, {"DEFAULT_AI_PROVIDER": "ollama"}):
            config = AIProvidersConfig()

            assert config.default_provider == "ollama"

    def test_enable_fallback_default_true(self):
        """Test that fallback is enabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            config = AIProvidersConfig()

            assert config.enable_fallback is True

    def test_enable_fallback_from_env_true(self):
        """Test that fallback can be enabled from environment."""
        with patch.dict(os.environ, {"ENABLE_AI_FALLBACK": "true"}):
            config = AIProvidersConfig()

            assert config.enable_fallback is True

    def test_enable_fallback_from_env_false(self):
        """Test that fallback can be disabled from environment."""
        with patch.dict(os.environ, {"ENABLE_AI_FALLBACK": "false"}):
            config = AIProvidersConfig()

            assert config.enable_fallback is False

    def test_fallback_priority_has_all_providers(self):
        """Test that fallback priority includes all 5 providers."""
        config = AIProvidersConfig()

        expected = ["claude_api", "mistral_api", "openai", "ollama", "clipboard"]
        assert config.fallback_priority == expected

    def test_clipboard_always_configured(self):
        """Test that clipboard is always considered configured."""
        with patch.dict(os.environ, {}, clear=True):
            config = AIProvidersConfig()

            assert config.is_provider_configured("clipboard") is True

    def test_ollama_always_configured(self):
        """Test that ollama is always considered configured (local)."""
        with patch.dict(os.environ, {}, clear=True):
            config = AIProvidersConfig()

            assert config.is_provider_configured("ollama") is True

    def test_claude_configured_with_api_key(self):
        """Test that Claude is configured when API key present."""
        with patch.dict(os.environ, {"CLAUDE_API_KEY": "test-key"}):
            config = AIProvidersConfig()

            assert config.is_provider_configured("claude_api") is True

    def test_claude_not_configured_without_api_key(self):
        """Test that Claude is not configured without API key."""
        with patch.dict(os.environ, {}, clear=True):
            config = AIProvidersConfig()

            assert config.is_provider_configured("claude_api") is False

    def test_mistral_configured_with_api_key(self):
        """Test that Mistral is configured when API key present."""
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            config = AIProvidersConfig()

            assert config.is_provider_configured("mistral_api") is True

    def test_mistral_not_configured_without_api_key(self):
        """Test that Mistral is not configured without API key."""
        with patch.dict(os.environ, {}, clear=True):
            config = AIProvidersConfig()

            assert config.is_provider_configured("mistral_api") is False

    def test_openai_configured_with_api_key(self):
        """Test that OpenAI is configured when API key present."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            config = AIProvidersConfig()

            assert config.is_provider_configured("openai") is True

    def test_openai_not_configured_without_api_key(self):
        """Test that OpenAI is not configured without API key."""
        with patch.dict(os.environ, {}, clear=True):
            config = AIProvidersConfig()

            assert config.is_provider_configured("openai") is False

    def test_get_available_providers_no_api_keys(self):
        """Test that only clipboard and ollama available without API keys."""
        with patch.dict(os.environ, {}, clear=True):
            config = AIProvidersConfig()

            available = config.get_available_providers()

            # Should have clipboard and ollama (both always available)
            assert "clipboard" in available
            assert "ollama" in available
            # Should not have API providers
            assert "claude_api" not in available
            assert "mistral_api" not in available
            assert "openai" not in available

    def test_get_available_providers_with_api_keys(self):
        """Test that API providers available with keys."""
        env = {
            "CLAUDE_API_KEY": "claude-key",
            "MISTRAL_API_KEY": "mistral-key",
            "OPENAI_API_KEY": "openai-key",
        }

        with patch.dict(os.environ, env):
            config = AIProvidersConfig()

            available = config.get_available_providers()

            # Should have all 5 providers
            assert len(available) == 5
            assert "clipboard" in available
            assert "claude_api" in available
            assert "mistral_api" in available
            assert "openai" in available
            assert "ollama" in available

    def test_get_provider_config_clipboard(self):
        """Test that clipboard config is empty dict."""
        config = AIProvidersConfig()

        provider_config = config.get_provider_config("clipboard")

        assert provider_config == {}

    def test_get_provider_config_claude(self):
        """Test that Claude config includes API key and model."""
        with patch.dict(os.environ, {"CLAUDE_API_KEY": "test-key", "CLAUDE_MODEL": "claude-3"}):
            config = AIProvidersConfig()

            provider_config = config.get_provider_config("claude_api")

            assert "claude_api_key" in provider_config
            assert provider_config["claude_api_key"] == "test-key"
            assert provider_config["claude_model"] == "claude-3"

    def test_get_provider_config_claude_default_model(self):
        """Test that Claude uses default model when not specified."""
        with patch.dict(os.environ, {"CLAUDE_API_KEY": "test-key"}, clear=True):
            config = AIProvidersConfig()

            provider_config = config.get_provider_config("claude_api")

            assert provider_config["claude_model"] == "claude-sonnet-4-20250514"

    def test_get_provider_config_mistral(self):
        """Test that Mistral config includes API key and model."""
        with patch.dict(
            os.environ, {"MISTRAL_API_KEY": "test-key", "MISTRAL_MODEL": "mistral-large"}
        ):
            config = AIProvidersConfig()

            provider_config = config.get_provider_config("mistral_api")

            assert "mistral_api_key" in provider_config
            assert provider_config["mistral_api_key"] == "test-key"
            assert provider_config["mistral_model"] == "mistral-large"

    def test_get_provider_config_openai(self):
        """Test that OpenAI config includes API key and model."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "gpt-4"}):
            config = AIProvidersConfig()

            provider_config = config.get_provider_config("openai")

            assert "openai_api_key" in provider_config
            assert provider_config["openai_api_key"] == "test-key"
            assert provider_config["openai_model"] == "gpt-4"

    def test_get_provider_config_ollama(self):
        """Test that Ollama config includes host and model."""
        with patch.dict(
            os.environ, {"OLLAMA_BASE_URL": "http://localhost:11434", "OLLAMA_MODEL": "mistral:7b"}
        ):
            config = AIProvidersConfig()

            provider_config = config.get_provider_config("ollama")

            assert "ollama_base_url" in provider_config
            assert provider_config["ollama_base_url"] == "http://localhost:11434"
            assert provider_config["ollama_model"] == "mistral:7b"

    def test_get_fallback_chain_with_fallback_disabled(self):
        """Test that fallback chain is just default provider when disabled."""
        with patch.dict(
            os.environ, {"ENABLE_AI_FALLBACK": "false", "DEFAULT_AI_PROVIDER": "clipboard"}
        ):
            config = AIProvidersConfig()

            chain = config.get_fallback_chain()

            assert chain == ["clipboard"]

    def test_get_fallback_chain_with_fallback_enabled(self):
        """Test that fallback chain includes available providers when enabled."""
        with patch.dict(os.environ, {"ENABLE_AI_FALLBACK": "true"}, clear=True):
            config = AIProvidersConfig()

            chain = config.get_fallback_chain()

            # Should include clipboard and ollama (always available)
            assert "clipboard" in chain
            assert "ollama" in chain
            # Should be in priority order
            assert chain[-1] == "clipboard"  # Clipboard is last fallback

    def test_get_fallback_chain_respects_priority(self):
        """Test that fallback chain respects priority order."""
        env = {
            "ENABLE_AI_FALLBACK": "true",
            "CLAUDE_API_KEY": "key1",
            "MISTRAL_API_KEY": "key2",
            "OPENAI_API_KEY": "key3",
        }

        with patch.dict(os.environ, env):
            config = AIProvidersConfig()

            chain = config.get_fallback_chain()

            # Should have all 5 in priority order
            expected_order = ["claude_api", "mistral_api", "openai", "ollama", "clipboard"]
            assert chain == expected_order


class TestConfigSingleton:
    """Tests for config singleton pattern."""

    def setup_method(self):
        """Reset config before each test."""
        reset_ai_config()

    def teardown_method(self):
        """Reset config after each test."""
        reset_ai_config()

    def test_get_ai_config_returns_instance(self):
        """Test that get_ai_config returns AIProvidersConfig instance."""
        config = get_ai_config()

        assert isinstance(config, AIProvidersConfig)

    def test_get_ai_config_singleton(self):
        """Test that get_ai_config returns same instance."""
        config1 = get_ai_config()
        config2 = get_ai_config()

        assert config1 is config2

    def test_reset_ai_config_creates_new_instance(self):
        """Test that reset_ai_config creates new instance on next call."""
        config1 = get_ai_config()
        reset_ai_config()
        config2 = get_ai_config()

        assert config1 is not config2

    def test_reset_ai_config_multiple_times(self):
        """Test that reset can be called multiple times."""
        reset_ai_config()
        reset_ai_config()
        config = get_ai_config()

        assert isinstance(config, AIProvidersConfig)
