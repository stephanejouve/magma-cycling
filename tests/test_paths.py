"""Tests for magma_cycling.paths — path resolution in dev vs bundle mode."""

import sys
from pathlib import Path
from unittest.mock import patch

from magma_cycling.paths import (
    get_athlete_yaml_path,
    get_bundle_data_dir,
    get_env_path,
    get_install_dir,
    get_user_config_dir,
    is_bundled,
    is_in_temporary_location,
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


# ---------------------------------------------------------------------------
# get_install_dir
# ---------------------------------------------------------------------------


def test_get_install_dir_windows():
    """On Windows, uses LOCALAPPDATA."""
    with (
        patch.object(sys, "platform", "win32"),
        patch.dict("os.environ", {"LOCALAPPDATA": r"C:\Users\Test\AppData\Local"}),
    ):
        result = get_install_dir()
        assert result.name == "magma-cycling"
        assert "AppData" in str(result)


def test_get_install_dir_unix():
    """On Unix, uses ~/.local/bin/magma-cycling."""
    with patch.object(sys, "platform", "linux"):
        result = get_install_dir()
        assert result == Path.home() / ".local" / "bin" / "magma-cycling"


# ---------------------------------------------------------------------------
# is_in_temporary_location
# ---------------------------------------------------------------------------


def test_is_in_temporary_location_dev_mode():
    """In dev mode (not bundled), always returns False."""
    assert is_in_temporary_location() is False


def test_is_in_temporary_location_downloads(monkeypatch):
    """Detects Downloads folder as temporary."""
    monkeypatch.setattr(sys, "executable", r"C:\Users\steph\Downloads\magma.exe")
    monkeypatch.setattr("magma_cycling.paths.is_bundled", lambda: True)
    assert is_in_temporary_location() is True


def test_is_in_temporary_location_permanent(monkeypatch):
    """Permanent install path is not temporary."""
    monkeypatch.setattr(sys, "executable", r"C:\Users\steph\AppData\Local\magma-cycling\magma.exe")
    monkeypatch.setattr("magma_cycling.paths.is_bundled", lambda: True)
    assert is_in_temporary_location() is False


def test_is_in_temporary_location_bureau_fr(monkeypatch):
    """Detects French 'Bureau' (Desktop) as temporary."""
    monkeypatch.setattr(sys, "executable", r"C:\Users\steph\Bureau\magma.exe")
    monkeypatch.setattr("magma_cycling.paths.is_bundled", lambda: True)
    assert is_in_temporary_location() is True


def test_is_in_temporary_location_temp(monkeypatch):
    """Detects Temp folder as temporary."""
    monkeypatch.setattr(sys, "executable", r"C:\Users\steph\AppData\Local\Temp\magma.exe")
    monkeypatch.setattr("magma_cycling.paths.is_bundled", lambda: True)
    assert is_in_temporary_location() is True
