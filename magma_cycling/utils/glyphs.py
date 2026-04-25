"""Cross-platform glyph constants with emoji / ASCII fallback.

Replaces hardcoded emoji literals scattered through CLI output. Detects
the host's ability to display emoji at import time and exposes a stable
set of named constants (``SEARCH``, ``OK``, ``WARN``, ...) that resolve
to the appropriate glyph.

Usage::

    from magma_cycling.utils.glyphs import SEARCH, OK, WARN

    print(f"{SEARCH} Évaluation conditions auto-servo...")
    print(f"{OK} Sync done")
    print(f"{WARN} TSS déficit detecté")

Detection rules:

- ``MAGMA_GLYPHS=emoji`` env var: force emoji rendering (testing override)
- ``MAGMA_GLYPHS=ascii`` env var: force ASCII fallback (CI / paranoid)
- otherwise: probe ``sys.stdout.encoding`` and only emit emoji when the
  encoding contains ``utf`` (covers UTF-8, utf8, utf-16). Windows console
  default ``cp1252`` falls back to ASCII automatically.

Why a dedicated module
----------------------

`magma_cycling/__init__.py` already forces UTF-8 on stdout/stderr to avoid
``UnicodeEncodeError`` (BT-012). That fix prevents crashes, but on consoles
without an emoji-capable font the glyphs render as ``?`` or empty boxes.
This module gives every caller a portable, stable name (``SEARCH``) and
delegates the rendering decision to a single place.
"""

from __future__ import annotations

import os
import sys


def _detect_emoji_support() -> bool:
    """Return True when the current stdout can render emoji glyphs.

    Pure function — does not consult any module-level state, so tests can
    monkey-patch ``os.environ`` and ``sys.stdout`` and call this directly.
    """
    forced = os.environ.get("MAGMA_GLYPHS", "").strip().lower()
    if forced == "emoji":
        return True
    if forced == "ascii":
        return False

    encoding = (getattr(sys.stdout, "encoding", "") or "").lower()
    return "utf" in encoding


# (Internal mapping — single source of truth for glyph definitions.)
_GLYPH_TABLE: dict[str, tuple[str, str]] = {
    # name        (emoji,    ascii fallback)
    "SEARCH": ("🔍", "[*]"),
    "OK": ("✅", "[ok]"),
    "WARN": ("⚠️", "[!]"),
    "ERROR": ("❌", "[x]"),
    "INFO": ("ℹ️", "[i]"),
    "ANALYZE": ("📊", "[stats]"),
    "ROCKET": ("🚀", "[go]"),
    "STOP": ("🚦", "[stop]"),
    "WRENCH": ("🔧", "[fix]"),
    "REFRESH": ("🔄", "[sync]"),
    "BIKE": ("🚴", "[bike]"),
    "TRASH": ("🗑️", "[del]"),
}


def use(name: str) -> str:
    """Return the glyph for ``name`` based on current detection.

    Useful when a caller wants to bypass the cached module-level constants
    (e.g., a test that toggles ``MAGMA_GLYPHS`` at runtime). Production
    code should prefer the imported constants for ergonomy::

        from magma_cycling.utils.glyphs import SEARCH

    rather than::

        from magma_cycling.utils.glyphs import use
        print(use("SEARCH"))
    """
    if name not in _GLYPH_TABLE:
        raise KeyError(f"Unknown glyph: {name!r}. Available: {sorted(_GLYPH_TABLE)}")
    emoji, ascii_fallback = _GLYPH_TABLE[name]
    return emoji if _detect_emoji_support() else ascii_fallback


def _publish_module_constants() -> None:
    """Inject named constants into the module namespace at import time."""
    emoji_mode = _detect_emoji_support()
    g = globals()
    for name, (emoji, ascii_fallback) in _GLYPH_TABLE.items():
        g[name] = emoji if emoji_mode else ascii_fallback


_publish_module_constants()


__all__ = ["use", *list(_GLYPH_TABLE.keys())]
