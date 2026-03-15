"""Withings API configuration.

Manages OAuth credentials and API settings for Withings health data integration.
"""

import json
import os


class WithingsConfig:
    """Configuration for Withings API.

    Attributes:
        client_id: Withings OAuth client ID
        client_secret: Withings OAuth client secret
        redirect_uri: OAuth callback URI
        credentials_path: Path to stored OAuth credentials JSON

    Examples:
        >>> config = get_withings_config()
        >>> print(config.is_configured())
        True
        >>> if config.has_valid_credentials():
        ...     pass
    """

    def __init__(self):
        """Initialize Withings configuration from environment variables."""
        from magma_cycling.config.data_repo import get_data_config

        self.client_id = os.getenv("WITHINGS_CLIENT_ID")
        self.client_secret = os.getenv("WITHINGS_CLIENT_SECRET")
        self.redirect_uri = os.getenv("WITHINGS_REDIRECT_URI", "http://localhost:8080/callback")

        data_config = get_data_config()
        self.credentials_path = data_config.data_repo_path / ".withings_credentials.json"

    def is_configured(self) -> bool:
        """Check if Withings API credentials are properly configured.

        Returns:
            True if both client_id and client_secret are set

        Examples:
            >>> config = get_withings_config()
            >>> if config.is_configured():
            ...     pass
            ... else:
            ...     print("Set WITHINGS_CLIENT_ID and WITHINGS_CLIENT_SECRET")
        """
        return bool(self.client_id and self.client_secret)

    def has_valid_credentials(self) -> bool:
        """Check if stored OAuth credentials exist and are valid.

        Returns:
            True if credentials file exists and tokens are not expired

        Examples:
            >>> config = get_withings_config()
            >>> if not config.has_valid_credentials():
            ...     print("Run setup_withings.py to authenticate")
        """
        if not self.credentials_path.exists():
            return False

        try:
            with open(self.credentials_path, encoding="utf-8") as f:
                creds = json.load(f)

            if not all(k in creds for k in ["access_token", "refresh_token", "token_expiry"]):
                return False

            return True

        except Exception:
            return False


# Global Withings config instance
_withings_config_instance: WithingsConfig | None = None


def get_withings_config() -> WithingsConfig:
    """Get singleton instance of Withings config.

    Returns:
        WithingsConfig instance

    Examples:
        >>> config = get_withings_config()
        >>> print(config.client_id)
        'your_withings_client_id_here'
    """
    global _withings_config_instance

    if _withings_config_instance is None:
        _withings_config_instance = WithingsConfig()
    return _withings_config_instance


def reset_withings_config():
    """Reset Withings config singleton (useful for tests).

    Examples:
        >>> reset_withings_config()
        >>> config = get_withings_config()  # Creates new instance
    """
    global _withings_config_instance
    _withings_config_instance = None


def create_withings_client():
    """Factory function for creating configured WithingsClient.

    Returns:
        WithingsClient: Configured client ready to use

    Raises:
        ValueError: If Withings credentials are not configured

    Examples:
        >>> from magma_cycling.config import create_withings_client
        >>> client = create_withings_client()
        >>> if client.is_authenticated():
        ...     sleep = client.get_last_night_sleep()
    """
    from magma_cycling.api.withings_client import WithingsClient

    config = get_withings_config()

    if not config.is_configured():
        raise ValueError(
            "Withings API not configured. "
            "Set WITHINGS_CLIENT_ID and WITHINGS_CLIENT_SECRET environment variables."
        )

    return WithingsClient(
        client_id=config.client_id,
        client_secret=config.client_secret,
        redirect_uri=config.redirect_uri,
        credentials_path=config.credentials_path,
    )


def create_health_provider():
    """Factory function for creating a configured HealthProvider.

    Delegates to magma_cycling.health.factory. Returns NullProvider if
    Withings is not configured or on any error.

    Returns:
        HealthProvider: Configured provider ready to use
    """
    from magma_cycling.health.factory import create_health_provider as _factory

    return _factory()
