# MCP Integration - Claude Desktop

## Vue d'Ensemble

Le **MCP Server** (Model Context Protocol) expose 48 tools de gestion d'entrainement directement a Claude Desktop et autres clients MCP compatibles.

**Date de deploiement :** 2026-02-21
**Status :** Production Ready
**Tools exposes :** 48

## Architecture

```
                  Claude Desktop
               (ou autre client MCP)
                        |
                        | JSON-RPC 2.0 over stdio
                        v
          +-----------------------------+
          |        MCP Server           |
          |  magma_cycling.mcp_server   |
          |                             |
          |  48 tools / 13 handlers     |
          +-----------------------------+
                   |         |
          +--------+    +--------+
          |             |
    Control Tower    IntervalsClient
    + Audit Log      + Withings API
```

### Structure handlers

```
magma_cycling/_mcp/handlers/
  planning.py           # 11 tools
  analysis.py           #  8 tools
  withings.py           #  8 tools
  intervals_sync.py     #  3 tools
  intervals_events.py   #  4 tools
  intervals_activities.py # 3 tools
  intervals_analysis.py #  2 tools
  sessions.py           #  3 tools
  workouts.py           #  2 tools
  athlete.py            #  2 tools
  catalog.py            #  1 tool
  admin.py              #  1 tool
  intervals.py          #  (re-export shim)
```

## Tools par categorie

### Planning (11 tools) — `planning.py`

| Tool | Description |
|------|-------------|
| `weekly-planner` | Genere planning hebdomadaire avec recommandations AI |
| `monthly-analysis` | Analyse mensuelle complete avec stats + insights AI |
| `daily-sync` | Synchronise activites depuis Intervals.icu |
| `update-session` | Met a jour statut d'une session |
| `list-weeks` | Liste les plannings hebdomadaires disponibles |
| `get-metrics` | Recupere metriques d'entrainement actuelles |
| `get-week-details` | Details complets d'une semaine (sessions, statuts, TSS) |
| `modify-session-details` | Modifie les details d'une session (type, nom, description) |
| `rename-session` | Renomme une session selon la convention de nommage |
| `create-session` | Cree une nouvelle session dans le planning |
| `delete-session` | Supprime une session du planning |

### Analysis (8 tools) — `analysis.py`

| Tool | Description |
|------|-------------|
| `validate-week-consistency` | Valide la coherence d'un planning hebdomadaire |
| `get-recommendations` | Recommandations d'entrainement basees sur les metriques |
| `analyze-session-adherence` | Analyse l'adherence seance planifiee vs realisee |
| `get-training-statistics` | Statistiques d'entrainement sur une periode |
| `export-week-to-json` | Exporte un planning en JSON |
| `restore-week-from-backup` | Restaure un planning depuis un backup |
| `analyze-training-patterns` | Analyse les patterns d'entrainement |
| `get-coach-analysis` | Analyse coach AI d'une activite |

### Withings (8 tools) — `withings.py`

| Tool | Description |
|------|-------------|
| `withings-auth-status` | Statut d'authentification Withings |
| `withings-authorize` | Lancer le flow OAuth Withings |
| `withings-get-sleep` | Donnees de sommeil |
| `withings-get-weight` | Donnees de poids et composition corporelle |
| `withings-get-readiness` | Score de readiness |
| `withings-sync-to-intervals` | Synchronise donnees Withings vers Intervals.icu |
| `withings-analyze-trends` | Analyse des tendances sante |
| `withings-enrich-session` | Enrichit une session avec donnees sante |

### Intervals.icu — Sync (3 tools) — `intervals_sync.py`

| Tool | Description |
|------|-------------|
| `sync-week-to-intervals` | Synchronise le planning local vers Intervals.icu |
| `sync-remote-to-local` | Synchronise les events Intervals.icu vers le planning local |
| `backfill-activities` | Backfill des activites historiques |

### Intervals.icu — Events (4 tools) — `intervals_events.py`

| Tool | Description |
|------|-------------|
| `delete-remote-session` | Supprime un event sur Intervals.icu |
| `list-remote-events` | Liste les events Intervals.icu pour une periode |
| `update-remote-session` | Met a jour un event sur Intervals.icu |
| `create-remote-note` | Cree une NOTE sur Intervals.icu |

### Intervals.icu — Activities (3 tools) — `intervals_activities.py`

| Tool | Description |
|------|-------------|
| `get-activity-details` | Details complets d'une activite |
| `get-activity-intervals` | Intervalles d'une activite (laps, segments) |
| `get-activity-streams` | Streams d'une activite (power, HR, cadence) |

### Intervals.icu — Analysis (2 tools) — `intervals_analysis.py`

| Tool | Description |
|------|-------------|
| `compare-intervals` | Compare intervalles planifies vs realises |
| `apply-workout-intervals` | Applique un workout Intervals.icu format a un event |

### Sessions (3 tools) — `sessions.py`

| Tool | Description |
|------|-------------|
| `duplicate-session` | Duplique une session dans le planning |
| `swap-sessions` | Echange deux sessions dans le planning |
| `attach-workout` | Attache un fichier workout a une session |

### Workouts (2 tools) — `workouts.py`

| Tool | Description |
|------|-------------|
| `get-workout` | Recupere le contenu d'un workout (fichier ou planning) |
| `validate-workout` | Valide le format d'un workout |

### Athlete (2 tools) — `athlete.py`

| Tool | Description |
|------|-------------|
| `get-athlete-profile` | Profil athlete (FTP, poids, zones, objectifs) |
| `update-athlete-profile` | Met a jour le profil athlete |

### Catalog (1 tool) — `catalog.py`

| Tool | Description |
|------|-------------|
| `list-workout-catalog` | Liste le catalogue de workouts Zwift disponibles |

### Admin (1 tool) — `admin.py`

| Tool | Description |
|------|-------------|
| `reload-server` | Rechargement a chaud du serveur MCP |

## Installation

### 1. Verifier l'installation

```bash
# Tester que le serveur MCP se lance
poetry run mcp-server
# Devrait attendre stdin (Ctrl+C pour quitter)

# Tester les imports
poetry run python -c "from magma_cycling.mcp_server import server; print('OK')"
```

### 2. Configuration Claude Desktop

**Localisation :** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "cyclisme-training": {
      "command": "poetry",
      "args": ["run", "mcp-server"],
      "cwd": "/chemin/vers/magma-cycling",
      "env": {}
    }
  }
}
```

### 3. Redemarrer Claude Desktop

Quitter completement et relancer. Verifier dans Settings > MCP Servers que "cyclisme-training" est connecte.

## Securite

### Permissions

Le MCP server utilise la **Control Tower** pour toutes les modifications :
- Backup automatique avant chaque modification
- Audit log complet (WHO/WHY/WHEN/WHAT)
- Permission system (anti-modifications concurrentes)
- Validation Pydantic sur toutes les donnees

### Tracabilite

Toutes les operations via MCP sont loguees :

```json
{
  "timestamp": "2026-03-15T15:30:45Z",
  "operation": "MODIFY",
  "week_id": "S085",
  "tool": "mcp-server",
  "username": "user",
  "reason": "MCP: Update S085-03 to completed",
  "status": "SUCCESS"
}
```

Audit log : `~/data/.planning_audit.jsonl`

## Troubleshooting

### Serveur MCP ne demarre pas

```bash
# Verifier les imports
poetry run python -c "from magma_cycling.mcp_server import server"

# Verifier les dependances
poetry show mcp

# Reinstaller si besoin
poetry install
```

### Claude Desktop ne voit pas le serveur

1. Verifier le chemin `cwd` dans `claude_desktop_config.json`
2. Verifier que `poetry run mcp-server` fonctionne en CLI
3. Redemarrer completement Claude Desktop
4. Checker les logs Claude Desktop : `~/Library/Logs/Claude/`

### Tool call echoue

Les erreurs sont retournees en JSON :

```json
{
  "error": "Session S085-03 not found in S085",
  "tool": "update-session",
  "arguments": {}
}
```

Verifier : format des arguments, existence des fichiers, permissions filesystem.

## Statistiques

| Metrique | Valeur |
|----------|--------|
| **Tools exposes** | 48 |
| **Handlers** | 13 fichiers |
| **Protocole** | JSON-RPC 2.0 over stdio |
| **Transport** | MCP SDK Python |
| **Securite** | Control Tower + Audit Log |
| **Status** | Production Ready |

## References

- **MCP Spec :** https://modelcontextprotocol.io/
- **Code Server :** `magma_cycling/mcp_server.py`
- **Handlers :** `magma_cycling/_mcp/handlers/`
- **Schemas :** `magma_cycling/_mcp/schemas/`
- **Control Tower :** `project-docs/CONTROL_TOWER.md`

---

**Date :** Mars 2026
**Version :** 2.0.0
**Status :** Production Ready
