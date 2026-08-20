"""BT-060 : agrégation des changements entre 2 versions MCP (spec DE-002).

Compose la réponse à « qu'est-ce qui a changé entre v3.72.0 et v3.74.0
côté contrat MCP ? » depuis 2 sources orthogonales :

- **derived** (source structurelle fiable par construction) :
  - Diff des schémas d'outils entre 2 snapshots BT-058
    (``magma-cycling-schemas-vX.Y.Z.json`` release assets)
  - Diff textuel des docstrings handler entre 2 snapshots — ferme le
    trou D3 (changements sémantiques à schéma constant)
- **declared** (source rédaction humaine, discipline requise) :
  - Entrées ``CHANGELOG.md`` entre les 2 versions (sections
    ``Added / Changed / Fixed / Deprecated`` avec IDs BT)
  - Commits mentionnant des BT-IDs entre les 2 tags git

- **absence_notes** (P3 DE-002) : versions dans la plage qui n'ont AUCUNE
  entrée déclarée. Signal explicite « aucune note enregistrée pour
  cette version », distinct de « aucun changement ».

Design décision Coach AI 2026-08-18 : garder ``derived`` et ``declared``
**strictement séparés** dans le payload — jamais de mélange dans un
champ uniforme. Un consommateur peut alors pondérer la confiance :
derived = fait vérifiable, declared = dépend de la discipline de
renseignement.

**Contrat V1** : le tool retourne des données brutes structurées pour
que le LLM consommateur (Coach AI, dev humain) compose sa propre
lecture. Pas de résumé, pas de « verdict ». Pas de formatage.

**État de la base au moment du merge** : BT-058 (dump_mcp_schemas) vient
d'être livré, donc **aucun snapshot n'existe encore** sur les releases
antérieures. La partie ``derived.schema_changes`` retournera
``{"note": "aucun snapshot..."}`` tant que la base n'a pas ≥ 2 snapshots.
La partie ``declared`` fonctionne dès aujourd'hui (lecture CHANGELOG local
+ git log). Le tool devient pleinement utile au fur et à mesure que les
releases produisent leurs snapshots.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

#: BT-058 : nom de fichier snapshot attendu dans les release assets
_SNAPSHOT_ASSET_TEMPLATE = "magma-cycling-schemas-{version}.json"


def _parse_semver(version: str) -> tuple[int, int, int]:
    """Convertit ``vX.Y.Z`` ou ``X.Y.Z`` en tuple ``(x, y, z)`` pour comparaison.

    Lève ``ValueError`` si le format est invalide. Utilisé pour valider
    l'ordre ``from_version < to_version`` avant tout appel réseau.
    """
    stripped = version.lstrip("v")
    parts = stripped.split(".")
    if len(parts) != 3:
        raise ValueError(f"invalid semver: {version!r} (expected X.Y.Z)")
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError as exc:
        raise ValueError(f"invalid semver components: {version!r}") from exc


def _normalize_version(version: str) -> str:
    """Retourne ``vX.Y.Z`` (préfixe ``v`` garanti)."""
    _parse_semver(version)  # validation
    return version if version.startswith("v") else f"v{version}"


def _fetch_snapshot_from_github(
    version: str,
    repo: str,
    github_client: Any | None = None,
) -> dict[str, Any] | None:
    """Télécharge le snapshot BT-058 attaché à une release.

    Args:
        version: tag ``vX.Y.Z``.
        repo: ``owner/name`` du repo GitHub.
        github_client: optional, permet d'injecter un client mocké en test.
            Si ``None``, utilise :mod:`urllib.request` avec le token
            GitHub App via ``outillages.github_utils._get_token``.

    Returns:
        Dict parsé depuis le JSON snapshot, ou ``None`` si la release
        existe sans l'asset (release antérieure à BT-058) ou si la release
        n'existe pas. Le caller propage cette absence dans ``absence_notes``.
        Ne lève jamais d'exception (contrat « never raise »).
    """
    if github_client is not None:
        return github_client(version, repo)

    import urllib.error
    import urllib.request

    try:
        from outillages.github_utils import _get_token

        token = _get_token()
    except Exception:
        # Pas de token dispo → impossible de fetch. Retourner None traité
        # comme snapshot absent (absence_notes signale la cause).
        return None

    asset_name = _SNAPSHOT_ASSET_TEMPLATE.format(version=version)
    api_url = f"https://api.github.com/repos/{repo}/releases/tags/{version}"

    try:
        req = urllib.request.Request(
            api_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            release = json.loads(resp.read())
    except Exception:
        # Release inexistante, réseau, timeout, parse : traité comme absent.
        return None

    for asset in release.get("assets", []):
        if asset.get("name") == asset_name:
            download_url = asset.get("browser_download_url")
            if not download_url:
                return None
            try:
                req = urllib.request.Request(
                    download_url,
                    headers={"Authorization": f"Bearer {token}"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return json.loads(resp.read())
            except Exception:
                return None

    return None  # asset attendu absent (release antérieure à BT-058)


def _diff_schemas(
    from_snapshot: dict[str, Any],
    to_snapshot: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Compare 2 snapshots BT-058 et produit un diff structurel.

    Détecte :
    - **tools_added** : outils présents dans ``to`` absents de ``from``
    - **tools_removed** : outils présents dans ``from`` absents de ``to``
    - **schema_changed** : outils dont ``input_schema`` diffère

    Le diff textuel des docstrings est calculé séparément (voir
    :func:`_diff_docstrings`) — il capture les changements de sémantique
    à schéma constant, ce qui est le vrai apport de BT-058.

    Args:
        from_snapshot: snapshot version antérieure (dict au format
            ``{version, tool_count, tools: [...]}``).
        to_snapshot: snapshot version postérieure.

    Returns:
        Dict avec 3 listes ``tools_added, tools_removed, schema_changed``.
        Chaque entrée = ``{"name": str, ...détails}``.
    """
    from_tools = {t["name"]: t for t in from_snapshot.get("tools", [])}
    to_tools = {t["name"]: t for t in to_snapshot.get("tools", [])}

    tools_added = [{"name": n} for n in sorted(to_tools.keys() - from_tools.keys())]
    tools_removed = [{"name": n} for n in sorted(from_tools.keys() - to_tools.keys())]
    schema_changed = []
    for name in sorted(from_tools.keys() & to_tools.keys()):
        if from_tools[name].get("input_schema") != to_tools[name].get("input_schema"):
            schema_changed.append({"name": name})
    return {
        "tools_added": tools_added,
        "tools_removed": tools_removed,
        "schema_changed": schema_changed,
    }


def _diff_docstrings(
    from_snapshot: dict[str, Any],
    to_snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    """Détecte les tools dont le docstring handler a changé.

    C'est le vrai apport BT-058 : capture les changements sémantiques à
    schéma constant. Cas exemplaire : ``intensity_distribution``
    v3.73→v3.74 (comptage activités → temps par zone, input_schema
    identique).

    Ne retourne QUE les tools où la docstring diffère textuellement
    (whitespace-sensitive intentionnel — un renommage de variable dans
    la doc compte comme un signal, un fix typo aussi).

    Returns:
        Liste ``[{name, from_docstring, to_docstring}, ...]`` — le
        consommateur (LLM ou humain) juge lui-même la significativité.
    """
    from_tools = {t["name"]: t for t in from_snapshot.get("tools", [])}
    to_tools = {t["name"]: t for t in to_snapshot.get("tools", [])}
    changes = []
    for name in sorted(from_tools.keys() & to_tools.keys()):
        f_doc = (from_tools[name].get("handler") or {}).get("docstring") or ""
        t_doc = (to_tools[name].get("handler") or {}).get("docstring") or ""
        if f_doc != t_doc:
            changes.append(
                {
                    "name": name,
                    "from_docstring": f_doc,
                    "to_docstring": t_doc,
                }
            )
    return changes


def _extract_changelog_between(
    from_version: str,
    to_version: str,
    changelog_path: Path,
) -> dict[str, list[str]]:
    """Extrait les sections CHANGELOG entre 2 versions.

    Parcourt ``CHANGELOG.md`` (format Keep-a-Changelog) et retourne les
    entrées des sections ``## [X.Y.Z]`` strictement entre ``from`` (exclu)
    et ``to`` (inclus). Si ``to_version`` cible ``[Unreleased]``, ce
    contenu est inclus.

    Args:
        from_version: ``vX.Y.Z`` (exclusive, changements après cette version)
        to_version: ``vX.Y.Z`` (inclusive)
        changelog_path: chemin ``CHANGELOG.md``.

    Returns:
        Dict ``{version: [ligne, ligne, ...]}`` pour chaque version dans
        la plage qui a des entrées. Absent si CHANGELOG introuvable ou
        sections vides.
    """
    if not changelog_path.exists():
        return {}

    content = changelog_path.read_text(encoding="utf-8")
    # Matcher les headers "## [X.Y.Z]" ou "## [Unreleased]"
    # Pattern non-greedy pour capturer jusqu'au prochain "## ["
    sections = re.findall(
        r"^## \[([^\]]+)\](.*?)(?=^## \[|\Z)",
        content,
        re.MULTILINE | re.DOTALL,
    )

    from_semver = _parse_semver(from_version)
    to_semver = _parse_semver(to_version)

    result: dict[str, list[str]] = {}
    for label, body in sections:
        # Ignorer les sections vides et les sections hors plage
        if label == "Unreleased":
            # Inclure si to_version reflète l'état courant
            # (heuristique : Unreleased est toujours "à partir de la
            # prochaine release", donc inclus si to == current __version__)
            # Pour V1, inclure systématiquement — consommateur pondère.
            if body.strip():
                result[label] = [ln for ln in body.strip().splitlines() if ln.strip()]
            continue
        try:
            label_semver = _parse_semver(label)
        except ValueError:
            continue
        if from_semver < label_semver <= to_semver:
            if body.strip():
                result[label] = [ln for ln in body.strip().splitlines() if ln.strip()]
    return result


def _git_log_between_tags(
    from_version: str,
    to_version: str,
    repo_root: Path,
) -> list[dict[str, str]]:
    """Liste les commits mentionnant BT-XXX entre 2 tags git.

    Utilise ``git log from_version..to_version --grep=BT-``. Ne lève
    jamais d'exception (contrat « never raise ») — retourne liste vide
    si git indisponible, tag absent, ou repo corrompu.

    Returns:
        Liste ``[{sha, subject}, ...]`` limitée aux commits BT-annotés.
    """
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                f"{from_version}..{to_version}",
                "--grep=BT-",
                "--pretty=format:%h %s",
                "--no-merges",
            ],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return []
    if result.returncode != 0:
        return []
    commits = []
    for line in result.stdout.strip().splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2:
            commits.append({"sha": parts[0], "subject": parts[1]})
    return commits


def compose_release_notes(
    from_version: str,
    to_version: str,
    *,
    repo: str = "stephanejouve/magma-cycling",
    changelog_path: Path | None = None,
    repo_root: Path | None = None,
    github_client: Any | None = None,
) -> dict[str, Any]:
    """Assemble le payload complet ``release-notes(from, to)``.

    Args:
        from_version: ``vX.Y.Z`` — version antérieure (exclusive).
        to_version: ``vX.Y.Z`` — version postérieure (inclusive).
        repo: ``owner/name`` GitHub pour les snapshots.
        changelog_path: chemin ``CHANGELOG.md``. Défaut : chemin repo courant.
        repo_root: racine du repo git pour ``git log``. Défaut : chemin repo courant.
        github_client: optional injection pour tests (voir
            :func:`_fetch_snapshot_from_github`).

    Returns:
        Dict avec la structure ``{from_version, to_version, derived,
        declared, absence_notes}``. Voir docstring du module pour le
        design décision « derived != declared ».
    """
    # Validation semver (raises ValueError avant tout I/O)
    from_norm = _normalize_version(from_version)
    to_norm = _normalize_version(to_version)
    if _parse_semver(from_norm) >= _parse_semver(to_norm):
        raise ValueError(
            f"from_version {from_norm} must be strictly less than to_version {to_norm}"
        )

    # Defaults : racine repo magma-cycling (calculée depuis le fichier)
    if changelog_path is None:
        changelog_path = Path(__file__).resolve().parents[2] / "CHANGELOG.md"
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]

    absence_notes: list[dict[str, str]] = []

    # ── DERIVED : snapshots BT-058 (bloc isolé) ───────────────────────
    # Coach AI 2026-08-21 : les 3 sources orthogonales doivent survivre
    # à un échec de l'une. Un échec de bloc = information (absence_notes),
    # pas panne. Catch (Exception, SystemExit) — pas BaseException seul
    # pour préserver KeyboardInterrupt. Fix contre `sys.exit` percolant
    # depuis outillages.github_utils (à corriger séparément côté source).
    derived: dict[str, Any] | None = {"schema_changes": None, "docstring_diffs": None}
    try:
        from_snap = _fetch_snapshot_from_github(from_norm, repo, github_client=github_client)
        to_snap = _fetch_snapshot_from_github(to_norm, repo, github_client=github_client)
        if from_snap is None:
            absence_notes.append(
                {
                    "type": "snapshot_missing",
                    "version": from_norm,
                    "message": (
                        f"Snapshot BT-058 absent pour {from_norm} — release "
                        "probablement antérieure à BT-058 (2026-08-18), ou "
                        "asset détruit. Impossible de calculer un diff structurel."
                    ),
                }
            )
        if to_snap is None:
            absence_notes.append(
                {
                    "type": "snapshot_missing",
                    "version": to_norm,
                    "message": (
                        f"Snapshot BT-058 absent pour {to_norm} — release "
                        "probablement antérieure à BT-058 (2026-08-18), ou "
                        "asset détruit. Impossible de calculer un diff structurel."
                    ),
                }
            )
        if from_snap is not None and to_snap is not None:
            derived["schema_changes"] = _diff_schemas(from_snap, to_snap)
            derived["docstring_diffs"] = _diff_docstrings(from_snap, to_snap)
    except (Exception, SystemExit) as exc:  # noqa: BLE001 — P3 isolation blocs
        derived = None
        absence_notes.append(
            {
                "type": "block_failed",
                "block": "derived",
                "message": (
                    f"Bloc derived a échoué ({type(exc).__name__}: {str(exc)[:200]}). "
                    "Cause probable : sys.exit percolant depuis une dépendance "
                    "importée (outillages.github_utils._get_token) — bug à traiter "
                    "côté source, pas ici. absence_notes.type=block_failed exposé "
                    "pour audit."
                ),
            }
        )

    # ── DECLARED : CHANGELOG + git log (bloc isolé) ───────────────────
    declared: dict[str, Any] | None
    try:
        changelog_entries = _extract_changelog_between(from_norm, to_norm, changelog_path)
        bt_commits = _git_log_between_tags(from_norm, to_norm, repo_root)
        declared = {"changelog_entries": changelog_entries, "bt_commits": bt_commits}
        if not changelog_entries:
            absence_notes.append(
                {
                    "type": "changelog_empty",
                    "message": (
                        f"Aucune entrée CHANGELOG.md déclarée entre {from_norm} "
                        f"et {to_norm}. Soit rien n'a été livré, soit la "
                        "discipline CHANGELOG a lâché sur cette plage."
                    ),
                }
            )
    except (Exception, SystemExit) as exc:  # noqa: BLE001 — P3 isolation blocs
        declared = None
        absence_notes.append(
            {
                "type": "block_failed",
                "block": "declared",
                "message": (
                    f"Bloc declared a échoué ({type(exc).__name__}: {str(exc)[:200]}). "
                    "Cause probable : accès git/CHANGELOG indisponible dans "
                    "l'environnement d'exécution (container prod sans repo local, "
                    "ou binary git absent)."
                ),
            }
        )

    return {
        "from_version": from_norm,
        "to_version": to_norm,
        "derived": derived,
        "declared": declared,
        "absence_notes": absence_notes,
    }
