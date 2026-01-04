#!/usr/bin/env python3
"""
Tests for Clipboard AI Provider.

Tests ClipboardAnalyzer for manual copy/paste workflow with realistic mocks.
"""
from unittest.mock import patch

from cyclisme_training_logs.ai_providers.base import AIProvider
from cyclisme_training_logs.ai_providers.clipboard import ClipboardAnalyzer


class TestClipboardAnalyzer:
    """Tests for ClipboardAnalyzer."""

    def test_initialization(self):
        """Test that ClipboardAnalyzer initializes correctly."""
        analyzer = ClipboardAnalyzer()

        assert analyzer is not None
        assert analyzer.provider == AIProvider.CLIPBOARD

    def test_provider_is_clipboard(self):
        """Test that provider attribute is set to CLIPBOARD."""
        analyzer = ClipboardAnalyzer()

        assert analyzer.provider == AIProvider.CLIPBOARD

    @patch("cyclisme_training_logs.ai_providers.clipboard.copy_to_clipboard")
    def test_analyze_session_copies_to_clipboard(self, mock_copy):
        """Test that analyze_session copies prompt to clipboard."""
        mock_copy.return_value = True

        analyzer = ClipboardAnalyzer()
        prompt = "Test cycling analysis prompt"

        result = analyzer.analyze_session(prompt)

        # Should call copy_to_clipboard
        mock_copy.assert_called_once_with(prompt)

        # Should return instructions (not empty)
        assert result is not None
        assert len(result) > 0

    @patch("cyclisme_training_logs.ai_providers.clipboard.copy_to_clipboard")
    def test_analyze_session_with_dataset(self, mock_copy):
        """Test that analyze_session handles dataset parameter."""
        mock_copy.return_value = True

        analyzer = ClipboardAnalyzer()
        prompt = "Test prompt"
        dataset = {"activity_id": "12345", "duration": 3600}

        result = analyzer.analyze_session(prompt, dataset=dataset)

        # Should still call copy_to_clipboard (dataset is optional)
        mock_copy.assert_called_once_with(prompt)
        assert result is not None

    @patch("cyclisme_training_logs.ai_providers.clipboard.copy_to_clipboard")
    def test_analyze_session_multiline_prompt(self, mock_copy):
        """Test that analyze_session handles multiline prompts."""
        mock_copy.return_value = True

        analyzer = ClipboardAnalyzer()
        prompt = """Line 1
Line 2
Line 3"""
        result = analyzer.analyze_session(prompt)

        # Should handle multiline prompt
        mock_copy.assert_called_once_with(prompt)
        assert result is not None

    def test_get_provider_info_returns_dict(self):
        """Test that get_provider_info returns dict with expected keys."""
        analyzer = ClipboardAnalyzer()

        info = analyzer.get_provider_info()

        assert isinstance(info, dict)
        assert "provider" in info
        assert "status" in info or "model" in info

    def test_get_provider_info_has_correct_values(self):
        """Test that provider info has correct values."""
        analyzer = ClipboardAnalyzer()

        info = analyzer.get_provider_info()

        assert info["provider"] == "clipboard"
        # Check for cost info (may be in different format)
        info_str = str(info).lower()
        assert "$0" in info_str or "free" in info_str or "gratuit" in info_str

    @patch("cyclisme_training_logs.ai_providers.clipboard.copy_to_clipboard")
    def test_validate_config_always_returns_true(self, mock_copy):
        """Test that validate_config always returns True (no config needed)."""
        mock_copy.return_value = True  # Mock clipboard availability

        analyzer = ClipboardAnalyzer()

        is_valid = analyzer.validate_config()

        assert is_valid is True

    @patch("cyclisme_training_logs.ai_providers.clipboard.copy_to_clipboard")
    def test_clipboard_analyzer_is_always_available(self, mock_copy):
        """Test that clipboard analyzer doesn't require any configuration."""
        mock_copy.return_value = True  # Mock clipboard availability

        # Should not raise any errors
        analyzer = ClipboardAnalyzer()

        assert analyzer.validate_config() is True

    @patch("cyclisme_training_logs.ai_providers.clipboard.copy_to_clipboard")
    def test_analyze_session_empty_prompt(self, mock_copy):
        """Test that analyze_session handles empty prompt."""
        mock_copy.return_value = True

        analyzer = ClipboardAnalyzer()
        prompt = ""

        result = analyzer.analyze_session(prompt)

        # Should still work with empty prompt
        mock_copy.assert_called_once_with("")
        assert result is not None

    @patch("cyclisme_training_logs.ai_providers.clipboard.copy_to_clipboard")
    def test_analyze_session_large_prompt(self, mock_copy):
        """Test that analyze_session handles large prompts."""
        mock_copy.return_value = True

        analyzer = ClipboardAnalyzer()
        prompt = "X" * 50000  # 50KB prompt

        result = analyzer.analyze_session(prompt)

        # Should handle large prompt
        mock_copy.assert_called_once_with(prompt)
        assert result is not None

    @patch("cyclisme_training_logs.ai_providers.clipboard.copy_to_clipboard")
    def test_analyze_session_special_characters(self, mock_copy):
        """Test that analyze_session handles special characters."""
        mock_copy.return_value = True

        analyzer = ClipboardAnalyzer()
        prompt = "Test with émojis 🚴‍♂️ and spéciål çhars: €$£"

        result = analyzer.analyze_session(prompt)

        # Should handle special characters
        mock_copy.assert_called_once_with(prompt)
        assert result is not None

    def test_provider_info_indicates_manual_workflow(self):
        """Test that provider info clearly indicates manual workflow."""
        analyzer = ClipboardAnalyzer()

        info = analyzer.get_provider_info()

        # Should have some indication of manual workflow
        info_str = str(info).lower()
        assert "manual" in info_str or "clipboard" in info_str

    def test_multiple_analyzers_independent(self):
        """Test that multiple clipboard analyzers are independent."""
        analyzer1 = ClipboardAnalyzer()

        analyzer2 = ClipboardAnalyzer()

        assert analyzer1 is not analyzer2
        assert analyzer1.provider == analyzer2.provider == AIProvider.CLIPBOARD

    @patch("cyclisme_training_logs.ai_providers.clipboard.copy_to_clipboard")
    def test_clipboard_copy_failure_handling(self, mock_copy):
        """Test handling when clipboard copy fails."""
        mock_copy.return_value = False  # Simulate failure

        analyzer = ClipboardAnalyzer()
        prompt = "Test"

        # Should still return result (with error message)
        result = analyzer.analyze_session(prompt)

        # Should have called copy
        mock_copy.assert_called_once_with(prompt)

        # Result should contain error or fallback info
        assert result is not None
        assert len(result) > 0

    @patch("cyclisme_training_logs.ai_providers.clipboard.copy_to_clipboard")
    def test_dataset_is_ignored(self, mock_copy):
        """Test that dataset parameter is ignored by clipboard provider."""
        mock_copy.return_value = True

        analyzer = ClipboardAnalyzer()
        dataset = {"tss": 65, "if": 0.85, "duration": 7200}

        result = analyzer.analyze_session("Test prompt", dataset)

        # Dataset should not affect behavior
        mock_copy.assert_called_once_with("Test prompt")
        assert result is not None

    def test_provider_info_structure(self):
        """Test that provider info has expected structure."""
        analyzer = ClipboardAnalyzer()

        info = analyzer.get_provider_info()

        # Must have provider name
        assert "provider" in info
        assert info["provider"] == "clipboard"

        # Should have some metadata
        assert len(info) >= 2  # At least provider and one other field

    @patch("cyclisme_training_logs.ai_providers.clipboard.copy_to_clipboard")
    def test_instructions_returned_on_success(self, mock_copy):
        """Test that instructions are returned when copy succeeds."""
        mock_copy.return_value = True

        analyzer = ClipboardAnalyzer()
        result = analyzer.analyze_session("Test prompt")

        # Should return non-empty instructions
        assert result is not None
        assert len(result) > 10  # Should be substantial instructions
        assert isinstance(result, str)

    @patch("cyclisme_training_logs.ai_providers.clipboard.copy_to_clipboard")
    def test_unicode_handling(self, mock_copy):
        """Test proper handling of unicode characters."""
        mock_copy.return_value = True

        analyzer = ClipboardAnalyzer()
        # Various unicode: emoji, accents, symbols, CJK
        prompt = "Test 🚴‍♂️ café résumé €100 中文 العربية"

        result = analyzer.analyze_session(prompt)

        # Should handle unicode properly
        mock_copy.assert_called_once_with(prompt)
        assert result is not None

    @patch("cyclisme_training_logs.ai_providers.clipboard.copy_to_clipboard")
    def test_newlines_and_tabs(self, mock_copy):
        """Test handling of newlines and tabs in prompt."""
        mock_copy.return_value = True

        analyzer = ClipboardAnalyzer()
        prompt = "Line1\nLine2\n\tIndented\n\n\tDouble indent"

        result = analyzer.analyze_session(prompt)

        # Should preserve formatting
        mock_copy.assert_called_once_with(prompt)
        assert result is not None
