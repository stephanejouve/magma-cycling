"""Tests for environment detection in format_activity_data()."""

from magma_cycling.workflows.prompt.data_formatting import DataFormattingMixin


class TestEnvironmentDetection:
    """Test indoor/outdoor detection based on activity type."""

    def setup_method(self):
        """Create a mixin instance for testing."""
        self.formatter = DataFormattingMixin()

    def _make_activity(self, activity_type=None):
        """Create minimal activity dict."""
        activity = {
            "start_date_local": "2026-03-07T08:00:00",
            "name": "Test Ride",
        }
        if activity_type is not None:
            activity["type"] = activity_type
        return activity

    def test_virtual_ride_is_indoor(self):
        """VirtualRide → indoor."""
        result = self.formatter.format_activity_data(self._make_activity("VirtualRide"))
        assert result["environment"] == "indoor"
        assert result["is_indoor"] is True

    def test_ride_is_outdoor(self):
        """Ride → outdoor."""
        result = self.formatter.format_activity_data(self._make_activity("Ride"))
        assert result["environment"] == "outdoor"
        assert result["is_indoor"] is False

    def test_missing_type_defaults_outdoor(self):
        """Type absent → outdoor."""
        result = self.formatter.format_activity_data(self._make_activity())
        assert result["environment"] == "outdoor"
        assert result["is_indoor"] is False

    def test_empty_type_is_outdoor(self):
        """Type vide → outdoor."""
        result = self.formatter.format_activity_data(self._make_activity(""))
        assert result["environment"] == "outdoor"
        assert result["is_indoor"] is False

    def test_other_type_is_outdoor(self):
        """Autre type (Run, etc.) → outdoor."""
        result = self.formatter.format_activity_data(self._make_activity("Run"))
        assert result["environment"] == "outdoor"
        assert result["is_indoor"] is False


class TestDisciplineInPrompt:
    """Test discipline section appears in prompt for outdoor with planned workout."""

    def setup_method(self):
        """Create a mixed class for testing prompt assembly."""
        from magma_cycling.workflows.prompt.prompt_assembly import PromptAssemblyMixin

        class TestGenerator(DataFormattingMixin, PromptAssemblyMixin):
            """Test class combining both mixins."""

            def get_power_value(self, act, key):
                return act.get(f"{key}_power", act.get("avg_power"))

            def get_cadence_value(self, act, key):
                return act.get(f"{key}_cadence", act.get("avg_cadence"))

            def get_hr_value(self, act, key):
                return act.get(f"{key}_hr", act.get("avg_hr"))

            def safe_format_metric(self, value, fmt, unit):
                if value is None:
                    return "N/A"
                return f"{value:{fmt}}{unit}"

            def _format_feel_value(self, feel):
                return str(feel) if feel else "N/A"

            def _format_athlete_notes(self, desc, comments):
                return desc or comments or "_Aucune note_"

            def _format_temperature_data(self, avg, min_t, max_t, has_weather):
                return "N/A"

        self.generator = TestGenerator()

    def _make_activity_data(self, is_indoor=False):
        """Create formatted activity data dict."""
        return {
            "id": "i123",
            "name": "Test Ride",
            "type": "VirtualRide" if is_indoor else "Ride",
            "date": "07/03/2026",
            "date_iso": "2026-03-07",
            "duration_min": 60,
            "tss": 50,
            "intensity": 0.85,
            "avg_power": 200,
            "np": 210,
            "avg_cadence": 90,
            "avg_hr": 140,
            "max_hr": 165,
            "decoupling": 3.5,
            "avg_temp": None,
            "min_temp": None,
            "max_temp": None,
            "has_weather": False,
            "description": "",
            "tags": [],
            "feel": 3,
            "is_strava": False,
            "source": "INTERVALS",
            "environment": "indoor" if is_indoor else "outdoor",
            "is_indoor": is_indoor,
        }

    def _make_planned_workout(self):
        """Create a planned workout event with workout_doc."""
        return {
            "name": "Sweet Spot 2x20",
            "description": "Sweet Spot intervals",
            "icu_training_load": 55,
            "icu_intensity": 82,
            "workout_doc": {
                "duration": 3600,
                "average_watts": 195,
                "normalized_power": 205,
                "joules": 0,
                "steps": [],
                "zoneTimes": [],
            },
        }

    def test_outdoor_with_planned_has_discipline_section(self):
        """Outdoor + planned workout → discipline section present."""
        act = self._make_activity_data(is_indoor=False)
        planned_event = self._make_planned_workout()

        prompt = self.generator.generate_prompt(
            activity_data=act,
            wellness_pre=None,
            wellness_post=None,
            athlete_context="Test context",
            recent_workouts="",
            planned_workout=planned_event,
        )

        assert "Analyse Discipline Outdoor" in prompt
        assert "IF prévu" in prompt
        assert "IF réel" in prompt

    def test_indoor_has_indoor_section(self):
        """Indoor → indoor environment section present."""
        act = self._make_activity_data(is_indoor=True)

        prompt = self.generator.generate_prompt(
            activity_data=act,
            wellness_pre=None,
            wellness_post=None,
            athlete_context="Test context",
            recent_workouts="",
        )

        assert "Indoor (Home Trainer)" in prompt
        assert "Conditions contrôlées" in prompt
        assert "Analyse Discipline Outdoor" not in prompt

    def test_outdoor_without_planned_has_outdoor_section(self):
        """Outdoor sans planned → section outdoor générique."""
        act = self._make_activity_data(is_indoor=False)

        prompt = self.generator.generate_prompt(
            activity_data=act,
            wellness_pre=None,
            wellness_post=None,
            athlete_context="Test context",
            recent_workouts="",
        )

        assert "Environnement : Outdoor" in prompt
        assert "Variables externes" in prompt

    def test_environment_in_general_info(self):
        """Environnement affiché dans Informations Générales."""
        act = self._make_activity_data(is_indoor=True)

        prompt = self.generator.generate_prompt(
            activity_data=act,
            wellness_pre=None,
            wellness_post=None,
            athlete_context="Test context",
            recent_workouts="",
        )

        assert "**Environnement** : Indoor (Home Trainer)" in prompt
