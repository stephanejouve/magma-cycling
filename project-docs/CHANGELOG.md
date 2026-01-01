# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).


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
