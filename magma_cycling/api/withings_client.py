"""Withings API client for health data integration.

This module provides OAuth 2.0 authenticated access to Withings health data
including sleep metrics, weight measurements, and heart rate data. Follows
the same architectural pattern as IntervalsClient for consistency.

Example:
    >>> from magma_cycling.config import create_withings_client
    >>> client = create_withings_client()
    >>> if not client.is_authenticated():
    ...     # First time setup
    ...     auth_url = client.get_authorization_url()
    ...     print(f"Visit: {auth_url}")
    ...     code = input("Enter authorization code: ")
    ...     client.exchange_code(code)
    >>> # Now authenticated
    >>> sleep = client.get_last_night_sleep()
    >>> weight = client.get_latest_weight()
"""

import logging
from pathlib import Path

from magma_cycling.api.withings.credentials import CredentialsMixin
from magma_cycling.api.withings.http import HttpMixin
from magma_cycling.api.withings.measurements import MeasurementsMixin
from magma_cycling.api.withings.oauth import OAuthMixin
from magma_cycling.api.withings.sleep import SleepMixin

logger = logging.getLogger(__name__)


class WithingsClient(
    OAuthMixin,
    CredentialsMixin,
    HttpMixin,
    SleepMixin,
    MeasurementsMixin,
):
    """Client for Withings API with OAuth 2.0 authentication.

    This client handles OAuth authentication, token management, and provides
    methods to retrieve health data from Withings API. Tokens are automatically
    refreshed before expiration.

    Attributes:
        client_id: Withings OAuth client ID
        client_secret: Withings OAuth client secret
        redirect_uri: OAuth callback URI
        credentials_path: Path to stored credentials JSON
        access_token: Current OAuth access token (None if not authenticated)
        refresh_token: OAuth refresh token for token renewal
        token_expiry: Token expiration timestamp
        user_id: Withings user ID
    """

    BASE_URL = "https://wbsapi.withings.net"
    AUTH_URL = "https://account.withings.com/oauth2_user/authorize2"
    TOKEN_URL = "https://wbsapi.withings.net/v2/oauth2"
    REDIRECT_URI_DEFAULT = "http://localhost:8080/callback"

    # API rate limit: 120 requests per minute
    MAX_REQUESTS_PER_MINUTE = 120
    _request_timestamps: list[float] = []

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str | None = None,
        credentials_path: Path | None = None,
    ):
        """Initialize Withings client with OAuth credentials.

        Args:
            client_id: Withings OAuth client ID
            client_secret: Withings OAuth client secret
            redirect_uri: OAuth callback URI (default: http://localhost:8080/callback)
            credentials_path: Path to stored credentials JSON (optional)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri or self.REDIRECT_URI_DEFAULT
        self.credentials_path = credentials_path

        # OAuth tokens (loaded from file or set via exchange_code)
        self.access_token: str | None = None
        self.refresh_token: str | None = None
        self.token_expiry: int | None = None  # Unix timestamp
        self.user_id: str | None = None

        # Try to load existing credentials
        if self.credentials_path and self.credentials_path.exists():
            self.load_credentials()
