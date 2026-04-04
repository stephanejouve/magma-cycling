"""Tests for magma_cycling.cli — CLI dispatcher."""

from unittest.mock import patch

import pytest

from magma_cycling import __version__
from magma_cycling.cli import (
    _check_env,
    _check_intervals,
    _status_icon,
    main,
)


def test_status_icon_ok():
    assert _status_icon(True) == "ok"


def test_status_icon_missing():
    assert _status_icon(False) == "--"


def test_check_env_missing(tmp_path):
    """When .env doesn't exist, returns False."""
    with patch("magma_cycling.cli.get_env_path", return_value=tmp_path / ".env"):
        ok, detail = _check_env()
        assert ok is False


def test_check_env_exists(tmp_path):
    """When .env exists, returns True."""
    env_file = tmp_path / ".env"
    env_file.write_text("SOME_VAR=value\n")
    with patch("magma_cycling.cli.get_env_path", return_value=env_file):
        ok, detail = _check_env()
        assert ok is True


def test_check_intervals_configured(tmp_path):
    """When .env has VITE_INTERVALS_ATHLETE_ID, returns True."""
    env_file = tmp_path / ".env"
    env_file.write_text("VITE_INTERVALS_ATHLETE_ID=i123456\n")
    with patch("magma_cycling.cli.get_env_path", return_value=env_file):
        ok, detail = _check_intervals()
        assert ok is True
        assert detail == "i123456"


def test_check_intervals_not_configured(tmp_path):
    """When .env has no athlete ID, returns False."""
    env_file = tmp_path / ".env"
    env_file.write_text("OTHER_VAR=value\n")
    with patch("magma_cycling.cli.get_env_path", return_value=env_file):
        ok, detail = _check_intervals()
        assert ok is False


def test_check_intervals_commented_out(tmp_path):
    """Commented-out athlete ID is not detected."""
    env_file = tmp_path / ".env"
    env_file.write_text("# VITE_INTERVALS_ATHLETE_ID=i123456\n")
    with patch("magma_cycling.cli.get_env_path", return_value=env_file):
        ok, _ = _check_intervals()
        assert ok is False


def test_main_no_args_calls_menu():
    """Without args, main() calls interactive_menu."""
    with (
        patch("sys.argv", ["magma-cycling"]),
        patch("magma_cycling.cli.interactive_menu") as mock_menu,
    ):
        main()
        mock_menu.assert_called_once()


def test_main_mcp_server():
    """'mcp-server' sub-command calls _run_mcp_server."""
    with (
        patch("sys.argv", ["magma-cycling", "mcp-server"]),
        patch("magma_cycling.cli._run_mcp_server") as mock_mcp,
    ):
        main()
        mock_mcp.assert_called_once()


def test_main_setup():
    """'setup' sub-command calls _run_setup."""
    with (
        patch("sys.argv", ["magma-cycling", "setup"]),
        patch("magma_cycling.cli._run_setup") as mock_setup,
    ):
        main()
        mock_setup.assert_called_once()


def test_main_version(capsys):
    """'--version' prints version and exits."""
    with patch("sys.argv", ["magma-cycling", "--version"]), pytest.raises(SystemExit):
        main()
    captured = capsys.readouterr()
    assert __version__ in captured.out
