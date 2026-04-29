"""Tests for startup_health_check (INFRA-001)."""

import logging
import sys

import pytest

from magma_cycling.config.data_repo import (
    _git_head_short,
    reset_data_config,
    startup_health_check,
)


@pytest.fixture
def valid_repo(tmp_path, monkeypatch):
    """Repo data valide minimal : workouts-history.md à la racine."""
    repo = tmp_path / "training-logs"
    repo.mkdir()
    (repo / "workouts-history.md").write_text("# History\n")
    monkeypatch.setenv("TRAINING_DATA_REPO", str(repo))
    reset_data_config()
    yield repo
    reset_data_config()


class TestStartupHealthCheck:
    """Fail-fast au boot si TRAINING_DATA_REPO invalide."""

    def test_passes_with_valid_repo(self, valid_repo, caplog):
        with caplog.at_level(logging.INFO, logger="magma_cycling.config.data_repo"):
            cfg = startup_health_check()
        assert cfg.data_repo_path == valid_repo.resolve()
        # Log INFO contient path + taille + head_sha placeholder
        assert any("data_repo_health_ok" in r.message for r in caplog.records)

    def test_fails_when_repo_dir_missing(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("TRAINING_DATA_REPO", str(tmp_path / "nonexistent"))
        reset_data_config()
        with pytest.raises(SystemExit) as exc:
            startup_health_check()
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "FATAL: training data repo invalid" in err

    def test_fails_when_workouts_history_missing(self, tmp_path, monkeypatch, capsys):
        repo = tmp_path / "training-logs"
        repo.mkdir()
        # Pas de workouts-history.md créé
        monkeypatch.setenv("TRAINING_DATA_REPO", str(repo))
        reset_data_config()
        with pytest.raises(SystemExit) as exc:
            startup_health_check()
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "FATAL" in err and "workouts-history.md" in err

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="POSIX chmod 0o000 doesn't translate to a read-blocking ACL on "
        "Windows; the readability check there is exercised through the "
        "FileNotFoundError and PermissionError paths covered above.",
    )
    def test_fails_when_workouts_history_unreadable(self, valid_repo, capsys):
        # chmod 000 → unreadable
        history = valid_repo / "workouts-history.md"
        history.chmod(0o000)
        try:
            with pytest.raises(SystemExit) as exc:
                startup_health_check()
            assert exc.value.code == 1
            err = capsys.readouterr().err
            assert "FATAL" in err
        finally:
            # Restaure pour cleanup pytest
            history.chmod(0o644)


class TestSkipEnvVar:
    """`MCP_SKIP_STARTUP_HEALTH_CHECK=1` bypasses the check entirely.

    Used by the PyInstaller smoke tests on CI runners that have no
    `~/training-logs/` repo. Production deployments must not set it.
    """

    def test_skip_env_returns_none_without_validation(self, tmp_path, monkeypatch, caplog):
        # No TRAINING_DATA_REPO set, no repo on disk — would normally fail
        monkeypatch.setenv("MCP_SKIP_STARTUP_HEALTH_CHECK", "1")
        monkeypatch.delenv("TRAINING_DATA_REPO", raising=False)
        reset_data_config()
        with caplog.at_level(logging.WARNING, logger="magma_cycling.config.data_repo"):
            result = startup_health_check()
        assert result is None
        assert any("data_repo_health_skipped" in r.message for r in caplog.records)

    def test_skip_env_false_value_does_not_skip(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("MCP_SKIP_STARTUP_HEALTH_CHECK", "0")
        monkeypatch.setenv("TRAINING_DATA_REPO", str(tmp_path / "nonexistent"))
        reset_data_config()
        with pytest.raises(SystemExit):
            startup_health_check()


class TestGitHeadShort:
    def test_returns_none_for_non_git_dir(self, tmp_path):
        assert _git_head_short(tmp_path) is None

    def test_returns_short_sha_for_git_repo(self, tmp_path):
        import subprocess

        subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.email=t@t",
                "-c",
                "user.name=T",
                "commit",
                "--allow-empty",
                "-m",
                "init",
                "--quiet",
            ],
            cwd=tmp_path,
            check=True,
        )
        sha = _git_head_short(tmp_path)
        assert sha is not None
        assert len(sha) == 12
        assert all(c in "0123456789abcdef" for c in sha)
