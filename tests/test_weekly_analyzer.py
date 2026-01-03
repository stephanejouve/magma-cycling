"""
Tests for WeeklyAnalyzer.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Author: Claude Code
Created: 2025-12-26
"""

import pytest

from cyclisme_training_logs.analyzers.weekly_analyzer import WeeklyAnalyzer


@pytest.fixture
def sample_weekly_data():
    """Données hebdomadaires pour tests."""
    return {
        "summary": {
            "total_tss": 320,
            "avg_tss": 45.7,
            "avg_if": 1.15,
            "total_duration": 21600,
            "final_metrics": {"ctl": 62.5, "atl": 60.0, "tsb": 2.5},
        },
        "workouts": [
            {
                "session_number": 1,
                "date": "2025-01-06",
                "name": "Sweet Spot",
                "tss": 45,
                "if": 1.2,
                "duration": 3600,
                "normalized_power": 180,
                "average_power": 175,
                "average_hr": 140,
                "max_hr": 165,
            },
            {
                "session_number": 2,
                "date": "2025-01-07",
                "name": "Endurance",
                "tss": 50,
                "if": 0.75,
                "duration": 5400,
                "normalized_power": 150,
                "average_power": 148,
                "average_hr": 130,
                "max_hr": 155,
                "feedback": {"rpe": 5, "comments": "Easy pace"},
            },
        ],
        "metrics_evolution": {
            "daily": [
                {"date": "2025-01-06", "ctl": 60, "atl": 58, "tsb": 2},
                {"date": "2025-01-07", "ctl": 61.5, "atl": 59.2, "tsb": 2.3},
            ],
            "trends": {"ctl_change": 2.5, "atl_change": 1.8, "tsb_change": 0.7},
        },
        "learnings": ["2 séances haute charge (TSS >80)", "1 séance intensité élevée (IF >1.0)"],
        "protocol_adaptations": [
            {
                "type": "recovery",
                "reason": "TSB dropped 5 points",
                "recommendation": "Add recovery day",
            }
        ],
        "transition": {
            "current_state": {"total_tss": 320, "avg_tss": 45.7, "final_tsb": 2.5},
            "recommendations": ["Continue progression"],
            "focus_areas": ["High TSS days", "Recovery monitoring"],
        },
        "compliance": {"planned_count": 7, "executed_count": 7, "rate": 100.0},
        "wellness_insights": {"sleep_hours_avg": 7.5, "weight_trend": -0.2},
    }


def test_weekly_analyzer_initialization(sample_weekly_data):
    """Test initialisation WeeklyAnalyzer."""
    analyzer = WeeklyAnalyzer(week="S073", weekly_data=sample_weekly_data)

    assert analyzer.week == "S073"
    assert analyzer.data == sample_weekly_data


def test_generate_workout_history(sample_weekly_data):
    """Test génération workout_history."""
    analyzer = WeeklyAnalyzer(week="S073", weekly_data=sample_weekly_data)

    history = analyzer.generate_workout_history()

    assert "# Historique Entraînements S073" in history
    assert "S073-01" in history
    assert "S073-02" in history
    assert "TSS:** 45" in history
    assert "Sweet Spot" in history
    assert "Endurance" in history


def test_generate_metrics_evolution(sample_weekly_data):
    """Test génération metrics_evolution."""
    analyzer = WeeklyAnalyzer(week="S073", weekly_data=sample_weekly_data)

    metrics = analyzer.generate_metrics_evolution()

    assert "# Évolution Métriques S073" in metrics
    assert "CTL/ATL/TSB Quotidien" in metrics
    assert "2025-01-06" in metrics
    assert "Tendances Hebdomadaires" in metrics
    assert "+2.5" in metrics  # CTL change
    assert "Wellness" in metrics
    assert "7.5h" in metrics  # Sleep


def test_generate_training_learnings(sample_weekly_data):
    """Test génération training_learnings."""
    analyzer = WeeklyAnalyzer(week="S073", weekly_data=sample_weekly_data)

    learnings = analyzer.generate_training_learnings()

    assert "# Enseignements d'Entraînement S073" in learnings
    assert "Découvertes Majeures" in learnings
    assert "haute charge" in learnings
    assert "intensité élevée" in learnings


def test_generate_protocol_adaptations(sample_weekly_data):
    """Test génération protocol_adaptations."""
    analyzer = WeeklyAnalyzer(week="S073", weekly_data=sample_weekly_data)

    adaptations = analyzer.generate_protocol_adaptations()

    assert "# Adaptations Protocoles S073" in adaptations
    assert "Recovery" in adaptations
    assert "TSB dropped" in adaptations
    assert "Add recovery day" in adaptations


def test_generate_transition(sample_weekly_data):
    """Test génération transition."""
    analyzer = WeeklyAnalyzer(week="S073", weekly_data=sample_weekly_data)

    transition = analyzer.generate_transition()

    assert "# Transition S073 → S074" in transition
    assert "État Final S073" in transition
    assert "TSS total :** 320" in transition
    assert "Recommandations S074" in transition
    assert "Points d'Attention" in transition


def test_generate_bilan_final(sample_weekly_data):
    """Test génération bilan_final."""
    analyzer = WeeklyAnalyzer(week="S073", weekly_data=sample_weekly_data)

    bilan = analyzer.generate_bilan_final()

    assert "# Bilan Final S073" in bilan
    assert "Objectifs vs Réalisé" in bilan
    assert "Compliance :** 100.0%" in bilan
    assert "TSS total :** 320" in bilan
    assert "Métriques Clés" in bilan


def test_generate_all_reports(sample_weekly_data):
    """Test génération complète 6 reports."""
    analyzer = WeeklyAnalyzer(week="S073", weekly_data=sample_weekly_data)

    reports = analyzer.generate_all_reports()

    assert len(reports) == 6
    assert "workout_history" in reports
    assert "metrics_evolution" in reports
    assert "training_learnings" in reports
    assert "protocol_adaptations" in reports
    assert "transition" in reports
    assert "bilan_final" in reports

    # Verify each report is not empty
    for name, content in reports.items():
        assert len(content) > 100, f"Report {name} too short"


def test_get_period(sample_weekly_data):
    """Test helper _get_period."""
    analyzer = WeeklyAnalyzer(week="S073", weekly_data=sample_weekly_data)

    period = analyzer._get_period()

    assert "2025-01-06" in period
    assert "2025-01-07" in period
    assert "→" in period


def test_empty_workouts_data():
    """Test analyzer avec données vides."""
    empty_data = {
        "summary": {},
        "workouts": [],
        "metrics_evolution": {},
        "learnings": [],
        "protocol_adaptations": [],
        "transition": {},
        "compliance": {},
    }

    analyzer = WeeklyAnalyzer(week="S073", weekly_data=empty_data)
    reports = analyzer.generate_all_reports()

    assert len(reports) == 6
    for _name, content in reports.items():
        assert "# " in content  # Has header
        assert "S073" in content
