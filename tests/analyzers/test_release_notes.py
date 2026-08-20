"""BT-060 : tests pour ``compose_release_notes`` (spec DE-002)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from magma_cycling.analyzers.release_notes import (
    _diff_docstrings,
    _diff_schemas,
    _extract_changelog_between,
    _git_log_between_tags,
    _normalize_version,
    _parse_semver,
    compose_release_notes,
)


class TestParseSemver:
    def test_valid_with_v_prefix(self):
        assert _parse_semver("v3.72.0") == (3, 72, 0)

    def test_valid_without_v_prefix(self):
        assert _parse_semver("3.72.0") == (3, 72, 0)

    def test_valid_large_numbers(self):
        assert _parse_semver("v10.999.42") == (10, 999, 42)

    def test_invalid_too_few_parts(self):
        with pytest.raises(ValueError, match="expected X.Y.Z"):
            _parse_semver("3.72")

    def test_invalid_non_numeric(self):
        with pytest.raises(ValueError, match="invalid semver"):
            _parse_semver("v3.72.beta")


class TestNormalizeVersion:
    def test_adds_v_prefix(self):
        assert _normalize_version("3.72.0") == "v3.72.0"

    def test_keeps_v_prefix(self):
        assert _normalize_version("v3.72.0") == "v3.72.0"

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _normalize_version("3.72")


class TestDiffSchemas:
    """``_diff_schemas`` détecte tools ajoutés/retirés + schema_changed."""

    def _snap(self, tools):
        return {"version": "vX.Y.Z", "tools": tools}

    def test_tools_added(self):
        from_snap = self._snap([{"name": "a", "input_schema": {}}])
        to_snap = self._snap(
            [
                {"name": "a", "input_schema": {}},
                {"name": "b", "input_schema": {}},
            ]
        )
        d = _diff_schemas(from_snap, to_snap)
        assert d["tools_added"] == [{"name": "b"}]
        assert d["tools_removed"] == []
        assert d["schema_changed"] == []

    def test_tools_removed(self):
        from_snap = self._snap(
            [
                {"name": "a", "input_schema": {}},
                {"name": "b", "input_schema": {}},
            ]
        )
        to_snap = self._snap([{"name": "a", "input_schema": {}}])
        d = _diff_schemas(from_snap, to_snap)
        assert d["tools_added"] == []
        assert d["tools_removed"] == [{"name": "b"}]

    def test_schema_changed(self):
        from_snap = self._snap(
            [{"name": "a", "input_schema": {"properties": {"x": {"type": "string"}}}}]
        )
        to_snap = self._snap(
            [
                {
                    "name": "a",
                    "input_schema": {
                        "properties": {"x": {"type": "string"}, "y": {"type": "integer"}}
                    },
                }
            ]
        )
        d = _diff_schemas(from_snap, to_snap)
        assert d["schema_changed"] == [{"name": "a"}]

    def test_no_change_returns_empty_lists(self):
        snap = self._snap([{"name": "a", "input_schema": {"foo": 1}}])
        d = _diff_schemas(snap, snap)
        assert d == {"tools_added": [], "tools_removed": [], "schema_changed": []}


class TestDiffDocstrings:
    """BT-060 : capture les changements sémantiques à schéma constant."""

    def test_docstring_diff_captured(self):
        """Cas exemplaire ``intensity_distribution`` v3.73→v3.74."""
        from_snap = {
            "tools": [
                {
                    "name": "get-training-statistics",
                    "handler": {
                        "docstring": "Get statistics. intensity_distribution = counting activities by global IF."
                    },
                }
            ]
        }
        to_snap = {
            "tools": [
                {
                    "name": "get-training-statistics",
                    "handler": {
                        "docstring": "Get statistics. intensity_distribution = time-per-zone via streams."
                    },
                }
            ]
        }
        diffs = _diff_docstrings(from_snap, to_snap)
        assert len(diffs) == 1
        assert diffs[0]["name"] == "get-training-statistics"
        assert "counting activities" in diffs[0]["from_docstring"]
        assert "time-per-zone" in diffs[0]["to_docstring"]

    def test_identical_docstring_not_in_diff(self):
        snap = {
            "tools": [
                {"name": "a", "handler": {"docstring": "same"}},
            ]
        }
        assert _diff_docstrings(snap, snap) == []

    def test_missing_handler_treated_as_empty_docstring(self):
        from_snap = {"tools": [{"name": "a"}]}  # pas de handler
        to_snap = {"tools": [{"name": "a", "handler": {"docstring": "new"}}]}
        diffs = _diff_docstrings(from_snap, to_snap)
        assert len(diffs) == 1
        assert diffs[0]["from_docstring"] == ""
        assert diffs[0]["to_docstring"] == "new"


class TestExtractChangelogBetween:
    """Parse ``## [X.Y.Z]`` sections entre 2 versions."""

    def _write(self, tmp_path: Path, content: str) -> Path:
        p = tmp_path / "CHANGELOG.md"
        p.write_text(content, encoding="utf-8")
        return p

    def test_extracts_versions_in_range(self, tmp_path):
        content = """# Changelog

## [3.74.0]

- feat: BT-050 intensity zones

## [3.73.0]

- fix: BT-048 adherence

## [3.72.0]

- Legacy
"""
        p = self._write(tmp_path, content)
        result = _extract_changelog_between("v3.72.0", "v3.74.0", p)
        assert "3.74.0" in result
        assert "3.73.0" in result
        # 3.72.0 exclue (from_version exclusive)
        assert "3.72.0" not in result

    def test_unreleased_included_when_content(self, tmp_path):
        content = """# Changelog

## [Unreleased]

- BT-060 en cours

## [3.74.0]

- Some entry
"""
        p = self._write(tmp_path, content)
        result = _extract_changelog_between("v3.73.0", "v3.74.0", p)
        assert "Unreleased" in result
        assert "3.74.0" in result

    def test_empty_sections_skipped(self, tmp_path):
        content = """## [3.74.0]

## [3.73.0]

- Real entry
"""
        p = self._write(tmp_path, content)
        result = _extract_changelog_between("v3.72.0", "v3.74.0", p)
        assert "3.73.0" in result
        # 3.74.0 section vide → skipped
        assert "3.74.0" not in result

    def test_missing_file_returns_empty(self, tmp_path):
        p = tmp_path / "nonexistent.md"
        assert _extract_changelog_between("v3.72.0", "v3.74.0", p) == {}


class TestGitLogBetweenTags:
    """``_git_log_between_tags`` avec mock subprocess."""

    @patch("magma_cycling.analyzers.release_notes.subprocess.run")
    def test_commits_parsed(self, mock_run, tmp_path):
        mock_run.return_value = type(
            "R",
            (),
            {
                "returncode": 0,
                "stdout": "abc1234 fix(mcp): BT-050 something\ndef5678 feat: BT-058 snapshot",
            },
        )()
        commits = _git_log_between_tags("v3.72.0", "v3.74.0", tmp_path)
        assert len(commits) == 2
        assert commits[0]["sha"] == "abc1234"
        assert "BT-050" in commits[0]["subject"]

    @patch("magma_cycling.analyzers.release_notes.subprocess.run")
    def test_git_error_returns_empty(self, mock_run, tmp_path):
        mock_run.return_value = type("R", (), {"returncode": 128, "stdout": ""})()
        assert _git_log_between_tags("v3.72.0", "v3.74.0", tmp_path) == []

    @patch(
        "magma_cycling.analyzers.release_notes.subprocess.run",
        side_effect=FileNotFoundError("git not found"),
    )
    def test_git_missing_returns_empty(self, mock_run, tmp_path):
        assert _git_log_between_tags("v3.72.0", "v3.74.0", tmp_path) == []


class TestComposeReleaseNotes:
    """Intégration : payload complet ``{derived, declared, absence_notes}``."""

    def _fake_github_client(self, snapshots: dict[str, dict]):
        """Retourne un client mock qui sert des snapshots depuis un dict."""

        def _client(version, repo):
            return snapshots.get(version)

        return _client

    def test_both_snapshots_present_derived_populated(self, tmp_path):
        snap_from = {
            "version": "v3.73.0",
            "tools": [{"name": "a", "input_schema": {}, "handler": {"docstring": "old"}}],
        }
        snap_to = {
            "version": "v3.74.0",
            "tools": [
                {"name": "a", "input_schema": {}, "handler": {"docstring": "new"}},
                {"name": "b", "input_schema": {}, "handler": {"docstring": "brand new"}},
            ],
        }
        client = self._fake_github_client({"v3.73.0": snap_from, "v3.74.0": snap_to})
        # CHANGELOG absent → declared vide + absence_notes changelog
        result = compose_release_notes(
            "v3.73.0",
            "v3.74.0",
            changelog_path=tmp_path / "no.md",
            repo_root=tmp_path,
            github_client=client,
        )
        assert result["from_version"] == "v3.73.0"
        assert result["to_version"] == "v3.74.0"
        assert result["derived"]["schema_changes"]["tools_added"] == [{"name": "b"}]
        assert len(result["derived"]["docstring_diffs"]) == 1
        assert result["derived"]["docstring_diffs"][0]["name"] == "a"

    def test_snapshot_missing_produces_absence_note(self, tmp_path):
        # Seul le snapshot to est présent
        client = self._fake_github_client({"v3.74.0": {"version": "v3.74.0", "tools": []}})
        result = compose_release_notes(
            "v3.73.0",
            "v3.74.0",
            changelog_path=tmp_path / "no.md",
            repo_root=tmp_path,
            github_client=client,
        )
        assert result["derived"]["schema_changes"] is None
        assert result["derived"]["docstring_diffs"] is None
        # absence_note pour from
        absence_types = [n["type"] for n in result["absence_notes"]]
        assert "snapshot_missing" in absence_types
        snapshot_missing = [n for n in result["absence_notes"] if n["type"] == "snapshot_missing"]
        assert snapshot_missing[0]["version"] == "v3.73.0"

    def test_changelog_empty_produces_absence_note(self, tmp_path):
        client = self._fake_github_client(
            {
                "v3.73.0": {"version": "v3.73.0", "tools": []},
                "v3.74.0": {"version": "v3.74.0", "tools": []},
            }
        )
        result = compose_release_notes(
            "v3.73.0",
            "v3.74.0",
            changelog_path=tmp_path / "no.md",
            repo_root=tmp_path,
            github_client=client,
        )
        assert result["declared"]["changelog_entries"] == {}
        assert any(n["type"] == "changelog_empty" for n in result["absence_notes"])

    def test_from_version_not_less_than_to_raises(self, tmp_path):
        with pytest.raises(ValueError, match="must be strictly less"):
            compose_release_notes(
                "v3.74.0",
                "v3.73.0",
                changelog_path=tmp_path / "no.md",
                repo_root=tmp_path,
                github_client=lambda v, r: None,
            )

    def test_equal_versions_raises(self, tmp_path):
        with pytest.raises(ValueError, match="must be strictly less"):
            compose_release_notes(
                "v3.74.0",
                "v3.74.0",
                changelog_path=tmp_path / "no.md",
                repo_root=tmp_path,
                github_client=lambda v, r: None,
            )

    def test_declared_derived_separated_in_payload(self, tmp_path):
        """Design décisif P2 DE-002 : derived et declared jamais mélangés."""
        client = self._fake_github_client(
            {
                "v3.73.0": {"version": "v3.73.0", "tools": []},
                "v3.74.0": {"version": "v3.74.0", "tools": []},
            }
        )
        result = compose_release_notes(
            "v3.73.0",
            "v3.74.0",
            changelog_path=tmp_path / "no.md",
            repo_root=tmp_path,
            github_client=client,
        )
        assert set(result.keys()) == {
            "from_version",
            "to_version",
            "derived",
            "declared",
            "absence_notes",
        }
        # Chaque bloc a sa structure typée
        assert set(result["derived"].keys()) == {"schema_changes", "docstring_diffs"}
        assert set(result["declared"].keys()) == {"changelog_entries", "bt_commits"}


class TestNormalizedVersionInPayload:
    """La version normalisée avec préfixe v est utilisée dans le payload."""

    def test_input_without_v_normalized(self, tmp_path):
        def _no_snap(v, r):
            return None

        result = compose_release_notes(
            "3.73.0",  # sans v
            "3.74.0",  # sans v
            changelog_path=tmp_path / "no.md",
            repo_root=tmp_path,
            github_client=_no_snap,
        )
        assert result["from_version"] == "v3.73.0"
        assert result["to_version"] == "v3.74.0"
