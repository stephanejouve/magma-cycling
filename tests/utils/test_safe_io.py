"""Tests for magma_cycling.utils.safe_io."""

from pathlib import Path

import pytest

from magma_cycling.utils.safe_io import safe_read_text, safe_write_text


class TestSafeReadText:
    def test_reads_utf8_content(self, tmp_path: Path):
        path = tmp_path / "f.md"
        path.write_text("# Hello 🔍 World", encoding="utf-8")
        assert safe_read_text(path) == "# Hello 🔍 World"

    def test_replaces_invalid_bytes_instead_of_raising(self, tmp_path: Path):
        # Write raw bytes that are not valid UTF-8
        path = tmp_path / "broken.md"
        path.write_bytes(b"valid \xff\xfe partial")
        # Must not raise
        result = safe_read_text(path)
        assert "valid" in result
        assert "partial" in result

    def test_propagates_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            safe_read_text(tmp_path / "missing.md")


class TestSafeWriteText:
    def test_writes_utf8_content(self, tmp_path: Path):
        path = tmp_path / "f.md"
        safe_write_text(path, "# Header 📊 stats")
        assert path.read_bytes() == "# Header 📊 stats".encode("utf-8")

    def test_overwrites_existing_file(self, tmp_path: Path):
        path = tmp_path / "f.md"
        path.write_text("old", encoding="utf-8")
        safe_write_text(path, "new 🚴")
        assert safe_read_text(path) == "new 🚴"

    def test_emoji_roundtrips(self, tmp_path: Path):
        """Write then read with the safe helpers preserves emoji content."""
        path = tmp_path / "roundtrip.md"
        original = "Workout 🔍 analyzed ✅ — TSS 52 / 50 ⚠️"
        safe_write_text(path, original)
        assert safe_read_text(path) == original
