"""
Tests for Biomechanics Integration with Intervals.icu API.

Tests extraction of biomechanical metrics from Intervals.icu activities
and cadence recommendations based on Grappe research.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from cyclisme_training_logs.intelligence.biomechanics_intervals import (
    extract_biomechanical_metrics,
    get_activities_last_n_weeks,
    get_cadence_recommendation_from_activities,
)


class TestExtractBiomechanicalMetrics:
    """Test suite for extract_biomechanical_metrics()."""

    def test_extract_metrics_empty_activities(self):
        """Test with empty activity list."""
        result = extract_biomechanical_metrics([])

        assert result["avg_cadence"] == 0
        assert result["avg_duration_min"] == 0
        assert result["avg_intensity"] == 0.0
        assert result["activity_count"] == 0

    def test_extract_metrics_single_activity(self):
        """Test with single valid activity."""
        activities = [
            {
                "average_cadence": 90,
                "moving_time": 3600,  # 60 min
                "icu_intensity": 75,  # 75% FTP
                "icu_training_load": 50,  # 50 TSS
            }
        ]

        result = extract_biomechanical_metrics(activities)

        assert result["avg_cadence"] == 90
        assert result["avg_duration_min"] == 60
        assert result["avg_intensity"] == 0.75
        assert result["activity_count"] == 1

    def test_extract_metrics_multiple_activities_weighted(self):
        """Test weighted averages with multiple activities."""
        activities = [
            {
                "average_cadence": 85,
                "moving_time": 3600,
                "icu_intensity": 70,
                "icu_training_load": 50,  # 50 TSS
            },
            {
                "average_cadence": 95,
                "moving_time": 2700,
                "icu_intensity": 90,
                "icu_training_load": 100,  # 100 TSS (more weight)
            },
        ]

        result = extract_biomechanical_metrics(activities)

        # Weighted cadence: (85*50 + 95*100) / 150 = 91.67 → 92
        assert result["avg_cadence"] == 92

        # Weighted intensity: (0.70*50 + 0.90*100) / 150 = 0.833 → 0.83
        assert result["avg_intensity"] == 0.83

        # Average duration: (60 + 45) / 2 = 52.5 → 52 (banker's rounding)
        assert result["avg_duration_min"] == 52

        assert result["activity_count"] == 2

    def test_extract_metrics_filters_zero_cadence(self):
        """Test filtering of activities with zero cadence (rest days)."""
        activities = [
            {
                "average_cadence": 90,
                "moving_time": 3600,
                "icu_intensity": 75,
                "icu_training_load": 50,
            },
            {
                "average_cadence": 0,  # Rest day or non-bike
                "moving_time": 0,
                "icu_intensity": 0,
                "icu_training_load": 0,
            },
        ]

        result = extract_biomechanical_metrics(activities)

        # Should only count the first activity
        assert result["avg_cadence"] == 90
        assert result["activity_count"] == 1

    def test_extract_metrics_filters_zero_tss(self):
        """Test filtering of activities with zero TSS."""
        activities = [
            {
                "average_cadence": 90,
                "moving_time": 3600,
                "icu_intensity": 75,
                "icu_training_load": 50,
            },
            {
                "average_cadence": 85,
                "moving_time": 1800,
                "icu_intensity": 60,
                "icu_training_load": 0,  # Zero TSS (invalid)
            },
        ]

        result = extract_biomechanical_metrics(activities)

        # Should only count the first activity
        assert result["avg_cadence"] == 90
        assert result["activity_count"] == 1

    def test_extract_metrics_missing_fields(self):
        """Test handling of activities with missing fields."""
        activities = [
            {
                "average_cadence": 90,
                "moving_time": 3600,
                # Missing icu_intensity
                "icu_training_load": 50,
            }
        ]

        result = extract_biomechanical_metrics(activities)

        # Should handle missing fields gracefully (defaults to 0)
        assert result["avg_cadence"] == 90
        assert result["avg_intensity"] == 0.0
        assert result["activity_count"] == 1


class TestGetCadenceRecommendationFromActivities:
    """Test suite for get_cadence_recommendation_from_activities()."""

    def test_cadence_recommendation_optimal_match(self):
        """Test when recent cadence matches optimal cadence."""
        activities = [
            {
                "average_cadence": 93,  # Close to Sweet-Spot optimal (93 rpm)
                "moving_time": 3600,
                "icu_intensity": 90,
                "icu_training_load": 50,
            }
        ]

        result = get_cadence_recommendation_from_activities(
            activities=activities,
            next_cycle_zone_ftp=0.90,  # Sweet-Spot
            next_cycle_duration_min=60,
            profil_fibres="mixte",
        )

        assert result["cadence_optimale"] == 93
        assert result["cadence_actuelle"] == 93
        assert result["ecart_rpm"] == 0
        assert result["correction_necessaire"] is False

    def test_cadence_recommendation_too_low(self):
        """Test when recent cadence is too low."""
        activities = [
            {
                "average_cadence": 80,  # 13 rpm below optimal
                "moving_time": 3600,
                "icu_intensity": 90,
                "icu_training_load": 50,
            }
        ]

        result = get_cadence_recommendation_from_activities(
            activities=activities,
            next_cycle_zone_ftp=0.90,  # Sweet-Spot optimal = 93
            next_cycle_duration_min=60,
            profil_fibres="mixte",
        )

        assert result["cadence_optimale"] == 93
        assert result["cadence_actuelle"] == 80
        assert result["ecart_rpm"] == 13
        assert result["correction_necessaire"] is True

    def test_cadence_recommendation_too_high(self):
        """Test when recent cadence is too high."""
        activities = [
            {
                "average_cadence": 100,  # 15 rpm above optimal
                "moving_time": 3600,
                "icu_intensity": 70,
                "icu_training_load": 50,
            }
        ]

        result = get_cadence_recommendation_from_activities(
            activities=activities,
            next_cycle_zone_ftp=0.70,  # Endurance optimal = 85
            next_cycle_duration_min=90,
            profil_fibres="mixte",
        )

        assert result["cadence_optimale"] == 85
        assert result["cadence_actuelle"] == 100
        assert result["ecart_rpm"] == -15
        assert result["correction_necessaire"] is True

    def test_cadence_recommendation_within_tolerance(self):
        """Test when cadence is within acceptable tolerance (±5 rpm)."""
        activities = [
            {
                "average_cadence": 88,  # 3 rpm below optimal (within tolerance)
                "moving_time": 3600,
                "icu_intensity": 70,
                "icu_training_load": 50,
            }
        ]

        result = get_cadence_recommendation_from_activities(
            activities=activities,
            next_cycle_zone_ftp=0.70,  # Endurance optimal = 85
            next_cycle_duration_min=60,
            profil_fibres="mixte",
        )

        assert result["cadence_optimale"] == 85
        assert result["cadence_actuelle"] == 88
        assert result["ecart_rpm"] == -3
        assert result["correction_necessaire"] is False  # Within ±5 rpm

    def test_cadence_recommendation_explosif_profile(self):
        """Test cadence recommendation with explosive fiber profile."""
        activities = [
            {
                "average_cadence": 90,
                "moving_time": 2700,
                "icu_intensity": 110,
                "icu_training_load": 80,
            }
        ]

        result = get_cadence_recommendation_from_activities(
            activities=activities,
            next_cycle_zone_ftp=1.10,  # VO2
            next_cycle_duration_min=45,
            profil_fibres="explosif",
        )

        # VO2 base = 103, explosive +10 = 113 rpm
        assert result["cadence_optimale"] == 113
        assert result["ecart_rpm"] == 113 - 90
        assert result["correction_necessaire"] is True

    def test_cadence_recommendation_empty_activities(self):
        """Test cadence recommendation with no activities."""
        result = get_cadence_recommendation_from_activities(
            activities=[],
            next_cycle_zone_ftp=0.90,
            next_cycle_duration_min=60,
            profil_fibres="mixte",
        )

        assert result["cadence_optimale"] == 93
        assert result["cadence_actuelle"] == 0
        assert result["ecart_rpm"] == 93
        assert result["correction_necessaire"] is True
        assert result["recent_metrics"]["activity_count"] == 0

    def test_cadence_recommendation_invalid_zone_ftp(self):
        """Test error handling for invalid zone_ftp."""
        activities = [
            {
                "average_cadence": 90,
                "moving_time": 3600,
                "icu_intensity": 75,
                "icu_training_load": 50,
            }
        ]

        with pytest.raises(ValueError, match="zone_ftp must be between 0.5 and 1.5"):
            get_cadence_recommendation_from_activities(
                activities=activities,
                next_cycle_zone_ftp=2.0,  # Invalid
                next_cycle_duration_min=60,
                profil_fibres="mixte",
            )

    def test_cadence_recommendation_includes_raw_metrics(self):
        """Test that result includes raw metrics for debugging."""
        activities = [
            {
                "average_cadence": 90,
                "moving_time": 3600,
                "icu_intensity": 75,
                "icu_training_load": 50,
            }
        ]

        result = get_cadence_recommendation_from_activities(
            activities=activities,
            next_cycle_zone_ftp=0.90,
            next_cycle_duration_min=60,
            profil_fibres="mixte",
        )

        assert "recent_metrics" in result
        assert result["recent_metrics"]["avg_cadence"] == 90
        assert result["recent_metrics"]["activity_count"] == 1

        assert "recommendation" in result
        assert "justification" in result["recommendation"]


class TestGetActivitiesLastNWeeks:
    """Test suite for get_activities_last_n_weeks()."""

    def test_get_activities_last_4_weeks(self):
        """Test fetching activities from last 4 weeks."""
        mock_client = Mock()
        mock_client.get_activities.return_value = [
            {"id": "i1", "average_cadence": 90},
            {"id": "i2", "average_cadence": 92},
        ]

        result = get_activities_last_n_weeks(mock_client, n_weeks=4)

        assert len(result) == 2
        assert result[0]["id"] == "i1"

        # Verify client was called with correct date range
        mock_client.get_activities.assert_called_once()
        call_kwargs = mock_client.get_activities.call_args.kwargs

        # Check oldest is ~4 weeks ago
        oldest_date = datetime.fromisoformat(call_kwargs["oldest"])
        expected_oldest = datetime.now() - timedelta(weeks=4)
        assert abs((oldest_date - expected_oldest).days) <= 1

        # Check newest is today
        newest_date = datetime.fromisoformat(call_kwargs["newest"])
        expected_newest = datetime.now()
        assert abs((newest_date - expected_newest).days) <= 1

    def test_get_activities_custom_weeks(self):
        """Test fetching activities with custom week count."""
        mock_client = Mock()
        mock_client.get_activities.return_value = []

        get_activities_last_n_weeks(mock_client, n_weeks=6)

        call_kwargs = mock_client.get_activities.call_args.kwargs
        oldest_date = datetime.fromisoformat(call_kwargs["oldest"])
        expected_oldest = datetime.now() - timedelta(weeks=6)
        assert abs((oldest_date - expected_oldest).days) <= 1
