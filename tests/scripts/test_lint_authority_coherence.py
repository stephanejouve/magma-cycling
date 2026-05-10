"""Tests pour le linter authority-coherence (ADR v5 Phase 2)."""

from __future__ import annotations

from pathlib import Path

import yaml

from magma_cycling.config.data_repo import OPERATORS_FILE
from magma_cycling.scripts.lint_authority_coherence import (
    Violation,
    lint,
)


def _make_repo(tmp_path: Path, operators: dict | None) -> Path:
    """Crée un repo training-logs minimal avec optionnellement .operators.yaml."""
    repo = tmp_path / "training-logs"
    repo.mkdir()
    (repo / "workouts-history.md").touch()
    (repo / ".gitignore").write_text("*.pyc\n")
    if operators is not None:
        with (repo / OPERATORS_FILE).open("w", encoding="utf-8") as fh:
            yaml.safe_dump(operators, fh)
    return repo


class TestLintBasics:
    def test_root_missing_emits_violation(self, tmp_path):
        violations = lint(tmp_path / "nope")
        assert any(v.code == "ROOT_MISSING" for v in violations)

    def test_no_operators_yaml_returns_info(self, tmp_path):
        repo = _make_repo(tmp_path, None)
        violations = lint(repo)
        assert any(v.code == "OPERATORS_YAML_ABSENT" for v in violations)

    def test_clean_repo_no_violations(self, tmp_path):
        operators = {
            "shared_root_files": [".gitignore", "workouts-history.md", OPERATORS_FILE],
            "writers": {
                "a3f7c1b2c4d5": {
                    "alias": "mac",
                    "host": "tiresias",
                    "provisioned_at": "2026-04-20T08:00:00Z",
                    "decommissioned_at": None,
                },
            },
        }
        repo = _make_repo(tmp_path, operators)
        (repo / "a3f7c1b2c4d5").mkdir()
        (repo / "a3f7c1b2c4d5" / ".gitkeep").touch()
        violations = lint(repo)
        assert violations == []


class TestWriterSubdirChecks:
    def test_writer_declared_but_subdir_missing(self, tmp_path):
        operators = {
            "shared_root_files": [".gitignore", "workouts-history.md", OPERATORS_FILE],
            "writers": {
                "ffffffffffff": {
                    "alias": "ghost",
                    "provisioned_at": "2026-04-20T08:00:00Z",
                    "decommissioned_at": None,
                },
            },
        }
        repo = _make_repo(tmp_path, operators)
        violations = lint(repo)
        assert any(v.code == "WRITER_SUBDIR_MISSING" for v in violations)
        msg = next(v.message for v in violations if v.code == "WRITER_SUBDIR_MISSING")
        assert "ffffffffffff" in msg
        assert "ghost" in msg

    def test_subdir_undeclared_emits_violation(self, tmp_path):
        operators = {
            "shared_root_files": [".gitignore", "workouts-history.md", OPERATORS_FILE],
            "writers": {},
        }
        repo = _make_repo(tmp_path, operators)
        # Subdir hash 12-char mais non déclaré
        (repo / "deadbeef1234").mkdir()
        violations = lint(repo)
        assert any(v.code == "WRITER_SUBDIR_UNDECLARED" for v in violations)

    def test_non_hash_subdir_not_flagged_as_undeclared(self, tmp_path):
        operators = {
            "shared_root_files": [".gitignore", "workouts-history.md", OPERATORS_FILE, "bilans"],
            "writers": {},
        }
        repo = _make_repo(tmp_path, operators)
        # bilans = subdir non-hash, OK car dans whitelist
        (repo / "bilans").mkdir()
        violations = lint(repo)
        assert not any(v.code == "WRITER_SUBDIR_UNDECLARED" for v in violations)


class TestRootEntryWhitelist:
    def test_unauthorized_root_file_flagged(self, tmp_path):
        operators = {
            "shared_root_files": [".gitignore", "workouts-history.md", OPERATORS_FILE],
            "writers": {},
        }
        repo = _make_repo(tmp_path, operators)
        (repo / "leak.txt").write_text("oops")
        violations = lint(repo)
        assert any(
            v.code == "ROOT_ENTRY_UNAUTHORIZED" and "leak.txt" in v.message for v in violations
        )

    def test_whitelist_dir_pattern_allows_subtree(self, tmp_path):
        operators = {
            "shared_root_files": [
                ".gitignore",
                "workouts-history.md",
                OPERATORS_FILE,
                "docs/architecture/**",
            ],
            "writers": {},
        }
        repo = _make_repo(tmp_path, operators)
        (repo / "docs").mkdir()
        (repo / "docs" / "architecture").mkdir()
        (repo / "docs" / "architecture" / "adr-v5.md").write_text("# ADR")
        violations = lint(repo)
        assert not any(v.code == "ROOT_ENTRY_UNAUTHORIZED" for v in violations)

    def test_git_dir_skipped(self, tmp_path):
        operators = {
            "shared_root_files": [".gitignore", "workouts-history.md", OPERATORS_FILE],
            "writers": {},
        }
        repo = _make_repo(tmp_path, operators)
        (repo / ".git").mkdir()
        violations = lint(repo)
        assert not any(".git" in v.message for v in violations)


class TestDecommissionedWriter:
    def test_decommissioned_writer_with_files_warns(self, tmp_path):
        operators = {
            "shared_root_files": [".gitignore", "workouts-history.md", OPERATORS_FILE],
            "writers": {
                "abc123def456": {
                    "alias": "old-mac",
                    "provisioned_at": "2025-01-01T00:00:00Z",
                    "decommissioned_at": "2026-04-15T00:00:00Z",
                },
            },
        }
        repo = _make_repo(tmp_path, operators)
        sub = repo / "abc123def456"
        sub.mkdir()
        (sub / "lingering.md").write_text("data still here")
        violations = lint(repo)
        assert any(v.code == "DECOMMISSIONED_WRITER_NOT_EMPTY" for v in violations)

    def test_decommissioned_writer_only_gitkeep_no_warn(self, tmp_path):
        operators = {
            "shared_root_files": [".gitignore", "workouts-history.md", OPERATORS_FILE],
            "writers": {
                "abc123def456": {
                    "alias": "old-mac",
                    "provisioned_at": "2025-01-01T00:00:00Z",
                    "decommissioned_at": "2026-04-15T00:00:00Z",
                },
            },
        }
        repo = _make_repo(tmp_path, operators)
        sub = repo / "abc123def456"
        sub.mkdir()
        (sub / ".gitkeep").touch()
        violations = lint(repo)
        assert not any(v.code == "DECOMMISSIONED_WRITER_NOT_EMPTY" for v in violations)


class TestParseErrors:
    def test_invalid_yaml_emits_parse_error(self, tmp_path):
        repo = tmp_path / "training-logs"
        repo.mkdir()
        (repo / OPERATORS_FILE).write_text("not: valid: yaml: [")
        violations = lint(repo)
        assert any(v.code == "OPERATORS_YAML_PARSE_ERROR" for v in violations)

    def test_writers_not_a_dict_emits_invalid(self, tmp_path):
        operators = {
            "shared_root_files": [".gitignore", "workouts-history.md", OPERATORS_FILE],
            "writers": "should-be-a-dict",
        }
        repo = _make_repo(tmp_path, operators)
        violations = lint(repo)
        assert any(v.code == "OPERATORS_YAML_INVALID" for v in violations)


class TestViolationFormat:
    def test_gha_format(self):
        v = Violation("CODE_X", "something off")
        assert v.format_gha() == "::warning title=CODE_X::something off"

    def test_plain_format(self):
        v = Violation("CODE_X", "something off")
        assert v.format_plain() == "[CODE_X] something off"
