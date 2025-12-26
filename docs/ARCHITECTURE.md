# 🏗️ ARCHITECTURE DU PROJET

**Dernière mise à jour :** 2025-12-26
**Version :** 2.0 (Post-Prompt 1 + Gartner TIME)

---

## 📊 CLASSIFICATION GARTNER TIME

Ce projet utilise le framework **Gartner TIME** pour classifier et gérer l'évolution de ses composants :

| Tag | Signification | Icône | Fichiers | Action |
|-----|---------------|-------|----------|--------|
| **I** | **Invest** - Stratégique | 🟢 | ~25 (62%) | Maintenir + Évolution |
| **T** | **Tolerate** - Legacy | 🟡 | ~8 (20%) | Maintenance minimale |
| **M** | **Migrate** - En migration | 🔵 | ~2 (5%) | Migration active |
| **E** | **Eliminate** - À supprimer | 🔴 | ~1 (2%) | Décommissionnement |

**Voir détails :** `GARTNER_TIME_INVENTORY.md`

---

## 🎯 COMPOSANTS PRINCIPAUX

### **Core Workflow** (Priority P0) 🟢

#### `workflow_coach.py` - Orchestrateur Principal
```
GARTNER_TIME: I (Invest)
STATUS: Production
PRIORITY: P0 - Critical

Orchestrateur du workflow quotidien d'analyse de séance.
Guide l'utilisateur à travers : détection type session, collecte feedback,
préparation prompt, validation, insertion, commit.

Usage: poetry run workflow-coach --activity-id i123456
```

#### `config.py` - Configuration Centrale
```
GARTNER_TIME: I (Invest)
STATUS: Production (Post-fix Prompt 1)
PRIORITY: P0 - Critical
RECENT_CHANGES: DataRepoConfig + TRAINING_DATA_REPO

Séparation code/données via DataRepoConfig.
Configuration paths externes vers ~/training-logs.

Usage: Variable TRAINING_DATA_REPO=~/training-logs
```

#### `prepare_analysis.py` - Génération Prompts
```
GARTNER_TIME: I (Invest)
STATUS: Production
PRIORITY: P0 - Critical

Génération prompts Coach pour analyse séance.
Collecte données Intervals.icu, feedback athlète, état workflow.

Usage: poetry run prepare-analysis --activity-id i123456
```

---

### **Insertion & Migration** (Priority P1) 🔵

#### `insert_analysis.py` - Insertion Analyses
```
GARTNER_TIME: M (Migrate)
STATUS: Migration (v1 → v2)
PRIORITY: P1 - High
MIGRATION_TARGET: core/timeline_injector.py

ACTUELLEMENT : Append-only insertion
FUTUR (Prompt 2) : Chronological injection via TimelineInjector

Usage: poetry run insert-analysis [--dry-run]
```

#### `backfill_history.py` - Backfill Historique
```
GARTNER_TIME: M (Migrate)
STATUS: Migration (v1 → v2)
PRIORITY: P2 - Medium
MIGRATION_TARGET: core/timeline_injector.py

Backfill workouts historiques depuis Intervals.icu.
DÉPEND DE : Chronological injection (Prompt 2 Phase 1)

Usage: poetry run backfill-history --start-date 2024-08-01 --limit 10
```

---

### **Intervals.icu Integration** (Priority P1-P2) 🟢

#### `sync_intervals.py` - Synchronisation
```
GARTNER_TIME: I (Invest)
STATUS: Production
PRIORITY: P1 - High

Synchronisation bidirectionnelle avec Intervals.icu.
Upload workouts, download activités, sync état.

Usage: poetry run sync-intervals
```

#### `upload_workouts.py` - Upload Workouts
```
GARTNER_TIME: I (Invest)
STATUS: Production
PRIORITY: P1 - High

Upload fichiers .zwo vers bibliothèque Intervals.icu.

Usage: poetry run upload-workouts workout.zwo
```

#### `planned_sessions_checker.py` - Vérification Sessions
```
GARTNER_TIME: I (Invest)
STATUS: Production
PRIORITY: P2 - Medium

Vérification cohérence sessions planifiées vs réalisées.

Usage: poetry run check-planned-sessions
```

---

### **Analysis & Planning** (Priority P2-P3) 🟡

#### `weekly_planner.py` - Planning Hebdomadaire
```
GARTNER_TIME: T (Tolerate)
STATUS: Production (Legacy)
PRIORITY: P2 - Medium
REPLACEMENT: analyzers/weekly_analyzer.py (Prompt 2 Phase 2)

Planification hebdomadaire actuelle.
SERA REMPLACÉ PAR : Système automatisé v2 (6 reports)

Usage: poetry run weekly-planner --week S073
```

#### `prepare_weekly_report.py` - Rapport Hebdomadaire
```
GARTNER_TIME: T (Tolerate)
STATUS: Production (Legacy)
PRIORITY: P3 - Low
REPLACEMENT: workflows/workflow_weekly.py (Prompt 2 Phase 2)

Préparation rapport hebdomadaire manuel.
SERA REMPLACÉ PAR : Workflow automatisé v2

Usage: poetry run prepare-weekly-report --week S073
```

---

### **AI Providers** (Priority P2) 🟢

Multi-provider AI analysis avec support :
- Mistral API (défaut)
- Claude API
- OpenAI API
- Ollama (local)
- Gemini (expérimental)

```
GARTNER_TIME: I (Invest)
STATUS: Production
PRIORITY: P2 - Medium

Tous fichiers ai_providers/*.py stratégiques.
```

---

## 🗺️ ROADMAP MIGRATIONS

### **Phase 1 : Core Infrastructure** (Semaine 1)
```
Prompt 2 Phase 1 - Création composants v2

🆕 core/timeline_injector.py → 🟢 I (Invest)
🆕 core/data_aggregator.py → 🟢 I (Invest)
🆕 core/prompt_generator.py → 🟢 I (Invest)
🆕 analyzers/daily_aggregator.py → 🟢 I (Invest)

🔵 insert_analysis.py → 🟢 I (après refactor)
🔵 backfill_history.py → 🟢 I (après refactor)
```

### **Phase 2 : Weekly Analysis** (Semaine 2)
```
Prompt 2 Phase 2 - Système hebdomadaire automatisé

🆕 analyzers/weekly_analyzer.py → 🟢 I (Invest)
🆕 analyzers/weekly_aggregator.py → 🟢 I (Invest)
🆕 workflows/workflow_weekly.py → 🟢 I (Invest)

🟡 weekly_planner.py → 🔴 E (deprecated)
🟡 prepare_weekly_report.py → 🔴 E (deprecated)
```

### **Phase 3 : Cleanup** (Semaine 3)
```
Élimination dead code

🔴 weekly_analysis.py → DELETED
🟡 Legacy utilities → ARCHIVED
```

---

## 📝 STANDARDS DOCUMENTATION

### **Docstrings v2**

Tous fichiers doivent suivre template standardisé :

```python
"""
Description concise en une ligne

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Description détaillée en français...

Examples:
    Command-line usage::
        poetry run command --option

    Programmatic usage::
        from module import Class
        obj = Class()
        result = obj.method()

Author: Claude Code
Created: YYYY-MM-DD
"""
```

**Voir détails :** `DOCSTRING_TEMPLATE_V2_GARTNER.md`

---

## 🔍 VALIDATION CONTINUE

### **Script de Validation**

```bash
# Valider tous fichiers
poetry run python scripts/validate_gartner_tags.py

# Rapport HTML
poetry run python scripts/validate_gartner_tags.py --html report.html
```

### **Cadence Review**

| Tag | Fréquence | Action |
|-----|-----------|--------|
| 🟢 I | Monthly | Update LAST_REVIEW |
| 🟡 T | Quarterly | Assess still needed |
| 🔵 M | Weekly | Track migration progress |
| 🔴 E | One-time | Execute elimination |

---

## 🎯 OBJECTIFS PROJET

### **Court Terme (1 mois)**
- ✅ Logs path externe (TRAINING_DATA_REPO) ← FAIT
- 🔵 Chronological injection (Prompt 2 Phase 1)
- 📝 Standardisation docstrings 6 fichiers core (Prompt 3 Priority 1)

### **Moyen Terme (2-3 mois)**
- 📊 Weekly analysis automatisé (6 reports)
- 🔄 Migration complète v1 → v2
- 📚 Documentation 100% v2

### **Long Terme (6 mois)**
- 🚀 Cycle analysis
- 📈 Position query
- 🧹 Élimination legacy complet

---

## 📊 MÉTRIQUES QUALITÉ

**Objectifs :**
- Docstring v2 coverage : 0% → 100%
- Tests passing : 273/273 (100%)
- Gartner I (Invest) : 62% → 80%
- Gartner T/E (Legacy) : 22% → 5%

**Suivi :**
```bash
poetry run python scripts/validate_gartner_tags.py
```

---

**Version :** 2.0
**Dernière mise à jour :** 2025-12-26
**Prochaine révision :** Post-Prompt 2 Phase 1
