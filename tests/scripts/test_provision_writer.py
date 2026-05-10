"""Tests pour le helper provision-writer (ADR v5 Phase 2)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

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
    subprocess.run(
        ["git", "init", "-q", "--initial-branch=main"], cwd=repo, check=True
    )
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
        ops = yaml.safe_load(
            (empty_training_repo / ".operators.yaml").read_text()
        )
        assert "shared_root_files" in ops
        assert ".gitignore" in ops["shared_root_files"]
        assert ".operators.yaml" in ops["shared_root_files"]

    def test_commit_created_with_writer_metadata(self, empty_training_repo):
        h = provision_writer(
            "mac", empty_training_repo, host="tiresias", push=False
        )
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
        ops = yaml.safe_load(
            (empty_training_repo / ".operators.yaml").read_text()
        )
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
