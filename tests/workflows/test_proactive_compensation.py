#!/usr/bin/env python3
"""
Unit tests for proactive TSS compensation module.

Tests couvrent :
- Détection déficit TSS (5 tests)
- Collection contexte (4 tests)
- Génération prompt & parsing (3 tests)
- Matrice stratégies (6 tests)
- Intégration (2 tests)

Total: 20 tests unitaires

Author: Claude Code
Created: 2026-01-29 (Sprint S080)
"""

from datetime import date
from unittest.mock import MagicMock

import pytest

from cyclisme_training_logs.intelligence.compensation_strategies import (
    CompensationAction,
    CompensationStrategy,
    get_strategy_matrix,
    select_strategies,
)
from cyclisme_training_logs.workflows.proactive_compensation import (
    _collect_compensation_context,
    _get_weather_forecast,
    _identify_available_rest_days,
    _identify_cancelled_sessions,
    _parse_cancelled_notes_tss,
    _parse_event_planned_tss,
    evaluate_weekly_deficit,
    format_compensation_section,
    generate_compensation_prompt,
    parse_ai_compensation_response,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_client():
    """Mock IntervalsClient for testing."""
    client = MagicMock()

    # Mock get_events (planned workouts + cancelled notes)
    client.get_events.return_value = [
        {
            "id": 1,
            "start_date_local": "2026-01-27T09:00:00",
            "category": "WORKOUT",
            "name": "Endurance 60min",
            "load": 60,
            "type": "Ride",
            "description": "Endurance Base (60min, 60 TSS)\n\nWarmup\n- 10m ramp 50-65%",
        },
        {
            "id": 2,
            "start_date_local": "2026-01-29T10:00:00",
            "category": "WORKOUT",
            "name": "Sweet Spot 2x10",
            "load": 55,
            "type": "Ride",
            "indoor": True,
            "description": "Sweet Spot 2x10 (50min, 55 TSS)\n\nMain set\n- 2x10m 90%",
        },
        {
            "id": 3,
            "start_date_local": "2026-01-31T09:00:00",
            "category": "WORKOUT",
            "name": "Tempo 45min",
            "load": 45,
            "type": "Ride",
            "description": "Tempo 45min (45min, 45 TSS)\n\nMain set\n- 30m 82%",
        },
        # Note: Cancelled session (TSS lost should be parsed)
        {
            "id": 4,
            "start_date_local": "2026-01-28T10:00:00",
            "category": "NOTE",
            "name": "[ANNULÉE] Intervals VO2",
            "description": "❌ SÉANCE ANNULÉE\nRaison: Fatigue\n\n--- Description originale ---\nIntervals VO2 5x3min (50min, 50 TSS)",
        },
    ]

    # Mock get_activities (completed workouts)
    client.get_activities.return_value = [
        {
            "id": 101,
            "start_date_local": "2026-01-27T09:15:00",
            "icu_training_load": 60,
            "name": "Endurance morning",
        }
    ]

    # Mock get_wellness (athlete metrics)
    client.get_wellness.return_value = {
        "ctl": 50,
        "atl": 45,
        "sleepSecs": 28800,  # 8h
        "hrv": 65,
        "rpe": 6,
        "weight": 72,
    }

    return client


@pytest.fixture
def sample_context():
    """Sample context for testing."""
    return {
        "deficit": 60,
        "deficit_pct": 20,
        "cancelled_sessions": [
            {"date": "2026-01-29", "name": "Sweet Spot", "tss": 55, "type": "Ride"}
        ],
        "remaining_sessions": [
            {
                "start_date_local": "2026-01-31T09:00:00",
                "name": "Tempo 45min",
                "load": 45,
            }
        ],
        "days_remaining": 2,
        "athlete_state": {"tsb": 5, "sleep_hours": 8, "hrv": 65, "rpe": 6, "weight": 72},
        "rest_days": [{"day_name": "Dimanche", "date": "2026-02-01", "weekday": 6}],
        "indoor_sessions": [{"name": "Sweet Spot", "load": 55}],
        "weather": {
            "avg_temp_celsius": 10,
            "precipitation_mm": 5,
            "suitable_outdoor": True,
            "note": "Mock data",
        },
        "week_id": "S078",
        "check_date": "2026-01-30",
    }


@pytest.fixture
def sample_recommendations():
    """Sample AI recommendations for testing."""
    return {
        "strategy": "combined",
        "actions": [
            {
                "type": "convert_outdoor",
                "session": "Tempo 45min",
                "from_tss": 45,
                "to_tss": 55,
                "gain": 10,
                "rationale": "Météo favorable, gain TSS outdoor",
            },
            {
                "type": "use_rest_day",
                "session": "Dimanche",
                "from_tss": 0,
                "to_tss": 50,
                "gain": 50,
                "rationale": "Forme excellente (TSB +5), repos disponible",
            },
        ],
        "total_compensated": 60,
        "conditions_required": ["Météo >5°C", "TSB >+5"],
        "overall_rationale": "Déficit compensable avec forme actuelle. Météo favorable permet sortie outdoor.",
    }


# ============================================================================
# Tests: Déficit Detection (5 tests)
# ============================================================================


def test_evaluate_weekly_deficit_below_threshold(mock_client):
    """Déficit < 50 TSS → Pas d'intervention."""
    # Setup: Only 1 session missed (45 TSS)
    mock_client.get_events.return_value = [
        {
            "start_date_local": "2026-01-29T10:00:00",
            "category": "WORKOUT",
            "name": "Tempo",
            "load": 45,
            "description": "Tempo 45min (45min, 45 TSS)\n\nMain set\n- 30m 82%",
        }
    ]
    mock_client.get_activities.return_value = []  # Nothing completed

    result = evaluate_weekly_deficit(
        week_id="S078", check_date=date(2026, 1, 30), client=mock_client, threshold_tss=50
    )

    assert result is None  # Below threshold, no intervention


def test_evaluate_weekly_deficit_above_threshold(mock_client):
    """Déficit > 50 TSS → Intervention nécessaire."""
    # Setup: 2 sessions missed (60 + 55 = 115 TSS)
    mock_client.get_activities.return_value = []  # Nothing completed

    result = evaluate_weekly_deficit(
        week_id="S078", check_date=date(2026, 1, 30), client=mock_client, threshold_tss=50
    )

    assert result is not None
    assert result["deficit"] > 50
    assert "cancelled_sessions" in result


def test_evaluate_weekly_deficit_calculates_correctly(mock_client):
    """Vérifie calcul déficit précis."""
    result = evaluate_weekly_deficit(
        week_id="S078", check_date=date(2026, 1, 30), client=mock_client
    )

    # Planned workouts (before check_date): 60 + 55 = 115 TSS
    # Lost TSS (cancelled note 28/01): 50 TSS
    # Total planned: 115 + 50 = 165 TSS
    # Completed: 60 TSS
    # Deficit: 165 - 60 = 105 TSS
    assert result is not None
    assert result["deficit"] == 105


def test_evaluate_weekly_deficit_with_zero_completed(mock_client):
    """Semaine sans activités complétées."""
    mock_client.get_activities.return_value = []

    result = evaluate_weekly_deficit(
        week_id="S078", check_date=date(2026, 1, 30), client=mock_client
    )

    assert result is not None
    # Planned workouts: 60 + 55 = 115 TSS
    # Lost TSS (note): 50 TSS
    # Total planned: 165 TSS
    # Completed: 0 TSS
    # Deficit: 165 TSS
    assert result["deficit"] == 165


def test_evaluate_weekly_deficit_with_surplus(mock_client):
    """Plus de TSS complété que planifié (surplus, pas déficit)."""
    # Setup: More activities completed than planned
    mock_client.get_activities.return_value = [
        {"start_date_local": "2026-01-27T09:00:00", "icu_training_load": 60},
        {"start_date_local": "2026-01-29T10:00:00", "icu_training_load": 70},  # Extra
    ]

    result = evaluate_weekly_deficit(
        week_id="S078", check_date=date(2026, 1, 30), client=mock_client, threshold_tss=50
    )

    # Surplus case: deficit is negative, but abs < threshold
    # Planned: 115, Completed: 130, Deficit: -15
    # abs(deficit) < 50 → No intervention
    assert result is None


# ============================================================================
# Tests: Contexte Collection (4 tests)
# ============================================================================


def test_collect_compensation_context_complete(mock_client):
    """Contexte complet avec toutes les données."""
    planned_events = mock_client.get_events()
    completed = mock_client.get_activities()

    context = _collect_compensation_context(
        week_id="S078",
        check_date=date(2026, 1, 30),
        deficit=55,
        planned_events=planned_events,
        completed_activities=completed,
        client=mock_client,
    )

    # Verify all required keys present
    assert "deficit" in context
    assert "athlete_state" in context
    assert "remaining_sessions" in context
    assert "cancelled_sessions" in context
    assert "days_remaining" in context
    assert context["deficit"] == 55


def test_identify_cancelled_sessions_two_missed():
    """Détecte 2 séances manquées."""
    planned = [
        {"start_date_local": "2026-01-27T09:00:00", "name": "Session 1", "load": 60},
        {"start_date_local": "2026-01-29T10:00:00", "name": "Session 2", "load": 55},
        {"start_date_local": "2026-01-31T09:00:00", "name": "Session 3", "load": 45},
    ]
    completed = [{"start_date_local": "2026-01-27T09:15:00"}]  # Only first session completed

    cancelled = _identify_cancelled_sessions(planned, completed, date(2026, 1, 30))

    # Session 2 was missed (before check_date)
    # Session 3 is in the future (after check_date)
    assert len(cancelled) == 1
    assert cancelled[0]["name"] == "Session 2"
    assert cancelled[0]["tss"] == 55


def test_parse_cancelled_notes_single_note():
    """Parse une note annulée avec TSS."""
    events = [
        {
            "category": "NOTE",
            "name": "[ANNULÉE] SS030-Ride-Sweet Spot 2x10-v1",
            "description": "❌ SÉANCE ANNULÉE\nRaison: Fatigue\n\n--- Description originale ---\nSweet Spot 2x10min (60min, 60 TSS)",
        }
    ]

    lost_tss = _parse_cancelled_notes_tss(events)

    assert lost_tss == 60.0


def test_parse_cancelled_notes_multiple_notes():
    """Parse plusieurs notes annulées."""
    events = [
        {
            "category": "NOTE",
            "name": "[ANNULÉE] Session 1",
            "description": "❌ SÉANCE ANNULÉE\n...\n(60min, 60 TSS)",
        },
        {
            "category": "NOTE",
            "name": "[SAUTÉE] Session 2",
            "description": "⏭️ SÉANCE SAUTÉE\n...\n(45min, 45 TSS)",
        },
        {
            "category": "NOTE",
            "name": "[REMPLACÉE] Session 3",
            "description": "🔄 SÉANCE REMPLACÉE\n...\n(90min, 85 TSS)",
        },
        {
            "category": "WORKOUT",  # Should be ignored
            "name": "Normal workout",
            "load": 50,
        },
    ]

    lost_tss = _parse_cancelled_notes_tss(events)

    # 60 + 45 + 85 = 190 TSS
    assert lost_tss == 190.0


def test_parse_cancelled_notes_no_notes():
    """Aucune note annulée."""
    events = [
        {"category": "WORKOUT", "name": "Session 1", "load": 60},
        {"category": "NOTE", "name": "Regular note", "description": "Just a note"},
    ]

    lost_tss = _parse_cancelled_notes_tss(events)

    assert lost_tss == 0.0


def test_parse_event_planned_tss_from_workout():
    """Parse TSS depuis description d'un workout."""
    event = {
        "category": "WORKOUT",
        "name": "Endurance Base",
        "description": "Endurance Base (75min, 56 TSS)\n\nWarmup\n- 12m ramp 50-65%",
    }

    tss = _parse_event_planned_tss(event)

    assert tss == 56.0


def test_parse_event_planned_tss_from_note():
    """Parse TSS depuis description d'une note annulée."""
    event = {
        "category": "NOTE",
        "name": "[ANNULÉE] Sweet Spot",
        "description": "❌ SÉANCE ANNULÉE\n...\n--- Description originale ---\nSweet Spot 3x10 (74min, 82 TSS)",
    }

    tss = _parse_event_planned_tss(event)

    assert tss == 82.0


def test_parse_event_planned_tss_no_match():
    """Pas de TSS parsable."""
    event = {
        "category": "NOTE",
        "name": "Regular note",
        "description": "Just a note without TSS",
    }

    tss = _parse_event_planned_tss(event)

    assert tss == 0.0


def test_identify_available_rest_days_sunday_free():
    """Dimanche disponible comme repos."""
    # 2026-01-30 is Friday (weekday=4)
    # Remaining sessions: Saturday only
    # Sunday should be free
    remaining_sessions = [
        {"start_date_local": "2026-01-31T10:00:00"},  # Saturday (weekday=5)
        # Sunday (weekday=6) is free
    ]

    rest_days = _identify_available_rest_days(remaining_sessions, date(2026, 1, 30))

    # New format: list of dicts with day_name, date, weekday
    # Friday=4, planned: [5], free: [6] = Dimanche (pas Vendredi car c'est aujourd'hui)
    assert len(rest_days) == 1
    assert rest_days[0]["day_name"] == "Dimanche"
    assert rest_days[0]["date"] == "2026-02-01"
    assert rest_days[0]["weekday"] == 6


def test_get_weather_forecast_returns_dict():
    """Météo retourne structure attendue."""
    weather = _get_weather_forecast(date(2026, 2, 10))

    assert isinstance(weather, dict)
    assert "avg_temp_celsius" in weather
    assert "suitable_outdoor" in weather
    assert weather["note"] == "Mock data - TODO: real API integration"


# ============================================================================
# Tests: Prompt Generation & Parsing (3 tests)
# ============================================================================


def test_generate_compensation_prompt_includes_deficit(sample_context):
    """Prompt contient le déficit TSS."""
    prompt = generate_compensation_prompt(sample_context)

    assert "Déficit hebdomadaire" in prompt
    assert "-60 TSS" in prompt or "-60.0 TSS" in prompt
    assert "6 Stratégies Disponibles" in prompt


def test_parse_ai_response_valid_json():
    """Parse correctement JSON valide."""
    response = """{
        "strategy": "combined",
        "actions": [
            {"type": "intensify", "session": "Tempo", "gain": 15, "rationale": "Forme OK"}
        ],
        "total_compensated": 60
    }"""

    data = parse_ai_compensation_response(response)

    assert data is not None
    assert data["strategy"] == "combined"
    assert len(data["actions"]) == 1
    assert data["total_compensated"] == 60


def test_parse_ai_response_with_markdown():
    """Parse JSON même avec markdown backticks."""
    response = """```json
    {
        "strategy": "single",
        "actions": [{"type": "accept_deficit", "gain": 0, "rationale": "Fatigue"}],
        "total_compensated": 0
    }
    ```"""

    data = parse_ai_compensation_response(response)

    assert data is not None
    assert data["strategy"] == "single"


# ============================================================================
# Tests: Strategies Matrix (6 tests)
# ============================================================================


def test_strategy_intensify_conditions():
    """Stratégie INTENSIFY applicable si forme excellente."""
    context = {
        "athlete_state": {"tsb": 8, "sleep_hours": 7.5},
        "days_remaining": 4,
        "indoor_sessions": [],
        "weather": {"suitable_outdoor": False},
    }

    strategies = select_strategies(context)

    assert CompensationStrategy.INTENSIFY in strategies


def test_strategy_add_short_applicable():
    """Stratégie ADD_SHORT si peu de jours restants."""
    context = {
        "athlete_state": {"tsb": 3, "sleep_hours": 7},
        "days_remaining": 2,
        "indoor_sessions": [],
        "weather": {"suitable_outdoor": False},
    }

    strategies = select_strategies(context)

    assert CompensationStrategy.ADD_SHORT in strategies


def test_strategy_convert_outdoor_weather_suitable():
    """Stratégie CONVERT_OUTDOOR si météo favorable."""
    context = {
        "athlete_state": {"tsb": 5, "sleep_hours": 7},
        "days_remaining": 3,
        "indoor_sessions": [{"name": "SS"}],
        "weather": {"suitable_outdoor": True},
    }

    strategies = select_strategies(context)

    assert CompensationStrategy.CONVERT_OUTDOOR in strategies


def test_strategy_use_rest_day_tsb_positive():
    """Stratégie USE_REST_DAY si TSB >+5."""
    context = {
        "athlete_state": {"tsb": 7, "sleep_hours": 8},
        "days_remaining": 3,
        "rest_days": ["Dimanche"],
        "indoor_sessions": [],
        "weather": {"suitable_outdoor": True},
    }

    strategies = select_strategies(context)

    assert CompensationStrategy.USE_REST_DAY in strategies


def test_strategy_partial_report_late_week():
    """Stratégie PARTIAL_REPORT si trop tard dans semaine."""
    context = {
        "athlete_state": {"tsb": 3, "sleep_hours": 7},
        "days_remaining": 0,
        "indoor_sessions": [],
        "weather": {"suitable_outdoor": True},
    }

    strategies = select_strategies(context)

    assert CompensationStrategy.PARTIAL_REPORT in strategies


def test_strategy_accept_deficit_fatigue():
    """Stratégie ACCEPT_DEFICIT si fatigue détectée."""
    context = {
        "athlete_state": {"tsb": -5, "sleep_hours": 5.5},
        "days_remaining": 3,
        "indoor_sessions": [],
        "weather": {"suitable_outdoor": True},
    }

    strategies = select_strategies(context)

    assert CompensationStrategy.ACCEPT_DEFICIT in strategies


# ============================================================================
# Tests: Integration (2 tests)
# ============================================================================


def test_format_compensation_section_includes_all_data(sample_context, sample_recommendations):
    """Section email contient toutes les données."""
    section = format_compensation_section(sample_context, sample_recommendations)

    assert "Compensation TSS Proactive" in section
    assert "S078" in section
    assert "-60" in section
    assert "COMBINED" in section
    assert "Action 1" in section
    assert "Action 2" in section


def test_compensation_action_to_dict():
    """CompensationAction sérialise correctement."""
    action = CompensationAction(
        strategy=CompensationStrategy.INTENSIFY,
        target_session="Mercredi SS",
        tss_gain=15,
        conditions=["Forme OK"],
        rationale="Déficit léger",
    )

    data = action.to_dict()

    assert data["strategy"] == "intensify"
    assert data["target_session"] == "Mercredi SS"
    assert data["tss_gain"] == 15
    assert "Forme OK" in data["conditions"]
    assert data["rationale"] == "Déficit léger"


# ============================================================================
# Tests: Strategy Matrix (1 bonus test)
# ============================================================================


def test_get_strategy_matrix_structure():
    """Matrice stratégies bien structurée."""
    matrix = get_strategy_matrix()

    assert "excellent_form_many_days" in matrix
    assert "good_form_few_days" in matrix
    assert "low_form_or_fatigue" in matrix
    assert "too_late_in_week" in matrix

    # Check structure
    for _situation, data in matrix.items():
        assert "description" in data
        assert "conditions" in data
        assert "strategies" in data
        assert "priority" in data
        assert isinstance(data["strategies"], list)
