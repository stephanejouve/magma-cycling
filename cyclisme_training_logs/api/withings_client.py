"""Withings API client for health data integration.

This module provides OAuth 2.0 authenticated access to Withings health data
including sleep metrics, weight measurements, and heart rate data. Follows
the same architectural pattern as IntervalsClient for consistency.

Example:
    >>> from cyclisme_training_logs.config import create_withings_client
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

import json
import logging
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


class WithingsClient:
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

    def exchange_code(self, authorization_code: str) -> dict[str, Any]:
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

    def _check_rate_limit(self) -> None:
        """Check and enforce API rate limiting (120 req/min).

        Sleeps if necessary to avoid exceeding rate limit.
        """
        now = time.time()

        # Remove timestamps older than 1 minute
        self._request_timestamps = [ts for ts in self._request_timestamps if now - ts < 60]

        if len(self._request_timestamps) >= self.MAX_REQUESTS_PER_MINUTE:
            # Calculate how long to sleep
            oldest = self._request_timestamps[0]
            sleep_time = 60 - (now - oldest) + 0.1  # Add 100ms buffer
            logger.warning(f"Rate limit reached, sleeping for {sleep_time:.1f}s")
            time.sleep(sleep_time)

            # Clear old timestamps again
            now = time.time()
            self._request_timestamps = [ts for ts in self._request_timestamps if now - ts < 60]

        # Add current request timestamp
        self._request_timestamps.append(now)

    def _make_request(
        self,
        action: str,
        params: dict[str, Any] | None = None,
        retry_count: int = 3,
    ) -> dict[str, Any]:
        """Make authenticated API request with retry logic.

        Args:
            action: Withings API action (e.g., "getmeas", "getsleep")
            params: Additional request parameters
            retry_count: Number of retries on failure (default: 3)

        Returns:
            API response body

        Raises:
            RequestException: If request fails after all retries
        """
        self._ensure_authenticated()
        self._check_rate_limit()

        # Support both full paths (v2/sleep) and short paths (measure)
        url = f"{self.BASE_URL}/{action}"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }

        request_params = params or {}

        for attempt in range(retry_count):
            try:
                response = requests.get(url, headers=headers, params=request_params)

                if response.status_code == 200:
                    data = response.json()

                    if data.get("status") == 0:
                        return data.get("body", {})
                    else:
                        error_msg = data.get("error", "Unknown error")
                        logger.error(f"Withings API error: {error_msg}")
                        raise RequestException(f"Withings API error: {error_msg}")

                elif response.status_code == 401:
                    # Token expired, try to refresh
                    logger.warning("401 Unauthorized, attempting token refresh")
                    self.refresh_access_token()
                    # Retry with new token
                    continue

                else:
                    logger.error(f"API request failed: {response.status_code} - {response.text}")
                    if attempt < retry_count - 1:
                        sleep_time = 2**attempt  # Exponential backoff
                        logger.info(f"Retrying in {sleep_time}s...")
                        time.sleep(sleep_time)
                    else:
                        raise RequestException(f"API request failed: {response.status_code}")

            except RequestException:
                raise
            except Exception as e:
                logger.error(f"Unexpected error during API request: {e}")
                if attempt < retry_count - 1:
                    sleep_time = 2**attempt
                    logger.info(f"Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    raise

        raise RequestException(f"Failed after {retry_count} attempts")

    # === Data Retrieval Methods ===

    def get_sleep(
        self,
        start_date: date,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Get sleep summary data for a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive, default: today)

        Returns:
            List of sleep sessions as dictionaries

        Example:
            >>> from datetime import date, timedelta
            >>> end = date.today()
            >>> start = end - timedelta(days=7)
            >>> sleep_data = client.get_sleep(start, end)
            >>> for session in sleep_data:
            ...     print(f"{session['date']}: {session['total_sleep_hours']}h")
        """
        if end_date is None:
            end_date = date.today()

        params = {
            "action": "getsummary",
            "startdateymd": start_date.strftime("%Y-%m-%d"),
            "enddateymd": end_date.strftime("%Y-%m-%d"),
            "data_fields": ",".join(
                [
                    "sleep_score",
                    "sleep_efficiency",
                    "total_sleep_time",
                    "deepsleepduration",
                    "lightsleepduration",
                    "remsleepduration",
                    "wakeupcount",
                    "wakeupduration",
                    "hr_average",
                    "hr_min",
                    "hr_max",
                    "rr_average",
                    "rr_min",
                    "rr_max",
                    "sleep_latency",
                    "out_of_bed_count",
                    "waso",
                    "nb_rem_episodes",
                ]
            ),
        }

        body = self._make_request("v2/sleep", params)

        sleep_sessions = []
        series = body.get("series", [])

        for session in series:
            # Parse sleep data
            start_ts = session.get("startdate")
            end_ts = session.get("enddate")

            if not start_ts or not end_ts:
                continue

            start_dt = datetime.fromtimestamp(start_ts)
            end_dt = datetime.fromtimestamp(end_ts)

            # Sleep date is the ending date (morning)
            sleep_date = end_dt.date()

            # Calculate total sleep in hours
            total_sleep_seconds = session.get("data", {}).get("total_sleep_time", 0)
            total_sleep_hours = total_sleep_seconds / 3600 if total_sleep_seconds else 0

            # Get sleep stages and metrics
            data = session.get("data", {})
            deep_sleep_sec = data.get("deepsleepduration", 0)
            light_sleep_sec = data.get("lightsleepduration", 0)
            rem_sleep_sec = data.get("remsleepduration", 0)
            wakeup_dur_sec = data.get("wakeupduration", 0)

            sleep_sessions.append(
                {
                    "date": sleep_date.isoformat(),
                    "start_datetime": start_dt.isoformat(),
                    "end_datetime": end_dt.isoformat(),
                    "total_sleep_hours": round(total_sleep_hours, 2),
                    "deep_sleep_minutes": round(deep_sleep_sec / 60, 1) if deep_sleep_sec else None,
                    "light_sleep_minutes": (
                        round(light_sleep_sec / 60, 1) if light_sleep_sec else None
                    ),
                    "rem_sleep_minutes": round(rem_sleep_sec / 60, 1) if rem_sleep_sec else None,
                    "sleep_score": data.get("sleep_score"),
                    "sleep_efficiency": data.get("sleep_efficiency"),
                    "wakeup_count": data.get("wakeupcount", 0),
                    "wakeup_minutes": round(wakeup_dur_sec / 60, 1) if wakeup_dur_sec else None,
                    "hr_average": data.get("hr_average"),
                    "hr_min": data.get("hr_min"),
                    "hr_max": data.get("hr_max"),
                    "rr_average": data.get("rr_average"),
                    "rr_min": data.get("rr_min"),
                    "rr_max": data.get("rr_max"),
                    "sleep_latency_min": (
                        round(data.get("sleep_latency", 0) / 60, 1)
                        if data.get("sleep_latency")
                        else None
                    ),
                    "out_of_bed_count": data.get("out_of_bed_count"),
                    "breathing_disturbances": data.get("breathing_disturbances_intensity"),
                }
            )

        logger.info(f"Retrieved {len(sleep_sessions)} sleep sessions")
        return sleep_sessions

    def get_last_night_sleep(self) -> dict[str, Any] | None:
        """Get last night's sleep data.

        Returns:
            Sleep session dict for last night, or None if not available

        Example:
            >>> sleep = client.get_last_night_sleep()
            >>> if sleep:
            ...     print(f"Slept {sleep['total_sleep_hours']}h")
        """
        # Get sleep from yesterday and today
        today = date.today()
        yesterday = today - timedelta(days=1)

        sessions = self.get_sleep(yesterday, today)

        if not sessions:
            return None

        # Return the most recent session
        return max(sessions, key=lambda s: s["end_datetime"])

    def get_measurements(
        self,
        start_date: date,
        end_date: date | None = None,
        measure_types: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Get weight and body composition measurements.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive, default: today)
            measure_types: List of measurement type IDs (default: [1] for weight)
                          1=Weight, 4=Height, 5=Fat Free Mass, 6=Fat Ratio, 8=Fat Mass Weight,
                          76=Muscle Mass, 77=Hydration, 88=Bone Mass

        Returns:
            List of measurements as dictionaries

        Example:
            >>> measurements = client.get_measurements(
            ...     start_date=date(2026, 2, 1),
            ...     end_date=date(2026, 2, 22),
            ...     measure_types=[1, 6, 8]  # Weight, fat ratio, fat mass
            ... )
        """
        if end_date is None:
            end_date = date.today()

        if measure_types is None:
            measure_types = [1]  # Default to weight only

        startdate = int(datetime.combine(start_date, datetime.min.time()).timestamp())
        enddate = int(datetime.combine(end_date, datetime.max.time()).timestamp())

        params = {
            "action": "getmeas",
            "startdate": startdate,
            "enddate": enddate,
            "meastypes": ",".join(map(str, measure_types)),
        }

        body = self._make_request("measure", params)

        measurements = []
        measuregrps = body.get("measuregrps", [])

        for grp in measuregrps:
            measure_date_ts = grp.get("date")
            if not measure_date_ts:
                continue

            measure_dt = datetime.fromtimestamp(measure_date_ts)
            measure_date_obj = measure_dt.date()

            # Parse measures in this group
            weight_kg = None
            fat_mass_kg = None
            muscle_mass_kg = None
            bone_mass_kg = None

            for measure in grp.get("measures", []):
                measure_type = measure.get("type")
                value = measure.get("value")
                unit = measure.get("unit", 0)

                if value is None:
                    continue

                # Calculate actual value: value * 10^unit
                actual_value = value * (10**unit)

                if measure_type == 1:  # Weight
                    weight_kg = actual_value
                elif measure_type == 8:  # Fat Mass
                    fat_mass_kg = actual_value
                elif measure_type == 76:  # Muscle Mass
                    muscle_mass_kg = actual_value
                elif measure_type == 88:  # Bone Mass
                    bone_mass_kg = actual_value

            if weight_kg is not None:
                measurements.append(
                    {
                        "date": measure_date_obj.isoformat(),
                        "datetime": measure_dt.isoformat(),
                        "weight_kg": round(weight_kg, 2),
                        "fat_mass_kg": round(fat_mass_kg, 2) if fat_mass_kg else None,
                        "muscle_mass_kg": round(muscle_mass_kg, 2) if muscle_mass_kg else None,
                        "bone_mass_kg": round(bone_mass_kg, 2) if bone_mass_kg else None,
                    }
                )

        logger.info(f"Retrieved {len(measurements)} weight measurements")
        return measurements

    def get_latest_weight(self) -> dict[str, Any] | None:
        """Get most recent weight measurement.

        Returns:
            Latest weight measurement dict, or None if not available

        Example:
            >>> weight = client.get_latest_weight()
            >>> if weight:
            ...     print(f"Current weight: {weight['weight_kg']} kg")
        """
        # Get measurements from last 30 days
        end = date.today()
        start = end - timedelta(days=30)

        measurements = self.get_measurements(start, end, measure_types=[1, 6, 8, 76, 88])

        if not measurements:
            return None

        # Return most recent
        return max(measurements, key=lambda m: m["datetime"])

    def evaluate_training_readiness(self, sleep_data: dict[str, Any]) -> dict[str, Any]:
        """Evaluate training readiness based on sleep quality.

        Based on sleep science and training adaptation principles:
        - Minimum 7h sleep for intense training
        - Deep sleep >= 60 min for recovery
        - Sleep score >= 75 for optimal performance

        Args:
            sleep_data: Sleep session dict from get_sleep() or get_last_night_sleep()

        Returns:
            Training readiness evaluation dict

        Example:
            >>> sleep = client.get_last_night_sleep()
            >>> readiness = client.evaluate_training_readiness(sleep)
            >>> print(readiness['recommended_intensity'])
            'all_systems_go'
        """
        sleep_hours = sleep_data.get("total_sleep_hours", 0)
        sleep_score = sleep_data.get("sleep_score")
        deep_sleep_min = sleep_data.get("deep_sleep_minutes", 0) or 0

        veto_reasons = []
        recommendations = []

        # Check sleep duration
        sufficient_duration = sleep_hours >= 7.0
        if not sufficient_duration:
            veto_reasons.append(f"Sommeil insuffisant ({sleep_hours:.1f}h < 7h)")

        # Check deep sleep
        deep_sleep_ok = deep_sleep_min >= 60
        if not deep_sleep_ok and deep_sleep_min > 0:
            veto_reasons.append(f"Sommeil profond insuffisant ({deep_sleep_min:.0f}min < 60min)")

        # Check sleep score
        good_score = sleep_score is not None and sleep_score >= 75

        # Determine recommended intensity
        if sleep_hours < 5.5:
            recommended_intensity = "recovery_only"
            recommendations.append("Récupération uniquement - sommeil très insuffisant")
        elif not sufficient_duration:
            recommended_intensity = "endurance_max"
            recommendations.append("Zone endurance maximum - éviter haute intensité")
        elif not good_score:
            recommended_intensity = "moderate"
            recommendations.append("Intensité modérée - qualité sommeil sous-optimale")
        else:
            recommended_intensity = "all_systems_go"
            if deep_sleep_ok:
                recommendations.append("Conditions optimales pour séance intensive")
            else:
                recommendations.append("Bonne condition, attention à la récupération")

        ready_for_intense = sufficient_duration and good_score and deep_sleep_ok

        return {
            "date": sleep_data.get("date"),
            "sleep_hours": sleep_hours,
            "sleep_score": sleep_score,
            "deep_sleep_minutes": deep_sleep_min,
            "ready_for_intense": ready_for_intense,
            "recommended_intensity": recommended_intensity,
            "veto_reasons": veto_reasons,
            "recommendations": recommendations,
            "sufficient_duration": sufficient_duration,
            "deep_sleep_ok": deep_sleep_ok,
        }
