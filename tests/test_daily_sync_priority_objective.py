"""Test that DailySync.run() forwards priority_objective to run_servo_adjustment.

Closes the wiring gap pointed by Leader's REQUEST_CHANGES (review 4445196860)
on PR #406 — without this, the helper added by issue #401 PR 3 would be
silently dormant in prod because `daily_sync.py:278` never passed the new
`priority_objective` kwarg.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

MODULE = "magma_cycling.daily_sync"


@pytest.fixture
def sync(tmp_path):
    """Create a minimal DailySync instance with auto-servo enabled and deps mocked."""
    with (
        patch(f"{MODULE}.create_intervals_client") as mock_client_factory,
        patch(f"{MODULE}.ActivityTracker"),
    ):
        from magma_cycling.daily_sync import DailySync

        mock_client_factory.return_value = MagicMock()
        s = DailySync(
            tracking_file=tmp_path / "tracking.json",
            reports_dir=tmp_path / "reports",
            enable_ai_analysis=False,
            enable_auto_servo=False,
            verbose=False,
        )
        s.client = MagicMock()
        return s


def _arm_servo_trigger(sync, activity):
    """Wire the minimum state to reach the servo branch in DailySync.run."""
    sync.enable_ai_analysis = True
    sync.enable_auto_servo = True
    sync.check_activities = MagicMock(return_value=([activity], []))
    sync.analyze_activity = MagicMock(return_value="analysis")
    sync.client.get_wellness.return_value = [{"ctl": 50}]
    sync.extract_metrics_from_activity = MagicMock(return_value={"decoupling": 10})
    sync.should_trigger_servo = MagicMock(return_value=(True, ["High decoupling"]))
    sync.generate_report = MagicMock(return_value=Path("/tmp/r.md"))


class TestDailySyncForwardsPriorityObjective:
    """Auto-servo loads the priority objective and passes it to the servo run."""

    def test_servo_receives_build_phase_objective(self, sync):
        activity = {"id": "i111", "name": "TMP", "start_date_local": "2026-06-15T10:00:00"}
        _arm_servo_trigger(sync, activity)
        captured = {}

        def fake_servo(**kwargs):
            captured.update(kwargs)
            return {"adjusted": True}

        sync.run_servo_adjustment = MagicMock(side_effect=fake_servo)

        fake_po = {
            "name": "Les Copains 81km",
            "type": "granfondo",
            "target_date": "2026-07-04",
            "days_until_target": 15,
        }
        with patch(
            "magma_cycling.config.objectives.load_priority_objective_as_dict",
            return_value=fake_po,
        ):
            sync.run(check_date=date(2026, 6, 15), week_id="S099")

        sync.run_servo_adjustment.assert_called_once()
        assert captured.get("priority_objective") == fake_po

    def test_servo_receives_none_when_no_objective_set(self, sync):
        activity = {"id": "i112", "name": "TMP", "start_date_local": "2026-06-15T10:00:00"}
        _arm_servo_trigger(sync, activity)
        captured = {}

        def fake_servo(**kwargs):
            captured.update(kwargs)
            return None

        sync.run_servo_adjustment = MagicMock(side_effect=fake_servo)

        with patch(
            "magma_cycling.config.objectives.load_priority_objective_as_dict",
            return_value=None,
        ):
            sync.run(check_date=date(2026, 6, 15), week_id="S099")

        sync.run_servo_adjustment.assert_called_once()
        assert captured.get("priority_objective") is None

    def test_priority_objective_load_is_skipped_when_servo_does_not_trigger(self, sync):
        """No PO lookup when should_trigger_servo returns False — avoid unnecessary I/O."""
        activity = {"id": "i113", "name": "Z2", "start_date_local": "2026-06-15T10:00:00"}
        sync.enable_ai_analysis = True
        sync.enable_auto_servo = True
        sync.check_activities = MagicMock(return_value=([activity], []))
        sync.analyze_activity = MagicMock(return_value=None)
        sync.client.get_wellness.return_value = [{"ctl": 50}]
        sync.extract_metrics_from_activity = MagicMock(return_value={})
        sync.should_trigger_servo = MagicMock(return_value=(False, []))
        sync.run_servo_adjustment = MagicMock()
        sync.generate_report = MagicMock(return_value=Path("/tmp/r.md"))

        with patch("magma_cycling.config.objectives.load_priority_objective_as_dict") as mock_load:
            sync.run(check_date=date(2026, 6, 15), week_id="S099")

        sync.run_servo_adjustment.assert_not_called()
        mock_load.assert_not_called()
