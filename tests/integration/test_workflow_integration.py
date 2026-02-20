#!/usr/bin/env python3
"""
Integration tests for AI Providers with WorkflowCoach.

Tests integration of AI provider system with main workflow.
"""
import os
from unittest.mock import patch

import pytest

from cyclisme_training_logs.ai_providers.base import AIProvider
from cyclisme_training_logs.ai_providers.factory import AIProviderFactory
from cyclisme_training_logs.config import get_ai_config, reset_ai_config


class TestWorkflowAIIntegration:
    """Integration tests for AI providers in workflow context."""

    def setup_method(self):
        """Reset config before each test."""
        reset_ai_config()

    def teardown_method(self):
        """Reset config after each test."""
        reset_ai_config()

    def test_workflow_default_provider_selection(self):
        """Test that workflow selects correct default provider."""
        with patch.dict(os.environ, {}, clear=True):
            reset_ai_config()
            config = get_ai_config()

            # Get first available provider (should be clipboard or ollama)
            available = config.get_available_providers()
            default_provider = available[0] if available else "clipboard"

            assert default_provider in ["clipboard", "ollama"]

    @pytest.mark.skipif(
        os.environ.get("CI") == "true", reason="Clipboard not available in CI environment"
    )
    def test_workflow_provider_initialization(self):
        """Test provider initialization sequence as workflow would do."""
        config = get_ai_config()

        # Simulate workflow provider selection
        provider_name = "clipboard"

        # Validate provider is configured
        assert config.is_provider_configured(provider_name)

        # Get config for provider
        provider_config = config.get_provider_config(provider_name)

        # Create analyzer
        analyzer = AIProviderFactory.create(provider_name, provider_config)

        # Verify workflow can use analyzer
        assert analyzer is not None
        assert analyzer.validate_config()
        assert hasattr(analyzer, "analyze_session")

    def test_workflow_with_explicit_provider(self):
        """Test workflow with explicitly specified provider."""
        with patch.dict(os.environ, {"OLLAMA_MODEL": "mistral:7b"}):
            reset_ai_config()
            config = get_ai_config()

            # Simulate user specifying --provider ollama
            provider_name = "ollama"

            # Workflow checks if configured
            is_configured = config.is_provider_configured(provider_name)
            assert is_configured is True

            # Workflow gets config
            provider_config = config.get_provider_config(provider_name)
            assert provider_config["ollama_model"] == "mistral:7b"

            # Workflow creates analyzer
            analyzer = AIProviderFactory.create(provider_name, provider_config)
            assert analyzer.model == "mistral:7b"

    def test_workflow_fallback_on_unconfigured_provider(self):
        """Test workflow fallback when requested provider not configured."""
        with patch.dict(os.environ, {}, clear=True):
            reset_ai_config()
            config = get_ai_config()

            # User requests API provider but no key configured
            requested_provider = "claude_api"

            # Workflow checks configuration
            is_configured = config.is_provider_configured(requested_provider)

            if not is_configured:
                # Workflow falls back to clipboard
                fallback_provider = "clipboard"

                # Should be configured
                assert config.is_provider_configured(fallback_provider)

                # Create fallback analyzer
                provider_config = config.get_provider_config(fallback_provider)
                analyzer = AIProviderFactory.create(fallback_provider, provider_config)

                assert analyzer.provider == AIProvider.CLIPBOARD

    def test_workflow_analysis_pipeline_clipboard(self):
        """Test complete analysis pipeline with clipboard provider."""
        config = get_ai_config()

        provider_config = config.get_provider_config("clipboard")
        analyzer = AIProviderFactory.create("clipboard", provider_config)

        # Simulate workflow generating prompt
        prompt = """# Analyse Séance Cyclisme

## Données
- Durée: 2h30
- Distance: 75 km
- Puissance: 210W

Analyse cette séance."""
        # Mock clipboard operation

        with patch("cyclisme_training_logs.ai_providers.clipboard.copy_to_clipboard") as mock_copy:
            mock_copy.return_value = True

            # Workflow calls analyze_session
            result = analyzer.analyze_session(prompt)

            # Should return instructions
            assert result is not None
            assert len(result) > 0

            # Clipboard should have been called
            mock_copy.assert_called_once_with(prompt)

    def test_workflow_provider_info_display(self):
        """Test that workflow can display provider information."""
        config = get_ai_config()

        # Simulate workflow --list-providers command
        available = config.get_available_providers()

        provider_infos = []
        for provider_name in available:
            provider_config = config.get_provider_config(provider_name)
            analyzer = AIProviderFactory.create(provider_name, provider_config)
            info = analyzer.get_provider_info()

            provider_infos.append(
                {
                    "name": provider_name,
                    "status": info.get("status"),
                    "cost": info.get("cost_input"),
                    "model": info.get("model"),
                }
            )

        # Should have info for all providers
        assert len(provider_infos) == len(available)

        # Each should have required fields
        for info in provider_infos:
            assert "name" in info
            assert "status" in info
            assert "cost" in info

    def test_workflow_auto_detection_logic(self):
        """Test workflow's auto-detection logic for provider selection."""
        with patch.dict(
            os.environ, {"DEFAULT_AI_PROVIDER": "clipboard", "ENABLE_AI_FALLBACK": "true"}
        ):
            reset_ai_config()
            config = get_ai_config()

            # Simulate workflow auto-detection
            # User didn't specify --provider, so use first available

            available = config.get_available_providers()
            selected_provider = available[0] if available else "clipboard"

            # Should be able to create this provider
            provider_config = config.get_provider_config(selected_provider)
            analyzer = AIProviderFactory.create(selected_provider, provider_config)

            assert analyzer is not None

    def test_workflow_error_handling(self):
        """Test workflow error handling when provider fails."""
        get_ai_config()

        # Try to create provider with invalid config
        try:
            # This should raise ConfigError
            AIProviderFactory.create("claude_api", {})  # Missing API key
            pytest.fail("Should have raised ConfigError")

        except Exception as e:
            # Workflow should catch and handle gracefully
            assert "API key" in str(e) or "required" in str(e).lower()

    def test_workflow_provider_switching(self):
        """Test that workflow can switch between providers."""
        config = get_ai_config()

        # Start with clipboard
        provider1_config = config.get_provider_config("clipboard")
        analyzer1 = AIProviderFactory.create("clipboard", provider1_config)
        assert analyzer1.provider == AIProvider.CLIPBOARD

        # Switch to ollama
        provider2_config = config.get_provider_config("ollama")
        analyzer2 = AIProviderFactory.create("ollama", provider2_config)
        assert analyzer2.provider == AIProvider.OLLAMA

        # Both should coexist independently
        assert analyzer1 is not analyzer2


class TestWorkflowEdgeCases:
    """Test edge cases in workflow integration."""

    def setup_method(self):
        """Reset config before each test."""
        reset_ai_config()

    def teardown_method(self):
        """Reset config after each test."""
        reset_ai_config()

    def test_empty_prompt_handling(self):
        """Test workflow handling of empty prompt."""
        config = get_ai_config()

        provider_config = config.get_provider_config("clipboard")
        analyzer = AIProviderFactory.create("clipboard", provider_config)

        with patch("cyclisme_training_logs.ai_providers.clipboard.copy_to_clipboard") as mock_copy:
            mock_copy.return_value = True

            # Empty prompt should still work
            result = analyzer.analyze_session("")

            # Should not crash
            assert result is not None

    def test_very_large_prompt_handling(self):
        """Test workflow handling of very large prompt."""
        config = get_ai_config()

        provider_config = config.get_provider_config("clipboard")
        analyzer = AIProviderFactory.create("clipboard", provider_config)

        # Create large prompt (50KB)
        large_prompt = "X" * 50000

        with patch("cyclisme_training_logs.ai_providers.clipboard.copy_to_clipboard") as mock_copy:
            mock_copy.return_value = True

            # Large prompt should work
            result = analyzer.analyze_session(large_prompt)

            # Should not crash
            assert result is not None
            mock_copy.assert_called_once_with(large_prompt)

    def test_special_characters_in_prompt(self):
        """Test workflow handling of special characters."""
        config = get_ai_config()

        provider_config = config.get_provider_config("clipboard")
        analyzer = AIProviderFactory.create("clipboard", provider_config)

        prompt = "Test 🚴‍♂️ with émojis and spéciål çhars: €$£"

        with patch("cyclisme_training_logs.ai_providers.clipboard.copy_to_clipboard") as mock_copy:
            mock_copy.return_value = True

            result = analyzer.analyze_session(prompt)

            # Should handle special characters
            assert result is not None
            mock_copy.assert_called_once_with(prompt)

    def test_concurrent_provider_usage(self):
        """Test that multiple providers can be used concurrently."""
        config = get_ai_config()

        # Create multiple analyzers
        clipboard_config = config.get_provider_config("clipboard")
        ollama_config = config.get_provider_config("ollama")

        analyzer1 = AIProviderFactory.create("clipboard", clipboard_config)
        analyzer2 = AIProviderFactory.create("ollama", ollama_config)

        # Both should work independently
        assert analyzer1.provider == AIProvider.CLIPBOARD
        assert analyzer2.provider == AIProvider.OLLAMA

        # Should have different instances
        assert analyzer1 is not analyzer2

    def test_config_change_detection(self):
        """Test that config changes are reflected in providers."""
        with patch.dict(os.environ, {"OLLAMA_MODEL": "model1"}):
            reset_ai_config()
            config1 = get_ai_config()

            provider_config1 = config1.get_provider_config("ollama")
            assert provider_config1["ollama_model"] == "model1"

        # Change environment and reset
        with patch.dict(os.environ, {"OLLAMA_MODEL": "model2"}):
            reset_ai_config()
            config2 = get_ai_config()

            provider_config2 = config2.get_provider_config("ollama")
            assert provider_config2["ollama_model"] == "model2"
