"""Tests pour le writer-scoping ADR v5 Phase 2 (ticket #39).

Couvre :
- Feature flag ``TRAINING_DATA_WRITER_SCOPED`` (default OFF = legacy flat)
- Résolution ``TRAINING_DATA_ROOT`` + fallback legacy ``TRAINING_DATA_REPO``
- Mode writer-scoped : ``data_repo_path = ROOT/<WRITER_ID>``
- Guard-rail ``writer_id`` manquant en mode scoped → RuntimeError
- ``is_safe_write_path`` legacy permissif vs scoped strict + whitelist
- Lazy-load ``.operators.yaml`` + parse ``shared_root_files``

Pattern fixture pytest ``temp_training_repo()`` : tmp_path + ``git init`` +
arborescence templated (workouts-history.md, .operators.yaml, subdirs).
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import pytest
import yaml

from magma_cycling.config.data_repo import (
    DEFAULT_SHARED_ROOT_FILES,
    LEGACY_ROOT_ENV,
    OPERATORS_FILE,
    ROOT_ENV,
    WRITER_ID_ENV,
    WRITER_SCOPED_ENV,
    DataRepoConfig,
)


@pytest.fixture
def temp_training_repo(tmp_path):
    """Crée un repo training-logs minimal avec git init + arborescence.

    Layout créé :
    - .git/ (init)
    - workouts-history.md (vide)
    - bilans/, data/ (dirs)
    - .operators.yaml (squelette avec shared_root_files par défaut + 2 writers)
    - <hash_a>/workouts-history.md, <hash_a>/bilans/, ... (subdir writer A)
    - <hash_b>/ (subdir writer B vide)

    Returns:
        Tuple ``(root_path, writer_a_hash, writer_b_hash)``.
    """
    repo = tmp_path / "training-logs"
    repo.mkdir()

    subprocess.run(
        ["git", "init", "-q", "--initial-branch=main"], cwd=repo, check=True
    )
    subprocess.run(["git", "config", "user.email", "test@magma"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)

    # Layout flat (legacy compat)
    (repo / "workouts-history.md").touch()
    (repo / "bilans").mkdir()
    (repo / "data").mkdir()
    (repo / "data" / "week_planning").mkdir()
    (repo / ".gitignore").write_text("*.pyc\n")
    (repo / "README.md").write_text("# training-logs\n")

    # 2 subdirs writers fictifs
    writer_a = "a3f7c1b2c4d5"
    writer_b = "9d4e2c117a8b"
    (repo / writer_a).mkdir()
    (repo / writer_a / "workouts-history.md").touch()
    (repo / writer_a / "bilans").mkdir()
    (repo / writer_a / "data").mkdir()
    (repo / writer_a / "data" / "week_planning").mkdir()
    (repo / writer_b).mkdir()
    (repo / writer_b / ".gitkeep").touch()

    # .operators.yaml minimal
    operators = {
        "shared_root_files": [
            ".gitignore",
            "README.md",
            ".operators.yaml",
            "docs/architecture/**",
        ],
        "writers": {
            writer_a: {
                "alias": "mac",
                "host": "tiresias",
                "provisioned_at": "2026-04-20T08:00:00Z",
                "decommissioned_at": None,
            },
            writer_b: {
                "alias": "nas-prod",
                "host": "synology",
                "provisioned_at": "2026-04-20T08:05:00Z",
                "decommissioned_at": None,
            },
        },
    }
    with (repo / OPERATORS_FILE).open("w", encoding="utf-8") as fh:
        yaml.safe_dump(operators, fh)

    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "initial training-logs fixture"],
        cwd=repo,
        check=True,
    )

    return repo, writer_a, writer_b


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """S'assure qu'aucune var d'env writer-scoping ne fuit entre tests."""
    for v in (ROOT_ENV, LEGACY_ROOT_ENV, WRITER_ID_ENV, WRITER_SCOPED_ENV):
        monkeypatch.delenv(v, raising=False)


class TestFeatureFlagDefault:
    """Flag default OFF = layout flat legacy (no-regression critique)."""

    def test_flag_off_data_repo_path_equals_root(self, temp_training_repo, monkeypatch):
        repo, _, _ = temp_training_repo
        monkeypatch.setenv(ROOT_ENV, str(repo))
        cfg = DataRepoConfig()
        assert cfg.data_repo_path == repo.resolve()
        assert cfg.root_path == repo.resolve()
        assert cfg.writer_id is None
        assert cfg.writer_scoped is False

    def test_flag_unset_treated_as_off(self, temp_training_repo, monkeypatch):
        repo, _, _ = temp_training_repo
        monkeypatch.setenv(ROOT_ENV, str(repo))
        # WRITER_SCOPED unset
        cfg = DataRepoConfig()
        assert cfg.writer_scoped is False
        assert cfg.data_repo_path == repo.resolve()

    def test_flag_zero_treated_as_off(self, temp_training_repo, monkeypatch):
        repo, _, _ = temp_training_repo
        monkeypatch.setenv(ROOT_ENV, str(repo))
        monkeypatch.setenv(WRITER_SCOPED_ENV, "0")
        cfg = DataRepoConfig()
        assert cfg.writer_scoped is False


class TestWriterScopedMode:
    """Flag ON + WRITER_ID → data_repo_path = root/<writer_id>."""

    def test_flag_on_with_writer_id_resolves_subdir(
        self, temp_training_repo, monkeypatch
    ):
        repo, writer_a, _ = temp_training_repo
        monkeypatch.setenv(ROOT_ENV, str(repo))
        monkeypatch.setenv(WRITER_SCOPED_ENV, "1")
        monkeypatch.setenv(WRITER_ID_ENV, writer_a)
        cfg = DataRepoConfig()
        assert cfg.writer_scoped is True
        assert cfg.writer_id == writer_a
        assert cfg.root_path == repo.resolve()
        assert cfg.data_repo_path == (repo / writer_a).resolve()

    def test_flag_on_without_writer_id_raises(self, temp_training_repo, monkeypatch):
        repo, _, _ = temp_training_repo
        monkeypatch.setenv(ROOT_ENV, str(repo))
        monkeypatch.setenv(WRITER_SCOPED_ENV, "1")
        # WRITER_ID volontairement absent
        with pytest.raises(RuntimeError, match=WRITER_ID_ENV):
            DataRepoConfig()

    def test_flag_off_via_constructor_overrides_env(
        self, temp_training_repo, monkeypatch
    ):
        """``writer_scoped=False`` constructeur force OFF même si env=1."""
        repo, writer_a, _ = temp_training_repo
        monkeypatch.setenv(ROOT_ENV, str(repo))
        monkeypatch.setenv(WRITER_SCOPED_ENV, "1")
        monkeypatch.setenv(WRITER_ID_ENV, writer_a)
        cfg = DataRepoConfig(writer_scoped=False)
        assert cfg.writer_scoped is False
        assert cfg.data_repo_path == repo.resolve()

    def test_workouts_history_path_in_subdir_when_scoped(
        self, temp_training_repo, monkeypatch
    ):
        repo, writer_a, _ = temp_training_repo
        monkeypatch.setenv(ROOT_ENV, str(repo))
        monkeypatch.setenv(WRITER_SCOPED_ENV, "1")
        monkeypatch.setenv(WRITER_ID_ENV, writer_a)
        cfg = DataRepoConfig()
        assert cfg.workouts_history_path == (repo / writer_a / "workouts-history.md").resolve()
        assert cfg.bilans_dir == (repo / writer_a / "bilans").resolve()
        assert cfg.week_planning_dir == (repo / writer_a / "data" / "week_planning").resolve()


class TestLegacyEnvFallback:
    """``TRAINING_DATA_REPO`` deprecated mais fallback obligatoire avec warning."""

    def test_legacy_env_used_when_root_absent(self, temp_training_repo, monkeypatch, caplog):
        repo, _, _ = temp_training_repo
        monkeypatch.setenv(LEGACY_ROOT_ENV, str(repo))
        with caplog.at_level(logging.WARNING, logger="magma_cycling.config.data_repo"):
            cfg = DataRepoConfig()
        assert cfg.root_path == repo.resolve()
        assert any("deprecated" in rec.message.lower() for rec in caplog.records)

    def test_root_takes_priority_over_legacy(
        self, tmp_path, temp_training_repo, monkeypatch, caplog
    ):
        repo, _, _ = temp_training_repo
        legacy = tmp_path / "legacy-repo"
        legacy.mkdir()
        (legacy / "workouts-history.md").touch()
        monkeypatch.setenv(ROOT_ENV, str(repo))
        monkeypatch.setenv(LEGACY_ROOT_ENV, str(legacy))
        with caplog.at_level(logging.WARNING, logger="magma_cycling.config.data_repo"):
            cfg = DataRepoConfig()
        assert cfg.root_path == repo.resolve()
        # Pas de warning quand ROOT prend priorité (même si LEGACY défini)
        assert not any("deprecated" in rec.message.lower() for rec in caplog.records)


class TestIsSafeWritePath:
    """Guard-rail write : legacy permissif, scoped strict + whitelist."""

    def _config_legacy(self, repo, monkeypatch):
        monkeypatch.setenv(ROOT_ENV, str(repo))
        return DataRepoConfig()

    def _config_scoped(self, repo, writer, monkeypatch):
        monkeypatch.setenv(ROOT_ENV, str(repo))
        monkeypatch.setenv(WRITER_SCOPED_ENV, "1")
        monkeypatch.setenv(WRITER_ID_ENV, writer)
        return DataRepoConfig()

    def test_legacy_allows_any_path_under_root(
        self, temp_training_repo, monkeypatch
    ):
        repo, _, _ = temp_training_repo
        cfg = self._config_legacy(repo, monkeypatch)
        # Tout sous root OK en legacy
        assert cfg.is_safe_write_path(repo / "workouts-history.md")
        assert cfg.is_safe_write_path(repo / "bilans" / "S091.md")
        assert cfg.is_safe_write_path(repo / "data" / "week_planning" / "S091.json")

    def test_legacy_refuses_path_outside_root(
        self, tmp_path, temp_training_repo, monkeypatch
    ):
        repo, _, _ = temp_training_repo
        cfg = self._config_legacy(repo, monkeypatch)
        outside = tmp_path / "elsewhere" / "leak.txt"
        assert cfg.is_safe_write_path(outside) is False

    def test_scoped_allows_under_writer_subdir(
        self, temp_training_repo, monkeypatch
    ):
        repo, writer_a, _ = temp_training_repo
        cfg = self._config_scoped(repo, writer_a, monkeypatch)
        assert cfg.is_safe_write_path(repo / writer_a / "workouts-history.md")
        assert cfg.is_safe_write_path(repo / writer_a / "bilans" / "S091.md")

    def test_scoped_refuses_other_writer_subdir(
        self, temp_training_repo, monkeypatch
    ):
        repo, writer_a, writer_b = temp_training_repo
        cfg = self._config_scoped(repo, writer_a, monkeypatch)
        # writer_b est un autre writer — refus de write
        assert cfg.is_safe_write_path(repo / writer_b / "leak.md") is False

    def test_scoped_refuses_root_write_outside_whitelist(
        self, temp_training_repo, monkeypatch
    ):
        repo, writer_a, _ = temp_training_repo
        cfg = self._config_scoped(repo, writer_a, monkeypatch)
        # Pas dans whitelist → refus
        assert cfg.is_safe_write_path(repo / "leak.md") is False
        assert cfg.is_safe_write_path(repo / "secret.txt") is False

    def test_scoped_allows_shared_root_files_whitelist(
        self, temp_training_repo, monkeypatch
    ):
        repo, writer_a, _ = temp_training_repo
        cfg = self._config_scoped(repo, writer_a, monkeypatch)
        # Dans whitelist (.operators.yaml::shared_root_files)
        assert cfg.is_safe_write_path(repo / ".gitignore")
        assert cfg.is_safe_write_path(repo / "README.md")
        assert cfg.is_safe_write_path(repo / OPERATORS_FILE)

    def test_scoped_allows_shared_root_dir_glob_pattern(
        self, temp_training_repo, monkeypatch
    ):
        """Pattern ``docs/architecture/**`` matche les fichiers sous ce dossier."""
        repo, writer_a, _ = temp_training_repo
        cfg = self._config_scoped(repo, writer_a, monkeypatch)
        assert cfg.is_safe_write_path(repo / "docs" / "architecture" / "x.md")

    def test_scoped_refuses_path_outside_root(
        self, tmp_path, temp_training_repo, monkeypatch
    ):
        repo, writer_a, _ = temp_training_repo
        cfg = self._config_scoped(repo, writer_a, monkeypatch)
        assert cfg.is_safe_write_path(tmp_path / "leak.txt") is False


class TestOperatorsYaml:
    """``.operators.yaml`` lazy-loaded, ``shared_root_files`` parsing."""

    def test_operators_yaml_loaded_when_present(
        self, temp_training_repo, monkeypatch
    ):
        repo, _, _ = temp_training_repo
        monkeypatch.setenv(ROOT_ENV, str(repo))
        cfg = DataRepoConfig()
        ops = cfg.operators_yaml
        assert ops is not None
        assert "writers" in ops
        assert "shared_root_files" in ops

    def test_operators_yaml_absent_returns_none(self, tmp_path, monkeypatch):
        bare = tmp_path / "bare-repo"
        bare.mkdir()
        (bare / "workouts-history.md").touch()
        monkeypatch.setenv(ROOT_ENV, str(bare))
        cfg = DataRepoConfig()
        assert cfg.operators_yaml is None

    def test_shared_root_files_from_yaml(self, temp_training_repo, monkeypatch):
        repo, _, _ = temp_training_repo
        monkeypatch.setenv(ROOT_ENV, str(repo))
        cfg = DataRepoConfig()
        whitelist = cfg.shared_root_files
        assert ".gitignore" in whitelist
        assert "README.md" in whitelist
        assert OPERATORS_FILE in whitelist

    def test_shared_root_files_default_when_yaml_absent(self, tmp_path, monkeypatch):
        bare = tmp_path / "bare-repo"
        bare.mkdir()
        (bare / "workouts-history.md").touch()
        monkeypatch.setenv(ROOT_ENV, str(bare))
        cfg = DataRepoConfig()
        whitelist = cfg.shared_root_files
        assert sorted(whitelist) == sorted(DEFAULT_SHARED_ROOT_FILES)
