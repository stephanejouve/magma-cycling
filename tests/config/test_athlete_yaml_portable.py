"""Tests for the portable athlete.yaml resolution (PR5 plan iso-config, AC1).

Covers :func:`resolve_athlete_yaml_path` (env priority + repo + legacy
fallback), :attr:`DataRepoConfig.athlete_config_path`, the
``config/athlete.yaml`` whitelist entry for writer-scoped guard-rail, and
the bootstrap fallback in :func:`load_athlete_context`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from magma_cycling.config.athlete_context import BUNDLE_ATHLETE_YAML, load_athlete_context
from magma_cycling.config.data_repo import (
    ATHLETE_CONFIG_FILENAME,
    ATHLETE_CONFIG_PATH_ENV,
    ATHLETE_CONFIG_SUBDIR,
    DEFAULT_SHARED_ROOT_FILES,
    LEGACY_ROOT_ENV,
    ROOT_ENV,
    WRITER_ID_ENV,
    WRITER_SCOPED_ENV,
    DataRepoConfig,
    resolve_athlete_yaml_path,
)
from magma_cycling.config.geo import GeoPoint, save_home_location
from magma_cycling.paths import get_athlete_yaml_path


@pytest.fixture
def temp_training_repo(tmp_path):
    """Repo training-logs minimal pour DataRepoConfig writer-scoped."""
    repo = tmp_path / "training-logs"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "--initial-branch=main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@magma"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "workouts-history.md").touch()
    writer_a = "a3f7c1b2c4d5"
    (repo / writer_a).mkdir()
    (repo / writer_a / "workouts-history.md").touch()
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=repo, check=True)
    return repo, writer_a


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for v in (
        ROOT_ENV,
        LEGACY_ROOT_ENV,
        WRITER_ID_ENV,
        WRITER_SCOPED_ENV,
        ATHLETE_CONFIG_PATH_ENV,
    ):
        monkeypatch.delenv(v, raising=False)


class TestResolverPriority:
    def test_legacy_fallback_when_no_env(self):
        path = resolve_athlete_yaml_path()
        assert path == get_athlete_yaml_path()

    def test_uses_training_data_root(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        path = resolve_athlete_yaml_path()
        assert path == tmp_path / ATHLETE_CONFIG_SUBDIR / ATHLETE_CONFIG_FILENAME

    def test_uses_legacy_training_data_repo(self, tmp_path, monkeypatch):
        monkeypatch.setenv(LEGACY_ROOT_ENV, str(tmp_path))
        path = resolve_athlete_yaml_path()
        assert path == tmp_path / ATHLETE_CONFIG_SUBDIR / ATHLETE_CONFIG_FILENAME

    def test_explicit_env_override_takes_priority(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path / "ignored"))
        monkeypatch.setenv(ATHLETE_CONFIG_PATH_ENV, str(tmp_path / "custom" / "a.yaml"))
        path = resolve_athlete_yaml_path()
        assert path == tmp_path / "custom" / "a.yaml"

    def test_override_expanduser(self, monkeypatch):
        monkeypatch.setenv(ATHLETE_CONFIG_PATH_ENV, "~/my-athlete.yaml")
        path = resolve_athlete_yaml_path()
        assert path == Path.home() / "my-athlete.yaml"

    def test_resolver_does_not_touch_filesystem(self, tmp_path, monkeypatch):
        nonexistent = tmp_path / "absent"
        monkeypatch.setenv(ROOT_ENV, str(nonexistent))
        path = resolve_athlete_yaml_path()
        assert path == nonexistent / ATHLETE_CONFIG_SUBDIR / ATHLETE_CONFIG_FILENAME
        assert not nonexistent.exists()


class TestConfigPropertyOnDataRepoConfig:
    def test_default_under_root_when_flat(self, temp_training_repo, monkeypatch):
        repo, _ = temp_training_repo
        monkeypatch.setenv(ROOT_ENV, str(repo))
        cfg = DataRepoConfig()
        assert (
            cfg.athlete_config_path
            == (repo / ATHLETE_CONFIG_SUBDIR / ATHLETE_CONFIG_FILENAME).resolve()
        )

    def test_shared_under_root_in_writer_scoped_mode(self, temp_training_repo, monkeypatch):
        """Critical: athlete.yaml stays at root in writer-scoped mode (1 athlete / repo)."""
        repo, writer_a = temp_training_repo
        monkeypatch.setenv(ROOT_ENV, str(repo))
        monkeypatch.setenv(WRITER_SCOPED_ENV, "1")
        monkeypatch.setenv(WRITER_ID_ENV, writer_a)
        cfg = DataRepoConfig()
        assert cfg.data_repo_path == (repo / writer_a).resolve()
        # athlete_config_path stays at root, NOT under the writer subdir
        assert (
            cfg.athlete_config_path
            == (repo / ATHLETE_CONFIG_SUBDIR / ATHLETE_CONFIG_FILENAME).resolve()
        )

    def test_explicit_env_override_on_config(self, tmp_path, temp_training_repo, monkeypatch):
        repo, _ = temp_training_repo
        monkeypatch.setenv(ROOT_ENV, str(repo))
        monkeypatch.setenv(ATHLETE_CONFIG_PATH_ENV, str(tmp_path / "x.yaml"))
        cfg = DataRepoConfig()
        assert cfg.athlete_config_path == tmp_path / "x.yaml"


class TestEnsureDirectoriesCreatesAthleteConfigDir:
    def test_creates_config_dir(self, temp_training_repo, monkeypatch):
        repo, _ = temp_training_repo
        monkeypatch.setenv(ROOT_ENV, str(repo))
        cfg = DataRepoConfig()
        config_dir = repo / ATHLETE_CONFIG_SUBDIR
        assert not config_dir.exists()
        cfg.ensure_directories()
        assert config_dir.is_dir()


class TestWhitelistContainsAthleteConfig:
    def test_default_whitelist_contains_athlete_yaml(self):
        assert "config/athlete.yaml" in DEFAULT_SHARED_ROOT_FILES

    def test_is_safe_write_path_allows_athlete_in_scoped_mode(
        self, temp_training_repo, monkeypatch
    ):
        repo, writer_a = temp_training_repo
        monkeypatch.setenv(ROOT_ENV, str(repo))
        monkeypatch.setenv(WRITER_SCOPED_ENV, "1")
        monkeypatch.setenv(WRITER_ID_ENV, writer_a)
        cfg = DataRepoConfig()
        athlete_file = repo / ATHLETE_CONFIG_SUBDIR / ATHLETE_CONFIG_FILENAME
        athlete_file.parent.mkdir(parents=True, exist_ok=True)
        athlete_file.touch()
        assert cfg.is_safe_write_path(athlete_file) is True


class TestHomeLocationGoesToPortableYaml:
    """MCT-XXX-0 home_location now writes to the portable training-logs YAML."""

    def test_save_home_location_lands_in_repo_when_root_set(self, temp_training_repo, monkeypatch):
        repo, _ = temp_training_repo
        monkeypatch.setenv(ROOT_ENV, str(repo))
        target = repo / ATHLETE_CONFIG_SUBDIR / ATHLETE_CONFIG_FILENAME
        assert not target.exists()
        save_home_location(GeoPoint(lat=45.69, lon=3.34, label="Chas"))
        # save_home_location resolves the path itself (via resolve_athlete_yaml_path)
        assert target.is_file()


class TestLoadAthleteContextBootstrapFallback:
    def test_falls_back_to_bundle_when_resolved_absent(self, tmp_path, monkeypatch):
        # ATHLETE_CONFIG_PATH points at a non-existent file → load falls back to bundle
        monkeypatch.setenv(ATHLETE_CONFIG_PATH_ENV, str(tmp_path / "absent.yaml"))
        ctx = load_athlete_context()
        # Bundle YAML provides a non-empty dict in the magma-cycling repo
        if BUNDLE_ATHLETE_YAML.exists():
            assert ctx  # non-empty
        else:
            assert ctx == {}

    def test_uses_resolved_path_when_present(self, tmp_path, monkeypatch):
        target = tmp_path / "athlete.yaml"
        target.write_text(
            "athlete:\n  name: Override\n  age: 99\n",
            encoding="utf-8",
        )
        monkeypatch.setenv(ATHLETE_CONFIG_PATH_ENV, str(target))
        ctx = load_athlete_context()
        assert ctx.get("name") == "Override"
        assert ctx.get("age") == 99
