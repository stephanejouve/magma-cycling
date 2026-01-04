# Analyse Projets MCP Intervals.icu

**Date :** 2026-01-03
**Analyseur :** Claude Code (Sonnet 4.5)
**Mission :** Analyse comparative 4 implémentations MCP Intervals.icu vs cyclisme-training-logs

---

## 📋 Executive Summary

**Objectif :** Identifier gaps fonctionnels et opportunités d'intégration MCP pour cyclisme-training-logs

**Résultats clés :**
- ✅ **4 projets MCP actifs** détectés (3 matures, 1 alpha)
- ✅ **2 langages dominants** : Python (3/4) et TypeScript (1/4)
- ✅ **Fonctionnalités complémentaires** : Read-only, Write, Grouping, Binaries
- ⚠️ **Gap majeur** : Aucun MCP n'implémente Training Intelligence / Planning avancé
- 🎯 **Opportunité unique** : cyclisme-training-logs dispose de fonctionnalités uniques (Intelligence, PID, Planning)

**Recommandation stratégique :** **Créer MCP distinct** pour cyclisme-training-logs (non fork) → Positionnement "AI Training Coach" vs "Data Access"

---

## 🗂️ Vue d'Ensemble Projets MCP

| Projet | Langage | Status | Tools | Spécialité | License |
|--------|---------|--------|-------|------------|---------|
| **mvilanova/intervals-mcp-server** | Python 3.12+ | ✅ Actif | 6 read-only | Multi-transport (Stdio+SSE) | GPL v3.0 |
| **mrgeorgegray/intervals-icu-mcp** | TypeScript/Node.js 22+ | ✅ Actif | 10 read+write | Event management | GPL v3.0 |
| **VSidhArt/intervals-mcp** | Python 3.12+ (FastMCP) | ✅ Actif | 3 read+grouping | Data aggregation | MIT |
| **notvincent/Intervals-ICU-MCP** | Python | ⚠️ Alpha | 4 write-focused | Workout creation (binaries) | Non spécifié |

---

## 🔬 Analyse Détaillée par Projet

### 1. mvilanova/intervals-mcp-server

**GitHub :** https://github.com/mvilanova/intervals-mcp-server
**Status :** ✅ **Actif** (Featured on Glama.ai, communauté active)
**Langage :** Python 3.12+
**MCP SDK :** Officiel (`mcp[cli]>=1.4.0`)

**Architecture :**
```
src/intervals_mcp_server/
├── api/
│   └── client.py          # HTTP client Intervals.icu
├── tools/
│   ├── activities.py      # MCP tools activités
│   ├── events.py          # MCP tools événements
│   └── wellness.py        # MCP tools wellness
├── utils/
│   ├── dates.py
│   ├── formatting.py
│   └── validation.py
└── server.py              # Entry point MCP
```

**Tools MCP implémentés (6) :**
1. `get_activities` - Liste activités (date range, filtre unnamed)
2. `get_activity_details` - Détails activité (power, HR, GPS)
3. `get_activity_intervals` - Intervalles détaillés activité
4. `get_wellness_data` - Données wellness (sleep, HRV, etc.)
5. `get_events` - Événements planifiés (workouts, races)
6. `get_event_by_id` - Détails événement spécifique

**Transports supportés :**
- **Stdio** (Claude Desktop)
- **SSE** (ChatGPT beta MCP connectors via `FASTMCP_HOST/PORT`)

**Points forts :**
- ✅ Documentation complète (README 220 lignes)
- ✅ Tests pytest (coverage `test_*.py`)
- ✅ CI/CD GitHub Actions (pylint, python-app, stale)
- ✅ Pre-commit hooks
- ✅ Multi-plateforme (Claude + ChatGPT)
- ✅ Featured Glama.ai (badge officiel)

**Limitations :**
- ❌ **Read-only** (aucune création/modification événements)
- ❌ Pas d'analyse AI
- ❌ Pas de planning avancé
- ❌ Pas d'agrégation données (verbeux pour grandes périodes)

**Dependencies clés :**
```toml
dependencies = [
    "mcp[cli]>=1.4.0",
    "httpx>=0.25.0",
    "python-dotenv>=1.0.0"
]
```

---

### 2. mrgeorgegray/intervals-icu-mcp

**GitHub :** https://github.com/mrgeorgegray/intervals-icu-mcp
**Status :** ✅ **Actif** (Inspiré de mvilanova, alternative TypeScript)
**Langage :** TypeScript, Node.js 22+
**MCP SDK :** Officiel

**Architecture :**
```
src/
├── client/
│   └── generated/        # OpenAPI TypeScript client auto-généré
├── tools/                # MCP tool implementations
├── utils/                # Utility functions
└── index.ts              # Main server entry point
```

**Tools MCP implémentés (10) :**

**Activity Tools (2) :**
1. `getActivities` - Liste activités (date range, limit, unnamed)
2. `getActivityDetails` - Détails activité (power, HR, GPS)

**Event Management (6) :**
3. `createEvent` - **Créer événement** (workout, race, note)
4. `createBulkEvents` - **Créer événements en masse** (training blocks)
5. `deleteEvent` - **Supprimer événement**
6. `deleteBulkEvents` - **Supprimer événements en masse**
7. `getEvents` - Liste événements (filtre date/type)
8. `getEventDetails` - Détails événement spécifique

**Profile & Wellness (2) :**
9. `getAthleteDetails` - Profil athlète (stats, achievements)
10. `getWellnessData` - Données wellness (sleep, stress, fatigue)

**Points forts :**
- ✅ **Read + Write** (création/suppression événements)
- ✅ **Bulk operations** (efficace pour training blocks)
- ✅ **OpenAPI client auto-généré** (`@hey-api/openapi-ts`)
- ✅ MCP Inspector support (debugging)
- ✅ TypeScript type-safety
- ✅ Documentation complète (207 lignes)

**Limitations :**
- ❌ Pas d'analyse AI
- ❌ Pas de planning avancé (création simple seulement)
- ❌ Pas d'agrégation données
- ❌ Transport Stdio uniquement (pas SSE)

**Dependencies clés :**
```json
"dependencies": {
  "@modelcontextprotocol/sdk": "^1.x",
  "@hey-api/openapi-ts": "^x.x.x",
  "dotenv": "^16.x"
}
```

---

### 3. VSidhArt/intervals-mcp

**GitHub :** https://github.com/VSidhArt/intervals-mcp
**Status :** ✅ **Actif**
**Langage :** Python 3.12+
**MCP SDK :** **FastMCP** (alternative SDK, pas officiel)

**Architecture :**
```
intervals-mcp/
├── main.py                # Entry point
├── server.py              # FastMCP server instance
├── tools/
│   ├── activities.py      # Activities tools (get, get_grouped)
│   └── wellness.py        # Wellness tools
└── utils/
    └── intervals_client.py # HTTP client
```

**Tools MCP implémentés (3) :**

**Activity Tools (2) :**
1. `get_activities(oldest_date, newest_date)` - Activités détaillées
2. `get_grouped_activities(oldest_date, newest_date, group_by, include_details)` - **Activités groupées/agrégées**
   - **group_by** : `"sport"`, `"day"`, `"week"`, `"month"`
   - **Retourne** : Counts, totals, averages par groupe
   - **Optimisé** : Grandes périodes (réduit verbosité)

**Wellness Tools (1) :**
3. `get_wellness(oldest_date, newest_date)` - Données wellness

**Points forts :**
- ✅ **Data grouping/aggregation** (unique parmi 4 projets)
- ✅ **Clean data output** (filtre empty/null values automatiquement)
- ✅ **Optimisé grandes périodes** (réduit token usage AI)
- ✅ **FastMCP framework** (alternative MCP SDK)
- ✅ License MIT (plus permissive)

**Limitations :**
- ❌ Read-only (pas création/modification)
- ❌ Tools limités (3 vs 6-10 autres projets)
- ❌ Pas d'event management
- ❌ Pas d'analyse AI

**FastMCP vs MCP officiel :**
- FastMCP = Framework Python simplifié pour MCP
- Moins verbeux que MCP SDK officiel
- Bonne option pour prototypes rapides

---

### 4. notvincent/Intervals-ICU-MCP

**GitHub :** https://github.com/notvincent/Intervals-ICU-MCP
**Status :** ⚠️ **Alpha** (v0.0.01-alpha)
**Langage :** Python
**MCP SDK :** Officiel

**Architecture :**
- **Binaries pré-compilés** (PyInstaller) : Windows (.exe), macOS, Linux
- Focus : **Utilisateurs non-techniques** (pas besoin Python)

**Tools MCP implémentés (4) :**

**Workout Management (4) :**
1. `CreateWorkouts` - **Créer workouts multiples** (descriptions structurées)
2. `ListEvents` - Liste événements (filtres)
3. `UpdateEvent` - **Modifier workout existant** (by ID)
4. `DeleteEvents` - **Supprimer événements multiples** (by IDs)

**Points forts :**
- ✅ **Pre-built binaries** (Windows/macOS/Linux) → Zero setup utilisateurs
- ✅ **Write-focused** (création/modification/suppression workouts)
- ✅ Documentation ultra-simple (screenshots, GIFs)
- ✅ **Training plan builder demo** (GIF animé)
- ✅ Target non-techniques (Claude.ai free tier recommended)

**Limitations :**
- ⚠️ **Alpha status** (v0.0.01-alpha, immaturité)
- ❌ Pas de read activities/wellness
- ❌ License non spécifiée (légal unclear)
- ❌ Pas de tests visibles
- ❌ Documentation technique limitée

**Use case principal :**
- **Utilisateur non-technique** veut créer plans entraînement via Claude.ai
- Double-click binary → Configure API key → Go

---

## 📊 Tableau Comparatif Fonctionnalités

| Feature | mvilanova | mrgeorgegray | VSidhArt | notvincent | **cyclisme-training-logs** |
|---------|-----------|--------------|----------|------------|----------------------------|
| **Read Activities** | ✅ | ✅ | ✅ | ❌ | ✅ (IntervalsClient) |
| **Read Activities Details** | ✅ | ✅ | ❌ | ❌ | ✅ (IntervalsClient) |
| **Read Activities Intervals** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Read Wellness** | ✅ | ✅ | ✅ | ❌ | ✅ (IntervalsClient) |
| **Read Events** | ✅ | ✅ | ❌ | ✅ | ✅ (IntervalsClient) |
| **Read Athlete Profile** | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Create Events** | ❌ | ✅ | ❌ | ✅ | ✅ (upload_workouts) |
| **Update Events** | ❌ | ❌ | ❌ | ✅ | ✅ (update_session_status) |
| **Delete Events** | ❌ | ✅ | ❌ | ✅ | ❌ |
| **Bulk Operations** | ❌ | ✅ | ❌ | ❌ | ✅ (upload_workouts batch) |
| **Data Grouping/Aggregation** | ❌ | ❌ | ✅ | ❌ | ✅ (weekly_aggregator, daily_aggregator) |
| **Weekly Analysis** | ❌ | ❌ | ❌ | ❌ | ✅ (weekly_analysis.py) |
| **Monthly Analysis** | ❌ | ❌ | ❌ | ❌ | ✅ (monthly_analysis.py) |
| **Training Intelligence** | ❌ | ❌ | ❌ | ❌ | ✅ (training_intelligence.py) |
| **PID Controller** | ❌ | ❌ | ❌ | ❌ | ✅ (pid_controller.py) |
| **Planning Manager** | ❌ | ❌ | ❌ | ❌ | ✅ (planning_manager.py) |
| **Weekly Planner** | ❌ | ❌ | ❌ | ❌ | ✅ (weekly_planner.py) |
| **Backfill Intelligence** | ❌ | ❌ | ❌ | ❌ | ✅ (backfill_intelligence.py) |
| **AI Providers** | ❌ | ❌ | ❌ | ❌ | ✅ (OpenAI, Claude, Mistral, Ollama) |
| **Workflow Coach** | ❌ | ❌ | ❌ | ❌ | ✅ (workflow_coach.py) |

---

## 🔍 Gaps Identifiés

### Gaps MCP Projects vs cyclisme-training-logs

**1. Analyse Intelligente**
- ❌ **Aucun MCP** n'implémente analyse AI avancée
- ✅ **cyclisme-training-logs** : Training Intelligence (learnings, patterns, adaptations)
- ✅ **cyclisme-training-logs** : PID Controller adaptatif (FTP progression)
- ✅ **cyclisme-training-logs** : Backfill historique (2+ ans données)

**2. Planning Avancé**
- ❌ **MCP projets** : Création événements simples uniquement
- ✅ **cyclisme-training-logs** : Planning Manager (constraints, calendar logic)
- ✅ **cyclisme-training-logs** : Weekly Planner (distribution TSS, recovery)
- ✅ **cyclisme-training-logs** : Workflow Coach (pipeline complet)

**3. Multi-AI Support**
- ❌ **MCP projets** : MCP servers (Claude/ChatGPT uniquement)
- ✅ **cyclisme-training-logs** : 4 AI providers (OpenAI, Claude, Mistral, Ollama)
- ✅ **cyclisme-training-logs** : Clipboard fallback (0 API cost)

**4. Agrégation Temporelle**
- ⚠️ **VSidhArt** : Grouping basique (sport/day/week/month)
- ✅ **cyclisme-training-logs** : Agrégateurs sophistiqués (weekly_aggregator, daily_aggregator)
- ✅ **cyclisme-training-logs** : Métriques avancées (IF zones, TSS distribution, recovery metrics)

**5. État Workflow**
- ❌ **Aucun MCP** : Gestion état workflow
- ✅ **cyclisme-training-logs** : workflow_state.py (tracking progression tâches)
- ✅ **cyclisme-training-logs** : manage_workflow_state.py (orchestration)

---

### Gaps cyclisme-training-logs vs MCP Projects

**1. MCP Server**
- ❌ **cyclisme-training-logs** : Pas de serveur MCP
- ✅ **MCP projets** : Serveurs MCP prêts (Claude Desktop integration)

**2. Delete Operations**
- ❌ **cyclisme-training-logs** : Pas de suppression événements
- ✅ **mrgeorgegray, notvincent** : Delete events (single + bulk)

**3. Pre-built Binaries**
- ❌ **cyclisme-training-logs** : Installation Python requise
- ✅ **notvincent** : Binaries Windows/macOS/Linux (zero setup)

**4. TypeScript Option**
- ❌ **cyclisme-training-logs** : Python uniquement
- ✅ **mrgeorgegray** : TypeScript/Node.js (écosystème différent)

---

## 🎯 Recommandations Stratégiques

### Option 1 : Créer MCP Server Distinct (Recommandé)

**Positionnement :** "AI Training Coach" vs "Data Access Layer"

**Rationale :**
- cyclisme-training-logs possède **fonctionnalités uniques** (Intelligence, PID, Planning)
- MCP projets existants = **Data access basique** (CRUD Intervals.icu)
- **Proposition valeur différente** : Coach AI vs API wrapper

**Architecture proposée :**
```
cyclisme-training-logs-mcp/
├── src/
│   ├── server.py              # MCP server entry point
│   └── tools/
│       ├── intelligence.py    # Training Intelligence tools
│       ├── planning.py        # Planning Manager tools
│       ├── analysis.py        # Weekly/Monthly analysis tools
│       └── workflow.py        # Workflow Coach tools
└── pyproject.toml
```

**Tools MCP recommandés (12) :**

**Intelligence Tools (4) :**
1. `get_training_learnings` - Récupérer learnings accumulés
2. `add_training_learning` - Ajouter learning manuel
3. `get_training_patterns` - Patterns récurrents détectés
4. `get_pid_correction` - Correction PID pour FTP target

**Planning Tools (4) :**
5. `generate_weekly_plan` - Générer plan semaine (TSS target, recovery)
6. `get_planning_constraints` - Contraintes athlète (availability, equipment)
7. `validate_plan` - Valider plan vs contraintes
8. `upload_plan_to_intervals` - Push plan Intervals.icu

**Analysis Tools (4) :**
9. `analyze_week` - Analyse semaine complète (AI-powered)
10. `analyze_month` - Analyse mensuelle (trends, progression)
11. `get_weekly_aggregates` - Agrégats hebdomadaires (TSS, IF, zones)
12. `backfill_intelligence` - Backfill historique → Intelligence

**Avantages :**
- ✅ **Positionnement unique** (coach AI, pas data access)
- ✅ **Valorise IP existante** (Intelligence, PID, Planning)
- ✅ **Pas de concurrence directe** avec projets existants
- ✅ **Potentiel communauté** (featured Glama.ai, forum Intervals.icu)
- ✅ **Multi-plateforme** (Claude Desktop + ChatGPT SSE)

**Effort estimé :** 3-4 jours (MCP wrapper sur code existant)

---

### Option 2 : Contribuer à Projet Existant

**Meilleur candidat :** **mvilanova/intervals-mcp-server**

**Rationale :**
- ✅ Projet le plus mature (tests, CI/CD, featured Glama.ai)
- ✅ Python (même stack)
- ✅ Architecture propre (easy to extend)
- ✅ Communauté active (forum Intervals.icu)

**Contributions proposées :**
1. **PR 1** : Add `get_grouped_activities` tool (inspiration VSidhArt)
2. **PR 2** : Add `create_event`/`delete_event` tools (inspiration mrgeorgegray)
3. **PR 3** : Add advanced aggregation utils (cyclisme-training-logs)

**Avantages :**
- ✅ **Quick win** (contribution communauté)
- ✅ **Leverage existing userbase** (Glama.ai featured)
- ✅ **Code review externe** (améliore qualité)

**Inconvénients :**
- ❌ **Dilue IP cyclisme-training-logs** (Intelligence/PID/Planning intégré projet tiers)
- ❌ **Moins de contrôle** (architecture, roadmap)
- ❌ **License GPL v3.0** (copyleft, contraint usages commerciaux futurs)

**Effort estimé :** 2-3 jours par PR

---

### Option 3 : Fork + Enhance

**Meilleur candidat :** **mvilanova/intervals-mcp-server**

**Modifications proposées :**
1. Fork `mvilanova/intervals-mcp-server`
2. Ajouter modules cyclisme-training-logs :
   - `tools/intelligence.py`
   - `tools/planning.py`
   - `tools/analysis.py`
3. Renommer `cyclisme-training-logs-mcp-enhanced`

**Avantages :**
- ✅ **Base solide** (tests, CI/CD)
- ✅ **Quick start** (pas MCP from scratch)
- ✅ **Contrôle total** (roadmap, features)

**Inconvénients :**
- ⚠️ **License GPL v3.0 héritée** (copyleft)
- ❌ **Maintenance divergence** (sync upstream mvilanova)
- ❌ **Confusion communauté** (fork vs original)

**Effort estimé :** 3-4 jours

---

### Option 4 : Addon MCP Distinct

**Concept :** Serveur MCP **complémentaire** aux projets existants

**Architecture :**
- **mvilanova/intervals-mcp-server** : Data access (activities, events, wellness)
- **cyclisme-training-logs-mcp** : AI coach (intelligence, planning, analysis)
- **Usage combiné** : Utilisateur configure les 2 MCP servers dans Claude Desktop

**Config Claude Desktop :**
```json
{
  "mcpServers": {
    "intervals-data": {
      "command": "/path/to/uv",
      "args": ["run", "mvilanova/intervals-mcp-server/server.py"],
      "env": { "API_KEY": "xxx", "ATHLETE_ID": "ixxx" }
    },
    "intervals-coach": {
      "command": "/path/to/uv",
      "args": ["run", "cyclisme-training-logs-mcp/server.py"],
      "env": { "API_KEY": "xxx", "ATHLETE_ID": "ixxx" }
    }
  }
}
```

**Avantages :**
- ✅ **Séparation concerns** (data vs intelligence)
- ✅ **Pas de concurrence** (complémentaire)
- ✅ **License libre** (MIT ou GPL v3.0 au choix)
- ✅ **Communauté win-win** (référence mutuelle)

**Inconvénients :**
- ⚠️ **2 serveurs MCP** (complexité setup utilisateur)
- ⚠️ **Duplication data access** (si cyclisme-training-logs-mcp réimplémente get_activities)

**Effort estimé :** 3 jours

---

## 📐 Comparaison Options

| Critère | Option 1 (Distinct) | Option 2 (Contribute) | Option 3 (Fork) | Option 4 (Addon) |
|---------|---------------------|------------------------|------------------|-------------------|
| **Effort** | 3-4 jours | 2-3 jours/PR | 3-4 jours | 3 jours |
| **Contrôle IP** | ✅ Total | ❌ Dilué | ✅ Total | ✅ Total |
| **License** | ✅ Libre choix | ❌ GPL v3.0 | ❌ GPL v3.0 | ✅ Libre choix |
| **Communauté** | ⚠️ Build from scratch | ✅ Leverage existing | ⚠️ Fork stigma | ✅ Complémentaire |
| **Positionnement** | ✅ Unique (Coach AI) | ❌ Generic (data) | ⚠️ Mixed | ✅ Unique (Coach AI) |
| **Maintenance** | ✅ Indépendant | ⚠️ Dépend upstream | ⚠️ Sync upstream | ✅ Indépendant |

**Recommandation MOA :** **Option 1 (MCP Distinct)** ou **Option 4 (Addon)**

**Justification :**
- ✅ **Valorise IP cyclisme-training-logs** (Intelligence/PID/Planning)
- ✅ **Positionnement différencié** ("AI Training Coach" vs "Data Access")
- ✅ **License libre** (MIT recommended pour adoption communauté)
- ✅ **Pas de concurrence directe** avec projets existants

---

## 🚀 Roadmap Implémentation (Option 1 Recommandée)

### Phase 1 : MCP Core (1-2 jours)

**Objectif :** Serveur MCP minimal fonctionnel

**Tasks :**
1. Setup projet MCP (`pyproject.toml`, dependencies)
2. Implement MCP server entry point (`server.py`)
3. Wrapper IntervalsClient (réutiliser cyclisme-training-logs)
4. Implement 2 tools basiques :
   - `get_training_learnings`
   - `analyze_week`
5. Test Claude Desktop integration

**Deliverables :**
- `cyclisme-training-logs-mcp/` repository
- 2 MCP tools fonctionnels
- README.md setup instructions

---

### Phase 2 : Intelligence Tools (1 jour)

**Objectif :** Exposer Training Intelligence via MCP

**Tasks :**
1. Implement `tools/intelligence.py` :
   - `get_training_learnings(level=None, category=None)`
   - `add_training_learning(category, description, evidence, level)`
   - `get_training_patterns(confidence=None)`
   - `get_pid_correction(current_ftp, target_ftp, dt=1.0)`
2. Tests unitaires
3. Documentation tools (docstrings + README examples)

**Deliverables :**
- 4 Intelligence tools
- Tests passing
- README examples

---

### Phase 3 : Planning Tools (1 jour)

**Objectif :** Exposer Planning Manager via MCP

**Tasks :**
1. Implement `tools/planning.py` :
   - `generate_weekly_plan(target_tss, athlete_profile, constraints)`
   - `get_planning_constraints(athlete_id)`
   - `validate_plan(plan_json)`
   - `upload_plan_to_intervals(plan_json, week_id)`
2. Tests unitaires
3. Documentation

**Deliverables :**
- 4 Planning tools
- Tests passing

---

### Phase 4 : Analysis Tools (0.5 jour)

**Objectif :** Exposer Analyzers via MCP

**Tasks :**
1. Implement `tools/analysis.py` :
   - `analyze_week(week_id, ai_provider=None)`
   - `analyze_month(month_id)`
   - `get_weekly_aggregates(week_id)`
   - `backfill_intelligence(start_date, end_date)`
2. Tests
3. Documentation

**Deliverables :**
- 4 Analysis tools
- Tests passing

---

### Phase 5 : Polish & Release (0.5 jour)

**Objectif :** Publication communauté

**Tasks :**
1. README complet (setup, usage, examples)
2. LICENSE (MIT recommended)
3. CHANGELOG.md
4. GitHub release v1.0.0
5. Publish Glama.ai (featured badge)
6. Post forum Intervals.icu (announcement)

**Deliverables :**
- GitHub release public
- Glama.ai listing
- Forum announcement

---

## 📚 Références Techniques

### MCP SDK Documentation

**Official MCP Docs :**
- https://modelcontextprotocol.io/overview
- https://github.com/modelcontextprotocol/python-sdk

**FastMCP (Alternative) :**
- https://github.com/gptscript-ai/fastmcp (si Option 1 avec FastMCP)

### Intervals.icu API

**API Docs :**
- https://intervals.icu/api-docs.html
- https://forum.intervals.icu/t/api-access-to-intervals-icu/609

**OpenAPI Spec :**
- https://intervals.icu/openapi-spec.json (utilisé par mrgeorgegray pour client auto-généré)

### Projets Référencés

1. **mvilanova/intervals-mcp-server** : https://github.com/mvilanova/intervals-mcp-server
2. **mrgeorgegray/intervals-icu-mcp** : https://github.com/mrgeorgegray/intervals-icu-mcp
3. **VSidhArt/intervals-mcp** : https://github.com/VSidhArt/intervals-mcp
4. **notvincent/Intervals-ICU-MCP** : https://github.com/notvincent/Intervals-ICU-MCP

---

## 🔚 Conclusion

**Synthèse :**
- ✅ **4 projets MCP actifs** analysés (3 matures Python/TypeScript, 1 alpha binaries)
- ✅ **Gap majeur identifié** : Aucun MCP n'implémente Training Intelligence/Planning avancé
- ✅ **Opportunité unique** : cyclisme-training-logs possède IP différenciante (Intelligence, PID, Planning)
- ✅ **Recommandation** : Créer **MCP distinct** positionné "AI Training Coach" (pas fork)

**Prochaine étape :**
- **Décision PO** : Quelle option stratégique ? (1=Distinct, 2=Contribute, 3=Fork, 4=Addon)
- **Si Option 1** : Démarrer Phase 1 roadmap (setup MCP core)

**Questions PO :**
1. Priorité : Développer MCP server maintenant, ou après autres features cyclisme-training-logs ?
2. License préférée : MIT (permissive) ou GPL v3.0 (copyleft) ?
3. Positionnement : "AI Coach" standalone ou addon "mvilanova/intervals-mcp-server" ?

---

**Rapport généré par :** Claude Code (Sonnet 4.5)
**Date :** 2026-01-03
**Durée analyse :** ~2h
**Repositories clonés :** `/tmp/mcp-analysis/` (4 projets)
**Status :** ✅ Analyse complète, recommandations stratégiques livrées
