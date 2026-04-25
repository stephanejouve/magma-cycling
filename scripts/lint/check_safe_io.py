#!/usr/bin/env python3
"""AST-based linter that enforces explicit ``encoding=utf-8`` on text I/O.

Run as a pre-commit hook and in CI. Flags:

- ``Path.read_text(...)``  without ``encoding=`` kwarg
- ``Path.write_text(...)`` without ``encoding=`` kwarg
- ``open(path, mode)`` in text mode without ``encoding=`` kwarg
  (binary modes ``rb``, ``wb``, ``ab``, ``r+b``, etc. are exempted)

Why
---

Without an explicit ``encoding=``, Python falls back to
``locale.getpreferredencoding()`` which is ``cp1252`` on Windows. Any
file containing emoji or non-Latin-1 characters then raises
``UnicodeDecodeError`` on read or ``UnicodeEncodeError`` on write —
exactly the daily-sync crash class fixed by PR #289 (safe_io helpers).

This linter prevents regressions: a future dev who forgets to add
``encoding="utf-8"`` (or to call ``safe_read_text`` / ``safe_write_text``)
will be caught before merge.

Usage
-----

::

    python scripts/lint/check_safe_io.py [path ...]

Without arguments, lints ``magma_cycling/`` recursively. Exits 1 on any
violation, 0 otherwise.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# Files exempted from the lint (the helpers that intentionally call the
# raw API to provide a safe wrapper around it).
EXEMPT_PATHS: set[str] = {
    "magma_cycling/utils/safe_io.py",
}

TEXT_MODES_DEFAULT = {""}  # No mode arg → default is "r" (text)


def _is_text_mode(mode: str) -> bool:
    """Return True when an open() mode string opens a file in text mode."""
    if mode == "":
        return True
    return "b" not in mode


class _IOVisitor(ast.NodeVisitor):
    """Collect read_text / write_text / open() calls without encoding= kwarg."""

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.violations: list[tuple[int, str]] = []

    def _has_encoding_kwarg(self, node: ast.Call) -> bool:
        return any(kw.arg == "encoding" for kw in node.keywords)

    def visit_Call(self, node: ast.Call) -> None:
        # Detect Path.read_text() / Path.write_text() (attribute call).
        # We do NOT match generic `.open()` attribute calls because that
        # would catch unrelated APIs like `webbrowser.open()`,
        # `subprocess.Popen.open()`, etc. The bare `open()` builtin below
        # covers the most common file I/O cases; Path.open() is rare and
        # can be migrated case by case if needed.
        if isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if attr in {"read_text", "write_text"} and not self._has_encoding_kwarg(node):
                self.violations.append(
                    (
                        node.lineno,
                        f"{attr}() without explicit encoding= "
                        f"(use safe_io.safe_{attr.replace('text', 'text')} or pass encoding='utf-8')",
                    )
                )

        # Detect bare open(...) call
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "open"
            and not self._has_encoding_kwarg(node)
        ):
            mode = self._extract_open_mode(node)
            if _is_text_mode(mode):
                self.violations.append(
                    (
                        node.lineno,
                        "open() in text mode without explicit encoding= (pass encoding='utf-8')",
                    )
                )

        # Continue walking children
        self.generic_visit(node)

    @staticmethod
    def _extract_open_mode(node: ast.Call) -> str:
        """Return the mode string passed to open(), or '' if implicit."""
        # open(path, mode) — second positional arg
        if len(node.args) >= 2:
            arg = node.args[1]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return arg.value
            # Non-literal mode → assume text to be safe (force encoding= anyway)
            return ""
        # open(path, mode=...) — keyword
        for kw in node.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                return kw.value.value if isinstance(kw.value.value, str) else ""
        return ""  # default mode "r"


def _is_exempt(path: Path) -> bool:
    """Check whether a file should be skipped by the linter."""
    posix = path.as_posix()
    return any(posix.endswith(exempt) for exempt in EXEMPT_PATHS)


def lint_file(path: Path) -> list[tuple[int, str]]:
    """Return the list of violations found in ``path``."""
    if _is_exempt(path):
        return []
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        # Don't fail the lint on syntax errors — that's another tool's job.
        return []
    visitor = _IOVisitor(str(path))
    visitor.visit(tree)
    return visitor.violations


def lint_paths(paths: list[Path]) -> int:
    """Run the linter on the given paths. Return 1 on any violation, else 0."""
    files: list[Path] = []
    for arg in paths:
        if arg.is_dir():
            files.extend(arg.rglob("*.py"))
        elif arg.is_file() and arg.suffix == ".py":
            files.append(arg)

    total_violations = 0
    for path in sorted(set(files)):
        violations = lint_file(path)
        for line, msg in violations:
            print(f"{path}:{line}: {msg}")
            total_violations += 1

    if total_violations:
        print(
            f"\n{total_violations} violation(s) — see https://github.com/stephanejouve/magma-cycling/pull/289 for context."
        )
        return 1
    return 0


def main() -> int:
    """Entry point — lint paths from sys.argv (default ``magma_cycling/``)."""
    args = sys.argv[1:]
    if not args:
        # Default scope when invoked without args
        args = ["magma_cycling"]
    paths = [Path(a) for a in args]
    return lint_paths(paths)


if __name__ == "__main__":
    sys.exit(main())
