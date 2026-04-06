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


def get_install_dir() -> Path:
    """Return the recommended permanent install directory for the .exe."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path.home() / ".local" / "bin"
    return base / "magma-cycling"


def is_in_temporary_location() -> bool:
    """Check if the .exe runs from Downloads, Temp, or Desktop."""
    if not is_bundled():
        return False
    exe_str = str(Path(sys.executable).resolve()).lower()
    return any(m in exe_str for m in ("downloads", "temp", "tmp", "desktop", "bureau"))


def auto_install_exe() -> bool:
    """Copy the .exe to a permanent location and relaunch.

    Returns True if relaunched (caller should exit), False if skipped.
    """
    import shutil
    import subprocess

    install_dir = get_install_dir()
    if sys.platform == "win32":
        target = install_dir / "magma-cycling.exe"
    else:
        target = install_dir / "magma-cycling"

    print("  Le programme tourne depuis un emplacement temporaire.")
    print(f"  Installation recommandee : {target}")
    print()

    try:
        answer = input("  Installer a cet emplacement ? (O/n) : ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False

    if answer not in ("", "o", "oui", "y", "yes"):
        return False

    install_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sys.executable, target)
    print(f"  Copie vers {target}")

    if os.name == "nt":
        print("  Redemarrage...")
        subprocess.Popen([str(target)], creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        print()
        print("  Pour lancer le programme, copie-colle dans le Terminal :")
        print(f"  {target}")
        print()

    return True
