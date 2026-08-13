"""BT-027 / ADR v5 §7 — upgrade path beta-testeurs training-logs.

Migre un repo ``training-logs`` en layout flat legacy vers le layout
writer-scoped Phase 2 :

1. Provisionne un writer (hash 12-char + entrée ``.operators.yaml``) via
   :func:`magma_cycling.scripts.provision_writer.provision_writer` sans
   commit (composé dans le commit atomique final).
2. ``git mv`` tous les fichiers/dossiers en racine hors whitelist +
   hors ``.git`` vers le subdir writer.
3. Commit atomique unique.
4. Push best-effort (rollback via ``git reset --hard HEAD~1`` si le push
   n'a pas encore été répliqué sur origin).

Invocation nominale via CLI setup :

    poetry run setup --migrate-training-logs

Optionnels :

    --alias <name>       # défaut = hostname
    --dry-run            # compter sans écrire
    --no-push            # pas de git push après le commit

Contexte : conçu pour les beta-testeurs qui ont un clone historique de
``training-logs`` en layout flat (pré-Phase 1). Le code refuse de tourner
en mode writer-scoped tant que la migration n'a pas eu lieu (cf.
:class:`LegacyLayoutError` dans :mod:`magma_cycling.config.data_repo`).
"""

from __future__ import annotations

import argparse
import logging
import socket
import subprocess
import sys
from pathlib import Path

from magma_cycling.config.data_repo import (
    LegacyLayoutError,
    _resolve_root_from_env,
    _root_files_outside_whitelist,
    detect_legacy_layout,
)

logger = logging.getLogger(__name__)


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Wrapper subprocess.run pour git, capture stdout+stderr, no-check."""
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=60)


def _default_alias() -> str:
    """Alias par défaut = hostname (short form)."""
    host = socket.gethostname()
    # Trim domain suffix si présent (ex. "tiresias.local" → "tiresias")
    return host.split(".")[0] or "local"


def migrate_training_logs(
    root: Path,
    *,
    alias: str | None = None,
    dry_run: bool = False,
    push: bool = True,
) -> dict:
    """Migre un repo training-logs legacy vers le layout writer-scoped.

    Args:
        root: Path racine du repo training-logs.
        alias: Alias du writer local (default = hostname sans domaine).
        dry_run: Si ``True``, log le plan de migration sans écrire.
        push: Si ``True``, push le commit atomique après. ``False`` pour
            environnements offline ou tests. Ignoré si ``dry_run=True``.

    Returns:
        Dict avec :
        - ``writer_hash``: hash 12-char du writer provisionné (ou None en dry_run)
        - ``alias``: alias effectif utilisé
        - ``moved_items``: liste des items déplacés vers ``<hash>/``
        - ``commit_sha``: SHA du commit atomique (ou None en dry_run / no-op)
        - ``pushed``: bool
        - ``rollback_hint``: str, commande git reset pour rollback

    Raises:
        FileNotFoundError: si ``root`` n'existe pas ou n'est pas un git repo.
        RuntimeError: si le repo n'est PAS en layout legacy (rien à migrer,
            ou déjà migré).
        RuntimeError: sur échec git (add, mv, commit).
    """
    # Validation early
    if not root.is_dir():
        raise FileNotFoundError(f"Training-logs root does not exist: {root}")
    if not (root / ".git").is_dir():
        raise FileNotFoundError(f"{root} is not a git repository — init it with `git init` first")
    if not detect_legacy_layout(root):
        raise RuntimeError(
            f"{root} is NOT in legacy layout (either already migrated, or empty).\n"
            f"Nothing to migrate. If you want to provision a first writer on a "
            f"fresh repo, use: poetry run provision-writer <alias>"
        )

    effective_alias = alias or _default_alias()
    items_to_move = _root_files_outside_whitelist(root)

    logger.info("Migration plan: alias=%s, %d items to move", effective_alias, len(items_to_move))
    for item in items_to_move:
        logger.info("  → will move: %s", item)

    if dry_run:
        logger.info("[DRY RUN] no writes")
        return {
            "writer_hash": None,
            "alias": effective_alias,
            "moved_items": items_to_move,
            "commit_sha": None,
            "pushed": False,
            "rollback_hint": "N/A (dry-run)",
        }

    # 1. Provisionne le writer sans commit (composé dans le commit atomique final)
    from magma_cycling.scripts.provision_writer import provision_writer

    writer_hash = provision_writer(effective_alias, root, push=False, commit=False)
    logger.info("Writer provisioned (uncommitted): hash=%s alias=%s", writer_hash, effective_alias)

    # 2. git mv des items legacy vers le subdir writer
    for item in items_to_move:
        src = root / item
        dst = root / writer_hash / item
        # git mv gère à la fois file + dir. Refuse si target existe déjà.
        mv = _git(["mv", str(src.relative_to(root)), str(dst.relative_to(root))], cwd=root)
        if mv.returncode != 0:
            raise RuntimeError(
                f"git mv failed for {item}: {mv.stderr.strip()}\n"
                f"Repo state may be partially staged — inspect with `git status` "
                f"and reset with `git reset --hard HEAD` if needed."
            )
        logger.info("  git mv %s → %s/", item, writer_hash)

    # 3. Commit atomique unique
    commit_msg = (
        f"[migrate] training-logs: flat → writer {effective_alias}/{writer_hash}\n\n"
        f"BT-027 / ADR v5 §7 upgrade path. Provisioned writer + moved "
        f"{len(items_to_move)} legacy items to subdir."
    )
    commit = _git(["commit", "-m", commit_msg], cwd=root)
    if commit.returncode != 0:
        raise RuntimeError(f"git commit failed: {commit.stderr.strip()}")

    # Récupère le SHA du commit qu'on vient de faire
    sha_res = _git(["rev-parse", "HEAD"], cwd=root)
    commit_sha = sha_res.stdout.strip() if sha_res.returncode == 0 else "unknown"

    logger.info("Committed migration: %s", commit_sha[:12])

    # 4. Push best-effort
    pushed = False
    if push:
        push_res = _git(["push", "origin", "HEAD"], cwd=root)
        if push_res.returncode == 0:
            pushed = True
            logger.info("Pushed to origin/HEAD")
        else:
            logger.warning(
                "git push failed (migration committed locally only, retry later): %s",
                push_res.stderr.strip(),
            )

    rollback_hint = (
        f"git -C {root} reset --hard HEAD~1"
        if not pushed
        else f"git -C {root} revert {commit_sha[:12]}  # (push already replicated to origin)"
    )
    logger.info("Rollback command (if needed): %s", rollback_hint)

    return {
        "writer_hash": writer_hash,
        "alias": effective_alias,
        "moved_items": items_to_move,
        "commit_sha": commit_sha,
        "pushed": pushed,
        "rollback_hint": rollback_hint,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point pour la migration training-logs.

    Invoqué via ``poetry run setup --migrate-training-logs`` (voie
    documentée ADR §7.3) ou directement
    ``python -m magma_cycling.scripts.migrate_training_logs``.
    """
    parser = argparse.ArgumentParser(
        prog="migrate-training-logs",
        description="Migre un repo training-logs legacy vers le layout writer-scoped ADR v5.",
    )
    parser.add_argument(
        "--root",
        type=str,
        default=None,
        help="Path racine du repo training-logs (default: TRAINING_DATA_ROOT env var).",
    )
    parser.add_argument(
        "--alias",
        type=str,
        default=None,
        help="Alias du writer local (default: hostname sans domaine).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log le plan de migration sans écrire.",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Ne pas git push après le commit atomique.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.root:
        root = Path(args.root).expanduser().resolve()
    else:
        env_root = _resolve_root_from_env()
        if env_root is None:
            print(
                "Error: --root not provided and TRAINING_DATA_ROOT env var not set.",
                file=sys.stderr,
            )
            return 1
        root = env_root

    print(f"📁 training-logs root: {root}", file=sys.stderr)

    try:
        result = migrate_training_logs(
            root, alias=args.alias, dry_run=args.dry_run, push=not args.no_push
        )
    except (FileNotFoundError, RuntimeError, LegacyLayoutError) as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(
            f"✅ [DRY RUN] would migrate {len(result['moved_items'])} items → "
            f"writer alias={result['alias']}",
            file=sys.stderr,
        )
    else:
        print(
            f"✅ Migration complete — writer {result['alias']}/{result['writer_hash']}, "
            f"{len(result['moved_items'])} items moved, "
            f"pushed={result['pushed']}",
            file=sys.stderr,
        )
        print(f"   Rollback: {result['rollback_hint']}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
