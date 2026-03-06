"""Tests for prompt builder and mission templates."""

import pytest

from magma_cycling.prompts.prompt_builder import (
    VALID_MISSIONS,
    build_prompt,
    format_athlete_profile,
    load_current_metrics,
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

    def test_includes_overtraining_risk(self):
        """Overtraining risk indicators appear in profile."""
        context = {"name": "Test", "age": 54}
        metrics = {
            "ftp": 220,
            "weight": 84.0,
            "ctl": 45.0,
            "atl": 60.0,
            "overtraining_risk": "high",
            "overtraining_veto": False,
            "overtraining_factors": ["ATL/CTL ratio elevated (1.33)"],
            "atl_ctl_ratio": 1.33,
            "tsb": -15.0,
            "recovery_priority": "medium",
            "recovery_recommendation": "Reduce intensity -10% OR duration -15%.",
            "intensity_limit_pct": 90,
        }
        result = format_athlete_profile(context, metrics)
        assert "Indicateurs de charge:" in result
        assert "TSB: -15.0" in result
        assert "ATL/CTL ratio: 1.33" in result
        assert "Risque surentrainement: HIGH" in result
        assert "Prescription recup:" in result
        assert "Intensite max: 90% FTP" in result

    def test_veto_displayed_when_active(self):
        """VETO message appears when overtraining_veto is True."""
        context = {"name": "Test", "age": 54}
        metrics = {
            "overtraining_risk": "critical",
            "overtraining_veto": True,
            "overtraining_factors": [],
            "atl_ctl_ratio": 1.85,
            "tsb": -28.0,
            "recovery_recommendation": "VETO: rest required",
            "intensity_limit_pct": 55,
        }
        result = format_athlete_profile(context, metrics)
        assert "VETO ACTIF" in result

    def test_no_indicators_without_risk(self):
        """No 'Indicateurs de charge' section if no overtraining_risk."""
        context = {"name": "Test", "age": 54}
        metrics = {"ftp": 220, "weight": 84.0}
        result = format_athlete_profile(context, metrics)
        assert "Indicateurs de charge" not in result

    def test_acwr_monotony_strain_displayed(self):
        """ACWR, Monotony, Strain appear in load indicators."""
        context = {"name": "Test", "age": 54}
        metrics = {
            "overtraining_risk": "low",
            "overtraining_veto": False,
            "overtraining_factors": [],
            "atl_ctl_ratio": 0.95,
            "tsb": 3.0,
            "recovery_recommendation": "Normal training.",
            "intensity_limit_pct": 100,
            "acwr": 1.1,
            "monotony": 1.5,
            "strain": 2800,
        }
        result = format_athlete_profile(context, metrics)
        assert "ACWR: 1.10 (optimal)" in result
        assert "Monotonie: 1.50 (OK)" in result
        assert "Strain: 2800 (OK)" in result

    def test_acwr_danger_label(self):
        """ACWR > 1.5 shows DANGER label."""
        context = {"name": "Test", "age": 54}
        metrics = {
            "overtraining_risk": "high",
            "overtraining_veto": False,
            "overtraining_factors": [],
            "atl_ctl_ratio": 1.6,
            "tsb": -18.0,
            "acwr": 1.8,
        }
        result = format_athlete_profile(context, metrics)
        assert "ACWR: 1.80 (DANGER)" in result

    def test_intensity_100_not_displayed(self):
        """Intensity limit of 100% is not displayed (normal training)."""
        context = {"name": "Test", "age": 54}
        metrics = {
            "overtraining_risk": "low",
            "overtraining_veto": False,
            "overtraining_factors": [],
            "atl_ctl_ratio": 0.95,
            "tsb": 3.0,
            "recovery_recommendation": "Normal training.",
            "intensity_limit_pct": 100,
        }
        result = format_athlete_profile(context, metrics)
        assert "Intensite max" not in result


class TestLoadCurrentMetricsDerived:
    """Tests for derived metrics in load_current_metrics()."""

    def test_derived_metrics_computed_from_ctl_atl(self):
        """When CTL/ATL available, derived metrics are computed."""
        from unittest.mock import MagicMock, patch

        mock_client = MagicMock()
        mock_client.get_wellness.return_value = [
            {"ctl": 50.0, "atl": 65.0, "rampRate": 4.0, "sleepSecs": 25200}
        ]
        mock_client.get_activities.return_value = []

        with (
            patch(
                "magma_cycling.config.AthleteProfile",
                side_effect=Exception("no env"),
            ),
            patch(
                "magma_cycling.config.create_intervals_client",
                return_value=mock_client,
            ),
        ):
            result = load_current_metrics()

        assert result["atl_ctl_ratio"] == 1.3
        assert result["tsb"] == -15.0
        assert result["overtraining_risk"] in ("low", "medium", "high", "critical")
        assert isinstance(result["overtraining_veto"], bool)
        assert isinstance(result["recovery_priority"], str)
        assert isinstance(result["recovery_recommendation"], str)
        assert isinstance(result["intensity_limit_pct"], int)

    def test_no_derived_metrics_without_ctl(self):
        """Without CTL, no derived metrics are computed."""
        from unittest.mock import MagicMock, patch

        mock_client = MagicMock()
        mock_client.get_wellness.return_value = [{"rampRate": 4.0}]

        with (
            patch(
                "magma_cycling.config.AthleteProfile",
                side_effect=Exception("no env"),
            ),
            patch(
                "magma_cycling.config.create_intervals_client",
                return_value=mock_client,
            ),
        ):
            result = load_current_metrics()

        assert "overtraining_risk" not in result
        assert "atl_ctl_ratio" not in result

    def test_acwr_computed_with_activities(self):
        """ACWR/Monotony/Strain computed when activities available."""
        from datetime import datetime, timedelta
        from unittest.mock import MagicMock, patch

        mock_client = MagicMock()
        mock_client.get_wellness.return_value = [{"ctl": 50.0, "atl": 45.0, "rampRate": 3.0}]
        today = datetime.now().date()
        activities = []
        for i in range(28):
            d = today - timedelta(days=27 - i)
            activities.append(
                {
                    "start_date_local": d.isoformat() + "T08:00:00",
                    "icu_training_load": 50.0,
                }
            )
        mock_client.get_activities.return_value = activities

        with (
            patch(
                "magma_cycling.config.AthleteProfile",
                side_effect=Exception("no env"),
            ),
            patch(
                "magma_cycling.config.create_intervals_client",
                return_value=mock_client,
            ),
        ):
            result = load_current_metrics()

        assert "acwr" in result
        assert result["acwr"] == 1.0  # Uniform load
        assert "monotony" in result
        assert "strain" in result


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


class TestLoadCurrentMetrics:
    """Tests for load_current_metrics()."""

    def test_returns_dict(self):
        """load_current_metrics always returns a dict."""
        result = load_current_metrics()
        assert isinstance(result, dict)

    def test_graceful_without_env(self):
        """Without env vars / API, returns empty dict."""
        result = load_current_metrics()
        assert isinstance(result, dict)

    def test_includes_ftp_when_available(self):
        """With mocked AthleteProfile, returns ftp/weight."""
        from unittest.mock import MagicMock, patch

        mock_profile = MagicMock()
        mock_profile.ftp = 230
        mock_profile.weight = 85.0

        mock_cls = MagicMock()
        mock_cls.from_env.return_value = mock_profile

        with (
            patch("magma_cycling.config.AthleteProfile", mock_cls),
            patch(
                "magma_cycling.config.create_intervals_client",
                side_effect=Exception("no API"),
            ),
        ):
            result = load_current_metrics()

        assert result["ftp"] == 230
        assert result["weight"] == 85.0

    def test_includes_ctl_atl_when_available(self):
        """With mocked Intervals.icu, returns ctl/atl/ramp_rate."""
        from unittest.mock import MagicMock, patch

        mock_client = MagicMock()
        mock_client.get_wellness.return_value = [{"ctl": 42.5, "atl": 38.0, "rampRate": 3.2}]

        with (
            patch(
                "magma_cycling.config.AthleteProfile",
                side_effect=Exception("no env"),
            ),
            patch(
                "magma_cycling.config.create_intervals_client",
                return_value=mock_client,
            ),
        ):
            result = load_current_metrics()

        assert result["ctl"] == 42.5
        assert result["atl"] == 38.0
        assert result["ramp_rate"] == 3.2


class TestDailySyncIntegration:
    """Integration tests for daily-sync AI analysis system_prompt."""

    def test_daily_sync_passes_system_prompt(self):
        """daily-sync AI analysis passes system_prompt to analyzer."""
        from unittest.mock import MagicMock, patch

        from magma_cycling.workflows.sync.ai_analysis import AIAnalysisMixin

        mixin = AIAnalysisMixin()
        mixin.enable_ai_analysis = True
        mixin.ai_analyzer = MagicMock()
        mixin.ai_analyzer.analyze_session.return_value = "AI result text here"
        mixin.history_manager = MagicMock()
        mixin.history_manager.read_history.return_value = ""
        mixin.history_manager.insert_analysis.return_value = True
        mixin.client = MagicMock()
        mixin.client.get_wellness.return_value = [{}]
        mixin.client.get_planned_workout.return_value = None
        mixin.prompt_generator = MagicMock()
        mixin.prompt_generator.load_athlete_context.return_value = {}
        mixin.prompt_generator.load_recent_workouts.return_value = []
        mixin.prompt_generator.format_activity_data.return_value = {}
        mixin.prompt_generator.load_periodization_context.return_value = {}
        mixin.prompt_generator.generate_prompt.return_value = "user prompt"

        activity = {
            "id": "i999",
            "name": "Test Activity",
            "start_date_local": "2026-03-05T08:00:00",
        }

        with (
            patch(
                "magma_cycling.workflows.sync.ai_analysis.load_current_metrics",
                return_value={"ftp": 220},
            ),
            patch(
                "magma_cycling.workflows.sync.ai_analysis.build_prompt",
                return_value=("system prompt", ""),
            ) as mock_build,
        ):
            result = mixin.analyze_activity(activity)

        mock_build.assert_called_once_with(
            mission="daily_feedback",
            current_metrics={"ftp": 220},
            workflow_data="",
        )
        mixin.ai_analyzer.analyze_session.assert_called_once_with(
            "user prompt", system_prompt="system prompt"
        )
        assert result is not None


class TestEndOfWeekIntegration:
    """Integration tests for end-of-week AI workout generation system_prompt."""

    def test_eow_passes_system_prompt(self, tmp_path):
        """end-of-week workout gen passes system_prompt to analyzer."""
        from datetime import date
        from unittest.mock import MagicMock, patch

        from magma_cycling.workflows.eow.ai_workouts import AIWorkoutsMixin

        mixin = AIWorkoutsMixin()
        mixin.provider = "claude_api"
        mixin.dry_run = False
        mixin.week_next = "S095"
        mixin.next_start_date = date(2026, 3, 9)
        mixin.planning_dir = tmp_path

        mock_analyzer = MagicMock()
        mock_analyzer.analyze_session.return_value = "workout content"
        mock_analyzer.get_provider_info.return_value = {
            "provider": "claude_api",
            "model": "claude-3",
        }

        mock_planner = MagicMock()
        mock_planner.generate_planning_prompt.return_value = "planning prompt"

        mock_ai_config = MagicMock()
        mock_ai_config.get_provider_config.return_value = {}

        with (
            patch(
                "magma_cycling.workflows.eow.ai_workouts.load_current_metrics",
                return_value={"ftp": 220},
            ),
            patch(
                "magma_cycling.workflows.eow.ai_workouts.build_prompt",
                return_value=("system prompt", ""),
            ) as mock_build,
            patch(
                "magma_cycling.ai_providers.factory.AIProviderFactory.validate_provider_config",
                return_value=(True, "OK"),
            ),
            patch(
                "magma_cycling.ai_providers.factory.AIProviderFactory.create",
                return_value=mock_analyzer,
            ),
            patch("magma_cycling.config.get_ai_config", return_value=mock_ai_config),
            patch("magma_cycling.weekly_planner.WeeklyPlanner", return_value=mock_planner),
        ):
            result = mixin._get_workouts_api("claude_api")

        mock_build.assert_called_once_with(
            mission="weekly_planning",
            current_metrics={"ftp": 220},
            workflow_data="",
        )
        mock_analyzer.analyze_session.assert_called_once_with(
            "planning prompt", system_prompt="system prompt"
        )
        assert result is True


class TestWorkflowCoachIntegration:
    """Integration tests for workflow_coach step 3 system_prompt."""

    def test_coach_passes_system_prompt(self):
        """workflow_coach step 3 passes system_prompt to analyzer."""
        from unittest.mock import MagicMock, patch

        from magma_cycling.workflows.coach.ai_analysis import AIAnalysisMixin

        mixin = AIAnalysisMixin()
        mixin.current_provider = "claude_api"
        mixin.activity_name = None
        mixin.activity_id = "i999"
        mixin.ai_analyzer = MagicMock()
        mixin.ai_analyzer.analyze_session.return_value = "analysis result"
        mixin.ai_config = MagicMock()

        # Mock clipboard read
        mock_clipboard = MagicMock()
        mock_clipboard.stdout = "prompt from clipboard"

        with (
            patch(
                "magma_cycling.workflows.coach.ai_analysis.load_current_metrics",
                return_value={"ftp": 220},
            ),
            patch(
                "magma_cycling.workflows.coach.ai_analysis.build_prompt",
                return_value=("system prompt", ""),
            ) as mock_build,
            patch("subprocess.run") as mock_run,
        ):
            # Mock prepare_analysis subprocess (returncode 0)
            mock_prepare = MagicMock()
            mock_prepare.returncode = 0
            # Mock pbpaste
            mock_pbpaste = MagicMock()
            mock_pbpaste.stdout = "prompt from clipboard"
            mock_run.side_effect = [mock_prepare, mock_pbpaste]

            # Mock wait_user to avoid interactive input
            mixin.clear_screen = MagicMock()
            mixin.print_header = MagicMock()
            mixin.print_separator = MagicMock()
            mixin.wait_user = MagicMock()

            mixin.step_3_prepare_analysis()

        mock_build.assert_called_once_with(
            mission="daily_feedback",
            current_metrics={"ftp": 220},
            workflow_data="",
        )
        mixin.ai_analyzer.analyze_session.assert_called_once_with(
            "prompt from clipboard",
            dataset=None,
            system_prompt="system prompt",
        )
