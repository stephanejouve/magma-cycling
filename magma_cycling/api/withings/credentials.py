"""Credentials management mixin for WithingsClient."""

import json
import logging
import time
from pathlib import Path

import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


class CredentialsMixin:
    """OAuth credentials persistence and token refresh."""

    def load_credentials(self, credentials_path: Path | None = None) -> bool:
        """Load stored credentials from JSON file.

        Args:
            credentials_path: Path to credentials file (uses self.credentials_path if None)

        Returns:
            True if credentials loaded successfully, False otherwise

        Example:
            >>> client = WithingsClient(...)
            >>> if client.load_credentials(Path("~/.withings_credentials.json")):
            ...     print("Authenticated")
        """
        path = credentials_path or self.credentials_path

        if not path or not path.exists():
            logger.warning(f"Credentials file not found: {path}")
            return False

        try:
            with open(path, "r") as f:
                creds = json.load(f)

            self.access_token = creds.get("access_token")
            self.refresh_token = creds.get("refresh_token")
            self.token_expiry = creds.get("token_expiry")
            self.user_id = creds.get("user_id")

            logger.info(f"Loaded credentials for user {self.user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return False

    def save_credentials(self) -> None:
        """Save current credentials to JSON file.

        Credentials are saved to self.credentials_path with permissions 600
        (owner read/write only) for security.

        Raises:
            ValueError: If credentials_path is not set
        """
        if not self.credentials_path:
            raise ValueError("credentials_path not set, cannot save credentials")

        creds = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_expiry": self.token_expiry,
            "user_id": self.user_id,
        }

        # Ensure parent directory exists
        self.credentials_path.parent.mkdir(parents=True, exist_ok=True)

        # Write credentials
        with open(self.credentials_path, "w") as f:
            json.dump(creds, f, indent=2)

        # Set file permissions to 600 (owner read/write only)
        self.credentials_path.chmod(0o600)

        logger.info(f"Saved credentials to {self.credentials_path}")

    def refresh_access_token(self) -> None:
        """Refresh expired access token using refresh token.

        This is called automatically by _ensure_authenticated() when the
        token is close to expiry. Can also be called manually.

        Raises:
            RequestException: If token refresh fails
        """
        if not self.refresh_token:
            raise ValueError("No refresh token available")

        payload = {
            "action": "requesttoken",
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
        }

        logger.info("Refreshing access token")
        response = requests.post(self.TOKEN_URL, data=payload)

        if response.status_code != 200:
            logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
            raise RequestException(f"Failed to refresh token: {response.status_code}")

        data = response.json()

        if data.get("status") != 0:
            error_msg = data.get("error", "Unknown error")
            logger.error(f"Withings API error during refresh: {error_msg}")
            raise RequestException(f"Withings API error: {error_msg}")

        body = data.get("body", {})

        # Update tokens
        self.access_token = body.get("access_token")
        self.refresh_token = body.get("refresh_token")

        # Calculate new expiry
        expires_in = body.get("expires_in", 3600)
        self.token_expiry = int(time.time()) + expires_in

        logger.info("Successfully refreshed access token")

        # Save updated credentials
        if self.credentials_path:
            self.save_credentials()

    def is_authenticated(self) -> bool:
        """Check if client has valid authentication.

        Returns:
            True if authenticated with non-expired token, False otherwise
        """
        if not self.access_token or not self.token_expiry:
            return False

        # Check if token is expired or expiring soon (within 5 minutes)
        return self.token_expiry > (time.time() + 300)

    def _ensure_authenticated(self) -> None:
        """Ensure token is valid, refresh if needed.

        Called before every API request to ensure authentication is valid.

        Raises:
            ValueError: If not authenticated and cannot refresh
        """
        if not self.access_token:
            raise ValueError("Not authenticated. Call exchange_code() first.")

        # Refresh if token expires within 5 minutes
        if self.token_expiry and self.token_expiry <= (time.time() + 300):
            logger.info("Token expiring soon, refreshing")
            self.refresh_access_token()
