"""Intervals.icu API configuration.

Manages athlete ID and API key for Intervals.icu integration.
"""

import os


class IntervalsConfig:
    """Configuration for Intervals.icu API.

    Attributes:
        athlete_id: Intervals.icu athlete ID (format: i123456)
        api_key: Intervals.icu API key
        base_url: API base URL (default: https://intervals.icu/api/v1)

    Examples:
        >>> config = get_intervals_config()
        >>> print(config.athlete_id)
        'iXXXXXX'
        >>> print(config.is_configured())
        True.
    """

    def __init__(self):
        """Initialize Intervals.icu configuration from environment variables."""
        self.athlete_id = os.getenv("VITE_INTERVALS_ATHLETE_ID")
        self.api_key = os.getenv("VITE_INTERVALS_API_KEY")
        self.base_url = os.getenv("VITE_INTERVALS_BASE_URL", "https://intervals.icu/api/v1")

    def is_configured(self) -> bool:
        """Check if Intervals.icu API is properly configured.

        Returns:
            True if both athlete_id and api_key are set

        Examples:
            >>> config = get_intervals_config()
            >>> if config.is_configured():
            ...     pass
            ... else:
            ...     pass.
        """
        return bool(self.athlete_id and self.api_key)

    def get_headers(self) -> dict:
        """Get authentication headers for Intervals.icu API.

        Returns:
            Dict with Authorization header using Basic auth

        Examples:
            >>> config = get_intervals_config()
            >>> headers = config.get_headers()
            >>> import requests
            >>> response = requests.get(url, headers=headers).
        """
        if not self.is_configured():
            raise ValueError("Intervals.icu API not configured")

        import base64

        auth_string = f"API_KEY:{self.api_key}"
        auth_bytes = auth_string.encode("ascii")
        base64_bytes = base64.b64encode(auth_bytes)
        base64_string = base64_bytes.decode("ascii")

        return {"Authorization": f"Basic {base64_string}", "Content-Type": "application/json"}


# Global Intervals config instance
_intervals_config_instance: IntervalsConfig | None = None


def get_intervals_config() -> IntervalsConfig:
    """Get singleton instance of Intervals.icu config.

    Returns:
        IntervalsConfig instance

    Examples:
        >>> config = get_intervals_config()
        >>> print(config.athlete_id)
        'iXXXXXX'.
    """
    global _intervals_config_instance

    if _intervals_config_instance is None:
        _intervals_config_instance = IntervalsConfig()
    return _intervals_config_instance


def reset_intervals_config():
    """Reset Intervals config singleton (useful for tests).

    Examples:
        >>> reset_intervals_config()
        >>> config = get_intervals_config()  # Creates new instance.
    """
    global _intervals_config_instance
    _intervals_config_instance = None


def create_intervals_client():
    """Factory function for creating configured IntervalsClient.

    Returns:
        IntervalsClient: Configured client ready to use

    Raises:
        ValueError: If Intervals.icu credentials are not configured

    Examples:
        >>> from magma_cycling.config import create_intervals_client
        >>> client = create_intervals_client()
        >>> activities = client.get_activities(oldest="2026-01-01", newest="2026-01-15")
    """
    from magma_cycling.api.intervals_client import IntervalsClient

    config = get_intervals_config()

    if not config.is_configured():
        raise ValueError(
            "Intervals.icu API not configured. "
            "Set VITE_INTERVALS_ATHLETE_ID and VITE_INTERVALS_API_KEY environment variables."
        )

    return IntervalsClient(athlete_id=config.athlete_id, api_key=config.api_key)
