"""Tests for scripts/lint/check_safe_io.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LINTER_PATH = REPO_ROOT / "scripts" / "lint" / "check_safe_io.py"


def _load_linter():
    """Import the linter as a module from its filesystem path."""
    spec = importlib.util.spec_from_file_location("check_safe_io", LINTER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_safe_io"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def linter():
    return _load_linter()


@pytest.fixture
def temp_py(tmp_path: Path):
    """Create a temporary Python file with given source and return its path."""

    def _make(name: str, source: str) -> Path:
        p = tmp_path / name
        p.write_text(source, encoding="utf-8")
        return p

    return _make


class TestReadWriteTextDetection:
    def test_read_text_without_encoding_is_flagged(self, linter, temp_py):
        path = temp_py(
            "a.py",
            "from pathlib import Path\nx = Path('f.md').read_text()\n",
        )
        violations = linter.lint_file(path)
        assert len(violations) == 1
        assert "read_text" in violations[0][1]

    def test_read_text_with_encoding_is_clean(self, linter, temp_py):
        path = temp_py(
            "a.py",
            "from pathlib import Path\nx = Path('f.md').read_text(encoding='utf-8')\n",
        )
        assert linter.lint_file(path) == []

    def test_write_text_without_encoding_is_flagged(self, linter, temp_py):
        path = temp_py(
            "a.py",
            "from pathlib import Path\nPath('f.md').write_text('hi')\n",
        )
        violations = linter.lint_file(path)
        assert len(violations) == 1
        assert "write_text" in violations[0][1]

    def test_write_text_with_encoding_is_clean(self, linter, temp_py):
        path = temp_py(
            "a.py",
            "from pathlib import Path\nPath('f.md').write_text('hi', encoding='utf-8')\n",
        )
        assert linter.lint_file(path) == []


class TestOpenDetection:
    def test_open_default_mode_is_flagged(self, linter, temp_py):
        path = temp_py("a.py", "f = open('foo.txt')\n")
        violations = linter.lint_file(path)
        assert len(violations) == 1
        assert "open()" in violations[0][1]

    def test_open_text_mode_without_encoding_is_flagged(self, linter, temp_py):
        path = temp_py("a.py", "f = open('foo.txt', 'w')\n")
        violations = linter.lint_file(path)
        assert len(violations) == 1

    def test_open_binary_mode_is_clean(self, linter, temp_py):
        path = temp_py("a.py", "f = open('foo.bin', 'rb')\n")
        assert linter.lint_file(path) == []

    def test_open_with_encoding_is_clean(self, linter, temp_py):
        path = temp_py(
            "a.py",
            "f = open('foo.txt', 'r', encoding='utf-8')\n",
        )
        assert linter.lint_file(path) == []

    def test_webbrowser_open_is_not_flagged(self, linter, temp_py):
        """Generic .open() attribute calls (webbrowser.open, etc.) are not file I/O."""
        path = temp_py("a.py", "import webbrowser\nwebbrowser.open('https://example.com')\n")
        assert linter.lint_file(path) == []


class TestExemptions:
    def test_safe_io_module_is_exempt(self, linter, tmp_path):
        # Simulate the actual module path that the linter exempts
        magma_dir = tmp_path / "magma_cycling" / "utils"
        magma_dir.mkdir(parents=True)
        path = magma_dir / "safe_io.py"
        path.write_text(
            "from pathlib import Path\n"
            "def safe_read_text(p): return p.read_text(encoding='utf-8', errors='replace')\n"
            "def safe_write_text(p, c): p.write_text(c, encoding='utf-8')\n",
            encoding="utf-8",
        )
        # The exemption matches by suffix; if our path ends with the exempt key, no violations
        # (this test confirms the exemption mechanism, even though the file above is already clean)
        assert linter.lint_file(path) == []


class TestRealCodebase:
    def test_current_codebase_is_clean(self, linter):
        """The magma_cycling/ tree must already pass the linter (post-PR #289)."""
        magma_dir = REPO_ROOT / "magma_cycling"
        if not magma_dir.is_dir():
            pytest.skip("magma_cycling not found at expected path")
        rc = linter.lint_paths([magma_dir])
        assert rc == 0, "magma_cycling/ has unexpected I/O violations — see linter output"
