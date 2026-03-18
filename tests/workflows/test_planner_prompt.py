"""Tests for workflows/planner/prompt.py — planning prompt generation.

Covers:
- generate_planning_prompt() full assembly
- Conditional periodization section
- Conditional mesocycle section
- _format_periodization_section() formatting
- Template variable substitution
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.weekly_planner import WeeklyPlanner


@pytest.fixture
def project_root(tmp_path):
    """Create temporary project root with required structure."""
    refs = tmp_path / "references"
    refs.mkdir()

    # Create template file
    templates_dir = tmp_path / "planner_templates"
    templates_dir.mkdir()

    return tmp_path


@pytest.fixture
def planner(project_root):
    """Create WeeklyPlanner with all prompt dependencies mocked."""
    with (
        patch(
            "magma_cycling.weekly_planner.create_intervals_client",
            side_effect=ValueError("No API"),
        ),
        patch("magma_cycling.config.get_data_config") as mock_config,
    ):
        config = MagicMock()
        config.week_planning_dir = project_root / "planning"
        config.data_repo_path = project_root / "data"
        mock_config.return_value = config
        (project_root / "planning").mkdir(exist_ok=True)

        p = WeeklyPlanner(
            week_number="S090",
            start_date=datetime(2026, 3, 9),
            project_root=project_root,
        )

    # Set required attributes for prompt generation
    p.current_metrics = {"ctl": 65.0, "atl": 58.0, "tsb": 7.0, "ftp": 260}
    p.previous_week_bilan = "## Bilan S089\nBonne semaine."
    p.context_files = {
        "project_prompt": "Athlète cycliste, 84kg, FTP 260W",
        "planning_preferences": "Préfère rouler le matin",
        "cycling_concepts": "Zone 2, Sweet Spot, VO2max",
        "protocols": "Échauffement 15min, retour au calme 10min",
        "intelligence": "Recommandation: augmenter volume",
    }

    return p


class TestGeneratePlanningPrompt:
    """Test generate_planning_prompt() full assembly."""

    def test_prompt_contains_header(self, planner):
        """Test prompt starts with week number header."""
        with (
            patch.object(planner, "load_periodization_context", return_value=None),
            patch.object(planner, "load_previous_week_workouts", return_value=""),
            patch.object(planner, "_load_mesocycle_context", return_value=None),
            patch.object(planner, "_load_available_zwift_workouts", return_value=""),
        ):
            prompt = planner.generate_planning_prompt()

        assert "S090" in prompt
        assert "Planification Hebdomadaire" in prompt

    def test_prompt_contains_dates(self, planner):
        """Test prompt includes correct date range."""
        with (
            patch.object(planner, "load_periodization_context", return_value=None),
            patch.object(planner, "load_previous_week_workouts", return_value=""),
            patch.object(planner, "_load_mesocycle_context", return_value=None),
            patch.object(planner, "_load_available_zwift_workouts", return_value=""),
        ):
            prompt = planner.generate_planning_prompt()

        assert "09/03/2026" in prompt
        assert "15/03/2026" in prompt

    def test_prompt_contains_metrics(self, planner):
        """Test prompt includes current metrics JSON."""
        with (
            patch.object(planner, "load_periodization_context", return_value=None),
            patch.object(planner, "load_previous_week_workouts", return_value=""),
            patch.object(planner, "_load_mesocycle_context", return_value=None),
            patch.object(planner, "_load_available_zwift_workouts", return_value=""),
        ):
            prompt = planner.generate_planning_prompt()

        assert "65.0" in prompt  # CTL
        assert "58.0" in prompt  # ATL

    def test_prompt_contains_previous_bilan(self, planner):
        """Test prompt includes previous week bilan."""
        with (
            patch.object(planner, "load_periodization_context", return_value=None),
            patch.object(planner, "load_previous_week_workouts", return_value=""),
            patch.object(planner, "_load_mesocycle_context", return_value=None),
            patch.object(planner, "_load_available_zwift_workouts", return_value=""),
        ):
            prompt = planner.generate_planning_prompt()

        assert "Bilan S089" in prompt
        assert "Bonne semaine" in prompt

    def test_prompt_contains_context_files(self, planner):
        """Test prompt includes athlete context."""
        with (
            patch.object(planner, "load_periodization_context", return_value=None),
            patch.object(planner, "load_previous_week_workouts", return_value=""),
            patch.object(planner, "_load_mesocycle_context", return_value=None),
            patch.object(planner, "_load_available_zwift_workouts", return_value=""),
        ):
            prompt = planner.generate_planning_prompt()

        assert "FTP 260W" in prompt

    def test_prompt_next_week_reference(self, planner):
        """Test prompt references next week number."""
        with (
            patch.object(planner, "load_periodization_context", return_value=None),
            patch.object(planner, "load_previous_week_workouts", return_value=""),
            patch.object(planner, "_load_mesocycle_context", return_value=None),
            patch.object(planner, "_load_available_zwift_workouts", return_value=""),
        ):
            prompt = planner.generate_planning_prompt()

        assert "S091" in prompt


class TestConditionalPeriodization:
    """Test conditional periodization section."""

    def test_periodization_included_when_available(self, planner):
        """Test periodization section is added when context exists."""
        pc = {
            "phase": "BUILD",
            "ctl_current": 65.0,
            "ctl_target": 80,
            "ctl_deficit": 15.0,
            "ftp_current": 260,
            "ftp_target": 280,
            "weeks_to_target": 8,
            "weekly_tss_load": 450,
            "weekly_tss_recovery": 300,
            "recovery_week_frequency": 4,
            "intensity_distribution": {"Z2": 0.70, "Z3": 0.10, "Z4": 0.15, "Z5": 0.05},
            "pid_status": "active",
            "rationale": "Phase de construction progressive",
        }

        with (
            patch.object(planner, "load_periodization_context", return_value=pc),
            patch.object(planner, "load_previous_week_workouts", return_value=""),
            patch.object(planner, "_load_mesocycle_context", return_value=None),
            patch.object(planner, "_load_available_zwift_workouts", return_value=""),
        ):
            prompt = planner.generate_planning_prompt()

        assert "Périodisation" in prompt
        assert "BUILD" in prompt
        assert "CTL" in prompt or "ctl" in prompt.lower()
        assert "450" in prompt  # weekly_tss_load

    def test_periodization_excluded_when_none(self, planner):
        """Test periodization section is skipped when context is None."""
        with (
            patch.object(planner, "load_periodization_context", return_value=None),
            patch.object(planner, "load_previous_week_workouts", return_value=""),
            patch.object(planner, "_load_mesocycle_context", return_value=None),
            patch.object(planner, "_load_available_zwift_workouts", return_value=""),
        ):
            prompt = planner.generate_planning_prompt()

        assert "Périodisation" not in prompt


class TestConditionalMesocycle:
    """Test conditional mesocycle section."""

    def test_mesocycle_included_when_available(self, planner):
        """Test mesocycle context is included when provided."""
        mesocycle_text = "## Contexte Mésocycle\nSemaine 3/4 du bloc BUILD."

        with (
            patch.object(planner, "load_periodization_context", return_value=None),
            patch.object(planner, "load_previous_week_workouts", return_value=""),
            patch.object(planner, "_load_mesocycle_context", return_value=mesocycle_text),
            patch.object(planner, "_load_available_zwift_workouts", return_value=""),
        ):
            prompt = planner.generate_planning_prompt()

        assert "Mésocycle" in prompt
        assert "Semaine 3/4" in prompt

    def test_mesocycle_excluded_when_none(self, planner):
        """Test mesocycle section is skipped when None."""
        with (
            patch.object(planner, "load_periodization_context", return_value=None),
            patch.object(planner, "load_previous_week_workouts", return_value=""),
            patch.object(planner, "_load_mesocycle_context", return_value=None),
            patch.object(planner, "_load_available_zwift_workouts", return_value=""),
        ):
            prompt = planner.generate_planning_prompt()

        assert "Mésocycle" not in prompt


class TestFormatPeriodizationSection:
    """Test _format_periodization_section() formatting."""

    def test_section_contains_phase(self, planner):
        """Test section displays phase name."""
        pc = {
            "phase": "RECOVERY",
            "ctl_current": 60.0,
            "ctl_target": 75,
            "ctl_deficit": 15.0,
            "ftp_current": 255,
            "ftp_target": 270,
            "weeks_to_target": 6,
            "weekly_tss_load": 400,
            "weekly_tss_recovery": 250,
            "recovery_week_frequency": 3,
            "intensity_distribution": {"Z2": 0.80, "Z3": 0.10, "Z4": 0.05, "Z5": 0.05},
            "pid_status": "paused",
            "rationale": "Semaine de récupération",
        }

        section = planner._format_periodization_section(pc)

        assert "RECOVERY" in section
        assert "60.0" in section  # ctl_current
        assert "75" in section  # ctl_target
        assert "255" in section  # ftp_current

    def test_section_marks_focus_zones(self, planner):
        """Test FOCUS marker for zones >= 20%."""
        pc = {
            "phase": "BUILD",
            "ctl_current": 65.0,
            "ctl_target": 80,
            "ctl_deficit": 15.0,
            "ftp_current": 260,
            "ftp_target": 280,
            "weeks_to_target": 8,
            "weekly_tss_load": 450,
            "weekly_tss_recovery": 300,
            "recovery_week_frequency": 4,
            "intensity_distribution": {"Z2": 0.70, "Z3": 0.10, "Z4": 0.15, "Z5": 0.05},
            "pid_status": "active",
            "rationale": "Construction",
        }

        section = planner._format_periodization_section(pc)

        # Z2 at 70% should have FOCUS marker
        assert "FOCUS" in section
        # Z5 at 5% should NOT have FOCUS marker
        lines = section.split("\n")
        z5_lines = [line for line in lines if "Z5" in line]
        assert all("FOCUS" not in line for line in z5_lines)

    def test_section_contains_pid_status(self, planner):
        """Test section displays PID controller status."""
        pc = {
            "phase": "MAINTAIN",
            "ctl_current": 75.0,
            "ctl_target": 80,
            "ctl_deficit": 5.0,
            "ftp_current": 270,
            "ftp_target": 280,
            "weeks_to_target": 3,
            "weekly_tss_load": 420,
            "weekly_tss_recovery": 280,
            "recovery_week_frequency": 4,
            "intensity_distribution": {"Z2": 0.65, "Z3": 0.15, "Z4": 0.15, "Z5": 0.05},
            "pid_status": "converged",
            "rationale": "Phase de maintien",
        }

        section = planner._format_periodization_section(pc)

        assert "converged" in section
        assert "CRITIQUE" in section

    def test_section_contains_weekly_tss_targets(self, planner):
        """Test section displays both load and recovery TSS."""
        pc = {
            "phase": "BUILD",
            "ctl_current": 65.0,
            "ctl_target": 80,
            "ctl_deficit": 15.0,
            "ftp_current": 260,
            "ftp_target": 280,
            "weeks_to_target": 8,
            "weekly_tss_load": 450,
            "weekly_tss_recovery": 300,
            "recovery_week_frequency": 4,
            "intensity_distribution": {"Z2": 0.70},
            "pid_status": "active",
            "rationale": "Build phase",
        }

        section = planner._format_periodization_section(pc)

        assert "450" in section  # load TSS
        assert "300" in section  # recovery TSS
        assert "4" in section  # recovery frequency
