"""Path resolution for bundled (PyInstaller) vs development environments.

Stdlib only — no external dependencies.
"""

import os
import sys
from pathlib import Path

# Project root in dev mode (3 levels up from this file is not reliable,
# use the parent of magma_cycling package)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def is_bundled() -> bool:
    """Return True if running inside a PyInstaller bundle."""
    return hasattr(sys, "_MEIPASS")


def get_user_config_dir() -> Path:
    """Return the user-writable config directory.

    - Bundled Windows: %LOCALAPPDATA%/magma-cycling
    - Bundled Unix: ~/.config/magma-cycling
    - Dev mode: project root
    """
    if not is_bundled():
        return _PROJECT_ROOT

    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path.home() / ".config"

    return base / "magma-cycling"


def get_env_path() -> Path:
    """Return path to the .env file."""
    return get_user_config_dir() / ".env"


def get_athlete_yaml_path() -> Path:
    """Return path to athlete_context.yaml."""
    return get_user_config_dir() / "athlete_context.yaml"


def get_bundle_data_dir() -> Path | None:
    """Return PyInstaller _MEIPASS directory, or None in dev mode."""
    if is_bundled():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return None
