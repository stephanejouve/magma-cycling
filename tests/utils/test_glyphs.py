"""Tests for magma_cycling.utils.glyphs."""

import io
import sys
from unittest.mock import patch

from magma_cycling.utils import glyphs


class TestDetectEmojiSupport:
    """Pure-function tests for the detection logic."""

    def test_force_emoji_via_env(self, monkeypatch):
        monkeypatch.setenv("MAGMA_GLYPHS", "emoji")
        assert glyphs._detect_emoji_support() is True

    def test_force_ascii_via_env(self, monkeypatch):
        monkeypatch.setenv("MAGMA_GLYPHS", "ascii")
        assert glyphs._detect_emoji_support() is False

    def test_force_env_is_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("MAGMA_GLYPHS", "ASCII")
        assert glyphs._detect_emoji_support() is False
        monkeypatch.setenv("MAGMA_GLYPHS", "EMOJI")
        assert glyphs._detect_emoji_support() is True

    def test_utf8_stdout_enables_emoji(self, monkeypatch):
        monkeypatch.delenv("MAGMA_GLYPHS", raising=False)
        utf8_stream = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
        with patch.object(sys, "stdout", utf8_stream):
            assert glyphs._detect_emoji_support() is True

    def test_cp1252_stdout_falls_back_to_ascii(self, monkeypatch):
        monkeypatch.delenv("MAGMA_GLYPHS", raising=False)
        cp_stream = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        with patch.object(sys, "stdout", cp_stream):
            assert glyphs._detect_emoji_support() is False


class TestUse:
    """Tests for the public use(name) helper."""

    def test_returns_emoji_when_supported(self, monkeypatch):
        monkeypatch.setenv("MAGMA_GLYPHS", "emoji")
        assert glyphs.use("SEARCH") == "🔍"
        assert glyphs.use("OK") == "✅"

    def test_returns_ascii_when_not_supported(self, monkeypatch):
        monkeypatch.setenv("MAGMA_GLYPHS", "ascii")
        assert glyphs.use("SEARCH") == "[*]"
        assert glyphs.use("OK") == "[ok]"

    def test_unknown_glyph_raises(self):
        try:
            glyphs.use("UNKNOWN")
        except KeyError as exc:
            assert "UNKNOWN" in str(exc)
        else:
            raise AssertionError("Expected KeyError")


class TestModuleConstants:
    """Module-level constants must mirror the table at import time."""

    def test_constants_are_strings(self):
        for name in ("SEARCH", "OK", "WARN", "ERROR", "INFO", "ANALYZE"):
            assert isinstance(getattr(glyphs, name), str)
            assert getattr(glyphs, name) != ""

    def test_all_table_entries_are_exported(self):
        for name in glyphs._GLYPH_TABLE:
            assert hasattr(glyphs, name), f"Missing module constant: {name}"
        # __all__ should contain every named constant
        for name in glyphs._GLYPH_TABLE:
            assert name in glyphs.__all__
