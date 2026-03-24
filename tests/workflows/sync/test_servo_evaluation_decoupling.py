"""Tests for decoupling recalculation in ServoEvaluationMixin."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.workflows.sync.servo_evaluation import ServoEvaluationMixin


class _FakeSync(ServoEvaluationMixin):
    """Minimal stand-in for DailySync to test the mixin."""

    def __init__(self, client=None):
        self.client = client or MagicMock()
        self.servo_criteria = {
            "decoupling_threshold": 7.5,
            "sleep_threshold_hours": 7.0,
            "feel_threshold": 4,
            "tsb_threshold": -10,
        }


def _make_plan(sessions):
    """Create a mock WeeklyPlan with given sessions."""
    plan = MagicMock()
    plan.planned_sessions = sessions
    return plan


def _make_session(session_date, duration_min=60, tss_planned=50):
    """Create a mock Session."""
    s = MagicMock()
    s.session_date = session_date
    s.duration_min = duration_min
    s.tss_planned = tss_planned
    return s


def _make_streams(watts_data, hr_data):
    """Create streams list matching Intervals.icu API format."""
    return [
        {"type": "watts", "data": watts_data},
        {"type": "heartrate", "data": hr_data},
    ]


class TestDecouplingRecalculatedWhenOvertime:
    """Test that decoupling is recalculated when activity duration exceeds prescribed."""

    def test_recalculated_when_overtime(self):
        """Overtime >15% triggers decoupling recalculation on prescribed window."""
        client = MagicMock()
        # 4500s of constant data (75min actual, 60min prescribed → 25% overtime)
        watts = [200.0] * 4500
        hr = [140.0] * 4500
        client.get_activity_streams.return_value = _make_streams(watts, hr)

        sync = _FakeSync(client=client)

        activity = {
            "id": "i123",
            "start_date_local": "2026-03-24T10:00:00",
            "icu_training_load": 75,
            "moving_time": 4500,  # 75min
            "decoupling": 11.9,
            "feel": None,
        }

        session = _make_session(date(2026, 3, 24), duration_min=60)
        plan = _make_plan([session])

        with patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower:
            mock_tower.read_week.return_value = plan

            metrics = sync.extract_metrics_from_activity(
                activity, analysis=None, wellness_pre=None, week_id="S086"
            )

        # Prescribed decoupling should be set (recalculated on 60min window)
        assert metrics["decoupling_prescribed"] is not None
        assert metrics["duration_planned_min"] == 60
        assert metrics["tss_planned"] == 50
        # Raw API decoupling preserved
        assert metrics["decoupling"] == 11.9
        # Overtime analysis should be present
        assert metrics["overtime_analysis"] is not None
        assert metrics["overtime_analysis"]["duration_extra_min"] > 0


class TestDecouplingKeptWhenNormalDuration:
    """Test that no recalculation happens when duration is within tolerance."""

    def test_no_recalculation_for_normal_duration(self):
        """Activity within 15% of prescribed → no recalculation."""
        client = MagicMock()
        sync = _FakeSync(client=client)

        activity = {
            "id": "i456",
            "start_date_local": "2026-03-24T10:00:00",
            "icu_training_load": 50,
            "moving_time": 3900,  # 65min (< 60 * 1.15 = 69min)
            "decoupling": 3.2,
        }

        session = _make_session(date(2026, 3, 24), duration_min=60)
        plan = _make_plan([session])

        with patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower:
            mock_tower.read_week.return_value = plan

            metrics = sync.extract_metrics_from_activity(
                activity, analysis=None, wellness_pre=None, week_id="S086"
            )

        # No recalculation — streams should NOT be fetched
        client.get_activity_streams.assert_not_called()
        assert metrics["decoupling_prescribed"] is None
        assert metrics["decoupling"] == 3.2
        assert metrics["overtime_analysis"] is None


class TestOvertimeAnalysisPassedToMetrics:
    """Test that overtime analysis dict is populated correctly."""

    def test_overtime_analysis_populated(self):
        """Overtime metrics include duration, power, HR."""
        client = MagicMock()
        prescribed_s = 3600  # 60min
        total_s = 4500  # 75min → 15min extension
        watts = [200.0] * prescribed_s + [100.0] * (total_s - prescribed_s)
        hr = [140.0] * prescribed_s + [120.0] * (total_s - prescribed_s)
        client.get_activity_streams.return_value = _make_streams(watts, hr)

        sync = _FakeSync(client=client)

        activity = {
            "id": "i789",
            "start_date_local": "2026-03-24T10:00:00",
            "icu_training_load": 80,
            "moving_time": total_s,
            "decoupling": 8.5,
        }

        session = _make_session(date(2026, 3, 24), duration_min=60)
        plan = _make_plan([session])

        with patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower:
            mock_tower.read_week.return_value = plan

            metrics = sync.extract_metrics_from_activity(
                activity, analysis=None, wellness_pre=None, week_id="S086"
            )

        ot = metrics["overtime_analysis"]
        assert ot is not None
        assert ot["duration_extra_min"] == pytest.approx(15.0, abs=0.5)
        assert ot["avg_power_watts"] == pytest.approx(100.0, abs=1.0)
        assert ot["avg_hr_bpm"] == pytest.approx(120.0, abs=1.0)


class TestServoUsesPrescribedDecoupling:
    """Test that servo trigger uses prescribed decoupling value."""

    def test_servo_uses_prescribed_value(self):
        """Seuil 7.5% applied to prescribed decoupling, not raw."""
        sync = _FakeSync()

        # Raw decoupling is 11.9% (would trigger)
        # But prescribed is 3.8% (below threshold)
        metrics = {
            "decoupling": 11.9,
            "decoupling_prescribed": 3.8,
            "sleep_hours": 8.0,
            "feel": 2,
            "tsb": 5,
            "overtime_analysis": None,
            "duration_planned_min": 60,
        }

        triggered, reasons = sync.should_trigger_servo(metrics)

        assert triggered is False
        assert reasons == []

    def test_servo_triggers_on_high_prescribed_decoupling(self):
        """Prescribed decoupling above threshold still triggers."""
        sync = _FakeSync()

        metrics = {
            "decoupling": 14.0,
            "decoupling_prescribed": 9.2,
            "sleep_hours": 8.0,
            "feel": 2,
            "tsb": 5,
            "overtime_analysis": None,
            "duration_planned_min": 60,
        }

        triggered, reasons = sync.should_trigger_servo(metrics)

        assert triggered is True
        assert any("9.2%" in r for r in reasons)
        assert any("prescrits" in r for r in reasons)

    def test_servo_falls_back_to_raw_when_no_prescribed(self):
        """Without prescribed value, uses raw decoupling from API."""
        sync = _FakeSync()

        metrics = {
            "decoupling": 8.5,
            "decoupling_prescribed": None,
            "sleep_hours": 8.0,
            "feel": 2,
            "tsb": 5,
            "overtime_analysis": None,
        }

        triggered, reasons = sync.should_trigger_servo(metrics)

        assert triggered is True
        assert any("8.5%" in r for r in reasons)


class TestDecouplingFallbackWhenNoStreams:
    """Test fallback behavior when streams are unavailable."""

    def test_fallback_when_streams_unavailable(self):
        """Overtime detected but streams fetch fails → fallback to API value."""
        client = MagicMock()
        client.get_activity_streams.side_effect = Exception("API error")

        sync = _FakeSync(client=client)

        activity = {
            "id": "i999",
            "start_date_local": "2026-03-24T10:00:00",
            "icu_training_load": 80,
            "moving_time": 4500,  # 75min, prescribed 60min → overtime
            "decoupling": 11.0,
        }

        session = _make_session(date(2026, 3, 24), duration_min=60)
        plan = _make_plan([session])

        with patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower:
            mock_tower.read_week.return_value = plan

            metrics = sync.extract_metrics_from_activity(
                activity, analysis=None, wellness_pre=None, week_id="S086"
            )

        # Fallback: no prescribed recalculation, raw value preserved
        assert metrics["decoupling_prescribed"] is None
        assert metrics["decoupling"] == 11.0
        assert metrics["overtime_analysis"] is None

    def test_fallback_when_no_planning(self):
        """Planning file not found → fallback to API value."""
        sync = _FakeSync()

        activity = {
            "id": "i888",
            "start_date_local": "2026-03-24T10:00:00",
            "icu_training_load": 80,
            "moving_time": 4500,
            "decoupling": 10.5,
        }

        with patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower:
            mock_tower.read_week.side_effect = FileNotFoundError("Not found")

            metrics = sync.extract_metrics_from_activity(
                activity, analysis=None, wellness_pre=None, week_id="S086"
            )

        assert metrics["decoupling_prescribed"] is None
        assert metrics["decoupling"] == 10.5

    def test_fallback_when_empty_streams(self):
        """Streams returned but empty → fallback."""
        client = MagicMock()
        client.get_activity_streams.return_value = []

        sync = _FakeSync(client=client)

        activity = {
            "id": "i777",
            "start_date_local": "2026-03-24T10:00:00",
            "icu_training_load": 80,
            "moving_time": 4500,
            "decoupling": 9.0,
        }

        session = _make_session(date(2026, 3, 24), duration_min=60)
        plan = _make_plan([session])

        with patch("magma_cycling.planning.control_tower.planning_tower") as mock_tower:
            mock_tower.read_week.return_value = plan

            metrics = sync.extract_metrics_from_activity(
                activity, analysis=None, wellness_pre=None, week_id="S086"
            )

        assert metrics["decoupling_prescribed"] is None
        assert metrics["decoupling"] == 9.0
