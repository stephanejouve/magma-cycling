"""Tests for ``magma_cycling.utils.hot_reload``.

Regression coverage for the ``__file__ = None`` crash observed in prod
(daily_sync.main() → mark_modules_loaded() → ``Path(None)`` TypeError
when a namespace package / built-in slipped into the magma_cycling.*
filter via ``hasattr(module, "__file__")`` returning True on a None value.
"""

from __future__ import annotations

import sys
import types

import pytest

from magma_cycling.utils import hot_reload


def _inject_module(
    monkeypatch: pytest.MonkeyPatch, name: str, file_attr: object
) -> types.ModuleType:
    """Inject a synthetic module into sys.modules with the given __file__."""
    mod = types.ModuleType(name)
    mod.__file__ = file_attr  # type: ignore[assignment]
    monkeypatch.setitem(sys.modules, name, mod)
    return mod


def test_mark_modules_loaded_skips_module_with_none_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: a magma_cycling.* module with __file__=None must not crash."""
    _inject_module(monkeypatch, "magma_cycling._test_synthetic_none", file_attr=None)

    # Must not raise TypeError("argument should be a str or an os.PathLike...")
    hot_reload.mark_modules_loaded(package_name="magma_cycling")


def test_hot_reload_if_needed_skips_module_with_none_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: same guard for hot_reload_if_needed()."""
    _inject_module(monkeypatch, "magma_cycling._test_synthetic_none2", file_attr=None)

    reloaded = hot_reload.hot_reload_if_needed(package_name="magma_cycling")
    assert isinstance(reloaded, list)


def test_mark_modules_loaded_sets_mtime_on_real_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """Happy path: a real magma_cycling module gets __mtime__ set."""
    # Use the hot_reload module itself — it's loaded with a real __file__.
    if hasattr(hot_reload, "__mtime__"):
        monkeypatch.delattr(hot_reload, "__mtime__", raising=False)

    hot_reload.mark_modules_loaded(package_name="magma_cycling")

    assert getattr(hot_reload, "__mtime__", 0) > 0


def test_hot_reload_if_needed_returns_empty_when_no_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path: no file changes → no reload, returns empty list."""
    # Force the module's stored mtime to "now" so the file check decides nothing changed.
    import time

    hot_reload.__mtime__ = time.time() + 3600  # type: ignore[attr-defined]

    reloaded = hot_reload.hot_reload_if_needed(package_name="magma_cycling")
    assert hot_reload.__name__ not in reloaded
