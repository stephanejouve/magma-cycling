"""Tests for MCP list-workout-catalog handler."""

import json
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling._mcp.handlers.catalog import handle_list_workout_catalog
from magma_cycling.external.zwift_models import (
    SegmentType,
    ZwiftCategory,
    ZwiftWorkout,
    ZwiftWorkoutSegment,
)

PATCH_CLIENT = "magma_cycling.external.zwift_client.ZwiftWorkoutClient"


def _make_workout(name, category, tss, duration, pattern=None):
    """Create a test ZwiftWorkout."""
    return ZwiftWorkout(
        name=name,
        category=category,
        duration_minutes=duration,
        tss=tss,
        url=f"https://whatsonzwift.com/workouts/{name.lower().replace(' ', '-')}",
        pattern=pattern,
        segments=[
            ZwiftWorkoutSegment(
                segment_type=SegmentType.WARMUP,
                duration_seconds=420,
                power_low=50,
                power_high=75,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.INTERVAL,
                duration_seconds=600,
                power_low=90,
                repeat_count=3,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.COOLDOWN,
                duration_seconds=360,
                power_low=65,
                power_high=40,
            ),
        ],
    )


@pytest.mark.asyncio
class TestListWorkoutCatalog:
    """Tests for handle_list_workout_catalog."""

    @patch(PATCH_CLIENT)
    async def test_empty_catalog(self, mock_client_cls):
        """Empty catalog returns appropriate message."""
        mock_client = MagicMock()
        mock_client.get_cache_stats.return_value = {"total_workouts": 0}
        mock_client_cls.return_value = mock_client

        result = await handle_list_workout_catalog({})
        data = json.loads(result[0].text)

        assert data["status"] == "empty"

    @patch(PATCH_CLIENT)
    async def test_returns_workouts(self, mock_client_cls):
        """Returns workouts with structure details."""
        halvfems = _make_workout("Halvfems", ZwiftCategory.INTERVALS, 68, 62, "blocs-repetes")
        novanta = _make_workout("Novanta", ZwiftCategory.INTERVALS, 70, 60, "libre")

        mock_client = MagicMock()
        mock_client.get_cache_stats.return_value = {"total_workouts": 24}
        mock_client.search_catalog.return_value = [halvfems, novanta]
        mock_client_cls.return_value = mock_client

        result = await handle_list_workout_catalog({"type": "INT"})
        data = json.loads(result[0].text)

        assert data["status"] == "success"
        assert data["results_count"] == 2
        assert data["workouts"][0]["name"] == "Halvfems"
        assert data["workouts"][0]["pattern"] == "blocs-repetes"
        assert "intervals_description" in data["workouts"][0]

    @patch(PATCH_CLIENT)
    async def test_filters_applied(self, mock_client_cls):
        """Filters are passed to search_catalog and reported."""
        mock_client = MagicMock()
        mock_client.get_cache_stats.return_value = {"total_workouts": 100}
        mock_client.search_catalog.return_value = []
        mock_client_cls.return_value = mock_client

        args = {"type": "END", "duration_min": 60, "tss_target": 55, "pattern": "progressif"}
        result = await handle_list_workout_catalog(args)
        data = json.loads(result[0].text)

        assert data["filters_applied"]["type"] == "END"
        assert data["filters_applied"]["duration_min"] == 60
        assert data["filters_applied"]["tss_target"] == 55
        assert data["filters_applied"]["pattern"] == "progressif"

        # Verify search_catalog was called with correct params
        mock_client.search_catalog.assert_called_once_with(
            session_type="END",
            duration_target=60,
            tss_target=55,
            pattern="progressif",
            limit=5,
        )

    @patch(PATCH_CLIENT)
    async def test_default_limit_5(self, mock_client_cls):
        """Default limit is 5."""
        mock_client = MagicMock()
        mock_client.get_cache_stats.return_value = {"total_workouts": 100}
        mock_client.search_catalog.return_value = []
        mock_client_cls.return_value = mock_client

        await handle_list_workout_catalog({})

        call_kwargs = mock_client.search_catalog.call_args
        assert call_kwargs[1]["limit"] == 5 or call_kwargs.kwargs.get("limit") == 5

    @patch(PATCH_CLIENT)
    async def test_exception_returns_error(self, mock_client_cls):
        """Exception returns error response."""
        mock_client_cls.side_effect = RuntimeError("DB error")

        result = await handle_list_workout_catalog({})
        data = json.loads(result[0].text)

        assert "error" in data

    @patch(PATCH_CLIENT)
    async def test_session_type_mapping(self, mock_client_cls):
        """Session type is correctly mapped in results."""
        workout = _make_workout("Test", ZwiftCategory.ENDURANCE, 50, 60)

        mock_client = MagicMock()
        mock_client.get_cache_stats.return_value = {"total_workouts": 10}
        mock_client.search_catalog.return_value = [workout]
        mock_client_cls.return_value = mock_client

        result = await handle_list_workout_catalog({})
        data = json.loads(result[0].text)

        assert data["workouts"][0]["session_type"] == "END"
        assert data["workouts"][0]["category"] == "Endurance"
