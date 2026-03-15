"""Tests for CycleMetricsAggregationMixin."""

from datetime import date
from unittest.mock import MagicMock

from magma_cycling.workflows.pid_eval.adherence import AdherenceMixin
from magma_cycling.workflows.pid_eval.cardiovascular import CardiovascularQualityMixin
from magma_cycling.workflows.pid_eval.cycle_metrics import CycleMetricsAggregationMixin
from magma_cycling.workflows.pid_eval.tss_capacity import TSSCapacityMixin


class StubMetrics(
    CycleMetricsAggregationMixin,
    AdherenceMixin,
    CardiovascularQualityMixin,
    TSSCapacityMixin,
):
    """Stub combining all data source mixins with aggregation."""

    def __init__(self):
        """Initialize stub."""
        self.client = MagicMock()
        self.adherence_file = MagicMock()
        self.adherence_file.exists.return_value = False
        self.workouts_history = MagicMock()
        self.workouts_history.exists.return_value = False


class TestCalculateCycleMetrics:
    """Tests for calculate_cycle_metrics."""

    def test_returns_all_expected_keys(self):
        """Result dict contains all required keys."""
        stub = StubMetrics()
        stub.client.get_events.return_value = []
        stub.client.get_activities.return_value = []
        result = stub.calculate_cycle_metrics(date(2026, 1, 1), date(2026, 1, 7))
        expected_keys = {
            "adherence_rate",
            "avg_cardiovascular_coupling",
            "tss_completion_rate",
            "days_with_data",
            "total_workouts",
        }
        assert expected_keys == set(result.keys())

    def test_no_data_defaults(self):
        """Empty data sources produce sensible defaults."""
        stub = StubMetrics()
        stub.client.get_events.return_value = []
        stub.client.get_activities.return_value = []
        result = stub.calculate_cycle_metrics(date(2026, 1, 1), date(2026, 1, 7))
        assert result["adherence_rate"] == 1.0  # no planned = 100%
        assert result["avg_cardiovascular_coupling"] == 0.05  # default
        assert result["tss_completion_rate"] == 1.0  # no planned = 100%
        assert result["days_with_data"] == 0
        assert result["total_workouts"] == 0

    def test_adherence_rate_calculation(self, tmp_path):
        """Adherence rate calculated correctly from records."""
        import json

        adherence_file = tmp_path / "adherence.jsonl"
        records = [
            {"date": "2026-01-10", "planned_workouts": 2, "completed_activities": 2},
            {"date": "2026-01-11", "planned_workouts": 1, "completed_activities": 0},
        ]
        with open(adherence_file, "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        stub = StubMetrics()
        stub.adherence_file = adherence_file
        stub.client.get_events.return_value = []
        stub.client.get_activities.return_value = []

        result = stub.calculate_cycle_metrics(date(2026, 1, 1), date(2026, 1, 31))
        # 2 completed / 3 planned = 0.667
        assert abs(result["adherence_rate"] - 2 / 3) < 0.01

    def test_coupling_integrated(self, tmp_path):
        """Cardiovascular coupling values integrated when available."""
        week_dir = tmp_path / "S073"
        week_dir.mkdir()
        (week_dir / "workout_history_S073.md").write_text("Découplage 6.0%\n")

        stub = StubMetrics()
        stub.workouts_history = tmp_path
        stub.client.get_events.return_value = []
        stub.client.get_activities.return_value = []

        result = stub.calculate_cycle_metrics(date(2026, 1, 1), date(2026, 1, 31))
        assert abs(result["avg_cardiovascular_coupling"] - 0.06) < 0.01

    def test_tss_completion_integrated(self):
        """TSS completion rate from API integrated correctly."""
        stub = StubMetrics()
        stub.client.get_events.return_value = [
            {"category": "WORKOUT", "name": "Endurance", "icu_training_load": 200},
        ]
        stub.client.get_activities.return_value = [{"icu_training_load": 180}]

        result = stub.calculate_cycle_metrics(date(2026, 1, 1), date(2026, 1, 7))
        assert abs(result["tss_completion_rate"] - 0.9) < 0.01
