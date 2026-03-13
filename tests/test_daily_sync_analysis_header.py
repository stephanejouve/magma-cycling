"""Tests for analysis header prepend in daily-sync ai_analysis.py."""

from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def ai_analysis_mixin():
    """Create an AIAnalysisMixin instance with mocked dependencies."""
    from magma_cycling.workflows.sync.ai_analysis import AIAnalysisMixin

    mixin = AIAnalysisMixin.__new__(AIAnalysisMixin)
    mixin.enable_ai_analysis = True
    mixin.ai_analyzer = Mock()
    mixin.history_manager = Mock()
    mixin.client = Mock()
    mixin.prompt_generator = Mock()
    return mixin


def _make_activity(name="S084-04-END-EnduranceLongue-V001", activity_id="i131572602"):
    """Create a mock activity dict."""
    return {
        "id": activity_id,
        "name": name,
        "start_date_local": "2026-03-12T10:00:00",
        "type": "VirtualRide",
        "moving_time": 5400,
        "icu_training_load": 80,
        "icu_intensity": 0.72,
    }


class TestAnalysisHeaderPrepend:
    """Tests for header prepend logic in analyze_activity()."""

    def test_raw_analysis_gets_header_prepended(self, ai_analysis_mixin):
        """Analysis without ### header gets the standard header prepended."""
        raw_analysis = (
            "#### Métriques Pré-séance\n"
            "- CTL : 45\n"
            "- ATL : 57\n\n"
            "#### Exécution\n"
            "- Durée : 90min\n"
            "- IF : 0.72\n"
        )
        ai_analysis_mixin.ai_analyzer.analyze_session.return_value = raw_analysis
        ai_analysis_mixin.history_manager.insert_analysis.return_value = True
        ai_analysis_mixin.history_manager.read_history.return_value = ""
        ai_analysis_mixin.client.get_wellness.return_value = []
        ai_analysis_mixin.prompt_generator.load_athlete_context.return_value = {}
        ai_analysis_mixin.prompt_generator.load_recent_workouts.return_value = []
        ai_analysis_mixin.prompt_generator.format_activity_data.return_value = {}
        ai_analysis_mixin.prompt_generator.load_periodization_context.return_value = {}
        ai_analysis_mixin.prompt_generator.generate_prompt.return_value = "prompt"

        activity = _make_activity()

        with (
            patch(
                "magma_cycling.workflows.sync.ai_analysis.load_current_metrics",
                return_value={},
            ),
            patch(
                "magma_cycling.workflows.sync.ai_analysis.build_prompt",
                return_value=("system", ""),
            ),
            patch(
                "magma_cycling.workflows.sync.ai_analysis.planning_tower",
            ),
        ):
            result = ai_analysis_mixin.analyze_activity(activity)

        assert result == raw_analysis

        # Verify insert_analysis was called with the header-prepended version
        call_args = ai_analysis_mixin.history_manager.insert_analysis.call_args[0][0]
        assert call_args.startswith("### S084-04-END-EnduranceLongue-V001\n")
        assert "ID : i131572602\n" in call_args
        assert "Date : 12/03/2026\n" in call_args
        assert "#### Métriques Pré-séance" in call_args

    def test_analysis_with_header_kept_as_is(self, ai_analysis_mixin):
        """Analysis already starting with ### is not double-headed."""
        formatted_analysis = (
            "### S084-04-END-EnduranceLongue-V001\n"
            "ID : i131572602\n"
            "Date : 12/03/2026\n\n"
            "#### Exécution\n"
            "- Durée : 90min\n"
        )
        ai_analysis_mixin.ai_analyzer.analyze_session.return_value = formatted_analysis
        ai_analysis_mixin.history_manager.insert_analysis.return_value = True
        ai_analysis_mixin.history_manager.read_history.return_value = ""
        ai_analysis_mixin.client.get_wellness.return_value = []
        ai_analysis_mixin.prompt_generator.load_athlete_context.return_value = {}
        ai_analysis_mixin.prompt_generator.load_recent_workouts.return_value = []
        ai_analysis_mixin.prompt_generator.format_activity_data.return_value = {}
        ai_analysis_mixin.prompt_generator.load_periodization_context.return_value = {}
        ai_analysis_mixin.prompt_generator.generate_prompt.return_value = "prompt"

        activity = _make_activity()

        with (
            patch(
                "magma_cycling.workflows.sync.ai_analysis.load_current_metrics",
                return_value={},
            ),
            patch(
                "magma_cycling.workflows.sync.ai_analysis.build_prompt",
                return_value=("system", ""),
            ),
            patch(
                "magma_cycling.workflows.sync.ai_analysis.planning_tower",
            ),
        ):
            ai_analysis_mixin.analyze_activity(activity)

        # insert_analysis should receive the original (already formatted) analysis
        call_args = ai_analysis_mixin.history_manager.insert_analysis.call_args[0][0]
        assert call_args == formatted_analysis
        # No double ### header
        assert call_args.count("### S084-04") == 1

    def test_header_uses_french_date(self, ai_analysis_mixin):
        """Prepended header uses DD/MM/YYYY date format, not ISO."""
        raw_analysis = "#### Exécution\n- Durée : 60min\n"
        ai_analysis_mixin.ai_analyzer.analyze_session.return_value = raw_analysis
        ai_analysis_mixin.history_manager.insert_analysis.return_value = True
        ai_analysis_mixin.history_manager.read_history.return_value = ""
        ai_analysis_mixin.client.get_wellness.return_value = []
        ai_analysis_mixin.prompt_generator.load_athlete_context.return_value = {}
        ai_analysis_mixin.prompt_generator.load_recent_workouts.return_value = []
        ai_analysis_mixin.prompt_generator.format_activity_data.return_value = {}
        ai_analysis_mixin.prompt_generator.load_periodization_context.return_value = {}
        ai_analysis_mixin.prompt_generator.generate_prompt.return_value = "prompt"

        activity = _make_activity()

        with (
            patch(
                "magma_cycling.workflows.sync.ai_analysis.load_current_metrics",
                return_value={},
            ),
            patch(
                "magma_cycling.workflows.sync.ai_analysis.build_prompt",
                return_value=("system", ""),
            ),
            patch(
                "magma_cycling.workflows.sync.ai_analysis.planning_tower",
            ),
        ):
            ai_analysis_mixin.analyze_activity(activity)

        call_args = ai_analysis_mixin.history_manager.insert_analysis.call_args[0][0]
        # Date should be DD/MM/YYYY (French format), not 2026-03-12 (ISO)
        assert "Date : 12/03/2026" in call_args
        assert "2026-03-12" not in call_args
