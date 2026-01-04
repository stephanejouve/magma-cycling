#!/usr/bin/env python3
"""
Integration tests for AI Provider system.

Tests real integration between providers, factory, and config.
"""
import os
from unittest.mock import patch

from cyclisme_training_logs.ai_providers.base import AIProvider
from cyclisme_training_logs.ai_providers.factory import AIProviderFactory
from cyclisme_training_logs.config import get_ai_config, reset_ai_config


class TestProviderIntegration:
    """Integration tests for provider system."""

    def setup_method(self):
        """Reset config before each test."""
        reset_ai_config()

    def teardown_method(self):
        """Reset config after each test."""
        reset_ai_config()

    def test_full_provider_lifecycle_clipboard(self):
        """Test complete lifecycle: config → factory → provider → analysis."""
        # Get config
        config = get_ai_config()

        # Clipboard should always be available
        assert config.is_provider_configured("clipboard")

        # Get provider config
        provider_config = config.get_provider_config("clipboard")

        # Create analyzer via factory
        analyzer = AIProviderFactory.create("clipboard", provider_config)

        # Verify analyzer properties
        assert analyzer.provider == AIProvider.CLIPBOARD
        assert analyzer.validate_config() is True

        # Test analysis (with mock)
        with patch("cyclisme_training_logs.ai_providers.clipboard.copy_to_clipboard") as mock_copy:
            mock_copy.return_value = True

            result = analyzer.analyze_session("Test prompt")

            # Should return instructions (not empty)
            assert len(result) > 0
            assert "prompt" in result.lower() or "clipboard" in result.lower()

    def test_full_provider_lifecycle_with_api_key(self):
        """Test complete lifecycle with API provider (mocked)."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}):
            reset_ai_config()
            config = get_ai_config()

            # OpenAI should be available with key
            assert config.is_provider_configured("openai")

            # Get provider config
            provider_config = config.get_provider_config("openai")
            assert provider_config["openai_api_key"] == "sk-test123"

            # Create analyzer via factory
            analyzer = AIProviderFactory.create("openai", provider_config)

            # Verify analyzer properties
            assert analyzer.provider == AIProvider.OPENAI
            assert analyzer.model == "gpt-4-turbo-preview"

    def test_provider_auto_detection_no_keys(self):
        """Test that auto-detection picks clipboard when no API keys."""
        with patch.dict(os.environ, {}, clear=True):
            reset_ai_config()
            config = get_ai_config()

            available = config.get_available_providers()

            # Should have clipboard and ollama (always available)
            assert "clipboard" in available
            assert "ollama" in available

            # Should not have API providers
            assert "claude_api" not in available
            assert "mistral_api" not in available
            assert "openai" not in available

    def test_provider_auto_detection_with_keys(self):
        """Test that auto-detection includes API providers with keys."""
        env = {"OPENAI_API_KEY": "sk-test", "MISTRAL_API_KEY": "test-mistral"}

        with patch.dict(os.environ, env):
            reset_ai_config()
            config = get_ai_config()

            available = config.get_available_providers()

            # Should have all available providers
            assert "clipboard" in available
            assert "ollama" in available
            assert "openai" in available
            assert "mistral_api" in available

    def test_provider_info_consistency(self):
        """Test that provider info is consistent across system."""
        config = get_ai_config()

        for provider_name in ["clipboard", "ollama"]:
            # Get via config
            is_configured = config.is_provider_configured(provider_name)
            assert is_configured is True

            # Create via factory
            provider_config = config.get_provider_config(provider_name)
            analyzer = AIProviderFactory.create(provider_name, provider_config)

            # Get provider info
            info = analyzer.get_provider_info()

            # Verify consistency
            assert info["provider"] == provider_name
            assert info["status"] in ["ready", "configured", "server_offline"]
            # Clipboard has single 'cost' field, API providers have cost_input/cost_output
            assert "cost" in info or ("cost_input" in info and "cost_output" in info)

    def test_factory_validation_matches_config(self):
        """Test that factory validation matches config is_provider_configured."""
        providers_to_test = [
            ("clipboard", {}),
            ("ollama", {}),
        ]

        config = get_ai_config()

        for provider_name, test_config in providers_to_test:
            # Check config
            is_configured = config.is_provider_configured(provider_name)

            # Check factory validation
            is_valid, message = AIProviderFactory.validate_provider_config(
                provider_name, test_config
            )

            # Should match
            assert (
                is_configured == is_valid
            ), f"Mismatch for {provider_name}: config={is_configured}, factory={is_valid}"

    def test_provider_creation_from_available_list(self):
        """Test that all available providers can be created."""
        config = get_ai_config()
        available = config.get_available_providers()

        for provider_name in available:
            provider_config = config.get_provider_config(provider_name)

            # Should not raise
            analyzer = AIProviderFactory.create(provider_name, provider_config)

            assert analyzer is not None
            assert analyzer.provider.value == provider_name

    def test_multiple_provider_instances_independent(self):
        """Test that multiple provider instances are independent."""
        config = get_ai_config()
        provider_config = config.get_provider_config("clipboard")

        analyzer1 = AIProviderFactory.create("clipboard", provider_config)
        analyzer2 = AIProviderFactory.create("clipboard", provider_config)

        # Should be different instances
        assert analyzer1 is not analyzer2

        # But same provider type
        assert analyzer1.provider == analyzer2.provider == AIProvider.CLIPBOARD

    def test_config_singleton_behavior(self):
        """Test that config singleton persists across provider operations."""
        config1 = get_ai_config()

        # Create some providers
        AIProviderFactory.create("clipboard", {})
        AIProviderFactory.create("ollama", {})

        # Get config again
        config2 = get_ai_config()

        # Should be same instance (singleton)
        assert config1 is config2

    def test_provider_with_custom_model(self):
        """Test provider creation with custom model configuration."""
        with patch.dict(os.environ, {"OLLAMA_MODEL": "custom-model:7b"}):
            reset_ai_config()
            config = get_ai_config()

            provider_config = config.get_provider_config("ollama")
            assert provider_config["ollama_model"] == "custom-model:7b"

            analyzer = AIProviderFactory.create("ollama", provider_config)
            assert analyzer.model == "custom-model:7b"

    def test_fallback_priority_order(self):
        """Test that fallback priority is maintained."""
        with patch.dict(os.environ, {"ENABLE_AI_FALLBACK": "true"}):
            reset_ai_config()
            config = get_ai_config()

            chain = config.get_fallback_chain()

            # Clipboard should be last (fallback of last resort)
            assert chain[-1] == "clipboard"

            # Should maintain priority order
            expected_order = ["claude_api", "mistral_api", "openai", "ollama", "clipboard"]
            available_in_order = [p for p in expected_order if p in chain]
            assert chain == available_in_order
