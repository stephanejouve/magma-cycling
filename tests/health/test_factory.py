"""Tests for create_health_provider factory."""

from unittest.mock import Mock, patch

from magma_cycling.health.factory import create_health_provider
from magma_cycling.health.intervals_provider import IntervalsHealthProvider
from magma_cycling.health.null_provider import NullProvider
from magma_cycling.health.withings_provider import WithingsProvider


class TestCreateHealthProvider:
    def test_returns_withings_provider_when_configured(self):
        mock_config = Mock()
        mock_config.is_configured.return_value = True
        mock_client = Mock()
        with (
            patch("magma_cycling.config.get_withings_config", return_value=mock_config),
            patch("magma_cycling.config.create_withings_client", return_value=mock_client),
        ):
            provider = create_health_provider()
        assert isinstance(provider, WithingsProvider)

    def test_returns_null_provider_when_not_configured(self):
        mock_config = Mock()
        mock_config.is_configured.return_value = False
        with patch("magma_cycling.config.get_withings_config", return_value=mock_config):
            provider = create_health_provider()
        assert isinstance(provider, NullProvider)

    def test_returns_null_provider_on_exception(self):
        with patch(
            "magma_cycling.config.get_withings_config",
            side_effect=RuntimeError("config broken"),
        ):
            provider = create_health_provider()
        assert isinstance(provider, NullProvider)


class TestIntervalsHealthProviderProbeWindow:
    """The Intervals provider probe must accept any sleep entry within a 7-day
    window. A single missing day (late Garmin sync, day off, weekend without
    the watch) must not silently disable the provider for the whole session."""

    def _withings_unconfigured(self):
        cfg = Mock()
        cfg.is_configured.return_value = False
        return cfg

    def test_returns_intervals_when_yesterday_has_sleep(self):
        """Happy path: yesterday already has sleepTime."""
        client = Mock()
        client.get_wellness.return_value = [
            {"id": "2026-04-21", "sleepTime": 26100},  # 7h15m
        ]
        with (
            patch(
                "magma_cycling.config.get_withings_config",
                return_value=self._withings_unconfigured(),
            ),
            patch("magma_cycling.config.create_intervals_client", return_value=client),
        ):
            provider = create_health_provider()
        assert isinstance(provider, IntervalsHealthProvider)

    def test_returns_intervals_when_only_older_day_has_sleep(self):
        """Regression test for BT-010 NullProvider: yesterday has no sleep
        (sync delayed / day off) but a day earlier in the week does. The
        previous code probed only yesterday and fell back to NullProvider."""
        client = Mock()
        client.get_wellness.return_value = [
            {"id": "2026-04-15", "sleepTime": 25000},  # day -7: has sleep
            {"id": "2026-04-16", "sleepTime": None},
            {"id": "2026-04-17", "sleepTime": None},
            {"id": "2026-04-18", "sleepTime": None},
            {"id": "2026-04-19", "sleepTime": None},
            {"id": "2026-04-20", "sleepTime": None},
            {"id": "2026-04-21", "sleepTime": None},  # yesterday: no sleep
        ]
        with (
            patch(
                "magma_cycling.config.get_withings_config",
                return_value=self._withings_unconfigured(),
            ),
            patch("magma_cycling.config.create_intervals_client", return_value=client),
        ):
            provider = create_health_provider()
        assert isinstance(provider, IntervalsHealthProvider)

    def test_falls_back_to_null_when_full_week_empty(self):
        """If the entire 7-day window has no sleepTime, NullProvider is the
        right answer (legitimately no Garmin/watch sync configured)."""
        client = Mock()
        client.get_wellness.return_value = [{"id": f"day-{i}", "sleepTime": None} for i in range(7)]
        with (
            patch(
                "magma_cycling.config.get_withings_config",
                return_value=self._withings_unconfigured(),
            ),
            patch("magma_cycling.config.create_intervals_client", return_value=client),
        ):
            provider = create_health_provider()
        assert isinstance(provider, NullProvider)

    def test_falls_back_to_null_when_no_wellness_at_all(self):
        """Empty wellness list (Intervals API returns nothing) → NullProvider."""
        client = Mock()
        client.get_wellness.return_value = []
        with (
            patch(
                "magma_cycling.config.get_withings_config",
                return_value=self._withings_unconfigured(),
            ),
            patch("magma_cycling.config.create_intervals_client", return_value=client),
        ):
            provider = create_health_provider()
        assert isinstance(provider, NullProvider)

    def test_probe_uses_7_day_window(self):
        """Verify get_wellness is called with a 7-day range, not a single day."""
        from datetime import date, timedelta

        client = Mock()
        client.get_wellness.return_value = [{"id": "y", "sleepTime": 25000}]
        with (
            patch(
                "magma_cycling.config.get_withings_config",
                return_value=self._withings_unconfigured(),
            ),
            patch("magma_cycling.config.create_intervals_client", return_value=client),
        ):
            create_health_provider()

        call = client.get_wellness.call_args
        oldest = call.kwargs.get("oldest") or call.args[0]
        newest = call.kwargs.get("newest") or call.args[1]
        expected_oldest = str(date.today() - timedelta(days=7))
        expected_newest = str(date.today() - timedelta(days=1))
        assert oldest == expected_oldest
        assert newest == expected_newest
