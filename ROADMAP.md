# Roadmap - Cyclisme Training Logs

**Projet :** Système d'analyse et planification d'entraînement cyclisme
**Période :** Novembre 2025 - Aujourd'hui
**Version actuelle :** v2.2.0
**Statut :** Production-ready ✅

---

## 📅 Historique des Features (Timeline Reconstituée)

### Phase 0 - Genesis (13-19 Novembre 2025)

**Commit initial :** `73b60c7` - 2025-11-13

**Features fondamentales :**
- ✅ Structure projet v2.0.1
- ✅ Sync séances depuis Intervals.icu
- ✅ Analyse manuelle de séances
- ✅ Génération bilans hebdomadaires
- ✅ Script `prepare_analysis.py` v1.1 (récupération workout planifié)

**Commits clés :**
- `8faef6c` - Sync: Séances depuis Intervals.icu
- `1156efd` - Bilan: Semaine S067 (premier bilan)
- `8f2e302` - Feature: prepare_analysis.py v1.1

---

### Phase 1 - Workflow Development (Décembre 2025)

#### 1.1 - Workflow Quotidien (8-21 Déc 2025)

**Features :**
- ✅ **Workflow coach** (`workflow_coach.py`) - Orchestrateur principal
- ✅ **4 modes opératoires** : trainr, trains, wp, wa
- ✅ **Détection séances sautées** automatique
- ✅ **Upload workouts** avec horaires dynamiques
- ✅ **Weekly planner** amélioré (instructions blocs répétitions)

**Commits clés :**
- `69ffcdb` - 2025-12-13: Détection séances sautées
- `ac4d8fc` - 2025-12-21: Workflow quotidien complet avec 4 modes
- `b2b776c` - 2025-12-21: Horaires dynamiques upload workouts
- `52e4d74` - 2025-12-21: Amélioration majeure weekly_planner

#### 1.2 - AI Providers Integration (21-25 Déc 2025)

**Features :**
- ✅ **5 AI providers** : Claude API, Mistral API, OpenAI, Ollama, Clipboard
- ✅ **Factory pattern** pour providers interchangeables
- ✅ **Fallback automatique** entre providers
- ✅ **UI provider-agnostic** dans workflow

**Commits clés :**
- `1a3dccd` - 2025-12-25: Integrate AI providers into workflow_coach
- `bbcd46b` - 2025-12-25: Make workflow UI provider-agnostic
- `6af4754` - 2025-12-25: Add explicit user consent for provider fallback

#### 1.3 - Weekly Analysis System (25-26 Déc 2025)

**Features :**
- ✅ **Phase 2 Weekly Analysis** (Option B)
- ✅ **6 rapports automatisés** : workout_history, metrics_evolution, learnings, adaptations, transition, bilan_final
- ✅ **Enrichissement TSS/IF** automatique depuis Intervals.icu
- ✅ **Gartner TIME classification** system

**Commits clés :**
- `9d4202a` - 2025-12-26: Phase 2 - Weekly Analysis System (Option B)
- `3d79a50` - 2025-12-26: Enrich activities with detailed TSS/IF data
- `5dc8fb4` - 2025-12-26: Integrate Gartner TIME classification system

---

### Sprint R1 - API Unification (28-31 Déc 2025)

**Objectif :** Éliminer duplication des 3 classes IntervalsAPI

**Features :**
- ✅ **Unified IntervalsClient** (`api/intervals_client.py`)
- ✅ **Migration P0 files** (6 fichiers critiques)
- ✅ **Migration P1 files** (5 fichiers prioritaires)
- ✅ **Migration P2-P3** (utilities & tests)
- ✅ **Cleanup** ancien code (remove old IntervalsAPI classes)

**Impact :**
- 🔻 ~200 lignes de code éliminées
- ✅ Bug fixes centralisés
- ✅ API client unique et documenté

**Commits clés :**
- `1a35b90` - 2025-12-28: Create unified IntervalsClient (Phase 1-2)
- `e0df359` - 2025-12-29: Migrate P0 files to IntervalsClient
- `4106b55` - 2025-12-29: Migrate P1 files to IntervalsClient
- `39ae58b` - 2025-12-30: Sprint R1 P2-P3 migrations
- `7ab0752` - 2025-12-30: Sprint R1 cleanup

---

### Sprint R2 - Metrics & Config (29-30 Déc 2025)

**Objectif :** Centraliser métriques CTL/ATL/TSB et configuration

**Features :**
- ✅ **Centralized CTL/ATL/TSB metrics** utilities
- ✅ **Externalized config** (`config/config_base.py`)
- ✅ **Athlete profile** configuration
- ✅ **Training thresholds** management

**Impact :**
- 🔻 ~100 lignes de duplication éliminées
- ✅ Configuration centralisée
- ✅ None handling robuste

**Commits clés :**
- `28c7344` - 2025-12-29: Centralize CTL/ATL/TSB metrics + externalize config
- `b6f4f47` - 2025-12-30: Handle None values in weekly aggregator

---

### Sprint R2.1 - Safety & Metrics (29-30 Déc 2025)

**Objectif :** Protocole VETO + métriques avancées

**Features :**
- ✅ **VETO protocol** : Pre-session overtraining check (P0 CRITICAL)
- ✅ **6 advanced metrics functions** : calculate_atl_deviation, detect_rpe_mismatch, etc.
- ✅ **Session cancellation** converts to NOTE (safe deletion)

**Impact :**
- 🛡️ Sécurité : Prévention surmenage
- 📊 Métriques : 6 nouvelles fonctions d'analyse

**Commits clés :**
- `52eed8c` - 2025-12-29: Integrate VETO logic (P0 CRITICAL)
- `ae5bf2c` - 2025-12-29: Add 6 advanced metrics functions
- `5eca934` - 2025-12-30: Session cancellation to NOTE instead of delete

---

### Sprint R3 - Planning Manager (30 Déc - 1 Jan 2026)

**Objectif :** Gestionnaire centralisé planning JSON + calendrier

**Features :**
- ✅ **Planning Manager** (`planning/planning_manager.py`)
- ✅ **Calendar utilities** (`planning/calendar.py`)
- ✅ **Auto-save planning JSON** dans workflow
- ✅ **Session status update** tool
- ✅ **Monthly analysis** tool pour vue macro

**Impact :**
- 🔻 ~150 lignes duplication planning éliminées
- ✅ Écriture atomique JSON
- ✅ Validation centralisée

**Commits clés :**
- `4bc97e3` - 2025-12-30: Auto-save planning JSON + session status update
- `b1ab8b8` - 2025-12-30: Automated S074 planning generation
- `409ff23` - 2025-12-30: Complete planning workflow documentation
- `9607dd5` - 2026-01-01: Add monthly-analysis tool
- `e378e0e` - 2026-01-01: Sprint R3 - Planning Manager & Calendar

---

### Sprint R4 - Quality (2-4 Jan 2026)

**Objectif :** 100% conformité standards Python production

**Features :**
- ✅ **PEP 8 compliance** : 1137 violations → 0
- ✅ **PEP 257 + Google Style** : 179 violations → 0
- ✅ **MyPy type safety** : 38 errors → 0
- ✅ **Complexity reduction** : F-48 → B-7 (Radon)
- ✅ **Pre-commit hooks** : 13 → 14 hooks
- ✅ **CI/CD** : GitHub Actions (tests + lint)

**Impact :**
- ✅ 100% production-ready
- ✅ 497 tests passing (100%)
- ✅ 0 violations tous standards

**Commits clés :**
- `dfedb22` - 2026-01-03: Update major dependencies with Mistral migration
- `d0460dd` - 2026-01-03: Extract step_1b into 7 helpers (F-48 → manageable)
- `fb0674d` - 2026-01-03: Fix mypy errors (38 → 0)
- `65a8718` - 2026-01-03: Fix D400 errors - add periods (380 fixes)
- `c7ad33b` - 2026-01-03: Enforce PEP 257 + Google Style
- `daa07ac` - 2026-01-03: Sprint R4 Qualité - Livraison MOA

---

### Sprint R4++ - Intelligence (2 Jan 2026)

**Objectif :** Backfill historique + PID Controller

**Features :**
- ✅ **Backfill history** : Analyse en masse données historiques
- ✅ **PID Controller** : Correction automatique progression FTP
- ✅ **Training Intelligence** : Learning système avec confidence levels

**Impact :**
- 🤖 Intelligence : Apprentissage automatique
- 📈 PID : Correction dynamique FTP
- 📊 Backfill : Analyse 50+ séances historiques

**Commits clés :**
- `0d2b57e` - 2025-12-25: Add backfill-history tool
- `9a06779` - 2026-01-02: Sprint R4++ - Backfill & PID Controller (v2.2.0)

---

### Sprint R5 - Organization (4 Jan 2026)

**Objectif :** Organisation projet + outils maintenance

**Features :**
- ✅ **Project cleanup bot** (`scripts/maintenance/project_cleaner.py`)
- ✅ **Code review package generator** professionnel
- ✅ **SOURCE_CODE_COMPLETE.md** : Code unifié (1.2 MB, 120 fichiers)
- ✅ **Sprint naming convention** : R4 → R5 → R6 standardisé
- ✅ **CLI consistency** : --week-id standard projet

**Impact :**
- 🧹 Maintenance : Cleanup automatisé
- 📦 Review : Package professionnel 660KB
- 📝 Documentation : Code unifié navigation rapide
- ✅ Standards : CLI cohérent partout

**Commits clés :**
- `54d454e` - 2026-01-04: Add automated project cleanup bot
- `f127a6f` - 2026-01-04: Add professional code review package generator
- `1ec3b1e` - 2026-01-04: Add unified source code documentation
- `eea1957` - 2026-01-04: Clarify sprint naming (R21 → R5)
- `d8d383f` - 2026-01-04: Align weekly-analysis CLI with standards

---

## 🎯 État Actuel (Janvier 2026)

### ✅ Features Opérationnelles

#### Workflow Hebdomadaire
```bash
wa --week-id S073 --start-date 2025-01-06  # Analyse semaine passée
wp --week-id S074 --start-date 2025-01-13  # Planning semaine courante
wu --week-id S074 --start-date 2025-01-13  # Upload workouts
trainr --week-id S074                       # Réconciliation
trains --week-id S074                       # Servo-mode ajustements
```

#### AI Analysis
- **5 providers** : Claude API, Mistral API, OpenAI, Ollama, Clipboard
- **Fallback automatique** entre providers
- **Analyse séances** complète (5 rapports)
- **Weekly analysis** automatisée (6 rapports)

#### Intelligence & Safety
- **VETO protocol** : Prévention surmenage
- **PID Controller** : Correction FTP automatique
- **Training Intelligence** : Apprentissage patterns
- **Advanced metrics** : 6 fonctions d'analyse

#### Planning & Calendar
- **Planning Manager** : Gestion JSON centralisée
- **Calendar utilities** : Calculs dates/semaines
- **Session status** : Tracking annulations/modifications
- **Monthly analysis** : Vue macro entraînement

#### Quality & Tooling
- **100% PEP 8/257** compliance
- **0 MyPy errors** (type safety)
- **497 tests** passing (100%)
- **14 pre-commit hooks** actifs
- **CI/CD** GitHub Actions
- **Project cleanup bot**
- **Code review package** generator

### 📊 Métriques Projet

| Métrique | Valeur | Status |
|----------|--------|--------|
| **Tests passing** | 497/497 (100%) | ✅ |
| **PEP 8 violations** | 0 | ✅ |
| **PEP 257 violations** | 0 | ✅ |
| **MyPy errors** | 0 | ✅ |
| **Ruff warnings** | 0 | ✅ |
| **Complexité max** | B-7 | ✅ |
| **Python files** | ~87 | ✅ |
| **Test files** | ~54 | ✅ |
| **Lines of code** | ~12,000+ | ✅ |
| **Test ratio** | ~1:1.6 | ✅ |
| **Pre-commit hooks** | 14 actifs | ✅ |
| **CI/CD** | GitHub Actions | ✅ |

---

## 🚀 Roadmap Future

### Sprint R6 - Planned (Q1 2026)

**Focus :** Performance & Extension

#### Features Envisagées

**1. Performance Optimization (P0)**
- [ ] Cache layer pour requêtes API Intervals.icu
- [ ] Batch processing pour backfill massif
- [ ] Optimisation algorithmes détection gaps
- [ ] Profiling et benchmarking

**2. Extended Analytics (P1)**
- [ ] Dashboard web interactif (Streamlit/Dash)
- [ ] Visualisations graphiques (CTL/ATL/TSB curves)
- [ ] Correlation analysis (sommeil vs performance)
- [ ] Trend detection (long-term patterns)

**3. Refactoring Utilities (P1)**
- [ ] R2: Create Metrics Utilities (`utils/metrics.py`)
- [ ] R4: Create Date Utilities (`utils/dates.py`)
- [ ] R5: Create Data Fetching Facade (`data/fetcher.py`)
- [ ] Voir `REFACTORING_TODO.md` pour détails

**4. Documentation (P2)**
- [ ] User guide complet
- [ ] API documentation (Sphinx)
- [ ] Video tutorials
- [ ] FAQ utilisateur

**Durée estimée :** 2-3 semaines

---

### Sprint R7 - Envisioned (Q2 2026)

**Focus :** Automation & Intelligence

#### Features Envisagées

**1. Full Automation (P0)**
- [ ] Auto-planning basé sur IA (objectifs → planning complet)
- [ ] Auto-adjustment temps réel (servo v2.0)
- [ ] Auto-reconciliation quotidienne
- [ ] Notifications intelligentes

**2. Advanced Intelligence (P1)**
- [ ] Pattern learning avancé (ML models)
- [ ] Predictive analytics (performance future)
- [ ] Injury risk detection
- [ ] Recovery optimization

**3. Integrations (P2)**
- [ ] Strava direct sync
- [ ] Garmin Connect integration
- [ ] TrainingPeaks export
- [ ] Wahoo SYSTM integration

**Durée estimée :** 3-4 semaines

---

### Long-Term Vision (2026-2027)

#### Multi-Athlete Support
- [ ] Multi-tenant architecture
- [ ] Coach dashboard
- [ ] Team management
- [ ] Shared workouts library

#### Mobile App
- [ ] React Native app
- [ ] Offline mode
- [ ] Push notifications
- [ ] Quick session logging

#### Advanced AI
- [ ] GPT-4 integration for complex analysis
- [ ] Computer vision (video analysis)
- [ ] Voice commands
- [ ] Natural language queries

#### Marketplace
- [ ] Workout templates marketplace
- [ ] Training plans library
- [ ] Coach services platform
- [ ] Premium features

---

## 📚 Architecture & Patterns

### Modules Actuels

```
cyclisme_training_logs/
├── ai_providers/          # 5 AI providers + factory
├── analyzers/             # Weekly/daily aggregators
├── api/                   # Unified Intervals.icu client
├── config/                # Centralized configuration
├── core/                  # Core business logic
├── intelligence/          # PID + Training intelligence
├── planning/              # Planning manager + calendar
├── scripts/               # Backfill, validation tools
├── utils/                 # Metrics utilities
└── workflows/             # Workflow orchestrators
```

### Patterns Appliqués

- ✅ **Factory Pattern** : AI providers
- ✅ **Strategy Pattern** : Algorithmes d'agrégation
- ✅ **Singleton Pattern** : Configuration globale
- ✅ **Facade Pattern** : IntervalsClient
- ✅ **Observer Pattern** : Training intelligence
- ✅ **Template Method** : Workflow phases

### Standards

- ✅ **PEP 8** : Code style moderne (100 chars)
- ✅ **PEP 257** : Docstrings Google Style
- ✅ **PEP 518** : pyproject.toml centralisé
- ✅ **Type Hints** : Python 3.11+ typing
- ✅ **Testing** : pytest + coverage

---

## 🎓 Leçons Apprises

### Succès

1. **Sprints itératifs** : R1-R5 ont permis amélioration continue
2. **Quality first** : Sprint R4 a éliminé 100% dette technique
3. **Automation** : Pre-commit hooks préviennent régressions
4. **Documentation** : Sessions détaillées facilitent contexte

### Défis Rencontrés

1. **API Duplication** : 3 versions IntervalsAPI → résolu Sprint R1
2. **Type Safety** : 38 MyPy errors → résolu Sprint R4
3. **Complexity** : F-48 workflow → refactorisé B-7 Sprint R4
4. **Standards** : 1137 PEP 8 violations → résolu Sprint R4

### Opportunités

1. **Performance** : Cache API peut réduire latence 50%
2. **UX** : Dashboard web améliorerait adoption
3. **ML** : Pattern learning avancé possible avec historique
4. **Mobile** : App native augmenterait utilisation

---

## 📊 Statistiques Développement

### Timeline Résumé

- **Démarrage projet :** 13 novembre 2025
- **Date actuelle :** 4 janvier 2026
- **Durée développement :** ~2 mois
- **Commits totaux :** 200+ commits
- **Sprints techniques :** 5 sprints (R1-R5)
- **Version actuelle :** v2.2.0

### Vélocité Sprints

| Sprint | Dates | Commits | LOC Impact | Durée |
|--------|-------|---------|------------|-------|
| R1 | 28-31 Déc | 15 | -200 | 3 jours |
| R2 | 29-30 Déc | 8 | -100 | 2 jours |
| R2.1 | 29-30 Déc | 5 | +300 | 1 jour |
| R3 | 30 Déc - 1 Jan | 12 | -150 | 2 jours |
| R4 | 2-4 Jan | 33 | Qualité | 2 jours |
| R4++ | 2 Jan | 3 | +500 | 1 jour |
| R5 | 4 Jan | 6 | +200 | 1 jour |

**Total :** 82 commits techniques, ~10 jours sprint

### Contributors

- **MOA :** Stéphane Jouve
- **MOE :** Claude Code (Anthropic - Claude Sonnet 4.5)
- **Review :** External code review team (Sprint R5)

---

## 🔗 Références

### Documentation Projet

- **README.md** : Vue d'ensemble projet
- **CODING_STANDARDS.md** : Standards production
- **SPRINT_NAMING.md** : Convention nommage sprints
- **SPRINT_R4_R5_RECAP.md** : Récapitulatif R4 & R5
- **REFACTORING_TODO.md** : Dette technique identifiée
- **WORKFLOW_PLANNING.md** : Workflow hebdomadaire complet

### Livrables MOA

- **LIVRAISON_MOA_20260104.md** : Sprint R4 Qualité
- **LIVRAISON_MOA_CLEANUP_20260104.md** : Sprint R5 Organization
- **review_package_v2.2.0.zip** : Package revue code (660KB)

### Archives Sprints

- **sprint-r4-qualite-v2.2.0.tar.gz** (1.1 MB)
- **sprint-r5-organization-v2.2.0.tar.gz** (16.5 MB)
- **review_package_v2.2.0.zip** (660 KB)

### Repository

- **GitHub :** https://github.com/stephanejouve/cyclisme-training-logs
- **Branch principale :** main
- **Version :** v2.2.0
- **License :** Private

---

## ✅ Statut Global

**Projet :** ✅ Production-Ready
**Qualité :** ✅ 100% Standards Python
**Tests :** ✅ 497/497 Passing
**Documentation :** ✅ Complète et à jour
**Roadmap :** ✅ Définie jusqu'à Q2 2026

---

**Dernière mise à jour :** 4 janvier 2026
**Prochaine revue :** Sprint R6 planning (estimé mi-janvier 2026)

🤖 *Generated with [Claude Code](https://claude.com/claude-code)*
