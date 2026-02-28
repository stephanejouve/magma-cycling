#!/usr/bin/env python3
"""
tests/test_asservissement.py - Tests pour fonctionnalités asservissement.
"""
import pytest

from magma_cycling.workflow_coach import WorkflowCoach


def test_load_workout_templates():
    """Test chargement catalogue templates."""
    coach = WorkflowCoach(servo_mode=True)

    templates = coach.workout_templates

    assert len(templates) == 6
    assert "recovery_active_30tss" in templates
    assert templates["recovery_active_30tss"]["tss"] == 30


def test_load_remaining_sessions():
    """Test chargement planning restant."""
    coach = WorkflowCoach()

    # Test with existing week planning
    remaining = coach.load_remaining_sessions("S072")

    assert isinstance(remaining, list)
    # Note: actual content depends on current date


def test_format_remaining_sessions_compact():
    """Test format compact planning."""
    coach = WorkflowCoach()

    remaining = [
        {
            "session_id": "S072-03",
            "date": "2025-12-18",
            "name": "Endurance",
            "type": "END",
            "version": "V001",
            "tss_planned": 45,
            "status": "planned",
        },
        {
            "session_id": "S072-04",
            "date": "2025-12-19",
            "name": "SweetSpot",
            "type": "INT",
            "version": "V001",
            "tss_planned": 55,
            "status": "planned",
        },
    ]

    formatted = coach.format_remaining_sessions_compact(remaining)

    assert "S072-03-END-Endurance-V001" in formatted
    assert "45 TSS" in formatted
    assert "2 séances" in formatted


def test_parse_modifications_empty():
    """Test parsing sans modification."""
    coach = WorkflowCoach()

    ai_response = "# Analyse\n\nTout va bien, planning maintenu."

    mods = coach.parse_ai_modifications(ai_response)

    assert mods == []


def test_parse_modifications_valid():
    """Test parsing avec modification valide."""
    coach = WorkflowCoach()

    ai_response = """
# Analyse

## Recommandations
```json
{"modifications": [{
  "action": "lighten",
  "target_date": "2025-12-18",
  "current_workout": "S072-03-END-V001",
  "template_id": "recovery_active_30tss",
  "reason": "HRV -15%"
}]}
```
"""
    mods = coach.parse_ai_modifications(ai_response)

    assert len(mods) == 1
    assert mods[0]["action"] == "lighten"
    assert mods[0]["template_id"] == "recovery_active_30tss"


def test_extract_day_number():
    """Test extraction numéro jour."""
    coach = WorkflowCoach()

    # Test with known week (S072 starts 2025-12-15, Monday)
    day_num = coach._extract_day_number("2025-12-18", "S072")

    assert day_num == 4  # 2025-12-18 (Thursday) is day 4 of week starting 2025-12-15 (Monday)


def test_templates_have_required_fields():
    """Test que tous les templates ont les champs requis."""
    coach = WorkflowCoach(servo_mode=True)

    required_fields = [
        "id",
        "name",
        "type",
        "tss",
        "duration_minutes",
        "description",
        "workout_code_pattern",
        "intervals_icu_format",
    ]

    for template_id, template in coach.workout_templates.items():
        for field in required_fields:
            assert field in template, f"Template {template_id} manque le champ {field}"


def test_apply_planning_modifications_empty():
    """Test application modifications vide."""
    coach = WorkflowCoach()

    # Should not raise exception with empty list
    coach.apply_planning_modifications([], "S072")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
