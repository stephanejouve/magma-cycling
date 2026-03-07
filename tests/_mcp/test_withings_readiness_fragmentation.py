"""Tests for sleep fragmentation warning in readiness handler."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling._mcp.handlers.withings import handle_withings_get_readiness
from magma_cycling.models.withings_models import SleepData, TrainingReadiness


def _make_sleep_data(segments_count=1, segments_detail=None):
    """Build a SleepData with fragmentation fields."""
    return SleepData(
        date=date(2026, 3, 7),
        start_datetime="2026-03-06T22:08:00",
        end_datetime="2026-03-07T07:09:00",
        total_sleep_hours=8.7,
        wakeup_count=3,
        sleep_score=78,
        segments_count=segments_count,
        segments_detail=segments_detail,
    )


def _make_readiness():
    """Build a TrainingReadiness for testing."""
    return TrainingReadiness(
        date=date(2026, 3, 7),
        sleep_hours=8.7,
        sleep_score=78,
        ready_for_intense=True,
        recommended_intensity="all_systems_go",
        veto_reasons=[],
        recommendations=["Conditions optimales"],
        sufficient_duration=True,
        deep_sleep_ok=False,
    )


@pytest.mark.asyncio
class TestReadinessFragmentationWarning:
    @patch("magma_cycling.health.create_health_provider")
    async def test_readiness_includes_fragmentation_warning(self, mock_create):
        provider = MagicMock()
        mock_create.return_value = provider
        provider.get_readiness.return_value = _make_readiness()
        provider.get_sleep_summary.return_value = _make_sleep_data(
            segments_count=2,
            segments_detail=[
                {"start": "22:08", "end": "01:30", "duration_hours": 3.2},
                {"start": "01:30", "end": "07:09", "duration_hours": 5.5},
            ],
        )

        result = await handle_withings_get_readiness({"date": "2026-03-07"})

        import json

        data = json.loads(result[0].text)
        assert "sleep_fragmentation" in data
        assert "2 segments fusionnés" in data["sleep_fragmentation"]
        assert "22:08" in data["sleep_fragmentation"]

    @patch("magma_cycling.health.create_health_provider")
    async def test_readiness_no_warning_single_segment(self, mock_create):
        provider = MagicMock()
        mock_create.return_value = provider
        provider.get_readiness.return_value = _make_readiness()
        provider.get_sleep_summary.return_value = _make_sleep_data(segments_count=1)

        result = await handle_withings_get_readiness({"date": "2026-03-07"})

        import json

        data = json.loads(result[0].text)
        assert "sleep_fragmentation" not in data
