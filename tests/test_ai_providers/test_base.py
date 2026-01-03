#!/usr/bin/env python3
"""
Tests for AI Providers base classes.

Tests AIProvider enum and AIAnalyzer abstract base class.
"""

import pytest

from cyclisme_training_logs.ai_providers.base import AIAnalyzer, AIProvider


class TestAIProviderEnum:
    """Tests for AIProvider enum."""

    def test_enum_has_all_providers(self):
        """Test that enum contains all 5 expected providers."""
        expected_providers = ["clipboard", "claude_api", "mistral_api", "openai", "ollama"]
        actual_providers = [p.value for p in AIProvider]

        assert len(actual_providers) == 5, f"Expected 5 providers, got {len(actual_providers)}"
        for provider in expected_providers:
            assert provider in actual_providers, f"Provider {provider} not in enum"

    def test_enum_values_are_strings(self):
        """Test that all enum values are strings."""
        for provider in AIProvider:
            assert isinstance(provider.value, str), f"Provider {provider.name} value is not string"

    def test_enum_clipboard_exists(self):
        """Test that CLIPBOARD provider exists (default)."""
        assert AIProvider.CLIPBOARD.value == "clipboard"

    def test_enum_claude_exists(self):
        """Test that CLAUDE provider exists."""
        assert AIProvider.CLAUDE.value == "claude_api"

    def test_enum_mistral_exists(self):
        """Test that MISTRAL provider exists."""
        assert AIProvider.MISTRAL.value == "mistral_api"

    def test_enum_openai_exists(self):
        """Test that OPENAI provider exists."""
        assert AIProvider.OPENAI.value == "openai"

    def test_enum_ollama_exists(self):
        """Test that OLLAMA provider exists."""
        assert AIProvider.OLLAMA.value == "ollama"

    def test_enum_from_string(self):
        """Test that enum can be created from string value."""
        provider = AIProvider("clipboard")
        assert provider == AIProvider.CLIPBOARD

    def test_enum_invalid_value_raises_error(self):
        """Test that invalid provider name raises ValueError."""
        with pytest.raises(ValueError):
            AIProvider("invalid_provider")


class TestAIAnalyzerABC:
    """Tests for AIAnalyzer abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that AIAnalyzer cannot be instantiated directly."""
        with pytest.raises(TypeError) as excinfo:
            AIAnalyzer()

        assert "Can't instantiate abstract class" in str(excinfo.value)

    def test_subclass_must_implement_analyze_session(self):
        """Test that subclass must implement analyze_session method."""

        # Create incomplete subclass
        class IncompleteAnalyzer(AIAnalyzer):
            pass

        with pytest.raises(TypeError) as excinfo:
            IncompleteAnalyzer()

        assert "analyze_session" in str(excinfo.value)

    def test_subclass_can_use_default_get_provider_info(self):
        """Test that subclass can use default get_provider_info implementation."""

        # Create subclass using default get_provider_info
        class SimpleAnalyzer(AIAnalyzer):
            def __init__(self):
                super().__init__()
                self.provider = AIProvider.CLIPBOARD

            def analyze_session(self, prompt, dataset=None):
                return "test"

        analyzer = SimpleAnalyzer()
        info = analyzer.get_provider_info()

        # Should use default implementation
        assert isinstance(info, dict)
        assert info["provider"] == "clipboard"

    def test_subclass_can_use_default_validate_config(self):
        """Test that subclass can use default validate_config implementation."""

        # Create subclass using default validate_config
        class SimpleAnalyzer(AIAnalyzer):
            def __init__(self):
                super().__init__()
                self.provider = AIProvider.CLIPBOARD

            def analyze_session(self, prompt, dataset=None):
                return "test"

        analyzer = SimpleAnalyzer()
        is_valid = analyzer.validate_config()

        # Should use default implementation (returns True)
        assert is_valid is True

    def test_complete_subclass_can_be_instantiated(self):
        """Test that complete subclass can be instantiated."""

        class CompleteAnalyzer(AIAnalyzer):
            def __init__(self):
                super().__init__()
                self.provider = AIProvider.CLIPBOARD

            def analyze_session(self, prompt, dataset=None):
                return "test analysis"

            def get_provider_info(self):
                return {"provider": "test"}

            def validate_config(self):
                return True

        # Should not raise
        analyzer = CompleteAnalyzer()
        assert analyzer is not None
        assert analyzer.provider == AIProvider.CLIPBOARD

    def test_subclass_analyze_session_signature(self):
        """Test that analyze_session has correct signature."""

        class TestAnalyzer(AIAnalyzer):
            def __init__(self):
                super().__init__()
                self.provider = AIProvider.CLIPBOARD

            def analyze_session(self, prompt, dataset=None):
                return f"Analyzed: {prompt[:20]}"

            def get_provider_info(self):
                return {}

            def validate_config(self):
                return True

        analyzer = TestAnalyzer()
        result = analyzer.analyze_session("Test prompt", dataset=None)
        assert result == "Analyzed: Test prompt"

    def test_subclass_has_provider_attribute(self):
        """Test that subclass instances have provider attribute."""

        class TestAnalyzer(AIAnalyzer):
            def __init__(self):
                super().__init__()
                self.provider = AIProvider.OLLAMA

            def analyze_session(self, prompt, dataset=None):
                return "test"

            def get_provider_info(self):
                return {}

            def validate_config(self):
                return True

        analyzer = TestAnalyzer()
        assert hasattr(analyzer, "provider")
        assert analyzer.provider == AIProvider.OLLAMA
