# MCP Integration - Claude Desktop

## 🎯 Vue d'Ensemble

Le **MCP Server** (Model Context Protocol) expose tous les outils de training logs directement à Claude Desktop et autres clients MCP compatibles.

**Date de déploiement:** 2026-02-21
**Status:** ✅ Production Ready

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│        Claude Desktop                   │
│  (ou autre client MCP)                  │
└─────────────┬───────────────────────────┘
              │ JSON-RPC 2.0 over stdio
              ▼
┌─────────────────────────────────────────┐
│     MCP Server                          │
│  cyclisme_training_logs.mcp_server      │
│                                         │
│  Tools:                                 │
│  ├── weekly-planner                     │
│  ├── monthly-analysis                   │
│  ├── daily-sync                         │
│  ├── update-session                     │
│  ├── list-weeks                         │
│  └── get-metrics                        │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│    Control Tower + Audit Log            │
│    + All existing tools                 │
└─────────────────────────────────────────┘
```

## 🚀 Installation

### 1. Vérifier l'Installation

```bash
# Tester que le serveur MCP se lance
poetry run mcp-server
# Devrait attendre stdin (Ctrl+C pour quitter)

# Tester les imports
poetry run python -c "from cyclisme_training_logs.mcp_server import server; print('✅ OK')"
```

### 2. Configuration Claude Desktop

**Localisation:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "cyclisme-training": {
      "command": "poetry",
      "args": ["run", "mcp-server"],
      "cwd": "/Users/stephanejouve/cyclisme-training-logs",
      "env": {}
    }
  }
}
```

**Remplacer `/Users/stephanejouve/cyclisme-training-logs` par votre chemin absolu au projet.**

### 3. Redémarrer Claude Desktop

```bash
# Quitter complètement Claude Desktop
# Relancer l'application

# Vérifier dans les settings que le serveur est connecté
# Section "MCP Servers" devrait montrer "cyclisme-training" ✅
```

## 🛠️ Tools Disponibles

### 1. weekly-planner

**Description:** Génère le planning hebdomadaire avec recommandations AI

**Paramètres:**
```json
{
  "week_id": "S082",           // Required: Week ID
  "start_date": "2026-02-23",  // Required: Monday start date (YYYY-MM-DD)
  "provider": "clipboard"      // Optional: AI provider (clipboard/claude_api/mistral_api)
}
```

**Exemple Claude Desktop:**
```
User: "Claude, génère le planning pour la semaine S082 qui commence le 23 février 2026"

Claude: [Calls MCP tool "weekly-planner"]
{
  "week_id": "S082",
  "start_date": "2026-02-23",
  "status": "prompt_generated",
  "prompt_length": 15234,
  "message": "Planning prompt generated for S082"
}
```

### 2. monthly-analysis

**Description:** Analyse mensuelle complète avec stats + insights AI

**Paramètres:**
```json
{
  "month": "2026-01",          // Required: Month (YYYY-MM)
  "provider": "mistral_api",   // Optional: AI provider
  "no_ai": false               // Optional: Skip AI analysis
}
```

**Exemple Claude Desktop:**
```
User: "Génère l'analyse mensuelle de janvier 2026"

Claude: [Calls MCP tool "monthly-analysis"]
{
  "month": "2026-01",
  "report_length": 2845,
  "report": "# 📊 Analyse Mensuelle - January 2026..."
}
```

### 3. daily-sync

**Description:** Synchronise les activités depuis Intervals.icu

**Paramètres:**
```json
{
  "date": "2026-02-21",        // Optional: Date to check (default: today)
  "week_id": "S082"            // Optional: Week ID for planning check
}
```

**Exemple Claude Desktop:**
```
User: "Synchronise les activités d'aujourd'hui"

Claude: [Calls MCP tool "daily-sync"]
{
  "date": "2026-02-21",
  "activities_found": 1,
  "status": "completed",
  "message": "Sync completed for 2026-02-21"
}
```

### 4. update-session

**Description:** Met à jour le statut d'une session

**Paramètres:**
```json
{
  "week_id": "S082",           // Required: Week ID
  "session_id": "S082-03",     // Required: Session ID
  "status": "completed",       // Required: New status
  "reason": "...",             // Optional: Reason (required for skipped/cancelled)
  "sync": false                // Optional: Sync to Intervals.icu
}
```

**Statuts valides:**
- `pending` - En attente
- `planned` - Planifiée
- `uploaded` - Uploadée sur Intervals.icu
- `completed` - Complétée
- `skipped` - Sautée (reason required)
- `cancelled` - Annulée (reason required)
- `rest_day` - Repos
- `replaced` - Remplacée (reason required)
- `modified` - Modifiée

**Exemple Claude Desktop:**
```
User: "Marque la session S082-03 comme complétée"

Claude: [Calls MCP tool "update-session"]
{
  "week_id": "S082",
  "session_id": "S082-03",
  "status": "completed",
  "message": "Session S082-03 updated to completed"
}
```

### 5. list-weeks

**Description:** Liste les plannings hebdomadaires disponibles

**Paramètres:**
```json
{
  "limit": 10,                 // Optional: Max weeks to return (1-52)
  "recent": true               // Optional: Most recent first
}
```

**Exemple Claude Desktop:**
```
User: "Quelles sont les 5 dernières semaines planifiées?"

Claude: [Calls MCP tool "list-weeks" with limit=5]
{
  "total_found": 5,
  "showing": 5,
  "weeks": [
    {
      "week_id": "S082",
      "start_date": "2026-02-23",
      "end_date": "2026-03-01",
      "tss_target": 385,
      "sessions": 7
    },
    ...
  ]
}
```

### 6. get-metrics

**Description:** Récupère les métriques d'entraînement actuelles

**Paramètres:** Aucun

**Exemple Claude Desktop:**
```
User: "Quelles sont mes métriques actuelles?"

Claude: [Calls MCP tool "get-metrics"]
{
  "date": "2026-02-21",
  "ctl": 42,
  "atl": 46,
  "tsb": -3,
  "rampRate": 0.8,
  "ctlLoad": 245,
  "atlLoad": 267
}

Claude: "Tes métriques actuelles:
- CTL (Chronic Training Load): 42
- ATL (Acute Training Load): 46
- TSB (Training Stress Balance): -3 (légère fatigue)
- Ramp Rate: 0.8
"
```

## 📝 Exemples d'Utilisation

### Workflow Complet via Claude Desktop

```
User: "Claude, je veux planifier ma semaine S082 qui commence lundi 23 février"

Claude: [Calls list-weeks to check existing]
       [Calls get-metrics to get current state]
       [Calls weekly-planner with S082, 2026-02-23]

       "Planning généré pour S082! Basé sur tes métriques:
       - CTL: 42 (bonne forme)
       - TSB: -3 (légère fatigue)

       Je recommande:
       - 7 séances
       - 385 TSS total
       - Focus endurance avec 1 séance intensité

       Le prompt est prêt dans ton clipboard."

User: "Super! Maintenant marque S081-07 comme repos car j'étais malade"

Claude: [Calls update-session]
       "✅ Session S081-07 marquée comme repos.
       Raison: Maladie
       Backup créé automatiquement par Control Tower."

User: "Montre-moi l'analyse de janvier"

Claude: [Calls monthly-analysis with month=2026-01]

       "📊 Analyse Janvier 2026:
       - 245 TSS réalisés / 739 cible (33%)
       - 6 sessions complétées
       - 50% adhérence
       - Meilleure semaine: S077 (63.6%)

       💡 Insights:
       - Tendance: Démarrage progressif post-coupure
       - Points forts: Régularité S077-S078
       - À améliorer: Taux de réalisation
       "
```

### Monitoring Quotidien

```
User: "Synchronise mes activités"

Claude: [Calls daily-sync]
       "✅ Sync terminé:
       - 1 activité trouvée aujourd'hui
       - S082-03 marquée 'completed' automatiquement
       - TSS: 72 enregistré"
```

## 🔒 Sécurité

### Permissions

Le MCP server utilise la **Control Tower** pour toutes les modifications:
- ✅ Backup automatique avant chaque modification
- ✅ Audit log complet (WHO/WHY/WHEN/WHAT)
- ✅ Permission system (anti-modifications concurrentes)
- ✅ Validation Pydantic sur toutes les données

### Traçabilité

Toutes les opérations via MCP sont loggées:

```json
{
  "timestamp": "2026-02-21T15:30:45Z",
  "operation": "MODIFY",
  "week_id": "S082",
  "tool": "mcp-server",
  "username": "stephanejouve",
  "reason": "MCP: Update S082-03 to completed",
  "status": "SUCCESS"
}
```

Audit log: `~/data/.planning_audit.jsonl`

## 🆘 Troubleshooting

### Serveur MCP ne démarre pas

```bash
# Vérifier les imports
poetry run python -c "from cyclisme_training_logs.mcp_server import server"

# Vérifier les dépendances
poetry show mcp

# Réinstaller si besoin
poetry install
```

### Claude Desktop ne voit pas le serveur

1. Vérifier le chemin `cwd` dans `claude_desktop_config.json`
2. Vérifier que `poetry run mcp-server` fonctionne en CLI
3. Redémarrer complètement Claude Desktop
4. Checker les logs Claude Desktop: `~/Library/Logs/Claude/`

### Tool call échoue

Les erreurs sont retournées en JSON:

```json
{
  "error": "Session S082-03 not found in S082",
  "tool": "update-session",
  "arguments": {...}
}
```

Vérifier:
- Format des arguments (week_id, dates, etc.)
- Que les fichiers existent
- Permissions filesystem

## 📊 Statistiques

**Tools exposés:** 6
**Protocole:** JSON-RPC 2.0 over stdio
**Transport:** MCP SDK Python
**Sécurité:** Control Tower + Audit Log
**Status:** ✅ Production Ready

## 🔮 Évolutions Futures

### Phase 2 - Tools Supplémentaires

- `end-of-week` - Workflow complet fin de semaine
- `backup-rollback` - Gestion backups/rollback
- `workout-coach` - Coach interactif
- `intelligence-query` - Interroger training intelligence

### Phase 3 - Notifications

- Push notifications sur activités complétées
- Alertes sur métriques (TSB critique, etc.)
- Rappels planification hebdo

### Phase 4 - Intégrations

- Strava sync
- Garmin Connect sync
- Wahoo sync

## 📚 Références

- **MCP Spec:** https://modelcontextprotocol.io/
- **Code Server:** `cyclisme_training_logs/mcp_server.py`
- **Control Tower:** `project-docs/CONTROL_TOWER.md`
- **Features Feb 2026:** `project-docs/FEATURES_FEB_2026.md`

---

**Auteur:** Claude Code
**Date:** 2026-02-21
**Version:** 1.0.0
**Status:** ✅ Production Ready
