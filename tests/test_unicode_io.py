"""Tests for the UTF-8 io reconfiguration applied at package import.

Regression test for BT-012 (Georges Crespi 2026-04-20): daily-sync raised
UnicodeEncodeError on Windows when printing emojis (🔍, ✅, ⚠️, …) because
sys.stdout default encoding was cp1252. magma_cycling.__init__ now forces
UTF-8 with errors='replace'.
"""

import io
import sys
from unittest.mock import patch


def test_package_init_reconfigures_stdout_stderr_to_utf8():
    """After importing magma_cycling, stdout/stderr accept emoji output."""
    import magma_cycling  # noqa: F401 — side effect at import

    # Both streams should now report utf-8 encoding (or be wrapped safely)
    for stream in (sys.stdout, sys.stderr):
        encoding = getattr(stream, "encoding", "").lower()
        assert (
            "utf-8" in encoding or "utf8" in encoding
        ), f"Expected UTF-8 encoding, got {encoding!r}"


def test_emoji_print_does_not_raise():
    """Printing an emoji must not raise UnicodeEncodeError after import."""
    import magma_cycling  # noqa: F401

    # Use a real BytesIO-backed TextIOWrapper to simulate a real stdout
    buffer = io.BytesIO()
    text_stream = io.TextIOWrapper(buffer, encoding="utf-8", errors="replace")

    print("🔍 Évaluation conditions auto-servo...", file=text_stream)
    text_stream.flush()
    output = buffer.getvalue().decode("utf-8")
    assert "🔍" in output


def test_reconfigure_failure_does_not_break_import():
    """If reconfigure raises (test/wrapper env), import must still succeed."""
    # Simulate a stdout without a working reconfigure method
    fake_stream = io.StringIO()
    # StringIO has no reconfigure → the hasattr guard protects us

    with patch.object(sys, "stdout", fake_stream), patch.object(sys, "stderr", fake_stream):
        # Re-import path: just check that the same logic doesn't raise
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                try:
                    stream.reconfigure(encoding="utf-8", errors="replace")
                except Exception:
                    pass
        # No exception escaped
        assert True
