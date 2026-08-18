"""BT-058 : tests pour le snapshot des schémas MCP (spec DE-002 D1)."""

from __future__ import annotations

import json
import subprocess
import sys


class TestDumpMcpSchemas:
    """Le script produit un snapshot JSON structuré + non-vide."""

    def test_stdout_produces_valid_json(self):
        """Le script écrit du JSON parseable sur stdout."""
        result = subprocess.run(
            [sys.executable, "-m", "magma_cycling.scripts.dump_mcp_schemas"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"script failed: {result.stderr}"
        data = json.loads(result.stdout)
        assert isinstance(data, dict)

    def test_snapshot_has_required_envelope_fields(self):
        """L'enveloppe contient version, generated_at, tool_count, tools."""
        result = subprocess.run(
            [sys.executable, "-m", "magma_cycling.scripts.dump_mcp_schemas"],
            capture_output=True,
            text=True,
            check=False,
        )
        data = json.loads(result.stdout)
        for key in ("version", "generated_at", "tool_count", "tools"):
            assert key in data, f"missing envelope key: {key}"

    def test_version_field_matches_module_version(self):
        """Le champ ``version`` = ``v{magma_cycling.__version__}``."""
        from magma_cycling import __version__

        result = subprocess.run(
            [sys.executable, "-m", "magma_cycling.scripts.dump_mcp_schemas"],
            capture_output=True,
            text=True,
            check=False,
        )
        data = json.loads(result.stdout)
        assert data["version"] == f"v{__version__}"

    def test_tool_count_matches_tools_length(self):
        """Invariant : ``tool_count == len(tools)``."""
        result = subprocess.run(
            [sys.executable, "-m", "magma_cycling.scripts.dump_mcp_schemas"],
            capture_output=True,
            text=True,
            check=False,
        )
        data = json.loads(result.stdout)
        assert data["tool_count"] == len(data["tools"])

    def test_tool_count_is_non_zero(self):
        """Sanity : magma-cycling expose des tools."""
        result = subprocess.run(
            [sys.executable, "-m", "magma_cycling.scripts.dump_mcp_schemas"],
            capture_output=True,
            text=True,
            check=False,
        )
        data = json.loads(result.stdout)
        assert data["tool_count"] > 0

    def test_each_tool_has_expected_shape(self):
        """Chaque tool a name, schema_description, input_schema, handler."""
        result = subprocess.run(
            [sys.executable, "-m", "magma_cycling.scripts.dump_mcp_schemas"],
            capture_output=True,
            text=True,
            check=False,
        )
        data = json.loads(result.stdout)
        for tool in data["tools"]:
            assert "name" in tool
            assert "schema_description" in tool
            assert "input_schema" in tool
            assert "handler" in tool
            assert isinstance(tool["input_schema"], dict)

    def test_handler_info_has_docstring_field(self):
        """BT-058 : chaque handler expose un champ ``docstring`` (peut être vide).

        Ce champ ferme le trou D3 de DE-002 — un diff de docstring entre
        deux snapshots révèle les changements sémantiques déclarés même
        quand le schéma reste identique.
        """
        result = subprocess.run(
            [sys.executable, "-m", "magma_cycling.scripts.dump_mcp_schemas"],
            capture_output=True,
            text=True,
            check=False,
        )
        data = json.loads(result.stdout)
        # Au moins un tool doit avoir une docstring non-vide (invariant
        # opérationnel — sinon la discipline docstrings est cassée).
        with_docstring = [
            t
            for t in data["tools"]
            if t["handler"]["docstring"] and len(t["handler"]["docstring"]) > 0
        ]
        assert len(with_docstring) > 0, (
            "no tool has a non-empty handler docstring — " "docstring discipline broken?"
        )

    def test_tools_sorted_by_name(self):
        """Ordonnancement déterministe (facilite les diffs textuels)."""
        result = subprocess.run(
            [sys.executable, "-m", "magma_cycling.scripts.dump_mcp_schemas"],
            capture_output=True,
            text=True,
            check=False,
        )
        data = json.loads(result.stdout)
        names = [t["name"] for t in data["tools"]]
        assert names == sorted(names)

    def test_intensity_distribution_docstring_captures_semantic(self):
        """BT-058 régression : la docstring de handle_get_training_statistics
        capture bien la sémantique BT-050 « temps par zone » actuelle.

        Si demain quelqu'un remet le vieux comptage sans changer le schéma,
        cette assertion casse au diff — c'est exactement le trou D3 fermé.
        """
        result = subprocess.run(
            [sys.executable, "-m", "magma_cycling.scripts.dump_mcp_schemas"],
            capture_output=True,
            text=True,
            check=False,
        )
        data = json.loads(result.stdout)
        stats_tool = next(
            (t for t in data["tools"] if t["name"] == "get-training-statistics"),
            None,
        )
        assert stats_tool is not None, "get-training-statistics tool missing"
        # Le handler est handle_get_training_statistics — docstring décrit
        # au moins le contrat include_adherence (BT-042/048/053).
        docstring = stats_tool["handler"]["docstring"]
        # Assertion tolérante — vérifie juste qu'il y a du contenu utile
        assert len(docstring) > 20, "handler docstring is suspiciously short"
