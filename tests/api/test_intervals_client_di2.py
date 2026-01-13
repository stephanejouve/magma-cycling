"""Tests for Di2 streams extraction in IntervalsClient.

Tests cover get_activity_streams() method for extracting
Di2 electronic shifting data (FrontGear, RearGear, GearRatio).
"""

from unittest.mock import Mock, patch

import pytest

from cyclisme_training_logs.api.intervals_client import IntervalsClient


class TestGetActivityStreamsDi2:
    """Test suite for Di2 streams extraction."""

    @pytest.fixture
    def client(self):
        """Create IntervalsClient with test credentials."""
        return IntervalsClient(athlete_id="i151223", api_key="test_key")

    @pytest.fixture
    def mock_di2_streams(self):
        """Mock Di2 streams data (realistic structure)."""
        return [
            {"type": "FrontGear", "data": [50, 50, 50, 34, 34, 50, 50]},
            {"type": "RearGear", "data": [21, 21, 24, 27, 27, 21, 18]},
            {"type": "GearRatio", "data": [2.38, 2.38, 2.08, 1.26, 1.26, 2.38, 2.78]},
            {"type": "watts", "data": [150, 160, 170, 140, 145, 155, 165]},
            {"type": "heartrate", "data": [120, 125, 130, 115, 118, 122, 128]},
        ]

    def test_get_activity_streams_success_with_di2(self, client, mock_di2_streams):
        """Test successful extraction of Di2 streams."""
        # Given: Activity with Di2 data
        activity_id = "i107424849"

        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_di2_streams
            mock_get.return_value = mock_response

            # When: Getting activity streams
            streams = client.get_activity_streams(activity_id)

            # Then: Returns complete stream data
            assert streams is not None
            assert isinstance(streams, list)
            assert len(streams) == 5

            # Verify Di2 streams present
            stream_types = [s["type"] for s in streams]
            assert "FrontGear" in stream_types
            assert "RearGear" in stream_types
            assert "GearRatio" in stream_types

            # Verify data structure
            front_gear = next(s for s in streams if s["type"] == "FrontGear")
            assert "data" in front_gear
            assert len(front_gear["data"]) == 7
            assert front_gear["data"][0] == 50  # First value

            # Verify API called correctly
            mock_get.assert_called_once()
            call_args = mock_get.call_args[0][0]
            assert activity_id in call_args
            assert "streams" in call_args

    def test_get_activity_streams_missing_di2_data(self, client):
        """Test activity without Di2 data (indoor trainer)."""
        # Given: Activity without Di2 (only watts, HR, cadence)
        activity_id = "i107424850"
        streams_no_di2 = [
            {"type": "watts", "data": [150, 160, 170]},
            {"type": "heartrate", "data": [120, 125, 130]},
            {"type": "cadence", "data": [90, 92, 95]},
        ]

        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = streams_no_di2
            mock_get.return_value = mock_response

            # When: Getting activity streams
            streams = client.get_activity_streams(activity_id)

            # Then: Returns streams without Di2
            assert streams is not None
            assert isinstance(streams, list)
            assert len(streams) == 3

            stream_types = [s["type"] for s in streams]
            assert "FrontGear" not in stream_types
            assert "RearGear" not in stream_types
            assert "watts" in stream_types

    def test_get_activity_streams_http_error(self, client):
        """Test graceful handling of HTTP errors."""
        # Given: API unavailable
        activity_id = "i107424851"

        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = Exception("HTTP 503 Service Unavailable")
            mock_get.return_value = mock_response

            # When/Then: Exception raised
            with pytest.raises(Exception) as exc_info:
                client.get_activity_streams(activity_id)

            assert "503" in str(exc_info.value)

    def test_get_activity_streams_empty_response(self, client):
        """Test handling of empty streams response."""
        # Given: Activity with empty streams (edge case)
        activity_id = "i107424852"

        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = []
            mock_get.return_value = mock_response

            # When: Getting streams
            streams = client.get_activity_streams(activity_id)

            # Then: Returns empty list (not None)
            assert streams is not None
            assert isinstance(streams, list)
            assert len(streams) == 0

    def test_get_activity_streams_partial_di2_data(self, client):
        """Test activity with only RearGear (FrontGear missing)."""
        # Given: Partial Di2 data (sensor failure scenario)
        activity_id = "i107424853"
        streams_partial = [
            {"type": "RearGear", "data": [21, 24, 27]},
            {"type": "watts", "data": [150, 160, 170]},
        ]

        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = streams_partial
            mock_get.return_value = mock_response

            # When: Getting streams
            streams = client.get_activity_streams(activity_id)

            # Then: Returns partial data (consumer handles missing FrontGear)
            assert streams is not None
            stream_types = [s["type"] for s in streams]
            assert "RearGear" in stream_types
            assert "FrontGear" not in stream_types

    def test_get_activity_streams_with_none_values(self, client):
        """Test Di2 streams containing None values (dropout)."""
        # Given: Streams with None (signal dropout)
        activity_id = "i107424854"
        streams_with_none = [
            {"type": "FrontGear", "data": [50, 50, None, 34, 34]},
            {"type": "RearGear", "data": [21, None, 24, 27, 27]},
        ]

        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = streams_with_none
            mock_get.return_value = mock_response

            # When: Getting streams
            streams = client.get_activity_streams(activity_id)

            # Then: Returns data including None (consumer filters)
            assert streams is not None
            front_gear = next(s for s in streams if s["type"] == "FrontGear")
            assert None in front_gear["data"]
            assert len(front_gear["data"]) == 5
