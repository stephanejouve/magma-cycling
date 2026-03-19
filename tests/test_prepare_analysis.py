"""
Tests for prepare_analysis.py - PromptGenerator formatting methods.

Focus: pure formatting functions that don't require external I/O.
Coverage goal: 7% → 60%

Author: Claude Sonnet 4.6
Created: 2026-02-24
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.prepare_analysis import (
    PromptGenerator,
    analyze_batch,
    display_activity_menu,
    main,
)


@pytest.fixture
def generator(tmp_path):
    """PromptGenerator with legacy project_root to bypass get_data_config()."""
    return PromptGenerator(project_root=tmp_path)


class TestFormatActivityData:
    """Test PromptGenerator.format_activity_data."""

    def test_full_activity(self, generator):
        """All fields present → correctly mapped."""
        activity = {
            "id": 12345,
            "name": "Endurance Z2",
            "type": "VirtualRide",
            "start_date_local": "2026-02-23T18:00:00",
            "moving_time": 4620,  # 77 min
            "icu_training_load": 57,
            "icu_intensity": 67,  # 67 → 0.67
            "icu_average_watts": 146,
            "icu_weighted_avg_watts": 149,
            "average_cadence": 85,
            "average_heartrate": 105,
            "max_heartrate": 140,
            "decoupling": 0.8,
            "description": "Séance tardive",
            "feel": 2,
            "source": "ZWIFT",
        }

        data = generator.format_activity_data(activity)

        assert data["id"] == 12345
        assert data["name"] == "Endurance Z2"
        assert data["type"] == "VirtualRide"
        assert data["duration_min"] == 77
        assert data["tss"] == 57
        assert data["intensity"] == pytest.approx(0.67)
        assert data["avg_power"] == 146
        assert data["np"] == 149
        assert data["avg_cadence"] == 85
        assert data["avg_hr"] == 105
        assert data["max_hr"] == 140
        assert data["decoupling"] == 0.8
        assert data["description"] == "Séance tardive"
        assert data["feel"] == 2
        assert data["source"] == "ZWIFT"
        assert data["is_strava"] is False

    def test_strava_source_flagged(self, generator):
        """STRAVA source sets is_strava=True."""
        activity = {
            "start_date_local": "2026-02-23T10:00:00",
            "source": "STRAVA",
        }
        data = generator.format_activity_data(activity)
        assert data["is_strava"] is True

    def test_minimal_activity_defaults(self, generator):
        """Missing optional fields use defaults."""
        activity = {"start_date_local": "2026-02-23T10:00:00"}

        data = generator.format_activity_data(activity)

        assert data["id"] == "Non spécifié"
        assert data["name"] == "Séance"
        assert data["type"] == "Cyclisme"
        assert data["tss"] == 0
        assert data["avg_power"] == 0
        assert data["decoupling"] is None
        assert data["feel"] is None
        assert data["is_strava"] is False

    def test_date_formatted_correctly(self, generator):
        """Date formatted as DD/MM/YYYY."""
        activity = {"start_date_local": "2026-02-23T18:30:00"}
        data = generator.format_activity_data(activity)
        assert data["date"] == "23/02/2026"
        assert data["date_iso"] == "2026-02-23"

    def test_duration_integer_division(self, generator):
        """duration_min uses integer division of moving_time."""
        activity = {"start_date_local": "2026-02-23T10:00:00", "moving_time": 4619}  # 76.98 min
        data = generator.format_activity_data(activity)
        assert data["duration_min"] == 76


class TestFormatFeelValue:
    """Test PromptGenerator._format_feel_value."""

    def test_none_returns_non_renseigne(self, generator):
        assert generator._format_feel_value(None) == "_Non renseigné_"

    def test_feel_1_excellent(self, generator):
        result = generator._format_feel_value(1)
        assert "Excellent" in result

    def test_feel_2_bien(self, generator):
        result = generator._format_feel_value(2)
        assert "Bien" in result

    def test_feel_3_moyen(self, generator):
        result = generator._format_feel_value(3)
        assert "Moyen" in result

    def test_feel_4_passable(self, generator):
        result = generator._format_feel_value(4)
        assert "Passable" in result

    def test_feel_5_mauvais(self, generator):
        result = generator._format_feel_value(5)
        assert "Mauvais" in result

    def test_unknown_value(self, generator):
        result = generator._format_feel_value(99)
        assert "99" in result


class TestFormatAthleteNotes:
    """Test PromptGenerator._format_athlete_notes."""

    def test_description_takes_priority(self, generator):
        result = generator._format_athlete_notes("Ma description", "Mon wellness")
        assert result == "Ma description"

    def test_wellness_fallback_when_no_description(self, generator):
        result = generator._format_athlete_notes("", "Mon wellness")
        assert "Mon wellness" in result
        assert "wellness" in result.lower()

    def test_none_description_falls_back_to_wellness(self, generator):
        result = generator._format_athlete_notes(None, "Commentaire wellness")
        assert "Commentaire wellness" in result

    def test_no_notes_at_all(self, generator):
        result = generator._format_athlete_notes(None, None)
        assert "Aucune note" in result

    def test_empty_strings_return_no_notes(self, generator):
        result = generator._format_athlete_notes("", "")
        assert "Aucune note" in result


class TestFormatTemperatureData:
    """Test PromptGenerator._format_temperature_data."""

    def test_no_weather_data(self, generator):
        result = generator._format_temperature_data(None, None, None, False)
        assert "non disponibles" in result.lower()

    def test_has_weather_but_no_avg(self, generator):
        result = generator._format_temperature_data(None, 5, 10, True)
        assert "non disponibles" in result.lower()

    def test_very_cold(self, generator):
        """< 5°C → very cold context."""
        result = generator._format_temperature_data(2.0, None, None, True)
        assert "2.0°C" in result
        assert "très froid" in result

    def test_cold(self, generator):
        """5-10°C → cold context."""
        result = generator._format_temperature_data(7.0, None, None, True)
        assert "froid" in result

    def test_temperate(self, generator):
        """15-20°C → tempéré context."""
        result = generator._format_temperature_data(18.0, None, None, True)
        assert "tempéré" in result

    def test_hot(self, generator):
        """25-30°C → chaud context."""
        result = generator._format_temperature_data(27.0, None, None, True)
        assert "chaud" in result

    def test_very_hot(self, generator):
        """>= 30°C → très chaud."""
        result = generator._format_temperature_data(32.0, None, None, True)
        assert "très chaud" in result

    def test_with_min_max(self, generator):
        """min/max added to output."""
        result = generator._format_temperature_data(18.0, 12, 24, True)
        assert "12°C" in result
        assert "24°C" in result


class TestFormatWellnessData:
    """Test PromptGenerator.format_wellness_data."""

    def test_none_returns_zeros(self, generator):
        """None wellness returns dict with zeros."""
        result = generator.format_wellness_data(None)
        assert result["ctl"] == 0
        assert result["atl"] == 0
        assert result["tsb"] == 0
        assert result["sleep_seconds"] == 0
        assert result["comments"] == ""

    def test_wellness_ctl_atl_tsb(self, generator):
        """CTL/ATL/TSB correctly extracted."""
        wellness = {"ctl": 50.0, "atl": 60.0}  # TSB = -10
        result = generator.format_wellness_data(wellness)
        assert result["ctl"] == 50.0
        assert result["atl"] == 60.0
        assert result["tsb"] == pytest.approx(-10.0)

    def test_wellness_sleep_and_comments(self, generator):
        """Sleep and comments passed through."""
        wellness = {
            "ctl": 44.0,
            "atl": 52.0,
            "sleepSecs": 16200,  # 4.5h
            "comments": "Fatigue accumulée",
        }
        result = generator.format_wellness_data(wellness)
        assert result["sleep_seconds"] == 16200
        assert result["comments"] == "Fatigue accumulée"

    def test_wellness_weight(self, generator):
        """Weight passed through."""
        wellness = {"ctl": 50.0, "atl": 50.0, "weight": 72.5}
        result = generator.format_wellness_data(wellness)
        assert result["weight"] == 72.5


class TestGetValueHelpers:
    """Test PromptGenerator.get_power_value, get_cadence_value, get_hr_value."""

    def test_get_power_avg(self, generator):
        assert generator.get_power_value({"avg_power": 150}, "avg") == 150

    def test_get_power_fallback_watts(self, generator):
        assert generator.get_power_value({"watts": 155}, "avg") == 155

    def test_get_power_np(self, generator):
        assert generator.get_power_value({"np": 160}, "np") == 160

    def test_get_power_none_when_zero(self, generator):
        assert generator.get_power_value({"avg_power": 0}, "avg") is None

    def test_get_power_empty(self, generator):
        assert generator.get_power_value({}, "avg") is None

    def test_get_cadence_avg(self, generator):
        assert generator.get_cadence_value({"avg_cadence": 85}, "avg") == 85

    def test_get_cadence_fallback(self, generator):
        assert generator.get_cadence_value({"cadence": 90}, "avg") == 90

    def test_get_hr_avg(self, generator):
        assert generator.get_hr_value({"avg_hr": 140}, "avg") == 140

    def test_get_hr_max(self, generator):
        assert generator.get_hr_value({"max_hr": 175}, "max") == 175

    def test_get_hr_none_missing(self, generator):
        assert generator.get_hr_value({}, "avg") is None


class TestSafeFormatMetric:
    """Test PromptGenerator.safe_format_metric."""

    def test_none_returns_default(self, generator):
        assert generator.safe_format_metric(None) == "N/A"

    def test_value_formatted(self, generator):
        assert generator.safe_format_metric(150.3, ".0f", "W") == "150W"

    def test_custom_default(self, generator):
        assert generator.safe_format_metric(None, ".0f", "", "—") == "—"


class TestFormatAthleteFeedback:
    """Test PromptGenerator.format_athlete_feedback."""

    def test_none_returns_none(self, generator):
        assert generator.format_athlete_feedback(None) is None

    def test_empty_dict_returns_none(self, generator):
        assert generator.format_athlete_feedback({}) is None

    def test_rpe_included(self, generator):
        result = generator.format_athlete_feedback({"rpe": 7})
        assert result is not None
        assert "7/10" in result

    def test_ressenti_general(self, generator):
        result = generator.format_athlete_feedback({"ressenti_general": "Bien"})
        assert "Bien" in result

    def test_multiple_fields(self, generator):
        feedback = {
            "rpe": 8,
            "ressenti_general": "Fatigue",
            "notes_libres": "Séance tardive",
        }
        result = generator.format_athlete_feedback(feedback)
        assert "8/10" in result
        assert "Fatigue" in result
        assert "Séance tardive" in result


class TestGeneratePrompt:
    """Test PromptGenerator.generate_prompt — the main prompt builder."""

    @pytest.fixture
    def activity_data(self, generator):
        """Already-formatted activity dict (output of format_activity_data)."""
        raw = {
            "id": 12345,
            "name": "S082-01-END-EnduranceBase-V001",
            "type": "VirtualRide",
            "start_date_local": "2026-02-23T18:00:00",
            "moving_time": 4620,
            "icu_training_load": 57,
            "icu_intensity": 67,
            "icu_average_watts": 146,
            "icu_weighted_avg_watts": 149,
            "average_cadence": 85,
            "average_heartrate": 105,
            "max_heartrate": 140,
            "decoupling": 0.8,
            "description": "Séance tardive",
            "feel": 2,
            "source": "ZWIFT",
        }
        return generator.format_activity_data(raw)

    def test_minimal_prompt_returned_as_string(self, generator, activity_data):
        """Minimal call returns a non-empty string."""
        prompt = generator.generate_prompt(
            activity_data=activity_data,
            wellness_pre=None,
            wellness_post=None,
            athlete_context=None,
            recent_workouts=None,
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_prompt_contains_activity_name(self, generator, activity_data):
        """Activity name appears in the prompt."""
        prompt = generator.generate_prompt(
            activity_data=activity_data,
            wellness_pre=None,
            wellness_post=None,
            athlete_context=None,
            recent_workouts=None,
        )
        assert "S082-01-END-EnduranceBase-V001" in prompt

    def test_prompt_contains_athlete_context(self, generator, activity_data):
        """Athlete context string injected."""
        prompt = generator.generate_prompt(
            activity_data=activity_data,
            wellness_pre=None,
            wellness_post=None,
            athlete_context="Mon profil athlète test",
            recent_workouts=None,
        )
        assert "Mon profil athlète test" in prompt

    def test_prompt_contains_recent_workouts(self, generator, activity_data):
        """Recent workouts injected."""
        prompt = generator.generate_prompt(
            activity_data=activity_data,
            wellness_pre=None,
            wellness_post=None,
            athlete_context=None,
            recent_workouts="### S081 séance récente",
        )
        assert "S081 séance récente" in prompt

    def test_prompt_with_wellness_pre(self, generator, activity_data):
        """Wellness pre-session values appear in prompt."""
        wellness = {"ctl": 44.0, "atl": 52.0, "sleepSecs": 16200}
        prompt = generator.generate_prompt(
            activity_data=activity_data,
            wellness_pre=wellness,
            wellness_post=None,
            athlete_context=None,
            recent_workouts=None,
        )
        assert "44" in prompt  # CTL
        assert "4.5" in prompt  # Sleep hours (16200 / 3600)

    def test_prompt_with_periodization_context(self, generator, activity_data):
        """Periodization context section added when provided."""
        periodization = {
            "phase": "RECONSTRUCTION_BASE",
            "ctl_current": 43.3,
            "ctl_target": 73.0,
            "ctl_deficit": 29.7,
            "ftp_current": 223,
            "ftp_target": 230,
            "weeks_to_target": 11,
            "weekly_tss_load": 350,
            "weekly_tss_recovery": 250,
            "recovery_week_frequency": 2,
            "pid_status": "OVERRIDE",
            "rationale": "CTL critique, reconstruction prioritaire",
        }
        prompt = generator.generate_prompt(
            activity_data=activity_data,
            wellness_pre=None,
            wellness_post=None,
            athlete_context=None,
            recent_workouts=None,
            periodization_context=periodization,
        )
        assert "RECONSTRUCTION_BASE" in prompt
        assert "43.3" in prompt

    def test_prompt_with_athlete_feedback(self, generator, activity_data):
        """Athlete feedback section added when provided."""
        feedback = {"rpe": 6, "ressenti_general": "Bonne séance"}
        prompt = generator.generate_prompt(
            activity_data=activity_data,
            wellness_pre=None,
            wellness_post=None,
            athlete_context=None,
            recent_workouts=None,
            athlete_feedback=feedback,
        )
        assert "6/10" in prompt
        assert "Bonne séance" in prompt

    def test_prompt_no_power_warning(self, generator, activity_data):
        """No power warning when avg_power present."""
        prompt = generator.generate_prompt(
            activity_data=activity_data,
            wellness_pre=None,
            wellness_post=None,
            athlete_context=None,
            recent_workouts=None,
        )
        # avg_power=146 → no warning
        assert "Aucune donnée de puissance" not in prompt

    def test_prompt_no_power_shows_warning(self, generator, activity_data):
        """Power warning shown when no power data."""
        activity_data["avg_power"] = None
        activity_data["np"] = None
        prompt = generator.generate_prompt(
            activity_data=activity_data,
            wellness_pre=None,
            wellness_post=None,
            athlete_context=None,
            recent_workouts=None,
        )
        assert "Aucune donnée de puissance" in prompt

    def test_prompt_strava_warning(self, generator):
        """STRAVA source triggers warning."""
        raw = {
            "id": 99,
            "name": "Strava Ride",
            "start_date_local": "2026-02-23T10:00:00",
            "source": "STRAVA",
        }
        activity_data = generator.format_activity_data(raw)
        prompt = generator.generate_prompt(
            activity_data=activity_data,
            wellness_pre=None,
            wellness_post=None,
            athlete_context=None,
            recent_workouts=None,
        )
        assert "ATTENTION : Activité Strava" in prompt


class TestFormatAthleteFeedbackBranches:
    """Test additional branches in format_athlete_feedback."""

    def test_difficultes(self, generator):
        result = generator.format_athlete_feedback({"difficultes": "Jambes lourdes"})
        assert "Jambes lourdes" in result

    def test_points_positifs(self, generator):
        result = generator.format_athlete_feedback({"points_positifs": "Bon rythme"})
        assert "Bon rythme" in result

    def test_contexte(self, generator):
        result = generator.format_athlete_feedback({"contexte": "Après travail"})
        assert "Après travail" in result

    def test_sensations_physiques(self, generator):
        result = generator.format_athlete_feedback(
            {"sensations_physiques": ["fatigue", "légèreté"]}
        )
        assert "fatigue" in result
        assert "légèreté" in result


class TestTemperatureRanges:
    """Cover the missing temperature range branches."""

    def test_cold_5_10(self, generator):
        result = generator._format_temperature_data(7.5, None, None, True)
        assert "froid" in result

    def test_frais_10_15(self, generator):
        result = generator._format_temperature_data(12.0, None, None, True)
        assert "frais" in result

    def test_agreable_20_25(self, generator):
        result = generator._format_temperature_data(22.0, None, None, True)
        assert "agréable" in result


class TestFormatPower:
    """Test PromptGenerator._format_power."""

    def test_empty_returns_na(self, generator):
        assert generator._format_power({}) == "N/A"

    def test_none_returns_na(self, generator):
        assert generator._format_power(None) == "N/A"

    def test_percent_ftp_value(self, generator):
        result = generator._format_power({"units": "%ftp", "value": 90})
        assert "90%FTP" in result

    def test_percent_ftp_range(self, generator):
        result = generator._format_power({"units": "%ftp", "start": 85, "end": 95})
        assert "85-95%FTP" in result

    def test_watts(self, generator):
        result = generator._format_power({"units": "w", "value": 220})
        assert "220W" in result

    def test_power_zone(self, generator):
        result = generator._format_power({"units": "power_zone", "value": 4})
        assert "Z4" in result

    def test_unknown_units(self, generator):
        result = generator._format_power({"units": "unknown"})
        assert result == "N/A"


class TestFileLoadMethods:
    """Test file-loading methods of PromptGenerator using tmp_path."""

    def test_load_athlete_context_existing(self, tmp_path):
        """load_athlete_context reads file when it exists."""
        gen = PromptGenerator(project_root=tmp_path)
        ref_dir = tmp_path / "references"
        ref_dir.mkdir()
        prompt_file = ref_dir / "project_prompt_v2_1_revised.md"
        prompt_file.write_text("Mon profil athlète", encoding="utf-8")

        result = gen.load_athlete_context()
        assert result == "Mon profil athlète"

    def test_load_athlete_context_missing(self, tmp_path):
        """load_athlete_context returns None when file missing."""
        gen = PromptGenerator(project_root=tmp_path)
        assert gen.load_athlete_context() is None

    def test_load_cycling_concepts_existing(self, tmp_path):
        """load_cycling_concepts reads file when it exists."""
        gen = PromptGenerator(project_root=tmp_path)
        ref_dir = tmp_path / "references"
        ref_dir.mkdir()
        (ref_dir / "cycling_training_concepts.md").write_text("Zones Z1-Z7", encoding="utf-8")

        result = gen.load_cycling_concepts()
        assert result == "Zones Z1-Z7"

    def test_load_cycling_concepts_missing(self, tmp_path):
        gen = PromptGenerator(project_root=tmp_path)
        assert gen.load_cycling_concepts() is None

    def test_load_recent_workouts_missing(self, tmp_path):
        """load_recent_workouts returns None when history file missing."""
        gen = PromptGenerator(project_root=tmp_path)
        assert gen.load_recent_workouts() is None

    def test_load_recent_workouts_existing(self, tmp_path):
        """load_recent_workouts reads sections from history file."""
        gen = PromptGenerator(project_root=tmp_path)
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        history = "## Historique\n### S081 séance\nDate : 2026-02-18\n"
        (logs_dir / "workouts-history.md").write_text(history, encoding="utf-8")

        result = gen.load_recent_workouts(limit=5)
        assert result is not None


class TestFormatPlannedWorkout:
    """Test PromptGenerator.format_planned_workout."""

    def test_none_returns_none(self, generator):
        assert generator.format_planned_workout(None) is None

    def test_no_workout_doc_returns_none(self, generator):
        assert generator.format_planned_workout({"name": "Test"}) is None

    def test_basic_workout_formatting(self, generator):
        """workout_doc with no steps → minimal format."""
        planned_event = {
            "name": "Sweet Spot 3x10",
            "description": "3 blocs SS",
            "icu_training_load": 82,
            "icu_intensity": 85,  # 85 → 0.85
            "workout_doc": {
                "duration": 4440,  # 74 min
                "average_watts": 180,
                "normalized_power": 190,
                "joules": 0,
                "steps": [],
            },
        }
        result = generator.format_planned_workout(planned_event)
        assert result is not None
        assert result["name"] == "Sweet Spot 3x10"
        assert result["duration_min"] == 74
        assert result["tss_planned"] == 82
        assert result["intensity_planned"] == pytest.approx(0.85)

    def test_workout_with_repeating_blocks(self, generator):
        """Steps with reps → intervals formatted as Nx(...)."""
        planned_event = {
            "name": "Intervalles",
            "icu_training_load": 90,
            "workout_doc": {
                "duration": 3600,
                "steps": [
                    {
                        "reps": 3,
                        "steps": [
                            {
                                "duration": 600,
                                "power": {"units": "%ftp", "value": 90},
                                "cadence": {"value": 90},
                            },
                            {
                                "duration": 240,
                                "power": {"units": "%ftp", "value": 60},
                                "cadence": {"value": 85},
                            },
                        ],
                    }
                ],
            },
        }
        result = generator.format_planned_workout(planned_event)
        assert len(result["intervals"]) == 1
        assert "3x" in result["intervals"][0]

    def test_workout_with_simple_step(self, generator):
        """Simple step (no reps) → added to intervals."""
        planned_event = {
            "name": "Warmup + Endurance",
            "icu_training_load": 50,
            "workout_doc": {
                "duration": 3600,
                "steps": [
                    {
                        "duration": 720,
                        "warmup": True,
                        "power": {"units": "%ftp", "start": 50, "end": 65},
                        "cadence": {"value": 85},
                    },
                    {
                        "duration": 2880,
                        "power": {"units": "%ftp", "value": 70},
                        "cadence": {"value": 88},
                    },
                ],
            },
        }
        result = generator.format_planned_workout(planned_event)
        assert len(result["intervals"]) == 2
        assert "[Warmup]" in result["intervals"][0]

    def test_workout_with_zone_times(self, generator):
        """Zone times in workout_doc → zone_distribution formatted."""
        planned_event = {
            "name": "Test",
            "icu_training_load": 60,
            "workout_doc": {
                "duration": 3600,
                "steps": [],
                "zoneTimes": [
                    {"id": "Z1", "name": "Recovery", "secs": 600},
                    {"id": "Z2", "name": "Endurance", "secs": 2400},
                    {"id": "Z3", "name": "Tempo", "secs": 0},  # skipped
                ],
            },
        }
        result = generator.format_planned_workout(planned_event)
        assert "Recovery" in result["zone_distribution"]
        assert "Endurance" in result["zone_distribution"]

    def test_workout_with_cooldown_step(self, generator):
        """Cooldown step → flagged in interval description."""
        planned_event = {
            "name": "Test",
            "icu_training_load": 40,
            "workout_doc": {
                "duration": 1800,
                "steps": [
                    {
                        "duration": 600,
                        "cooldown": True,
                        "power": {"units": "%ftp", "start": 65, "end": 50},
                        "cadence": {"value": 85},
                    }
                ],
            },
        }
        result = generator.format_planned_workout(planned_event)
        assert "[Cooldown]" in result["intervals"][0]


class TestPromptGeneratorInit:
    """Test PromptGenerator.__init__ branches."""

    @patch("magma_cycling.config.get_data_config")
    def test_init_with_data_config_success(self, mock_get_config, tmp_path):
        """project_root=None + get_data_config() succeeds → data_repo_path set."""
        mock_config = MagicMock()
        mock_config.data_repo_path = tmp_path / "data"
        mock_get_config.return_value = mock_config

        gen = PromptGenerator(project_root=None)

        assert gen.logs_dir == tmp_path / "data"
        assert gen.data_repo_path == tmp_path / "data"

    @patch("magma_cycling.config.get_data_config")
    def test_init_fallback_on_file_not_found(self, mock_get_config):
        """project_root=None + get_data_config() raises FileNotFoundError → fallback."""
        mock_get_config.side_effect = FileNotFoundError("no config")

        gen = PromptGenerator(project_root=None)

        # Falls back to Path.cwd()
        assert gen.project_root == Path.cwd()


class TestLoadAthleteCallback:
    """Test load_athlete_feedback file reading."""

    def test_load_feedback_existing_file(self, tmp_path):
        """Load feedback from existing JSON file."""
        gen = PromptGenerator(project_root=tmp_path)
        feedback_dir = Path(".athlete_feedback")
        feedback_dir.mkdir(exist_ok=True)
        feedback_file = feedback_dir / "last_feedback.json"
        feedback_data = {"rpe": 7, "ressenti_general": "Bien"}
        feedback_file.write_text(json.dumps(feedback_data), encoding="utf-8")

        try:
            result = gen.load_athlete_feedback()
            assert result is not None
            assert result["rpe"] == 7
        finally:
            feedback_file.unlink(missing_ok=True)

    def test_load_feedback_missing_file(self, tmp_path):
        """Returns None when feedback file missing."""
        gen = PromptGenerator(project_root=tmp_path)
        # Ensure the file does NOT exist by using a custom feedback_dir
        gen.feedback_file = tmp_path / ".athlete_feedback" / "nonexistent.json"
        assert gen.load_athlete_feedback() is None


class TestSafeFormatMetricEdgeCases:
    """Test safe_format_metric error handling."""

    def test_bad_format_spec_returns_default(self, generator):
        """Invalid format spec → returns default."""
        result = generator.safe_format_metric("not_a_number", ".0f", "W")
        assert result == "N/A"


class TestGeneratePromptWithPlanned:
    """Test generate_prompt with planned workout → covers planned section."""

    @pytest.fixture
    def activity_data(self, generator):
        raw = {
            "id": 12345,
            "name": "S082-03-INT-SweetSpot-V001",
            "start_date_local": "2026-02-25T17:00:00",
            "moving_time": 4440,
            "icu_training_load": 82,
            "icu_intensity": 85,
            "icu_average_watts": 190,
            "icu_weighted_avg_watts": 200,
            "avg_hr": 145,
            "max_hr": 172,
            "decoupling": 2.5,
            "source": "ZWIFT",
        }
        return generator.format_activity_data(raw)

    def test_prompt_with_planned_workout(self, generator, activity_data):
        """Planned workout with intervals → planned section in prompt."""
        planned_event = {
            "name": "Sweet Spot 3x10",
            "description": "3 blocs Sweet Spot 90%",
            "icu_training_load": 82,
            "icu_intensity": 85,
            "workout_doc": {
                "duration": 4440,
                "average_watts": 185,
                "normalized_power": 195,
                "steps": [
                    {
                        "reps": 3,
                        "steps": [
                            {
                                "duration": 600,
                                "power": {"units": "%ftp", "value": 90},
                                "cadence": {"value": 92},
                            },
                            {
                                "duration": 240,
                                "power": {"units": "%ftp", "value": 62},
                                "cadence": {"value": 85},
                            },
                        ],
                    }
                ],
                "zoneTimes": [],
            },
        }
        prompt = generator.generate_prompt(
            activity_data=activity_data,
            wellness_pre=None,
            wellness_post=None,
            athlete_context=None,
            recent_workouts=None,
            planned_workout=planned_event,
        )
        assert "Workout Planifié vs Réalisé" in prompt
        assert "Sweet Spot 3x10" in prompt


class TestDisplayActivityMenu:
    """Test display_activity_menu standalone function."""

    ACTIVITY = {
        "id": 123,
        "name": "Test Ride",
        "start_date_local": "2026-02-23T18:00:00",
        "moving_time": 4620,
        "icu_training_load": 57,
    }

    def test_empty_list_returns_cancel(self):
        """No activities → cancel immediately."""
        mode, activity_id = display_activity_menu([])
        assert mode == "cancel"
        assert activity_id is None

    @patch("builtins.input", return_value="1")
    def test_single_activity_choice_1_returns_single(self, mock_input):
        """Single activity, user chooses 1 → single mode."""
        mode, activity_id = display_activity_menu([self.ACTIVITY])
        assert mode == "single"
        assert activity_id == 123

    @patch("builtins.input", return_value="0")
    def test_single_activity_choice_0_returns_cancel(self, mock_input):
        """Single activity, user chooses 0 → cancel."""
        mode, activity_id = display_activity_menu([self.ACTIVITY])
        assert mode == "cancel"

    @patch("builtins.input", return_value="1")
    def test_multiple_activities_choice_1_returns_last(self, mock_input):
        """Multiple activities, choice 1 → last (first in list) activity."""
        activities = [
            {**self.ACTIVITY, "id": 111},
            {**self.ACTIVITY, "id": 222},
        ]
        mode, activity_id = display_activity_menu(activities)
        assert mode == "single"
        assert activity_id == 111  # First item (most recent)

    @patch("builtins.input", return_value="3")
    def test_multiple_activities_choice_3_returns_batch(self, mock_input):
        """Multiple activities, choice 3 → batch mode."""
        activities = [
            {**self.ACTIVITY, "id": 111},
            {**self.ACTIVITY, "id": 222},
        ]
        mode, activity_id = display_activity_menu(activities)
        assert mode == "batch"
        assert activity_id is None

    @patch("builtins.input", side_effect=["0"])
    def test_multiple_activities_choice_0_returns_cancel(self, mock_input):
        """Multiple activities, choice 0 → cancel."""
        activities = [
            {**self.ACTIVITY, "id": 111},
            {**self.ACTIVITY, "id": 222},
        ]
        mode, activity_id = display_activity_menu(activities)
        assert mode == "cancel"

    @patch("builtins.input", side_effect=["2", "1"])
    def test_multiple_activities_choice_2_valid_selection(self, mock_input):
        """Multiple activities, choice 2 + valid number → single with that activity."""
        activities = [
            {**self.ACTIVITY, "id": 111},
            {**self.ACTIVITY, "id": 222},
        ]
        mode, activity_id = display_activity_menu(activities)
        assert mode == "single"
        assert activity_id == 111

    @patch("builtins.input", side_effect=["2", "99"])
    def test_multiple_activities_choice_2_out_of_range(self, mock_input):
        """Choice 2 + out-of-range → cancel."""
        activities = [
            {**self.ACTIVITY, "id": 111},
            {**self.ACTIVITY, "id": 222},
        ]
        mode, activity_id = display_activity_menu(activities)
        assert mode == "cancel"

    @patch("builtins.input", side_effect=["2", "abc"])
    def test_multiple_activities_choice_2_invalid_input(self, mock_input):
        """Choice 2 + non-integer → cancel."""
        activities = [
            {**self.ACTIVITY, "id": 111},
            {**self.ACTIVITY, "id": 222},
        ]
        mode, activity_id = display_activity_menu(activities)
        assert mode == "cancel"


class TestLoadPeriodizationContext:
    """Test PromptGenerator.load_periodization_context."""

    def test_no_wellness_returns_none(self, generator):
        """None wellness → returns None early."""
        result = generator.load_periodization_context(wellness_data=None)
        assert result is None

    def test_ctl_zero_returns_none(self, generator):
        """CTL=0 → returns None."""
        result = generator.load_periodization_context(wellness_data={"ctl": 0.0, "atl": 0.0})
        assert result is None

    @patch("magma_cycling.config.athlete_profile.AthleteProfile.from_env")
    def test_exception_returns_none_gracefully(self, mock_from_env, generator):
        """Exception in profile loading → returns None gracefully."""
        mock_from_env.side_effect = Exception("env error")
        result = generator.load_periodization_context(wellness_data={"ctl": 50.0, "atl": 55.0})
        assert result is None

    @patch("magma_cycling.workflows.pid_peaks_integration.compute_integrated_correction")
    @patch("magma_cycling.planning.peaks_phases.determine_training_phase")
    @patch("magma_cycling.config.athlete_profile.AthleteProfile.from_env")
    def test_success_returns_dict(self, mock_profile, mock_determine, mock_compute, generator):
        """Success path → returns periodization context dict."""
        from magma_cycling.workflows.pid_peaks_integration import ControlMode

        mock_profile_obj = MagicMock()
        mock_profile_obj.ftp = 223
        mock_profile_obj.ftp_target = 230
        mock_profile_obj.age = 40
        mock_profile.return_value = mock_profile_obj

        mock_phase_rec = MagicMock()
        mock_phase_rec.phase = MagicMock()
        mock_phase_rec.phase.value = "reconstruction_base"
        mock_phase_rec.ctl_target = 73.0
        mock_phase_rec.ctl_deficit = 29.7
        mock_phase_rec.weeks_to_rebuild = 11
        mock_phase_rec.weekly_tss_load = 350
        mock_phase_rec.weekly_tss_recovery = 250
        mock_phase_rec.recovery_week_frequency = 2
        mock_phase_rec.rationale = "CTL critique"
        mock_determine.return_value = mock_phase_rec

        mock_integrated = MagicMock()
        mock_integrated.override_active = True
        mock_integrated.mode = ControlMode.PEAKS_OVERRIDE
        mock_compute.return_value = mock_integrated

        result = generator.load_periodization_context(wellness_data={"ctl": 43.3, "atl": 51.0})

        assert result is not None
        assert result["phase"] == "RECONSTRUCTION BASE"
        assert result["ctl_current"] == pytest.approx(43.3)
        assert result["ftp_current"] == 223
        assert result["weeks_to_target"] == 11
        assert "Override" in result["pid_status"]


class TestLoadAthleteCallbackException:
    """Test load_athlete_feedback exception path."""

    def test_invalid_json_returns_none(self, tmp_path):
        """Feedback file with invalid JSON → returns None."""
        gen = PromptGenerator(project_root=tmp_path)
        # Override feedback file path to point to file with invalid JSON
        feedback_dir = tmp_path / ".athlete_feedback"
        feedback_dir.mkdir()
        feedback_file = feedback_dir / "last_feedback.json"
        feedback_file.write_text("invalid json {{{", encoding="utf-8")
        gen.feedback_file = feedback_file

        result = gen.load_athlete_feedback()
        assert result is None


class TestCopyToClipboard:
    """Test PromptGenerator.copy_to_clipboard."""

    @patch("subprocess.Popen")
    def test_success(self, mock_popen, generator):
        """Successful pbcopy call → returns True."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        result = generator.copy_to_clipboard("test text")
        assert result is True

    @patch("subprocess.Popen", side_effect=FileNotFoundError("pbcopy not found"))
    def test_failure(self, mock_popen, generator):
        """pbcopy not found → returns False."""
        result = generator.copy_to_clipboard("test text")
        assert result is False


class TestLoadRecentWorkoutsLimit:
    """Cover the break branch in load_recent_workouts."""

    def test_limit_stops_early(self, tmp_path):
        """Limit=1 with multiple sections → only 1 returned."""
        gen = PromptGenerator(project_root=tmp_path)
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        history = (
            "## Historique\n"
            "### S082\nDate : 2026-02-23\nContent 1\n"
            "### S081\nDate : 2026-02-16\nContent 2\n"
            "### S080\nDate : 2026-02-09\nContent 3\n"
        )
        (logs_dir / "workouts-history.md").write_text(history, encoding="utf-8")

        result = gen.load_recent_workouts(limit=1)
        assert result is not None
        assert "S082" in result
        # Should NOT include S081 or S080 since limit=1
        assert "S081" not in result


class TestPIDModeBranches:
    """Cover PID_CONSTRAINED and autonomous branches in load_periodization_context."""

    @patch("magma_cycling.workflows.pid_peaks_integration.compute_integrated_correction")
    @patch("magma_cycling.planning.peaks_phases.determine_training_phase")
    @patch("magma_cycling.config.athlete_profile.AthleteProfile.from_env")
    def test_pid_constrained_mode(self, mock_profile, mock_determine, mock_compute, generator):
        """override_active=False + PID_CONSTRAINED → correct status."""
        from magma_cycling.workflows.pid_peaks_integration import ControlMode

        mock_profile_obj = MagicMock()
        mock_profile_obj.ftp = 223
        mock_profile_obj.ftp_target = 230
        mock_profile_obj.age = 40
        mock_profile.return_value = mock_profile_obj

        mock_phase = MagicMock()
        mock_phase.phase = MagicMock()
        mock_phase.phase.value = "consolidation"
        mock_phase.ctl_target = 65.0
        mock_phase.ctl_deficit = 5.0
        mock_phase.weeks_to_rebuild = 3
        mock_phase.weekly_tss_load = 400
        mock_phase.weekly_tss_recovery = 280
        mock_phase.recovery_week_frequency = 3
        mock_phase.rationale = "CTL proche cible"
        mock_determine.return_value = mock_phase

        mock_integrated = MagicMock()
        mock_integrated.override_active = False
        mock_integrated.mode = ControlMode.PID_CONSTRAINED
        mock_compute.return_value = mock_integrated

        result = generator.load_periodization_context(wellness_data={"ctl": 60.0, "atl": 62.0})
        assert result is not None
        assert "contraintes" in result["pid_status"]

    @patch("magma_cycling.workflows.pid_peaks_integration.compute_integrated_correction")
    @patch("magma_cycling.planning.peaks_phases.determine_training_phase")
    @patch("magma_cycling.config.athlete_profile.AthleteProfile.from_env")
    def test_pid_autonomous_mode(self, mock_profile, mock_determine, mock_compute, generator):
        """override_active=False + PID mode → autonomous status."""
        from magma_cycling.workflows.pid_peaks_integration import ControlMode

        mock_profile_obj = MagicMock()
        mock_profile_obj.ftp = 223
        mock_profile_obj.ftp_target = 230
        mock_profile_obj.age = 40
        mock_profile.return_value = mock_profile_obj

        mock_phase = MagicMock()
        mock_phase.phase = MagicMock()
        mock_phase.phase.value = "development_ftp"
        mock_phase.ctl_target = 73.0
        mock_phase.ctl_deficit = 0.0
        mock_phase.weeks_to_rebuild = 0
        mock_phase.weekly_tss_load = 450
        mock_phase.weekly_tss_recovery = 300
        mock_phase.recovery_week_frequency = 3
        mock_phase.rationale = "Phase développement"
        mock_determine.return_value = mock_phase

        mock_integrated = MagicMock()
        mock_integrated.override_active = False
        mock_integrated.mode = ControlMode.PID_AUTONOMOUS  # Not PEAKS_OVERRIDE, not PID_CONSTRAINED
        mock_compute.return_value = mock_integrated

        result = generator.load_periodization_context(wellness_data={"ctl": 73.0, "atl": 70.0})
        assert result is not None
        assert "autonome" in result["pid_status"]


class TestAnalyzeBatch:
    """Test analyze_batch function — covers CLI prefix without full interactive flow."""

    @patch("builtins.input", return_value="")
    def test_analyze_batch_empty_list(self, mock_input, tmp_path):
        """analyze_batch with empty list → input called, loop not entered."""
        api = MagicMock()
        gen = PromptGenerator(project_root=tmp_path)
        state = MagicMock()

        analyze_batch(api, [], gen, state, str(tmp_path))

        # input() was called once (initial "Appuyez sur Entrée")
        mock_input.assert_called_once()

    @patch("subprocess.Popen")
    @patch("builtins.input")
    def test_analyze_batch_one_activity(self, mock_input, mock_popen, tmp_path):
        """analyze_batch with one activity + mocked API covers loop body."""
        # Mock input sequence: initial Enter, no feedback, copy response Enter, no insertion
        mock_input.side_effect = ["", "n", "", "n"]

        # Mock Popen for clipboard
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        # Mock API
        api = MagicMock()
        full_activity = {
            "id": 123,
            "name": "S082-01-END-Test",
            "type": "VirtualRide",
            "start_date_local": "2026-02-23T18:00:00",
            "moving_time": 4620,
            "icu_training_load": 57,
            "icu_intensity": 67,
            "source": "ZWIFT",
        }
        api.get_activity.return_value = full_activity
        api.get_wellness.return_value = []
        api.get_planned_workout.return_value = None

        activity = {
            "id": 123,
            "name": "S082-01-END-Test",
            "start_date_local": "2026-02-23T18:00:00",
            "icu_training_load": 57,
            "moving_time": 4620,
        }

        gen = PromptGenerator(project_root=tmp_path)
        state = MagicMock()

        analyze_batch(api, [activity], gen, state, str(tmp_path))

        # Verify API was called
        api.get_activity.assert_called_once_with(123)


class TestMainCLI:
    """Tests for main() CLI entry point."""

    ACTIVITY = {
        "id": "i999",
        "name": "S082-01-END-Test",
        "start_date_local": "2026-02-23T18:00:00",
        "moving_time": 3600,
        "icu_training_load": 50,
        "icu_intensity": 70,
        "source": "ZWIFT",
    }

    @pytest.fixture
    def mock_env(self, tmp_path, monkeypatch):
        """Set up common mocks for main() tests."""
        # Mock API client
        mock_client = MagicMock()
        monkeypatch.setattr(
            "magma_cycling.prepare_analysis.create_intervals_client",
            lambda: mock_client,
        )

        # Mock AI config
        mock_ai_config = MagicMock()
        mock_ai_config.default_provider = "clipboard"
        monkeypatch.setattr(
            "magma_cycling.prepare_analysis.get_ai_config",
            lambda: mock_ai_config,
        )

        # Mock data config for PromptGenerator
        mock_data_config = MagicMock()
        mock_data_config.data_repo_path = tmp_path
        monkeypatch.setattr(
            "magma_cycling.config.get_data_config",
            lambda: mock_data_config,
        )

        # Mock WorkflowState
        mock_state_cls = MagicMock()
        mock_state = MagicMock()
        mock_state.get_last_analyzed_id.return_value = None
        mock_state.get_unanalyzed_activities.side_effect = lambda acts: acts
        mock_state_cls.return_value = mock_state
        monkeypatch.setattr(
            "magma_cycling.prepare_analysis.WorkflowState",
            mock_state_cls,
        )

        # Create required directories
        (tmp_path / "references").mkdir(exist_ok=True)
        (tmp_path / "logs").mkdir(exist_ok=True)

        return mock_client, mock_state

    def test_main_with_activity_id(self, tmp_path, monkeypatch, mock_env):
        """--activity-id bypasses menu and analyzes directly."""
        mock_client, _ = mock_env
        mock_client.get_activity.return_value = self.ACTIVITY.copy()
        mock_client.get_wellness.return_value = []
        mock_client.get_planned_workout.return_value = None

        monkeypatch.setattr(
            "sys.argv",
            ["prog", "--activity-id", "i999", "--project-root", str(tmp_path)],
        )
        # Mock clipboard copy
        monkeypatch.setattr(
            "magma_cycling.workflows.prompt.prompt_assembly.subprocess.run",
            MagicMock(return_value=MagicMock(returncode=0)),
        )

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_main_no_activities_exits_1(self, tmp_path, monkeypatch, mock_env):
        """Exit 1 when API returns no activities."""
        mock_client, _ = mock_env
        mock_client.get_activities.return_value = []

        monkeypatch.setattr(
            "sys.argv",
            ["prog", "--project-root", str(tmp_path)],
        )

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_main_list_mode(self, tmp_path, monkeypatch, mock_env, capsys):
        """--list shows unanalyzed activities and exits 0."""
        mock_client, _ = mock_env
        mock_client.get_activities.return_value = [self.ACTIVITY.copy()]

        monkeypatch.setattr(
            "sys.argv",
            ["prog", "--list", "--project-root", str(tmp_path)],
        )

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

        output = capsys.readouterr().out
        assert "non analysée" in output

    def test_main_list_empty(self, tmp_path, monkeypatch, mock_env, capsys):
        """--list with no unanalyzed activities shows success."""
        mock_client, mock_state = mock_env
        mock_client.get_activities.return_value = [self.ACTIVITY.copy()]
        mock_state.get_unanalyzed_activities.side_effect = lambda acts: []

        monkeypatch.setattr(
            "sys.argv",
            ["prog", "--list", "--project-root", str(tmp_path)],
        )

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

        output = capsys.readouterr().out
        assert "Aucune activité non analysée" in output

    def test_main_menu_cancel(self, tmp_path, monkeypatch, mock_env):
        """User cancels from activity menu exits 0."""
        mock_client, _ = mock_env
        mock_client.get_activities.return_value = [self.ACTIVITY.copy()]

        monkeypatch.setattr(
            "sys.argv",
            ["prog", "--project-root", str(tmp_path)],
        )
        monkeypatch.setattr(
            "magma_cycling.prepare_analysis.display_activity_menu",
            lambda acts: ("cancel", None),
        )

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_main_menu_single(self, tmp_path, monkeypatch, mock_env):
        """User selects single activity from menu."""
        mock_client, _ = mock_env
        activity = self.ACTIVITY.copy()
        mock_client.get_activities.return_value = [activity]
        mock_client.get_activity.return_value = activity
        mock_client.get_wellness.return_value = []
        mock_client.get_planned_workout.return_value = None

        monkeypatch.setattr(
            "sys.argv",
            ["prog", "--project-root", str(tmp_path)],
        )
        monkeypatch.setattr(
            "magma_cycling.prepare_analysis.display_activity_menu",
            lambda acts: ("single", "i999"),
        )
        monkeypatch.setattr(
            "magma_cycling.workflows.prompt.prompt_assembly.subprocess.run",
            MagicMock(return_value=MagicMock(returncode=0)),
        )

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_main_strava_source_warning(self, tmp_path, monkeypatch, mock_env, capsys):
        """STRAVA source activity shows warning."""
        mock_client, _ = mock_env
        activity = self.ACTIVITY.copy()
        activity["source"] = "STRAVA"
        mock_client.get_activity.return_value = activity
        mock_client.get_wellness.return_value = []
        mock_client.get_planned_workout.return_value = None

        monkeypatch.setattr(
            "sys.argv",
            ["prog", "--activity-id", "i999", "--project-root", str(tmp_path)],
        )
        monkeypatch.setattr(
            "magma_cycling.workflows.prompt.prompt_assembly.subprocess.run",
            MagicMock(return_value=MagicMock(returncode=0)),
        )

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

        output = capsys.readouterr().out
        assert "Strava" in output

    def test_main_api_provider(self, tmp_path, monkeypatch, mock_env, capsys):
        """API provider shows automated workflow message."""
        mock_client, _ = mock_env
        mock_client.get_activity.return_value = self.ACTIVITY.copy()
        mock_client.get_wellness.return_value = []
        mock_client.get_planned_workout.return_value = None

        # Override AI config to use API provider
        mock_ai_config = MagicMock()
        mock_ai_config.default_provider = "claude_api"
        monkeypatch.setattr(
            "magma_cycling.prepare_analysis.get_ai_config",
            lambda: mock_ai_config,
        )

        monkeypatch.setattr(
            "sys.argv",
            ["prog", "--activity-id", "i999", "--project-root", str(tmp_path)],
        )
        monkeypatch.setattr(
            "magma_cycling.workflows.prompt.prompt_assembly.subprocess.run",
            MagicMock(return_value=MagicMock(returncode=0)),
        )

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

        output = capsys.readouterr().out
        assert "API" in output

    def test_main_clipboard_copy_fails(self, tmp_path, monkeypatch, mock_env, capsys):
        """Clipboard copy failure prints prompt to stdout."""
        mock_client, _ = mock_env
        mock_client.get_activity.return_value = self.ACTIVITY.copy()
        mock_client.get_wellness.return_value = []
        mock_client.get_planned_workout.return_value = None

        monkeypatch.setattr(
            "sys.argv",
            ["prog", "--activity-id", "i999", "--project-root", str(tmp_path)],
        )
        # Make clipboard copy fail
        monkeypatch.setattr(
            "magma_cycling.workflows.prompt.prompt_assembly.subprocess.run",
            MagicMock(side_effect=FileNotFoundError("pbcopy not found")),
        )

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
