"""
Tests for IntervalsClient unified API client.

Tests pour le client API unifié IntervalsClient.
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from magma_cycling.api.intervals_client import IntervalsClient


@pytest.fixture
def mock_session():
    """Create a mock requests.Session."""
    with patch("magma_cycling.api.intervals_client.requests.Session") as mock:
        session = MagicMock()
        mock.return_value = session
        yield session


@pytest.fixture
def client(mock_session):
    """Create an IntervalsClient instance with mocked session."""
    return IntervalsClient(athlete_id="iXXXXXX", api_key="test_key")


class TestIntervalsClientInit:
    """Tests for IntervalsClient initialization."""

    def test_init_success(self, mock_session):
        """Test successful initialization."""
        client = IntervalsClient(athlete_id="iXXXXXX", api_key="test_key")

        assert client.athlete_id == "iXXXXXX"
        assert client.BASE_URL == "https://intervals.icu/api/v1"

        # Verify session setup
        mock_session.auth = ("API_KEY", "test_key")
        mock_session.headers.update.assert_called_once_with({"Content-Type": "application/json"})

    def test_init_empty_athlete_id(self):
        """Test initialization fails with empty athlete_id."""
        with pytest.raises(ValueError, match="athlete_id and api_key are required"):
            IntervalsClient(athlete_id="", api_key="test_key")

    def test_init_empty_api_key(self):
        """Test initialization fails with empty api_key."""
        with pytest.raises(ValueError, match="athlete_id and api_key are required"):
            IntervalsClient(athlete_id="iXXXXXX", api_key="")


class TestGetAthlete:
    """Tests for get_athlete method."""

    def test_get_athlete_success(self, client, mock_session):
        """Test successful athlete profile fetch."""
        mock_response = Mock()

        mock_response.json.return_value = {
            "id": "iXXXXXX",
            "name": "Test Athlete",
            "ftp": 250,
            "weight": 75.0,
        }
        mock_session.get.return_value = mock_response

        result = client.get_athlete()

        assert result["id"] == "iXXXXXX"
        assert result["ftp"] == 250
        mock_session.get.assert_called_once_with("https://intervals.icu/api/v1/athlete/iXXXXXX")
        mock_response.raise_for_status.assert_called_once()


class TestGetActivities:
    """Tests for get_activities method."""

    def test_get_activities_no_params(self, client, mock_session):
        """Test get_activities without date filters."""
        mock_response = Mock()

        mock_response.json.return_value = [
            {"id": "i107424849", "type": "Ride", "icu_training_load": 65}
        ]
        mock_session.get.return_value = mock_response

        result = client.get_activities()

        assert len(result) == 1
        assert result[0]["id"] == "i107424849"
        mock_session.get.assert_called_once_with(
            "https://intervals.icu/api/v1/athlete/iXXXXXX/activities", params={}
        )

    def test_get_activities_with_dates(self, client, mock_session):
        """Test get_activities with oldest/newest parameters."""
        mock_response = Mock()

        mock_response.json.return_value = []
        mock_session.get.return_value = mock_response

        client.get_activities(oldest="2025-12-22", newest="2025-12-28")

        mock_session.get.assert_called_once_with(
            "https://intervals.icu/api/v1/athlete/iXXXXXX/activities",
            params={"oldest": "2025-12-22", "newest": "2025-12-28"},
        )


class TestGetActivity:
    """Tests for get_activity method."""

    def test_get_activity_success(self, client, mock_session):
        """Test successful single activity fetch."""
        mock_response = Mock()

        mock_response.json.return_value = {
            "id": "i107424849",
            "icu_training_load": 65,
            "icu_intensity": 0.68,
        }
        mock_session.get.return_value = mock_response

        result = client.get_activity("i107424849")

        assert result["id"] == "i107424849"
        assert result["icu_training_load"] == 65
        mock_session.get.assert_called_once_with("https://intervals.icu/api/v1/activity/i107424849")


class TestGetWellness:
    """Tests for get_wellness method."""

    def test_get_wellness_success(self, client, mock_session):
        """Test successful wellness data fetch."""
        mock_response = Mock()

        mock_response.json.return_value = [
            {"id": "2025-12-22", "ctl": 45.6, "atl": 37.7, "weight": 75.0}
        ]
        mock_session.get.return_value = mock_response

        result = client.get_wellness(oldest="2025-12-22", newest="2025-12-22")

        assert len(result) == 1
        assert result[0]["ctl"] == 45.6
        mock_session.get.assert_called_once_with(
            "https://intervals.icu/api/v1/athlete/iXXXXXX/wellness",
            params={"oldest": "2025-12-22", "newest": "2025-12-22"},
        )

    def test_get_wellness_returns_list(self, client, mock_session):
        """Test that get_wellness returns a list, not a dict."""
        mock_response = Mock()

        mock_response.json.return_value = [
            {"id": "2025-12-22", "ctl": 45.6},
            {"id": "2025-12-23", "ctl": 45.8},
        ]
        mock_session.get.return_value = mock_response

        result = client.get_wellness(oldest="2025-12-22", newest="2025-12-23")

        assert isinstance(result, list)
        assert len(result) == 2


class TestGetEvents:
    """Tests for get_events method."""

    def test_get_events_success(self, client, mock_session):
        """Test successful events fetch."""
        mock_response = Mock()

        mock_response.json.return_value = [
            {"id": 86044984, "category": "WORKOUT", "name": "S074-01-END-EnduranceBase"}
        ]
        mock_session.get.return_value = mock_response

        result = client.get_events(oldest="2025-12-29", newest="2026-01-04")

        assert len(result) == 1
        assert result[0]["category"] == "WORKOUT"
        mock_session.get.assert_called_once_with(
            "https://intervals.icu/api/v1/athlete/iXXXXXX/events",
            params={"oldest": "2025-12-29", "newest": "2026-01-04"},
        )


class TestGetPlannedWorkout:
    """Tests for get_planned_workout method."""

    def test_get_planned_workout_found(self, client, mock_session):
        """Test finding a planned workout."""
        mock_response = Mock()

        mock_response.json.return_value = [
            {"id": 86044984, "category": "WORKOUT", "paired_activity_id": "i107424849"}
        ]
        mock_session.get.return_value = mock_response

        activity_date = datetime(2025, 12, 30)
        result = client.get_planned_workout("i107424849", activity_date)

        assert result is not None
        assert result["paired_activity_id"] == "i107424849"

    def test_get_planned_workout_not_found(self, client, mock_session):
        """Test when no planned workout is found."""
        mock_response = Mock()

        mock_response.json.return_value = [
            {"id": 86044984, "category": "WORKOUT", "paired_activity_id": "i999999"}  # Different ID
        ]
        mock_session.get.return_value = mock_response

        activity_date = datetime(2025, 12, 30)
        result = client.get_planned_workout("i107424849", activity_date)

        assert result is None


class TestCreateEvent:
    """Tests for create_event method."""

    def test_create_event_success(self, client, mock_session):
        """Test successful event creation."""
        mock_response = Mock()

        mock_response.json.return_value = {"id": 86044984, "name": "S074-01-END-EnduranceBase"}
        mock_session.post.return_value = mock_response

        event_data = {
            "category": "WORKOUT",
            "name": "S074-01-END-EnduranceBase",
            "description": "60min @ 70% FTP",
            "start_date_local": "2025-12-29",
        }

        result = client.create_event(event_data)

        assert result is not None
        assert result["id"] == 86044984
        mock_session.post.assert_called_once_with(
            "https://intervals.icu/api/v1/athlete/iXXXXXX/events", json=event_data
        )

    def test_create_event_http_error(self, client, mock_session):
        """Test event creation with HTTP error."""
        import requests

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
        mock_response.response = None
        mock_session.post.return_value = mock_response

        event_data = {"category": "WORKOUT", "name": "Test"}

        result = client.create_event(event_data)

        assert result is None

    def test_create_event_generic_error(self, client, mock_session):
        """Test event creation with generic exception."""
        mock_session.post.side_effect = Exception("Network error")

        event_data = {"category": "WORKOUT", "name": "Test"}

        result = client.create_event(event_data)

        assert result is None


class TestErrorHandling:
    """Tests for error handling across all methods."""

    def test_http_error_propagation(self, client, mock_session):
        """Test that HTTP errors are propagated correctly."""
        import requests

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500")
        mock_session.get.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            client.get_athlete()


class TestSafeDecodeHelpers:
    """Regression tests for BT-011 — Intervals.icu API responses with raw
    Latin-1 bytes (notably 0xE9) in user-authored fields like notes must not
    crash the MCP tool. The _safe_text / _safe_json helpers fall back to a
    UTF-8 decode with errors='replace' when response.text / response.json()
    raise UnicodeDecodeError."""

    def test_safe_text_passthrough_when_clean_utf8(self):
        from magma_cycling.api.intervals_client import _safe_text

        response = Mock()
        response.text = "no problem here"
        assert _safe_text(response) == "no problem here"

    def test_safe_text_falls_back_on_unicode_decode_error(self):
        from magma_cycling.api.intervals_client import _safe_text

        response = Mock()
        type(response).text = property(
            lambda self: (_ for _ in ()).throw(UnicodeDecodeError("utf-8", b"", 0, 1, "stub"))
        )
        # Raw body containing a stray Latin-1 byte 0xE9 in the middle of a
        # UTF-8 string — Intervals.icu real-world payload pattern.
        response.content = b"prefix " + bytes([0xE9]) + b" suffix"

        result = _safe_text(response)
        assert result.startswith("prefix ")
        assert result.endswith(" suffix")

    def test_safe_json_passthrough_when_clean_utf8(self):
        from magma_cycling.api.intervals_client import _safe_json

        response = Mock()
        response.json.return_value = {"id": 42, "name": "ok"}
        assert _safe_json(response) == {"id": 42, "name": "ok"}

    def test_safe_json_falls_back_on_unicode_decode_error(self):
        from magma_cycling.api.intervals_client import _safe_json

        response = Mock()
        response.json.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "stub")
        # Forge a JSON body where the user-authored "name" field contains a
        # raw Latin-1 byte 0xE9 (cp1252 'é'), invalid as UTF-8.
        response.content = b'{"id": 42, "name": "Kin' + bytes([0xE9]) + b' midi"}'

        result = _safe_json(response)
        assert result["id"] == 42
        assert result["name"].startswith("Kin")
        assert result["name"].endswith(" midi")

    def test_safe_helpers_used_throughout_client(self, client, mock_session):
        """Smoke test: a get_events call where the API response would have
        previously crashed (UnicodeDecodeError on response.json()) returns a
        usable payload through the fallback decode path."""
        response = Mock()
        response.json.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "stub")
        response.content = (
            b'[{"id": 106796340, "name": "Insolation ' + bytes([0xE9]) + b'", "category": "NOTE"}]'
        )
        mock_session.get.return_value = response

        events = client.get_events(oldest="2026-04-01", newest="2026-04-30")
        assert events[0]["id"] == 106796340
        assert events[0]["category"] == "NOTE"
        assert events[0]["name"].startswith("Insolation ")
