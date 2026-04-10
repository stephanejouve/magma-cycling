"""Tests for WeekReferenceConfig.get_s001_for_date()."""

import json
from datetime import date

import pytest

from magma_cycling.config.week_reference import WeekReferenceConfig


@pytest.fixture
def single_season_config(tmp_path):
    """Single-season (legacy) config."""
    config = {
        "week_reference": {
            "s001_date": "2024-08-05",
            "description": "Test season",
            "season": "2024-2025",
        }
    }
    config_file = tmp_path / ".config.json"
    config_file.write_text(json.dumps(config))
    return WeekReferenceConfig(data_repo_path=tmp_path)


@pytest.fixture
def multi_season_config(tmp_path):
    """Multi-season config with two seasons."""
    config = {
        "week_reference": {
            "seasons": {
                "2024-2025": {
                    "s001_date": "2024-08-05",
                    "global_week_start": 1,
                    "global_week_end": 74,
                },
                "2026": {
                    "s001_date": "2026-01-05",
                    "global_week_start": 75,
                    "global_week_end": None,
                },
            },
            "active_season": "2026",
        }
    }
    config_file = tmp_path / ".config.json"
    config_file.write_text(json.dumps(config))
    return WeekReferenceConfig(data_repo_path=tmp_path)


class TestGetS001ForDate:
    """Tests for get_s001_for_date()."""

    def test_single_season_returns_s001(self, single_season_config):
        """Single-season config returns the only season."""
        s001, week_start = single_season_config.get_s001_for_date(date(2025, 3, 15))
        assert s001 == date(2024, 8, 5)
        assert week_start == 1

    def test_multi_season_first_season(self, multi_season_config):
        """Date in first season returns first season's s001."""
        s001, week_start = multi_season_config.get_s001_for_date(date(2025, 6, 15))
        assert s001 == date(2024, 8, 5)
        assert week_start == 1

    def test_multi_season_second_season(self, multi_season_config):
        """Date in second season returns second season's s001."""
        s001, week_start = multi_season_config.get_s001_for_date(date(2026, 3, 15))
        assert s001 == date(2026, 1, 5)
        assert week_start == 75

    def test_multi_season_exact_boundary(self, multi_season_config):
        """Date exactly on season 2 s001 returns season 2."""
        s001, week_start = multi_season_config.get_s001_for_date(date(2026, 1, 5))
        assert s001 == date(2026, 1, 5)
        assert week_start == 75

    def test_multi_season_day_before_season2(self, multi_season_config):
        """Date one day before season 2 returns season 1."""
        s001, week_start = multi_season_config.get_s001_for_date(date(2026, 1, 4))
        assert s001 == date(2024, 8, 5)
        assert week_start == 1

    def test_date_before_all_seasons_fallback(self, multi_season_config):
        """Date before all seasons falls back to first season."""
        s001, week_start = multi_season_config.get_s001_for_date(date(2024, 1, 1))
        assert s001 == date(2024, 8, 5)
        assert week_start == 1

    def test_single_season_week_calculation(self, single_season_config):
        """Verify week calculation with single-season returns correct week IDs."""
        # S001 reference = 2024-08-05
        s001, week_start = single_season_config.get_s001_for_date(date(2024, 8, 5))
        weeks_offset = (date(2024, 8, 5) - s001).days // 7
        week_id = f"S{weeks_offset + week_start:03d}"
        assert week_id == "S001"

    def test_multi_season_week_calculation(self, multi_season_config):
        """Verify week calculation with multi-season returns correct week IDs."""
        target = date(2026, 3, 9)  # Monday, 9 weeks after 2026-01-05
        s001, week_start = multi_season_config.get_s001_for_date(target)
        weeks_offset = (target - s001).days // 7
        week_id = f"S{weeks_offset + week_start:03d}"
        assert week_id == "S084"
