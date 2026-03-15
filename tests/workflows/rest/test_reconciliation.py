"""Tests for workflows/rest/reconciliation.py."""

from magma_cycling.workflows.rest.reconciliation import reconcile_planned_vs_actual


def _make_session(session_id, date, status, name="Test"):
    """Helper to create session dict."""
    return {
        "session_id": session_id,
        "date": date,
        "type": "END",
        "name": name,
        "status": status,
    }


def _make_activity(date, name="Activity"):
    """Helper to create activity dict."""
    return {"start_date_local": f"{date}T10:00:00", "name": name}


class TestReconcilePlannedVsActual:
    """Tests for reconcile_planned_vs_actual."""

    def test_matched_session(self):
        """Completed session matched with activity."""
        planning = {
            "week_id": "S090",
            "planned_sessions": [_make_session("S090-01", "2026-03-09", "completed")],
        }
        activities = [_make_activity("2026-03-09")]

        result = reconcile_planned_vs_actual(planning, activities)

        assert len(result["matched"]) == 1
        assert result["matched"][0]["activity"] is activities[0]

    def test_rest_day(self):
        """Rest day session categorized correctly."""
        planning = {
            "week_id": "S090",
            "planned_sessions": [_make_session("S090-01", "2026-03-09", "rest_day")],
        }

        result = reconcile_planned_vs_actual(planning, [])

        assert len(result["rest_days"]) == 1

    def test_cancelled_session(self):
        """Cancelled session categorized correctly."""
        planning = {
            "week_id": "S090",
            "planned_sessions": [_make_session("S090-01", "2026-03-09", "cancelled")],
        }

        result = reconcile_planned_vs_actual(planning, [])

        assert len(result["cancelled"]) == 1

    def test_skipped_session(self):
        """Skipped session categorized correctly."""
        planning = {
            "week_id": "S090",
            "planned_sessions": [_make_session("S090-01", "2026-03-09", "skipped")],
        }

        result = reconcile_planned_vs_actual(planning, [])

        assert len(result["skipped"]) == 1

    def test_unplanned_activity(self):
        """Activity on unplanned date is unplanned."""
        planning = {
            "week_id": "S090",
            "planned_sessions": [_make_session("S090-01", "2026-03-09", "rest_day")],
        }
        activities = [_make_activity("2026-03-10", "Bonus Ride")]

        result = reconcile_planned_vs_actual(planning, activities)

        assert len(result["unplanned"]) == 1

    def test_completed_without_activity_reclassed_skipped(self):
        """Completed session without matching activity reclassed as skipped."""
        planning = {
            "week_id": "S090",
            "planned_sessions": [_make_session("S090-01", "2026-03-09", "completed")],
        }

        result = reconcile_planned_vs_actual(planning, [])

        assert len(result["skipped"]) == 1
        assert len(result["matched"]) == 0
