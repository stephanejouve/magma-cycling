#!/usr/bin/env python3
"""
Tests for Mistral API Provider.

Tests MistralAPIAnalyzer with realistic Mistral SDK mocks.
"""

from unittest.mock import MagicMock, patch

import pytest

from cyclisme_training_logs.ai_providers.base import AIProvider
from cyclisme_training_logs.ai_providers.mistral_api import MistralAPIAnalyzer, WorkflowError


@pytest.fixture
def valid_api_key():
    """Valid Mistral API key."""
    return "mistral-test-key-12345"


@pytest.fixture
def mistral_config(valid_api_key):
    """Valid Mistral configuration."""
    return {
        "api_key": valid_api_key,
        "model": "mistral-large-latest",
        "max_tokens": 4000,
        "temperature": 0.7,
    }


@pytest.fixture
def mock_mistral_client():
    """Mock Mistral client."""
    with patch("cyclisme_training_logs.ai_providers.mistral_api.MistralClient") as mock_class:
        mock_client = MagicMock()
        # Mock the chat method directly (not chat.complete)
        mock_client.chat = MagicMock()
        mock_class.return_value = mock_client
        yield mock_client


class TestMistralAPIAnalyzer:
    """Tests for MistralAPIAnalyzer."""

    # === Initialization Tests ===

    def test_init_success(self, valid_api_key):
        """Test successful initialization with valid config."""
        analyzer = MistralAPIAnalyzer(api_key=valid_api_key, model="mistral-large-latest")

        assert analyzer.provider == AIProvider.MISTRAL
        assert analyzer.model == "mistral-large-latest"
        assert analyzer.client is not None
        assert analyzer.temperature == 0.7  # Default

    def test_init_missing_api_key(self):
        """Test initialization fails without API key."""
        with pytest.raises(WorkflowError) as exc_info:
            MistralAPIAnalyzer(api_key=None, model="mistral-large-latest")

        error_msg = str(exc_info.value).lower()
        assert "api key" in error_msg or "required" in error_msg

    def test_init_empty_api_key(self):
        """Test initialization fails with empty API key."""
        with pytest.raises(WorkflowError) as exc_info:
            MistralAPIAnalyzer(api_key="", model="mistral-large-latest")

        error_msg = str(exc_info.value).lower()
        assert "api key" in error_msg or "required" in error_msg

    def test_init_default_model(self, valid_api_key):
        """Test that default model is used when not specified."""
        analyzer = MistralAPIAnalyzer(api_key=valid_api_key)

        assert analyzer.model == "mistral-large-latest"

    def test_init_custom_parameters(self, valid_api_key):
        """Test initialization with custom parameters."""
        analyzer = MistralAPIAnalyzer(
            api_key=valid_api_key,
            model="mistral-medium-latest",
            temperature=0.5,
            max_tokens=8000,
            timeout=120,
        )

        assert analyzer.model == "mistral-medium-latest"
        assert analyzer.temperature == 0.5
        assert analyzer.max_tokens == 8000
        assert analyzer.timeout == 120

    # === Success Tests ===

    def test_analyze_session_success(self, valid_api_key, mock_mistral_client):
        """Test successful analysis."""
        # Mock successful response
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Analyse complète de la séance cyclisme."
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_mistral_client.chat.return_value = mock_response

        analyzer = MistralAPIAnalyzer(api_key=valid_api_key)
        result = analyzer.analyze_session("Analyser cette séance")

        assert "Analyse complète" in result
        mock_mistral_client.chat.assert_called_once()

    def test_analyze_with_dataset(self, valid_api_key, mock_mistral_client):
        """Test analysis with dataset parameter."""
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Analyse avec données."
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_mistral_client.chat.return_value = mock_response

        analyzer = MistralAPIAnalyzer(api_key=valid_api_key)
        dataset = {"tss": 65, "if": 0.85}
        result = analyzer.analyze_session("Prompt", dataset)

        assert "Analyse avec données" in result

    def test_analyze_empty_prompt(self, valid_api_key, mock_mistral_client):
        """Test analysis with empty prompt."""
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = ""
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_mistral_client.chat.return_value = mock_response

        analyzer = MistralAPIAnalyzer(api_key=valid_api_key)
        result = analyzer.analyze_session("")

        # Should handle empty prompt
        assert result == ""

    def test_analyze_large_prompt(self, valid_api_key, mock_mistral_client):
        """Test analysis with very large prompt."""
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Réponse à prompt large"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_mistral_client.chat.return_value = mock_response

        analyzer = MistralAPIAnalyzer(api_key=valid_api_key)
        large_prompt = "A" * 30000  # 30KB prompt

        result = analyzer.analyze_session(large_prompt)

        assert "Réponse" in result
        # Verify prompt was passed
        call_args = mock_mistral_client.chat.call_args
        assert call_args is not None

    def test_analyze_special_characters(self, valid_api_key, mock_mistral_client):
        """Test analysis with special characters."""
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Réponse avec émojis 🚴‍♂️"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_mistral_client.chat.return_value = mock_response

        analyzer = MistralAPIAnalyzer(api_key=valid_api_key)
        prompt = "Test émojis 🚴‍♂️ and spéciål çhars: €$£"

        result = analyzer.analyze_session(prompt)

        assert result is not None

    # === Error Handling Tests ===

    def test_analyze_authentication_error(self, valid_api_key, mock_mistral_client):
        """Test handling of authentication error."""
        mock_mistral_client.chat.side_effect = Exception("Invalid API key")

        analyzer = MistralAPIAnalyzer(api_key=valid_api_key)

        with pytest.raises(WorkflowError) as exc_info:
            analyzer.analyze_session("Test")

        assert "API key" in str(exc_info.value) or "Invalid" in str(exc_info.value)

    def test_analyze_rate_limit_error(self, valid_api_key, mock_mistral_client):
        """Test handling of rate limit error."""
        mock_mistral_client.chat.side_effect = Exception("Rate limit exceeded")

        analyzer = MistralAPIAnalyzer(api_key=valid_api_key)

        with pytest.raises(WorkflowError) as exc_info:
            analyzer.analyze_session("Test")

        assert "Rate limit" in str(exc_info.value) or "exceeded" in str(exc_info.value)

    def test_analyze_server_error(self, valid_api_key, mock_mistral_client):
        """Test handling of server error."""
        mock_mistral_client.chat.side_effect = Exception("Internal server error")

        analyzer = MistralAPIAnalyzer(api_key=valid_api_key)

        with pytest.raises(WorkflowError) as exc_info:
            analyzer.analyze_session("Test")

        assert "server" in str(exc_info.value).lower() or "error" in str(exc_info.value).lower()

    def test_analyze_timeout_error(self, valid_api_key, mock_mistral_client):
        """Test handling of timeout."""
        import requests

        mock_mistral_client.chat.side_effect = requests.Timeout("Request timeout")

        analyzer = MistralAPIAnalyzer(api_key=valid_api_key)

        with pytest.raises(WorkflowError) as exc_info:
            analyzer.analyze_session("Test")

        assert "timeout" in str(exc_info.value).lower()

    def test_analyze_connection_error(self, valid_api_key, mock_mistral_client):
        """Test handling of connection error."""
        import requests

        mock_mistral_client.chat.side_effect = requests.ConnectionError("Cannot connect")

        analyzer = MistralAPIAnalyzer(api_key=valid_api_key)

        with pytest.raises(WorkflowError) as exc_info:
            analyzer.analyze_session("Test")

        assert "connect" in str(exc_info.value).lower()

    # === Provider Info Tests ===

    def test_get_provider_info(self, valid_api_key):
        """Test get_provider_info returns correct information."""
        analyzer = MistralAPIAnalyzer(api_key=valid_api_key, model="mistral-medium-latest")

        info = analyzer.get_provider_info()

        assert info["provider"] == "mistral_api"
        assert info["model"] == "mistral-medium-latest"
        assert info["requires_api_key"] is True

    def test_get_provider_info_structure(self, valid_api_key):
        """Test provider info has expected structure."""
        analyzer = MistralAPIAnalyzer(api_key=valid_api_key)

        info = analyzer.get_provider_info()

        assert isinstance(info, dict)
        assert "provider" in info
        assert "model" in info
        assert "cost_input" in info
        assert "cost_output" in info

    def test_validate_config_success(self, valid_api_key):
        """Test config validation returns True with valid config."""
        analyzer = MistralAPIAnalyzer(api_key=valid_api_key)

        is_valid = analyzer.validate_config()

        assert is_valid is True

    # === Edge Cases ===

    def test_multiple_analyzers_independent(self, valid_api_key):
        """Test multiple analyzer instances are independent."""
        analyzer1 = MistralAPIAnalyzer(api_key=valid_api_key, model="mistral-large-latest")
        analyzer2 = MistralAPIAnalyzer(api_key=valid_api_key, model="mistral-medium-latest")

        assert analyzer1 is not analyzer2
        assert analyzer1.model != analyzer2.model

    def test_model_parameter_preserved(self, valid_api_key):
        """Test that model parameter is preserved."""
        custom_model = "mistral-small-latest"
        analyzer = MistralAPIAnalyzer(api_key=valid_api_key, model=custom_model)

        assert analyzer.model == custom_model

    def test_client_initialized(self, valid_api_key):
        """Test that Mistral client is properly initialized."""
        analyzer = MistralAPIAnalyzer(api_key=valid_api_key)

        assert hasattr(analyzer, "client")
        assert analyzer.client is not None
        assert analyzer.validate_config() is True

    def test_temperature_parameter(self, valid_api_key):
        """Test that temperature parameter is preserved."""
        analyzer = MistralAPIAnalyzer(api_key=valid_api_key, temperature=0.3)

        assert analyzer.temperature == 0.3

    def test_max_tokens_parameter(self, valid_api_key):
        """Test that max_tokens parameter is preserved."""
        analyzer = MistralAPIAnalyzer(api_key=valid_api_key, max_tokens=8000)

        assert analyzer.max_tokens == 8000

    def test_timeout_parameter(self, valid_api_key):
        """Test that timeout parameter is preserved."""
        analyzer = MistralAPIAnalyzer(api_key=valid_api_key, timeout=120)

        assert analyzer.timeout == 120

    def test_provider_enum_value(self, valid_api_key):
        """Test provider enum is correctly set."""
        analyzer = MistralAPIAnalyzer(api_key=valid_api_key)

        assert analyzer.provider == AIProvider.MISTRAL
        assert analyzer.provider.value == "mistral_api"
