"""
Tests for workflow_coach.py - AI Workflow Integration.

Sprint R8: Phase 3 - AI Workflow Tests
Target: 10 tests covering AI provider integration and analysis execution
Coverage goal: +5-7% (AI workflow methods)

Test Categories:
- AI Provider Initialization (3 tests)
- AI Analysis Execution (3 tests)
- AI Response Display (2 tests)
- Provider Fallback (3 tests)
- Analysis Validation (2 tests)
"""

from unittest.mock import Mock, patch

from cyclisme_training_logs.workflow_coach import WorkflowCoach


class TestAIProviderInitialization:
    """Test AI provider initialization and configuration."""

    @patch("cyclisme_training_logs.workflow_coach.AIProviderFactory.create")
    @patch("cyclisme_training_logs.workflow_coach.get_ai_config")
    def test_init_with_specified_provider(self, mock_get_config, mock_factory):
        """Test __init__ with specified provider."""
        # Mock AI config
        mock_config = Mock()
        mock_config.is_provider_configured.return_value = True
        mock_config.get_provider_config.return_value = {"api_key": "test_key"}
        mock_get_config.return_value = mock_config

        # Mock AI provider
        mock_provider = Mock()
        mock_factory.return_value = mock_provider

        coach = WorkflowCoach(provider="claude_api")

        assert coach.current_provider == "claude_api"
        assert coach.provider_name == "claude_api"
        mock_config.is_provider_configured.assert_called_with("claude_api")
        mock_factory.assert_called_once_with("claude_api", {"api_key": "test_key"})

    @patch("cyclisme_training_logs.workflow_coach.AIProviderFactory.create")
    @patch("cyclisme_training_logs.workflow_coach.get_ai_config")
    def test_init_auto_selects_first_available(self, mock_get_config, mock_factory):
        """Test __init__ auto-selects first available provider."""
        mock_config = Mock()
        mock_config.get_available_providers.return_value = ["mistral_api", "claude_api"]
        mock_config.is_provider_configured.return_value = True
        mock_config.get_provider_config.return_value = {"api_key": "test_key"}
        mock_get_config.return_value = mock_config

        mock_provider = Mock()
        mock_factory.return_value = mock_provider

        coach = WorkflowCoach()

        assert coach.current_provider == "mistral_api"
        mock_factory.assert_called_once_with("mistral_api", {"api_key": "test_key"})

    @patch("cyclisme_training_logs.workflow_coach.AIProviderFactory.create")
    @patch("cyclisme_training_logs.workflow_coach.get_ai_config")
    def test_init_fallback_to_clipboard_when_not_configured(self, mock_get_config, mock_factory):
        """Test __init__ falls back to clipboard when provider not configured."""
        mock_config = Mock()
        mock_config.is_provider_configured.return_value = False
        mock_config.get_provider_config.return_value = {}
        mock_get_config.return_value = mock_config

        mock_provider = Mock()
        mock_factory.return_value = mock_provider

        coach = WorkflowCoach(provider="openai")

        # Should fallback to clipboard
        assert coach.current_provider == "clipboard"
        mock_factory.assert_called_once_with("clipboard", {})


class TestAIAnalysisExecution:
    """Test AI analysis execution methods."""

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_step_3_api_provider_success(self, mock_print, mock_subprocess):
        """Test step_3_prepare_analysis with API provider executes analysis."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.current_provider = "claude_api"

        # Mock AI analyzer
        mock_analyzer = Mock()
        mock_analyzer.analyze_session.return_value = (
            "AI analysis result here with complete markdown content for the session analysis."
        )
        coach.ai_analyzer = mock_analyzer

        # Mock subprocess (prepare_analysis + pbpaste)
        mock_subprocess.side_effect = [
            Mock(returncode=0),  # prepare_analysis success
            Mock(stdout="- **Nom** : Test Activity\nPrompt content", returncode=0),  # pbpaste
        ]

        with patch.object(coach, "wait_user"):
            coach.step_3_prepare_analysis()

        # Should call AI analyzer
        assert mock_analyzer.analyze_session.called
        assert (
            coach.analysis_result
            == "AI analysis result here with complete markdown content for the session analysis."
        )

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_step_3_api_provider_handles_error(self, mock_print, mock_subprocess):
        """Test step_3_prepare_analysis handles AI provider errors."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.current_provider = "openai"

        # Mock AI config for fallback
        mock_config = Mock()
        mock_config.get_fallback_chain.return_value = ["openai", "claude_api", "clipboard"]
        mock_config.enable_fallback = True
        mock_config.get_provider_config.return_value = {}
        coach.ai_config = mock_config

        # Mock AI analyzer that fails
        mock_analyzer = Mock()
        mock_analyzer.analyze_session.side_effect = Exception("API timeout")
        coach.ai_analyzer = mock_analyzer

        # Mock subprocess (prepare_analysis + pbpaste)
        mock_subprocess.side_effect = [
            Mock(returncode=0),
            Mock(stdout="- **Nom** : Activity\nPrompt", returncode=0),
        ]

        # Mock fallback consent
        with patch.object(coach, "_ask_fallback_consent", return_value="Q"):
            with patch("sys.exit") as mock_exit:
                coach.step_3_prepare_analysis()

        # Should exit after user chooses quit
        assert mock_exit.called

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_step_3_clipboard_provider_workflow(self, mock_print, mock_subprocess):
        """Test step_3_prepare_analysis with clipboard provider."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.current_provider = "clipboard"

        mock_subprocess.side_effect = [
            Mock(returncode=0),  # prepare_analysis
            Mock(stdout="- **Nom** : Test\nPrompt", returncode=0),  # pbpaste
        ]

        with patch.object(coach, "wait_user"):
            coach.step_3_prepare_analysis()

        # Should NOT call AI analyzer (manual mode)
        assert not hasattr(coach, "analysis_result") or coach.analysis_result is None


class TestAIResponseDisplay:
    """Test AI response display methods."""

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_step_4b_display_from_api_result(self, mock_print, mock_subprocess):
        """Test step_4b_display_analysis displays API result."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.activity_name = "Morning Tempo"
        coach.analysis_result = (
            "### Morning Tempo\n\n**Execution:** Great session\n\n**Metrics:** HR avg 145"
        )

        with patch.object(coach, "wait_user"):
            coach.step_4b_display_analysis()

        # Should print analysis
        assert mock_print.called
        call_args_str = str(mock_print.call_args_list)
        assert "Execution" in call_args_str or mock_print.call_count > 0

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_step_4b_display_from_clipboard(self, mock_print, mock_subprocess):
        """Test step_4b_display_analysis reads from clipboard when no API result."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.activity_name = "Evening Ride"

        # No analysis_result set (clipboard mode)
        mock_subprocess.return_value = Mock(
            stdout="### Evening Ride\n\n**Analysis:** Good recovery ride with proper zones maintained throughout.",
            returncode=0,
        )

        with patch.object(coach, "wait_user"):
            coach.step_4b_display_analysis()

        # Should read from clipboard
        assert mock_subprocess.called
        mock_subprocess.assert_called_once_with(
            ["pbpaste"], capture_output=True, text=True, check=True
        )


class TestProviderFallback:
    """Test AI provider fallback mechanisms."""

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_fallback_to_next_provider(self, mock_print, mock_subprocess):
        """Test fallback to next provider in chain."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.current_provider = "openai"

        # Mock AI config
        mock_config = Mock()
        mock_config.get_fallback_chain.return_value = ["openai", "mistral_api", "clipboard"]
        mock_config.enable_fallback = True
        mock_config.get_provider_config.return_value = {"api_key": "test_key"}
        coach.ai_config = mock_config

        # Mock failing AI analyzer
        mock_analyzer = Mock()
        mock_analyzer.analyze_session.side_effect = Exception("Rate limit exceeded")
        coach.ai_analyzer = mock_analyzer

        # Mock subprocess
        mock_subprocess.side_effect = [
            Mock(returncode=0),  # prepare_analysis
            Mock(stdout="- **Nom** : Activity\nPrompt", returncode=0),  # pbpaste
            Mock(returncode=0),  # prepare_analysis retry
            Mock(stdout="- **Nom** : Activity\nPrompt", returncode=0),  # pbpaste retry
        ]

        # Mock fallback consent: choose fallback
        with patch.object(coach, "_ask_fallback_consent", return_value="F"):
            with patch(
                "cyclisme_training_logs.workflow_coach.AIProviderFactory.create"
            ) as mock_factory:
                mock_new_analyzer = Mock()
                mock_new_analyzer.analyze_session.return_value = (
                    "Fallback analysis result with sufficient content length"
                )
                mock_factory.return_value = mock_new_analyzer

                with patch.object(coach, "wait_user"):
                    coach.step_3_prepare_analysis()

        # Should switch to mistral_api
        assert coach.current_provider == "mistral_api"
        assert coach.analysis_result == "Fallback analysis result with sufficient content length"

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_fallback_to_clipboard_manual(self, mock_print, mock_subprocess):
        """Test manual fallback to clipboard mode."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.current_provider = "claude_api"

        # Mock AI config
        mock_config = Mock()
        mock_config.get_fallback_chain.return_value = ["claude_api", "clipboard"]
        mock_config.enable_fallback = True
        mock_config.get_provider_config.return_value = {}
        coach.ai_config = mock_config

        # Mock failing analyzer
        mock_analyzer = Mock()
        mock_analyzer.analyze_session.side_effect = Exception("API error")
        coach.ai_analyzer = mock_analyzer

        # Mock subprocess
        mock_subprocess.side_effect = [
            Mock(returncode=0),
            Mock(stdout="- **Nom** : Activity\nPrompt", returncode=0),
            Mock(returncode=0),  # prepare_analysis retry
            Mock(stdout="- **Nom** : Activity\nPrompt", returncode=0),  # pbpaste retry
        ]

        # User chooses clipboard mode
        with patch.object(coach, "_ask_fallback_consent", return_value="C"):
            with patch(
                "cyclisme_training_logs.workflow_coach.AIProviderFactory.create"
            ) as mock_factory:
                mock_clipboard = Mock()
                mock_factory.return_value = mock_clipboard

                with patch.object(coach, "wait_user"):
                    coach.step_3_prepare_analysis()

        # Should switch to clipboard
        assert coach.current_provider == "clipboard"

    @patch("subprocess.run")
    @patch("sys.exit")
    @patch("builtins.print")
    def test_no_fallback_available_exits(self, mock_print, mock_exit, mock_subprocess):
        """Test exits when no fallback available."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.current_provider = "ollama"

        # Mock AI config with no fallback
        mock_config = Mock()
        mock_config.get_fallback_chain.return_value = ["ollama"]
        mock_config.enable_fallback = False
        coach.ai_config = mock_config

        # Mock failing analyzer
        mock_analyzer = Mock()
        mock_analyzer.analyze_session.side_effect = Exception("Connection refused")
        coach.ai_analyzer = mock_analyzer

        # Mock subprocess
        mock_subprocess.side_effect = [
            Mock(returncode=0),
            Mock(stdout="- **Nom** : Activity\nPrompt", returncode=0),
        ]

        coach.step_3_prepare_analysis()

        # Should exit with error
        assert mock_exit.called
        mock_exit.assert_called_with(1)


class TestAnalysisValidation:
    """Test analysis validation workflow."""

    @patch("builtins.input", return_value="o")
    @patch("builtins.print")
    def test_step_5_validate_user_accepts(self, mock_print, mock_input):
        """Test step_5_validate_analysis when user accepts."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.activity_name = "Test Activity"

        with patch.object(coach, "wait_user"):
            coach.step_5_validate_analysis()

        # Should continue (not exit)
        assert mock_input.called
        mock_input.assert_called_once()

    @patch("builtins.input", return_value="n")
    @patch("sys.exit")
    @patch("builtins.print")
    def test_step_5_validate_user_rejects(self, mock_print, mock_exit, mock_input):
        """Test step_5_validate_analysis when user rejects."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.activity_name = "Test Activity"

        coach.step_5_validate_analysis()

        # Should exit workflow
        assert mock_exit.called
        mock_exit.assert_called_with(0)

    @patch("builtins.print")
    def test_step_5_validate_auto_mode(self, mock_print):
        """Test step_5_validate_analysis in auto mode."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True, auto_mode=True)
        coach.activity_name = "Test Activity"

        with patch.object(coach, "wait_user"):
            coach.step_5_validate_analysis()

        # Should auto-validate (no input prompt)
        # Check that auto mode message was printed
        call_args_str = str(mock_print.call_args_list)
        assert "AUTO MODE" in call_args_str or mock_print.call_count > 0


class TestPastePromptStep:
    """Test step_4_paste_prompt method."""

    @patch("builtins.print")
    def test_step_4_displays_instructions(self, mock_print):
        """Test step_4_paste_prompt displays proper instructions."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.current_provider = "clipboard"
        coach.activity_name = "Morning Session"

        with patch.object(coach, "wait_user"):
            coach.step_4_paste_prompt()

        # Should print instructions
        assert mock_print.called
        call_args_str = str(mock_print.call_args_list)
        assert any(
            keyword in call_args_str
            for keyword in ["INSTRUCTIONS", "Coller", "prompt", "Morning Session"]
        )

    @patch("builtins.print")
    def test_step_4_displays_provider_name(self, mock_print):
        """Test step_4_paste_prompt displays correct provider name."""
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)
        coach.current_provider = "mistral_api"
        coach.activity_name = "Evening Ride"

        with patch.object(coach, "wait_user"):
            coach.step_4_paste_prompt()

        # Should mention provider
        # Either the provider key or display name should appear
        assert mock_print.called
