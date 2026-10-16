"""Tests for packaging/magma-cycling.spec — PyInstaller hidden imports."""

import ast
import importlib.util
from pathlib import Path

SPEC_PATH = Path(__file__).resolve().parent.parent / "packaging" / "magma-cycling.spec"


def _hidden_imports(source: str) -> list[str]:
    """Return the string literals passed as ``hiddenimports=`` in a spec."""
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.keyword) and node.arg == "hiddenimports":
            return [elt.value for elt in node.value.elts]
    return []


def _unresolvable(names: list[str]) -> list[str]:
    """Return the module names that importlib cannot locate."""
    missing = []
    for name in names:
        try:
            found = importlib.util.find_spec(name) is not None
        except ModuleNotFoundError:
            found = False
        if not found:
            missing.append(name)
    return missing


def test_spec_hidden_imports_parsed():
    """The parser finds the hiddenimports list (guards against a silent empty list)."""
    names = _hidden_imports(SPEC_PATH.read_text())
    assert "magma_cycling.cli" in names
    assert len(names) > 10


def test_spec_hidden_imports_all_resolve():
    """Every hidden import must exist, otherwise PyInstaller only logs an ERROR."""
    names = _hidden_imports(SPEC_PATH.read_text())
    assert _unresolvable(names) == []


def test_unresolvable_flags_pre_fix_names():
    """Counter-example: the names shipped in the spec until this fix are caught."""
    pre_fix = [
        "magma_cycling.ai.providers.anthropic_provider",
        "magma_cycling.ai.providers.mistral_provider",
        "magma_cycling.ai.providers.openai_provider",
        "magma_cycling.ai.providers.ollama_provider",
    ]
    assert _unresolvable(pre_fix) == pre_fix
    assert _unresolvable(["magma_cycling.ai_providers.claude_api"]) == []
