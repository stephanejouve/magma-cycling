"""Tests for prompt builder and mission templates."""

import pytest

from magma_cycling.prompts.prompt_builder import (
    VALID_MISSIONS,
    build_prompt,
    format_athlete_profile,
)


@pytest.fixture
def sample_context():
    """Sample athlete context dict."""
    return {
        "name": "Test Athlete",
        "age": 54,
        "training_since": "2023-06",
        "platform": "Home trainer",
        "objectives": "General fitness",
        "constraints": [
            "Dette de sommeil chronique",
            "Travail terrain",
        ],
        "system_context": "Ne recommande JAMAIS d'outils externes.",
    }


@pytest.fixture
def sample_metrics():
    """Sample runtime metrics."""
    return {
        "ftp": 223,
        "weight": 84.7,
        "ctl": 41.0,
        "atl": 38.2,
        "ramp_rate": 3.5,
    }


@pytest.fixture
def sample_workflow_data():
    """Sample workflow data string."""
    return "TSS Cible: 300\nTSS Realise: 250\nAdherence: 83%"


# --- build_prompt tests ---


class TestBuildPrompt:
    """Tests for build_prompt()."""

    def test_returns_tuple(self, sample_context, sample_metrics, sample_workflow_data):
        """build_prompt returns a (system, user) tuple."""
        result = build_prompt(
            mission="mesocycle_analysis",
            current_metrics=sample_metrics,
            workflow_data=sample_workflow_data,
            athlete_context=sample_context,
        )
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_includes_base_system(self, sample_context, sample_metrics, sample_workflow_data):
        """System prompt contains the base system text."""
        system, _ = build_prompt(
            mission="mesocycle_analysis",
            current_metrics=sample_metrics,
            workflow_data=sample_workflow_data,
            athlete_context=sample_context,
        )
        assert "coach cyclisme IA" in system
        assert "Interdictions absolues" in system

    def test_includes_athlete_profile(self, sample_context, sample_metrics, sample_workflow_data):
        """System prompt contains athlete profile data."""
        system, _ = build_prompt(
            mission="mesocycle_analysis",
            current_metrics=sample_metrics,
            workflow_data=sample_workflow_data,
            athlete_context=sample_context,
        )
        assert "Test Athlete" in system
        assert "54 ans" in system
        assert "223W" in system
        assert "CTL: 41.0" in system

    def test_includes_mission_text(self, sample_context, sample_metrics, sample_workflow_data):
        """System prompt contains the mission-specific text."""
        system, _ = build_prompt(
            mission="mesocycle_analysis",
            current_metrics=sample_metrics,
            workflow_data=sample_workflow_data,
            athlete_context=sample_context,
        )
        assert "MESOCYCLE" in system

    def test_user_prompt_is_workflow_data(
        self, sample_context, sample_metrics, sample_workflow_data
    ):
        """User prompt is exactly the workflow data."""
        _, user = build_prompt(
            mission="mesocycle_analysis",
            current_metrics=sample_metrics,
            workflow_data=sample_workflow_data,
            athlete_context=sample_context,
        )
        assert user == sample_workflow_data

    def test_invalid_mission_raises(self, sample_metrics, sample_workflow_data):
        """Unknown mission raises ValueError."""
        with pytest.raises(ValueError, match="Unknown mission"):
            build_prompt(
                mission="invalid_mission",
                current_metrics=sample_metrics,
                workflow_data=sample_workflow_data,
            )

    def test_no_athlete_context_graceful(self, sample_metrics, sample_workflow_data):
        """With empty context, prompt still works with fallback text."""
        system, _ = build_prompt(
            mission="mesocycle_analysis",
            current_metrics=sample_metrics,
            workflow_data=sample_workflow_data,
            athlete_context={},
        )
        assert "Contexte athlete non disponible" in system

    def test_no_external_tools_in_base(self, sample_context, sample_metrics):
        """Base system prompt forbids external tool recommendations."""
        system, _ = build_prompt(
            mission="mesocycle_analysis",
            current_metrics=sample_metrics,
            workflow_data="data",
            athlete_context=sample_context,
        )
        assert "Ne recommande JAMAIS d'outils externes" in system


class TestMissions:
    """Tests for each mission template."""

    def test_mesocycle_analysis(self, sample_context, sample_metrics):
        """Mesocycle mission contains macro-level analysis directives."""
        system, _ = build_prompt(
            mission="mesocycle_analysis",
            current_metrics=sample_metrics,
            workflow_data="data",
            athlete_context=sample_context,
        )
        assert "MESOCYCLE" in system
        assert "periodisation" in system

    def test_weekly_planning(self, sample_context, sample_metrics):
        """Weekly planning mission contains prescription directives."""
        system, _ = build_prompt(
            mission="weekly_planning",
            current_metrics=sample_metrics,
            workflow_data="data",
            athlete_context=sample_context,
        )
        assert "SEANCES CONCRETES" in system
        assert "%FTP" in system

    def test_daily_feedback(self, sample_context, sample_metrics):
        """Daily feedback mission contains session evaluation directives."""
        system, _ = build_prompt(
            mission="daily_feedback",
            current_metrics=sample_metrics,
            workflow_data="data",
            athlete_context=sample_context,
        )
        assert "UNE SEANCE" in system
        assert "adherence" in system

    def test_weekly_review(self, sample_context, sample_metrics):
        """Weekly review mission contains review directives."""
        system, _ = build_prompt(
            mission="weekly_review",
            current_metrics=sample_metrics,
            workflow_data="data",
            athlete_context=sample_context,
        )
        assert "BILAN" in system
        assert "Compliance" in system

    def test_all_valid_missions_loadable(self, sample_metrics):
        """All VALID_MISSIONS can be loaded without error."""
        for mission in VALID_MISSIONS:
            system, user = build_prompt(
                mission=mission,
                current_metrics=sample_metrics,
                workflow_data="test data",
                athlete_context={"name": "X"},
            )
            assert len(system) > 100
            assert user == "test data"


class TestBuildPromptDegradation:
    """Tests for graceful degradation of build_prompt()."""

    def test_without_athlete_context_still_has_base_and_mission(self):
        """With athlete_context=None and no YAML, base + mission still present."""
        from unittest.mock import patch

        with patch("magma_cycling.prompts.prompt_builder.load_athlete_context", return_value={}):
            system, user = build_prompt(
                mission="mesocycle_analysis",
                current_metrics={"ftp": 200},
                workflow_data="data",
            )
        assert "coach cyclisme" in system
        assert "MESOCYCLE" in system

    def test_partial_metrics_no_crash(self):
        """Partial metrics (ftp only, no CTL/ATL) must not crash."""
        system, _ = build_prompt(
            mission="mesocycle_analysis",
            current_metrics={"ftp": 223},
            workflow_data="data",
            athlete_context={"name": "Test", "age": 54},
        )
        assert "223" in system
        # CTL/ATL should not appear since not provided
        assert "CTL:" not in system or "?" in system

    def test_empty_metrics_graceful(self):
        """Empty metrics dict produces valid system prompt."""
        system, _ = build_prompt(
            mission="mesocycle_analysis",
            current_metrics={},
            workflow_data="data",
            athlete_context={"name": "Test"},
        )
        assert len(system) > 50
        assert "coach cyclisme" in system

    def test_missing_yaml_file_returns_valid_prompt(self):
        """Missing YAML file still produces a valid prompt."""
        from unittest.mock import patch

        with patch("magma_cycling.prompts.prompt_builder.load_athlete_context", return_value={}):
            system, _ = build_prompt(
                mission="weekly_planning",
                current_metrics={},
                workflow_data="data",
            )
        assert "SEANCES CONCRETES" in system

    def test_corrupted_yaml_returns_empty_context(self, tmp_path):
        """Corrupted YAML degrades gracefully."""
        from magma_cycling.config.athlete_context import load_athlete_context

        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("{{invalid", encoding="utf-8")
        context = load_athlete_context(bad_file)
        # Should get empty dict, not crash
        system, _ = build_prompt(
            mission="mesocycle_analysis",
            current_metrics={},
            workflow_data="data",
            athlete_context=context,
        )
        assert "non disponible" in system


class TestVendorAgnostic:
    """Tests that prompts contain no vendor-specific references."""

    VENDOR_NAMES = ["Zwift", "Withings", "Mistral", "Claude", "OpenAI", "ChatGPT"]

    def test_base_system_no_vendor_references(self):
        """base_system.txt must not reference any vendor."""
        from magma_cycling.prompts.prompt_builder import PROMPTS_DIR

        base = (PROMPTS_DIR / "base_system.txt").read_text(encoding="utf-8")
        for vendor in self.VENDOR_NAMES:
            assert vendor not in base, f"Vendor '{vendor}' found in base_system.txt"

    def test_mission_files_no_vendor_references(self):
        """Mission files must not reference any vendor."""
        from magma_cycling.prompts.prompt_builder import PROMPTS_DIR

        for mission in VALID_MISSIONS:
            text = (PROMPTS_DIR / f"{mission}.txt").read_text(encoding="utf-8")
            for vendor in self.VENDOR_NAMES:
                assert vendor not in text, f"Vendor '{vendor}' found in {mission}.txt"

    def test_built_system_prompt_no_vendor_references(self):
        """Assembled system prompt must not reference vendors."""
        context = {"name": "Test", "age": 40, "constraints": ["Sleep debt"]}
        metrics = {"ftp": 200, "weight": 80, "ctl": 40.0, "atl": 35.0}
        system, _ = build_prompt(
            mission="mesocycle_analysis",
            current_metrics=metrics,
            workflow_data="data",
            athlete_context=context,
        )
        for vendor in self.VENDOR_NAMES:
            assert vendor not in system, f"Vendor '{vendor}' found in system prompt"


class TestFormatAthleteProfile:
    """Tests for format_athlete_profile()."""

    def test_computes_w_per_kg(self):
        """The formatter computes W/kg correctly."""
        context = {"name": "Test", "age": 40}
        metrics = {"ftp": 200, "weight": 80.0}
        result = format_athlete_profile(context, metrics)
        assert "2.50 W/kg" in result

    def test_missing_ftp_shows_question_mark(self):
        """Missing FTP shows '?' for W/kg."""
        context = {"name": "Test", "age": 40}
        metrics = {"weight": 80.0}
        result = format_athlete_profile(context, metrics)
        assert "? W/kg" in result

    def test_includes_constraints(self):
        """Constraints are listed in the profile."""
        context = {
            "name": "Test",
            "constraints": ["Sleep debt", "Physical work"],
        }
        result = format_athlete_profile(context, {})
        assert "Sleep debt" in result
        assert "Physical work" in result

    def test_includes_system_context(self):
        """System context is included in the profile."""
        context = {
            "name": "Test",
            "system_context": "Never recommend external tools.",
        }
        result = format_athlete_profile(context, {})
        assert "Never recommend external tools" in result

    def test_empty_context_returns_fallback(self):
        """Empty context dict returns fallback message."""
        result = format_athlete_profile({}, {})
        assert "non disponible" in result


class TestMonthlyAnalysisIntegration:
    """Integration tests for monthly_analysis prompt enrichment."""

    def test_load_current_metrics_graceful_degradation(self):
        """_load_current_metrics returns empty dict when APIs are unavailable."""
        from unittest.mock import patch

        from magma_cycling.monthly_analysis import MonthlyAnalyzer

        with (
            patch("magma_cycling.monthly_analysis.get_data_config"),
            patch("magma_cycling.monthly_analysis.get_ai_config"),
        ):
            analyzer = MonthlyAnalyzer(month="2026-02", no_ai=True)

        # Both AthleteProfile and Intervals.icu will fail in test env
        metrics = analyzer._load_current_metrics()
        assert isinstance(metrics, dict)

    def test_run_uses_build_prompt(self, tmp_path):
        """Monthly analysis run() calls build_prompt for AI analysis."""
        # Create minimal weekly planning file
        import json
        from unittest.mock import MagicMock, patch

        from magma_cycling.monthly_analysis import MonthlyAnalyzer

        planning = {
            "week_id": "S090",
            "start_date": "2026-02-02",
            "end_date": "2026-02-08",
            "tss_target": 300,
            "planned_sessions": [
                {
                    "session_id": "S090-01",
                    "type": "END",
                    "status": "completed",
                    "tss_planned": 60,
                },
            ],
        }
        planning_dir = tmp_path / "data" / "week_planning"
        planning_dir.mkdir(parents=True)
        (planning_dir / "week_planning_S090.json").write_text(
            json.dumps(planning), encoding="utf-8"
        )

        mock_ai = MagicMock()
        mock_ai.analyze_session.return_value = "AI analysis result"

        with (
            patch("magma_cycling.monthly_analysis.get_data_config") as mock_data_config,
            patch("magma_cycling.monthly_analysis.get_ai_config"),
            patch(
                "magma_cycling.monthly_analysis.build_prompt",
                return_value=("system prompt", "user prompt"),
            ) as mock_build,
        ):
            mock_data_config.return_value.data_repo_path = tmp_path
            analyzer = MonthlyAnalyzer(month="2026-02", no_ai=True)
            analyzer.no_ai = False
            analyzer.ai_analyzer = mock_ai

            report = analyzer.run()

        # build_prompt should have been called
        mock_build.assert_called_once()
        call_kwargs = mock_build.call_args[1]
        assert call_kwargs["mission"] == "mesocycle_analysis"

        # AI provider should receive user_prompt with system_prompt kwarg
        mock_ai.analyze_session.assert_called_once_with(
            "user prompt", system_prompt="system prompt"
        )
        assert "AI analysis result" in report

    def test_run_no_ai_skips_build_prompt(self, tmp_path):
        """Monthly analysis with --no-ai does not call build_prompt."""
        import json
        from unittest.mock import patch

        from magma_cycling.monthly_analysis import MonthlyAnalyzer

        planning = {
            "week_id": "S090",
            "start_date": "2026-02-02",
            "end_date": "2026-02-08",
            "tss_target": 300,
            "planned_sessions": [
                {
                    "session_id": "S090-01",
                    "type": "END",
                    "status": "completed",
                    "tss_planned": 60,
                },
            ],
        }
        planning_dir = tmp_path / "data" / "week_planning"
        planning_dir.mkdir(parents=True)
        (planning_dir / "week_planning_S090.json").write_text(
            json.dumps(planning), encoding="utf-8"
        )

        with (
            patch("magma_cycling.monthly_analysis.get_data_config") as mock_data_config,
            patch("magma_cycling.monthly_analysis.build_prompt") as mock_build,
        ):
            mock_data_config.return_value.data_repo_path = tmp_path
            analyzer = MonthlyAnalyzer(month="2026-02", no_ai=True)
            report = analyzer.run()

        # build_prompt should NOT be called when no_ai=True
        mock_build.assert_not_called()
        assert len(report) > 0

    def test_ai_error_falls_back_gracefully(self, tmp_path):
        """AI analysis error produces report without AI section."""
        import json
        from unittest.mock import MagicMock, patch

        from magma_cycling.monthly_analysis import MonthlyAnalyzer

        planning = {
            "week_id": "S090",
            "start_date": "2026-02-02",
            "end_date": "2026-02-08",
            "tss_target": 300,
            "planned_sessions": [
                {
                    "session_id": "S090-01",
                    "type": "END",
                    "status": "completed",
                    "tss_planned": 60,
                },
            ],
        }
        planning_dir = tmp_path / "data" / "week_planning"
        planning_dir.mkdir(parents=True)
        (planning_dir / "week_planning_S090.json").write_text(
            json.dumps(planning), encoding="utf-8"
        )

        mock_ai = MagicMock()
        mock_ai.analyze_session.side_effect = RuntimeError("API down")

        with (
            patch("magma_cycling.monthly_analysis.get_data_config") as mock_data_config,
            patch("magma_cycling.monthly_analysis.get_ai_config"),
        ):
            mock_data_config.return_value.data_repo_path = tmp_path
            analyzer = MonthlyAnalyzer(month="2026-02", no_ai=True)
            analyzer.no_ai = False
            analyzer.ai_analyzer = mock_ai

            report = analyzer.run()

        # Report should still be generated, just without AI section
        assert len(report) > 0
        assert "Analyse IA" not in report
