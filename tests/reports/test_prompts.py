"""Tests for AI prompt builders.

Sprint R10 MVP Day 2 - Tests for prompt construction.

Author: Claude Code
Created: 2026-01-18
"""

import pytest

from cyclisme_training_logs.reports.prompts.workout_history_prompt import (
    _calculate_tss_percentage,
    _format_activities,
    _format_learnings,
    _format_metrics_evolution,
    _format_wellness,
    build_workout_history_prompt,
)
from tests.reports.fixtures import (
    SAMPLE_ACTIVITIES_S076,
    SAMPLE_LEARNINGS,
    SAMPLE_WELLNESS_DATA,
)


class TestBuildWorkoutHistoryPrompt:
    """Tests for build_workout_history_prompt function."""

    def test_build_prompt_with_valid_data(self):
        """Test prompt building with valid week data."""
        # Given: Valid week data with all required fields
        week_data = {
            "week_number": "S076",
            "start_date": "2026-01-13",
            "end_date": "2026-01-19",
            "tss_planned": 450,
            "tss_realized": 423,
            "activities": SAMPLE_ACTIVITIES_S076,
            "wellness_data": SAMPLE_WELLNESS_DATA,
            "learnings": SAMPLE_LEARNINGS,
            "metrics_evolution": {
                "start": {"ctl": 100, "atl": 50, "tsb": 10, "hrv": 58},
                "end": {"ctl": 105, "atl": 55, "tsb": 8, "hrv": 58},
            },
        }

        # When: Building prompt
        prompt = build_workout_history_prompt(week_data)

        # Then: Prompt should contain key elements
        assert "expert cycling coach" in prompt.lower()
        assert "S076" in prompt
        assert "2026-01-13" in prompt
        assert "2026-01-19" in prompt
        assert "450" in prompt  # TSS planned
        assert "423" in prompt  # TSS realized
        assert "NO HALLUCINATIONS" in prompt
        assert "French" in prompt or "français" in prompt.lower()
        assert "Chronologie Complète" in prompt
        assert "2000 words" in prompt or "2000" in prompt

    def test_build_prompt_missing_required_field(self):
        """Test prompt building fails with missing required field."""
        # Given: Incomplete week data (missing activities)
        week_data = {
            "week_number": "S076",
            "start_date": "2026-01-13",
            "end_date": "2026-01-19",
            "tss_planned": 450,
            "tss_realized": 423,
            # Missing activities, wellness_data, learnings, metrics_evolution
        }

        # When/Then: Building prompt should raise ValueError
        with pytest.raises(ValueError, match="Missing required field"):
            build_workout_history_prompt(week_data)

    def test_prompt_contains_activity_details(self):
        """Test prompt includes detailed activity information."""
        # Given: Week data with activities
        week_data = {
            "week_number": "S076",
            "start_date": "2026-01-13",
            "end_date": "2026-01-19",
            "tss_planned": 450,
            "tss_realized": 423,
            "activities": SAMPLE_ACTIVITIES_S076,
            "wellness_data": SAMPLE_WELLNESS_DATA,
            "learnings": SAMPLE_LEARNINGS,
            "metrics_evolution": {"start": {}, "end": {}},
        }

        # When: Building prompt
        prompt = build_workout_history_prompt(week_data)

        # Then: Prompt should include activity names and metrics
        assert "Z2 Base Indoor" in prompt or "Session 1" in prompt
        assert "TSS" in prompt
        assert "IF" in prompt


class TestFormatActivities:
    """Tests for _format_activities helper."""

    def test_format_activities_with_data(self):
        """Test formatting activities list."""
        # Given: List of activities
        activities = SAMPLE_ACTIVITIES_S076

        # When: Formatting activities
        formatted = _format_activities(activities)

        # Then: Should contain activity details
        assert "Session 1" in formatted or "Session" in formatted
        assert "TSS" in formatted
        assert "Indoor" in formatted or "Outdoor" in formatted

    def test_format_activities_empty_list(self):
        """Test formatting empty activities list."""
        # Given: Empty list
        activities = []

        # When: Formatting activities
        formatted = _format_activities(activities)

        # Then: Should return "no activities" message
        assert "Aucune activité" in formatted or "no activity" in formatted.lower()


class TestFormatWellness:
    """Tests for _format_wellness helper."""

    def test_format_wellness_with_data(self):
        """Test formatting wellness data."""
        # Given: Wellness data
        wellness = SAMPLE_WELLNESS_DATA

        # When: Formatting wellness
        formatted = _format_wellness(wellness)

        # Then: Should contain wellness metrics
        assert "HRV" in formatted
        assert "58" in formatted  # HRV value
        assert "sommeil" in formatted.lower() or "sleep" in formatted.lower()


class TestFormatLearnings:
    """Tests for _format_learnings helper."""

    def test_format_learnings_with_data(self):
        """Test formatting learnings list."""
        # Given: List of learnings
        learnings = SAMPLE_LEARNINGS

        # When: Formatting learnings
        formatted = _format_learnings(learnings)

        # Then: Should contain learning details
        assert "Learning 1" in formatted or "Learning" in formatted
        assert "protocol" in formatted.lower() or "validation" in formatted.lower()

    def test_format_learnings_empty_list(self):
        """Test formatting empty learnings list."""
        # Given: Empty list
        learnings = []

        # When: Formatting learnings
        formatted = _format_learnings(learnings)

        # Then: Should return "no learnings" message
        assert "Aucun" in formatted or "no learning" in formatted.lower()


class TestFormatMetricsEvolution:
    """Tests for _format_metrics_evolution helper."""

    def test_format_metrics_evolution_with_data(self):
        """Test formatting metrics evolution."""
        # Given: Metrics evolution data
        metrics = {
            "start": {"ctl": 100, "atl": 50, "tsb": 10, "hrv": 58},
            "end": {"ctl": 105, "atl": 55, "tsb": 8, "hrv": 58},
        }

        # When: Formatting metrics
        formatted = _format_metrics_evolution(metrics)

        # Then: Should contain start and end metrics
        assert "Début" in formatted or "start" in formatted.lower()
        assert "Fin" in formatted or "end" in formatted.lower()
        assert "CTL" in formatted
        assert "100" in formatted  # Start CTL
        assert "105" in formatted  # End CTL

    def test_format_metrics_evolution_empty_data(self):
        """Test formatting empty metrics evolution."""
        # Given: Empty metrics
        metrics = {"start": {}, "end": {}}

        # When: Formatting metrics
        formatted = _format_metrics_evolution(metrics)

        # Then: Should return "not available" message
        assert "non disponibles" in formatted.lower() or "not available" in formatted.lower()


class TestCalculateTSSPercentage:
    """Tests for _calculate_tss_percentage helper."""

    def test_calculate_tss_percentage_normal(self):
        """Test TSS percentage calculation."""
        # Given: Planned and realized TSS
        tss_planned = 450
        tss_realized = 423

        # When: Calculating percentage
        percentage = _calculate_tss_percentage(tss_planned, tss_realized)

        # Then: Should calculate correctly (423/450 = 94%)
        assert percentage == 94

    def test_calculate_tss_percentage_zero_planned(self):
        """Test TSS percentage with zero planned."""
        # Given: Zero planned TSS
        tss_planned = 0
        tss_realized = 100

        # When: Calculating percentage
        percentage = _calculate_tss_percentage(tss_planned, tss_realized)

        # Then: Should return 0 (avoid division by zero)
        assert percentage == 0

    def test_calculate_tss_percentage_over_100(self):
        """Test TSS percentage over 100%."""
        # Given: Realized exceeds planned
        tss_planned = 400
        tss_realized = 500

        # When: Calculating percentage
        percentage = _calculate_tss_percentage(tss_planned, tss_realized)

        # Then: Should calculate correctly (500/400 = 125%)
        assert percentage == 125
