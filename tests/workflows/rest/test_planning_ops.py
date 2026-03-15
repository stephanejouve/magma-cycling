"""Tests for workflows/rest/planning_ops.py."""

from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.workflows.rest.planning_ops import (
    load_week_planning,
    validate_week_planning,
)


class TestLoadWeekPlanning:
    """Tests for load_week_planning."""

    @patch("magma_cycling.workflows.rest.planning_ops.planning_tower")
    def test_load_returns_plan(self, mock_tower):
        """Returns WeeklyPlan from Control Tower."""
        mock_plan = MagicMock()
        mock_plan.planned_sessions = [MagicMock(), MagicMock()]
        mock_tower.read_week.return_value = mock_plan

        result = load_week_planning("S090")

        mock_tower.read_week.assert_called_once_with("S090")
        assert result is mock_plan

    @patch("magma_cycling.workflows.rest.planning_ops.planning_tower")
    def test_load_raises_file_not_found(self, mock_tower):
        """Raises FileNotFoundError when planning file missing."""
        mock_tower.read_week.side_effect = FileNotFoundError("not found")

        with pytest.raises(FileNotFoundError, match="Planning non trouvé"):
            load_week_planning("S999")

    @patch("magma_cycling.workflows.rest.planning_ops.planning_tower")
    def test_load_raises_value_error_on_validation(self, mock_tower):
        """Raises ValueError on Pydantic ValidationError."""
        from pydantic import ValidationError

        mock_tower.read_week.side_effect = ValidationError.from_exception_data(
            title="WeeklyPlan", line_errors=[]
        )

        with pytest.raises(ValueError, match="Planning invalide"):
            load_week_planning("S090")

    @patch("magma_cycling.workflows.rest.planning_ops.planning_tower")
    def test_load_ignores_deprecated_planning_dir(self, mock_tower):
        """planning_dir parameter is ignored (deprecated)."""
        mock_plan = MagicMock()
        mock_plan.planned_sessions = []
        mock_tower.read_week.return_value = mock_plan

        result = load_week_planning("S090", planning_dir="/tmp/old")

        assert result is mock_plan


class TestValidateWeekPlanning:
    """Tests for validate_week_planning."""

    def test_validate_weekly_plan_object(self):
        """WeeklyPlan instance is always valid (Pydantic validated)."""
        from datetime import datetime

        from magma_cycling.planning.models import WeeklyPlan

        plan = WeeklyPlan(
            week_id="S090",
            start_date="2026-03-09",
            end_date="2026-03-15",
            created_at=datetime.now(),
            last_updated=datetime.now(),
            version=1,
            athlete_id="i000000",
            tss_target=400,
            planned_sessions=[],
        )
        assert validate_week_planning(plan) is True

    def test_validate_valid_dict(self):
        """Valid dict passes validation."""
        planning = {
            "week_id": "S090",
            "start_date": "2026-03-09",
            "end_date": "2026-03-15",
            "planned_sessions": [
                {
                    "session_id": "S090-01",
                    "date": "2026-03-09",
                    "type": "END",
                    "name": "Endurance",
                    "status": "planned",
                },
            ],
        }
        assert validate_week_planning(planning) is True

    def test_validate_missing_required_field(self):
        """Dict missing required field returns False."""
        planning = {"week_id": "S090"}  # Missing start_date, end_date, sessions
        assert validate_week_planning(planning) is False

    def test_validate_invalid_status(self):
        """Invalid session status returns False."""
        planning = {
            "week_id": "S090",
            "start_date": "2026-03-09",
            "end_date": "2026-03-15",
            "planned_sessions": [
                {
                    "session_id": "S090-01",
                    "date": "2026-03-09",
                    "type": "END",
                    "name": "Test",
                    "status": "INVALID_STATUS",
                },
            ],
        }
        assert validate_week_planning(planning) is False

    def test_validate_cancelled_without_reason(self):
        """Cancelled session without reason returns False."""
        planning = {
            "week_id": "S090",
            "start_date": "2026-03-09",
            "end_date": "2026-03-15",
            "planned_sessions": [
                {
                    "session_id": "S090-01",
                    "date": "2026-03-09",
                    "type": "END",
                    "name": "Test",
                    "status": "cancelled",
                },
            ],
        }
        assert validate_week_planning(planning) is False

    def test_validate_duplicate_session_id(self):
        """Duplicate session IDs returns False."""
        planning = {
            "week_id": "S090",
            "start_date": "2026-03-09",
            "end_date": "2026-03-15",
            "planned_sessions": [
                {
                    "session_id": "S090-01",
                    "date": "2026-03-09",
                    "type": "END",
                    "name": "A",
                    "status": "planned",
                },
                {
                    "session_id": "S090-01",
                    "date": "2026-03-10",
                    "type": "INT",
                    "name": "B",
                    "status": "planned",
                },
            ],
        }
        assert validate_week_planning(planning) is False
