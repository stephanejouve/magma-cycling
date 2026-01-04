#!/usr/bin/env python3
"""
Integration tests for AI Provider fallback chain.

Tests automatic fallback between providers when failures occur.
"""
import os
from unittest.mock import patch

import pytest

from cyclisme_training_logs.ai_providers.factory import AIProviderFactory
from cyclisme_training_logs.config import get_ai_config, reset_ai_config


class TestFallbackChain:
    """Integration tests for provider fallback system."""

    def setup_method(self):
        """Reset config before each test."""
        reset_ai_config()

    def teardown_method(self):
        """Reset config after each test."""
        reset_ai_config()

    def test_fallback_chain_basic(self):
        """Test that fallback chain returns providers in priority order."""
        with patch.dict(os.environ, {"ENABLE_AI_FALLBACK": "true"}):
            reset_ai_config()
            config = get_ai_config()

            chain = config.get_fallback_chain()

            # Should always end with clipboard
            assert chain[-1] == "clipboard"

            # Should have at least clipboard and ollama
            assert "clipboard" in chain
            assert "ollama" in chain

    def test_fallback_disabled_returns_only_default(self):
        """Test that disabling fallback returns only default provider."""
        with patch.dict(
            os.environ, {"ENABLE_AI_FALLBACK": "false", "DEFAULT_AI_PROVIDER": "clipboard"}
        ):
            reset_ai_config()
            config = get_ai_config()

            chain = config.get_fallback_chain()

            # Should only have default provider
            assert len(chain) == 1
            assert chain[0] == "clipboard"

    def test_fallback_with_all_providers_available(self):
        """Test fallback chain when all providers are configured."""
        env = {
            "ENABLE_AI_FALLBACK": "true",
            "CLAUDE_API_KEY": "sk-ant-test",
            "MISTRAL_API_KEY": "test-mistral",
            "OPENAI_API_KEY": "sk-test",
        }

        with patch.dict(os.environ, env):
            reset_ai_config()
            config = get_ai_config()

            chain = config.get_fallback_chain()

            # Should have all 5 providers in priority order
            expected = ["claude_api", "mistral_api", "openai", "ollama", "clipboard"]
            assert chain == expected

    def test_fallback_skips_unconfigured_providers(self):
        """Test that fallback chain skips providers without API keys."""
        with patch.dict(
            os.environ, {"ENABLE_AI_FALLBACK": "true", "OPENAI_API_KEY": "sk-test"}, clear=True
        ):
            reset_ai_config()
            config = get_ai_config()

            chain = config.get_fallback_chain()

            # Should have openai, ollama, clipboard (skip claude, mistral)
            assert "openai" in chain
            assert "ollama" in chain
            assert "clipboard" in chain
            assert "claude_api" not in chain
            assert "mistral_api" not in chain

    def test_fallback_creates_valid_providers(self):
        """Test that each provider in fallback chain can be created."""
        with patch.dict(os.environ, {"ENABLE_AI_FALLBACK": "true"}):
            reset_ai_config()
            config = get_ai_config()

            chain = config.get_fallback_chain()

            for provider_name in chain:
                provider_config = config.get_provider_config(provider_name)

                # Should not raise
                analyzer = AIProviderFactory.create(provider_name, provider_config)
                assert analyzer is not None
                assert analyzer.provider.value == provider_name

    def test_fallback_maintains_order_with_partial_keys(self):
        """Test that fallback maintains priority even with partial configuration."""
        env = {
            "ENABLE_AI_FALLBACK": "true",
            "MISTRAL_API_KEY": "test-mistral",
            # Skip claude and openai
        }

        with patch.dict(os.environ, env, clear=True):
            reset_ai_config()
            config = get_ai_config()

            chain = config.get_fallback_chain()

            # Should maintain order: mistral before ollama before clipboard
            mistral_idx = chain.index("mistral_api")
            ollama_idx = chain.index("ollama")
            clipboard_idx = chain.index("clipboard")

            assert mistral_idx < ollama_idx < clipboard_idx

    def test_get_next_fallback_provider(self):
        """Test getting next provider in fallback chain after failure."""
        with patch.dict(os.environ, {"ENABLE_AI_FALLBACK": "true", "OPENAI_API_KEY": "sk-test"}):
            reset_ai_config()
            config = get_ai_config()

            chain = config.get_fallback_chain()

            # Simulate failure with first provider
            current_provider = chain[0]

            # Get next provider
            try:
                current_idx = chain.index(current_provider)
                next_provider = chain[current_idx + 1] if current_idx + 1 < len(chain) else None

                assert next_provider is not None
                assert next_provider in chain

            except (ValueError, IndexError):
                pytest.fail("Should find next provider in chain")

    def test_fallback_to_clipboard_always_possible(self):
        """Test that clipboard is always available as final fallback."""
        with patch.dict(os.environ, {}, clear=True):
            reset_ai_config()
            config = get_ai_config()

            # Even with no API keys
            available = config.get_available_providers()

            # Clipboard should always be available
            assert "clipboard" in available

            # Should be able to create clipboard provider
            provider_config = config.get_provider_config("clipboard")
            analyzer = AIProviderFactory.create("clipboard", provider_config)

            assert analyzer is not None

    def test_custom_fallback_priority(self):
        """Test that fallback priority is respected from config."""
        config = get_ai_config()

        # Check that priority list is as expected
        expected_priority = ["claude_api", "mistral_api", "openai", "ollama", "clipboard"]
        assert config.fallback_priority == expected_priority

    def test_fallback_with_all_api_providers_unavailable(self):
        """Test fallback when all API providers are unavailable."""
        with patch.dict(os.environ, {}, clear=True):
            reset_ai_config()
            config = get_ai_config()

            chain = config.get_fallback_chain()

            # Should fallback to local providers only
            assert "ollama" in chain
            assert "clipboard" in chain

            # No API providers
            assert "claude_api" not in chain
            assert "mistral_api" not in chain
            assert "openai" not in chain


class TestFallbackScenarios:
    """Test realistic fallback scenarios."""

    def setup_method(self):
        """Reset config before each test."""
        reset_ai_config()

    def teardown_method(self):
        """Reset config after each test."""
        reset_ai_config()

    def test_scenario_api_key_expired(self):
        """Simulate scenario where API key is configured but expired."""
        with patch.dict(
            os.environ,
            {
                "ENABLE_AI_FALLBACK": "true",
                "CLAUDE_API_KEY": "sk-ant-expired",
                "OPENAI_API_KEY": "sk-backup",
            },
        ):
            reset_ai_config()
            config = get_ai_config()

            chain = config.get_fallback_chain()

            # Should have multiple fallbacks
            assert len(chain) >= 3

            # If first fails, has backup
            assert chain[0] == "claude_api"
            assert "openai" in chain
            assert "clipboard" in chain

    def test_scenario_network_failure(self):
        """Simulate scenario where network fails (local fallback)."""
        with patch.dict(os.environ, {"ENABLE_AI_FALLBACK": "true"}):
            reset_ai_config()
            config = get_ai_config()

            chain = config.get_fallback_chain()

            # Should have local fallbacks
            local_fallbacks = [p for p in chain if p in ["ollama", "clipboard"]]
            assert len(local_fallbacks) >= 2

    def test_scenario_cost_optimization(self):
        """Test scenario where user wants cheap then free fallback."""
        env = {
            "ENABLE_AI_FALLBACK": "true",
            "MISTRAL_API_KEY": "test",  # Cheapest API
            "OPENAI_API_KEY": "test2",  # More expensive
        }

        with patch.dict(os.environ, env):
            reset_ai_config()
            config = get_ai_config()

            chain = config.get_fallback_chain()

            # Mistral (cheap) should come before OpenAI (expensive)
            if "mistral_api" in chain and "openai" in chain:
                mistral_idx = chain.index("mistral_api")
                openai_idx = chain.index("openai")
                assert mistral_idx < openai_idx

            # Ollama (free) should be in chain
            assert "ollama" in chain

    def test_scenario_privacy_first(self):
        """Test scenario where user prioritizes privacy (local first)."""
        with patch.dict(
            os.environ,
            {"ENABLE_AI_FALLBACK": "true", "DEFAULT_AI_PROVIDER": "ollama"},  # Start with local
        ):
            reset_ai_config()
            config = get_ai_config()

            # Default provider should be ollama
            assert config.default_provider == "ollama"

            # Clipboard always available as final fallback
            chain = config.get_fallback_chain()
            assert "clipboard" in chain
