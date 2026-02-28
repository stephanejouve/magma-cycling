#!/usr/bin/env python3
"""
Tests for OpenAI API Provider.

Tests OpenAIAnalyzer with realistic OpenAI SDK mocks.
"""
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.ai_providers.base import AIProvider
from magma_cycling.ai_providers.openai_api import OpenAIAnalyzer, WorkflowError


@pytest.fixture
def valid_api_key():
    """Valid OpenAI API key format."""
    return "sk-test-openai-key-12345"


@pytest.fixture
def openai_config(valid_api_key):
    """Valid OpenAI configuration."""
    return {"api_key": valid_api_key, "model": "gpt-4-turbo"}


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    with patch("magma_cycling.ai_providers.openai_api.OpenAI") as mock_class:
        mock_client = MagicMock()
        mock_class.return_value = mock_client
        yield mock_client


class TestOpenAIAnalyzer:
    """Tests for OpenAIAnalyzer."""

    # === Initialization Tests ===

    def test_init_success(self, valid_api_key):
        """Test successful initialization with valid config."""
        analyzer = OpenAIAnalyzer(api_key=valid_api_key, model="gpt-4-turbo")

        assert analyzer.provider == AIProvider.OPENAI
        assert analyzer.model == "gpt-4-turbo"
        assert analyzer.client is not None

    def test_init_missing_api_key(self):
        """Test initialization fails without API key."""
        with pytest.raises(WorkflowError) as exc_info:
            OpenAIAnalyzer(api_key=None, model="gpt-4-turbo")

        error_msg = str(exc_info.value).lower()
        assert "api key" in error_msg or "required" in error_msg

    def test_init_empty_api_key(self):
        """Test initialization fails with empty API key."""
        with pytest.raises(WorkflowError) as exc_info:
            OpenAIAnalyzer(api_key="", model="gpt-4-turbo")

        error_msg = str(exc_info.value).lower()
        assert "api key" in error_msg or "required" in error_msg

    def test_init_default_model(self, valid_api_key):
        """Test that default model is used when not specified."""
        analyzer = OpenAIAnalyzer(api_key=valid_api_key)

        assert analyzer.model == "gpt-4-turbo"

    def test_init_custom_model(self, valid_api_key):
        """Test initialization with custom model."""
        analyzer = OpenAIAnalyzer(api_key=valid_api_key, model="gpt-3.5-turbo")

        assert analyzer.model == "gpt-3.5-turbo"

    # === Success Tests ===

    def test_analyze_session_success(self, valid_api_key, mock_openai_client):
        """Test successful analysis."""
        # Mock successful response

        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Analyse complète de la séance cyclisme."
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response

        analyzer = OpenAIAnalyzer(api_key=valid_api_key)
        result = analyzer.analyze_session("Analyser cette séance")

        assert "Analyse complète" in result
        mock_openai_client.chat.completions.create.assert_called_once()

    def test_analyze_with_dataset(self, valid_api_key, mock_openai_client):
        """Test analysis with dataset parameter."""
        mock_response = MagicMock()

        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Analyse avec données."
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response

        analyzer = OpenAIAnalyzer(api_key=valid_api_key)
        dataset = {"tss": 65, "if": 0.85}
        result = analyzer.analyze_session("Prompt", dataset)

        assert "Analyse avec données" in result

    def test_analyze_empty_prompt(self, valid_api_key, mock_openai_client):
        """Test analysis with empty prompt."""
        mock_response = MagicMock()

        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = ""
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response

        analyzer = OpenAIAnalyzer(api_key=valid_api_key)
        result = analyzer.analyze_session("")

        # Should handle empty prompt
        assert result == ""

    def test_analyze_large_prompt(self, valid_api_key, mock_openai_client):
        """Test analysis with very large prompt."""
        mock_response = MagicMock()

        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Réponse à prompt large"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response

        analyzer = OpenAIAnalyzer(api_key=valid_api_key)
        large_prompt = "A" * 100000  # 100KB prompt (GPT-4 handles large context)

        result = analyzer.analyze_session(large_prompt)

        assert "Réponse" in result
        # Verify prompt was passed
        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args is not None

    def test_analyze_special_characters(self, valid_api_key, mock_openai_client):
        """Test analysis with special characters."""
        mock_response = MagicMock()

        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Réponse avec émojis 🚴‍♂️"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response

        analyzer = OpenAIAnalyzer(api_key=valid_api_key)
        prompt = "Test émojis 🚴‍♂️ and spéciål çhars: €$£"

        result = analyzer.analyze_session(prompt)

        assert result is not None

    # === Error Handling Tests ===

    def test_analyze_authentication_error(self, valid_api_key, mock_openai_client):
        """Test handling of authentication error."""
        mock_openai_client.chat.completions.create.side_effect = Exception("Invalid API key")

        analyzer = OpenAIAnalyzer(api_key=valid_api_key)

        with pytest.raises(WorkflowError) as exc_info:
            analyzer.analyze_session("Test")

        assert "API key" in str(exc_info.value) or "Invalid" in str(exc_info.value)

    def test_analyze_rate_limit_error(self, valid_api_key, mock_openai_client):
        """Test handling of rate limit error."""
        mock_openai_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")

        analyzer = OpenAIAnalyzer(api_key=valid_api_key)

        with pytest.raises(WorkflowError) as exc_info:
            analyzer.analyze_session("Test")

        assert "Rate limit" in str(exc_info.value) or "exceeded" in str(exc_info.value)

    def test_analyze_server_error(self, valid_api_key, mock_openai_client):
        """Test handling of server error."""
        mock_openai_client.chat.completions.create.side_effect = Exception("Internal server error")

        analyzer = OpenAIAnalyzer(api_key=valid_api_key)

        with pytest.raises(WorkflowError) as exc_info:
            analyzer.analyze_session("Test")

        assert "server" in str(exc_info.value).lower() or "error" in str(exc_info.value).lower()

    def test_analyze_timeout_error(self, valid_api_key, mock_openai_client):
        """Test handling of timeout."""
        import requests

        mock_openai_client.chat.completions.create.side_effect = requests.Timeout("Request timeout")

        analyzer = OpenAIAnalyzer(api_key=valid_api_key)

        with pytest.raises(WorkflowError) as exc_info:
            analyzer.analyze_session("Test")

        assert "timeout" in str(exc_info.value).lower()

    def test_analyze_connection_error(self, valid_api_key, mock_openai_client):
        """Test handling of connection error."""
        import requests

        mock_openai_client.chat.completions.create.side_effect = requests.ConnectionError(
            "Cannot connect"
        )

        analyzer = OpenAIAnalyzer(api_key=valid_api_key)

        with pytest.raises(WorkflowError) as exc_info:
            analyzer.analyze_session("Test")

        assert "connect" in str(exc_info.value).lower()

    # === Provider Info Tests ===

    def test_get_provider_info(self, valid_api_key):
        """Test get_provider_info returns correct information."""
        analyzer = OpenAIAnalyzer(api_key=valid_api_key, model="gpt-3.5-turbo")

        info = analyzer.get_provider_info()

        assert info["provider"] == "openai"
        assert info["model"] == "gpt-3.5-turbo"
        assert info["requires_api_key"] is True

    def test_get_provider_info_structure(self, valid_api_key):
        """Test provider info has expected structure."""
        analyzer = OpenAIAnalyzer(api_key=valid_api_key)

        info = analyzer.get_provider_info()

        assert isinstance(info, dict)
        assert "provider" in info
        assert "model" in info
        assert "cost_input" in info
        assert "cost_output" in info

    def test_validate_config_success(self, valid_api_key):
        """Test config validation returns True with valid config."""
        analyzer = OpenAIAnalyzer(api_key=valid_api_key)

        is_valid = analyzer.validate_config()

        assert is_valid is True

    # === Edge Cases ===

    def test_multiple_analyzers_independent(self, valid_api_key):
        """Test multiple analyzer instances are independent."""
        analyzer1 = OpenAIAnalyzer(api_key=valid_api_key, model="gpt-4-turbo")

        analyzer2 = OpenAIAnalyzer(api_key=valid_api_key, model="gpt-3.5-turbo")

        assert analyzer1 is not analyzer2
        assert analyzer1.model != analyzer2.model

    def test_model_parameter_preserved(self, valid_api_key):
        """Test that model parameter is preserved."""
        custom_model = "gpt-4"

        analyzer = OpenAIAnalyzer(api_key=valid_api_key, model=custom_model)

        assert analyzer.model == custom_model

    def test_client_initialized(self, valid_api_key):
        """Test that OpenAI client is properly initialized."""
        analyzer = OpenAIAnalyzer(api_key=valid_api_key)

        assert hasattr(analyzer, "client")
        assert analyzer.client is not None
        assert analyzer.validate_config() is True

    def test_provider_enum_value(self, valid_api_key):
        """Test provider enum is correctly set."""
        analyzer = OpenAIAnalyzer(api_key=valid_api_key)

        assert analyzer.provider == AIProvider.OPENAI
        assert analyzer.provider.value == "openai"

    def test_gpt4_turbo_default(self, valid_api_key):
        """Test that gpt-4-turbo is the default model."""
        analyzer = OpenAIAnalyzer(api_key=valid_api_key)

        assert analyzer.model == "gpt-4-turbo"
