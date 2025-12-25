#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Ollama Local LLM Provider.

Tests OllamaAnalyzer with mocked requests to local server.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from cyclisme_training_logs.ai_providers.ollama import OllamaAnalyzer, WorkflowError
from cyclisme_training_logs.ai_providers.base import AIProvider
import requests


@pytest.fixture
def default_host():
    """Default Ollama host."""
    return 'http://localhost:11434'


@pytest.fixture
def ollama_config(default_host):
    """Valid Ollama configuration."""
    return {
        'host': default_host,
        'model': 'mistral:7b'
    }


class TestOllamaAnalyzer:
    """Tests for OllamaAnalyzer."""

    # === Initialization Tests ===

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        analyzer = OllamaAnalyzer()

        assert analyzer.provider == AIProvider.OLLAMA
        assert analyzer.model == 'mistral:7b'  # Default model
        assert analyzer.host == 'http://localhost:11434'  # Default host
        assert analyzer.api_url == 'http://localhost:11434/api/generate'

    def test_init_with_custom_model(self):
        """Test initialization with custom model."""
        analyzer = OllamaAnalyzer(model='llama3.1:70b')

        assert analyzer.model == 'llama3.1:70b'
        assert analyzer.host == 'http://localhost:11434'

    def test_init_with_custom_host(self):
        """Test initialization with custom host."""
        custom_host = 'http://192.168.1.100:11434'
        analyzer = OllamaAnalyzer(host=custom_host)

        assert analyzer.host == custom_host
        assert analyzer.api_url == f'{custom_host}/api/generate'

    def test_init_with_all_custom_params(self):
        """Test initialization with all custom parameters."""
        analyzer = OllamaAnalyzer(
            host='http://custom-host:8080',
            model='codellama:13b'
        )

        assert analyzer.host == 'http://custom-host:8080'
        assert analyzer.model == 'codellama:13b'
        assert analyzer.api_url == 'http://custom-host:8080/api/generate'

    def test_api_url_construction(self):
        """Test that API URL is correctly constructed."""
        analyzer = OllamaAnalyzer(host='http://example.com:11434')

        assert analyzer.api_url == 'http://example.com:11434/api/generate'

    # === Success Tests ===

    @patch('cyclisme_training_logs.ai_providers.ollama.requests.post')
    def test_analyze_session_success(self, mock_post):
        """Test successful analysis."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'response': 'Analyse complète de la séance cyclisme.'}
        mock_post.return_value = mock_response

        analyzer = OllamaAnalyzer()
        result = analyzer.analyze_session("Analyser cette séance")

        assert "Analyse complète" in result
        mock_post.assert_called_once()

        # Verify request parameters
        call_args = mock_post.call_args
        assert call_args[1]['json']['model'] == 'mistral:7b'
        assert call_args[1]['json']['stream'] is False

    @patch('cyclisme_training_logs.ai_providers.ollama.requests.post')
    def test_analyze_with_dataset(self, mock_post):
        """Test analysis with dataset parameter."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'response': 'Analyse avec données.'}
        mock_post.return_value = mock_response

        analyzer = OllamaAnalyzer()
        dataset = {"tss": 65, "if": 0.85}
        result = analyzer.analyze_session("Prompt", dataset)

        assert "Analyse avec données" in result

    @patch('cyclisme_training_logs.ai_providers.ollama.requests.post')
    def test_analyze_empty_prompt(self, mock_post):
        """Test analysis with empty prompt."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'response': ''}
        mock_post.return_value = mock_response

        analyzer = OllamaAnalyzer()
        result = analyzer.analyze_session("")

        assert result == ""

    @patch('cyclisme_training_logs.ai_providers.ollama.requests.post')
    def test_analyze_large_prompt(self, mock_post):
        """Test analysis with very large prompt."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'response': 'Réponse à prompt large'}
        mock_post.return_value = mock_response

        analyzer = OllamaAnalyzer()
        large_prompt = "A" * 50000  # 50KB prompt

        result = analyzer.analyze_session(large_prompt)

        assert "Réponse" in result
        mock_post.assert_called_once()

    @patch('cyclisme_training_logs.ai_providers.ollama.requests.post')
    def test_analyze_special_characters(self, mock_post):
        """Test analysis with special characters."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'response': 'Réponse avec émojis 🚴‍♂️'}
        mock_post.return_value = mock_response

        analyzer = OllamaAnalyzer()
        prompt = "Test émojis 🚴‍♂️ and spéciål çhars: €$£"

        result = analyzer.analyze_session(prompt)

        assert result is not None

    @patch('cyclisme_training_logs.ai_providers.ollama.requests.post')
    def test_timeout_parameter(self, mock_post):
        """Test that timeout is set to 600s (10min)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'response': 'Test'}
        mock_post.return_value = mock_response

        analyzer = OllamaAnalyzer()
        analyzer.analyze_session("Test prompt")

        # Verify timeout parameter
        call_args = mock_post.call_args
        assert call_args[1]['timeout'] == 600

    # === Error Handling Tests ===

    @patch('cyclisme_training_logs.ai_providers.ollama.requests.post')
    def test_analyze_connection_error(self, mock_post):
        """Test handling of connection error (server not running)."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Cannot connect")

        analyzer = OllamaAnalyzer()

        with pytest.raises(WorkflowError) as exc_info:
            analyzer.analyze_session("Test")

        error_msg = str(exc_info.value).lower()
        assert "connect" in error_msg or "ollama" in error_msg

    @patch('cyclisme_training_logs.ai_providers.ollama.requests.post')
    def test_analyze_timeout_error(self, mock_post):
        """Test handling of timeout."""
        mock_post.side_effect = requests.exceptions.Timeout("Request timeout")

        analyzer = OllamaAnalyzer()

        with pytest.raises(WorkflowError) as exc_info:
            analyzer.analyze_session("Test")

        assert "timeout" in str(exc_info.value).lower() or "failed" in str(exc_info.value).lower()

    @patch('cyclisme_training_logs.ai_providers.ollama.requests.post')
    def test_analyze_http_error(self, mock_post):
        """Test handling of HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        mock_post.return_value = mock_response

        analyzer = OllamaAnalyzer()

        with pytest.raises(WorkflowError) as exc_info:
            analyzer.analyze_session("Test")

        assert "failed" in str(exc_info.value).lower() or "error" in str(exc_info.value).lower()

    @patch('cyclisme_training_logs.ai_providers.ollama.requests.post')
    def test_analyze_invalid_json_response(self, mock_post):
        """Test handling of invalid JSON response."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response

        analyzer = OllamaAnalyzer()

        with pytest.raises(WorkflowError) as exc_info:
            analyzer.analyze_session("Test")

        assert "failed" in str(exc_info.value).lower()

    @patch('cyclisme_training_logs.ai_providers.ollama.requests.post')
    def test_analyze_missing_response_field(self, mock_post):
        """Test handling when response field is missing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}  # Missing 'response' field
        mock_post.return_value = mock_response

        analyzer = OllamaAnalyzer()
        result = analyzer.analyze_session("Test")

        # Should return empty string when response field missing
        assert result == ''

    # === Provider Info Tests ===

    @patch('cyclisme_training_logs.ai_providers.ollama.requests.get')
    def test_get_provider_info(self, mock_get):
        """Test get_provider_info returns correct information."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        analyzer = OllamaAnalyzer(model='llama3.1:70b')
        info = analyzer.get_provider_info()

        assert info['provider'] == 'ollama'
        assert info['model'] == 'llama3.1:70b'
        assert info['requires_api_key'] is False
        assert '$0' in info['cost_input']

    @patch('cyclisme_training_logs.ai_providers.ollama.requests.get')
    def test_get_provider_info_structure(self, mock_get):
        """Test provider info has expected structure."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        analyzer = OllamaAnalyzer()
        info = analyzer.get_provider_info()

        assert isinstance(info, dict)
        assert 'provider' in info
        assert 'model' in info
        assert 'host' in info
        assert 'privacy' in info

    @patch('cyclisme_training_logs.ai_providers.ollama.requests.get')
    def test_validate_config_success(self, mock_get):
        """Test config validation returns True when server accessible."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        analyzer = OllamaAnalyzer()
        is_valid = analyzer.validate_config()

        assert is_valid is True
        # Verify it called /api/tags endpoint
        mock_get.assert_called_once_with('http://localhost:11434/api/tags', timeout=5)

    @patch('cyclisme_training_logs.ai_providers.ollama.requests.get')
    def test_validate_config_server_offline(self, mock_get):
        """Test config validation returns False when server offline."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Cannot connect")

        analyzer = OllamaAnalyzer()
        is_valid = analyzer.validate_config()

        assert is_valid is False

    @patch('cyclisme_training_logs.ai_providers.ollama.requests.get')
    def test_validate_config_timeout(self, mock_get):
        """Test config validation returns False on timeout."""
        mock_get.side_effect = requests.exceptions.Timeout("Timeout")

        analyzer = OllamaAnalyzer()
        is_valid = analyzer.validate_config()

        assert is_valid is False

    @patch('cyclisme_training_logs.ai_providers.ollama.requests.get')
    def test_validate_config_http_error(self, mock_get):
        """Test config validation returns False on HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        analyzer = OllamaAnalyzer()
        is_valid = analyzer.validate_config()

        # Should return False for non-200 status
        assert is_valid is False

    # === Edge Cases ===

    def test_multiple_analyzers_independent(self):
        """Test multiple analyzer instances are independent."""
        analyzer1 = OllamaAnalyzer(model='llama3.1:70b')
        analyzer2 = OllamaAnalyzer(model='mistral:7b')

        assert analyzer1 is not analyzer2
        assert analyzer1.model != analyzer2.model

    def test_model_parameter_preserved(self):
        """Test that model parameter is preserved."""
        custom_model = 'codellama:13b'
        analyzer = OllamaAnalyzer(model=custom_model)

        assert analyzer.model == custom_model

    def test_host_parameter_preserved(self):
        """Test that host parameter is preserved."""
        custom_host = 'http://192.168.1.50:11434'
        analyzer = OllamaAnalyzer(host=custom_host)

        assert analyzer.host == custom_host

    def test_provider_enum_value(self):
        """Test provider enum is correctly set."""
        analyzer = OllamaAnalyzer()

        assert analyzer.provider == AIProvider.OLLAMA
        assert analyzer.provider.value == 'ollama'

    def test_no_api_key_required(self):
        """Test that Ollama doesn't require API key."""
        # Should not raise any errors
        analyzer = OllamaAnalyzer()

        assert analyzer is not None
        assert analyzer.provider == AIProvider.OLLAMA

    @patch('cyclisme_training_logs.ai_providers.ollama.requests.get')
    def test_provider_info_status_ready_when_online(self, mock_get):
        """Test that status is 'ready' when server is online."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        analyzer = OllamaAnalyzer()
        info = analyzer.get_provider_info()

        assert info['status'] == 'ready'

    @patch('cyclisme_training_logs.ai_providers.ollama.requests.get')
    def test_provider_info_status_offline_when_unavailable(self, mock_get):
        """Test that status is 'server_offline' when server unavailable."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Cannot connect")

        analyzer = OllamaAnalyzer()
        info = analyzer.get_provider_info()

        assert info['status'] == 'server_offline'
