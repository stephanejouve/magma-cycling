"""CLI dispatcher for magma-cycling.

Provides an interactive menu when launched without arguments (double-click .exe),
and routes sub-commands (mcp-server, setup) for programmatic usage.

Usage:
    magma-cycling.exe                -> interactive menu + dashboard
    magma-cycling.exe mcp-server     -> MCP server (for Claude Desktop)
    magma-cycling.exe setup          -> configuration wizard
    magma-cycling.exe --version      -> print version
"""

import argparse
import json
import os
from pathlib import Path

from magma_cycling import __version__
from magma_cycling.paths import get_env_path, get_user_config_dir

# ---------------------------------------------------------------------------
# Dashboard helpers
# ---------------------------------------------------------------------------


def _check_env() -> tuple[bool, str]:
    """Check if .env file exists."""
    env_path = get_env_path()
    if env_path.exists():
        return True, str(env_path)
    return False, str(env_path)


def _check_intervals() -> tuple[bool, str]:
    """Check if Intervals.icu is configured in .env."""
    env_path = get_env_path()
    if not env_path.exists():
        return False, ""
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("VITE_INTERVALS_ATHLETE_ID=") and not stripped.startswith("#"):
                value = stripped.split("=", 1)[1].strip()
                if value:
                    return True, value
    except OSError:
        pass
    return False, ""


def _check_withings() -> tuple[bool, str]:
    """Check if Withings credentials exist."""
    config_dir = get_user_config_dir()
    # In dev mode, check project root; in bundle, check user config dir
    candidates = [
        config_dir / ".withings_credentials.json",
        Path.home() / ".withings_credentials.json",
    ]
    for p in candidates:
        if p.exists():
            return True, str(p)
    return False, ""


def _check_data_repo() -> tuple[bool, str]:
    """Check if training-logs directory exists."""
    # Check env var first
    env_repo = os.getenv("TRAINING_DATA_REPO")
    if env_repo:
        p = Path(env_repo).expanduser()
        if p.exists():
            return True, str(p)
    default = Path.home() / "training-logs"
    if default.exists():
        return True, str(default)
    return False, str(default)


def _check_claude_desktop() -> tuple[bool, str]:
    """Check if Claude Desktop config directory exists."""
    candidates = [
        Path.home() / "AppData" / "Roaming" / "Claude",  # Windows
        Path.home() / "Library" / "Application Support" / "Claude",  # macOS
        Path.home() / ".config" / "claude",  # Linux
    ]
    for p in candidates:
        if p.exists():
            return True, str(p)
    return False, ""


def _check_mcp_registered() -> tuple[bool, str]:
    """Check if magma-cycling is registered in Claude Desktop config.

    SECURITY: only checks for the 'magma-cycling' key existence.
    Never reads or displays other keys/tokens.
    """
    config_candidates = [
        Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",
        Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
        Path.home() / ".config" / "claude" / "claude_desktop_config.json",
    ]
    for config_path in config_candidates:
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text(encoding="utf-8"))
                servers = data.get("mcpServers", {})
                if "magma-cycling" in servers:
                    return True, "magma-cycling"
            except (json.JSONDecodeError, OSError):
                pass
    return False, ""


# ---------------------------------------------------------------------------
# Dashboard display
# ---------------------------------------------------------------------------


def _status_icon(ok: bool) -> str:
    """Return a text status indicator."""
    return "ok" if ok else "--"


def print_dashboard():
    """Print configuration and connection status dashboard."""
    env_ok, env_detail = _check_env()
    int_ok, int_detail = _check_intervals()
    with_ok, _ = _check_withings()
    data_ok, data_detail = _check_data_repo()
    claude_ok, _ = _check_claude_desktop()
    mcp_ok, _ = _check_mcp_registered()

    print(f"\n  magma-cycling v{__version__}")
    print()
    print("  Configuration")
    print(f"    {_status_icon(env_ok)} .env {'trouve' if env_ok else 'non trouve'}")
    if int_ok:
        print(f"    {_status_icon(int_ok)} Intervals.icu configure (athlete: {int_detail})")
    else:
        print(f"    {_status_icon(int_ok)} Intervals.icu non configure")
    if with_ok:
        print(f"    {_status_icon(with_ok)} Withings configure")
    else:
        print(f"    {_status_icon(with_ok)} Withings non configure")
    print(
        f"    {_status_icon(data_ok)} Espace donnees "
        f"{'~/' + Path(data_detail).name if data_ok else 'non trouve'}"
    )
    print()
    print("  Connexion IA")
    print(
        f"    {_status_icon(claude_ok)} Claude Desktop "
        f"{'detecte' if claude_ok else 'non detecte'}"
    )
    print(
        f"    {_status_icon(mcp_ok)} MCP magma-cycling "
        f"{'enregistre' if mcp_ok else 'non enregistre'}"
    )
    print()


# ---------------------------------------------------------------------------
# Interactive menu
# ---------------------------------------------------------------------------


def interactive_menu():
    """Display dashboard and action menu."""
    import sys

    from magma_cycling.paths import auto_install_exe, is_bundled, is_in_temporary_location

    print_dashboard()

    if is_bundled() and is_in_temporary_location():
        if auto_install_exe():
            sys.exit(0)

    print("  Actions :")
    print("    1. Lancer le setup (configuration)")
    print("    2. Demarrer le serveur MCP")
    print("    3. Quitter")
    print()

    while True:
        try:
            choice = input("  Choix [1-3] : ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if choice == "1":
            _run_setup()
            break
        elif choice == "2":
            _run_mcp_server()
            break
        elif choice == "3":
            break
        else:
            print("  Choix invalide, tape 1, 2 ou 3.")


def _run_setup():
    """Launch the setup wizard."""
    from magma_cycling.scripts.setup_wizard import main as setup_main

    setup_main()


def _run_mcp_server():
    """Launch the MCP server."""
    import sys

    print("  Demarrage du serveur MCP... (en attente de connexion)", file=sys.stderr)
    print("  Ctrl+C pour arreter.\n", file=sys.stderr)
    from magma_cycling.mcp_server import main as mcp_main

    mcp_main()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    """CLI entry point — dispatcher."""
    parser = argparse.ArgumentParser(
        prog="magma-cycling",
        description="magma-cycling — coach IA cyclisme",
    )
    parser.add_argument("--version", action="version", version=f"magma-cycling {__version__}")

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("mcp-server", help="Demarrer le serveur MCP")
    subparsers.add_parser("setup", help="Lancer l'assistant de configuration")

    args = parser.parse_args()

    if args.command is None:
        interactive_menu()
    elif args.command == "mcp-server":
        _run_mcp_server()
    elif args.command == "setup":
        _run_setup()


if __name__ == "__main__":
    main()
