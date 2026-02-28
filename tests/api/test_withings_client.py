"""
Tests for WithingsClient - Black-box testing approach.

Tests the external behavior and API contract of WithingsClient
without knowledge of internal implementation details.
"""

from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import Mock, patch

import pytest
import requests

from magma_cycling.api.withings_client import WithingsClient


@pytest.fixture
def temp_credentials_file():
    """Create a temporary credentials file for testing."""
    with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(
            """{
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "token_expiry": 9999999999,
            "user_id": "12345"
        }"""
        )
        f.flush()
    # File is now closed, so it can be read
    yield Path(f.name)
    Path(f.name).unlink()


@pytest.fixture
def client():
    """Create a WithingsClient instance for testing."""
    return WithingsClient(
        client_id="test_client_id",
        client_secret="test_client_secret",
        redirect_uri="http://localhost:8080/callback",
    )


class TestOAuthFlow:
    """Test OAuth authentication flow - external behavior."""

    def test_get_authorization_url_returns_valid_url(self, client):
        """Authorization URL should contain required OAuth parameters."""
        url = client.get_authorization_url()

        assert "https://account.withings.com/oauth2_user/authorize2" in url
        assert "client_id=test_client_id" in url
        assert "redirect_uri=" in url
        assert "scope=user.metrics,user.activity" in url
        assert "response_type=code" in url

    def test_get_authorization_url_with_state(self, client):
        """Authorization URL should include state parameter when provided."""
        url = client.get_authorization_url(state="test_state_123")

        assert "state=test_state_123" in url

    @patch("requests.post")
    def test_exchange_code_success(self, mock_post, client, temp_credentials_file):
        """Successful code exchange should return tokens and save credentials."""
        client.credentials_path = temp_credentials_file

        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": 0,
            "body": {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "userid": "12345",
                "expires_in": 3600,
            },
        }
        mock_post.return_value = mock_response

        result = client.exchange_code("test_auth_code")

        # Verify tokens returned
        assert result["access_token"] == "new_access_token"
        assert result["refresh_token"] == "new_refresh_token"
        assert result["user_id"] == "12345"

        # Verify credentials saved
        assert temp_credentials_file.exists()

    @patch("requests.post")
    def test_exchange_code_api_error(self, mock_post, client):
        """API error during code exchange should raise exception."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": 2048, "error": "Invalid code"}
        mock_post.return_value = mock_response

        with pytest.raises(requests.exceptions.RequestException, match="Withings API error"):
            client.exchange_code("invalid_code")

    @patch("requests.post")
    def test_exchange_code_http_error(self, mock_post, client):
        """HTTP error during code exchange should raise exception."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        with pytest.raises(
            requests.exceptions.RequestException, match="Failed to exchange authorization code"
        ):
            client.exchange_code("invalid_code")

    def test_is_authenticated_without_token(self, client):
        """Client without token should not be authenticated."""
        assert client.is_authenticated() is False

    def test_is_authenticated_with_valid_token(self, client, temp_credentials_file):
        """Client with valid token should be authenticated."""
        client.credentials_path = temp_credentials_file
        client.load_credentials()

        assert client.is_authenticated() is True

    def test_is_authenticated_with_expired_token(self, client, temp_credentials_file):
        """Client with expired token should not be authenticated."""
        # Create credentials with expired token
        with open(temp_credentials_file, "w") as f:
            f.write(
                """{
                "access_token": "expired_token",
                "refresh_token": "test_refresh_token",
                "token_expiry": 1000000,
                "user_id": "12345"
            }"""
            )

        client.credentials_path = temp_credentials_file
        client.load_credentials()

        assert client.is_authenticated() is False


class TestSleepData:
    """Test sleep data retrieval - external behavior."""

    @patch.object(WithingsClient, "_make_request")
    def test_get_sleep_returns_list(self, mock_request, client):
        """get_sleep should return list of sleep sessions."""
        # Setup: Client needs to be authenticated
        client.access_token = "test_token"
        client.token_expiry = 9999999999

        # Mock API response
        mock_request.return_value = {
            "series": [
                {
                    "startdate": 1708560000,
                    "enddate": 1708585200,
                    "data": {
                        "total_sleep_time": 25200,
                        "deepsleepduration": 5400,
                        "lightsleepduration": 14400,
                        "remsleepduration": 5400,
                        "sleep_score": 85,
                        "wakeupcount": 2,
                    },
                }
            ]
        }

        result = client.get_sleep(date(2026, 2, 20), date(2026, 2, 22))

        # Verify behavior
        assert isinstance(result, list)
        assert len(result) == 1
        assert "total_sleep_hours" in result[0]
        assert result[0]["total_sleep_hours"] == 7.0
        assert result[0]["sleep_score"] == 85

    @patch.object(WithingsClient, "_make_request")
    def test_get_sleep_empty_response(self, mock_request, client):
        """get_sleep with no data should return empty list."""
        client.access_token = "test_token"
        client.token_expiry = 9999999999

        mock_request.return_value = {"series": []}

        result = client.get_sleep(date(2026, 2, 20), date(2026, 2, 22))

        assert result == []

    @patch.object(WithingsClient, "_make_request")
    def test_get_last_night_sleep_returns_most_recent(self, mock_request, client):
        """get_last_night_sleep should return most recent sleep session."""
        client.access_token = "test_token"
        client.token_expiry = 9999999999

        mock_request.return_value = {
            "series": [
                {
                    "startdate": 1708560000,
                    "enddate": 1708585200,
                    "data": {"total_sleep_time": 25200, "wakeupcount": 2},
                }
            ]
        }

        result = client.get_last_night_sleep()

        assert result is not None
        assert "total_sleep_hours" in result
        assert result["total_sleep_hours"] == 7.0

    @patch.object(WithingsClient, "_make_request")
    def test_get_last_night_sleep_no_data(self, mock_request, client):
        """get_last_night_sleep with no data should return None."""
        client.access_token = "test_token"
        client.token_expiry = 9999999999

        mock_request.return_value = {"series": []}

        result = client.get_last_night_sleep()

        assert result is None


class TestWeightData:
    """Test weight data retrieval - external behavior."""

    @patch.object(WithingsClient, "_make_request")
    def test_get_measurements_returns_list(self, mock_request, client):
        """get_measurements should return list of weight measurements."""
        client.access_token = "test_token"
        client.token_expiry = 9999999999

        mock_request.return_value = {
            "measuregrps": [
                {
                    "date": 1708560000,
                    "measures": [{"type": 1, "value": 750, "unit": -1}],  # Weight: 75.0 kg
                }
            ]
        }

        result = client.get_measurements(date(2026, 2, 20), date(2026, 2, 22))

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["weight_kg"] == 75.0

    @patch.object(WithingsClient, "_make_request")
    def test_get_measurements_with_body_composition(self, mock_request, client):
        """get_measurements should handle body composition data."""
        client.access_token = "test_token"
        client.token_expiry = 9999999999

        mock_request.return_value = {
            "measuregrps": [
                {
                    "date": 1708560000,
                    "measures": [
                        {"type": 1, "value": 750, "unit": -1},  # Weight
                        {"type": 8, "value": 150, "unit": -1},  # Fat mass
                        {"type": 76, "value": 350, "unit": -1},  # Muscle mass
                    ],
                }
            ]
        }

        result = client.get_measurements(
            date(2026, 2, 20), date(2026, 2, 22), measure_types=[1, 8, 76]
        )

        assert len(result) == 1
        assert result[0]["weight_kg"] == 75.0
        assert result[0]["fat_mass_kg"] == 15.0
        assert result[0]["muscle_mass_kg"] == 35.0

    @patch.object(WithingsClient, "_make_request")
    def test_get_latest_weight_returns_most_recent(self, mock_request, client):
        """get_latest_weight should return most recent measurement."""
        client.access_token = "test_token"
        client.token_expiry = 9999999999

        mock_request.return_value = {
            "measuregrps": [
                {"date": 1708560000, "measures": [{"type": 1, "value": 750, "unit": -1}]},
                {"date": 1708646400, "measures": [{"type": 1, "value": 752, "unit": -1}]},
            ]
        }

        result = client.get_latest_weight()

        assert result is not None
        assert result["weight_kg"] == 75.2  # Most recent


class TestTrainingReadiness:
    """Test training readiness evaluation - external behavior."""

    def test_evaluate_training_readiness_optimal(self, client):
        """Optimal sleep should recommend all_systems_go."""
        sleep_data = {
            "total_sleep_hours": 8.0,
            "sleep_score": 85,
            "deep_sleep_minutes": 90,
        }

        result = client.evaluate_training_readiness(sleep_data)

        assert result["ready_for_intense"] is True
        assert result["recommended_intensity"] == "all_systems_go"
        assert len(result["veto_reasons"]) == 0

    def test_evaluate_training_readiness_insufficient_sleep(self, client):
        """Insufficient sleep should veto intense training."""
        sleep_data = {
            "total_sleep_hours": 5.0,
            "sleep_score": 70,
            "deep_sleep_minutes": 40,
        }

        result = client.evaluate_training_readiness(sleep_data)

        assert result["ready_for_intense"] is False
        assert result["recommended_intensity"] == "recovery_only"
        assert len(result["veto_reasons"]) > 0

    def test_evaluate_training_readiness_moderate_sleep(self, client):
        """Moderate sleep should recommend moderate intensity."""
        sleep_data = {
            "total_sleep_hours": 6.5,
            "sleep_score": 65,
            "deep_sleep_minutes": 55,
        }

        result = client.evaluate_training_readiness(sleep_data)

        assert result["ready_for_intense"] is False
        assert result["recommended_intensity"] in ["endurance_max", "moderate"]

    def test_evaluate_training_readiness_missing_score(self, client):
        """Readiness evaluation should handle missing sleep score."""
        sleep_data = {
            "total_sleep_hours": 7.5,
            "sleep_score": None,
            "deep_sleep_minutes": 80,
        }

        result = client.evaluate_training_readiness(sleep_data)

        # Should still provide recommendation
        assert "recommended_intensity" in result
        assert isinstance(result["ready_for_intense"], bool)


class TestCredentialsManagement:
    """Test credentials loading and saving - external behavior."""

    def test_load_credentials_success(self, client, temp_credentials_file):
        """Loading valid credentials should succeed."""
        client.credentials_path = temp_credentials_file

        result = client.load_credentials()

        assert result is True
        assert client.access_token == "test_access_token"
        assert client.user_id == "12345"

    def test_load_credentials_file_not_found(self, client):
        """Loading from non-existent file should return False."""
        client.credentials_path = Path("/non/existent/path.json")

        result = client.load_credentials()

        assert result is False

    def test_save_credentials_creates_file(self, client, tmp_path):
        """Saving credentials should create file with correct permissions."""
        creds_path = tmp_path / "test_credentials.json"
        client.credentials_path = creds_path
        client.access_token = "test_token"
        client.refresh_token = "test_refresh"
        client.token_expiry = 9999999999
        client.user_id = "12345"

        client.save_credentials()

        assert creds_path.exists()
        # Check file permissions (600 = owner read/write only)
        assert oct(creds_path.stat().st_mode)[-3:] == "600"

    def test_save_credentials_without_path_raises_error(self, client):
        """Saving without credentials_path should raise ValueError."""
        client.credentials_path = None

        with pytest.raises(ValueError, match="credentials_path not set"):
            client.save_credentials()


class TestErrorHandling:
    """Test error handling and edge cases - external behavior."""

    @patch.object(WithingsClient, "_make_request")
    def test_network_error_handling(self, mock_request, client):
        """Network errors should be properly raised."""
        client.access_token = "test_token"
        client.token_expiry = 9999999999

        mock_request.side_effect = requests.exceptions.RequestException("Network error")

        with pytest.raises(requests.exceptions.RequestException):
            client.get_sleep(date(2026, 2, 20), date(2026, 2, 22))

    def test_unauthenticated_request_raises_error(self, client):
        """Requests without authentication should raise ValueError."""
        with pytest.raises(ValueError, match="Not authenticated"):
            client.get_sleep(date(2026, 2, 20), date(2026, 2, 22))

    @patch("time.time")
    @patch("requests.post")
    def test_token_refresh_on_expiry(self, mock_post, mock_time, client):
        """Expired token should trigger automatic refresh."""
        # Setup client with expiring token
        client.access_token = "old_token"
        client.refresh_token = "refresh_token"
        client.token_expiry = 1000  # Expired
        mock_time.return_value = 2000

        # Mock refresh response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": 0,
            "body": {
                "access_token": "new_token",
                "refresh_token": "new_refresh",
                "expires_in": 3600,
            },
        }
        mock_post.return_value = mock_response

        # This should trigger refresh
        client.refresh_access_token()

        assert client.access_token == "new_token"
        assert mock_post.called
