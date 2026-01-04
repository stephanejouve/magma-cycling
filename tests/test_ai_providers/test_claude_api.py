#!/usr/bin/env python3
"""
Tests for Claude API Provider.

Tests ClaudeAPIAnalyzer with realistic Anthropic SDK mocks.
"""
from unittest.mock import MagicMock, patch

import pytest

from cyclisme_training_logs.ai_providers.base import AIProvider
from cyclisme_training_logs.ai_providers.claude_api import ClaudeAPIAnalyzer


@pytest.fixture
def valid_api_key():
    """Valid Claude API key format."""
    return "sk-ant-test-key-123"


@pytest.fixture
def claude_config(valid_api_key):
    """Valid Claude configuration."""
    return {"api_key": valid_api_key, "model": "claude-sonnet-4-20250514", "max_tokens": 4000}


@pytest.fixture
def mock_anthropic():
    """Mock Anthropic client."""
    with patch("cyclisme_training_logs.ai_providers.claude_api.Anthropic") as mock_class:
        mock_client = MagicMock()
        mock_class.return_value = mock_client
        yield mock_client


class TestClaudeAPIAnalyzer:
    """Tests for ClaudeAPIAnalyzer."""

    # === Initialization Tests ===

    def test_init_success(self, valid_api_key):
        """Test successful initialization with valid config."""
        analyzer = ClaudeAPIAnalyzer(api_key=valid_api_key, model="claude-sonnet-4-20250514")

        assert analyzer.provider == AIProvider.CLAUDE
        assert analyzer.model == "claude-sonnet-4-20250514"
        assert analyzer.client is not None

    def test_init_missing_api_key(self):
        """Test initialization fails without API key."""
        from cyclisme_training_logs.ai_providers.claude_api import WorkflowError

        with pytest.raises(WorkflowError) as exc_info:
            ClaudeAPIAnalyzer(api_key=None, model="claude-sonnet-4")

        error_msg = str(exc_info.value).lower()
        assert "api key" in error_msg or "format" in error_msg

    def test_init_invalid_api_key_format(self):
        """Test initialization fails with invalid API key format."""
        from cyclisme_training_logs.ai_providers.claude_api import WorkflowError

        with pytest.raises(WorkflowError) as exc_info:
            ClaudeAPIAnalyzer(api_key="invalid-key", model="claude-sonnet-4")

        error_msg = str(exc_info.value).lower()
        assert "sk-ant-" in error_msg or "format" in error_msg

    def test_init_default_model(self, valid_api_key):
        """Test that default model is used when not specified."""
        analyzer = ClaudeAPIAnalyzer(api_key=valid_api_key)

        assert analyzer.model == "claude-sonnet-4-20250514"

    def test_init_custom_max_tokens(self, valid_api_key):
        """Test initialization with custom max_tokens."""
        analyzer = ClaudeAPIAnalyzer(
            api_key=valid_api_key, model="claude-sonnet-4", max_tokens=8000
        )

        assert analyzer.max_tokens == 8000

    # === Success Tests ===

    def test_analyze_session_success(self, valid_api_key, mock_anthropic):
        """Test successful analysis."""
        # Mock successful response
        mock_message = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Analyse complète de la séance cyclisme."
        mock_message.content = [mock_content]
        mock_anthropic.messages.create.return_value = mock_message

        analyzer = ClaudeAPIAnalyzer(api_key=valid_api_key)
        result = analyzer.analyze_session("Analyser cette séance")

        assert "Analyse complète" in result
        mock_anthropic.messages.create.assert_called_once()

    def test_analyze_with_dataset(self, valid_api_key, mock_anthropic):
        """Test analysis with dataset parameter."""
        mock_message = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Analyse avec données."
        mock_message.content = [mock_content]
        mock_anthropic.messages.create.return_value = mock_message

        analyzer = ClaudeAPIAnalyzer(api_key=valid_api_key)
        dataset = {"tss": 65, "if": 0.85}
        result = analyzer.analyze_session("Prompt", dataset)

        assert "Analyse avec données" in result

    def test_analyze_empty_prompt(self, valid_api_key, mock_anthropic):
        """Test analysis with empty prompt."""
        mock_message = MagicMock()
        mock_content = MagicMock()
        mock_content.text = ""
        mock_message.content = [mock_content]
        mock_anthropic.messages.create.return_value = mock_message

        analyzer = ClaudeAPIAnalyzer(api_key=valid_api_key)
        result = analyzer.analyze_session("")

        # Should handle empty prompt
        assert result == ""

    def test_analyze_large_prompt(self, valid_api_key, mock_anthropic):
        """Test analysis with very large prompt."""
        mock_message = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Réponse à prompt large"
        mock_message.content = [mock_content]
        mock_anthropic.messages.create.return_value = mock_message

        analyzer = ClaudeAPIAnalyzer(api_key=valid_api_key)
        large_prompt = "A" * 50000

        result = analyzer.analyze_session(large_prompt)

        assert "Réponse" in result
        # Verify prompt was passed
        call_args = mock_anthropic.messages.create.call_args
        assert call_args is not None

    def test_analyze_special_characters(self, valid_api_key, mock_anthropic):
        """Test analysis with special characters."""
        mock_message = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Réponse avec émojis 🚴‍♂️"
        mock_message.content = [mock_content]
        mock_anthropic.messages.create.return_value = mock_message

        analyzer = ClaudeAPIAnalyzer(api_key=valid_api_key)
        prompt = "Test émojis 🚴‍♂️ and spéciål çhars: €$£"

        result = analyzer.analyze_session(prompt)

        assert result is not None

    # === Error Handling Tests ===

    def test_analyze_authentication_error(self, valid_api_key, mock_anthropic):
        """Test handling of authentication error."""
        # Mock authentication error
        mock_anthropic.messages.create.side_effect = Exception("Invalid API key")

        analyzer = ClaudeAPIAnalyzer(api_key=valid_api_key)

        with pytest.raises(Exception) as exc_info:
            analyzer.analyze_session("Test")

        assert "API key" in str(exc_info.value) or "Invalid" in str(exc_info.value)

    def test_analyze_rate_limit_error(self, valid_api_key, mock_anthropic):
        """Test handling of rate limit error."""
        mock_anthropic.messages.create.side_effect = Exception("Rate limit exceeded")

        analyzer = ClaudeAPIAnalyzer(api_key=valid_api_key)

        with pytest.raises(Exception) as exc_info:
            analyzer.analyze_session("Test")

        assert "Rate limit" in str(exc_info.value) or "exceeded" in str(exc_info.value)

    def test_analyze_server_error(self, valid_api_key, mock_anthropic):
        """Test handling of server error."""
        mock_anthropic.messages.create.side_effect = Exception("Internal server error")

        analyzer = ClaudeAPIAnalyzer(api_key=valid_api_key)

        with pytest.raises(Exception) as exc_info:
            analyzer.analyze_session("Test")

        assert "server" in str(exc_info.value).lower() or "error" in str(exc_info.value).lower()

    def test_analyze_timeout_error(self, valid_api_key, mock_anthropic):
        """Test handling of timeout."""
        import requests

        from cyclisme_training_logs.ai_providers.claude_api import WorkflowError

        mock_anthropic.messages.create.side_effect = requests.Timeout("Request timeout")

        analyzer = ClaudeAPIAnalyzer(api_key=valid_api_key)

        with pytest.raises(WorkflowError) as exc_info:
            analyzer.analyze_session("Test")

        assert "timeout" in str(exc_info.value).lower()

    def test_analyze_connection_error(self, valid_api_key, mock_anthropic):
        """Test handling of connection error."""
        import requests

        from cyclisme_training_logs.ai_providers.claude_api import WorkflowError

        mock_anthropic.messages.create.side_effect = requests.ConnectionError("Cannot connect")

        analyzer = ClaudeAPIAnalyzer(api_key=valid_api_key)

        with pytest.raises(WorkflowError) as exc_info:
            analyzer.analyze_session("Test")

        assert "connect" in str(exc_info.value).lower()

    # === Provider Info Tests ===

    def test_get_provider_info(self, valid_api_key):
        """Test get_provider_info returns correct information."""
        analyzer = ClaudeAPIAnalyzer(api_key=valid_api_key, model="claude-3-opus")

        info = analyzer.get_provider_info()

        assert info["provider"] == "claude_api"
        assert info["model"] == "claude-3-opus"
        assert info["requires_api_key"] is True

    def test_get_provider_info_structure(self, valid_api_key):
        """Test provider info has expected structure."""
        analyzer = ClaudeAPIAnalyzer(api_key=valid_api_key)

        info = analyzer.get_provider_info()

        assert isinstance(info, dict)
        assert "provider" in info
        assert "model" in info
        assert "status" in info or "requires_api_key" in info

    def test_validate_config_success(self, valid_api_key):
        """Test config validation returns True with valid config."""
        analyzer = ClaudeAPIAnalyzer(api_key=valid_api_key)

        is_valid = analyzer.validate_config()

        assert is_valid is True

    # === Edge Cases ===

    def test_multiple_analyzers_independent(self, valid_api_key):
        """Test multiple analyzer instances are independent."""
        analyzer1 = ClaudeAPIAnalyzer(api_key=valid_api_key, model="claude-3-opus")
        analyzer2 = ClaudeAPIAnalyzer(api_key=valid_api_key, model="claude-3-sonnet")

        assert analyzer1 is not analyzer2
        assert analyzer1.model != analyzer2.model

    def test_model_parameter_preserved(self, valid_api_key):
        """Test that model parameter is preserved."""
        custom_model = "claude-3-haiku"
        analyzer = ClaudeAPIAnalyzer(api_key=valid_api_key, model=custom_model)

        assert analyzer.model == custom_model

    def test_client_initialized(self, valid_api_key):
        """Test that Anthropic client is properly initialized."""
        analyzer = ClaudeAPIAnalyzer(api_key=valid_api_key)

        assert hasattr(analyzer, "client")
        assert analyzer.client is not None
        assert analyzer.validate_config() is True

    def test_max_tokens_default(self, valid_api_key):
        """Test default max_tokens value."""
        analyzer = ClaudeAPIAnalyzer(api_key=valid_api_key)

        assert hasattr(analyzer, "max_tokens")
        assert analyzer.max_tokens == 4000

    def test_provider_enum_value(self, valid_api_key):
        """Test provider enum is correctly set."""
        analyzer = ClaudeAPIAnalyzer(api_key=valid_api_key)

        assert analyzer.provider == AIProvider.CLAUDE
        assert analyzer.provider.value == "claude_api"
