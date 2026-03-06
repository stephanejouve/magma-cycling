"""Tests for training load metrics (ACWR, Monotony, Strain)."""

from datetime import datetime, timedelta

import pytest

from magma_cycling.utils.training_load import compute_training_load


def _make_activities(daily_tss: list[float], days_back: int = 28) -> list[dict]:
    """Create synthetic activities from daily TSS values.

    Args:
        daily_tss: List of TSS values (oldest first), length <= days_back.
        days_back: Number of days to span (default 28).
    """
    today = datetime.now().date()
    activities = []
    for i, tss in enumerate(daily_tss):
        if tss > 0:
            d = today - timedelta(days=days_back - 1 - i)
            activities.append(
                {
                    "start_date_local": d.isoformat() + "T08:00:00",
                    "icu_training_load": tss,
                }
            )
    return activities


class TestComputeTrainingLoad:
    """Tests for compute_training_load()."""

    def test_empty_activities_returns_empty(self):
        """Empty activity list returns empty dict."""
        assert compute_training_load([]) == {}

    def test_uniform_load_acwr_one(self):
        """Uniform daily load should give ACWR close to 1.0."""
        daily = [50.0] * 28
        activities = _make_activities(daily)
        result = compute_training_load(activities)
        assert result["acwr"] == 1.0

    def test_acute_spike_high_acwr(self):
        """High acute vs low chronic gives ACWR > 1.5."""
        daily = [20.0] * 21 + [80.0] * 7
        activities = _make_activities(daily)
        result = compute_training_load(activities)
        assert result["acwr"] > 1.5

    def test_detraining_low_acwr(self):
        """Low acute vs high chronic gives ACWR < 0.8."""
        daily = [80.0] * 21 + [10.0] * 7
        activities = _make_activities(daily)
        result = compute_training_load(activities)
        assert result["acwr"] < 0.8

    def test_monotony_uniform_high(self):
        """Uniform daily load has zero stdev → monotony 0."""
        daily = [50.0] * 28
        activities = _make_activities(daily)
        result = compute_training_load(activities)
        # stdev=0 → monotony=0 (division safety)
        assert result["monotony"] == 0.0

    def test_monotony_varied_load(self):
        """Varied load should produce non-zero monotony."""
        daily = [20.0] * 21 + [0, 40, 60, 0, 80, 30, 50]
        activities = _make_activities(daily)
        result = compute_training_load(activities)
        assert result["monotony"] > 0

    def test_strain_calculation(self):
        """Strain = weekly_load * monotony."""
        daily = [20.0] * 21 + [0, 40, 60, 0, 80, 30, 50]
        activities = _make_activities(daily)
        result = compute_training_load(activities)
        weekly_load = sum(daily[-7:])
        expected_strain = round(weekly_load * result["monotony"], 0)
        assert result["strain"] == expected_strain

    def test_result_keys(self):
        """Result contains all expected keys."""
        daily = [50.0] * 28
        activities = _make_activities(daily)
        result = compute_training_load(activities)
        expected_keys = {"acwr", "monotony", "strain", "acute_load", "chronic_load"}
        assert set(result.keys()) == expected_keys

    def test_rest_days_counted_as_zero(self):
        """Days without activities count as TSS=0."""
        # Only 3 activities in 28 days
        today = datetime.now().date()
        activities = [
            {
                "start_date_local": (today - timedelta(days=2)).isoformat() + "T08:00:00",
                "icu_training_load": 100,
            },
            {
                "start_date_local": (today - timedelta(days=5)).isoformat() + "T08:00:00",
                "icu_training_load": 80,
            },
            {
                "start_date_local": (today - timedelta(days=20)).isoformat() + "T08:00:00",
                "icu_training_load": 60,
            },
        ]
        result = compute_training_load(activities)
        assert result["chronic_load"] == pytest.approx((100 + 80 + 60) / 28, rel=0.01)

    def test_multiple_activities_same_day(self):
        """Multiple activities on same day are summed."""
        today = datetime.now().date()
        date_str = (today - timedelta(days=1)).isoformat() + "T08:00:00"
        activities = [
            {"start_date_local": date_str, "icu_training_load": 40},
            {"start_date_local": date_str, "icu_training_load": 30},
        ]
        result = compute_training_load(activities)
        assert result  # Should not crash
        # The combined TSS should be 70 for that day
        assert result["acute_load"] == pytest.approx(70 / 7, rel=0.01)

    def test_missing_tss_skipped(self):
        """Activities without icu_training_load are skipped."""
        today = datetime.now().date()
        activities = [
            {
                "start_date_local": (today - timedelta(days=1)).isoformat() + "T08:00:00",
                "icu_training_load": None,
            },
            {
                "start_date_local": (today - timedelta(days=2)).isoformat() + "T08:00:00",
            },
        ]
        result = compute_training_load(activities)
        assert result["acute_load"] == 0.0
