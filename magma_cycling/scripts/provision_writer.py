"""Provision a new writer for the training-logs repo (ADR v5 Phase 2).

Calcule un hash 12-char opaque depuis ``sha256("<timestamp_utc_z>#<alias>")``,
ajoute l'entrée dans ``.operators.yaml`` à la racine du repo, crée la subdir
correspondante, commit + push.

Usage scriptable (CI, setup_wizard) ::

    poetry run provision-writer mac
    poetry run provision-writer nas-prod --root ~/training-logs

Usage interactif (humain) ::

    poetry run provision-writer --interactive
    # → prompt l'alias, default = hostname

Format strict du timestamp : ISO 8601 UTC avec suffixe ``Z`` (pas d'offset
local, secondes sans fraction). Garantit la reproductibilité du hash si un
provisioning doit être rejoué.

Sortie sur stdout : le hash 12-char (pour scriptability — pipe-friendly).
Logs INFO + diagnostics sur stderr.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from magma_cycling.config.data_repo import (
    DEFAULT_SHARED_ROOT_FILES,
    OPERATORS_FILE,
    _resolve_root_from_env,
)

logger = logging.getLogger(__name__)


def _utc_timestamp_z() -> str:
    """Génère un timestamp UTC strict ISO 8601 avec suffixe ``Z``.

    Format exigé par l'ADR v5 (lignes 60-62) : pas d'offset local, secondes
    sans fraction. Reproductible.
    """
    now = datetime.now(timezone.utc)
    return now.isoformat(timespec="seconds").replace("+00:00", "Z")


def _compute_writer_hash(timestamp: str, alias: str) -> str:
    """Calcule le hash 12-char depuis ``timestamp#alias``.

    Args:
        timestamp: ISO 8601 UTC strict avec suffixe ``Z``.
        alias: Nom court humain (ex. ``mac``, ``nas-prod``).

    Returns:
        Premiers 12 hex chars du SHA256.
    """
    payload = f"{timestamp}#{alias}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]


def _load_or_init_operators(yaml_path: Path) -> dict:
    """Lit ``.operators.yaml`` ou initialise un squelette par défaut."""
    if yaml_path.is_file():
        with yaml_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        if not isinstance(data, dict):
            raise RuntimeError(
                f"{yaml_path} ne contient pas un mapping YAML valide"
            )
        data.setdefault("shared_root_files", list(DEFAULT_SHARED_ROOT_FILES))
        data.setdefault("writers", {})
        return data
    return {
        "shared_root_files": list(DEFAULT_SHARED_ROOT_FILES),
        "writers": {},
    }


def _write_operators(yaml_path: Path, data: dict) -> None:
    """Écrit ``.operators.yaml`` (atomic via tmp + rename, format YAML lisible)."""
    tmp = yaml_path.with_suffix(yaml_path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, default_flow_style=False, sort_keys=False)
    tmp.replace(yaml_path)


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Wrapper subprocess.run pour git, avec capture + check OFF (caller decide)."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def provision_writer(
    alias: str,
    root: Path,
    *,
    host: str | None = None,
    push: bool = True,
) -> str:
    """Provisionne un writer dans le repo training-logs.

    Args:
        alias: Nom court humain du writer (ex. ``mac``, ``nas-prod``).
        root: Path racine du repo training-logs.
        host: Hostname de la machine (default = socket.gethostname()).
        push: Si ``True``, ``git push origin main`` après commit. ``False``
            pour les tests locaux ou setups offline.

    Returns:
        Le hash 12-char du writer provisionné.

    Raises:
        FileNotFoundError: si ``root`` n'existe pas ou n'est pas un git repo.
        RuntimeError: si l'alias est déjà présent dans ``.operators.yaml``.
    """
    if not root.is_dir():
        raise FileNotFoundError(f"Root path does not exist: {root}")
    if not (root / ".git").is_dir():
        raise FileNotFoundError(
            f"{root} is not a git repository — initialize with `git init` first"
        )

    timestamp = _utc_timestamp_z()
    writer_hash = _compute_writer_hash(timestamp, alias)
    host = host or socket.gethostname()

    yaml_path = root / OPERATORS_FILE
    operators = _load_or_init_operators(yaml_path)

    # Refus si l'alias existe déjà (active) — éviter écrasement silencieux
    for existing_hash, meta in (operators.get("writers") or {}).items():
        if not isinstance(meta, dict):
            continue
        if (
            meta.get("alias") == alias
            and meta.get("decommissioned_at") in (None, "", "null")
        ):
            raise RuntimeError(
                f"Writer alias {alias!r} already provisioned and active "
                f"(hash={existing_hash}). Decommission it first or pick a different alias."
            )

    operators.setdefault("writers", {})[writer_hash] = {
        "alias": alias,
        "host": host,
        "provisioned_at": timestamp,
        "decommissioned_at": None,
    }

    _write_operators(yaml_path, operators)

    subdir = root / writer_hash
    subdir.mkdir(parents=True, exist_ok=True)
    # Garde-le présent dans git via un .gitkeep (sinon le subdir vide
    # n'apparaît pas — git ignore les dossiers vides). Créé seulement si
    # le subdir est vide pour ne pas masquer un usage existant.
    if not any(subdir.iterdir()):
        (subdir / ".gitkeep").touch()

    msg = (
        f"chore(training-logs): provision writer {alias} ({writer_hash})\n\n"
        f"timestamp_utc: {timestamp}\nhost: {host}\n"
    )
    add = _git(["add", OPERATORS_FILE, writer_hash], cwd=root)
    if add.returncode != 0:
        raise RuntimeError(f"git add failed: {add.stderr.strip()}")
    commit = _git(["commit", "-m", msg], cwd=root)
    if commit.returncode != 0:
        raise RuntimeError(f"git commit failed: {commit.stderr.strip()}")

    if push:
        push_res = _git(["push", "origin", "HEAD"], cwd=root)
        if push_res.returncode != 0:
            logger.warning(
                "git push failed (writer provisioned locally only): %s",
                push_res.stderr.strip(),
            )

    print(
        f"Writer provisioned: alias={alias} hash={writer_hash} "
        f"host={host} timestamp={timestamp}",
        file=sys.stderr,
    )
    return writer_hash


def _resolve_root_or_exit(arg_root: str | None) -> Path:
    """Résolve le root depuis arg CLI ou env var, exit si introuvable."""
    if arg_root:
        return Path(arg_root).expanduser().resolve()
    env_root = _resolve_root_from_env()
    if env_root is None:
        print(
            "Error: --root not provided and TRAINING_DATA_ROOT (or "
            "TRAINING_DATA_REPO) env var not set.",
            file=sys.stderr,
        )
        sys.exit(1)
    return env_root.resolve()


def main() -> int:
    """Entry point CLI ``provision-writer``."""
    parser = argparse.ArgumentParser(
        prog="provision-writer",
        description="Provision a new training-logs writer (ADR v5 Phase 2).",
    )
    parser.add_argument(
        "alias",
        nargs="?",
        help="Writer alias (e.g. mac, nas-prod). Required unless --interactive.",
    )
    parser.add_argument(
        "--root",
        help="Override the training-logs repo root (default: env var).",
    )
    parser.add_argument(
        "--host",
        help="Hostname to record (default: socket.gethostname()).",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Skip git push origin (commit local only).",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for alias if not provided in argv.",
    )
    args = parser.parse_args()

    alias = args.alias
    if not alias:
        if not args.interactive:
            print(
                "Error: alias required. Pass as positional argv or use --interactive.",
                file=sys.stderr,
            )
            return 1
        default = socket.gethostname() or "local"
        try:
            alias = input(f"Writer alias [{default}]: ").strip() or default
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.", file=sys.stderr)
            return 1

    root = _resolve_root_or_exit(args.root)

    try:
        writer_hash = provision_writer(
            alias,
            root,
            host=args.host,
            push=not args.no_push,
        )
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Hash sur stdout pour scriptability (eval `provision-writer mac`)
    print(writer_hash)
    return 0


if __name__ == "__main__":
    sys.exit(main())
