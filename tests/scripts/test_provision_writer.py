"""Tests pour le helper provision-writer (ADR v5 Phase 2)."""

from __future__ import annotations

import re
import subprocess

import pytest
import yaml

from magma_cycling.scripts.provision_writer import (
    _compute_writer_hash,
    _utc_timestamp_z,
    provision_writer,
)


@pytest.fixture
def empty_training_repo(tmp_path):
    """Repo training-logs vide initialisé git, prêt pour 1er provision."""
    repo = tmp_path / "training-logs"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "--initial-branch=main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@magma"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "README.md").write_text("# training-logs\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=repo, check=True)
    return repo


class TestUtcTimestampZ:
    def test_format_strict_z_suffix(self):
        ts = _utc_timestamp_z()
        # Format ISO 8601 avec Z (pas +00:00, pas d'offset)
        assert ts.endswith("Z")
        # Exact regex : YYYY-MM-DDTHH:MM:SSZ (no fractional seconds)
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", ts)
        assert "+" not in ts

    def test_no_offset_local_time(self):
        ts = _utc_timestamp_z()
        # Pas de signe d'offset local
        assert "+00:00" not in ts


class TestComputeWriterHash:
    def test_hash_is_12_hex_chars(self):
        h = _compute_writer_hash("2026-04-20T08:00:00Z", "mac")
        assert len(h) == 12
        assert re.match(r"^[0-9a-f]{12}$", h)

    def test_hash_reproducible_for_same_inputs(self):
        h1 = _compute_writer_hash("2026-04-20T08:00:00Z", "mac")
        h2 = _compute_writer_hash("2026-04-20T08:00:00Z", "mac")
        assert h1 == h2

    def test_different_alias_different_hash(self):
        h1 = _compute_writer_hash("2026-04-20T08:00:00Z", "mac")
        h2 = _compute_writer_hash("2026-04-20T08:00:00Z", "nas-prod")
        assert h1 != h2

    def test_different_timestamp_different_hash(self):
        h1 = _compute_writer_hash("2026-04-20T08:00:00Z", "mac")
        h2 = _compute_writer_hash("2026-04-20T08:00:01Z", "mac")
        assert h1 != h2


class TestProvisionWriter:
    def test_creates_yaml_with_writer_entry(self, empty_training_repo):
        h = provision_writer(
            "mac",
            empty_training_repo,
            host="tiresias",
            push=False,
        )
        yaml_path = empty_training_repo / ".operators.yaml"
        assert yaml_path.is_file()
        ops = yaml.safe_load(yaml_path.read_text())
        assert h in ops["writers"]
        entry = ops["writers"][h]
        assert entry["alias"] == "mac"
        assert entry["host"] == "tiresias"
        assert entry["provisioned_at"].endswith("Z")
        assert entry["decommissioned_at"] is None

    def test_creates_subdir_with_gitkeep(self, empty_training_repo):
        h = provision_writer("mac", empty_training_repo, push=False)
        subdir = empty_training_repo / h
        assert subdir.is_dir()
        # Pour que git tracke le subdir vide, .gitkeep créé
        assert (subdir / ".gitkeep").is_file()

    def test_default_shared_root_files_seeded(self, empty_training_repo):
        provision_writer("mac", empty_training_repo, push=False)
        ops = yaml.safe_load((empty_training_repo / ".operators.yaml").read_text())
        assert "shared_root_files" in ops
        assert ".gitignore" in ops["shared_root_files"]
        assert ".operators.yaml" in ops["shared_root_files"]

    def test_commit_created_with_writer_metadata(self, empty_training_repo):
        h = provision_writer("mac", empty_training_repo, host="tiresias", push=False)
        # Vérifier le commit log
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B"],
            cwd=empty_training_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_msg = result.stdout
        assert "provision writer mac" in commit_msg
        assert h in commit_msg
        assert "tiresias" in commit_msg

    def test_appends_to_existing_yaml(self, empty_training_repo):
        h1 = provision_writer("mac", empty_training_repo, push=False)
        h2 = provision_writer("nas-prod", empty_training_repo, push=False)
        ops = yaml.safe_load((empty_training_repo / ".operators.yaml").read_text())
        assert h1 in ops["writers"]
        assert h2 in ops["writers"]
        assert ops["writers"][h1]["alias"] == "mac"
        assert ops["writers"][h2]["alias"] == "nas-prod"

    def test_refuses_duplicate_active_alias(self, empty_training_repo):
        provision_writer("mac", empty_training_repo, push=False)
        with pytest.raises(RuntimeError, match="already provisioned and active"):
            provision_writer("mac", empty_training_repo, push=False)

    def test_returns_hash_for_scriptability(self, empty_training_repo):
        h = provision_writer("mac", empty_training_repo, push=False)
        assert len(h) == 12
        assert re.match(r"^[0-9a-f]{12}$", h)

    def test_raises_if_root_not_a_git_repo(self, tmp_path):
        not_git = tmp_path / "not-git"
        not_git.mkdir()
        with pytest.raises(FileNotFoundError, match="not a git repository"):
            provision_writer("mac", not_git, push=False)

    def test_raises_if_root_does_not_exist(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="does not exist"):
            provision_writer("mac", tmp_path / "nope", push=False)


class TestBT032MergeSharedRootFiles:
    """BT-032 : ``_load_or_init_operators`` doit merger la whitelist
    existante avec ``DEFAULT_SHARED_ROOT_FILES`` (union), pas juste
    ``setdefault`` qui préserve une whitelist restrictive.

    Bug reproduit 2× le 2026-08-16 (chain BT-027 prod NAS) : un yaml
    avec whitelist minimale [.gitignore, README.md, .operators.yaml]
    restait restrictif après provision → guard hybrid layout re-fire
    au premier write dans ``data/wellness/`` (shared par design ADR V5).
    """

    def _init_repo_with_restrictive_yaml(self, tmp_path, extra_writers=None):
        """Helper : crée un repo git avec .operators.yaml restrictif."""
        repo = tmp_path / "training-logs-restrictive"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
        (repo / ".gitignore").touch()
        # Whitelist restrictive : 3 items seulement, sans les patterns data/xxx/**
        operators = {
            "shared_root_files": [".gitignore", "README.md", ".operators.yaml"],
            "writers": extra_writers or {},
        }
        (repo / ".operators.yaml").write_text(yaml.safe_dump(operators), encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "restrictive fixture"], cwd=repo, check=True)
        return repo

    def test_provision_extends_restrictive_whitelist_with_defaults(self, tmp_path):
        """Le cas reproduit en prod : yaml restrictif → après provision,
        whitelist contient les 4 patterns canoniques ADR V5."""
        repo = self._init_repo_with_restrictive_yaml(tmp_path)
        provision_writer("mac", repo, push=False)
        ops = yaml.safe_load((repo / ".operators.yaml").read_text())
        whitelist = ops["shared_root_files"]
        # Restrictifs originels préservés
        assert ".gitignore" in whitelist
        assert "README.md" in whitelist
        assert ".operators.yaml" in whitelist
        # Patterns canoniques ADR V5 ajoutés
        assert "data/intelligence/**" in whitelist
        assert "data/wellness/**" in whitelist
        assert "data/decisions/**" in whitelist
        assert "config/athlete.yaml" in whitelist

    def test_provision_preserves_user_extensions(self, tmp_path):
        """Extensions user légitimes (résidus runtime, patterns beta)
        préservées lors du merge — pas d'écrasement."""
        repo = tmp_path / "training-logs-extended"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
        (repo / ".gitignore").touch()
        # Whitelist canonique + extensions user (ex. résidus runtime racine)
        operators = {
            "shared_root_files": [
                ".gitignore",
                ".operators.yaml",
                "data/wellness/**",
                "bilans/**",  # extension user
                "handoff/**",  # extension user
            ],
            "writers": {},
        }
        (repo / ".operators.yaml").write_text(yaml.safe_dump(operators), encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "extended fixture"], cwd=repo, check=True)

        provision_writer("mac", repo, push=False)
        ops = yaml.safe_load((repo / ".operators.yaml").read_text())
        whitelist = ops["shared_root_files"]
        # Extensions user préservées
        assert "bilans/**" in whitelist
        assert "handoff/**" in whitelist
        # Patterns canoniques ajoutés (data/intelligence, decisions, config)
        assert "data/intelligence/**" in whitelist
        assert "data/decisions/**" in whitelist
        assert "config/athlete.yaml" in whitelist

    def test_provision_idempotent_on_canonical_yaml(self, tmp_path):
        """Yaml déjà canonique → provision n'ajoute pas de doublon."""
        repo = tmp_path / "training-logs-canonical"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
        (repo / ".gitignore").touch()
        # Whitelist DEFAULT_SHARED_ROOT_FILES complet
        from magma_cycling.config.data_repo import DEFAULT_SHARED_ROOT_FILES

        operators = {
            "shared_root_files": list(DEFAULT_SHARED_ROOT_FILES),
            "writers": {},
        }
        (repo / ".operators.yaml").write_text(yaml.safe_dump(operators), encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "canonical fixture"], cwd=repo, check=True)

        before = list(DEFAULT_SHARED_ROOT_FILES)
        provision_writer("mac", repo, push=False)
        ops = yaml.safe_load((repo / ".operators.yaml").read_text())
        after = ops["shared_root_files"]
        # Aucun doublon, ordre préservé
        assert len(after) == len(before)
        assert set(after) == set(before)

    def test_provision_yaml_without_shared_root_files_key(self, tmp_path):
        """Yaml sans clé ``shared_root_files`` → set à DEFAULT complet."""
        repo = tmp_path / "training-logs-no-key"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
        (repo / ".gitignore").touch()
        # Yaml sans shared_root_files du tout (juste writers)
        (repo / ".operators.yaml").write_text("writers: {}\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "no-key fixture"], cwd=repo, check=True)

        from magma_cycling.config.data_repo import DEFAULT_SHARED_ROOT_FILES

        provision_writer("mac", repo, push=False)
        ops = yaml.safe_load((repo / ".operators.yaml").read_text())
        assert set(ops["shared_root_files"]) == set(DEFAULT_SHARED_ROOT_FILES)
