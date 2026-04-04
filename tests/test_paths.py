"""Tests for magma_cycling.paths — path resolution in dev vs bundle mode."""

import sys
from pathlib import Path
from unittest.mock import patch

from magma_cycling.paths import (
    get_athlete_yaml_path,
    get_bundle_data_dir,
    get_env_path,
    get_user_config_dir,
    is_bundled,
)


def test_is_bundled_false_in_dev():
    """In dev mode, is_bundled() returns False."""
    assert is_bundled() is False


def test_get_user_config_dir_dev():
    """In dev mode, returns project root."""
    config_dir = get_user_config_dir()
    # Should be the project root (parent of magma_cycling package)
    assert (config_dir / "magma_cycling").is_dir()


def test_get_env_path_dev():
    """In dev mode, .env is at project root."""
    env_path = get_env_path()
    assert env_path.name == ".env"
    assert (env_path.parent / "magma_cycling").is_dir()


def test_get_athlete_yaml_path_dev():
    """In dev mode, athlete_context.yaml is at project root."""
    yaml_path = get_athlete_yaml_path()
    assert yaml_path.name == "athlete_context.yaml"


def test_get_bundle_data_dir_none_in_dev():
    """In dev mode, returns None."""
    assert get_bundle_data_dir() is None


def test_is_bundled_true_with_meipass():
    """When sys._MEIPASS exists, is_bundled() returns True."""
    with patch.object(sys, "_MEIPASS", "/tmp/meipass", create=True):
        assert is_bundled() is True


def test_get_user_config_dir_bundled_windows():
    """In bundled mode on Windows, uses LOCALAPPDATA."""
    with (
        patch.object(sys, "_MEIPASS", "/tmp/meipass", create=True),
        patch.object(sys, "platform", "win32"),
        patch.dict("os.environ", {"LOCALAPPDATA": "C:\\Users\\Test\\AppData\\Local"}),
    ):
        config_dir = get_user_config_dir()
        # Compare parts to handle PosixPath on macOS test runners
        assert config_dir.name == "magma-cycling"
        assert "AppData" in str(config_dir)


def test_get_user_config_dir_bundled_unix():
    """In bundled mode on Unix, uses ~/.config/magma-cycling."""
    with (
        patch.object(sys, "_MEIPASS", "/tmp/meipass", create=True),
        patch.object(sys, "platform", "linux"),
    ):
        config_dir = get_user_config_dir()
        assert config_dir == Path.home() / ".config" / "magma-cycling"


def test_get_bundle_data_dir_with_meipass():
    """When sys._MEIPASS exists, returns that path."""
    with patch.object(sys, "_MEIPASS", "/tmp/meipass", create=True):
        result = get_bundle_data_dir()
        assert result == Path("/tmp/meipass")
