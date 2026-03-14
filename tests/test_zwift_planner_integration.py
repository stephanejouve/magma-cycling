"""Tests for Zwift catalogue integration in weekly planner."""

from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.external.zwift_models import (
    SegmentType,
    WorkoutMatch,
    ZwiftCategory,
    ZwiftWorkout,
    ZwiftWorkoutSegment,
)
from magma_cycling.workflows.planner.periodization import PeriodizationMixin

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

RECONSTRUCTION_BASE_DISTRIBUTION = {
    "Recovery": 0.10,
    "Endurance": 0.25,
    "Tempo": 0.35,
    "Sweet-Spot": 0.20,
    "FTP": 0.05,
    "VO2": 0.03,
    "AC_Neuro": 0.02,
}

CONSOLIDATION_DISTRIBUTION = {
    "Recovery": 0.10,
    "Endurance": 0.20,
    "Tempo": 0.25,
    "Sweet-Spot": 0.25,
    "FTP": 0.10,
    "VO2": 0.08,
    "AC_Neuro": 0.02,
}


def _make_workout(name, category, tss, duration, segments=None):
    """Create a ZwiftWorkout for testing."""
    return ZwiftWorkout(
        name=name,
        category=category,
        duration_minutes=duration,
        tss=tss,
        url=f"https://whatsonzwift.com/workouts/{name.lower().replace(' ', '-')}",
        segments=segments
        or [
            ZwiftWorkoutSegment(
                segment_type=SegmentType.WARMUP,
                duration_seconds=600,
                power_low=50,
                power_high=65,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.INTERVAL,
                duration_seconds=600,
                power_low=90,
                repeat_count=3,
            ),
            ZwiftWorkoutSegment(
                segment_type=SegmentType.COOLDOWN,
                duration_seconds=600,
                power_low=65,
                power_high=50,
            ),
        ],
    )


def _make_match(workout, score=80.0):
    """Create a WorkoutMatch for testing."""
    return WorkoutMatch(
        workout=workout,
        score=score,
        tss_delta=abs(workout.tss - 60),
        type_match=True,
        recently_used=False,
    )


class FakePlanner(PeriodizationMixin):
    """Minimal planner stub for testing PeriodizationMixin."""

    def __init__(self):
        self.current_metrics = {"ctl": 45.0}


@pytest.fixture
def planner():
    """Create a FakePlanner instance."""
    return FakePlanner()


@pytest.fixture
def periodization_context():
    """Standard RECONSTRUCTION_BASE periodization context."""
    return {
        "phase": "RECONSTRUCTION BASE",
        "weekly_tss_load": 350,
        "intensity_distribution": RECONSTRUCTION_BASE_DISTRIBUTION,
    }


@pytest.fixture
def cache_stats():
    """Typical cache stats."""
    return {
        "total_workouts": 24,
        "by_category": {"Intervals": 8, "Endurance": 6, "FTP": 4, "Recovery": 6},
        "oldest_cached": "2026-01-01T00:00:00",
        "newest_cached": "2026-03-01T00:00:00",
        "cache_path": "/tmp/zwift.db",
    }


PATCH_CLIENT = "magma_cycling.external.zwift_client.ZwiftWorkoutClient"


# ---------------------------------------------------------------------------
# Tests _derive_session_type_targets
# ---------------------------------------------------------------------------


class TestDeriveSessionTypeTargets:
    """Tests for _derive_session_type_targets."""

    def test_reconstruction_base_produces_end_and_int(self, planner, periodization_context):
        """RECONSTRUCTION_BASE distribution produces END and INT targets."""
        targets = planner._derive_session_type_targets(periodization_context)
        types = {t["session_type"] for t in targets}
        assert "END" in types
        assert "INT" in types

    def test_skip_recovery_zone(self, planner, periodization_context):
        """Recovery zone is excluded from targets."""
        targets = planner._derive_session_type_targets(periodization_context)
        zone_labels = " ".join(t["zone_label"] for t in targets)
        assert "Recovery" not in zone_labels

    def test_merge_zones_same_type(self, planner, periodization_context):
        """Endurance + Tempo are merged into single END target."""
        targets = planner._derive_session_type_targets(periodization_context)
        end_targets = [t for t in targets if t["session_type"] == "END"]
        assert len(end_targets) == 1
        assert "Endurance" in end_targets[0]["zone_label"]
        assert "Tempo" in end_targets[0]["zone_label"]

    def test_tss_target_calculation(self, planner, periodization_context):
        """TSS target = weekly_tss_load * merged zone percentage."""
        targets = planner._derive_session_type_targets(periodization_context)
        end_target = next(t for t in targets if t["session_type"] == "END")
        # Endurance 25% + Tempo 35% = 60% of 350 = 210
        assert end_target["tss_target"] == 210

    def test_empty_distribution_returns_empty(self, planner):
        """Empty distribution returns empty list."""
        context = {"intensity_distribution": {}, "weekly_tss_load": 350}
        assert planner._derive_session_type_targets(context) == []

    def test_filter_below_5_percent(self, planner):
        """Zones below 5% are filtered out."""
        context = {
            "intensity_distribution": {
                "Endurance": 0.90,
                "FTP": 0.04,  # Below 5%
                "VO2": 0.03,  # Below 5%
                "AC_Neuro": 0.03,
            },
            "weekly_tss_load": 350,
        }
        targets = planner._derive_session_type_targets(context)
        types = {t["session_type"] for t in targets}
        assert "END" in types
        # FTP at 4% alone is below 5%
        assert "FTP" not in types
        # VO2 3% maps to INT, below 5%
        assert "INT" not in types

    def test_consolidation_includes_ftp(self, planner):
        """CONSOLIDATION phase includes FTP at 10%."""
        context = {
            "intensity_distribution": CONSOLIDATION_DISTRIBUTION,
            "weekly_tss_load": 400,
        }
        targets = planner._derive_session_type_targets(context)
        types = {t["session_type"] for t in targets}
        assert "FTP" in types


# ---------------------------------------------------------------------------
# Tests _load_available_zwift_workouts
# ---------------------------------------------------------------------------


class TestLoadAvailableZwiftWorkouts:
    """Tests for _load_available_zwift_workouts."""

    @patch(PATCH_CLIENT)
    def test_empty_cache_returns_empty(self, mock_client_cls, planner):
        """Empty cache returns empty string."""
        mock_client = MagicMock()
        mock_client.get_cache_stats.return_value = {"total_workouts": 0}
        mock_client_cls.return_value = mock_client

        assert planner._load_available_zwift_workouts() == ""

    @patch(PATCH_CLIENT)
    def test_no_periodization_returns_stats_only(self, mock_client_cls, planner, cache_stats):
        """Without periodization context, returns stats-only format."""
        mock_client = MagicMock()
        mock_client.get_cache_stats.return_value = cache_stats
        mock_client_cls.return_value = mock_client

        # No _periodization_context set
        result = planner._load_available_zwift_workouts()

        assert "Workouts Externes Disponibles" in result
        assert "24 workouts" in result
        assert "Structures Recommandees" not in result

    @patch(PATCH_CLIENT)
    def test_with_matches_returns_suggestions(
        self, mock_client_cls, planner, periodization_context, cache_stats
    ):
        """With periodization context and matches, returns suggestions."""
        planner._periodization_context = periodization_context

        halvfems = _make_workout("Halvfems", ZwiftCategory.INTERVALS, 68, 62)
        novanta = _make_workout("Novanta", ZwiftCategory.INTERVALS, 70, 60)
        devedeset = _make_workout("Devedeset", ZwiftCategory.ENDURANCE, 62, 60)

        mock_client = MagicMock()
        mock_client.get_cache_stats.return_value = cache_stats
        mock_client.search_workouts.side_effect = lambda criteria: {
            "END": [_make_match(devedeset, 85.0)],
            "INT": [_make_match(halvfems, 90.0), _make_match(novanta, 72.0)],
            "FTP": [],
        }.get(criteria.session_type, [])
        mock_client_cls.return_value = mock_client

        result = planner._load_available_zwift_workouts()

        assert "Structures Recommandees" in result
        assert "Halvfems" in result
        assert "Novanta" in result
        assert "Devedeset" in result

    @patch(PATCH_CLIENT)
    def test_max_3_suggestions_per_type(
        self, mock_client_cls, planner, periodization_context, cache_stats
    ):
        """Maximum 3 suggestions per session type."""
        planner._periodization_context = periodization_context

        workouts = [
            _make_workout(f"Workout{i}", ZwiftCategory.INTERVALS, 65 + i, 60) for i in range(5)
        ]
        matches = [_make_match(w, 90 - i * 5) for i, w in enumerate(workouts)]

        mock_client = MagicMock()
        mock_client.get_cache_stats.return_value = cache_stats
        mock_client.search_workouts.return_value = matches
        mock_client_cls.return_value = mock_client

        result = planner._load_available_zwift_workouts()

        # Should contain only 3 suggestions per type (counted by "Score:" markers)
        # 3 types (END, INT, FTP) * 3 max = 9
        assert result.count("Score:") <= 9

    @patch(PATCH_CLIENT)
    def test_exception_returns_empty(self, mock_client_cls, planner):
        """Exception during loading returns empty string."""
        mock_client_cls.side_effect = RuntimeError("DB error")

        result = planner._load_available_zwift_workouts()
        assert result == ""

    @patch(PATCH_CLIENT)
    def test_diversity_window_28_days(
        self, mock_client_cls, planner, periodization_context, cache_stats
    ):
        """Search criteria use diversity_window_days=28."""
        planner._periodization_context = periodization_context

        mock_client = MagicMock()
        mock_client.get_cache_stats.return_value = cache_stats
        mock_client.search_workouts.return_value = []
        mock_client_cls.return_value = mock_client

        planner._load_available_zwift_workouts()

        # Check all search_workouts calls used diversity_window_days=28
        for call in mock_client.search_workouts.call_args_list:
            criteria = call[0][0]
            assert criteria.diversity_window_days == 28

    @patch(PATCH_CLIENT)
    def test_tss_tolerance_10(self, mock_client_cls, planner, periodization_context, cache_stats):
        """Search criteria use tss_tolerance=10."""
        planner._periodization_context = periodization_context

        mock_client = MagicMock()
        mock_client.get_cache_stats.return_value = cache_stats
        mock_client.search_workouts.return_value = []
        mock_client_cls.return_value = mock_client

        planner._load_available_zwift_workouts()

        for call in mock_client.search_workouts.call_args_list:
            criteria = call[0][0]
            assert criteria.tss_tolerance == 10


# ---------------------------------------------------------------------------
# Tests format methods
# ---------------------------------------------------------------------------


class TestFormatMethods:
    """Tests for format helper methods."""

    def test_suggestions_contain_intervals_format(self, planner):
        """Suggestion output contains Intervals.icu workout text."""
        halvfems = _make_workout("Halvfems", ZwiftCategory.INTERVALS, 68, 62)
        suggestions = {"INT": [_make_match(halvfems, 90.0)]}
        targets = [{"session_type": "INT", "tss_target": 70, "zone_label": "Sweet-Spot/VO2"}]
        stats = {"total_workouts": 24}

        result = planner._format_zwift_suggestions(suggestions, targets, stats)

        # Should contain Intervals.icu format from to_intervals_description()
        assert "Halvfems" in result
        assert "62min" in result
        assert "68 TSS" in result
        assert "Score: 90" in result

    def test_no_matches_shows_cache_insuffisant(self, planner):
        """Empty matches for a type shows 'cache insuffisant'."""
        suggestions = {"FTP": []}
        targets = [{"session_type": "FTP", "tss_target": 50, "zone_label": "FTP"}]
        stats = {"total_workouts": 24}

        result = planner._format_zwift_suggestions(suggestions, targets, stats)

        assert "cache insuffisant" in result

    def test_fallback_stats_only_format(self, planner, cache_stats):
        """Stats-only format contains expected information."""
        result = planner._format_zwift_stats_only(cache_stats)

        assert "Workouts Externes Disponibles" in result
        assert "24 workouts" in result
        assert "Intervals" in result
        assert "DIVERSITE" in result
