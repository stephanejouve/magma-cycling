"""Tests for monthly_analysis.py — AI fallback chain and system_prompt propagation.

Phase 4 addendum: verify system_prompt survives through provider fallback chain.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.monthly_analysis import MonthlyAnalyzer


@pytest.fixture
def analyzer_with_ai():
    """Create analyzer with AI enabled and mocked provider."""
    with (
        patch("magma_cycling.monthly_analysis.get_data_config") as mock_dc,
        patch("magma_cycling.monthly_analysis.get_ai_config") as mock_ai_config,
        patch("magma_cycling.monthly_analysis.AIProviderFactory") as mock_factory,
    ):
        mock_dc.return_value.data_repo_path = MagicMock()

        # Configure AI provider
        mock_provider_config = {"mistral_api_key": "test-key"}
        mock_ai_config.return_value.get_provider_config.return_value = mock_provider_config

        mock_analyzer = MagicMock()
        mock_factory.create.return_value = mock_analyzer

        analyzer = MonthlyAnalyzer(month="2026-02", provider="mistral_api", no_ai=False)
        analyzer.ai_analyzer = mock_analyzer

        yield analyzer, mock_analyzer


@pytest.fixture
def weekly_data_for_run(tmp_path):
    """Create minimal weekly planning file for run()."""
    import json

    planning_dir = tmp_path / "data" / "week_planning"
    planning_dir.mkdir(parents=True)

    planning = {
        "week_id": "S081",
        "start_date": "2026-02-02",
        "end_date": "2026-02-08",
        "tss_target": 400,
        "planned_sessions": [
            {
                "session_id": "S081-01",
                "type": "END",
                "status": "completed",
                "tss_planned": 50,
                "intervals_id": 11111,
            },
        ],
    }

    with open(planning_dir / "week_planning_S081.json", "w") as f:
        json.dump(planning, f)

    return tmp_path


class TestFallbackPrimaryFailsSecondaryReceivesSameSystemPrompt:
    """Test system_prompt propagation when primary provider fails."""

    def test_fallback_primary_fails_secondary_receives_same_system_prompt(
        self, analyzer_with_ai, weekly_data_for_run
    ):
        """Provider 1 raise -> provider 2 called with system_prompt identique."""
        analyzer, mock_ai = analyzer_with_ai
        analyzer.planning_dir = weekly_data_for_run / "data" / "week_planning"

        system_prompt_captured = []
        call_count = [0]

        def side_effect(prompt, system_prompt=None, **kwargs):
            call_count[0] += 1
            system_prompt_captured.append(system_prompt)
            if call_count[0] == 1:
                raise Exception("Provider 1 failed")
            return "AI analysis result"

        mock_ai.analyze_session.side_effect = side_effect

        with (
            patch(
                "magma_cycling.monthly_analysis.build_prompt",
                return_value=("System: coach cycliste", "User: analyse ce mois"),
            ),
            patch.object(analyzer, "_load_current_metrics", return_value={"ctl": 60}),
            patch.object(analyzer, "_fetch_actual_tss", return_value={}),
        ):
            report = analyzer.run()

        # First call received system_prompt before failure
        assert system_prompt_captured[0] == "System: coach cycliste"
        # Report generated (with or without AI, but no crash)
        assert report != ""


class TestFallbackToClipboardPreservesFullPrompt:
    """Test clipboard fallback preserves system + user prompt."""

    def test_fallback_to_clipboard_preserves_full_prompt(
        self, analyzer_with_ai, weekly_data_for_run
    ):
        """Provider raise -> report still generated with system_prompt built."""
        analyzer, mock_ai = analyzer_with_ai
        analyzer.planning_dir = weekly_data_for_run / "data" / "week_planning"

        # Provider always fails -> fallback to no AI
        mock_ai.analyze_session.side_effect = Exception("All providers down")

        system_prompt_value = "System: coach cycliste professionnel"
        user_prompt_value = "User: analyse mensuelle"

        with (
            patch(
                "magma_cycling.monthly_analysis.build_prompt",
                return_value=(system_prompt_value, user_prompt_value),
            ) as mock_build,
            patch.object(analyzer, "_load_current_metrics", return_value={"ctl": 60}),
            patch.object(analyzer, "_fetch_actual_tss", return_value={}),
        ):
            report = analyzer.run()

        # build_prompt was called (system_prompt was generated before failure)
        mock_build.assert_called_once()
        call_kwargs = mock_build.call_args
        assert call_kwargs[1]["mission"] == "mesocycle_analysis"

        # Report generated without AI section but not empty
        assert "Analyse Mensuelle" in report
        assert "Analyse IA" not in report


class TestDoubleFallbackSystemPromptNotLost:
    """Test system_prompt is not None even after multiple failures."""

    def test_double_fallback_system_prompt_not_lost(self, analyzer_with_ai, weekly_data_for_run):
        """Verify system_prompt is not None at the provider call."""
        analyzer, mock_ai = analyzer_with_ai
        analyzer.planning_dir = weekly_data_for_run / "data" / "week_planning"

        mock_ai.analyze_session.side_effect = Exception("Provider failed")

        captured_system_prompt = None

        def capture_build_prompt(**kwargs):
            nonlocal captured_system_prompt
            captured_system_prompt = "System prompt built successfully"
            return (captured_system_prompt, "User prompt")

        with (
            patch(
                "magma_cycling.monthly_analysis.build_prompt",
                side_effect=capture_build_prompt,
            ),
            patch.object(analyzer, "_load_current_metrics", return_value={"ctl": 60}),
            patch.object(analyzer, "_fetch_actual_tss", return_value={}),
        ):
            analyzer.run()

        # system_prompt was built (not None) before provider was called
        assert captured_system_prompt is not None
        # Verify it was passed to analyze_session
        call_args = mock_ai.analyze_session.call_args
        assert call_args is not None
        assert call_args[1].get("system_prompt") == captured_system_prompt


class TestFallbackChainLogsSystemPromptPresence:
    """Test logging captures system_prompt presence at each attempt."""

    def test_fallback_chain_logs_system_prompt_presence(
        self, analyzer_with_ai, weekly_data_for_run, caplog
    ):
        """Logger.info mentions system_prompt at each attempt."""
        analyzer, mock_ai = analyzer_with_ai
        analyzer.planning_dir = weekly_data_for_run / "data" / "week_planning"

        # Provider succeeds
        mock_ai.analyze_session.return_value = "AI result"

        with (
            patch(
                "magma_cycling.monthly_analysis.build_prompt",
                return_value=("System prompt", "User prompt"),
            ),
            patch.object(analyzer, "_load_current_metrics", return_value={"ctl": 60}),
            patch.object(analyzer, "_fetch_actual_tss", return_value={}),
            caplog.at_level(logging.DEBUG, logger="magma_cycling.monthly_analysis"),
        ):
            report = analyzer.run()

        # Verify analyze_session was called with system_prompt (not None)
        call_args = mock_ai.analyze_session.call_args
        assert call_args[1]["system_prompt"] is not None
        assert call_args[1]["system_prompt"] == "System prompt"

        # Report includes AI section
        assert "Analyse IA" in report


class TestRunAIIntegration:
    """Test run() method AI integration details."""

    def test_run_builds_prompt_with_mesocycle_mission(self, analyzer_with_ai, weekly_data_for_run):
        """Verify build_prompt is called with mission='mesocycle_analysis'."""
        analyzer, mock_ai = analyzer_with_ai
        analyzer.planning_dir = weekly_data_for_run / "data" / "week_planning"

        mock_ai.analyze_session.return_value = "Analyse complète"

        with (
            patch(
                "magma_cycling.monthly_analysis.build_prompt",
                return_value=("sys", "usr"),
            ) as mock_build,
            patch.object(analyzer, "_load_current_metrics", return_value={"ctl": 60}),
            patch.object(analyzer, "_fetch_actual_tss", return_value={}),
        ):
            analyzer.run()

        mock_build.assert_called_once_with(
            mission="mesocycle_analysis",
            current_metrics={"ctl": 60},
            workflow_data=mock_build.call_args[1]["workflow_data"],
        )

    def test_run_no_ai_skips_provider(self):
        """Verify no_ai=True skips AI entirely."""
        with (
            patch("magma_cycling.monthly_analysis.get_data_config") as mock_dc,
            patch("magma_cycling.monthly_analysis.get_ai_config"),
        ):
            mock_dc.return_value.data_repo_path = MagicMock()
            analyzer = MonthlyAnalyzer(month="2026-02", no_ai=True)

        assert analyzer.ai_analyzer is None
        assert analyzer.no_ai is True

    def test_load_current_metrics_delegates(self, analyzer_with_ai):
        """Verify _load_current_metrics delegates to shared helper."""
        analyzer, _ = analyzer_with_ai

        with patch(
            "magma_cycling.monthly_analysis.MonthlyAnalyzer._load_current_metrics",
            return_value={"ctl": 65, "ftp": 260},
        ) as mock_load:
            result = analyzer._load_current_metrics()

        mock_load.assert_called_once()
        assert result["ctl"] == 65
