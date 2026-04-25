"""Cyclisme Training Logs - Training analysis and planning system."""

import sys as _sys

__version__ = "3.7.0"


# Force UTF-8 on stdout/stderr so emoji characters used throughout the
# codebase (🔍, ✅, ⚠️, 📊, 🚦, etc.) do not raise UnicodeEncodeError on
# Windows where the console default codepage is cp1252. Applied at package
# import time so every entrypoint (mcp-server, daily-sync, withings-presync,
# end-of-week, etc.) is covered without per-script bootstrap. errors="replace"
# guarantees no crash if a char is still non-encodable downstream.
# Reported by Georges Crespi 2026-04-20 (BT-012, daily-sync 'charmap' codec
# error on \U0001f50d).
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            # Some test or wrapper environments expose objects without a
            # working .reconfigure() — silent fallback is acceptable since
            # the original behavior is preserved.
            pass
