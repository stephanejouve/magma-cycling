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
from typing import Any, NamedTuple


class FetchResult(NamedTuple):
    """Résultat typé de :func:`_fetch_snapshot_from_github` (BT-060 L2/L3).

    ``reason`` discrimine les 5+ sous-cas d'absence pour éviter le silence
    trompeur ``None`` monolithique. Coach AI 2026-08-21 : « un outil qui
    se trompe sur l'origine d'une absence est pire qu'un outil muet ».
    """

    snapshot: dict[str, Any] | None
    reason: str  # "ok" | "no_token" | "network_error" | "release_not_found" | "asset_not_found" | "download_error" | "parse_error"
    detail: str = ""


class ChangelogResult(NamedTuple):
    """Résultat typé de :func:`_extract_changelog_between` (BT-060 L2)."""

    entries: dict[str, list[str]]
    reason: str  # "ok" | "source_unreadable" | "no_entries" | "parser_no_match"
    detail: str = ""
    total_sections: int = 0


class GitLogResult(NamedTuple):
    """Résultat typé de :func:`_git_log_between_tags` (BT-060 L1/L2)."""

    commits: list[dict[str, str]]
    reason: str  # "ok" | "source_unreadable" | "no_entries" | "parser_no_match"
    detail: str = ""
    total_seen: int = 0


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
) -> FetchResult:
    """Télécharge le snapshot BT-058 attaché à une release.

    Args:
        version: tag ``vX.Y.Z``.
        repo: ``owner/name`` du repo GitHub.
        github_client: optional, permet d'injecter un client mocké en test.
            Callable ``(version, repo) -> dict | None`` — pour tests, la
            distinction fine des reasons ne peut pas être inférée depuis
            un simple None (on suppose « release_not_found »).
            Si ``None``, utilise :mod:`urllib.request` avec le token
            GitHub App via ``outillages.github_utils._get_token``.

    Returns:
        :class:`FetchResult` avec ``snapshot``, ``reason`` typé et ``detail``.
        BT-060 L3 : ``reason`` discrimine 7 sous-cas au lieu du ``None``
        monolithique historique. Ne lève jamais d'exception.
    """
    if github_client is not None:
        snap = github_client(version, repo)
        return FetchResult(
            snap,
            "ok" if snap is not None else "release_not_found",
            "" if snap is not None else f"github_client returned None for {version}",
        )

    import urllib.error
    import urllib.request

    try:
        from outillages.github_utils import _get_token

        token = _get_token()
    except Exception as exc:  # noqa: BLE001 — never raise
        return FetchResult(None, "no_token", f"{type(exc).__name__}: {str(exc)[:200]}")

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
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return FetchResult(None, "release_not_found", f"HTTP 404 on {api_url}")
        return FetchResult(None, "network_error", f"HTTP {exc.code} on {api_url}: {exc.reason}")
    except urllib.error.URLError as exc:
        return FetchResult(None, "network_error", f"URLError on {api_url}: {exc.reason}")
    except (ValueError, json.JSONDecodeError) as exc:
        return FetchResult(None, "parse_error", f"JSON parse on release: {str(exc)[:200]}")
    except Exception as exc:  # noqa: BLE001 — never raise
        return FetchResult(None, "network_error", f"{type(exc).__name__}: {str(exc)[:200]}")

    for asset in release.get("assets", []):
        if asset.get("name") == asset_name:
            download_url = asset.get("browser_download_url")
            if not download_url:
                return FetchResult(
                    None, "asset_not_found", f"asset {asset_name} present without download_url"
                )
            try:
                req = urllib.request.Request(
                    download_url,
                    headers={"Authorization": f"Bearer {token}"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    payload = json.loads(resp.read())
                    return FetchResult(payload, "ok", f"fetched {asset_name}")
            except (urllib.error.HTTPError, urllib.error.URLError) as exc:
                return FetchResult(
                    None, "download_error", f"failed download {asset_name}: {str(exc)[:200]}"
                )
            except (ValueError, json.JSONDecodeError) as exc:
                return FetchResult(
                    None, "parse_error", f"JSON parse on {asset_name}: {str(exc)[:200]}"
                )
            except Exception as exc:  # noqa: BLE001 — never raise
                return FetchResult(
                    None, "download_error", f"{type(exc).__name__}: {str(exc)[:200]}"
                )

    return FetchResult(
        None,
        "asset_not_found",
        f"release {version} present, but asset {asset_name} absent (release probably pre-BT-058)",
    )


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
) -> ChangelogResult:
    """Extrait les sections CHANGELOG entre 2 versions.

    Parcourt ``CHANGELOG.md`` (format Keep-a-Changelog) et retourne les
    entrées des sections ``## [X.Y.Z]`` strictement entre ``from`` (exclu)
    et ``to`` (inclus). Si ``to_version`` cible ``[Unreleased]``, ce
    contenu est inclus.

    BT-060 L2 : retourne :class:`ChangelogResult` avec ``reason`` typé pour
    discriminer les 3 sous-cas d'absence :

    - ``source_unreadable`` : fichier absent (typique container prod sans COPY CHANGELOG.md)
    - ``no_entries`` : fichier lu, aucune section dans la plage
    - ``parser_no_match`` : fichier lu, sections présentes, aucune ne matche la plage
    """
    if not changelog_path.exists():
        return ChangelogResult(
            {},
            "source_unreadable",
            f"CHANGELOG.md absent au chemin {changelog_path} (container sans COPY CHANGELOG ?)",
        )

    content = changelog_path.read_text(encoding="utf-8")
    # Matcher les headers "## [X.Y.Z]" ou "## [Unreleased]"
    sections = re.findall(
        r"^## \[([^\]]+)\](.*?)(?=^## \[|\Z)",
        content,
        re.MULTILINE | re.DOTALL,
    )
    total_sections = len(sections)

    if total_sections == 0:
        return ChangelogResult(
            {},
            "no_entries",
            f"CHANGELOG.md lu ({len(content)} chars) mais 0 section ## [X.Y.Z] trouvée",
        )

    from_semver = _parse_semver(from_version)
    to_semver = _parse_semver(to_version)

    result: dict[str, list[str]] = {}
    for label, body in sections:
        if label == "Unreleased":
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

    if not result:
        return ChangelogResult(
            {},
            "parser_no_match",
            f"CHANGELOG.md lu, {total_sections} sections présentes, 0 captée dans plage {from_version}..{to_version}",
            total_sections=total_sections,
        )

    return ChangelogResult(
        result,
        "ok",
        f"{len(result)} sections captées / {total_sections} présentes",
        total_sections=total_sections,
    )


#: BT-060 L1 : regex généralisée pour matcher BT-XXX dans le message commit.
#: Insensible à la casse (matche ``BT-060``, ``bt-060``, ``Bt-060``) ;
#: ``\b`` word boundaries évitent les faux positifs (ex ``bt-something-nonnumeric``).
_BT_COMMIT_PATTERN = re.compile(r"\bBT-\d+\b", re.IGNORECASE)


def _git_log_between_tags(
    from_version: str,
    to_version: str,
    repo_root: Path,
) -> GitLogResult:
    """Liste les commits mentionnant BT-XXX entre 2 tags git.

    BT-060 L1 + L2 : parser Python avec :data:`_BT_COMMIT_PATTERN`
    (insensible casse + word boundary), et 3 états d'absence distincts.

    Returns:
        :class:`GitLogResult` avec ``reason`` typé :

        - ``source_unreadable`` : git binary absent, repo non-git, tags manquants,
          subprocess timeout, permission (cas typique container prod sans .git/)
        - ``no_entries`` : git log OK, 0 commits dans la plage
        - ``parser_no_match`` : commits dans la plage mais aucun avec BT-XXX
    """
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                f"{from_version}..{to_version}",
                "--pretty=format:%h %s",
                "--no-merges",
            ],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as exc:  # noqa: BLE001 — never raise
        return GitLogResult(
            [],
            "source_unreadable",
            f"subprocess git log failed: {type(exc).__name__}: {str(exc)[:200]}",
        )

    if result.returncode != 0:
        stderr_short = (result.stderr or "").strip()[:200]
        return GitLogResult(
            [],
            "source_unreadable",
            f"git log rc={result.returncode} (repo_root={repo_root}): {stderr_short}",
        )

    lines = [ln for ln in result.stdout.strip().splitlines() if ln.strip()]
    total_seen = len(lines)

    if total_seen == 0:
        return GitLogResult(
            [],
            "no_entries",
            f"git log OK, 0 commit dans plage {from_version}..{to_version}",
            total_seen=0,
        )

    commits: list[dict[str, str]] = []
    for line in lines:
        parts = line.split(" ", 1)
        if len(parts) == 2:
            sha, subject = parts
            if _BT_COMMIT_PATTERN.search(subject):
                commits.append({"sha": sha, "subject": subject})

    if not commits:
        return GitLogResult(
            [],
            "parser_no_match",
            f"{total_seen} commits vus dans plage, 0 avec pattern BT-XXX (subjects only)",
            total_seen=total_seen,
        )

    return GitLogResult(
        commits,
        "ok",
        f"{len(commits)}/{total_seen} commits BT-annotés captés",
        total_seen=total_seen,
    )


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
    # BT-060 L3 : chaque snapshot fetch discrimine 7 sous-cas via FetchResult
    # (release_not_found / asset_not_found / no_token / network_error /
    # download_error / parse_error / ok). Plus jamais un `None` monolithique
    # ambigu. Absence_notes porte le type + le detail pour orienter le fix.
    derived: dict[str, Any] | None = {"schema_changes": None, "docstring_diffs": None}
    try:
        from_result = _fetch_snapshot_from_github(from_norm, repo, github_client=github_client)
        to_result = _fetch_snapshot_from_github(to_norm, repo, github_client=github_client)

        if from_result.reason != "ok":
            absence_notes.append(
                {
                    "type": "snapshot_missing",
                    "sub_type": from_result.reason,
                    "version": from_norm,
                    "message": (
                        f"Snapshot BT-058 absent pour {from_norm} (reason={from_result.reason}). "
                        f"{from_result.detail}"
                    ),
                }
            )
        if to_result.reason != "ok":
            absence_notes.append(
                {
                    "type": "snapshot_missing",
                    "sub_type": to_result.reason,
                    "version": to_norm,
                    "message": (
                        f"Snapshot BT-058 absent pour {to_norm} (reason={to_result.reason}). "
                        f"{to_result.detail}"
                    ),
                }
            )
        if from_result.snapshot is not None and to_result.snapshot is not None:
            derived["schema_changes"] = _diff_schemas(from_result.snapshot, to_result.snapshot)
            derived["docstring_diffs"] = _diff_docstrings(from_result.snapshot, to_result.snapshot)
            # BT-060 L3 : "comparé, 0 changement" ≠ "pas comparé". Marqueur explicite.
            sc = derived["schema_changes"]
            no_schema_change = (
                not sc["tools_added"] and not sc["tools_removed"] and not sc["schema_changed"]
            )
            if no_schema_change and not derived["docstring_diffs"]:
                absence_notes.append(
                    {
                        "type": "derived_no_diff",
                        "message": (
                            f"Comparaison BT-058 effectuée sur les 2 snapshots {from_norm} et {to_norm}, "
                            "aucun changement structurel détecté (schemas identiques, docstrings identiques)."
                        ),
                    }
                )
    except (Exception, SystemExit) as exc:  # noqa: BLE001 — P3 isolation blocs
        derived = None
        absence_notes.append(
            {
                "type": "block_failed",
                "block": "derived",
                "message": (
                    f"Bloc derived a échoué ({type(exc).__name__}: {str(exc)[:200]}). "
                    "Cause probable : sys.exit percolant depuis une dépendance importée."
                ),
            }
        )

    # ── DECLARED : CHANGELOG + git log (bloc isolé) ───────────────────
    # BT-060 L2 : chaque source déclare son propre absence_notes avec les
    # 3 états typés (source_unreadable / no_entries / parser_no_match) et
    # les chiffres portés dans le message ("N vus, 0 capté").
    declared: dict[str, Any] | None
    try:
        cl_result = _extract_changelog_between(from_norm, to_norm, changelog_path)
        gl_result = _git_log_between_tags(from_norm, to_norm, repo_root)
        declared = {
            "changelog_entries": cl_result.entries,
            "bt_commits": gl_result.commits,
        }
        if cl_result.reason != "ok":
            absence_notes.append(
                {
                    "type": "changelog_missing",
                    "sub_type": cl_result.reason,
                    "message": (
                        f"CHANGELOG.md pour {from_norm}..{to_norm} : reason={cl_result.reason}. "
                        f"{cl_result.detail}"
                    ),
                }
            )
        if gl_result.reason != "ok":
            absence_notes.append(
                {
                    "type": "bt_commits_missing",
                    "sub_type": gl_result.reason,
                    "total_seen": gl_result.total_seen,
                    "message": (
                        f"Git log BT-annotés pour {from_norm}..{to_norm} : reason={gl_result.reason}. "
                        f"{gl_result.detail}"
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
                    "Cause probable : accès filesystem/git binary indisponible."
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
