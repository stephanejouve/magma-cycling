"""Tests for reports.prompts.workout_history_prompt module.

Tests build_workout_history_prompt and helper formatters:
_format_activities, _format_wellness, _format_learnings,
_format_metrics_evolution, _calculate_tss_percentage.
"""

import pytest

from magma_cycling.reports.prompts.workout_history_prompt import (
    _calculate_tss_percentage,
    _format_activities,
    _format_learnings,
    _format_metrics_evolution,
    _format_wellness,
    build_workout_history_prompt,
)


def _make_week_data(**overrides):
    """Build minimal valid week_data dict."""
    data = {
        "week_number": "S076",
        "start_date": "2026-01-13",
        "end_date": "2026-01-19",
        "tss_planned": 500,
        "tss_realized": 450,
        "activities": [],
        "wellness_data": {},
        "learnings": [],
        "metrics_evolution": {},
    }
    data.update(overrides)
    return data


# ─── build_workout_history_prompt ────────────────────────────────────


class TestBuildWorkoutHistoryPrompt:
    """Tests for build_workout_history_prompt()."""

    def test_valid_prompt_generated(self):
        data = _make_week_data()
        prompt = build_workout_history_prompt(data)
        assert "S076" in prompt
        assert "expert cycling coach" in prompt
        assert "2026-01-13" in prompt

    def test_missing_required_field_raises(self):
        data = _make_week_data()
        del data["week_number"]
        with pytest.raises(ValueError, match="Missing required field: week_number"):
            build_workout_history_prompt(data)

    def test_all_required_fields_checked(self):
        required = [
            "week_number",
            "start_date",
            "end_date",
            "tss_planned",
            "tss_realized",
            "activities",
            "wellness_data",
            "learnings",
            "metrics_evolution",
        ]
        for field in required:
            data = _make_week_data()
            del data[field]
            with pytest.raises(ValueError, match=f"Missing required field: {field}"):
                build_workout_history_prompt(data)

    def test_tss_percentage_in_prompt(self):
        data = _make_week_data(tss_planned=500, tss_realized=450)
        prompt = build_workout_history_prompt(data)
        assert "90%" in prompt

    def test_contains_required_sections(self):
        data = _make_week_data()
        prompt = build_workout_history_prompt(data)
        assert "Contexte Semaine" in prompt
        assert "Chronologie Complète" in prompt
        assert "Métriques Évolution" in prompt
        assert "Enseignements Majeurs" in prompt

    def test_contains_quality_checklist(self):
        data = _make_week_data()
        prompt = build_workout_history_prompt(data)
        assert "Quality Checklist" in prompt
        assert "Word count" in prompt

    def test_activities_included(self):
        activities = [
            {
                "name": "Z2 Base",
                "start_date": "2026-01-13",
                "type": "Ride",
                "tss": 85,
                "moving_time": 5400,
                "if_": 0.72,
                "np": 180,
                "avg_hr": 135,
                "indoor": True,
            }
        ]
        data = _make_week_data(activities=activities)
        prompt = build_workout_history_prompt(data)
        assert "Z2 Base" in prompt
        assert "Indoor" in prompt


# ─── _format_activities ──────────────────────────────────────────────


class TestFormatActivities:
    """Tests for _format_activities()."""

    def test_empty_activities(self):
        result = _format_activities([])
        assert "Aucune activité" in result

    def test_single_activity(self):
        activities = [
            {
                "name": "Z2 Base Indoor",
                "start_date": "2026-01-13",
                "type": "Ride",
                "tss": 85,
                "moving_time": 5400,
                "if_": 0.72,
                "np": 180,
                "avg_hr": 135,
                "indoor": True,
            }
        ]
        result = _format_activities(activities)
        assert "Session 1: Z2 Base Indoor" in result
        assert "TSS: 85" in result
        assert "Durée: 90 minutes" in result
        assert "IF: 0.72" in result
        assert "Indoor" in result

    def test_outdoor_activity(self):
        activities = [
            {
                "name": "Long Ride",
                "start_date": "2026-01-14",
                "type": "Ride",
                "tss": 120,
                "moving_time": 7200,
                "if_": 0.68,
                "np": 170,
                "avg_hr": 128,
                "indoor": False,
            }
        ]
        result = _format_activities(activities)
        assert "Outdoor" in result

    def test_multiple_activities(self):
        activities = [
            {"name": "Session A", "moving_time": 3600},
            {"name": "Session B", "moving_time": 5400},
        ]
        result = _format_activities(activities)
        assert "Session 1:" in result
        assert "Session 2:" in result

    def test_missing_fields_use_defaults(self):
        activities = [{}]
        result = _format_activities(activities)
        assert "Session sans nom" in result
        assert "Date inconnue" in result


# ─── _format_wellness ────────────────────────────────────────────────


class TestFormatWellness:
    """Tests for _format_wellness()."""

    def test_full_data(self):
        wellness = {
            "hrv_avg": 55,
            "hrv_trend": "improving",
            "sleep_quality_avg": 7.5,
            "fatigue_score_avg": 3.2,
            "readiness_avg": 8.1,
        }
        result = _format_wellness(wellness)
        assert "55" in result
        assert "improving" in result
        assert "7.5" in result

    def test_empty_data_defaults(self):
        result = _format_wellness({})
        assert "N/A" in result
        assert "stable" in result


# ─── _format_learnings ───────────────────────────────────────────────


class TestFormatLearnings:
    """Tests for _format_learnings()."""

    def test_empty_learnings(self):
        result = _format_learnings([])
        assert "Aucun apprentissage" in result

    def test_single_learning(self):
        learnings = [
            {
                "type": "protocol",
                "title": "Z2 Indoor Validated",
                "description": "90min Z2 indoor protocol confirmed",
                "confidence": "high",
            }
        ]
        result = _format_learnings(learnings)
        assert "Learning 1: Z2 Indoor Validated" in result
        assert "protocol" in result
        assert "high" in result

    def test_multiple_learnings(self):
        learnings = [
            {"title": "A", "description": "First"},
            {"title": "B", "description": "Second"},
        ]
        result = _format_learnings(learnings)
        assert "Learning 1:" in result
        assert "Learning 2:" in result

    def test_missing_fields_defaults(self):
        learnings = [{}]
        result = _format_learnings(learnings)
        assert "Apprentissage" in result
        assert "medium" in result


# ─── _format_metrics_evolution ───────────────────────────────────────


class TestFormatMetricsEvolution:
    """Tests for _format_metrics_evolution()."""

    def test_full_data(self):
        evolution = {
            "start": {"ctl": 40, "atl": 35, "tsb": 5, "hrv": 55},
            "end": {"ctl": 42, "atl": 38, "tsb": 4, "hrv": 53},
        }
        result = _format_metrics_evolution(evolution)
        assert "CTL: 40" in result
        assert "CTL: 42" in result
        assert "Début de semaine" in result
        assert "Fin de semaine" in result

    def test_empty_data(self):
        result = _format_metrics_evolution({})
        assert "non disponibles" in result

    def test_missing_start(self):
        result = _format_metrics_evolution({"end": {"ctl": 42}})
        assert "non disponibles" in result

    def test_missing_end(self):
        result = _format_metrics_evolution({"start": {"ctl": 40}})
        assert "non disponibles" in result

    def test_partial_metrics(self):
        evolution = {"start": {"ctl": 40}, "end": {"ctl": 42}}
        result = _format_metrics_evolution(evolution)
        assert "CTL: 40" in result
        assert "N/A" in result  # Missing fields show N/A


# ─── _calculate_tss_percentage ───────────────────────────────────────


class TestCalculateTssPercentage:
    """Tests for _calculate_tss_percentage()."""

    def test_normal_percentage(self):
        assert _calculate_tss_percentage(500, 450) == 90

    def test_over_100_percent(self):
        assert _calculate_tss_percentage(400, 480) == 120

    def test_zero_planned(self):
        assert _calculate_tss_percentage(0, 100) == 0

    def test_zero_realized(self):
        assert _calculate_tss_percentage(500, 0) == 0

    def test_exact_match(self):
        assert _calculate_tss_percentage(500, 500) == 100

    def test_rounding(self):
        # 333/500 = 66.6 → 67
        assert _calculate_tss_percentage(500, 333) == 67
