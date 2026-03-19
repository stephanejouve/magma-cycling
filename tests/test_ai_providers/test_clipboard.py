#!/usr/bin/env python3
"""
Tests for Clipboard AI Provider.

Tests ClipboardAnalyzer for manual copy/paste workflow with realistic mocks.
"""
import subprocess
from unittest.mock import MagicMock, patch

from magma_cycling.ai_providers.base import AIProvider
from magma_cycling.ai_providers.clipboard import (
    ClipboardAnalyzer,
    _copy_to_clipboard_native,
    _copy_to_clipboard_pyperclip,
    copy_to_clipboard,
)


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

    @patch("magma_cycling.ai_providers.clipboard.copy_to_clipboard")
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

    @patch("magma_cycling.ai_providers.clipboard.copy_to_clipboard")
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

    @patch("magma_cycling.ai_providers.clipboard.copy_to_clipboard")
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

    @patch("magma_cycling.ai_providers.clipboard.copy_to_clipboard")
    def test_validate_config_always_returns_true(self, mock_copy):
        """Test that validate_config always returns True (no config needed)."""
        mock_copy.return_value = True  # Mock clipboard availability

        analyzer = ClipboardAnalyzer()

        is_valid = analyzer.validate_config()

        assert is_valid is True

    @patch("magma_cycling.ai_providers.clipboard.copy_to_clipboard")
    def test_clipboard_analyzer_is_always_available(self, mock_copy):
        """Test that clipboard analyzer doesn't require any configuration."""
        mock_copy.return_value = True  # Mock clipboard availability

        # Should not raise any errors
        analyzer = ClipboardAnalyzer()

        assert analyzer.validate_config() is True

    @patch("magma_cycling.ai_providers.clipboard.copy_to_clipboard")
    def test_analyze_session_empty_prompt(self, mock_copy):
        """Test that analyze_session handles empty prompt."""
        mock_copy.return_value = True

        analyzer = ClipboardAnalyzer()
        prompt = ""

        result = analyzer.analyze_session(prompt)

        # Should still work with empty prompt
        mock_copy.assert_called_once_with("")
        assert result is not None

    @patch("magma_cycling.ai_providers.clipboard.copy_to_clipboard")
    def test_analyze_session_large_prompt(self, mock_copy):
        """Test that analyze_session handles large prompts."""
        mock_copy.return_value = True

        analyzer = ClipboardAnalyzer()
        prompt = "X" * 50000  # 50KB prompt

        result = analyzer.analyze_session(prompt)

        # Should handle large prompt
        mock_copy.assert_called_once_with(prompt)
        assert result is not None

    @patch("magma_cycling.ai_providers.clipboard.copy_to_clipboard")
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

    @patch("magma_cycling.ai_providers.clipboard.copy_to_clipboard")
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

    @patch("magma_cycling.ai_providers.clipboard.copy_to_clipboard")
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

    @patch("magma_cycling.ai_providers.clipboard.copy_to_clipboard")
    def test_instructions_returned_on_success(self, mock_copy):
        """Test that instructions are returned when copy succeeds."""
        mock_copy.return_value = True

        analyzer = ClipboardAnalyzer()
        result = analyzer.analyze_session("Test prompt")

        # Should return non-empty instructions
        assert result is not None
        assert len(result) > 10  # Should be substantial instructions
        assert isinstance(result, str)

    @patch("magma_cycling.ai_providers.clipboard.copy_to_clipboard")
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

    @patch("magma_cycling.ai_providers.clipboard.copy_to_clipboard")
    def test_newlines_and_tabs(self, mock_copy):
        """Test handling of newlines and tabs in prompt."""
        mock_copy.return_value = True

        analyzer = ClipboardAnalyzer()
        prompt = "Line1\nLine2\n\tIndented\n\n\tDouble indent"

        result = analyzer.analyze_session(prompt)

        # Should preserve formatting
        mock_copy.assert_called_once_with(prompt)
        assert result is not None

    # === system_prompt Tests ===

    @patch("magma_cycling.ai_providers.clipboard.copy_to_clipboard")
    def test_no_system_prompt_copies_prompt_only(self, mock_copy):
        """Without system_prompt, only the user prompt is copied."""
        mock_copy.return_value = True

        analyzer = ClipboardAnalyzer()
        analyzer.analyze_session("User prompt only")

        mock_copy.assert_called_once_with("User prompt only")

    @patch("magma_cycling.ai_providers.clipboard.copy_to_clipboard")
    def test_system_prompt_concatenated_readable(self, mock_copy):
        """With system_prompt, both are concatenated and copied."""
        mock_copy.return_value = True

        analyzer = ClipboardAnalyzer()
        analyzer.analyze_session("User data", system_prompt="Coach role context")

        copied_text = mock_copy.call_args[0][0]
        assert "Coach role context" in copied_text
        assert "User data" in copied_text

    @patch("magma_cycling.ai_providers.clipboard.copy_to_clipboard")
    def test_clipboard_output_is_self_contained(self, mock_copy):
        """Copied text contains both system context and user data."""
        mock_copy.return_value = True

        system = "Tu es un coach cyclisme. Profil: FTP 223W."
        user = "TSS Cible: 300, TSS Realise: 250"

        analyzer = ClipboardAnalyzer()
        analyzer.analyze_session(user, system_prompt=system)

        copied_text = mock_copy.call_args[0][0]
        assert "coach cyclisme" in copied_text
        assert "FTP 223W" in copied_text
        assert "TSS Cible" in copied_text

    @patch("magma_cycling.ai_providers.clipboard.copy_to_clipboard")
    def test_clipboard_output_no_api_keys(self, mock_copy):
        """Clipboard output must not contain API key patterns."""
        mock_copy.return_value = True

        analyzer = ClipboardAnalyzer()
        analyzer.analyze_session("Data", system_prompt="Coach context")

        copied_text = mock_copy.call_args[0][0]
        assert "sk-" not in copied_text
        assert "api_key" not in copied_text
        assert "Bearer" not in copied_text


# =====================================================================
# Internal functions — _copy_to_clipboard_native / pyperclip / orchestration
# =====================================================================


class TestCopyToClipboardNativeDarwin:
    """Tests for _copy_to_clipboard_native on macOS (Darwin)."""

    @patch("magma_cycling.ai_providers.clipboard.platform.system", return_value="Darwin")
    @patch("magma_cycling.ai_providers.clipboard.subprocess.Popen")
    def test_darwin_pbcopy_success(self, mock_popen, _mock_sys):
        """pbcopy success returns True."""
        proc = MagicMock()
        proc.returncode = 0
        mock_popen.return_value = proc

        assert _copy_to_clipboard_native("hello") is True
        mock_popen.assert_called_once_with(["pbcopy"], stdin=subprocess.PIPE, close_fds=True)
        proc.communicate.assert_called_once_with(b"hello")

    @patch("magma_cycling.ai_providers.clipboard.platform.system", return_value="Darwin")
    @patch("magma_cycling.ai_providers.clipboard.subprocess.Popen")
    def test_darwin_pbcopy_failure(self, mock_popen, _mock_sys):
        """pbcopy returncode != 0 returns False."""
        proc = MagicMock()
        proc.returncode = 1
        mock_popen.return_value = proc

        assert _copy_to_clipboard_native("hello") is False


class TestCopyToClipboardNativeLinux:
    """Tests for _copy_to_clipboard_native on Linux."""

    @patch("magma_cycling.ai_providers.clipboard.platform.system", return_value="Linux")
    @patch("magma_cycling.ai_providers.clipboard.subprocess.Popen")
    def test_linux_xclip_success(self, mock_popen, _mock_sys):
        """xclip success returns True without trying xsel."""
        proc = MagicMock()
        proc.returncode = 0
        mock_popen.return_value = proc

        assert _copy_to_clipboard_native("data") is True
        # Only one call — xclip succeeded, xsel not attempted
        assert mock_popen.call_count == 1

    @patch("magma_cycling.ai_providers.clipboard.platform.system", return_value="Linux")
    @patch("magma_cycling.ai_providers.clipboard.subprocess.Popen")
    def test_linux_xclip_missing_xsel_fallback(self, mock_popen, _mock_sys):
        """xclip FileNotFoundError → falls back to xsel."""
        proc_xsel = MagicMock()
        proc_xsel.returncode = 0

        def side_effect(cmd, **kwargs):
            if cmd[0] == "xclip":
                raise FileNotFoundError("xclip not found")
            return proc_xsel

        mock_popen.side_effect = side_effect

        assert _copy_to_clipboard_native("data") is True
        assert mock_popen.call_count == 2

    @patch("magma_cycling.ai_providers.clipboard.platform.system", return_value="Linux")
    @patch("magma_cycling.ai_providers.clipboard.subprocess.Popen")
    def test_linux_both_missing(self, mock_popen, _mock_sys):
        """Neither xclip nor xsel → returns False."""
        mock_popen.side_effect = FileNotFoundError("not found")

        assert _copy_to_clipboard_native("data") is False


class TestCopyToClipboardNativeWindows:
    """Tests for _copy_to_clipboard_native on Windows."""

    @patch("magma_cycling.ai_providers.clipboard.platform.system", return_value="Windows")
    @patch("magma_cycling.ai_providers.clipboard.subprocess.Popen")
    def test_windows_clip_success(self, mock_popen, _mock_sys):
        """clip success with utf-16 encoding."""
        proc = MagicMock()
        proc.returncode = 0
        mock_popen.return_value = proc

        assert _copy_to_clipboard_native("data") is True
        proc.communicate.assert_called_once_with("data".encode("utf-16"))


class TestCopyToClipboardNativeEdgeCases:
    """Edge cases for _copy_to_clipboard_native."""

    @patch("magma_cycling.ai_providers.clipboard.platform.system", return_value="FreeBSD")
    def test_unknown_os_returns_false(self, _mock_sys):
        """Unknown OS falls through to return False."""
        assert _copy_to_clipboard_native("data") is False

    @patch("magma_cycling.ai_providers.clipboard.platform.system", return_value="Darwin")
    @patch("magma_cycling.ai_providers.clipboard.subprocess.Popen", side_effect=OSError("boom"))
    def test_exception_returns_false(self, _mock_popen, _mock_sys):
        """Exception in subprocess returns False."""
        assert _copy_to_clipboard_native("data") is False


class TestCopyToClipboardPyperclip:
    """Tests for _copy_to_clipboard_pyperclip."""

    def test_pyperclip_success(self):
        """pyperclip.copy() works → returns True."""
        mock_pyperclip = MagicMock()
        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            assert _copy_to_clipboard_pyperclip("hello") is True
            mock_pyperclip.copy.assert_called_once_with("hello")

    def test_pyperclip_import_fails(self):
        """pyperclip not installed → returns False."""
        with patch.dict("sys.modules", {"pyperclip": None}):
            assert _copy_to_clipboard_pyperclip("hello") is False


class TestCopyToClipboardOrchestration:
    """Tests for copy_to_clipboard orchestration."""

    @patch("magma_cycling.ai_providers.clipboard._copy_to_clipboard_native", return_value=True)
    @patch("magma_cycling.ai_providers.clipboard._copy_to_clipboard_pyperclip")
    def test_native_success_skips_pyperclip(self, mock_pyp, mock_native):
        """Native success → pyperclip not called."""
        assert copy_to_clipboard("data") is True
        mock_native.assert_called_once_with("data")
        mock_pyp.assert_not_called()

    @patch("magma_cycling.ai_providers.clipboard._copy_to_clipboard_native", return_value=False)
    @patch(
        "magma_cycling.ai_providers.clipboard._copy_to_clipboard_pyperclip",
        return_value=True,
    )
    def test_native_fails_pyperclip_fallback(self, mock_pyp, mock_native):
        """Native fails → falls back to pyperclip."""
        assert copy_to_clipboard("data") is True
        mock_native.assert_called_once_with("data")
        mock_pyp.assert_called_once_with("data")

    @patch("magma_cycling.ai_providers.clipboard._copy_to_clipboard_native", return_value=False)
    @patch(
        "magma_cycling.ai_providers.clipboard._copy_to_clipboard_pyperclip",
        return_value=False,
    )
    def test_all_methods_fail(self, mock_pyp, mock_native):
        """Both methods fail → returns False."""
        assert copy_to_clipboard("data") is False
