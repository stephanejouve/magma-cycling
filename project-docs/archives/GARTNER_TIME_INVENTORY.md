# 🏷️ INVENTAIRE GARTNER TIME - Cyclisme Training Logs

**Date :** 26 décembre 2025
**Version projet :** Post-Prompt 1 (Logs Path Fix)
**Total fichiers :** ~40 Python files

---

## 📋 LÉGENDE TAGS

| Tag | Signification | Icône | Action |
|-----|---------------|-------|--------|
| **I** | **Invest** - Stratégique, investissement actif | 🟢 | Maintenir + Évolution |
| **T** | **Tolerate** - Fonctionnel mais legacy | 🟡 | Maintenance minimale |
| **M** | **Migrate** - En cours de migration v2 | 🔵 | Migration active |
| **E** | **Eliminate** - À supprimer | 🔴 | Décommissionnement |

---

## 🎯 CORE WORKFLOW FILES

### **workflow_coach.py** 🟢
```
GARTNER_TIME: I (Invest)
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P0 - Critical
DOCSTRING: v1 (À standardiser → Prompt 3)
NEXT_ACTION: Standardize docstring + Add DailyAggregator (Prompt 2)
```

**Raison I :** Orchestrateur principal workflow, utilisé quotidiennement

---

### **prepare_analysis.py** 🟢
```
GARTNER_TIME: I (Invest)
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P0 - Critical
DOCSTRING: v1 (À standardiser → Prompt 3)
NEXT_ACTION: Standardize docstring
```

**Raison I :** Génération prompts Coach, core workflow

---

### **insert_analysis.py** 🔵
```
GARTNER_TIME: M (Migrate)
STATUS: Migration (v1 → v2 chronological)
LAST_REVIEW: 2025-12-26
PRIORITY: P1 - High
MIGRATION_TARGET: core/timeline_injector.py
DOCSTRING: v1 (À standardiser → Prompt 3)
NEXT_ACTION: Refactor with TimelineInjector (Prompt 2 Phase 1)
```

**Raison M :** Migration vers injection chronologique v2

---

### **backfill_history.py** 🔵
```
GARTNER_TIME: M (Migrate)
STATUS: Migration (v1 → v2 chronological)
LAST_REVIEW: 2025-12-26
PRIORITY: P2 - Medium
MIGRATION_TARGET: core/timeline_injector.py
DOCSTRING: v1 (À standardiser → Prompt 3)
NEXT_ACTION: Use TimelineInjector (Prompt 2 Phase 1)
```

**Raison M :** Dépend de chronological injection

---

### **config.py** 🟢
```
GARTNER_TIME: I (Invest)
STATUS: Production (Post-fix Prompt 1)
LAST_REVIEW: 2025-12-26
PRIORITY: P0 - Critical
RECENT_CHANGES: DataRepoConfig + TRAINING_DATA_REPO
DOCSTRING: v1 partial (À compléter → Prompt 3)
NEXT_ACTION: Complete docstring with Examples
```

**Raison I :** Configuration centrale, fraîchement refactorisé

---

### **manage_state.py** 🟢
```
GARTNER_TIME: I (Invest)
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1 - High
DOCSTRING: v1 (À standardiser → Prompt 3)
NEXT_ACTION: Standardize docstring
```

**Raison I :** Gestion état workflow, essentiel

---

## 📊 ANALYSIS & PLANNING FILES

### **weekly_planner.py** 🟡
```
GARTNER_TIME: T (Tolerate)
STATUS: Production (Legacy)
LAST_REVIEW: 2025-12-26
PRIORITY: P2 - Medium
REPLACEMENT: analyzers/weekly_analyzer.py (Prompt 2 Phase 2)
DOCSTRING: v1 (À standardiser → Prompt 3)
NEXT_ACTION: Tolerate until v2 weekly analysis ready
```

**Raison T :** Fonctionnel mais sera remplacé par v2

---

### **prepare_weekly_report.py** 🟡
```
GARTNER_TIME: T (Tolerate)
STATUS: Production (Legacy)
LAST_REVIEW: 2025-12-26
PRIORITY: P3 - Low
REPLACEMENT: workflows/workflow_weekly.py (Prompt 2 Phase 2)
DOCSTRING: v1 minimal
NEXT_ACTION: Tolerate until v2 ready
```

**Raison T :** Sera remplacé par workflow automatisé v2

---

### **weekly_analysis.py** 🔴
```
GARTNER_TIME: E (Eliminate)
STATUS: Deprecated (Duplicate de weekly_planner)
LAST_REVIEW: 2025-12-26
PRIORITY: P4 - Cleanup
DEPRECATION_DATE: 2025-12-26
NEXT_ACTION: Vérifier si utilisé, sinon supprimer
```

**Raison E :** Probable duplicate, non documenté

---

### **organize_weekly_report.py** 🟡
```
GARTNER_TIME: T (Tolerate)
STATUS: Production (Utility)
LAST_REVIEW: 2025-12-26
PRIORITY: P3 - Low
DOCSTRING: v1 minimal
NEXT_ACTION: Tolerate, low priority standardization
```

**Raison T :** Utilitaire fonctionnel mais non critique

---

### **normalize_weekly_reports_casing.py** 🟡
```
GARTNER_TIME: T (Tolerate)
STATUS: Production (One-time utility)
LAST_REVIEW: 2025-12-26
PRIORITY: P4 - Cleanup
DOCSTRING: None
NEXT_ACTION: Document or eliminate
```

**Raison T :** Script one-time, à garder pour référence

---

## 🔧 INTERVALS.ICU INTEGRATION

### **sync_intervals.py** 🟢
```
GARTNER_TIME: I (Invest)
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1 - High
DOCSTRING: v1 (À standardiser → Prompt 3)
NEXT_ACTION: Standardize docstring
```

**Raison I :** Synchronisation critique avec Intervals.icu

---

### **upload_workouts.py** 🟢
```
GARTNER_TIME: I (Invest)
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1 - High
DOCSTRING: v1 (À standardiser → Prompt 3)
NEXT_ACTION: Standardize docstring
```

**Raison I :** Upload workouts vers Intervals.icu

---

### **planned_sessions_checker.py** 🟢
```
GARTNER_TIME: I (Invest)
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P2 - Medium
DOCSTRING: v1 (À standardiser → Prompt 3)
NEXT_ACTION: Standardize docstring
```

**Raison I :** Vérification sessions planifiées

---

### **intervals_format_validator.py** 🟢
```
GARTNER_TIME: I (Invest)
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P2 - Medium
DOCSTRING: v1 (À standardiser → Prompt 3)
NEXT_ACTION: Standardize docstring
```

**Raison I :** Validation formats workouts

---

## 🛠️ UTILITIES

### **rest_and_cancellations.py** 🟢
```
GARTNER_TIME: I (Invest)
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P2 - Medium
DOCSTRING: v1 (À standardiser → Prompt 3)
NEXT_ACTION: Standardize docstring
```

**Raison I :** Gestion repos/annulations

---

### **workflow_state.py** 🟢
```
GARTNER_TIME: I (Invest)
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1 - High
DOCSTRING: v1 (À standardiser → Prompt 3)
NEXT_ACTION: Standardize docstring
```

**Raison I :** Gestion état workflow persistant

---

### **stats.py** 🟡
```
GARTNER_TIME: T (Tolerate)
STATUS: Production (Utility)
LAST_REVIEW: 2025-12-26
PRIORITY: P3 - Low
DOCSTRING: v1 minimal
NEXT_ACTION: Low priority standardization
```

**Raison T :** Statistiques basiques, non critique

---

## 🤖 AI PROVIDERS

### **ai_providers/__init__.py** 🟢
```
GARTNER_TIME: I (Invest)
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P2 - Medium
DOCSTRING: v1 (À standardiser → Prompt 3)
NEXT_ACTION: Standardize docstring
```

---

### **ai_providers/mistral_api.py** 🟢
```
GARTNER_TIME: I (Invest)
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P2 - Medium
DOCSTRING: v1 (À standardiser → Prompt 3)
NEXT_ACTION: Standardize docstring
```

---

### **ai_providers/claude_api.py** 🟢
```
GARTNER_TIME: I (Invest)
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P2 - Medium
DOCSTRING: v1 (À standardiser → Prompt 3)
NEXT_ACTION: Standardize docstring
```

---

### **ai_providers/openai_api.py** 🟢
```
GARTNER_TIME: I (Invest)
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P2 - Medium
DOCSTRING: v1 (À standardiser → Prompt 3)
NEXT_ACTION: Standardize docstring
```

---

### **ai_providers/ollama_api.py** 🟢
```
GARTNER_TIME: I (Invest)
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P2 - Medium
DOCSTRING: v1 (À standardiser → Prompt 3)
NEXT_ACTION: Standardize docstring
```

---

### **ai_providers/gemini_api.py** 🟡
```
GARTNER_TIME: T (Tolerate)
STATUS: Production (Experimental)
LAST_REVIEW: 2025-12-26
PRIORITY: P3 - Low
DOCSTRING: v1 minimal
NEXT_ACTION: Monitor usage, standardize if adopted
```

**Raison T :** Provider expérimental, usage faible

---

## 🧪 TESTS

### **test_*.py (10+ fichiers)** 🟢
```
GARTNER_TIME: I (Invest)
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P2 - Medium (All tests)
DOCSTRING: v1 minimal (À standardiser → Prompt 3 Priority 4)
NEXT_ACTION: Standardize all test docstrings (batch)
```

**Raison I :** Tests critiques pour validation

---

## 🚀 NOUVEAUX FICHIERS (À CRÉER - Prompt 2)

### **core/timeline_injector.py** 🆕
```
GARTNER_TIME: I (Invest)
STATUS: Development (Prompt 2 Phase 1)
LAST_REVIEW: N/A
PRIORITY: P0 - Critical
MIGRATION_SOURCE: insert_analysis.py (partial)
DOCSTRING: v2 standard (création)
NEXT_ACTION: Create from v2 markdown_parser.py
```

---

### **core/data_aggregator.py** 🆕
```
GARTNER_TIME: I (Invest)
STATUS: Development (Prompt 2 Phase 1)
LAST_REVIEW: N/A
PRIORITY: P0 - Critical
DOCSTRING: v2 standard (création)
NEXT_ACTION: Migrate from v2 project
```

---

### **core/prompt_generator.py** 🆕
```
GARTNER_TIME: I (Invest)
STATUS: Development (Prompt 2 Phase 1)
LAST_REVIEW: N/A
PRIORITY: P1 - High
DOCSTRING: v2 standard (création)
NEXT_ACTION: Migrate from v2 project
```

---

### **analyzers/daily_aggregator.py** 🆕
```
GARTNER_TIME: I (Invest)
STATUS: Development (Prompt 2 Phase 1)
LAST_REVIEW: N/A
PRIORITY: P1 - High
DOCSTRING: v2 standard (création)
NEXT_ACTION: Create from DataAggregator
```

---

### **analyzers/weekly_aggregator.py** 🆕
```
GARTNER_TIME: I (Invest)
STATUS: Development (Prompt 2 Phase 2)
LAST_REVIEW: N/A
PRIORITY: P1 - High
DOCSTRING: v2 standard (création)
NEXT_ACTION: Create from DataAggregator
```

---

### **analyzers/weekly_analyzer.py** 🆕
```
GARTNER_TIME: I (Invest)
STATUS: Development (Prompt 2 Phase 2)
LAST_REVIEW: N/A
PRIORITY: P1 - High
REPLACEMENT_FOR: weekly_planner.py
DOCSTRING: v2 standard (création)
NEXT_ACTION: Migrate from v2 project
```

---

### **workflows/workflow_weekly.py** 🆕
```
GARTNER_TIME: I (Invest)
STATUS: Development (Prompt 2 Phase 2)
LAST_REVIEW: N/A
PRIORITY: P1 - High
REPLACEMENT_FOR: prepare_weekly_report.py
DOCSTRING: v2 standard (création)
NEXT_ACTION: Migrate from v2 project
```

---

## 📊 STATISTIQUES CLASSIFICATION

### **Par Tag Gartner TIME**

| Tag | Count | Pourcentage | Description |
|-----|-------|-------------|-------------|
| 🟢 **I** (Invest) | ~25 | 62% | Fichiers stratégiques |
| 🟡 **T** (Tolerate) | ~8 | 20% | Legacy fonctionnel |
| 🔵 **M** (Migrate) | ~2 | 5% | En migration v2 |
| 🔴 **E** (Eliminate) | ~1 | 2% | À supprimer |
| 🆕 **NEW** | ~7 | 18% | À créer (Prompt 2) |

### **Par Priorité**

| Priorité | Count | Action |
|----------|-------|--------|
| **P0** (Critical) | 6 | Immédiat |
| **P1** (High) | 12 | Court terme |
| **P2** (Medium) | 15 | Moyen terme |
| **P3** (Low) | 5 | Long terme |
| **P4** (Cleanup) | 2 | Opportuniste |

### **Par État Docstring**

| État | Count | Action |
|------|-------|--------|
| **v1** (À standardiser) | ~30 | Prompt 3 |
| **v1 minimal** | ~5 | Prompt 3 Priority 2-3 |
| **v2 standard** | 0 | Aucun (encore) |
| **None** | ~2 | Prompt 3 Priority 4 |

---

## 🎯 ROADMAP PAR TAG

### **Phase 1 : Prompt 2 Phase 1** (Semaine 1)
```
FOCUS: Créer fichiers 🆕 (I - Invest)
├─ core/timeline_injector.py
├─ core/data_aggregator.py
├─ core/prompt_generator.py
└─ analyzers/daily_aggregator.py

IMPACT: Fichiers 🔵 (M - Migrate)
├─ insert_analysis.py → Passe à I après refactor
└─ backfill_history.py → Passe à I après refactor
```

### **Phase 2 : Prompt 3 Priority 1** (Semaine 1-2)
```
FOCUS: Standardiser fichiers 🟢 (I - Invest) P0-P1
├─ workflow_coach.py
├─ prepare_analysis.py
├─ insert_analysis.py (post-refactor)
├─ backfill_history.py (post-refactor)
├─ manage_state.py
└─ config.py

RÉSULTAT: 6 fichiers → v2 docstring ✅
```

### **Phase 3 : Prompt 2 Phase 2** (Semaine 2)
```
FOCUS: Créer fichiers 🆕 (I - Invest) weekly analysis
├─ analyzers/weekly_aggregator.py
├─ analyzers/weekly_analyzer.py
└─ workflows/workflow_weekly.py

IMPACT: Fichiers 🟡 (T - Tolerate) → Deprecated
├─ weekly_planner.py → Tag E (à terme)
└─ prepare_weekly_report.py → Tag E (à terme)
```

### **Phase 4 : Prompt 3 Priority 2-3** (Semaine 2-3)
```
FOCUS: Standardiser fichiers 🟢 (I - Invest) P2-P3
├─ sync_intervals.py
├─ upload_workouts.py
├─ planned_sessions_checker.py
├─ intervals_format_validator.py
├─ rest_and_cancellations.py
└─ ai_providers/*.py (6 fichiers)

RÉSULTAT: ~15 fichiers → v2 docstring ✅
```

### **Phase 5 : Cleanup** (Semaine 3)
```
FOCUS: Gérer fichiers 🔴 (E - Eliminate) et 🟡 (T - Tolerate)
├─ weekly_analysis.py → SUPPRIMER
├─ weekly_planner.py → DEPRECATED (garder si utilisé)
├─ prepare_weekly_report.py → DEPRECATED
└─ normalize_weekly_reports_casing.py → ARCHIVER

FOCUS: Standardiser tests 🟢 (I) P2
└─ test_*.py (10+ fichiers) → v2 docstring ✅
```

---

## 📝 TEMPLATE DOCSTRING AVEC TAG

### **Pour Fichiers Existants (Standardisation)**

```python
"""
[Description une ligne]

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2 (Standardized Prompt 3)

[Description détaillée en français 2-3 phrases]

Examples:
    Command-line usage::

        poetry run command --option value

    Programmatic usage::

        from cyclisme_training_logs.module import Class

        obj = Class(param="value")
        result = obj.method()

Author: Claude Code
Created: YYYY-MM-DD
Updated: 2025-12-26 (Standardization Prompt 3)
"""
```

### **Pour Nouveaux Fichiers (Création)**

```python
"""
[Description une ligne]

GARTNER_TIME: I
STATUS: Development
LAST_REVIEW: 2025-12-26
PRIORITY: P0
MIGRATION_SOURCE: cyclisme-training-automation-v2/src/core/module.py
DOCSTRING: v2 (Created Prompt 2)

[Description détaillée en français 2-3 phrases]

Examples:
    Basic usage::

        from cyclisme_training_logs.core.module import Class

        obj = Class()
        result = obj.method()

Author: Claude Code
Created: 2025-12-26 (Migrated from v2)
"""
```

### **Pour Fichiers En Migration**

```python
"""
[Description une ligne]

GARTNER_TIME: M
STATUS: Migration (v1 → v2)
LAST_REVIEW: 2025-12-26
PRIORITY: P1
MIGRATION_TARGET: core/timeline_injector.py
DEPRECATION_PLAN: Replace with TimelineInjector after Prompt 2 Phase 1
DOCSTRING: v2 (Updated during migration)

[Description détaillée]

Examples:
    [Code examples]

Author: Claude Code
Created: YYYY-MM-DD
Updated: 2025-12-26 (Migration Prompt 2)
"""
```

---

## 🔍 MAINTENANCE TAGS

### **Review Cadence**

| Tag | Review Frequency | Action |
|-----|------------------|--------|
| 🟢 **I** | Monthly | Update LAST_REVIEW |
| 🟡 **T** | Quarterly | Assess if still needed |
| 🔵 **M** | Weekly | Track migration progress |
| 🔴 **E** | One-time | Execute elimination |

### **Upgrade Path**

```
🔴 E (Eliminate) → DELETED
🟡 T (Tolerate) → 🔵 M (Migrate) → 🟢 I (Invest)
🔵 M (Migrate) → 🟢 I (Invest) [after completion]
🟢 I (Invest) → 🟡 T (Tolerate) [if superseded]
```

---

## ✅ ACTIONS IMMÉDIATES

### **1. Ajouter Tags à Tous les Fichiers**
- [ ] Prompt 3 integrates tags automatically
- [ ] Template docstring includes GARTNER_TIME
- [ ] All new files (Prompt 2) start with tag

### **2. Créer Script Validation**
```python
# scripts/validate_gartner_tags.py
def check_all_files_have_tags():
    """Vérifier que tous les .py ont un tag GARTNER_TIME"""
    pass

def generate_tag_report():
    """Générer rapport classification actuelle"""
    pass
```

### **3. Mettre à Jour Documentation**
- [ ] README.md section "Architecture"
- [ ] CONTRIBUTING.md avec règles tags
- [ ] CHANGELOG.md avec migrations

---

## 📊 DASHBOARD VISUEL (Futur)

```python
# scripts/gartner_dashboard.py

def generate_html_dashboard():
    """
    Générer dashboard HTML avec :
    - Pie chart par tag
    - Timeline migrations
    - Priority matrix
    - Docstring coverage
    """
    pass
```

---

## ✅ CONCLUSION

**Inventaire complet créé** avec classification Gartner TIME ✅

**Prochaines étapes :**
1. Intégrer tags dans Prompt 2 (nouveaux fichiers)
2. Intégrer tags dans Prompt 3 (standardisation)
3. Créer script validation automatique
4. Maintenir tags à jour (LAST_REVIEW)

**Avantage :**
- Visibilité claire état projet
- Roadmap migration tracée
- Priorisation objective
- Maintenance proactive

---

**Version :** 1.0
**Dernière mise à jour :** 2025-12-26
**Prochaine révision :** Post-Prompt 2 Phase 1
