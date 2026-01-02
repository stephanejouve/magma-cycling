# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).


## [2.1.1] - 2026-01-02

### Fixed

**Intervals.icu API Client** (`cyclisme_training_logs/api/intervals_client.py`):
- Ajout méthode `delete_event(event_id)` : Suppression événements calendrier
- Ajout méthode `update_event(event_id, event_data)` : Mise à jour événements calendrier
- Support complet CRUD pour événements (Create, Read, Update, Delete)

**Session Status Tool** (`cyclisme_training_logs/update_session_status.py` v2.1.0):
- Correction comportement sync Intervals.icu pour respecter spec originale
- `cancelled`/`skipped` : Convertit event en NOTE avec tag [ANNULÉE]/[SAUTÉE] au lieu de supprimer
- Création automatique NOTE si événement n'existe pas (traçabilité complète)
- Ajout support `TRAINING_DATA_REPO` via `get_data_config()` (résolution chemins correct)
- Ajout chargement automatique `.env` via `load_dotenv()`
- Format date corrigé pour API Intervals.icu (`YYYY-MM-DDTHH:MM:SS`)

**Documentation**:
- Ajout section "Behavior" dans docstring `update_session_status.py`
- Exemples usage enrichis (cancel, skip, complete avec/sans sync)

**Impact**:
- Calendrier Intervals.icu cohérent avec séances annulées marquées [ANNULÉE]
- Historique complet préservé (pas de suppression)
- Compatible avec workflow existant LIVRAISON_MOA_20251230

## [2.1.0] - 2026-01-01

### Added - Sprint R4 (Training Intelligence & Feedback Loop)

**Training Intelligence** (`cyclisme_training_logs/intelligence/training_intelligence.py`):
- `TrainingIntelligence` : Gestionnaire mémoire partagée multi-temporelle
  - `add_learning()` : Ajouter enseignements avec progression confidence (LOW→VALIDATED)
  - `identify_pattern()` : Détecter patterns récurrents avec trigger conditions
  - `propose_adaptation()` : Proposer évolution protocoles basée sur evidence
  - `get_daily_insights()` : Insights quotidiens (warnings + recommendations)
  - `get_weekly_synthesis()` : Synthèse hebdo (patterns émergents + learnings validés)
  - `get_monthly_trends()` : Tendances mensuelles (protocoles validés + top patterns)
  - `save_to_file()` / `load_from_file()` : Persistance JSON état complet
- `TrainingLearning` : Dataclass enseignement avec confidence progressive
  - Attributes: id, timestamp, level, category, description, evidence, confidence, impact, applied, validated
  - `promote_confidence()` : Progression automatique confidence
- `Pattern` : Dataclass pattern récurrent avec conditions déclencheurs
  - Attributes: id, name, trigger_conditions, observed_outcome, frequency, first_seen, last_seen, confidence
  - `matches()` : Vérification conditions (opérateurs <, >, =)
  - `promote_confidence()` : Progression basée sur frequency
- `ProtocolAdaptation` : Dataclass adaptation protocole
  - Attributes: id, protocol_name, adaptation_type, current_rule, proposed_rule, justification, evidence, confidence, status
  - Lifecycle: PROPOSED → TESTED → VALIDATED/REJECTED
- **Enums** :
  - `AnalysisLevel` (DAILY/WEEKLY/MONTHLY) : Niveau temporel analyse
  - `ConfidenceLevel` (LOW/MEDIUM/HIGH/VALIDATED) : Progression validation
- **Feedback Loop** : Enrichissement mutuel analyses quotidienne/hebdo/mensuelle
- **19 tests unitaires** (100% coverage, 0 failures)

**Architecture**:
- 100% in-memory (Dict storage, 0 hardcoded paths)
- JSON persistence optionnelle (`~/cyclisme-training-logs-data/intelligence/`)
- Backward compatible (enrichit workflow existant sans breaking changes)
- Progressive validation : 1-2 obs → LOW, 3-5 → MEDIUM, 6-10 → HIGH, 10+ → VALIDATED

**Documentation**:
- **GUIDE_INTELLIGENCE.md** (700+ lignes) : Guide complet avec cas d'usage et exemples
- **Sphinx API** : Documentation auto-générée (docs/modules/intelligence.rst)
- Exemples complets : Sweet-Spot Optimal, Prévention VO2 Échec

**Impact**:
- Résolution silos temporels : Analyses quotidienne/hebdo/mensuelle partagent mémoire
- Détection patterns automatique : Prévention échecs (ex: sleep debt → VO2 failure)
- Validation progressive protocoles : Evidence-based (10+ observations → VALIDATED)
- Insights contextuels : Recommendations basées sur historique complet
- Évolution protocoles : Adaptations proposées automatiquement selon patterns

**Métriques Sprint R4**:
- Code: 689 lignes (training_intelligence.py)
- Tests: 19 tests (100% passing)
- Documentation: 700+ lignes (GUIDE_INTELLIGENCE.md)
- Coverage: 507/509 global tests passing (99.6%)


## [2.0.0] - 2026-01-01

### Added - Sprint R3 (Planning Manager & Calendar)

**Planning Manager** (`cyclisme_training_logs/planning/planning_manager.py`):
- `PlanningManager` : Gestionnaire de plans d'entraînement
  - `create_training_plan()` : Création plans 4-12 semaines
  - `add_deadline()` : Ajout objectifs/échéances
  - `get_plan_timeline()` : Vue timeline avec milestones
  - `validate_plan_feasibility()` : Validation TSS/CTL vs profil athlète
- `TrainingPlan` : Dataclass plan avec objectifs, TSS targets, durée
- `TrainingObjective` : Dataclass objectif avec priorité, type, progression
- Enums : `PriorityLevel` (LOW/MEDIUM/HIGH/CRITICAL), `ObjectiveType` (EVENT/FTP_TARGET/CTL_TARGET/WEIGHT_TARGET/MILESTONE)
- **Contraintes master athletes** : Max 380 TSS/semaine, 7 points CTL/semaine
- **21 tests unitaires** (210% over-delivery vs 8-10 attendus)

**Training Calendar** (`cyclisme_training_logs/planning/calendar.py`):
- `TrainingCalendar` : Calendrier hebdomadaire avec gestion séances
  - `generate_weekly_calendar()` : Génération ISO weeks (semaines 1-53)
  - `mark_rest_days()` : Configuration jours repos (dimanche obligatoire master)
  - `add_session()` : Ajout séances avec validation jours repos
  - `get_week_summary()` : Résumé hebdomadaire TSS par type, intensité moyenne
- `TrainingSession` : Dataclass séance (TSS planifié/réel, durée, intensité)
- `WeeklySummary` : Dataclass résumé hebdo (TSS total, sessions, repos, breakdown)
- `WorkoutType` enum : ENDURANCE/TEMPO/THRESHOLD/VO2MAX/RECOVERY/REST
- **20 tests unitaires** (250% over-delivery vs 6-8 attendus)

**Architecture**:
- 100% in-memory (Dict storage, 0 fichiers hardcodés)
- Intégration `AthleteProfile` via `config.py`
- ISO week handling (Jan 4 rule)
- **488 tests passing** (+41 nouveaux tests Sprint R3)

### Added - Sprint R2.1 (Integrations & VETO Logic)

**VETO Logic** (`cyclisme_training_logs/utils/metrics_advanced.py`):
- Intégration détection sommeil insuffisant dans `assess_overtraining_risk()`
- **VETO immédiat** si sommeil < 5.5h (master) ou < 6.0h (senior)
- Recommandations prioritaires : repos obligatoire, sommeil, intensité réduite
- Message explicite : "🚨 VETO: Sommeil insuffisant détecté"

**Integration Tests** (`tests/integration/`):
- Tests providers (Intervals.icu, Withings)
- Validation cohérence metrics entre modules

**Tests**:
- 467 tests passing (94% couverture)

### Added - Sprint R2 (Metrics Advanced)

**Nouvelles Métriques** (`cyclisme_training_logs/utils/metrics_advanced.py`):
- `calculate_ctl()` : Chronic Training Load (fitness 42 jours)
- `calculate_tsb()` : Training Stress Balance (forme vs fatigue)
- `calculate_ramp_rate()` : Rampe CTL avec validation limites
- `assess_overtraining_risk()` : Évaluation risque surentraînement
  - Niveaux : LOW/MEDIUM/HIGH
  - Critères : TSB, CTL ramp rate, profil athlète
  - Recommandations personnalisées

**Athlete Profile** (`cyclisme_training_logs/config/athlete_profile.py`):
- Configuration centralisée via `.env`
- Support master/senior athletes
- Paramètres : FTP, poids, âge, capacité récupération, dépendance sommeil

**Tests**:
- 446 tests passing (91% couverture)
- Tests exhaustifs cas limites (CTL négatif, TSS nul, master vs senior)

## [1.1.1] - 2025-11-25

### Documentation
- **GUIDE_UPLOAD_WORKOUTS.md** : Correction annotations format workouts
  - Nom workout extrait du délimiteur `=== WORKOUT ... ===` (et non première ligne)
  - Ajout section "Format Nom Important" avec exemples
  - Clarification avantages : traçabilité, cohérence, parsing automatique
- Référence : fix `upload_workouts.py` lignes 124+175 (v1.1.0)

## [1.1.0] - 2025-11-25

### Added
- `docs/GUIDE_COMMIT_GITHUB.md` : Guide complet commit et push GitHub
- `docs/README.md` : Index central de la documentation
- `scripts/setup_documentation.sh` : Setup automatique documentation
- `scripts/analyze_documentation.sh` : Analyse cohérence documentation

### Changed
- Migration complète vers `logs/weekly_reports/` (terminée)
- Documentation centralisée dans `docs/`
- Correction références obsolètes `bilans_hebdo/` dans tous scripts
- Standardisation noms fichiers documentation

### Fixed
- Cohérence chemins dans `organize_weekly_report.py`
- Cohérence chemins dans `prepare_weekly_report.py`
- Référence `project_prompt_v2.md` → `project_prompt_v2_1_revised.md`

## v2.3 - 2025-11-18

### Ajouté
- **Workflow automation v1.1** : Analyse planifié vs réalisé
- `prepare_analysis.py` v1.1 : Récupération workout planifié via API
- Section complète "Analyse Planifié vs Réalisé"
- Détection écarts >10% TSS, >5% IF
- Cas d'usage patterns documentés

### Performance
- Temps documentation : 5min → 2.5min (-50%)

## v2.2 - 2025-11-17

### Ajouté
- **Workflow automation v1.0** : Scripts Python
- 4 scripts automation (collect, prepare, insert, sync)
- Feedback subjectif intégré

### Performance
- Temps documentation : 20min → 5min (-75%)

## v2.1 - 2025-11-12

### Initial
- Structure Project Prompt coaching
- Documentation 4 logs + 6 rapports hebdo
- Protocoles critiques établis
