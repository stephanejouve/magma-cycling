"""Tests for reports.prompts.bilan_final_prompt module.

Tests build_bilan_final_prompt: validation, prompt structure, strategic focus.
"""

import pytest

from magma_cycling.reports.prompts.bilan_final_prompt import build_bilan_final_prompt


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


class TestBuildBilanFinalPrompt:
    """Tests for build_bilan_final_prompt()."""

    def test_valid_prompt_generated(self):
        data = _make_week_data()
        prompt = build_bilan_final_prompt(data)
        assert "S076" in prompt
        assert "strategic" in prompt.lower()
        assert "synthesis" in prompt.lower()

    def test_missing_required_field_raises(self):
        data = _make_week_data()
        del data["week_number"]
        with pytest.raises(ValueError, match="Missing required field: week_number"):
            build_bilan_final_prompt(data)

    def test_contains_bilan_sections(self):
        data = _make_week_data()
        prompt = build_bilan_final_prompt(data)
        assert "Semaine en Chiffres" in prompt
        assert "Métriques Finales" in prompt
        assert "Découvertes Majeures" in prompt
        assert "Conclusion" in prompt

    def test_contains_strategic_constraints(self):
        data = _make_week_data()
        prompt = build_bilan_final_prompt(data)
        assert "SYNTHESIS FOCUS" in prompt
        assert "MAX 3-4 DISCOVERIES" in prompt
        assert "1500 words" in prompt

    def test_tss_percentage_included(self):
        data = _make_week_data(tss_planned=500, tss_realized=450)
        prompt = build_bilan_final_prompt(data)
        assert "90%" in prompt

    def test_activities_formatted(self):
        activities = [
            {
                "name": "SST Intervals",
                "start_date": "2026-01-15",
                "type": "Ride",
                "tss": 95,
                "moving_time": 3600,
                "if_": 0.88,
                "np": 220,
                "avg_hr": 155,
                "indoor": True,
            }
        ]
        data = _make_week_data(activities=activities)
        prompt = build_bilan_final_prompt(data)
        assert "SST Intervals" in prompt

    def test_wellness_formatted(self):
        data = _make_week_data(wellness_data={"hrv_avg": 58, "hrv_trend": "improving"})
        prompt = build_bilan_final_prompt(data)
        assert "58" in prompt
        assert "improving" in prompt

    def test_learnings_formatted(self):
        data = _make_week_data(learnings=[{"title": "Z2 Protocol", "description": "Validated"}])
        prompt = build_bilan_final_prompt(data)
        assert "Z2 Protocol" in prompt

    def test_metrics_evolution_formatted(self):
        data = _make_week_data(
            metrics_evolution={
                "start": {"ctl": 40, "atl": 35},
                "end": {"ctl": 42, "atl": 38},
            }
        )
        prompt = build_bilan_final_prompt(data)
        assert "CTL: 40" in prompt
        assert "CTL: 42" in prompt

    def test_quality_checklist_present(self):
        data = _make_week_data()
        prompt = build_bilan_final_prompt(data)
        assert "Quality Checklist" in prompt
        assert "Word count" in prompt

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
                build_bilan_final_prompt(data)
