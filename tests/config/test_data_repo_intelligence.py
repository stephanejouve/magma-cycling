"""Tests pour la migration intelligence.json (plan iso-config PR1).

Couvre :

- ``resolve_intelligence_file_path()`` standalone helper (priorité env + fallback)
- ``DataRepoConfig.intelligence_dir`` / ``intelligence_file_path`` properties
- ``ensure_directories`` crée le dossier intelligence
- ``DEFAULT_SHARED_ROOT_FILES`` contient le pattern ``data/intelligence/**`` pour
  l'autorisation writer-scoped future
- ``is_safe_write_path`` autorise les écritures sous ``data/intelligence/`` en
  mode writer-scoped via la whitelist
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from magma_cycling.config.data_repo import (
    DEFAULT_SHARED_ROOT_FILES,
    INTELLIGENCE_DATA_DIR_ENV,
    INTELLIGENCE_FILENAME,
    INTELLIGENCE_SUBDIR,
    LEGACY_ROOT_ENV,
    OPERATORS_FILE,
    ROOT_ENV,
    WRITER_ID_ENV,
    WRITER_SCOPED_ENV,
    DataRepoConfig,
    resolve_intelligence_file_path,
)


@pytest.fixture
def temp_training_repo(tmp_path):
    """Repo training-logs minimal pour DataRepoConfig.

    Returns:
        Tuple ``(root_path, writer_a_hash)``.
    """
    repo = tmp_path / "training-logs"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "--initial-branch=main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@magma"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "workouts-history.md").touch()
    writer_a = "a3f7c1b2c4d5"
    (repo / writer_a).mkdir()
    (repo / writer_a / "workouts-history.md").touch()
    operators = {
        "shared_root_files": [
            ".gitignore",
            "README.md",
            OPERATORS_FILE,
            "data/intelligence/**",
        ],
        "writers": {
            writer_a: {
                "alias": "mac",
                "host": "tiresias",
                "provisioned_at": "2026-04-20T08:00:00Z",
                "decommissioned_at": None,
            },
        },
    }
    (repo / OPERATORS_FILE).write_text(yaml.safe_dump(operators), encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=repo, check=True)
    return repo, writer_a


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Wipe environment vars between tests."""
    for v in (
        ROOT_ENV,
        LEGACY_ROOT_ENV,
        WRITER_ID_ENV,
        WRITER_SCOPED_ENV,
        INTELLIGENCE_DATA_DIR_ENV,
    ):
        monkeypatch.delenv(v, raising=False)


class TestResolveIntelligenceFilePath:
    """Standalone helper — no DataRepoConfig instantiation, no filesystem touch."""

    def test_fallback_legacy_when_no_env(self):
        path = resolve_intelligence_file_path()
        assert path == Path.home() / "data" / INTELLIGENCE_FILENAME

    def test_uses_training_data_root(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        path = resolve_intelligence_file_path()
        assert path == tmp_path / INTELLIGENCE_SUBDIR / INTELLIGENCE_FILENAME

    def test_uses_legacy_training_data_repo(self, tmp_path, monkeypatch):
        monkeypatch.setenv(LEGACY_ROOT_ENV, str(tmp_path))
        path = resolve_intelligence_file_path()
        assert path == tmp_path / INTELLIGENCE_SUBDIR / INTELLIGENCE_FILENAME

    def test_override_env_takes_priority(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path / "ignored"))
        monkeypatch.setenv(INTELLIGENCE_DATA_DIR_ENV, str(tmp_path / "custom"))
        path = resolve_intelligence_file_path()
        assert path == tmp_path / "custom" / INTELLIGENCE_FILENAME

    def test_override_env_expanduser(self, monkeypatch):
        monkeypatch.setenv(INTELLIGENCE_DATA_DIR_ENV, "~/my-intel")
        path = resolve_intelligence_file_path()
        assert path == Path.home() / "my-intel" / INTELLIGENCE_FILENAME

    def test_resolver_does_not_touch_filesystem(self, tmp_path, monkeypatch):
        nonexistent = tmp_path / "absent"
        monkeypatch.setenv(ROOT_ENV, str(nonexistent))
        # Doit retourner le path sans lever — ne crée pas le dossier
        path = resolve_intelligence_file_path()
        assert path == nonexistent / INTELLIGENCE_SUBDIR / INTELLIGENCE_FILENAME
        assert not nonexistent.exists()


class TestIntelligenceDirOnConfig:
    """``DataRepoConfig.intelligence_dir`` resolves under root, not writer subdir."""

    def test_default_under_root_when_flat(self, temp_training_repo, monkeypatch):
        repo, _ = temp_training_repo
        monkeypatch.setenv(ROOT_ENV, str(repo))
        cfg = DataRepoConfig()
        assert cfg.intelligence_dir == (repo / INTELLIGENCE_SUBDIR).resolve()
        assert cfg.intelligence_file_path == (
            repo / INTELLIGENCE_SUBDIR / INTELLIGENCE_FILENAME
        ).resolve()

    def test_shared_under_root_even_when_writer_scoped(
        self, temp_training_repo, monkeypatch
    ):
        """Critical: intelligence stays under ROOT in writer-scoped mode."""
        repo, writer_a = temp_training_repo
        monkeypatch.setenv(ROOT_ENV, str(repo))
        monkeypatch.setenv(WRITER_SCOPED_ENV, "1")
        monkeypatch.setenv(WRITER_ID_ENV, writer_a)
        cfg = DataRepoConfig()
        # data_repo_path is under writer subdir
        assert cfg.data_repo_path == (repo / writer_a).resolve()
        # but intelligence_dir stays at root (shared cross-writers)
        assert cfg.intelligence_dir == (repo / INTELLIGENCE_SUBDIR).resolve()

    def test_override_env_takes_priority_on_config(
        self, tmp_path, temp_training_repo, monkeypatch
    ):
        repo, _ = temp_training_repo
        monkeypatch.setenv(ROOT_ENV, str(repo))
        monkeypatch.setenv(INTELLIGENCE_DATA_DIR_ENV, str(tmp_path / "custom"))
        cfg = DataRepoConfig()
        assert cfg.intelligence_dir == tmp_path / "custom"


class TestEnsureDirectoriesCreatesIntelligence:
    """``ensure_directories`` includes ``intelligence_dir``."""

    def test_creates_intelligence_dir(self, temp_training_repo, monkeypatch):
        repo, _ = temp_training_repo
        monkeypatch.setenv(ROOT_ENV, str(repo))
        cfg = DataRepoConfig()
        intel_dir = repo / INTELLIGENCE_SUBDIR
        assert not intel_dir.exists()
        cfg.ensure_directories()
        assert intel_dir.is_dir()


class TestWhitelistContainsIntelligence:
    """``DEFAULT_SHARED_ROOT_FILES`` must include ``data/intelligence/**``."""

    def test_default_whitelist_contains_intelligence_pattern(self):
        assert "data/intelligence/**" in DEFAULT_SHARED_ROOT_FILES

    def test_is_safe_write_path_allows_intelligence_in_scoped_mode(
        self, temp_training_repo, monkeypatch
    ):
        """Critical: when scoped flag ON, intelligence writes must still pass guard-rail."""
        repo, writer_a = temp_training_repo
        monkeypatch.setenv(ROOT_ENV, str(repo))
        monkeypatch.setenv(WRITER_SCOPED_ENV, "1")
        monkeypatch.setenv(WRITER_ID_ENV, writer_a)
        cfg = DataRepoConfig()
        intel_file = repo / "data" / "intelligence" / "intelligence.json"
        # Path doesn't need to exist for the check (operates on resolved paths)
        intel_file.parent.mkdir(parents=True, exist_ok=True)
        intel_file.touch()
        assert cfg.is_safe_write_path(intel_file) is True
