# Roadmap - Magma Cycling

> ⚠️ **Claude Code:** Ce fichier est long.
> **NE PAS LIRE entièrement** - Utiliser Grep + offset/limit
> Voir guidelines: [CLAUDE_CODE_GUIDELINES.md](CLAUDE_CODE_GUIDELINES.md)

**Projet :** Système d'analyse et planification d'entraînement cyclisme
**Période :** Novembre 2025 - Aujourd'hui
**Version actuelle :** v3.x
**Statut :** Production-ready ✅

---

## 🗺️ Vue d'ensemble - Phases du projet

```
✅ Phase 0    Nov 2025        Genesis — structure projet, sync Intervals.icu
✅ Phase 1    Déc 2025        Workflow, AI Providers, Weekly Analysis
✅ Sprints    R1→R9  Jan 2026 API, Metrics, Quality, PID, Monitoring, Baseline
✅ Phase 2.5  Fév 2026        Workout Diversity, Tests S080
🔧 Phase 3    Fév-Mars 2026   Refactoring God Scripts + Enrichissement IA (EN COURS)
📋 Phase 4    Q2-Q3 2026      Déploiement : API REST + BDD + UX Client (PLANIFIÉE)
💡 Phase 5    Q3-Q4 2026      Intelligence avancée + Intégrations (BACKLOG)
```

---

## 📅 Historique des Phases Complétées

### Phase 0 - Genesis (13-19 Novembre 2025)

- ✅ Structure projet v2.0.1
- ✅ Sync séances depuis Intervals.icu
- ✅ Analyse manuelle de séances
- ✅ Génération bilans hebdomadaires
- ✅ Script `prepare_analysis.py` v1.1

---

### Phase 1 - Workflow Development (Décembre 2025)

**1.1 - Workflow Quotidien (8-21 Déc)**
- ✅ Workflow coach (`workflow_coach.py`) — orchestrateur principal, 4 modes
- ✅ Détection séances sautées automatique
- ✅ Upload workouts avec horaires dynamiques
- ✅ Weekly planner amélioré

**1.2 - AI Providers Integration (21-25 Déc)**
- ✅ 5 AI providers : Claude API, Mistral API, OpenAI, Ollama, Clipboard
- ✅ Factory pattern, fallback automatique, UI provider-agnostic

**1.3 - Weekly Analysis System (25-26 Déc)**
- ✅ 6 rapports automatisés
- ✅ Enrichissement TSS/IF depuis Intervals.icu
- ✅ Gartner TIME classification system

---

### Sprints R1→R9 (28 Déc 2025 - 25 Jan 2026)

| Sprint | Période | Focus | Impact |
|--------|---------|-------|--------|
| R1 | 28-31 Déc | API Unification | IntervalsClient unique, -200 LOC |
| R2 | 29-30 Déc | Metrics & Config | CTL/ATL/TSB centralisés |
| R2.1 | 29-30 Déc | Safety & Metrics | VETO protocol, 6 métriques avancées |
| R3 | 30 Déc-1 Jan | Planning Manager | JSON centralisé, calendar utils |
| R4 | 2-4 Jan | Quality | PEP 8/257 100%, MyPy 0 errors, Radon B-7 |
| R4++ | 2 Jan | Intelligence | Backfill historique, PID Controller |
| R5 | 4 Jan | Organization | Cleanup bot, code review package |
| R6 | 5-7 Jan | CI/CD & Monitoring | GitHub Actions, adherence monitoring |
| R7 | 7-10 Jan | PID & Testing | PID discret, validation multi-critères |
| R8 | 11-12 Jan | Workflow Tests | +31 tests, coverage workflow_coach +10% |
| R9.A-F | 4-25 Jan | Monitoring & Baseline | Adherence 77.8%, patterns, risk scoring |

---

### Phase 2.5 - Workout Diversity & Tests (Fév 2026)

**Sprints S1-S3 (9-10 Fév) ✅**
- ✅ Intégration recherche workouts externes
- ✅ SQLite cache local + seed data
- ✅ WorkoutDiversityTracker + rotation 21 jours
- ✅ 24 workouts bibliothèque (vs 4 initiaux)

**Tests S080 (10-16 Fév) ✅**
- ✅ Tests FTP/VO2/Anaérobie/Sprint réalisés
- ✅ FTP validée à 223W (progression depuis 201W en juin 2023)
- ✅ Gains massifs efforts courts (sprint +76W, anaérobie +81W, VO2max +37W)
- ✅ Baseline complète pour calibration PID

**MCP Server (Fév 2026) ✅**
- ✅ Serveur MCP opérationnel (28+ outils)
- ✅ Intégration Withings (sommeil, poids, readiness)
- ✅ Health provider agnostique (ABC + factory + NullProvider)
- ✅ AI providers agnostiques (même pattern)

---

## 🔧 Phase 3 — Refactoring & Intelligence (Fév-Mars 2026) — EN COURS

### 3.1 — Refactoring God Scripts ⭐ EN COURS

**Objectif :** Décomposer les fichiers monolithiques en modules maintenables via pattern mixin + façade.

#### Complétés ✅

| Fichier | Avant | Après | Pattern |
|---------|-------|-------|---------|
| `mcp_server.py` | 4 574L | ~500L façade + handlers modulaires | Split par domaine |
| `workflow_coach.py` | 3 700L | 513L façade + mixins | Mixin decomposition |
| `daily_sync.py` | 2 159L | 448L façade + 7 mixins | Mixin decomposition |
| `end_of_week.py` | 1 102L | 425L façade + 5 mixins (`eow/`) | Mixin decomposition |
| `baseline_preliminary.py` | 1 535L | ~145L façade + 5 mixins (`baseline/`) | Mixin decomposition |
| `prepare_analysis.py` | 1 500L | ~620L façade + 4 mixins (`prompt/`) | Mixin decomposition |
| `rest_and_cancellations.py` | 1 013L | ~180L façade + 4 modules (`rest/`) | Module decomposition |

**Résultats validés :** 1 872 tests passing, 15/15 pre-commit hooks, rétrocompatibilité préservée.

#### Candidats restants

| Fichier | Lignes | Type | Priorité |
|---------|--------|------|----------|
| `_mcp/handlers/intervals.py` | 1 762 | 12 handlers monolithique | HIGH |
| ~~`analysis/baseline_preliminary.py`~~ | ~~1 535~~ | ~~God class (30+ méthodes)~~ | ✅ Done |
| ~~`prepare_analysis.py`~~ | ~~1 500~~ | ~~God class (40+ méthodes)~~ | ✅ Done |
| `config/config_base.py` | 1 158 | 6 dataclasses + 23 fonctions | HIGH |
| ~~`workflows/end_of_week.py`~~ | ~~1 102~~ | ~~Orchestrateur dense~~ | ✅ Done |
| `scripts/pid_daily_evaluation.py` | 1 025 | God class PID | HIGH |
| ~~`rest_and_cancellations.py`~~ | ~~1 013~~ | ~~Module utilitaire~~ | ✅ Done |
| `_mcp/handlers/planning.py` | 904 | 11 handlers | MEDIUM |
| `analyzers/weekly_aggregator.py` | 904 | God class | MEDIUM |
| `intelligence/training_intelligence.py` | 856 | Monolithe cohérent | MEDIUM |

**Modules à ne PAS toucher** (bien focalisés) :
- `intervals_client.py` (522L) — API client pur
- `control_tower.py` (611L) — singleton bien structuré
- `discrete_pid_controller.py` (622L) — algorithme mathématique
- `zwift_seed_data.py` (2 475L) — données, pas du code

---

### 3.2 — Enrichissement Prompts IA Coach ⭐ PLANIFIÉ

**Objectif :** Contextualiser les analyses IA avec le profil athlète et des missions spécifiques par moment du cycle d'entraînement.

**Problème :** Les providers IA reçoivent uniquement des statistiques brutes, produisant des recommandations génériques et déconnectées (outils externes recommandés, phase d'entraînement ignorée, contraintes inconnues).

**Architecture :**

```
config/
  └── athlete_context.yaml        → QUI : profil, contraintes, historique (commun)

prompts/
  ├── base_system.txt             → Socle : rôle coach, consignes, interdictions
  ├── mesocycle_analysis.txt      → Mission macro : tendances, périodisation
  ├── weekly_planning.txt         → Mission tactique : prescription semaine
  ├── daily_feedback.txt          → Mission micro : feedback post-séance
  └── weekly_review.txt           → Mission intermédiaire : bilan hebdo
```

**Assemblage :** `base_system + athlete_context (dynamique) + mission_spécifique + données workflow`

**Principes :**
- 1 contexte athlète partagé, N consommateurs
- Provider-agnostic (aucune référence à un provider ou service spécifique)
- Dégradation gracieuse si contexte absent
- Fichiers .txt éditables sans toucher au code Python

**Spec complète :** `PROMPT_ENRICH_AI_COACH_CONTEXT.md`

**Implémentation :**
1. Phase 1 : `athlete_context.yaml` + `load_athlete_context()` + tests
2. Phase 2 : `prompts/base_system.txt` + 4 missions + `prompt_builder.py` + tests
3. Phase 3 : Migration `monthly-analysis` sur nouveau système
4. Phase 4 : Migration `weekly-planner`, `daily-sync`, `end_of_week`

---

### 3.3 — Items Phase 3 additionnels

| Item | Priorité | Effort | Status |
|------|----------|--------|--------|
| PID Calibration post-S080 (R10) | P1 | 5-7j | 📋 Planifié |
| DRY violation Intervals.icu scales | P2 | 2-3h | 📋 Backlog |
| Workflow Diversity Integration (S4) | P1 | 2-3h | 📋 Planifié |
| Test History Tracking | P2 | 2-4h | 📋 Backlog |
| Indoor/Outdoor Adaptive Analysis | P1 | 3-4h | 📋 Backlog |

---

## 📋 Phase 4 — Déploiement : API REST + BDD + UX Client (Q2-Q3 2026)

### Vision

Transformer le système actuel (CLI + MCP local) en application web hébergée, accessible à d'autres cyclistes sans compétences techniques.

### Architecture cible

```
┌─────────────────────────────────────┐
│  UX Client (navigateur)             │
│  Dashboard + Interface Chat         │
│  (React / Vue / autre)              │
└──────────────┬──────────────────────┘
               │ HTTP/JSON
┌──────────────▼──────────────────────┐
│  API REST (FastAPI)                 │
│  /sessions, /weeks, /metrics,       │
│  /analysis, /chat, /health...       │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Logique métier                     │
│  Mixins, services, providers        │
│  (code refactoré Phase 3)           │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  BDD PostgreSQL                     │
│  + APIs externes (Intervals.icu,    │
│    health providers)                │
└─────────────────────────────────────┘
```

**Hébergement :** VM (VPS ou cloud) — backend complet + frontend statique servis par la même instance.

### 4.1 — Base de données (P0)

**Objectif :** Migrer du stockage fichiers YAML/JSON vers PostgreSQL.

**Modélisation :** Les modèles Pydantic existants servent de base directe pour le schéma de tables.

| Table | Source actuelle | Notes |
|-------|----------------|-------|
| `athletes` | `athlete_context.yaml` | Multi-utilisateur natif |
| `weeks` | `planning/S0XX.json` | Métadonnées semaine |
| `sessions` | Sessions dans JSON | Statuts, TSS, durées |
| `activities` | Intervals.icu sync | Données réalisées |
| `metrics` | `get_metrics()` | CTL, ATL, TSB quotidiens |
| `health_data` | Health provider | Sommeil, poids, readiness |
| `ai_analyses` | Rapports markdown | Historique analyses IA |

**Chantiers :**
- [ ] Schéma PostgreSQL depuis modèles Pydantic
- [ ] Couche ORM (SQLAlchemy ou équivalent)
- [ ] Migration des données existantes
- [ ] Tests d'intégrité données

### 4.2 — API REST (P0)

**Objectif :** Exposer la logique métier via endpoints REST.

**Approche :** Les handlers MCP actuels font déjà validation + appel métier + formatage réponse — même pattern qu'un endpoint FastAPI. Migration quasi-mécanique.

| Groupe endpoints | Source MCP | Exemples routes |
|------------------|-----------|-----------------|
| Planning | handlers/planning.py | `GET /weeks`, `POST /sessions`, `PUT /sessions/{id}` |
| Sync | handlers/sync.py | `POST /sync/daily`, `GET /activities/{id}` |
| Metrics | handlers/metrics.py | `GET /metrics`, `GET /athlete/profile` |
| Analysis | handlers/analysis.py | `POST /analysis/monthly`, `GET /recommendations` |
| Health | handlers/health.py | `GET /health/sleep`, `GET /health/readiness` |
| Auth | — (nouveau) | `POST /auth/login`, `POST /auth/register` |

**Chantiers :**
- [ ] Setup FastAPI + structure projet
- [ ] Authentification / gestion utilisateurs
- [ ] Migration handlers MCP → endpoints REST
- [ ] Documentation OpenAPI auto-générée
- [ ] Tests API (pytest + httpx)

### 4.3 — UX Client (P1)

**Objectif :** Interface web accessible aux cyclistes non-techniques.

**Approche hybride :** Dashboard classique (boutons, graphiques) + interface chat (interaction IA conversationnelle). Stratégie de conversion graduelle des utilisateurs vers l'IA.

**Fonctionnalités clés :**
- Dashboard : CTL/ATL/TSB en temps réel, planning semaine, historique
- Chat : interaction coaching IA (prescription, feedback, bilan)
- Graphiques : progression FTP, distribution zones, compliance
- Planning : visualisation et modification des séances
- Santé : intégration données sommeil/poids/readiness

**Chantiers :**
- [ ] Choix framework frontend (React, Vue, Svelte...)
- [ ] Design système / maquettes
- [ ] Composants dashboard
- [ ] Interface chat + streaming réponses IA
- [ ] Responsive mobile

### 4.4 — Déploiement VM (P1)

**Objectif :** Hébergement production accessible publiquement.

**Chantiers :**
- [ ] Choix hébergeur (OVH, Hetzner, Scaleway...)
- [ ] Setup VM (Ubuntu, Docker, nginx, PostgreSQL)
- [ ] CI/CD : GitHub Actions → déploiement automatique
- [ ] SSL/TLS, domaine, monitoring
- [ ] Backup BDD automatisé
- [ ] Documentation installation / administration

### Prérequis Phase 4

- ✅ Refactoring god scripts complété (façades propres = couche service prête)
- ✅ Enrichissement prompts IA (missions par workflow)
- ✅ Provider patterns agnostiques (IA, santé)
- [ ] Tests coverage ≥ 60% sur modules critiques
- [ ] Stabilisation features Phase 3

### Effort estimé Phase 4

| Sprint | Focus | Durée estimée |
|--------|-------|---------------|
| D1 | BDD : schéma + ORM + migration | 2-3 semaines |
| D2 | API REST : FastAPI + auth + endpoints | 2-3 semaines |
| D3 | UX Client : dashboard + chat | 3-4 semaines |
| D4 | Déploiement : VM + CI/CD + monitoring | 1-2 semaines |

**Total estimé :** 8-12 semaines

---

## 💡 Phase 5 — Intelligence avancée & Intégrations (BACKLOG)

Items long-terme, priorisés après déploiement Phase 4.

### Intelligence

- [ ] Pattern learning avancé (ML models)
- [ ] Predictive analytics (performance future)
- [ ] Injury risk detection
- [ ] Recovery optimization automatisée
- [ ] Auto-planning IA complet (objectifs → planning)

### Intégrations externes

- [ ] Strava direct sync
- [ ] Garmin Connect integration
- [ ] Export multi-plateformes
- [ ] Multi-systèmes transmission (SRAM AXS, Campagnolo EPS)

### Configuration & Flexibilité

- [ ] Multi-saison / multi-athlète natif
- [ ] Configuration externalisée complète
- [ ] Marketplace workouts communautaire

---

## 📊 Métriques Projet (Mars 2026)

| Métrique | Valeur | Status |
|----------|--------|--------|
| **Tests passing** | 1 872+ | ✅ |
| **Pre-commit hooks** | 15 actifs | ✅ |
| **PEP 8/257 violations** | 0 | ✅ |
| **MyPy errors** | 0 | ✅ |
| **MCP tools** | 28+ opérationnels | ✅ |
| **AI providers** | 4 (Claude, Mistral, OpenAI, Ollama) | ✅ |
| **Health providers** | 1 + NullProvider (agnostique) | ✅ |
| **God scripts refactorés** | 7/10 (mcp_server, workflow_coach, daily_sync, end_of_week, baseline_preliminary, prepare_analysis, rest_and_cancellations) | 🔧 |

### Progression athlète

| Métrique | Début (Juin 2023) | Actuel (Mars 2026) | Delta |
|----------|-------------------|--------------------|-------|
| FTP | 201W | 223W | +11% |
| Poids | 88.0 kg | 84.7 kg | -3.8% |
| W/kg | 2.28 | 2.63 | +15% |
| CTL | — | ~43 | Reconstruction |

---

## 🔗 Références

### Documentation Projet

- **README.md** : Vue d'ensemble projet
- **CODING_STANDARDS.md** : Standards production
- **PROMPT_ENRICH_AI_COACH_CONTEXT.md** : Spec enrichissement prompts IA
- **CLAUDE_CODE_GUIDELINES.md** : Guidelines Claude Code

### Repository

- **GitHub :** https://github.com/stephanejouve/magma-cycling
- **Branch principale :** main
- **License :** MIT

---

## 🔧 Dette Technique

### DRY Violation: Intervals.icu Scales

**Priorité :** P2 | **Effort :** 2-3h | **Status :** Backlog

Échelle Feel d'Intervals.icu (1-5) dupliquée dans `prepare_analysis.py` et `daily_sync.py`.
Solution : module centralisé `intervals_scales.py` (même pattern applicable aux autres échelles).

### ~~sync-week-to-intervals force_update incomplete~~

**Priorité :** P1 | **Effort :** <1h | **Status :** ✅ Corrigé (PR #61)

`force_update` ne poussait que `name` + `start_date_local`, la description était silencieusement ignorée. Ajout de `"description": full_description` dans `update_data`.

### Refactoring Massif - God Scripts restants

**Priorité :** P1 | **Status :** En cours (voir section 3.1)

3 fichiers HIGH priority + 3 MEDIUM restants après les 7 premiers complétés.
Pattern validé : mixin decomposition + façade légère.

---

**Dernière mise à jour :** 1er mars 2026
**Prochaine revue :** Post-refactoring Phase 3.1 (god scripts)

🤖 *Maintained with Claude Code & Claude.ai*
