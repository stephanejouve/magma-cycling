"""Tests for workout diversity tracking system.

Sprint: Zwift Integration S2
Created: 2026-02-10
"""

import json
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest

from magma_cycling.intelligence.workout_diversity import (
    WorkoutDiversityTracker,
    WorkoutUsage,
)


@pytest.fixture
def temp_intelligence_file():
    """Create a temporary intelligence.json file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        initial_data = {
            "learnings": {},
            "patterns": {},
            "adaptations": {},
            "workout_history": [],
        }
        json.dump(initial_data, f)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def tracker(temp_intelligence_file):
    """Create a WorkoutDiversityTracker with temp intelligence file."""
    return WorkoutDiversityTracker(intelligence_file=temp_intelligence_file)


def test_workout_usage_dataclass():
    """Test WorkoutUsage dataclass creation and serialization."""
    usage = WorkoutUsage(
        workout_url="https://whatsonzwift.com/test",
        workout_name="Test Workout",
        date_used="2026-02-10",
        session_id="S081-02",
        source="whatsonzwift.com",
        category="FTP",
        tss=56,
    )

    assert usage.workout_url == "https://whatsonzwift.com/test"
    assert usage.workout_name == "Test Workout"
    assert usage.session_id == "S081-02"

    # Test serialization
    usage_dict = usage.to_dict()
    assert isinstance(usage_dict, dict)
    assert usage_dict["workout_url"] == "https://whatsonzwift.com/test"
    assert usage_dict["tss"] == 56


def test_tracker_initialization(tracker, temp_intelligence_file):
    """Test tracker initializes with correct intelligence file."""
    assert tracker.intelligence_file == temp_intelligence_file
    assert tracker.rotation_window_days == 21
    assert tracker.max_repetition_rate == 0.40
    assert "workout_history" in tracker.intelligence_data


def test_record_workout_usage(tracker):
    """Test recording a workout usage."""
    usage = WorkoutUsage(
        workout_url="https://whatsonzwift.com/flat-out-fast",
        workout_name="Flat Out Fast",
        date_used="2026-02-10",
        session_id="S081-02",
        category="FTP",
        tss=56,
    )

    tracker.record_workout_usage(usage)

    # Verify it was saved
    assert len(tracker.intelligence_data["workout_history"]) == 1
    saved_usage = tracker.intelligence_data["workout_history"][0]
    assert saved_usage["workout_name"] == "Flat Out Fast"
    assert saved_usage["tss"] == 56


def test_is_recently_used(tracker):
    """Test checking if workout was recently used."""
    workout_url = "https://whatsonzwift.com/flat-out-fast"

    # Should not be recently used initially
    assert not tracker.is_recently_used(workout_url)

    # Record usage today
    usage = WorkoutUsage(
        workout_url=workout_url,
        workout_name="Flat Out Fast",
        date_used=date.today().isoformat(),
        session_id="S081-02",
        category="FTP",
        tss=56,
    )
    tracker.record_workout_usage(usage)

    # Should be recently used now
    assert tracker.is_recently_used(workout_url)

    # Record old usage (outside window)
    old_date = (date.today() - timedelta(days=30)).isoformat()
    old_usage = WorkoutUsage(
        workout_url="https://whatsonzwift.com/old-workout",
        workout_name="Old Workout",
        date_used=old_date,
        session_id="S070-01",
        category="INT",
        tss=70,
    )
    tracker.record_workout_usage(old_usage)

    # Old workout should not be recently used (outside 21-day window)
    assert not tracker.is_recently_used("https://whatsonzwift.com/old-workout")


def test_get_recent_usage(tracker):
    """Test getting recent usage records for a workout."""
    workout_url = "https://whatsonzwift.com/flat-out-fast"

    # Add multiple usages
    for i in range(3):
        days_ago = i * 7  # 0, 7, 14 days ago
        usage_date = (date.today() - timedelta(days=days_ago)).isoformat()
        usage = WorkoutUsage(
            workout_url=workout_url,
            workout_name="Flat Out Fast",
            date_used=usage_date,
            session_id=f"S{81-i:03d}-02",
            category="FTP",
            tss=56,
        )
        tracker.record_workout_usage(usage)

    # Get recent usage (all should be within 21-day window)
    recent = tracker.get_recent_usage(workout_url)
    assert len(recent) == 3

    # Get recent usage with shorter window (should get fewer)
    # Note: 7-day window includes today (day 0) and 7 days ago (day 7), so 2 usages
    recent_week = tracker.get_recent_usage(workout_url, window_days=7)
    assert len(recent_week) == 2  # Today and 7 days ago


def test_get_workout_stats(tracker):
    """Test getting workout statistics."""
    workout_url = "https://whatsonzwift.com/flat-out-fast"

    # Stats for non-existent workout
    stats = tracker.get_workout_stats(workout_url)
    assert stats["total_uses"] == 0
    assert stats["last_used"] is None

    # Add usages
    for i in range(3):
        days_ago = i * 5
        usage_date = (date.today() - timedelta(days=days_ago)).isoformat()
        usage = WorkoutUsage(
            workout_url=workout_url,
            workout_name="Flat Out Fast",
            date_used=usage_date,
            session_id=f"S{81-i:03d}-02",
            category="FTP",
            tss=56,
        )
        tracker.record_workout_usage(usage)

    # Get updated stats
    stats = tracker.get_workout_stats(workout_url)
    assert stats["total_uses"] == 3
    assert stats["last_used"] == date.today().isoformat()
    assert stats["recent_uses"] == 3  # All within 21 days


def test_get_diversity_report(tracker):
    """Test diversity report generation."""
    # Add workouts with different repetition patterns
    workouts = [
        ("workout1", "Workout 1", "FTP", 56),
        ("workout1", "Workout 1", "FTP", 56),  # Repeat
        ("workout2", "Workout 2", "INT", 70),
        ("workout3", "Workout 3", "END", 50),
    ]

    for i, (url_suffix, name, category, tss) in enumerate(workouts):
        usage = WorkoutUsage(
            workout_url=f"https://whatsonzwift.com/{url_suffix}",
            workout_name=name,
            date_used=(date.today() - timedelta(days=i)).isoformat(),
            session_id=f"S081-{i:02d}",
            category=category,
            tss=tss,
        )
        tracker.record_workout_usage(usage)

    # Get diversity report
    report = tracker.get_diversity_report(days=30)

    assert report["period_days"] == 30
    assert report["total_sessions"] == 4
    assert report["unique_workouts"] == 3
    assert report["repetition_rate"] == pytest.approx(0.25)  # 1 - (3/4)
    assert report["diversity_ok"]  # 25% < 40% threshold

    # Check most used
    assert len(report["most_used"]) == 3
    assert report["most_used"][0]["name"] == "Workout 1"
    assert report["most_used"][0]["count"] == 2


def test_get_available_workouts_for_diversity(tracker):
    """Test filtering workouts by diversity constraints."""
    # Record recent usage of workout1
    usage = WorkoutUsage(
        workout_url="https://whatsonzwift.com/workout1",
        workout_name="Workout 1",
        date_used=date.today().isoformat(),
        session_id="S081-02",
        category="FTP",
        tss=56,
    )
    tracker.record_workout_usage(usage)

    # Test filtering
    all_workouts = [
        "https://whatsonzwift.com/workout1",  # Recently used
        "https://whatsonzwift.com/workout2",  # Not used
        "https://whatsonzwift.com/workout3",  # Not used
    ]

    available = tracker.get_available_workouts_for_diversity(all_workouts)

    # Should exclude workout1
    assert len(available) == 2
    assert "https://whatsonzwift.com/workout1" not in available
    assert "https://whatsonzwift.com/workout2" in available
    assert "https://whatsonzwift.com/workout3" in available


def test_custom_rotation_window(temp_intelligence_file):
    """Test tracker with custom rotation window."""
    tracker = WorkoutDiversityTracker(
        intelligence_file=temp_intelligence_file, rotation_window_days=14
    )

    assert tracker.rotation_window_days == 14

    workout_url = "https://whatsonzwift.com/test"

    # Add usage 15 days ago (outside 14-day window)
    old_usage = WorkoutUsage(
        workout_url=workout_url,
        workout_name="Test",
        date_used=(date.today() - timedelta(days=15)).isoformat(),
        session_id="S070-01",
        category="FTP",
        tss=56,
    )
    tracker.record_workout_usage(old_usage)

    # Should not be recently used with 14-day window
    assert not tracker.is_recently_used(workout_url, window_days=14)


def test_custom_max_repetition_rate(temp_intelligence_file):
    """Test tracker with custom max repetition rate."""
    tracker = WorkoutDiversityTracker(
        intelligence_file=temp_intelligence_file, max_repetition_rate=0.30
    )

    assert tracker.max_repetition_rate == 0.30

    # Add workouts with 33% repetition (exceeds 30% threshold)
    for i in range(3):
        url_suffix = "workout1" if i < 2 else "workout2"
        usage = WorkoutUsage(
            workout_url=f"https://whatsonzwift.com/{url_suffix}",
            workout_name=f"Workout {url_suffix[-1]}",
            date_used=(date.today() - timedelta(days=i)).isoformat(),
            session_id=f"S081-{i:02d}",
            category="FTP",
            tss=56,
        )
        tracker.record_workout_usage(usage)

    report = tracker.get_diversity_report(days=30)

    # 2 unique out of 3 sessions = 33% repetition
    assert report["repetition_rate"] == pytest.approx(0.333, abs=0.01)
    assert not report["diversity_ok"]  # 33% > 30% threshold
