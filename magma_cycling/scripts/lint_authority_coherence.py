"""Lint authority coherence between ``.operators.yaml`` and the actual
training-logs repo state (ADR v5 Phase 2).

Vérifications :

1. Toute entrée ``writers[<hash>]`` dans ``.operators.yaml`` a son subdir
   correspondant à la racine du repo.
2. Tout subdir nommé en hex 12-char (forme writer_hash) à la racine est
   déclaré dans ``writers``.
3. Tout fichier/dir à la racine du repo est soit dans la whitelist
   ``shared_root_files``, soit dans un subdir writer enregistré.
4. Tout subdir d'un writer marqué ``decommissioned_at != null`` qui contient
   encore des fichiers tracked → WARN (devrait être archivé/purgé).

Usage ::

    poetry run lint-authority-coherence [PATH]
    poetry run lint-authority-coherence --self-test

Si ``PATH`` absent, fallback sur ``TRAINING_DATA_ROOT`` env var.
``--self-test`` exécute un check minimaliste (instantiation OK) sans
dépendre d'un repo training-logs réel — utile en CI.

Output : violations sur stdout au format GitHub Actions ``::warning ::``.
Exit code TOUJOURS 0 (WARN-only pendant la transition ADR v5 ; le passage
en fail-PR sera décidé après stabilisation, cf. ADR v5 §4).
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from magma_cycling.config.data_repo import (
    DEFAULT_SHARED_ROOT_FILES,
    OPERATORS_FILE,
    _resolve_root_from_env,
)

WRITER_HASH_RE = re.compile(r"^[0-9a-f]{12}$")


@dataclass(frozen=True)
class Violation:
    """Une violation de cohérence détectée par le linter."""

    code: str
    message: str

    def format_gha(self) -> str:
        """Format GitHub Actions ``::warning title=<code>::<message>``."""
        return f"::warning title={self.code}::{self.message}"

    def format_plain(self) -> str:
        """Format plain text (non-CI)."""
        return f"[{self.code}] {self.message}"


def _load_yaml(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        return {"__parse_error__": str(exc)}
    if not isinstance(data, dict):
        return {"__parse_error__": "root is not a mapping"}
    return data


def _whitelist_matches(rel: str, entry: str) -> bool:
    """``True`` si ``rel`` matche une entrée whitelist (exact ou prefix dir)."""
    cleaned = entry.rstrip("/").rstrip("*").rstrip("/")
    if rel == entry or rel == cleaned:
        return True
    if cleaned and rel.startswith(cleaned + "/"):
        return True
    return False


def lint(root: Path) -> list[Violation]:
    """Lint le repo training-logs à ``root`` et retourne la liste des violations."""
    violations: list[Violation] = []

    if not root.is_dir():
        violations.append(
            Violation("ROOT_MISSING", f"root path does not exist or is not a dir: {root}")
        )
        return violations

    yaml_path = root / OPERATORS_FILE
    operators = _load_yaml(yaml_path)

    if operators is None:
        # Pas de yaml = layout flat legacy, pas de check à faire.
        # On émet juste un INFO discret.
        violations.append(
            Violation(
                "OPERATORS_YAML_ABSENT",
                f"{OPERATORS_FILE} absent — flat layout assumed (no scoping check).",
            )
        )
        return violations

    if "__parse_error__" in operators:
        violations.append(
            Violation(
                "OPERATORS_YAML_PARSE_ERROR",
                f"{yaml_path}: {operators['__parse_error__']}",
            )
        )
        return violations

    writers = operators.get("writers") or {}
    if not isinstance(writers, dict):
        violations.append(
            Violation(
                "OPERATORS_YAML_INVALID",
                f"{yaml_path}: 'writers' must be a mapping",
            )
        )
        writers = {}

    whitelist = operators.get("shared_root_files")
    if not isinstance(whitelist, list):
        whitelist = list(DEFAULT_SHARED_ROOT_FILES)

    # Check 1 : chaque writer déclaré a son subdir
    for writer_hash, meta in writers.items():
        subdir = root / writer_hash
        if not subdir.is_dir():
            alias = meta.get("alias", "?") if isinstance(meta, dict) else "?"
            violations.append(
                Violation(
                    "WRITER_SUBDIR_MISSING",
                    f"writer {writer_hash} (alias={alias}) declared in {OPERATORS_FILE} "
                    f"but subdir not found at {subdir}",
                )
            )

    # Check 2 : chaque subdir hex 12-char est déclaré
    declared_hashes = set(writers.keys())
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        name = entry.name
        if name.startswith("."):
            continue
        if WRITER_HASH_RE.match(name) and name not in declared_hashes:
            violations.append(
                Violation(
                    "WRITER_SUBDIR_UNDECLARED",
                    f"subdir {name} matches writer-hash format but is not declared "
                    f"in {OPERATORS_FILE}::writers",
                )
            )

    # Check 3 : fichiers/dirs racine hors whitelist + hors writer subdirs
    for entry in root.iterdir():
        name = entry.name
        if name == ".git":
            continue
        # Subdir writer déclaré → OK
        if entry.is_dir() and name in declared_hashes:
            continue
        # Match whitelist ?
        rel = name
        if any(_whitelist_matches(rel, w) for w in whitelist):
            continue
        # Pour les dirs, on regarde aussi si la whitelist contient un pattern
        # qui couvre leur contenu (ex. docs/architecture/**)
        if entry.is_dir():
            covered = any(
                w.rstrip("/").rstrip("*").rstrip("/").startswith(name + "/")
                or w.rstrip("/").rstrip("*").rstrip("/") == name
                for w in whitelist
            )
            if covered:
                continue
        violations.append(
            Violation(
                "ROOT_ENTRY_UNAUTHORIZED",
                f"{name} at repo root is not in shared_root_files whitelist "
                f"and not a declared writer subdir",
            )
        )

    # Check 4 : writer décommissionné avec subdir non-vide
    for writer_hash, meta in writers.items():
        if not isinstance(meta, dict):
            continue
        decom = meta.get("decommissioned_at")
        if decom in (None, "", "null"):
            continue
        subdir = root / writer_hash
        if not subdir.is_dir():
            continue
        contents = [p for p in subdir.iterdir() if p.name != ".gitkeep"]
        if contents:
            violations.append(
                Violation(
                    "DECOMMISSIONED_WRITER_NOT_EMPTY",
                    f"writer {writer_hash} (alias={meta.get('alias', '?')}) decommissioned "
                    f"at {decom} but subdir still contains {len(contents)} entries",
                )
            )

    return violations


def _self_test() -> int:
    """Sanity check : instantiation + import OK. Pour CI sans repo réel."""
    print("lint-authority-coherence: self-test OK", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="lint-authority-coherence",
        description="Lint .operators.yaml ↔ training-logs repo state coherence (ADR v5 Phase 2).",
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="Training-logs repo root (default: $TRAINING_DATA_ROOT or $TRAINING_DATA_REPO).",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Sanity check sans dépendre d'un repo réel (mode CI).",
    )
    parser.add_argument(
        "--format",
        choices=("gha", "plain"),
        default="gha",
        help="Output format: GitHub Actions warning (default) or plain.",
    )
    args = parser.parse_args()

    if args.self_test:
        return _self_test()

    if args.path:
        root = Path(args.path).expanduser().resolve()
    else:
        env_root = _resolve_root_from_env()
        if env_root is None:
            print(
                "Error: no path provided and TRAINING_DATA_ROOT (or "
                "TRAINING_DATA_REPO) env var not set. Use --self-test for CI.",
                file=sys.stderr,
            )
            return 0
        root = env_root.resolve()

    violations = lint(root)

    if not violations:
        print(
            f"lint-authority-coherence: OK — no violations found at {root}",
            file=sys.stderr,
        )
        return 0

    formatter = (
        Violation.format_gha if args.format == "gha" else Violation.format_plain
    )
    for v in violations:
        print(formatter(v))
    print(
        f"lint-authority-coherence: {len(violations)} violation(s) at {root} "
        f"(WARN-only — exit 0 during ADR v5 transition)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
