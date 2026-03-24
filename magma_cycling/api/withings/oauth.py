"""OAuth flow mixin for WithingsClient."""

import logging
import time

import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


class OAuthMixin:
    """OAuth 2.0 authorization and code exchange."""

    def get_authorization_url(self, state: str | None = None) -> str:
        """Generate OAuth authorization URL for user consent.

        The user should visit this URL in a browser, authorize the application,
        and will be redirected to redirect_uri with an authorization code.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to visit in browser

        Example:
            >>> client = WithingsClient(client_id="...", client_secret="...")
            >>> url = client.get_authorization_url()
            >>> print(f"Visit: {url}")
        """
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "user.metrics,user.activity,user.sleepevents",
        }
        if state:
            params["state"] = state

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        auth_url = f"{self.AUTH_URL}?{query_string}"

        logger.info("Generated authorization URL")
        return auth_url

    def exchange_code(self, authorization_code: str) -> dict:
        """Exchange authorization code for access/refresh tokens.

        After user authorizes and you receive the authorization code from the
        callback, use this method to exchange it for access tokens.

        Args:
            authorization_code: Authorization code from OAuth callback

        Returns:
            Dictionary with token information

        Raises:
            RequestException: If token exchange fails

        Example:
            >>> client.exchange_code("authorization_code_from_callback")
            >>> # Credentials are now saved and client is authenticated
        """
        payload = {
            "action": "requesttoken",
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": authorization_code,
            "redirect_uri": self.redirect_uri,
        }

        logger.info("Exchanging authorization code for tokens")
        response = requests.post(self.TOKEN_URL, data=payload)

        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
            raise RequestException(f"Failed to exchange authorization code: {response.status_code}")

        data = response.json()

        if data.get("status") != 0:
            error_msg = data.get("error", "Unknown error")
            logger.error(f"Withings API error: {error_msg}")
            raise RequestException(f"Withings API error: {error_msg}")

        body = data.get("body", {})

        # Store tokens
        self.access_token = body.get("access_token")
        self.refresh_token = body.get("refresh_token")
        self.user_id = str(body.get("userid"))

        # Calculate token expiry (expires_in is in seconds)
        expires_in = body.get("expires_in", 3600)
        self.token_expiry = int(time.time()) + expires_in

        logger.info(f"Successfully authenticated user {self.user_id}")

        # Save credentials
        if self.credentials_path:
            self.save_credentials()

        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_expiry": self.token_expiry,
            "user_id": self.user_id,
        }
