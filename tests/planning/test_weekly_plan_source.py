"""Tests for WeeklyPlan source field."""

import json

from magma_cycling.planning.models import WeeklyPlan


def _make_plan_data(**overrides):
    """Build minimal valid WeeklyPlan data dict."""
    data = {
        "week_id": "S084",
        "start_date": "2026-03-09",
        "end_date": "2026-03-15",
        "created_at": "2026-03-08T20:00:00",
        "last_updated": "2026-03-08T20:00:00",
        "version": 1,
        "athlete_id": "i999999",
        "tss_target": 300,
        "planned_sessions": [
            {
                "session_id": "S084-01",
                "date": "2026-03-09",
                "name": "Endurance",
                "type": "END",
                "tss_planned": 50,
                "duration_min": 60,
                "status": "planned",
            },
        ],
    }
    data.update(overrides)
    return data


class TestWeeklyPlanSourceField:
    """Test source field on WeeklyPlan model."""

    def test_source_field_default_none(self):
        """WeeklyPlan without source field defaults to None."""
        plan = WeeklyPlan(**_make_plan_data())
        assert plan.source is None

    def test_source_field_roundtrip(self, tmp_path):
        """Serialization/deserialization preserves source field."""
        plan = WeeklyPlan(**_make_plan_data(source="mcp"))
        assert plan.source == "mcp"

        json_file = tmp_path / "week_planning_S084.json"
        plan.to_json(json_file)

        loaded = WeeklyPlan.from_json(json_file)
        assert loaded.source == "mcp"

    def test_legacy_json_without_source_loads(self, tmp_path):
        """Legacy JSON without source field loads without error."""
        data = _make_plan_data()
        assert "source" not in data

        json_file = tmp_path / "week_planning_S084.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")

        plan = WeeklyPlan.from_json(json_file)
        assert plan.source is None
        assert len(plan.planned_sessions) == 1
