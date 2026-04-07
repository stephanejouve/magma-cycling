"""
Tests for WithingsConfig - Black-box testing approach.

Tests configuration loading and validation without knowledge of
internal implementation details.
"""

import json
import time
from unittest.mock import patch

import pytest

from magma_cycling.config import (
    create_withings_client,
    get_withings_config,
    reset_withings_config,
)


class TestWithingsConfigInitialization:
    """Test WithingsConfig initialization and environment variable loading."""

    def test_config_with_all_env_vars(self, monkeypatch, tmp_path):
        """Configuration should load all environment variables."""
        monkeypatch.setenv("WITHINGS_CLIENT_ID", "test_client_id_123")
        monkeypatch.setenv("WITHINGS_CLIENT_SECRET", "test_secret_456")
        monkeypatch.setenv("WITHINGS_REDIRECT_URI", "http://custom:9000/callback")

        # Mock data config to use temp path
        with patch("magma_cycling.config.data_repo.get_data_config") as mock_data:
            mock_data.return_value.data_repo_path = tmp_path
            reset_withings_config()  # Clear singleton
            config = get_withings_config()

            assert config.client_id == "test_client_id_123"
            assert config.client_secret == "test_secret_456"
            assert config.redirect_uri == "http://custom:9000/callback"

    def test_config_with_default_redirect_uri(self, monkeypatch, tmp_path):
        """Configuration should use default redirect URI when not provided."""
        monkeypatch.setenv("WITHINGS_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("WITHINGS_CLIENT_SECRET", "test_secret")
        monkeypatch.delenv("WITHINGS_REDIRECT_URI", raising=False)

        with patch("magma_cycling.config.data_repo.get_data_config") as mock_data:
            mock_data.return_value.data_repo_path = tmp_path
            reset_withings_config()
            config = get_withings_config()

            assert config.redirect_uri == "http://localhost:8080/callback"

    def test_config_without_env_vars(self, monkeypatch, tmp_path):
        """Configuration should handle missing environment variables."""
        monkeypatch.delenv("WITHINGS_CLIENT_ID", raising=False)
        monkeypatch.delenv("WITHINGS_CLIENT_SECRET", raising=False)

        with patch("magma_cycling.config.data_repo.get_data_config") as mock_data:
            mock_data.return_value.data_repo_path = tmp_path
            reset_withings_config()
            config = get_withings_config()

            assert config.client_id is None
            assert config.client_secret is None

    def test_credentials_path_uses_data_repo(self, monkeypatch, tmp_path):
        """Credentials path should be in data repository."""
        monkeypatch.setenv("WITHINGS_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("WITHINGS_CLIENT_SECRET", "test_secret")
        monkeypatch.delenv("WITHINGS_CREDENTIALS_PATH", raising=False)

        with patch("magma_cycling.config.data_repo.get_data_config") as mock_data:
            mock_data.return_value.data_repo_path = tmp_path
            reset_withings_config()
            config = get_withings_config()

            expected_path = tmp_path / ".withings_credentials.json"
            assert config.credentials_path == expected_path

    def test_credentials_path_from_env_var(self, monkeypatch):
        """WITHINGS_CREDENTIALS_PATH should override default credentials path."""
        from pathlib import Path

        monkeypatch.setenv("WITHINGS_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("WITHINGS_CLIENT_SECRET", "test_secret")
        monkeypatch.setenv("WITHINGS_CREDENTIALS_PATH", "/data/credentials/withings.json")

        reset_withings_config()
        config = get_withings_config()

        assert config.credentials_path == Path("/data/credentials/withings.json")


class TestWithingsConfigValidation:
    """Test configuration validation methods."""

    def test_is_configured_with_credentials(self, monkeypatch, tmp_path):
        """Configuration should be configured when credentials are set."""
        monkeypatch.setenv("WITHINGS_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("WITHINGS_CLIENT_SECRET", "test_secret")

        with patch("magma_cycling.config.data_repo.get_data_config") as mock_data:
            mock_data.return_value.data_repo_path = tmp_path
            reset_withings_config()
            config = get_withings_config()

            assert config.is_configured() is True

    def test_is_configured_without_client_id(self, monkeypatch, tmp_path):
        """Configuration should not be configured without client ID."""
        monkeypatch.delenv("WITHINGS_CLIENT_ID", raising=False)
        monkeypatch.setenv("WITHINGS_CLIENT_SECRET", "test_secret")

        with patch("magma_cycling.config.data_repo.get_data_config") as mock_data:
            mock_data.return_value.data_repo_path = tmp_path
            reset_withings_config()
            config = get_withings_config()

            assert config.is_configured() is False

    def test_is_configured_without_client_secret(self, monkeypatch, tmp_path):
        """Configuration should not be configured without client secret."""
        monkeypatch.setenv("WITHINGS_CLIENT_ID", "test_client_id")
        monkeypatch.delenv("WITHINGS_CLIENT_SECRET", raising=False)

        with patch("magma_cycling.config.data_repo.get_data_config") as mock_data:
            mock_data.return_value.data_repo_path = tmp_path
            reset_withings_config()
            config = get_withings_config()

            assert config.is_configured() is False

    def test_has_valid_credentials_file_not_exists(self, monkeypatch, tmp_path):
        """Should return False when credentials file doesn't exist."""
        monkeypatch.setenv("WITHINGS_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("WITHINGS_CLIENT_SECRET", "test_secret")

        with patch("magma_cycling.config.data_repo.get_data_config") as mock_data:
            mock_data.return_value.data_repo_path = tmp_path
            reset_withings_config()
            config = get_withings_config()

            assert config.has_valid_credentials() is False

    def test_has_valid_credentials_with_valid_file(self, monkeypatch, tmp_path):
        """Should return True when credentials file is valid and not expired."""
        monkeypatch.setenv("WITHINGS_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("WITHINGS_CLIENT_SECRET", "test_secret")

        # Create valid credentials file
        creds_file = tmp_path / ".withings_credentials.json"
        creds_data = {
            "access_token": "test_token",
            "refresh_token": "test_refresh",
            "token_expiry": int(time.time()) + 7200,  # Valid for 2 hours
            "user_id": "12345",
        }
        with open(creds_file, "w") as f:
            json.dump(creds_data, f)

        with patch("magma_cycling.config.data_repo.get_data_config") as mock_data:
            mock_data.return_value.data_repo_path = tmp_path
            reset_withings_config()
            config = get_withings_config()

            assert config.has_valid_credentials() is True

    def test_has_valid_credentials_with_expired_token_but_refresh(self, monkeypatch, tmp_path):
        """Should return True when access token expired but refresh_token exists."""
        monkeypatch.setenv("WITHINGS_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("WITHINGS_CLIENT_SECRET", "test_secret")

        # Create expired credentials file (refresh_token present → still valid)
        creds_file = tmp_path / ".withings_credentials.json"
        creds_data = {
            "access_token": "expired_token",
            "refresh_token": "test_refresh",
            "token_expiry": int(time.time()) - 3600,  # Expired 1 hour ago
            "user_id": "12345",
        }
        with open(creds_file, "w") as f:
            json.dump(creds_data, f)

        with patch("magma_cycling.config.data_repo.get_data_config") as mock_data:
            mock_data.return_value.data_repo_path = tmp_path
            reset_withings_config()
            config = get_withings_config()

            assert config.has_valid_credentials() is True

    def test_has_valid_credentials_missing_fields(self, monkeypatch, tmp_path):
        """Should return False when credentials file is missing required fields."""
        monkeypatch.setenv("WITHINGS_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("WITHINGS_CLIENT_SECRET", "test_secret")

        # Create incomplete credentials file
        creds_file = tmp_path / ".withings_credentials.json"
        creds_data = {
            "access_token": "test_token",
            # Missing refresh_token and token_expiry
        }
        with open(creds_file, "w") as f:
            json.dump(creds_data, f)

        with patch("magma_cycling.config.data_repo.get_data_config") as mock_data:
            mock_data.return_value.data_repo_path = tmp_path
            reset_withings_config()
            config = get_withings_config()

            assert config.has_valid_credentials() is False

    def test_has_valid_credentials_invalid_json(self, monkeypatch, tmp_path):
        """Should return False when credentials file contains invalid JSON."""
        monkeypatch.setenv("WITHINGS_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("WITHINGS_CLIENT_SECRET", "test_secret")

        # Create file with invalid JSON
        creds_file = tmp_path / ".withings_credentials.json"
        with open(creds_file, "w") as f:
            f.write("invalid json content {")

        with patch("magma_cycling.config.data_repo.get_data_config") as mock_data:
            mock_data.return_value.data_repo_path = tmp_path
            reset_withings_config()
            config = get_withings_config()

            assert config.has_valid_credentials() is False


class TestWithingsClientFactory:
    """Test create_withings_client factory function."""

    def test_create_client_with_valid_config(self, monkeypatch, tmp_path):
        """Factory should create client when configuration is valid."""
        monkeypatch.setenv("WITHINGS_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("WITHINGS_CLIENT_SECRET", "test_secret")

        with patch("magma_cycling.config.data_repo.get_data_config") as mock_data:
            mock_data.return_value.data_repo_path = tmp_path
            reset_withings_config()

            client = create_withings_client()

            assert client is not None
            assert client.client_id == "test_client_id"
            assert client.client_secret == "test_secret"

    def test_create_client_without_config_raises_error(self, monkeypatch, tmp_path):
        """Factory should raise error when configuration is missing."""
        monkeypatch.delenv("WITHINGS_CLIENT_ID", raising=False)
        monkeypatch.delenv("WITHINGS_CLIENT_SECRET", raising=False)

        with patch("magma_cycling.config.data_repo.get_data_config") as mock_data:
            mock_data.return_value.data_repo_path = tmp_path
            reset_withings_config()

            with pytest.raises(ValueError, match="Withings API not configured.*WITHINGS_CLIENT_ID"):
                create_withings_client()

    def test_create_client_uses_custom_redirect_uri(self, monkeypatch, tmp_path):
        """Factory should use custom redirect URI from environment."""
        monkeypatch.setenv("WITHINGS_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("WITHINGS_CLIENT_SECRET", "test_secret")
        monkeypatch.setenv("WITHINGS_REDIRECT_URI", "http://custom:8000/auth")

        with patch("magma_cycling.config.data_repo.get_data_config") as mock_data:
            mock_data.return_value.data_repo_path = tmp_path
            reset_withings_config()

            client = create_withings_client()

            assert client.redirect_uri == "http://custom:8000/auth"


class TestConfigSingleton:
    """Test singleton behavior of config."""

    def test_get_withings_config_returns_same_instance(self, monkeypatch, tmp_path):
        """get_withings_config should return same instance on multiple calls."""
        monkeypatch.setenv("WITHINGS_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("WITHINGS_CLIENT_SECRET", "test_secret")

        with patch("magma_cycling.config.data_repo.get_data_config") as mock_data:
            mock_data.return_value.data_repo_path = tmp_path
            reset_withings_config()

            config1 = get_withings_config()
            config2 = get_withings_config()

            assert config1 is config2

    def test_reset_withings_config_clears_singleton(self, monkeypatch, tmp_path):
        """reset_withings_config should clear singleton instance."""
        monkeypatch.setenv("WITHINGS_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("WITHINGS_CLIENT_SECRET", "test_secret")

        with patch("magma_cycling.config.data_repo.get_data_config") as mock_data:
            mock_data.return_value.data_repo_path = tmp_path
            reset_withings_config()

            config1 = get_withings_config()
            reset_withings_config()
            config2 = get_withings_config()

            assert config1 is not config2
