"""UTF-8-safe text file I/O helpers.

Wrap ``Path.read_text`` / ``Path.write_text`` to force UTF-8 encoding
explicitly. Without an explicit encoding, Python falls back to
``locale.getpreferredencoding()`` which is ``cp1252`` on Windows by
default — meaning any emoji or non-Latin-1 character in a magma-cycling
markdown file (``workouts-history.md`` for instance, often populated by
LLM output) will raise ``UnicodeDecodeError`` on read or
``UnicodeEncodeError`` on write.

These helpers eliminate that class of bug at I/O time, symmetrically to
``magma_cycling.utils.glyphs.safe_print`` which handles stdout output.

Usage::

    from magma_cycling.utils.safe_io import safe_read_text, safe_write_text

    content = safe_read_text(Path("workouts-history.md"))   # never crashes
    safe_write_text(Path("output.md"), content)              # always UTF-8
"""

from __future__ import annotations

from pathlib import Path


def safe_read_text(path: Path) -> str:
    """Read a text file as UTF-8 with replacement on decode error.

    The ``errors="replace"`` policy is intentional on the read side: we
    consume content that may have been produced by external tools or older
    versions of the codebase with a different encoding, and we prefer a
    ``?`` placeholder over a hard crash. Caller code that needs strict
    decoding should call ``Path.read_text(encoding="utf-8")`` directly.
    """
    return path.read_text(encoding="utf-8", errors="replace")


def safe_write_text(path: Path, content: str) -> None:
    """Write a text file as UTF-8 strict.

    Strict (no ``errors="replace"``) on the write side because a
    replacement here would silently corrupt user data. Python strings are
    Unicode internally, so any string can be encoded to UTF-8 — the strict
    policy will only ever raise if ``content`` contains lone surrogates,
    which would already be a bug upstream.
    """
    path.write_text(content, encoding="utf-8")


__all__ = ["safe_read_text", "safe_write_text"]
