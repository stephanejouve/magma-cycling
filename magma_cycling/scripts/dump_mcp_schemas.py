"""BT-058 : dump MCP schemas snapshot pour diff rétrospectif (spec DE-002 D1).

Snapshot du contrat MCP courant à une version donnée. Contenu :

- **Dérivé structurel** (fiable par construction) :
  - Nom d'outil, ``description`` du schéma, ``inputSchema`` complet
  - Version magma-cycling (``__version__``)
- **Dérivé sémantique** (fiable par construction) :
  - Docstring Python du handler (via ``inspect.getdoc``) — capture la
    sémantique DÉCLARÉE de l'outil. Un changement de docstring révèle
    un changement de sens même si le schéma reste identique.
    Cas exemplaire : ``intensity_distribution`` v3.73→v3.74 (comptage
    activités par IF → temps par zone), schéma constant, docstring
    change → diff sémantique visible.

Spec Coach AI 2026-08-18 DE-002 : D1 (snapshot dérivé irrattrapable)
+ ce que ce script ajoute au design initial (docstring introspection)
qui absorbe D3 (« changements sémantiques à schéma constant »).

**Contrat opérationnel** :

- Écrit sur ``stdout`` un JSON parseable.
- Attaché en garde dure du build dans ``.github/workflows/docker-publish.yml``
  (BT-058) : le build échoue si ce script ne produit pas un snapshot valide.
- Fichier attaché comme release asset ``schemas-v{X.Y.Z}.json``.
- Récupération : ``gh release download vX.Y.Z --repo stephanejouve/magma-cycling
  -p 'schemas-*.json'`` ou via ``get-release-notes(from, to)`` MCP tool.

Motif de la garde dure : chaque release sans snapshot = point de diff
perdu **définitivement** (backfill impossible — on ne peut pas reconstruire
le schéma d'une version déjà déployée). L'irrattrapabilité justifie de
faire échouer le build plutôt que de le laisser passer silencieusement.

Usage::

    poetry run python -m magma_cycling.scripts.dump_mcp_schemas > schemas-vX.Y.Z.json
"""

from __future__ import annotations

import asyncio
import inspect
import json
import sys
from datetime import datetime, timezone
from typing import Any


async def _list_tools_async() -> list[Any]:
    """Récupère la liste des ``Tool`` MCP via l'agrégateur ``list_tools()``."""
    # Import intentionnellement local pour éviter les side-effects
    # d'import (le module ``mcp_server`` charge la config, connecte les
    # handlers, etc.). Isolé au moment de l'exécution du script.
    from magma_cycling import mcp_server

    # ``list_tools`` est décoré par ``@server.list_tools()`` et enregistré
    # sur l'instance server. On appelle la fonction sous-jacente directement
    # (sans passer par la boucle MCP) — c'est ce que l'aide au dispatch fait.
    return await mcp_server.list_tools()


def _handler_info(tool_name: str) -> dict[str, Any]:
    """Résout le handler enregistré pour un tool et extrait sa docstring.

    Convention magma-cycling : ``mcp_server.TOOL_HANDLERS`` est le dict de
    dispatch ``{tool_name: handler_function}``. Un tool sans handler
    (théoriquement impossible en release stable) est signalé par des champs
    ``None`` — un diff futur détectera la régression.
    """
    from magma_cycling import mcp_server

    handler = mcp_server.TOOL_HANDLERS.get(tool_name)
    if handler is None:
        return {"module": None, "function": None, "docstring": None}

    return {
        "module": handler.__module__,
        "function": handler.__name__,
        "docstring": inspect.getdoc(handler) or "",
    }


def _serialize_tool(tool: Any) -> dict[str, Any]:
    """Convertit un ``mcp.types.Tool`` en dict JSON-safe + handler info."""
    return {
        "name": tool.name,
        "schema_description": tool.description,
        "input_schema": tool.inputSchema,
        "handler": _handler_info(tool.name),
    }


async def _snapshot() -> dict[str, Any]:
    """Assemble le snapshot complet, prêt à sérialiser en JSON."""
    from magma_cycling import __version__

    tools = await _list_tools_async()

    return {
        "version": f"v{__version__}",
        "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tool_count": len(tools),
        "tools": sorted(
            [_serialize_tool(t) for t in tools],
            key=lambda t: t["name"],
        ),
    }


def main() -> int:
    """CLI entry point. Écrit le snapshot sur stdout, exit 0 si succès."""
    try:
        snapshot = asyncio.run(_snapshot())
    except Exception as exc:
        # Fail-loud sur stderr — le workflow docker-publish détecte l'exit 1
        # et fait échouer le build (garde BT-058).
        print(f"[dump-mcp-schemas] ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    # Assertion minimum : version + tool_count non nul (protège contre un
    # snapshot vide qui passerait la garde mais n'aurait aucune valeur).
    if snapshot["tool_count"] == 0:
        print(
            "[dump-mcp-schemas] ERROR: empty tool list — refusing to write empty snapshot",
            file=sys.stderr,
        )
        return 1

    json.dump(snapshot, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
