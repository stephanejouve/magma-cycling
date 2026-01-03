"""
Tests for DailyAggregator concrete implementation.

GARTNER_TIME: I
STATUS: Development
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Author: Claude Code
Created: 2025-12-26
"""

import json

import pytest

from cyclisme_training_logs.analyzers.daily_aggregator import DailyAggregator


@pytest.fixture
def temp_training_dir(tmp_path):
    """Créer structure training-logs temporaire pour tests."""
    training_dir = tmp_path / "training-logs"
    training_dir.mkdir()

    # Créer fichier feedback
    feedback_file = training_dir / "daily-feedback.json"
    feedback_data = {
        "entries": [
            {
                "activity_id": "i123456789",
                "notes": "Séance difficile mais bonne exécution",
                "rpe": 8,
            }
        ]
    }
    feedback_file.write_text(json.dumps(feedback_data, indent=2))

    # Créer fichier workflow state
    state_file = training_dir / ".workflow_state.json"
    state_data = {"step_3_completed": True, "activity_id": "i123456789"}
    state_file.write_text(json.dumps(state_data, indent=2))

    # Créer fichier power zones
    zones_file = training_dir / "power-zones.json"
    zones_data = {
        "ftp": 220,
        "zones": {
            "z1": [0, 121],
            "z2": [122, 165],
            "z3": [166, 187],
            "z4": [188, 209],
            "z5": [210, 242],
            "z6": [243, 999],
        },
    }
    zones_file.write_text(json.dumps(zones_data, indent=2))

    return training_dir


def test_daily_aggregator_initialization(temp_training_dir):
    """Test initialisation DailyAggregator."""
    aggregator = DailyAggregator(activity_id="i123456789", data_dir=temp_training_dir)

    assert aggregator.activity_id == "i123456789"
    assert aggregator.data_dir == temp_training_dir
    assert aggregator.feedback_file.exists()
    assert aggregator.workflow_state_file.exists()
    assert aggregator.power_zones_file.exists()


def test_collect_raw_data(temp_training_dir):
    """Test collecte données brutes."""
    aggregator = DailyAggregator(activity_id="i123456789", data_dir=temp_training_dir)

    raw_data = aggregator.collect_raw_data()

    assert "activity" in raw_data
    assert "feedback" in raw_data
    assert "workflow_state" in raw_data
    assert "fitness_metrics" in raw_data
    assert "power_zones" in raw_data

    # Vérifier feedback chargé
    assert raw_data["feedback"]["activity_id"] == "i123456789"
    assert "difficile" in raw_data["feedback"]["notes"]

    # Vérifier workflow state chargé
    assert raw_data["workflow_state"]["step_3_completed"] is True

    # Vérifier power zones chargées
    assert raw_data["power_zones"]["ftp"] == 220


def test_process_data(temp_training_dir):
    """Test traitement données."""
    aggregator = DailyAggregator(activity_id="i123456789", data_dir=temp_training_dir)

    raw_data = aggregator.collect_raw_data()
    processed_data = aggregator.process_data(raw_data)

    # Vérifier structure processed
    assert "workout" in processed_data
    assert "athlete" in processed_data
    assert "feedback" in processed_data
    assert "derived_metrics" in processed_data
    assert "analysis_context" in processed_data

    # Vérifier workout data
    workout = processed_data["workout"]
    assert workout["activity_id"] == "i123456789"
    assert workout["tss"] > 0
    assert workout["duration"] > 0

    # Vérifier athlete data
    athlete = processed_data["athlete"]
    assert athlete["FTP"] == 220
    assert athlete["ctl"] > 0

    # Vérifier feedback
    assert "difficile" in processed_data["feedback"]

    # Vérifier métriques dérivées
    derived = processed_data["derived_metrics"]
    assert "decoupling" in derived
    assert "power_to_weight" in derived
    assert "variability_index" in derived


def test_format_output(temp_training_dir):
    """Test formatage sortie markdown."""
    aggregator = DailyAggregator(activity_id="i123456789", data_dir=temp_training_dir)

    raw_data = aggregator.collect_raw_data()
    processed_data = aggregator.process_data(raw_data)
    output = aggregator.format_output(processed_data)

    # Vérifier format markdown
    assert "###" in output  # Header
    assert "Durée:" in output
    assert "TSS:" in output
    assert "IF:" in output
    assert "Métriques Pré-séance" in output
    assert "CTL:" in output
    assert "ATL:" in output
    assert "TSB:" in output
    assert "Exécution" in output
    assert "Feedback Athlète" in output
    assert "difficile" in output


def test_complete_aggregation_pipeline(temp_training_dir):
    """Test pipeline complet d'agrégation."""
    aggregator = DailyAggregator(activity_id="i123456789", data_dir=temp_training_dir)

    result = aggregator.aggregate()

    assert result.success
    assert "raw" in result.data
    assert "processed" in result.data
    assert "formatted" in result.data

    # Vérifier formatted output
    formatted = result.data["formatted"]
    assert isinstance(formatted, str)
    assert len(formatted) > 100
    assert "TSS:" in formatted


def test_load_feedback_missing_file(tmp_path):
    """Test chargement feedback fichier inexistant."""
    aggregator = DailyAggregator(activity_id="i999999999", data_dir=tmp_path)

    feedback = aggregator._load_feedback()

    assert feedback == {}


def test_load_feedback_wrong_activity(temp_training_dir):
    """Test chargement feedback activité non trouvée."""
    aggregator = DailyAggregator(
        activity_id="i999999999", data_dir=temp_training_dir  # ID non présent
    )

    feedback = aggregator._load_feedback()

    assert feedback == {}


def test_calculate_derived_metrics(temp_training_dir):
    """Test calcul métriques dérivées."""
    aggregator = DailyAggregator(activity_id="i123456789", data_dir=temp_training_dir)

    workout = {"average_power": 180, "normalized_power": 185, "average_hr": 145}

    athlete = {"weight": 75, "FTP": 220}

    derived = aggregator._calculate_derived_metrics(workout, athlete)

    assert "power_to_weight" in derived
    assert derived["power_to_weight"] == pytest.approx(180 / 75, rel=0.01)

    assert "variability_index" in derived
    assert derived["variability_index"] == pytest.approx(185 / 180, rel=0.01)

    assert "decoupling" in derived


def test_classify_fitness_state(temp_training_dir):
    """Test classification état fitness."""
    aggregator = DailyAggregator(activity_id="i123456789", data_dir=temp_training_dir)

    # Fresh
    assert aggregator._classify_fitness_state({"tsb": 15}) == "fresh"

    # Optimal
    assert aggregator._classify_fitness_state({"tsb": 5}) == "optimal"
    assert aggregator._classify_fitness_state({"tsb": -5}) == "optimal"

    # Fatigued
    assert aggregator._classify_fitness_state({"tsb": -15}) == "fatigued"

    # Overreached
    assert aggregator._classify_fitness_state({"tsb": -25}) == "overreached"


def test_classify_intensity(temp_training_dir):
    """Test classification intensité workout."""
    aggregator = DailyAggregator(activity_id="i123456789", data_dir=temp_training_dir)

    # Recovery
    assert aggregator._classify_intensity({"intensity_factor": 0.5}) == "recovery"

    # Endurance
    assert aggregator._classify_intensity({"intensity_factor": 0.65}) == "endurance"

    # Tempo
    assert aggregator._classify_intensity({"intensity_factor": 0.80}) == "tempo"

    # Threshold
    assert aggregator._classify_intensity({"intensity_factor": 0.90}) == "threshold"

    # VO2max
    assert aggregator._classify_intensity({"intensity_factor": 1.0}) == "vo2max"


def test_aggregator_with_missing_files(tmp_path):
    """Test agrégateur avec fichiers manquants (robustesse)."""
    aggregator = DailyAggregator(activity_id="i123456789", data_dir=tmp_path)

    result = aggregator.aggregate()

    # Doit réussir même avec fichiers manquants
    assert result.success
    # Peut avoir des warnings mais pas d'erreurs fatales
    assert len(result.errors) == 0


def test_load_power_zones_missing_file(tmp_path):
    """Test chargement power zones fichier inexistant."""
    aggregator = DailyAggregator(activity_id="i123456789", data_dir=tmp_path)

    zones = aggregator._load_power_zones()

    # Doit retourner FTP par défaut
    assert zones["ftp"] == 220
