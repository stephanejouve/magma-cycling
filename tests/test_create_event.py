"""Tests for create_event API method (mocked, no live calls)."""

from unittest.mock import patch

from magma_cycling.api.intervals_client import IntervalsClient


class TestCreateEventDateOnly:
    """Test create_event with date-only format."""

    @patch.object(IntervalsClient, "__init__", lambda self, **kw: None)
    @patch.object(IntervalsClient, "create_event")
    def test_create_event_date_only(self, mock_create):
        """Date-only start_date_local is passed correctly to create_event."""
        mock_create.return_value = {"id": "evt_001", "name": "Test Simple"}

        api = IntervalsClient()
        event_data = {
            "category": "WORKOUT",
            "name": "Test Simple",
            "description": "Warmup 10min\nMain set 20min\nCooldown 10min",
            "start_date_local": "2025-12-01",
        }
        result = api.create_event(event_data)

        mock_create.assert_called_once_with(event_data)
        assert result["id"] == "evt_001"
        assert result["name"] == "Test Simple"


class TestCreateEventDatetime:
    """Test create_event with datetime format."""

    @patch.object(IntervalsClient, "__init__", lambda self, **kw: None)
    @patch.object(IntervalsClient, "create_event")
    def test_create_event_datetime(self, mock_create):
        """Datetime start_date_local (with time) is passed correctly."""
        mock_create.return_value = {"id": "evt_002", "name": "Test Avec Heure"}

        api = IntervalsClient()
        event_data = {
            "category": "WORKOUT",
            "name": "Test Avec Heure",
            "description": "Warmup 10min\nMain set 20min\nCooldown 10min",
            "start_date_local": "2025-12-02T08:00:00",
        }
        result = api.create_event(event_data)

        mock_create.assert_called_once_with(event_data)
        assert result["id"] == "evt_002"
        assert "T08:00:00" in event_data["start_date_local"]
