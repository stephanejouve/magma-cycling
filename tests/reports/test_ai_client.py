"""Tests for AI client.

Sprint R10 MVP Day 2 - Tests for AI client abstraction.

Author: Claude Code
Created: 2026-01-18
"""

from unittest.mock import Mock, patch

import pytest

from cyclisme_training_logs.reports.ai_client import (
    AIClientError,
    ClaudeClient,
    OpenAIClient,
    create_ai_client,
)


class TestClaudeClient:
    """Tests for ClaudeClient."""

    @patch("anthropic.Anthropic")
    def test_init_with_api_key(self, mock_anthropic):
        """Test ClaudeClient initialization with API key."""
        # Given: API key provided
        api_key = "test_api_key"
        mock_anthropic.return_value = Mock()

        # When: Creating client
        client = ClaudeClient(api_key=api_key)

        # Then: Client should be initialized
        assert client.api_key == api_key
        assert client.model == ClaudeClient.DEFAULT_MODEL
        assert client.max_retries == 3

    @patch("anthropic.Anthropic")
    @patch.dict("os.environ", {}, clear=True)
    def test_init_without_api_key(self, mock_anthropic):
        """Test ClaudeClient initialization without API key."""
        # Given: No API key
        # When: Creating client
        client = ClaudeClient()

        # Then: Should initialize but not be configured
        assert client.api_key is None
        assert not client.is_configured()

    @patch("anthropic.Anthropic")
    def test_is_configured_with_api_key(self, mock_anthropic):
        """Test is_configured returns True with API key."""
        # Given: Client with API key
        mock_anthropic.return_value = Mock()
        client = ClaudeClient(api_key="test_key")

        # When/Then: Should be configured
        assert client.is_configured() is True

    @patch("anthropic.Anthropic")
    @patch.dict("os.environ", {}, clear=True)
    def test_is_configured_without_api_key(self, mock_anthropic):
        """Test is_configured returns False without API key."""
        # Given: Client without API key
        client = ClaudeClient()

        # When/Then: Should not be configured
        assert client.is_configured() is False

    @patch("anthropic.Anthropic")
    def test_generate_success(self, mock_anthropic):
        """Test successful text generation."""
        # Given: Configured client with mocked API
        mock_client = Mock()
        mock_anthropic.return_value = mock_client

        # Mock response
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "Generated report content"
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        client = ClaudeClient(api_key="test_key")

        # When: Generating text
        result = client.generate("Test prompt", max_tokens=1000)

        # Then: Should return generated text
        assert result == "Generated report content"
        mock_client.messages.create.assert_called_once()

    @patch("anthropic.Anthropic")
    @patch.dict("os.environ", {}, clear=True)
    def test_generate_not_configured(self, mock_anthropic):
        """Test generate raises error when not configured."""
        # Given: Unconfigured client
        client = ClaudeClient()

        # When/Then: Generate should raise AIClientError
        with pytest.raises(AIClientError, match="not configured"):
            client.generate("Test prompt")

    @patch("anthropic.Anthropic")
    @patch("time.sleep")
    def test_generate_with_retry_on_rate_limit(self, mock_sleep, mock_anthropic):
        """Test generate retries on rate limit error."""
        # Given: Client that fails once with rate limit then succeeds
        mock_client = Mock()
        mock_anthropic.return_value = mock_client

        # First call fails with rate limit, second succeeds
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "Success after retry"
        mock_response.content = [mock_content]

        mock_client.messages.create.side_effect = [
            Exception("rate_limit error 429"),
            mock_response,
        ]

        client = ClaudeClient(api_key="test_key", max_retries=3)

        # When: Generating
        result = client.generate("Test prompt")

        # Then: Should succeed after retry
        assert result == "Success after retry"
        assert mock_client.messages.create.call_count == 2
        mock_sleep.assert_called()  # Should have slept for backoff


class TestOpenAIClient:
    """Tests for OpenAIClient (stub)."""

    def test_init(self):
        """Test OpenAIClient initialization."""
        # When: Creating client
        client = OpenAIClient(api_key="test_key")

        # Then: Should initialize with API key
        assert client.api_key == "test_key"
        assert client.model == "gpt-4-turbo"

    def test_is_configured(self):
        """Test is_configured with API key."""
        # Given: Client with API key
        client = OpenAIClient(api_key="test_key")

        # When/Then: Should be configured
        assert client.is_configured() is True

    def test_generate_not_implemented(self):
        """Test generate raises NotImplementedError."""
        # Given: OpenAI client
        client = OpenAIClient(api_key="test_key")

        # When/Then: Generate should raise NotImplementedError
        with pytest.raises(NotImplementedError, match="not yet implemented"):
            client.generate("Test prompt")


class TestCreateAIClient:
    """Tests for create_ai_client factory function."""

    @patch("anthropic.Anthropic")
    def test_create_claude_client(self, mock_anthropic):
        """Test creating Claude client."""
        # When: Creating Claude client
        mock_anthropic.return_value = Mock()
        client = create_ai_client("claude", api_key="test_key")

        # Then: Should return ClaudeClient instance
        assert isinstance(client, ClaudeClient)

    def test_create_openai_client(self):
        """Test creating OpenAI client."""
        # When: Creating OpenAI client
        client = create_ai_client("openai", api_key="test_key")

        # Then: Should return OpenAIClient instance
        assert isinstance(client, OpenAIClient)

    def test_create_unknown_provider(self):
        """Test creating client with unknown provider."""
        # When/Then: Should raise ValueError
        with pytest.raises(ValueError, match="Unknown AI provider"):
            create_ai_client("unknown_provider")
