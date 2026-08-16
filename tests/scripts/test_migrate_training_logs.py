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
    """Repo git déjà migré (.operators.yaml présent + subdir + racine clean)."""
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


@pytest.fixture
def hybrid_git_repo(tmp_path):
    """Repo git hybride BT-030 : ``.operators.yaml`` + writer subdir
    déjà provisionné (Phase 1A partielle) + du flat racine encore à
    absorber. Cas réel constaté sur prod NAS (2026-08-15)."""
    root = tmp_path / "training-logs-hybrid"
    root.mkdir()
    _git(["init", "-b", "main"], cwd=root)
    _git(["config", "user.email", "test@example.com"], cwd=root)
    _git(["config", "user.name", "test"], cwd=root)
    (root / ".gitignore").write_text("*.pyc\n")
    (root / ".operators.yaml").write_text(
        "shared_root_files:\n  - .gitignore\n  - .operators.yaml\n"
        "writers:\n  88bc132e32a0:\n    alias: nas-prod\n    host: nas\n"
        "    provisioned_at: 2026-05-03T09:44:00Z\n"
        "    decommissioned_at: null\n"
    )
    # Writer déjà provisionné (Phase 1A partielle)
    (root / "88bc132e32a0").mkdir()
    (root / "88bc132e32a0" / "workouts-history.md").write_text("legacy\n")
    # Contenu flat racine encore à absorber (écritures runtime post-Phase 1A).
    # NB : ``data/`` est whitelisté au toplevel (partagé entre writers) donc
    # on ne l'ajoute pas ici. On simule uniquement des paths clairement
    # hors whitelist, représentatifs du cas prod NAS (backups, weekly-reports,
    # activities tracking).
    (root / "activities_tracking.json").write_text('{"live": true}')
    (root / "backups").mkdir()
    (root / "backups" / "S105-backup.md").write_text("backup\n")
    weekly = root / "weekly-reports"
    weekly.mkdir()
    (weekly / "S105.md").write_text("weekly S105\n")
    _git(["add", "-A"], cwd=root)
    _git(["commit", "-m", "hybrid state"], cwd=root)
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


class TestHybridMigration:
    """BT-030 : le script doit accepter et migrer un repo hybride
    (``.operators.yaml`` présent + writer subdir + flat racine)."""

    def test_migrates_hybrid_repo_end_to_end(self, hybrid_git_repo):
        """La migration doit :
        - provisionner un NOUVEAU writer distinct de celui existant
        - déplacer le contenu flat racine vers le nouveau subdir
        - laisser le writer existant (``88bc132e32a0``) intact
        - laisser ``.operators.yaml`` avec les 2 writers listés
        """
        result = migrate_training_logs(hybrid_git_repo, alias="new-writer", push=False)
        assert result["writer_hash"] is not None
        assert result["writer_hash"] != "88bc132e32a0"  # nouveau writer distinct
        assert set(result["moved_items"]) == {
            "activities_tracking.json",
            "backups",
            "weekly-reports",
        }
        # Nouveau subdir peuplé
        new_dir = hybrid_git_repo / result["writer_hash"]
        assert (new_dir / "activities_tracking.json").is_file()
        assert (new_dir / "backups" / "S105-backup.md").is_file()
        assert (new_dir / "weekly-reports" / "S105.md").is_file()
        # Ancien writer intact
        assert (hybrid_git_repo / "88bc132e32a0" / "workouts-history.md").is_file()
        # Flat racine purgé
        assert not (hybrid_git_repo / "activities_tracking.json").exists()
        assert not (hybrid_git_repo / "backups").exists()
        assert not (hybrid_git_repo / "weekly-reports").exists()
        # Post-migration : plus de layout hybride (racine 100 % whitelist + writers)
        from magma_cycling.config.data_repo import detect_legacy_layout as _detect

        assert _detect(hybrid_git_repo) is False

    def test_hybrid_migration_atomic_single_commit(self, hybrid_git_repo):
        """Provision + git mv du flat = 1 seul commit atomique (doctrine BT-027)."""
        before = int(
            subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=hybrid_git_repo,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        migrate_training_logs(hybrid_git_repo, alias="new-writer", push=False)
        after = int(
            subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=hybrid_git_repo,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        assert after == before + 1


class TestSkipUntrackedItemsBT031:
    """BT-031 : les items untracked/gitignored en racine doivent être
    laissés en place, pas ``git mv`` vers le writer subdir. Raison de
    sécurité (creds runtime) + robustesse (git mv fail hard sur untracked
    → cassait la migration BT-027 mid-course, incident prod 2026-08-16)."""

    @pytest.fixture
    def legacy_repo_with_untracked(self, tmp_path):
        """Repo legacy avec :
        - tracked : ``activities_tracking.json``, ``weekly-reports/`` (à migrer)
        - untracked/gitignored : ``.withings_credentials.json``, ``.env``
          (doivent rester en racine)"""
        root = tmp_path / "training-logs"
        root.mkdir()
        _git(["init", "-b", "main"], cwd=root)
        _git(["config", "user.email", "test@example.com"], cwd=root)
        _git(["config", "user.name", "test"], cwd=root)

        # Tracked items (à migrer)
        (root / "activities_tracking.json").write_text("{}")
        weekly = root / "weekly-reports"
        weekly.mkdir()
        (weekly / "S099.md").write_text("report\n")
        # Whitelist
        (root / ".gitignore").write_text("*.pyc\n" ".withings_credentials.json\n" ".env\n")
        _git(["add", "-A"], cwd=root)
        _git(["commit", "-m", "initial legacy"], cwd=root)

        # Untracked runtime/creds — présents sur fs mais gitignored,
        # jamais git add
        (root / ".withings_credentials.json").write_text('{"secret": "REDACTED"}')
        (root / ".env").write_text("API_KEY=REDACTED\n")

        return root

    def test_skips_untracked_and_migrates_tracked(self, legacy_repo_with_untracked):
        """Le script filtre les untracked, ne fail pas, migre les tracked
        proprement. Les untracked restent en racine."""
        result = migrate_training_logs(legacy_repo_with_untracked, alias="w", push=False)
        # Tracked migrated
        assert set(result["moved_items"]) == {"activities_tracking.json", "weekly-reports"}
        # Untracked skipped, listés dans le return
        assert set(result["skipped_untracked"]) == {".withings_credentials.json", ".env"}
        # Filesystem : untracked toujours en racine
        assert (legacy_repo_with_untracked / ".withings_credentials.json").is_file()
        assert (legacy_repo_with_untracked / ".env").is_file()
        # Tracked bien moved
        writer_dir = legacy_repo_with_untracked / result["writer_hash"]
        assert (writer_dir / "activities_tracking.json").is_file()
        assert (writer_dir / "weekly-reports" / "S099.md").is_file()
        # Untracked JAMAIS moved dans le subdir (sécurité anti-leak)
        assert not (writer_dir / ".withings_credentials.json").exists()
        assert not (writer_dir / ".env").exists()

    def test_dry_run_reports_untracked_separately(self, legacy_repo_with_untracked):
        """En dry-run, ``skipped_untracked`` doit lister les items skippés
        pour que l'opérateur voit clairement ce qui restera en racine."""
        result = migrate_training_logs(
            legacy_repo_with_untracked, alias="w", dry_run=True, push=False
        )
        assert set(result["skipped_untracked"]) == {".withings_credentials.json", ".env"}
        assert set(result["moved_items"]) == {"activities_tracking.json", "weekly-reports"}
        # Aucun write : untracked toujours en racine, tracked aussi (dry-run)
        assert (legacy_repo_with_untracked / ".withings_credentials.json").is_file()
        assert (legacy_repo_with_untracked / "activities_tracking.json").is_file()

    def test_only_untracked_items_result_in_provision_but_no_move(self, tmp_path):
        """Edge case : repo avec UNIQUEMENT des items untracked en racine
        (rien à migrer côté git). Le script doit quand même détecter
        « legacy » (car items fs présents) mais ne rien mover, juste
        provisionner le writer."""
        root = tmp_path / "training-logs-only-untracked"
        root.mkdir()
        _git(["init", "-b", "main"], cwd=root)
        _git(["config", "user.email", "test@example.com"], cwd=root)
        _git(["config", "user.name", "test"], cwd=root)
        (root / ".gitignore").write_text(".env\n")
        _git(["add", "-A"], cwd=root)
        _git(["commit", "-m", "gitignore only"], cwd=root)
        # Ajout untracked APRÈS le commit initial (jamais staged)
        (root / ".env").write_text("secret\n")
        (root / "runtime-state.json").write_text("{}")  # non gitignored mais jamais add

        result = migrate_training_logs(root, alias="w", push=False)
        assert result["moved_items"] == []
        assert set(result["skipped_untracked"]) == {".env", "runtime-state.json"}
        # Writer provisionné mais vide de contenu migré (à part .gitkeep)
        assert result["writer_hash"] is not None
        # Untracked toujours en racine
        assert (root / ".env").is_file()
        assert (root / "runtime-state.json").is_file()


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
