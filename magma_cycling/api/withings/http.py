"""HTTP core mixin for WithingsClient."""

import logging
import time
from typing import Any

import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


class HttpMixin:
    """Authenticated HTTP requests with rate limiting and retry."""

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
