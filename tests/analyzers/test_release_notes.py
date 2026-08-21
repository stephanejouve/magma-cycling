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
        assert result.reason == "ok"
        assert "3.74.0" in result.entries
        assert "3.73.0" in result.entries
        # 3.72.0 exclue (from_version exclusive)
        assert "3.72.0" not in result.entries
        assert result.total_sections == 3

    def test_unreleased_included_when_content(self, tmp_path):
        content = """# Changelog

## [Unreleased]

- BT-060 en cours

## [3.74.0]

- Some entry
"""
        p = self._write(tmp_path, content)
        result = _extract_changelog_between("v3.73.0", "v3.74.0", p)
        assert result.reason == "ok"
        assert "Unreleased" in result.entries
        assert "3.74.0" in result.entries

    def test_empty_sections_skipped(self, tmp_path):
        content = """## [3.74.0]

## [3.73.0]

- Real entry
"""
        p = self._write(tmp_path, content)
        result = _extract_changelog_between("v3.72.0", "v3.74.0", p)
        assert result.reason == "ok"
        assert "3.73.0" in result.entries
        # 3.74.0 section vide → skipped
        assert "3.74.0" not in result.entries

    def test_missing_file_returns_source_unreadable(self, tmp_path):
        """BT-060 L2 : fichier absent → source_unreadable (pas silence vide)."""
        p = tmp_path / "nonexistent.md"
        result = _extract_changelog_between("v3.72.0", "v3.74.0", p)
        assert result.entries == {}
        assert result.reason == "source_unreadable"
        assert "nonexistent.md" in result.detail

    def test_parser_no_match_when_out_of_range(self, tmp_path):
        """BT-060 L2 : sections présentes mais aucune dans la plage → parser_no_match."""
        content = """## [3.10.0]

- Only old entry
"""
        p = self._write(tmp_path, content)
        result = _extract_changelog_between("v3.72.0", "v3.74.0", p)
        assert result.entries == {}
        assert result.reason == "parser_no_match"
        assert result.total_sections == 1
        assert "1 sections présentes" in result.detail

    def test_no_entries_when_empty_file(self, tmp_path):
        """BT-060 L2 : fichier lu mais 0 section trouvée → no_entries."""
        content = "# Changelog\n\nCe fichier n'a pas encore de section versionnée.\n"
        p = self._write(tmp_path, content)
        result = _extract_changelog_between("v3.72.0", "v3.74.0", p)
        assert result.entries == {}
        assert result.reason == "no_entries"
        assert "0 section" in result.detail


class TestGitLogBetweenTags:
    """``_git_log_between_tags`` avec mock subprocess.

    BT-060 L1 : regex `\\bBT-\\d+\\b` case-insensitive matche les 3 formes
    (BT-060 majuscule, bt-060 minuscule scope, Bt-060 mixed case).

    BT-060 L2 : 3 états d'absence typés (source_unreadable / no_entries /
    parser_no_match) avec chiffres portés dans detail.
    """

    def _mock_run(self, returncode=0, stdout="", stderr=""):
        return type("R", (), {"returncode": returncode, "stdout": stdout, "stderr": stderr})()

    @patch("magma_cycling.analyzers.release_notes.subprocess.run")
    def test_commits_parsed(self, mock_run, tmp_path):
        mock_run.return_value = self._mock_run(
            stdout="abc1234 fix(mcp): BT-050 something\ndef5678 feat: BT-058 snapshot"
        )
        result = _git_log_between_tags("v3.72.0", "v3.74.0", tmp_path)
        assert result.reason == "ok"
        assert len(result.commits) == 2
        assert result.commits[0]["sha"] == "abc1234"
        assert "BT-050" in result.commits[0]["subject"]
        assert result.total_seen == 2

    @patch("magma_cycling.analyzers.release_notes.subprocess.run")
    def test_bt_regex_case_insensitive_and_scope_parens(self, mock_run, tmp_path):
        """BT-060 L1 : matche bt-060 (scope minuscule), Bt-060 (mixed), BT-060 (majuscule)."""
        mock_run.return_value = self._mock_run(
            stdout=(
                "aaa1111 fix(bt-060): isolate blocks\n"
                "bbb2222 feat: Bt-042 something\n"
                "ccc3333 chore: BT-058 snapshot\n"
                "ddd4444 refactor: no bt id here\n"
            )
        )
        result = _git_log_between_tags("v3.75.0", "v3.76.0", tmp_path)
        assert result.reason == "ok"
        assert len(result.commits) == 3
        assert result.total_seen == 4  # 4 commits, 1 sans BT-XXX
        shas = [c["sha"] for c in result.commits]
        assert shas == ["aaa1111", "bbb2222", "ccc3333"]

    @patch("magma_cycling.analyzers.release_notes.subprocess.run")
    def test_git_error_returns_source_unreadable(self, mock_run, tmp_path):
        """BT-060 L2 : git log rc != 0 → source_unreadable (typique container prod)."""
        mock_run.return_value = self._mock_run(returncode=128, stderr="fatal: not a git repository")
        result = _git_log_between_tags("v3.72.0", "v3.74.0", tmp_path)
        assert result.commits == []
        assert result.reason == "source_unreadable"
        assert "rc=128" in result.detail
        assert "not a git repository" in result.detail

    @patch(
        "magma_cycling.analyzers.release_notes.subprocess.run",
        side_effect=FileNotFoundError("git binary missing"),
    )
    def test_git_missing_returns_source_unreadable(self, mock_run, tmp_path):
        """BT-060 L2 : git binary absent → source_unreadable."""
        result = _git_log_between_tags("v3.72.0", "v3.74.0", tmp_path)
        assert result.commits == []
        assert result.reason == "source_unreadable"
        assert "FileNotFoundError" in result.detail

    @patch("magma_cycling.analyzers.release_notes.subprocess.run")
    def test_no_entries_when_empty_range(self, mock_run, tmp_path):
        """BT-060 L2 : git log OK mais 0 commit dans plage → no_entries."""
        mock_run.return_value = self._mock_run(stdout="")
        result = _git_log_between_tags("v3.72.0", "v3.72.0", tmp_path)
        assert result.commits == []
        assert result.reason == "no_entries"
        assert result.total_seen == 0

    @patch("magma_cycling.analyzers.release_notes.subprocess.run")
    def test_parser_no_match_when_commits_no_bt(self, mock_run, tmp_path):
        """BT-060 L2 : commits présents mais aucun BT-annoté → parser_no_match."""
        mock_run.return_value = self._mock_run(
            stdout=(
                "aaa1111 chore: bump deps\n"
                "bbb2222 style: format\n"
                "ccc3333 test: add coverage\n"
            )
        )
        result = _git_log_between_tags("v3.72.0", "v3.74.0", tmp_path)
        assert result.commits == []
        assert result.reason == "parser_no_match"
        assert result.total_seen == 3
        assert "3 commits vus" in result.detail
        assert "0 avec pattern" in result.detail


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

    def test_changelog_missing_produces_absence_note_typed(self, tmp_path):
        """BT-060 L2 : CHANGELOG absent → absence_note type=changelog_missing
        sub_type=source_unreadable (au lieu de l'ancien 'changelog_empty' ambigu)."""
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
        cl_notes = [n for n in result["absence_notes"] if n["type"] == "changelog_missing"]
        assert len(cl_notes) == 1
        assert cl_notes[0]["sub_type"] == "source_unreadable"

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


class TestBlockIsolation:
    """P3 — un échec dans un bloc ne doit pas faire tomber l'appel entier.

    Coach AI 2026-08-21 : simule sys.exit percolant depuis une dépendance
    importée (motif réel : outillages.github_utils._get_token qui appelle
    sys.exit(1) sur erreur de config NC). Le catch (Exception, SystemExit)
    doit convertir en absence_notes.type='block_failed' + le bloc = None.
    """

    def test_derived_block_systemexit_isolated(self, tmp_path):
        """sys.exit dans _fetch_snapshot_from_github → derived=None, declared OK."""

        def _exiting_client(v, r):
            raise SystemExit(1)

        result = compose_release_notes(
            "v3.73.0",
            "v3.74.0",
            changelog_path=tmp_path / "no.md",
            repo_root=tmp_path,
            github_client=_exiting_client,
        )
        assert result["derived"] is None
        assert result["declared"] is not None  # bloc declared inchangé
        block_failed = [n for n in result["absence_notes"] if n["type"] == "block_failed"]
        assert any(n["block"] == "derived" for n in block_failed)
        # Le message expose le type d'exception pour audit
        derived_fail = next(n for n in block_failed if n["block"] == "derived")
        assert "SystemExit" in derived_fail["message"]

    def test_declared_block_exception_isolated(self, tmp_path):
        """Exception dans _extract_changelog_between → declared=None, derived OK."""

        def _no_snap(v, r):
            return None

        with patch(
            "magma_cycling.analyzers.release_notes._extract_changelog_between",
            side_effect=RuntimeError("git binary missing"),
        ):
            result = compose_release_notes(
                "v3.73.0",
                "v3.74.0",
                changelog_path=tmp_path / "no.md",
                repo_root=tmp_path,
                github_client=_no_snap,
            )
        assert result["declared"] is None
        assert result["derived"] is not None  # bloc derived inchangé (client no-op)
        block_failed = [n for n in result["absence_notes"] if n["type"] == "block_failed"]
        assert any(n["block"] == "declared" for n in block_failed)

    def test_both_blocks_fail_call_still_succeeds(self, tmp_path):
        """Défense P3 stricte : même si les 2 blocs échouent, l'appel réussit."""

        def _exiting_client(v, r):
            raise SystemExit(1)

        with patch(
            "magma_cycling.analyzers.release_notes._extract_changelog_between",
            side_effect=SystemExit(1),
        ):
            result = compose_release_notes(
                "v3.73.0",
                "v3.74.0",
                changelog_path=tmp_path / "no.md",
                repo_root=tmp_path,
                github_client=_exiting_client,
            )
        assert result["derived"] is None
        assert result["declared"] is None
        assert result["from_version"] == "v3.73.0"  # payload structure intacte
        assert result["to_version"] == "v3.74.0"
        block_failed_blocks = {
            n["block"] for n in result["absence_notes"] if n["type"] == "block_failed"
        }
        assert block_failed_blocks == {"derived", "declared"}


class TestObservabilityAbsenceNotesTyped:
    """BT-060 L2/L3 — chaque source expose son état d'absence de façon typée.

    Coach AI 2026-08-21 : « un outil d'observabilité qui se trompe sur
    l'origine d'une absence est pire qu'un outil muet ». absence_notes
    porte le type + sub_type (source_unreadable / no_entries / parser_no_match)
    + chiffres dans le message pour orienter le fix vers la bonne cause.
    """

    def _no_snap(self, v, r):
        return None

    def test_snapshot_missing_carries_sub_type(self, tmp_path):
        """derived : reason=release_not_found propagé en absence_note.sub_type."""
        result = compose_release_notes(
            "v3.73.0",
            "v3.74.0",
            changelog_path=tmp_path / "no.md",
            repo_root=tmp_path,
            github_client=self._no_snap,
        )
        snap_notes = [n for n in result["absence_notes"] if n["type"] == "snapshot_missing"]
        assert len(snap_notes) == 2  # from + to
        for note in snap_notes:
            assert note["sub_type"] == "release_not_found"
            assert "version" in note

    def test_derived_no_diff_signals_comparison_happened(self, tmp_path):
        """BT-060 L3 : quand comparaison OK sans changement, absence_note explicite."""
        snap = {"version": "v3.73.0", "tools": []}
        client = lambda v, r: snap  # noqa: E731 — same snap both versions
        result = compose_release_notes(
            "v3.73.0",
            "v3.74.0",
            changelog_path=tmp_path / "no.md",
            repo_root=tmp_path,
            github_client=client,
        )
        no_diff_notes = [n for n in result["absence_notes"] if n["type"] == "derived_no_diff"]
        assert len(no_diff_notes) == 1
        assert (
            "0 changement" in no_diff_notes[0]["message"]
            or "aucun changement" in no_diff_notes[0]["message"].lower()
        )

    def test_git_log_container_prod_pattern(self, tmp_path):
        """Cas réel prod BT-060 : repo git absent → source_unreadable."""
        result = compose_release_notes(
            "v3.76.1",
            "v3.76.3",
            changelog_path=tmp_path / "no.md",
            repo_root=tmp_path,  # tmp_path n'est pas un git repo
            github_client=self._no_snap,
        )
        git_notes = [n for n in result["absence_notes"] if n["type"] == "bt_commits_missing"]
        assert len(git_notes) == 1
        assert git_notes[0]["sub_type"] == "source_unreadable"
        # Le message porte le retour d'erreur pour orientation vers la vraie cause
        assert "rc=" in git_notes[0]["message"] or "git" in git_notes[0]["message"].lower()

    def test_changelog_present_but_out_of_range_parser_no_match(self, tmp_path):
        """CHANGELOG lu, sections présentes mais aucune dans la plage → parser_no_match."""
        cl = tmp_path / "CHANGELOG.md"
        cl.write_text(
            "# Changelog\n\n## [3.10.0]\n\n- Old only\n",
            encoding="utf-8",
        )
        result = compose_release_notes(
            "v3.73.0",
            "v3.74.0",
            changelog_path=cl,
            repo_root=tmp_path,
            github_client=self._no_snap,
        )
        cl_notes = [n for n in result["absence_notes"] if n["type"] == "changelog_missing"]
        assert len(cl_notes) == 1
        assert cl_notes[0]["sub_type"] == "parser_no_match"
        assert "sections présentes" in cl_notes[0]["message"]
