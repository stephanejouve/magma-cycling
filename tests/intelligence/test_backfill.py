"""
Tests for backfill_intelligence module.

Tests backfill extraction of learnings/patterns from Intervals.icu history.
"""

from unittest.mock import Mock, patch

import pytest

from cyclisme_training_logs.intelligence.training_intelligence import ConfidenceLevel
from cyclisme_training_logs.scripts.backfill_intelligence import IntervalsICUBackfiller


@pytest.fixture
def mock_intervals_client():
    """Mock IntervalsClient for testing."""
    with patch("cyclisme_training_logs.scripts.backfill_intelligence.IntervalsClient") as mock:
        yield mock


@pytest.fixture
def backfiller(mock_intervals_client):
    """Create backfiller instance with mocked client."""
    return IntervalsICUBackfiller(athlete_id="i151223", api_key="test_key")


def test_classify_workout_type_sweet_spot(backfiller):
    """Test classification of Sweet-Spot workouts."""
    # Name-based classification
    activity = {"name": "Sweet Spot 3x10", "icu_intensity": 0.89}
    assert backfiller.classify_workout_type(activity) == "sweet-spot"

    # IF-based classification
    activity = {"name": "Random Ride", "icu_intensity": 0.88}
    assert backfiller.classify_workout_type(activity) == "sweet-spot"


def test_classify_workout_type_vo2(backfiller):
    """Test classification of VO2 max workouts."""
    # Name-based
    activity = {"name": "VO2 Max 5x3min", "icu_intensity": 1.15}
    assert backfiller.classify_workout_type(activity) == "vo2"

    # IF-based
    activity = {"name": "Hard Intervals", "icu_intensity": 1.10}
    assert backfiller.classify_workout_type(activity) == "vo2"


def test_backfill_sweet_spot_extraction(backfiller, mock_intervals_client):
    """Test extraction of Sweet-Spot learning from API data."""
    # Mock 90 sweet-spot sessions
    mock_activities = [
        {
            "name": f"Sweet Spot {i}",
            "icu_intensity": 0.89,
            "icu_training_load": 75,
            "start_date_local": f"2024-{i%12+1:02d}-01",
        }
        for i in range(90)
    ]

    backfiller.client.get_activities = Mock(return_value=mock_activities)
    backfiller.client.get_wellness = Mock(return_value=[])

    # Run analysis
    backfiller.analyze_sweet_spot_sessions(mock_activities)

    # Verify learning created
    assert len(backfiller.intelligence.learnings) >= 1

    # Find sweet-spot learning
    sweet_spot_learning = next(
        (l for l in backfiller.intelligence.learnings.values() if l.category == "sweet-spot"), None
    )

    assert sweet_spot_learning is not None
    assert sweet_spot_learning.confidence == ConfidenceLevel.VALIDATED  # 90 obs >> 10
    assert "88-90% FTP" in sweet_spot_learning.description
    assert any("90 sessions" in str(ev) for ev in sweet_spot_learning.evidence)


def test_backfill_vo2_sleep_correlation(backfiller, mock_intervals_client):
    """Test VO2/sleep correlation pattern extraction."""
    # Mock 40 VO2 sessions
    mock_activities = []
    mock_wellness = []

    for i in range(40):
        activity_date = f"2024-{i%12+1:02d}-{i%28+1:02d}"

        # Half with poor sleep (<6h) and low completion
        # Half with good sleep (>6.5h) and high completion
        if i < 20:
            # Poor sleep group
            sleep_hours = 5.5
            intensity = 0.95  # Failed to complete (IF < 1.05)
            tss = 25
        else:
            # Good sleep group
            sleep_hours = 7.0
            intensity = 1.15  # Completed successfully
            tss = 50

        mock_activities.append(
            {
                "name": f"VO2 Max {i}",
                "type": "VirtualRide",
                "icu_intensity": intensity,
                "icu_training_load": tss,
                "start_date_local": f"{activity_date}T08:00:00",
            }
        )

        mock_wellness.append({"id": activity_date, "sleepSecs": int(sleep_hours * 3600)})

    backfiller.client.get_activities = Mock(return_value=mock_activities)
    backfiller.client.get_wellness = Mock(return_value=mock_wellness)

    # Run analysis
    backfiller.analyze_vo2_sleep_correlation(mock_activities, mock_wellness)

    # Verify pattern created
    assert len(backfiller.intelligence.patterns) >= 1

    # Find sleep/VO2 pattern
    sleep_pattern = next(
        (p for p in backfiller.intelligence.patterns.values() if "sleep" in p.name.lower()), None
    )

    assert sleep_pattern is not None
    assert sleep_pattern.name == "sleep_debt_vo2_failure"
    assert sleep_pattern.trigger_conditions.get("sleep") == "<6h"
    assert sleep_pattern.trigger_conditions.get("workout_type") == "VO2"
    assert sleep_pattern.frequency == 40
    assert sleep_pattern.confidence == ConfidenceLevel.VALIDATED


def test_backfill_outdoor_discipline(backfiller, mock_intervals_client):
    """Test outdoor intensity overshoot pattern extraction."""
    # Mock 100 outdoor rides with +15% IF overshoot
    outdoor_activities = [
        {
            "name": f"Outdoor Ride {i}",
            "type": "Ride",  # Outdoor
            "icu_intensity": 0.92,  # High IF
            "start_date_local": f"2024-{i%12+1:02d}-01",
        }
        for i in range(100)
    ]

    # Mock 80 indoor rides with normal IF
    indoor_activities = [
        {
            "name": f"Indoor Ride {i}",
            "type": "VirtualRide",  # Indoor
            "icu_intensity": 0.80,  # Normal IF
            "start_date_local": f"2024-{i%12+1:02d}-15",
        }
        for i in range(80)
    ]

    all_activities = outdoor_activities + indoor_activities
    backfiller.client.get_activities = Mock(return_value=all_activities)

    # Run analysis
    backfiller.analyze_outdoor_discipline(all_activities)

    # Verify pattern created
    assert len(backfiller.intelligence.patterns) >= 1

    # Find outdoor pattern
    outdoor_pattern = next(
        (p for p in backfiller.intelligence.patterns.values() if "outdoor" in p.name.lower()), None
    )

    assert outdoor_pattern is not None
    assert outdoor_pattern.name == "outdoor_intensity_overshoot"
    assert outdoor_pattern.trigger_conditions.get("workout_location") == "outdoor"
    assert outdoor_pattern.frequency == 100
    assert outdoor_pattern.confidence == ConfidenceLevel.VALIDATED


def test_backfill_ftp_progression(backfiller, mock_intervals_client):
    """Test FTP progression learning extraction."""
    # Mock athlete with current FTP
    # Mock activities with FTP test
    mock_activities = [
        {
            "start_date_local": "2024-06-15T10:00:00",
            "name": "FTP Test 20min",
            "source": "STRAVA",
            "icu_average_watts": 210,
            "icu_ftp": 200,
            "icu_rolling_ftp": 205,
            "max_avg_watts": {},
        }
    ]

    # Mock wellness with eFTP changes
    mock_wellness = [
        {"id": "2024-01-01", "sportInfo": [{"type": "Ride", "eftp": 200.0}]},
        {"id": "2024-06-15", "sportInfo": [{"type": "Ride", "eftp": 210.0}]},
        {"id": "2025-12-31", "sportInfo": [{"type": "Ride", "eftp": 220.0}]},
    ]

    # Run analysis (24 months)
    backfiller.analyze_ftp_progression("2024-01-01", "2025-12-31", mock_activities, mock_wellness)

    # Verify learning created
    assert len(backfiller.intelligence.learnings) >= 1

    # Find FTP progression learning
    ftp_learning = next(
        (l for l in backfiller.intelligence.learnings.values() if l.category == "ftp_progression"),
        None,
    )

    assert ftp_learning is not None
    # Check FTP values in description (200W -> 220W based on wellness data)
    assert "200W" in ftp_learning.description or "210W" in ftp_learning.description
    assert "220W" in ftp_learning.description
    # Confidence based on number of tests and time period (3 eFTP changes over 24 months)
    assert ftp_learning.confidence in [
        ConfidenceLevel.MEDIUM,
        ConfidenceLevel.HIGH,
        ConfidenceLevel.VALIDATED,
    ]
    assert len(ftp_learning.evidence) >= 4  # At least period, progression, rate, total tests


def test_backfill_saves_valid_json(backfiller, mock_intervals_client, tmp_path):
    """Test backfill saves valid intelligence JSON."""
    # Mock minimal data
    mock_activities = [
        {
            "name": "Sweet Spot",
            "icu_intensity": 0.89,
            "icu_training_load": 75,
            "start_date_local": "2024-01-01T08:00:00",
        }
    ]

    mock_athlete = {"ftp": 220}

    backfiller.client.get_activities = Mock(return_value=mock_activities)
    backfiller.client.get_wellness = Mock(return_value=[])
    backfiller.client.get_athlete = Mock(return_value=mock_athlete)

    # Run backfill
    output_path = tmp_path / "test_intelligence.json"
    backfiller.run("2024-01-01", "2024-12-31", output_path)

    # Verify file created
    assert output_path.exists()

    # Verify valid JSON
    import json

    with open(output_path) as f:
        data = json.load(f)

    assert "learnings" in data
    assert "patterns" in data
    assert isinstance(data["learnings"], dict)
    assert isinstance(data["patterns"], dict)


def test_classify_workout_type_fallback_cases(backfiller):
    """Test workout type classification edge cases."""
    # Tempo by IF
    assert backfiller.classify_workout_type({"name": "Unknown", "icu_intensity": 0.80}) == "tempo"

    # Recovery by IF
    assert (
        backfiller.classify_workout_type({"name": "Easy Spin", "icu_intensity": 0.55}) == "recovery"
    )

    # Endurance fallback
    assert (
        backfiller.classify_workout_type({"name": "Long Ride", "icu_intensity": 0.70})
        == "endurance"
    )


def test_analyze_empty_activities(backfiller):
    """Test analysis with no activities returns gracefully."""
    empty_activities = []

    # Should not raise, just print warnings
    backfiller.analyze_sweet_spot_sessions(empty_activities)
    backfiller.analyze_vo2_sleep_correlation(empty_activities, [])
    backfiller.analyze_outdoor_discipline(empty_activities)

    # No learnings/patterns should be created
    assert len(backfiller.intelligence.learnings) == 0
    assert len(backfiller.intelligence.patterns) == 0
