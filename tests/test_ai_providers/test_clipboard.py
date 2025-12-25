#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Clipboard AI Provider.

Tests ClipboardAnalyzer for manual copy/paste workflow.
"""

import pytest
from unittest.mock import patch, MagicMock
from cyclisme_training_logs.ai_providers.clipboard import ClipboardAnalyzer
from cyclisme_training_logs.ai_providers.base import AIProvider


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

    @patch('cyclisme_training_logs.ai_providers.clipboard.subprocess.run')
    def test_analyze_session_copies_to_clipboard(self, mock_run):
        """Test that analyze_session copies prompt to clipboard."""
        mock_run.return_value = MagicMock(returncode=0)

        analyzer = ClipboardAnalyzer()
        prompt = "Test cycling analysis prompt"

        result = analyzer.analyze_session(prompt)

        # Should call pbcopy
        mock_run.assert_called_once()
        call_args = mock_run.call_args

        # Check that pbcopy was called
        assert 'pbcopy' in str(call_args)

        # Check that prompt was passed via stdin
        assert call_args.kwargs.get('input') == prompt

        # Should return empty string (manual workflow)
        assert result == ""

    @patch('cyclisme_training_logs.ai_providers.clipboard.subprocess.run')
    def test_analyze_session_with_dataset(self, mock_run):
        """Test that analyze_session handles dataset parameter."""
        mock_run.return_value = MagicMock(returncode=0)

        analyzer = ClipboardAnalyzer()
        prompt = "Test prompt"
        dataset = {'activity_id': '12345', 'duration': 3600}

        result = analyzer.analyze_session(prompt, dataset=dataset)

        # Should still call pbcopy (dataset is optional)
        mock_run.assert_called_once()
        assert result == ""

    @patch('cyclisme_training_logs.ai_providers.clipboard.subprocess.run')
    def test_analyze_session_multiline_prompt(self, mock_run):
        """Test that analyze_session handles multiline prompts."""
        mock_run.return_value = MagicMock(returncode=0)

        analyzer = ClipboardAnalyzer()
        prompt = """Line 1
Line 2
Line 3"""

        result = analyzer.analyze_session(prompt)

        # Should call pbcopy with full multiline prompt
        call_args = mock_run.call_args
        assert call_args.kwargs.get('input') == prompt

    def test_get_provider_info_returns_dict(self):
        """Test that get_provider_info returns dict with expected keys."""
        analyzer = ClipboardAnalyzer()

        info = analyzer.get_provider_info()

        assert isinstance(info, dict)
        assert 'provider' in info
        assert 'status' in info
        assert 'cost_input' in info
        assert 'cost_output' in info

    def test_get_provider_info_has_correct_values(self):
        """Test that provider info has correct values."""
        analyzer = ClipboardAnalyzer()

        info = analyzer.get_provider_info()

        assert info['provider'] == 'clipboard'
        assert info['status'] == 'ready'
        assert info['requires_api_key'] is False
        assert '$0' in info['cost_input']
        assert '$0' in info['cost_output']

    def test_validate_config_always_returns_true(self):
        """Test that validate_config always returns True (no config needed)."""
        analyzer = ClipboardAnalyzer()

        is_valid = analyzer.validate_config()

        assert is_valid is True

    def test_clipboard_analyzer_is_always_available(self):
        """Test that clipboard analyzer doesn't require any configuration."""
        # Should not raise any errors
        analyzer = ClipboardAnalyzer()

        assert analyzer.validate_config() is True

    @patch('cyclisme_training_logs.ai_providers.clipboard.subprocess.run')
    def test_analyze_session_empty_prompt(self, mock_run):
        """Test that analyze_session handles empty prompt."""
        mock_run.return_value = MagicMock(returncode=0)

        analyzer = ClipboardAnalyzer()
        prompt = ""

        result = analyzer.analyze_session(prompt)

        # Should still call pbcopy even with empty prompt
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args.kwargs.get('input') == ""

    @patch('cyclisme_training_logs.ai_providers.clipboard.subprocess.run')
    def test_analyze_session_large_prompt(self, mock_run):
        """Test that analyze_session handles large prompts."""
        mock_run.return_value = MagicMock(returncode=0)

        analyzer = ClipboardAnalyzer()
        prompt = "X" * 10000  # 10KB prompt

        result = analyzer.analyze_session(prompt)

        # Should call pbcopy with full large prompt
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert len(call_args.kwargs.get('input')) == 10000

    @patch('cyclisme_training_logs.ai_providers.clipboard.subprocess.run')
    def test_analyze_session_special_characters(self, mock_run):
        """Test that analyze_session handles special characters."""
        mock_run.return_value = MagicMock(returncode=0)

        analyzer = ClipboardAnalyzer()
        prompt = "Test with émojis 🚴‍♂️ and spéciál çhars: €$£"

        result = analyzer.analyze_session(prompt)

        # Should call pbcopy with special characters preserved
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args.kwargs.get('input') == prompt

    def test_provider_info_indicates_manual_workflow(self):
        """Test that provider info clearly indicates manual workflow."""
        analyzer = ClipboardAnalyzer()

        info = analyzer.get_provider_info()

        # Should have some indication of manual workflow
        info_str = str(info).lower()
        assert 'manual' in info_str or 'clipboard' in info_str

    def test_provider_info_indicates_no_cost(self):
        """Test that provider info indicates no cost."""
        analyzer = ClipboardAnalyzer()

        info = analyzer.get_provider_info()

        # Both input and output should be free
        assert '$0' in info['cost_input'] or 'free' in info['cost_input'].lower()
        assert '$0' in info['cost_output'] or 'free' in info['cost_output'].lower()

    def test_multiple_analyzers_independent(self):
        """Test that multiple clipboard analyzers are independent."""
        analyzer1 = ClipboardAnalyzer()
        analyzer2 = ClipboardAnalyzer()

        assert analyzer1 is not analyzer2
        assert analyzer1.provider == analyzer2.provider == AIProvider.CLIPBOARD
