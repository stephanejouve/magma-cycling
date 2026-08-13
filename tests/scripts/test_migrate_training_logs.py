"""Tests BT-027 / ADR v5 §7 — script migrate_training_logs.

Couvre :
- Nominal : repo legacy → writer provisionné + git mv des items legacy
  + commit atomique unique.
- Dry-run : plan loggé sans écriture disque, retour writer_hash=None.
- Alias : default = hostname, override CLI.
- Idempotent : appel sur repo déjà migré → RuntimeError (pas de re-migration).
- Racine invalide (inexistante, pas git) → FileNotFoundError.
- No-push : commit local, pas de push (approprié pour tests).
- Rollback : `git reset --hard HEAD~1` restaure l'état legacy.
"""

from __future__ import annotations

import subprocess

import pytest

from magma_cycling.config.data_repo import detect_legacy_layout
from magma_cycling.scripts.migrate_training_logs import (
    _default_alias,
    migrate_training_logs,
)


def _git(args, cwd):
    """Wrapper minimal pour git dans les tests."""
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


@pytest.fixture
def legacy_git_repo(tmp_path):
    """Repo git legacy avec quelques fichiers en racine hors whitelist."""
    root = tmp_path / "training-logs"
    root.mkdir()
    _git(["init", "-b", "main"], cwd=root)
    _git(["config", "user.email", "test@example.com"], cwd=root)
    _git(["config", "user.name", "test"], cwd=root)

    # Fichiers legacy racine (hors whitelist)
    (root / "activities_tracking.json").write_text('{"foo": "bar"}\n')
    (root / "workouts-history.md").write_text("# History\n")
    weekly = root / "weekly-reports"
    weekly.mkdir()
    (weekly / "S099.md").write_text("weekly S099\n")

    # Whitelist items (ne doivent PAS être déplacés)
    (root / ".gitignore").write_text("*.pyc\n")
    (root / "README.md").write_text("# training-logs\n")

    _git(["add", "-A"], cwd=root)
    _git(["commit", "-m", "initial legacy state"], cwd=root)

    return root


@pytest.fixture
def migrated_git_repo(tmp_path):
    """Repo git déjà migré (.operators.yaml présent + subdir)."""
    root = tmp_path / "training-logs-migrated"
    root.mkdir()
    _git(["init", "-b", "main"], cwd=root)
    _git(["config", "user.email", "test@example.com"], cwd=root)
    _git(["config", "user.name", "test"], cwd=root)
    (root / ".gitignore").write_text("*.pyc\n")
    (root / ".operators.yaml").write_text(
        "shared_root_files:\n  - .gitignore\n  - .operators.yaml\n"
        "writers:\n  abc123def456:\n    alias: mac\n    host: tiresias\n"
        "    provisioned_at: 2026-08-13T21:00:00Z\n"
        "    decommissioned_at: null\n"
    )
    (root / "abc123def456").mkdir()
    (root / "abc123def456" / "data.json").write_text("{}")
    _git(["add", "-A"], cwd=root)
    _git(["commit", "-m", "migrated state"], cwd=root)
    return root


class TestNominalMigration:
    def test_migrates_legacy_repo_end_to_end(self, legacy_git_repo):
        result = migrate_training_logs(legacy_git_repo, alias="testwriter", push=False)
        assert result["writer_hash"] is not None
        assert len(result["writer_hash"]) == 12
        assert result["alias"] == "testwriter"
        assert set(result["moved_items"]) == {
            "activities_tracking.json",
            "workouts-history.md",
            "weekly-reports",
        }
        assert result["commit_sha"] not in (None, "unknown")
        assert result["pushed"] is False  # push=False
        assert "reset --hard HEAD~1" in result["rollback_hint"]

        # Sanity filesystem
        assert (legacy_git_repo / ".operators.yaml").is_file()
        writer_dir = legacy_git_repo / result["writer_hash"]
        assert writer_dir.is_dir()
        assert (writer_dir / "activities_tracking.json").is_file()
        assert (writer_dir / "workouts-history.md").is_file()
        assert (writer_dir / "weekly-reports" / "S099.md").is_file()

        # Whitelist items restent en racine
        assert (legacy_git_repo / ".gitignore").is_file()
        assert (legacy_git_repo / "README.md").is_file()

        # Legacy items disparus de la racine
        assert not (legacy_git_repo / "activities_tracking.json").exists()
        assert not (legacy_git_repo / "workouts-history.md").exists()
        assert not (legacy_git_repo / "weekly-reports").exists()

        # Post-migration : le repo n'est plus legacy
        assert detect_legacy_layout(legacy_git_repo) is False

    def test_commit_is_atomic(self, legacy_git_repo):
        """Un seul commit couvre provision + git mv (pas 2 commits séparés)."""
        _before_count = int(
            subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=legacy_git_repo,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        migrate_training_logs(legacy_git_repo, alias="atomic", push=False)
        after_count = int(
            subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=legacy_git_repo,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        assert after_count == _before_count + 1  # exactement 1 commit ajouté

    def test_commit_message_references_bt_and_alias(self, legacy_git_repo):
        migrate_training_logs(legacy_git_repo, alias="beta", push=False)
        msg = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=legacy_git_repo,
            capture_output=True,
            text=True,
        ).stdout
        assert "[migrate] training-logs:" in msg
        assert "beta" in msg
        assert "BT-027" in msg
        assert "ADR v5" in msg


class TestDryRun:
    def test_dry_run_no_writes(self, legacy_git_repo):
        result = migrate_training_logs(legacy_git_repo, alias="beta", dry_run=True, push=False)
        assert result["writer_hash"] is None
        assert result["alias"] == "beta"
        assert set(result["moved_items"]) == {
            "activities_tracking.json",
            "workouts-history.md",
            "weekly-reports",
        }
        assert result["commit_sha"] is None
        assert result["pushed"] is False
        # Rien n'a été écrit
        assert not (legacy_git_repo / ".operators.yaml").exists()
        assert (legacy_git_repo / "activities_tracking.json").is_file()

    def test_dry_run_repo_still_legacy(self, legacy_git_repo):
        migrate_training_logs(legacy_git_repo, dry_run=True, push=False)
        assert detect_legacy_layout(legacy_git_repo) is True


class TestAlias:
    def test_default_alias_matches_hostname(self):
        alias = _default_alias()
        assert alias  # non-vide
        assert "." not in alias  # domaine tronqué

    def test_default_alias_used_when_none(self, legacy_git_repo):
        result = migrate_training_logs(legacy_git_repo, alias=None, push=False)
        assert result["alias"] == _default_alias()

    def test_alias_override(self, legacy_git_repo):
        result = migrate_training_logs(legacy_git_repo, alias="custom-name", push=False)
        assert result["alias"] == "custom-name"


class TestIdempotencyAndValidation:
    def test_migrated_repo_raises(self, migrated_git_repo):
        with pytest.raises(RuntimeError, match="NOT in legacy layout"):
            migrate_training_logs(migrated_git_repo, push=False)

    def test_nonexistent_root_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="does not exist"):
            migrate_training_logs(tmp_path / "no-such-dir", push=False)

    def test_non_git_root_raises(self, tmp_path):
        d = tmp_path / "not-a-git-repo"
        d.mkdir()
        with pytest.raises(FileNotFoundError, match="not a git repository"):
            migrate_training_logs(d, push=False)


class TestRollback:
    def test_reset_hard_restores_legacy_state(self, legacy_git_repo):
        """Le rollback commande advertisée dans le return marche vraiment."""
        # État avant migration
        legacy_files_before = sorted(p.name for p in legacy_git_repo.iterdir() if p.name != ".git")
        result = migrate_training_logs(legacy_git_repo, alias="beta", push=False)

        # Assertion préliminaire : la migration a bien changé l'état
        legacy_files_after_migrate = sorted(
            p.name for p in legacy_git_repo.iterdir() if p.name != ".git"
        )
        assert legacy_files_before != legacy_files_after_migrate

        # Exécuter le rollback tel que suggéré
        _git(["reset", "--hard", "HEAD~1"], cwd=legacy_git_repo)

        # État post-rollback = état pré-migration
        legacy_files_after_rollback = sorted(
            p.name for p in legacy_git_repo.iterdir() if p.name != ".git"
        )
        assert legacy_files_after_rollback == legacy_files_before
        assert detect_legacy_layout(legacy_git_repo) is True

        # Rollback hint reference le commit produit (non trivial car
        # ce test valide que push=False → hint = reset, pas revert)
        assert "reset --hard HEAD~1" in result["rollback_hint"]
