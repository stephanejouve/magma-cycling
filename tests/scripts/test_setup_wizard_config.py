"""Tests for setup_wizard .config.json generation."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from magma_cycling.scripts.setup_wizard import (
    _create_week_reference_config,
    _monday_of_current_week,
)


class TestMondayOfCurrentWeek:
    def test_monday_returns_itself(self):
        monday = date(2026, 4, 13)  # lundi
        assert _monday_of_current_week(monday) == monday

    def test_sunday_returns_previous_monday(self):
        sunday = date(2026, 4, 19)  # dimanche
        assert _monday_of_current_week(sunday) == date(2026, 4, 13)

    def test_wednesday_returns_monday_of_same_week(self):
        wednesday = date(2026, 4, 15)
        assert _monday_of_current_week(wednesday) == date(2026, 4, 13)

    def test_default_uses_today(self):
        # Just verify no exception; actual value depends on wall clock
        result = _monday_of_current_week()
        assert result.weekday() == 0


class TestCreateWeekReferenceConfig:
    def test_creates_file_with_multi_season_structure(self, tmp_path: Path):
        created = _create_week_reference_config(tmp_path, athlete_id="i12345", name="Alice")
        assert created is True

        config_path = tmp_path / ".config.json"
        assert config_path.exists()
        payload = json.loads(config_path.read_text())

        assert payload["athlete_id"] == "i12345"
        assert payload["name"] == "Alice"
        assert "week_reference" in payload
        assert "seasons" in payload["week_reference"]
        assert "initial" in payload["week_reference"]["seasons"]

        season = payload["week_reference"]["seasons"]["initial"]
        assert "s001_date" in season
        assert season["global_week_start"] == 1
        assert season["global_week_end"] is None

        assert payload["week_reference"]["active_season"] == "initial"

        assert payload["intervals_config"]["athlete_id"] == "i12345"
        assert payload["intervals_config"]["base_url"] == "https://intervals.icu/api/v1"

    def test_s001_defaults_to_monday_of_current_week(self, tmp_path: Path):
        _create_week_reference_config(tmp_path, "i1", "X")
        payload = json.loads((tmp_path / ".config.json").read_text())
        s001 = date.fromisoformat(payload["week_reference"]["seasons"]["initial"]["s001_date"])
        assert s001.weekday() == 0  # Monday

    def test_custom_s001_date_respected(self, tmp_path: Path):
        custom = date(2026, 1, 5)
        _create_week_reference_config(tmp_path, "i1", "X", s001_date=custom)
        payload = json.loads((tmp_path / ".config.json").read_text())
        assert payload["week_reference"]["seasons"]["initial"]["s001_date"] == "2026-01-05"

    def test_idempotent_does_not_overwrite(self, tmp_path: Path):
        # First creation
        _create_week_reference_config(tmp_path, "i1", "X")
        original = (tmp_path / ".config.json").read_text()

        # Second call with different args
        created_again = _create_week_reference_config(tmp_path, athlete_id="i_DIFFERENT", name="Y")
        assert created_again is False  # not recreated

        # Content unchanged
        assert (tmp_path / ".config.json").read_text() == original

    def test_file_valid_for_WeekReferenceConfig_loader(self, tmp_path: Path):
        """Generated file must be readable by the real WeekReferenceConfig."""
        from magma_cycling.config.week_reference import WeekReferenceConfig

        _create_week_reference_config(tmp_path, "i1", "Alice")
        cfg = WeekReferenceConfig(data_repo_path=tmp_path)
        # Should not raise
        assert cfg.active_season == "initial"
        assert "initial" in cfg.seasons
        # s001 date should be a valid Monday
        s001_str = cfg.seasons["initial"]["s001_date"]
        s001 = date.fromisoformat(s001_str)
        assert s001.weekday() == 0

    def test_final_newline_in_file(self, tmp_path: Path):
        _create_week_reference_config(tmp_path, "i1", "X")
        content = (tmp_path / ".config.json").read_text()
        assert content.endswith("\n")


class TestCreateConfigIntegratedInInitDataRepo:
    """_init_data_repo should create .config.json when athlete info is passed."""

    def test_creates_config_on_fresh_init(self, tmp_path: Path):
        from magma_cycling.scripts.setup_wizard import _init_data_repo

        repo = tmp_path / "training-logs"
        _init_data_repo(repo, athlete_id="i42", name="Bob")

        assert (repo / ".config.json").exists()
        payload = json.loads((repo / ".config.json").read_text())
        assert payload["athlete_id"] == "i42"

    def test_no_config_when_athlete_id_missing(self, tmp_path: Path):
        from magma_cycling.scripts.setup_wizard import _init_data_repo

        repo = tmp_path / "training-logs"
        _init_data_repo(repo)  # no athlete info
        assert not (repo / ".config.json").exists()

    def test_idempotent_on_pre_existing_repo(self, tmp_path: Path):
        """Pre-existing repo without .config.json gets one on next run."""
        from magma_cycling.scripts.setup_wizard import _init_data_repo

        repo = tmp_path / "training-logs"
        repo.mkdir()
        (repo / "workouts-history.md").write_text("# exists\n")
        (repo / ".workflow_state.json").write_text("{}")

        assert not (repo / ".config.json").exists()

        _init_data_repo(repo, athlete_id="i99", name="Charlie")

        assert (repo / ".config.json").exists()
