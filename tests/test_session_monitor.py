"""Tests for magma_cycling.session_monitor — focus on #368 unplanned activity fork.

Coverage:
    - Regression: planned session + activity → existing behavior unchanged
    - #368: no planned session + Intervals activity → adapted pipeline (skip adherence)
    - #368: no planned session + no activity → exit
    - #368: idempotence cache → skip on second tick same day
    - #368: Sunday + unplanned → end-of-week trigger
    - #368: cache helpers (load empty, load stale, save/load roundtrip)
"""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.session_monitor import (
    _handle_unplanned_activity,
    _load_processed_today_cache,
    _save_processed_today_cache,
)


@pytest.fixture
def cache_path(tmp_path, monkeypatch):
    """Redirect PROCESSED_CACHE_PATH to a tmp path for test isolation."""
    fake = tmp_path / "processed_today.json"
    monkeypatch.setattr("magma_cycling.session_monitor.PROCESSED_CACHE_PATH", fake)
    return fake


class TestProcessedCacheHelpers:
    """Unit tests for _load/_save_processed_today_cache helpers."""

    def test_load_empty_when_file_absent(self, cache_path):
        assert _load_processed_today_cache(date(2026, 5, 23)) == set()

    def test_load_empty_when_date_stale(self, cache_path):
        cache_path.write_text(
            json.dumps({"date": "2026-05-22", "activity_ids": ["A1", "A2"]}),
            encoding="utf-8",
        )
        assert _load_processed_today_cache(date(2026, 5, 23)) == set()

    def test_load_returns_ids_when_date_matches(self, cache_path):
        cache_path.write_text(
            json.dumps({"date": "2026-05-23", "activity_ids": ["A1", "A2"]}),
            encoding="utf-8",
        )
        assert _load_processed_today_cache(date(2026, 5, 23)) == {"A1", "A2"}

    def test_save_then_load_roundtrip(self, cache_path):
        _save_processed_today_cache(date(2026, 5, 23), {"X1", "X2", "X3"})
        assert _load_processed_today_cache(date(2026, 5, 23)) == {"X1", "X2", "X3"}

    def test_load_returns_empty_on_corrupted_json(self, cache_path):
        cache_path.write_text("not valid json {{{", encoding="utf-8")
        assert _load_processed_today_cache(date(2026, 5, 23)) == set()

    def test_save_creates_parent_dir(self, tmp_path, monkeypatch):
        nested = tmp_path / "deep" / "nested" / "processed.json"
        monkeypatch.setattr("magma_cycling.session_monitor.PROCESSED_CACHE_PATH", nested)
        _save_processed_today_cache(date(2026, 5, 23), {"X1"})
        assert nested.exists()


class TestHandleUnplannedActivityNoActivity:
    """Exit path when no Intervals activity is present."""

    def test_no_activity_exits_zero(self, cache_path):
        client = MagicMock()
        client.get_activities.return_value = []
        with patch("magma_cycling.session_monitor.create_intervals_client", return_value=client):
            with patch("magma_cycling.session_monitor.run_command") as mock_run:
                rc = _handle_unplanned_activity(date(2026, 5, 23))
        assert rc == 0
        mock_run.assert_not_called()

    def test_non_cycling_activity_ignored(self, cache_path):
        client = MagicMock()
        client.get_activities.return_value = [
            {"id": "R1", "type": "Run"},
            {"id": "S1", "type": "Swim"},
        ]
        with patch("magma_cycling.session_monitor.create_intervals_client", return_value=client):
            with patch("magma_cycling.session_monitor.run_command") as mock_run:
                rc = _handle_unplanned_activity(date(2026, 5, 23))
        assert rc == 0
        mock_run.assert_not_called()

    def test_intervals_error_exits_zero(self, cache_path):
        client = MagicMock()
        client.get_activities.side_effect = Exception("network down")
        with patch("magma_cycling.session_monitor.create_intervals_client", return_value=client):
            with patch("magma_cycling.session_monitor.run_command") as mock_run:
                rc = _handle_unplanned_activity(date(2026, 5, 23))
        assert rc == 0
        mock_run.assert_not_called()

    def test_icu_ignore_time_activity_filtered_out(self, cache_path):
        """Activities flagged icu_ignore_time should not trigger the pipeline."""
        client = MagicMock()
        client.get_activities.return_value = [
            {"id": "A1", "type": "Ride", "icu_ignore_time": True},
        ]
        with patch("magma_cycling.session_monitor.create_intervals_client", return_value=client):
            with patch("magma_cycling.session_monitor.run_command") as mock_run:
                rc = _handle_unplanned_activity(date(2026, 5, 23))
        assert rc == 0
        mock_run.assert_not_called()


class TestHandleUnplannedActivityPipelineTrigger:
    """Adapted pipeline (skip adherence) fires on unplanned cycling activity."""

    def test_unplanned_ride_triggers_adapted_pipeline(self, cache_path):
        client = MagicMock()
        client.get_activities.return_value = [
            {"id": "A1", "type": "Ride", "icu_ignore_time": False},
        ]
        # Not Sunday (Friday 2026-05-22)
        with patch("magma_cycling.session_monitor.create_intervals_client", return_value=client):
            with patch("magma_cycling.session_monitor.run_command") as mock_run:
                rc = _handle_unplanned_activity(date(2026, 5, 22))

        assert rc == 0
        labels = [call.args[0] for call in mock_run.call_args_list]
        assert "withings-presync" in labels
        assert "daily-sync" in labels
        assert "pid-evaluation" in labels
        assert "adherence" not in labels  # SKIPPED for unplanned
        assert "end-of-week" not in labels  # not Sunday

    def test_unplanned_virtualride_triggers_pipeline(self, cache_path):
        client = MagicMock()
        client.get_activities.return_value = [
            {"id": "VR1", "type": "VirtualRide", "icu_ignore_time": False},
        ]
        with patch("magma_cycling.session_monitor.create_intervals_client", return_value=client):
            with patch("magma_cycling.session_monitor.run_command") as mock_run:
                rc = _handle_unplanned_activity(date(2026, 5, 22))
        assert rc == 0
        labels = [call.args[0] for call in mock_run.call_args_list]
        assert "withings-presync" in labels
        assert "daily-sync" in labels

    def test_sunday_unplanned_triggers_end_of_week(self, cache_path):
        client = MagicMock()
        client.get_activities.return_value = [
            {"id": "A1", "type": "Ride", "icu_ignore_time": False},
        ]
        # Sunday 2026-05-24 (weekday 6)
        sunday = date(2026, 5, 24)
        assert sunday.weekday() == 6
        with patch("magma_cycling.session_monitor.create_intervals_client", return_value=client):
            with patch("magma_cycling.session_monitor.run_command") as mock_run:
                rc = _handle_unplanned_activity(sunday)

        assert rc == 0
        labels = [call.args[0] for call in mock_run.call_args_list]
        assert "end-of-week" in labels


class TestHandleUnplannedActivityIdempotence:
    """Cache prevents double-trigger across cron ticks."""

    def test_first_tick_runs_pipeline_and_caches(self, cache_path):
        client = MagicMock()
        client.get_activities.return_value = [
            {"id": "A1", "type": "Ride", "icu_ignore_time": False},
        ]
        with patch("magma_cycling.session_monitor.create_intervals_client", return_value=client):
            with patch("magma_cycling.session_monitor.run_command") as mock_run:
                rc = _handle_unplanned_activity(date(2026, 5, 22))

        assert rc == 0
        assert mock_run.called
        cached = _load_processed_today_cache(date(2026, 5, 22))
        assert cached == {"A1"}

    def test_second_tick_skips_when_id_already_cached(self, cache_path):
        _save_processed_today_cache(date(2026, 5, 22), {"A1"})

        client = MagicMock()
        client.get_activities.return_value = [
            {"id": "A1", "type": "Ride", "icu_ignore_time": False},
        ]
        with patch("magma_cycling.session_monitor.create_intervals_client", return_value=client):
            with patch("magma_cycling.session_monitor.run_command") as mock_run:
                rc = _handle_unplanned_activity(date(2026, 5, 22))

        assert rc == 0
        mock_run.assert_not_called()

    def test_new_activity_alongside_cached_one_triggers_pipeline(self, cache_path):
        """A2 nouvelle → pipeline ré-armé même si A1 déjà processed."""
        _save_processed_today_cache(date(2026, 5, 22), {"A1"})

        client = MagicMock()
        client.get_activities.return_value = [
            {"id": "A1", "type": "Ride", "icu_ignore_time": False},
            {"id": "A2", "type": "Ride", "icu_ignore_time": False},
        ]
        with patch("magma_cycling.session_monitor.create_intervals_client", return_value=client):
            with patch("magma_cycling.session_monitor.run_command") as mock_run:
                rc = _handle_unplanned_activity(date(2026, 5, 22))

        assert rc == 0
        assert mock_run.called
        cached = _load_processed_today_cache(date(2026, 5, 22))
        assert cached == {"A1", "A2"}

    def test_stale_cache_from_yesterday_reset_and_pipeline_runs(self, cache_path):
        """Cache file dated 2026-05-21 must not prevent run on 2026-05-22."""
        _save_processed_today_cache(date(2026, 5, 21), {"A1"})

        client = MagicMock()
        client.get_activities.return_value = [
            {"id": "A1", "type": "Ride", "icu_ignore_time": False},
        ]
        with patch("magma_cycling.session_monitor.create_intervals_client", return_value=client):
            with patch("magma_cycling.session_monitor.run_command") as mock_run:
                rc = _handle_unplanned_activity(date(2026, 5, 22))

        assert rc == 0
        assert mock_run.called
        cached = _load_processed_today_cache(date(2026, 5, 22))
        assert cached == {"A1"}
