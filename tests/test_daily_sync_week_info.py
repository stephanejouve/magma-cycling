"""Tests for daily_sync.calculate_current_week_info().

Fonction pure standalone : calcul week-id et start date à partir d'une date cible.
"""

from datetime import date
from unittest.mock import MagicMock, patch

from magma_cycling.daily_sync import calculate_current_week_info


@patch("magma_cycling.daily_sync.get_week_config")
class TestCalculateCurrentWeekInfo:
    """Tests for calculate_current_week_info()."""

    def _setup_mock(self, mock_config, s001_date=date(2024, 10, 28)):
        """Helper to setup mock week config with S001 reference date."""
        config = MagicMock()
        config.get_s001_date_obj.return_value = s001_date
        mock_config.return_value = config

    def test_s001_reference_date(self, mock_config):
        self._setup_mock(mock_config, s001_date=date(2024, 10, 28))
        week_id, start_date = calculate_current_week_info(date(2024, 10, 28))
        assert week_id == "S001"
        assert start_date == date(2024, 10, 28)

    def test_second_week(self, mock_config):
        self._setup_mock(mock_config, s001_date=date(2024, 10, 28))
        week_id, start_date = calculate_current_week_info(date(2024, 11, 4))
        assert week_id == "S002"
        assert start_date == date(2024, 11, 4)

    def test_mid_week(self, mock_config):
        self._setup_mock(mock_config, s001_date=date(2024, 10, 28))
        # Wednesday of week 1
        week_id, start_date = calculate_current_week_info(date(2024, 10, 30))
        assert week_id == "S001"
        assert start_date == date(2024, 10, 28)

    def test_high_week_number(self, mock_config):
        self._setup_mock(mock_config, s001_date=date(2024, 10, 28))
        # ~74 weeks later
        week_id, start_date = calculate_current_week_info(date(2026, 3, 16))
        assert week_id.startswith("S0")
        # Verify it's a valid week number
        week_num = int(week_id[1:])
        assert week_num > 70

    def test_start_date_is_monday(self, mock_config):
        self._setup_mock(mock_config, s001_date=date(2024, 10, 28))
        # Any date should return a start_date that's a Monday
        _, start_date = calculate_current_week_info(date(2026, 3, 12))  # Thursday
        assert start_date.weekday() == 0  # Monday

    def test_default_date_is_today(self, mock_config):
        self._setup_mock(mock_config, s001_date=date(2024, 10, 28))
        week_id, start_date = calculate_current_week_info()
        assert week_id.startswith("S")
        assert start_date <= date.today()
