"""Tests for SessionUpdatesMixin — regex suffix fix + auto-complete rest sessions."""

import json
from datetime import date
from unittest.mock import patch

import pytest

from magma_cycling.planning.control_tower import planning_tower
from magma_cycling.workflows.sync.session_updates import SessionUpdatesMixin


class TestExtractSessionId:
    """Tests for _extract_session_id regex."""

    def setup_method(self):
        self.mixin = SessionUpdatesMixin()

    def test_standard_session_id(self):
        """S079-02 without suffix."""
        result = self.mixin._extract_session_id("S079-02-INT-SweetSpotModere-V001")
        assert result == ("S079", "S079-02")

    def test_session_id_with_suffix(self):
        """S086-06b with letter suffix."""
        result = self.mixin._extract_session_id("S086-06b-INT-ZwiftFTPTestStandard-V001")
        assert result == ("S086", "S086-06b")

    def test_session_id_suffix_a(self):
        """S081-04a with suffix 'a'."""
        result = self.mixin._extract_session_id("S081-04a-END-EnduranceDouce-V001")
        assert result == ("S081", "S081-04a")

    def test_no_match(self):
        """Non-matching activity name returns None."""
        result = self.mixin._extract_session_id("Morning Ride")
        assert result is None

    def test_session_id_no_suffix_still_works(self):
        """Regression: standard IDs without suffix are not broken."""
        result = self.mixin._extract_session_id("S086-06-END-EnduranceDouce-V001")
        assert result == ("S086", "S086-06")


class TestAutoCompleteRestSessions:
    """Tests for auto_complete_rest_sessions."""

    @pytest.fixture
    def mock_tower(self, tmp_path):
        """Mock Control Tower to use tmp_path."""
        original_dir = planning_tower.planning_dir
        original_backup_dir = planning_tower.backup_system.planning_dir

        planning_tower.planning_dir = tmp_path
        planning_tower.backup_system.planning_dir = tmp_path

        yield tmp_path

        planning_tower.planning_dir = original_dir
        planning_tower.backup_system.planning_dir = original_backup_dir

    def _write_planning(self, tmp_path, week_id, sessions, start_date="2026-03-23"):
        """Helper to write a planning JSON file."""
        # Compute end_date as start + 6 days
        from datetime import date as d
        from datetime import timedelta

        sd = d.fromisoformat(start_date)
        ed = (sd + timedelta(days=6)).isoformat()
        planning_data = {
            "week_id": week_id,
            "start_date": start_date,
            "end_date": ed,
            "created_at": "2026-03-01T00:00:00Z",
            "last_updated": "2026-03-01T00:00:00Z",
            "version": 1,
            "athlete_id": "iXXXXXX",
            "tss_target": 300,
            "planned_sessions": sessions,
        }
        planning_file = tmp_path / f"week_planning_{week_id}.json"
        with open(planning_file, "w", encoding="utf-8") as f:
            json.dump(planning_data, f, indent=2)
        return planning_file

    def test_rest_session_past_date_completed(self, mock_tower):
        """Rest session (TSS=0, dur=0) with past date → completed."""
        self._write_planning(
            mock_tower,
            "S086",
            [
                {
                    "session_id": "S086-01",
                    "date": "2026-03-23",
                    "name": "Repos",
                    "type": "REC",
                    "version": "V001",
                    "tss_planned": 0,
                    "duration_min": 0,
                    "description": "",
                    "status": "planned",
                },
            ],
        )

        mixin = SessionUpdatesMixin()
        check_date = date(2026, 3, 31)

        with patch(
            "magma_cycling.daily_sync.calculate_current_week_info",
            return_value=("S086", date(2026, 3, 23)),
        ):
            result = mixin.auto_complete_rest_sessions(check_date)

        assert result == ["S086-01"]

        # Verify persisted
        from magma_cycling.planning.models import WeeklyPlan

        plan = WeeklyPlan.from_json(mock_tower / "week_planning_S086.json")
        assert plan.planned_sessions[0].status == "completed"

    def test_rest_session_future_date_stays_planned(self, mock_tower):
        """Rest session with future date → remains planned."""
        self._write_planning(
            mock_tower,
            "S086",
            [
                {
                    "session_id": "S086-07",
                    "date": "2026-03-29",
                    "name": "Repos",
                    "type": "REC",
                    "version": "V001",
                    "tss_planned": 0,
                    "duration_min": 0,
                    "description": "",
                    "status": "planned",
                },
            ],
        )

        mixin = SessionUpdatesMixin()
        check_date = date(2026, 3, 25)  # Before session date

        with patch(
            "magma_cycling.daily_sync.calculate_current_week_info",
            return_value=("S086", date(2026, 3, 23)),
        ):
            result = mixin.auto_complete_rest_sessions(check_date)

        assert result == []

        from magma_cycling.planning.models import WeeklyPlan

        plan = WeeklyPlan.from_json(mock_tower / "week_planning_S086.json")
        assert plan.planned_sessions[0].status == "planned"

    def test_rec_session_with_tss_stays_unchanged(self, mock_tower):
        """REC session with TSS > 0 is NOT a rest day, stays planned."""
        self._write_planning(
            mock_tower,
            "S086",
            [
                {
                    "session_id": "S086-05",
                    "date": "2026-03-27",
                    "name": "RecupActive",
                    "type": "REC",
                    "version": "V001",
                    "tss_planned": 30,
                    "duration_min": 45,
                    "description": "Recup active",
                    "status": "planned",
                },
            ],
        )

        mixin = SessionUpdatesMixin()
        check_date = date(2026, 3, 31)

        with patch(
            "magma_cycling.daily_sync.calculate_current_week_info",
            return_value=("S086", date(2026, 3, 23)),
        ):
            result = mixin.auto_complete_rest_sessions(check_date)

        assert result == []

        from magma_cycling.planning.models import WeeklyPlan

        plan = WeeklyPlan.from_json(mock_tower / "week_planning_S086.json")
        assert plan.planned_sessions[0].status == "planned"

    def test_already_completed_not_touched(self, mock_tower):
        """Already completed rest session is not re-processed."""
        self._write_planning(
            mock_tower,
            "S086",
            [
                {
                    "session_id": "S086-01",
                    "date": "2026-03-23",
                    "name": "Repos",
                    "type": "REC",
                    "version": "V001",
                    "tss_planned": 0,
                    "duration_min": 0,
                    "description": "",
                    "status": "completed",
                },
            ],
        )

        mixin = SessionUpdatesMixin()
        check_date = date(2026, 3, 31)

        with patch(
            "magma_cycling.daily_sync.calculate_current_week_info",
            return_value=("S086", date(2026, 3, 23)),
        ):
            result = mixin.auto_complete_rest_sessions(check_date)

        assert result == []

    def test_previous_week_also_checked(self, mock_tower):
        """Previous week rest sessions are also auto-completed."""
        self._write_planning(
            mock_tower,
            "S085",
            [
                {
                    "session_id": "S085-01",
                    "date": "2026-03-16",
                    "name": "Repos",
                    "type": "REC",
                    "version": "V001",
                    "tss_planned": 0,
                    "duration_min": 0,
                    "description": "",
                    "status": "planned",
                },
            ],
            start_date="2026-03-16",
        )
        self._write_planning(
            mock_tower,
            "S086",
            [
                {
                    "session_id": "S086-03",
                    "date": "2026-03-25",
                    "name": "Repos",
                    "type": "REC",
                    "version": "V001",
                    "tss_planned": 0,
                    "duration_min": 0,
                    "description": "",
                    "status": "planned",
                },
            ],
        )

        mixin = SessionUpdatesMixin()
        check_date = date(2026, 3, 31)

        with patch(
            "magma_cycling.daily_sync.calculate_current_week_info",
            return_value=("S086", date(2026, 3, 23)),
        ):
            result = mixin.auto_complete_rest_sessions(check_date)

        assert "S086-03" in result
        assert "S085-01" in result
