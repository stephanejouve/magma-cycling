# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).


## [3.0.0] - 2026-01-25

### Added - Sprint R9 Complete: Monitoring & Baseline Analysis

**Sprint R9.A-F** (04-25 Jan 2026) - **206 commits depuis v2.0.0**:

**R9.A - Daily Workout Sync** (`daily-sync` command):
- Sync quotidien automatique Intervals.icu (activities, wellness, events)
- Email reporting avec analyse AI (via `--send-email --ai-analysis`)
- Auto-servo mode pour ajustements FTP adaptatifs (`--auto-servo`)
- LaunchAgent macOS: exécution automatique 21:30 daily

**R9.B - Session Update & Sync** (`update-session` command):
- Cancel/skip session avec sync bidirectionnel Intervals.icu
- Format NOTE Intervals: `[ANNULÉE]` ou `[SAUTÉE]` avec raison
- Status tracking: completed/cancelled/skipped/missed
- Sync flag `--sync` pour propagation immédiate

**R9.C - Adherence Monitoring** (`check-workout-adherence` command):
- Surveillance automatique adherence workouts vs planned
- Export JSON format JSONL: `~/data/monitoring/workout_adherence.jsonl`
- Métriques: adherence_rate, completed_count, skipped_count, reasons
- LaunchAgent macOS: exécution 22:00 daily

**R9.D - End-of-Week Planning** (`end-of-week` command):
- Génération automatique planning semaine suivante
- Analysis semaine écoulée (TSS, IF, zones, recovery)
- AI-powered weekly plan avec contraintes athlète
- LaunchAgent macOS: exécution dimanche 20:00

**R9.E - Baseline Preliminary Analysis** (`baseline-analysis` command):
- Analyse 21 jours baseline adherence (5-25 Jan 2026)
- **Adherence baseline: 77.8%** (14/18 workouts completed)
- **4 insights actionnables**:
  - Skips concentrés lundi-mardi (50%)
  - Planning inadapté début semaine
  - Week-end 100% adherence (force du projet)
  - TSS target réaliste (350 TSS/semaine)

**R9.F - Advanced Pattern Analysis** (`pattern-analysis` command):
- Détection patterns jour semaine (day-of-week adherence)
- Clustering skip reasons (fatigue, weather, schedule)
- **Risk scoring 0-100**: probabilité skip par contexte
- Statistical analysis: chi-square tests, correlation matrices

**Monitoring Infrastructure**:
- **7 LaunchAgents macOS** (architecture productive):
  - `com.cyclisme.rept.10-daily-sync-21h30` (reporting)
  - `com.cyclisme.mon.10-adherence-22h` (monitoring)
  - `com.cyclisme.anls.10-pid-evaluation-23h` (intelligence AI)
  - `com.cyclisme.flow.10-end-of-week-sun-20h` (workflow)
  - `com.cyclisme.mnt.10-project-clean-daily` (maintenance)
  - `com.cyclisme.flow.20-check-training-logs-hourly` (checks)
  - `com.cyclisme.mon.20-sync-backup-daily-23h30` (backup)
- Migration scripts 3-phases: install → validate (48h) → archive (7j)
- Auto-migration via LaunchAgents (phase triggers automatiques)

**Dataset v2.0.0** (`~/data/monitoring/`):
- `workout_adherence.jsonl`: baseline 21 jours (18 entrées)
- `pattern_analysis.json`: day-of-week statistics
- `baseline_report.json`: metrics + insights + recommendations

### Added - Tests Suite v3.0.0

**38 nouveaux tests** monitoring & analysis (84% coverage modules nouveaux):

**Adherence Monitoring** (`tests/monitoring/test_adherence.py` - 15 tests):
- `test_check_workout_adherence_full_week`: Adherence semaine complète
- `test_check_workout_adherence_partial_completion`: Completion partielle
- `test_check_workout_adherence_all_skipped`: Tous workouts skipped
- `test_check_workout_adherence_mixed_status`: Statuts mixtes
- `test_check_workout_adherence_no_events`: Aucun event Intervals.icu
- Edge cases: empty week, API failures, malformed data

**Pattern Analysis** (`tests/monitoring/test_patterns.py` - 12 tests):
- `test_pattern_analysis_day_of_week`: Analyse jour semaine
- `test_pattern_analysis_skip_reasons_clustering`: Clustering raisons
- `test_pattern_analysis_risk_scoring`: Risk scoring 0-100
- `test_pattern_analysis_correlation_matrix`: Corrélations TSS/IF/adherence
- `test_pattern_analysis_empty_data`: Dataset vide
- Statistical validation: chi-square, distributions

**Baseline Analysis** (`tests/monitoring/test_baseline.py` - 11 tests):
- `test_baseline_analysis_21_days`: Baseline 21 jours validation
- `test_baseline_analysis_adherence_calculation`: Calcul adherence 77.8%
- `test_baseline_analysis_insights_generation`: Génération insights
- `test_baseline_analysis_recommendations`: Recommendations actionnables
- Edge cases: insufficient data, outliers, partial weeks

**Test Suite Overall**:
- **636+ tests total** (634+ passed, 99.7% success rate)
- **Coverage: 30%** overall (+1% from v2.3.1)
  - Monitoring modules: 84% (adherence, patterns, baseline)
  - Core modules: 90-100% (utils, intelligence, planning)
  - API modules: 53-72% (upload_workouts, intervals_client)
- Pre-commit hooks: ✅ 0 violations

### Changed - Documentation & Standards

**COMMIT_CONVENTIONS.md** (new file):
- Convention traçabilité git: `[ROADMAP@<commit-sha>]`
- Format: `<type>(<scope>): <description> [ROADMAP@<sha>]`
- Référence ROADMAP version active au moment du commit
- Résout dualité git history vs ROADMAP actuel (Sprint R9 reorganization)
- Helper command: `git log -1 --format=%h project-docs/ROADMAP.md`

**README.md** v3.0.0:
- Section "Automation & Monitoring" (Sprint R9 features)
- Section "Development Standards & Conventions":
  - CODING_STANDARDS.md (docstrings PEP 257 + Google Style)
  - COMMIT_CONVENTIONS.md (ROADMAP traceability)
  - Configuration management (config.py mandatory for .env)
- Brevo email configuration (daily-sync reports)
- LaunchAgents clarification: macOS-only, optional (CLI commands work everywhere)
- Version updated: v2.3.1 → v3.0.0
- Test stats: 598 → 636+ tests
- Release notes: v3.0.0 with 206 commits

**ROADMAP.md** reorganization:
- Sprint R9: "Monitoring & Baseline Analysis" (04-25 Jan) - 6 sub-sprints (R9.A-F)
- Pause Stratégique S078-S079 (27 Jan - 09 Fév)
- Sprint S080 Tests FTP (10-16 Fév)
- Phase 3: Post-S080 Sprints (R10-R13)
- Roadmap Summary avec timeline consolidée
- Note historique: dualité git history (Grappe 15 Jan) vs ROADMAP actuel (Monitoring)

**LaunchAgents Documentation**:
- `scripts/launchagents/README.md`: Migration guide 3-phases
- Convention naming: `com.cyclisme.{CATEGORY}.{SEQ}-{NAME}-{SCHEDULE}`
- Categories: rept (reporting), mon (monitoring), anls (analysis), flow (workflow), mnt (maintenance)
- Validation: `plutil -lint` sur tous les .plist (16/16 passed)

### Fixed - Git History Traceability

**History rewrite** (reset soft + force push):
- Commits ROADMAP reorganization avec références `[ROADMAP@<sha>]`
- 2 commits réecrits: ROADMAP update + historical note
- Force push avec `--force-with-lease` après pre-flight checks
- 0 PR/Issue references impactés (clean history)

**Configuration standards**:
- Enforcement: ALL .env access via `magma_cycling/config.py`
- Prohibition: Direct .env reading by modules
- Documentation: README + code comments + pre-commit reminder

### Release

**GitHub Release v3.0.0** (25 Jan 2026):
- URL: https://github.com/stephanejouve/magma-cycling/releases/tag/v3.0.0
- Tag: v3.0.0
- 206 commits depuis v2.0.0 (1er Jan 2026)
- Release notes: Sprint R9 completion, LaunchAgents, ROADMAP reorganization
- Artifacts: adherence baseline dataset (JSON), LaunchAgents migration scripts

---

## [2.3.1] - 2026-01-10

### Added - Tests Suite Di2 & Upload Workouts

**54 nouveaux tests créés** (360% objectif MOA de 15 tests):

**API Di2** (`tests/api/test_intervals_client_di2.py` - 6 tests):
- `test_get_activity_streams_success_with_di2` : Extraction réussie Di2 complet
- `test_get_activity_streams_missing_di2_data` : Activité sans Di2 (indoor)
- `test_get_activity_streams_http_error` : Gestion erreur HTTP (timeout)
- `test_get_activity_streams_empty_response` : Réponse vide
- `test_get_activity_streams_partial_di2_data` : Données partielles (RearGear seul)
- `test_get_activity_streams_with_none_values` : Valeurs None (dropout signal)

**Analyzers Gear** (`tests/analyzers/test_gear_metrics.py` - 9 tests):
- `test_extract_gear_metrics_complete_data` : Extraction métriques complètes
- `test_extract_gear_metrics_cross_chaining_detection` : Détection cross-chaining
- `test_extract_gear_metrics_empty_streams` : Streams vides
- `test_extract_gear_metrics_missing_front_gear` : FrontGear manquant
- `test_extract_gear_metrics_missing_rear_gear` : RearGear manquant
- `test_extract_gear_metrics_with_none_values` : Filtrage valeurs None
- `test_gear_ratio_distribution_top_5` : Distribution top 5 ratios
- `test_extract_gear_metrics_api_exception` : Exception API
- `test_extract_gear_metrics_no_shifts` : 0 shifts (constant gear)

**Workflows Validator** (`tests/workflows/test_upload_workouts_validator.py` - 14 tests):
- Pattern `(?i)-REPOS($|\s)` : 14 tests edge cases
  - Variants: uppercase, lowercase, mixed, avec espace
  - False positives: "-REPOS-COMPLET", "PostRepos"
  - Normal workouts require warmup/cooldown validation

**Workflows Upload** (`tests/workflows/test_upload_workouts_full.py` - 18 tests):
- `TestCalculateWeekStartDate` (3 tests) : S075, S001, validation Monday
- `TestWorkoutUploaderInit` (3 tests) : Config file, env vars, no credentials
- `TestValidateWorkoutNotation` (3 tests) : Valid, bad notation, rest day
- `TestParseWorkoutsFile` (3 tests) : Single, multiple, TSS extraction
- `TestUploadWorkout` (2 tests) : Success, API failure
- `TestUploadAll` (3 tests) : Dry-run, success, partial failure
- `TestIntegrationUploadWorkflow` (1 test) : Parse → validate → upload

**Integration Di2** (`tests/integration/test_di2_workflow.py` - 8 tests):
- End-to-end workflow: extraction → aggregation → learnings
- Indoor/outdoor detection, API exceptions, multiple activities
- 7 passed + 1 skipped (requires real API)

### Changed - Coverage Improvement

**Coverage overall: 29%** (+1% improvement from 28%):
- **Total:** 9,854 lignes, 6,958 missed
- **upload_workouts.py:** 0% → 53% (+53%!) - 148 lignes couvertes
- **intervals_client.py:** 72% (Di2 methods tested)
- **weekly_aggregator.py:** 44% (gear metrics functions covered)

**Test suite:**
- **598 tests total** (596 passed, 1 failed legacy, 1 skipped)
- **99.7% success rate**
- Pre-commit hooks: ✅ 0 violations
- Ruff, MyPy, Pydocstyle: ✅ All validated

**Core modules well-tested:**
- utils/metrics.py: 100%
- ai_providers/ollama.py: 100%
- planning/calendar.py: 98%
- intelligence/training_intelligence.py: 95%
- planning/planning_manager.py: 96%

### Documentation

**Reports:**
- `docs/TESTS_COVERAGE_REPORT.md` : Rapport complet coverage v2.3.1
  - 54 tests créés (360% objectif)
  - Coverage détaillé par module
  - Output pytest complet
  - Recommandation acceptation MOA

**Sphinx Documentation:**
- Compilation HTML: `docs/_build/html/`
- Modules API, Analyzers, Config, Core, Intelligence, Planning, Utils

---

## [2.3.0] - 2026-01-10

### Added - Analyse Di2 & Optimisation Synchro Shift

**Extraction Données Di2** (`magma_cycling/api/intervals_client.py`, `magma_cycling/analyzers/weekly_aggregator.py`):
- **IntervalsClient.get_activity_streams()** : Récupération streams temporels activités
  - Accès 17 types streams : FrontGear, RearGear, GearRatio, RearGearIndex, watts, heartrate, cadence, etc.
  - Format: List[dict] avec 'type' et 'data' fields
  - Utilisé pour extraction données Di2 (Shimano Electronic Shifting)
- **WeeklyAggregator._extract_gear_metrics()** : Extraction métriques changements vitesse
  - Calcul shifts totaux, front shifts, rear shifts
  - Calcul ratio moyen développement (gear_ratio)
  - Distribution top 5 ratios utilisés (pour analyse préférences)
  - Détection outdoor/indoor: `activity.get("trainer") is False or activity.get("type") == "Ride"`
- **Analyse Patterns Training Learnings** :
  - Détection changements excessifs (>50 shifts/h) → recommandation anticipation fluide
  - Reconnaissance bonne gestion (<20 shifts/h, >30 shifts) → validation pratique
  - Analyse développement moyen : <1.5 (vallonné) vs >3.0 (plat)

**Insights Analyse 23 Sorties** (Mai 2025 - Novembre 2025):
- **211,579 points données** collectés (5,406 shifts totaux sur 58h50)
- **Corrélation négative dénivelé vs shifts** (r = -0.40) :
  - Terrain plat (<8m/km) : 123 shifts/h (micro-ajustements continus)
  - Terrain vallonné+ (>12m/km) : 84 shifts/h (rapport stable sur pentes)
  - Intensité non corrélée : r = -0.09 (changements = fonction terrain, pas effort)
- **Cross-chaining détecté 19.4%** :
  - 50T + gros pignons (≥24T) : 18.9% du temps
  - Impact : usure transmission +39%, efficacité -2-3%
- **Usage plateaux** :
  - Grand plateau (50T) : 76.9% (terrain majoritairement plat)
  - Petit plateau (34T) : 23.1%
  - Ratio plateau/pignon : 1:14.9 (15× plus changements pignon que plateau)

**Configuration Synchro Shift Personnalisée** :
- **PDF Professionnel** : `~/training-logs/Di2_Synchro_Shift_Configuration.pdf`
  - 8 pages, 12 KB
  - Analyse personnalisée basée sur données réelles utilisateur
- **Recommandations** :
  - Mode : Semi-Synchro priorité grand plateau (50T)
  - Transition UP (34T → 50T) : Point 21T (observé 47× naturellement)
  - Transition DOWN (50T → 34T) : Point 30T (observé 59× naturellement)
  - Plages autorisées : 34T pour 21-34T, 50T pour 11-24T
- **Bénéfices attendus** :
  - Réduction cross-chaining : 19.4% → <2%
  - Usure chaîne réduite : ~39%
  - Efficacité transmission : +2-3%
- **Guide complet** :
  - Configuration E-Tube Project (PC/Mac)
  - Configuration E-Tube Ride (smartphone)
  - Procédure test et ajustement
  - Alternative règle mentale simple

**Tests** :
- Validation extraction Di2 sur S067-01-TERRAIN (10 nov 2025) : 394 shifts détectés
- Test corrélation terrain : 23 sorties, 3 catégories (plat/vallonné/vallonné+)
- Génération PDF : 23 sorties analysées en <2min

### Fixed - Validateur Jours Repos

**WorkoutUploader.validate_workout_notation()** (`magma_cycling/upload_workouts.py`):
- **Problème** : Validateur exigeait warmup/cooldown pour TOUS workouts, y compris repos
  - Jours repos (format: S076-07-REPOS) rejetés comme incomplets
  - Utilisateur forcé d'ajouter sections factices "Warmup: Repos" pour passer validation
- **Solution** : Détection automatique jours repos + skip validation
  - Pattern détection : `r"(?i)-REPOS($|\s)"` (case insensitive, word boundary)
  - Si repos détecté → skip validation warmup/cooldown
  - Autres workouts → validation normale maintenue
- **Format accepté** :
  ```
  === WORKOUT S076-07-REPOS ===
  REPOS COMPLET - Aucune activite
  === FIN WORKOUT ===
  ```
- **Tests** :
  - S999-01-REC-Test (normal) : ✅ Validation warmup/cooldown active
  - S999-07-REPOS (repos) : ✅ Skip validation, pas warnings
  - Pre-commit hooks : ✅ Tous passés

### Changed - Weekly Analysis

**Training Learnings** (`magma_cycling/analyzers/weekly_aggregator.py`):
- **Refactoring** : `_extract_training_learnings()` reçoit maintenant `processed["workouts"]` au lieu de `raw_data["activities"]`
  - Permet accès données enrichies : gear_metrics, pedal_balance, etc.
  - Fix data flow : extraction gear → process workouts → analyze learnings
- **Nouveau champ workouts** : `gear_metrics` (dict optionnel) :
  - `shifts` : int (total changements vitesse)
  - `front_shifts` : int (changements plateau avant)
  - `rear_shifts` : int (changements pignon arrière)
  - `avg_gear_ratio` : float (ratio moyen développement)
  - `gear_ratio_distribution` : dict (top 5 ratios utilisés)

### Documentation

**Session Log** (`project-docs/sessions/SESSION_20260110_DI2_ANALYSIS.md`):
- Brief MOA complet (10 janvier 2026)
- Objectifs, livrables, statistiques, découvertes techniques
- Validation MOA : ✅ Prêt production

**Références** :
- Commits : a5c75c7 (feat Di2), cd066a0 (fix validateur)
- Documents générés : Di2_Synchro_Shift_Configuration.pdf
- Période analysée : Mai 2025 - Novembre 2025 (23 sorties outdoor)

---

## [2.2.0] - 2026-01-02

### Added - Sprint R4++ (Backfill Historique & PID Controller)

**Phase 2 - Backfill Historique** (`magma_cycling/scripts/backfill_intelligence.py`):
- **IntervalsICUBackfiller** : Extraction learnings/patterns depuis historique Intervals.icu (2024-2025)
  - `fetch_activities()` : Récupération activités via IntervalsClient API
  - `fetch_wellness()` : Récupération données sommeil/HRV
  - `classify_workout_type()` : Classification automatique (sweet-spot, vo2, tempo, endurance, recovery)
  - `analyze_sweet_spot_sessions()` : Extraction intensité optimale (88-90% FTP)
  - `analyze_vo2_sleep_correlation()` : Détection pattern échec VO2 après nuit courte (<6h)
  - `analyze_outdoor_discipline()` : Mesure overshoot intensité outdoor vs indoor
  - `analyze_ftp_progression()` : Documentation progression FTP historique
  - `run()` : Pipeline complet backfill avec output JSON
- **CLI Script** : `poetry run backfill-intelligence --start-date YYYY-MM-DD --end-date YYYY-MM-DD`
  - Support credentials via `.env` (INTERVALS_ATHLETE_ID, INTERVALS_API_KEY)
  - Arguments optionnels : `--athlete-id`, `--api-key`, `--output`
  - Output détaillé : Learnings count, Patterns count, Confidence levels
- **Bénéfices** :
  - Démarrage accéléré avec 10+ learnings VALIDATED au lieu de partir de zéro
  - Patterns récurrents détectés automatiquement (ex: 12 échecs VO2/34 tentatives)
  - FTP progression documentée (ex: +10W sur 24 mois)
  - Gains PID adaptatifs immédiatement opérationnels
- **9 tests backfill** (test_backfill.py, 180% over-delivery vs 5 requis) :
  - `test_backfill_sweet_spot_extraction` : Extraction learning avec VALIDATED confidence
  - `test_backfill_vo2_sleep_correlation` : Pattern VO2/sommeil avec 40 observations
  - `test_backfill_outdoor_discipline` : Pattern overshoot intensité outdoor
  - `test_backfill_ftp_progression` : Learning progression FTP historique
  - `test_backfill_workout_classification` : Classification IF-based et name-based
  - `test_backfill_confidence_assignment` : Confidence basée sur session count (pas evidence count)
  - `test_backfill_fetch_activities` : Mock IntervalsClient.get_activities()
  - `test_backfill_fetch_wellness` : Mock IntervalsClient.get_wellness()
  - `test_backfill_empty_data` : Gestion données vides (0 activités)

**Phase 3 - PID Controller** (`magma_cycling/intelligence/pid_controller.py`):
- **PIDController** : Contrôleur PID adaptatif pour progression FTP automatique
  - `compute()` : Calcul correction PID (Proportionnel + Intégral + Dérivé)
    - Formula: `output = Kp × error + Ki × ∫error dt + Kd × d(error)/dt`
    - TSS translation: `+1W FTP ≈ +12.5 TSS/semaine` (approximation middle-range)
    - Output: Dict avec error, p_term, i_term, d_term, output, tss_adjustment
  - `reset()` : Reset état interne (integral, prev_error) lors changement phase
  - `get_action_recommendation()` : Traduction correction → recommandation actionnable (français)
  - **Anti-Windup** : Saturation integral term à ±100W (éviter accumulation excessive)
  - **Output Saturation** : TSS adjustment limité à ±50 TSS/semaine (limites raisonnables)
- **PIDState** : Dataclass état interne (integral, prev_error, last_update)
- **compute_pid_gains_from_intelligence()** : Calcul gains adaptatifs depuis Training Intelligence
  - **Kp (Proportionnel)** : Basé sur learnings validés (confidence système)
    - 0 learnings → 0.005 (conservateur)
    - 100+ learnings → 0.015 (agressif)
    - Range: 0.005-0.015
  - **Ki (Intégral)** : Basé sur evidence cumulée (stabilité corrections)
    - <20 evidence → 0.001
    - 20-50 evidence → 0.002
    - >50 evidence → 0.003
  - **Kd (Dérivé)** : Basé sur patterns fréquents (détection tendances)
    - 0 patterns (freq >= 10) → 0.10
    - 1-2 patterns → 0.15
    - 3+ patterns → 0.25
- **TrainingIntelligence.get_pid_correction()** : Méthode intégrée correction PID
  - Args: current_ftp, target_ftp, dt
  - Returns: Dict avec correction, recommendation, gains
  - Calcul automatique gains depuis intelligence accumulée
- **16 tests PID** (test_pid_controller.py, 320% over-delivery vs 5 requis) :
  - `test_pid_compute_positive_error` : Correction positive (FTP < target)
  - `test_pid_compute_negative_error` : Correction négative (FTP > target)
  - `test_pid_integral_anti_windup` : Saturation integral à ±100W
  - `test_pid_derivative_term` : Détection tendances (error croissant/décroissant)
  - `test_pid_output_saturation` : TSS adjustment limité à ±50
  - `test_pid_reset` : Reset état interne
  - `test_pid_action_recommendation_increase` : Recommandation augmentation TSS
  - `test_pid_action_recommendation_decrease` : Recommandation réduction TSS
  - `test_pid_action_recommendation_maintain` : Recommandation maintien
  - `test_compute_gains_from_empty_intelligence` : Gains par défaut (conservateurs)
  - `test_compute_gains_from_validated_learnings` : Kp augmente avec learnings validés
  - `test_compute_gains_with_many_patterns` : Kd augmente avec patterns fréquents
  - `test_compute_gains_with_high_evidence` : Ki augmente avec evidence cumulée
  - `test_training_intelligence_get_pid_correction` : Intégration TrainingIntelligence
  - `test_pid_controller_invalid_inputs` : Validation gains négatifs/setpoint invalide
  - `test_pid_multiple_iterations` : Convergence sur 20 semaines

**Exports & Integration** (`magma_cycling/intelligence/__init__.py`):
- Ajout exports : `PIDController`, `PIDState`, `compute_pid_gains_from_intelligence`
- Backward compatible : Enrichit API sans breaking changes

**Documentation** (project-docs/guides/GUIDE_INTELLIGENCE.md v2.1.0 → v2.2.0):
- **Section "Backfill Historique"** (~370 lignes) :
  - Principe et avantages
  - Installation script et configuration credentials
  - Usage basique (CLI + Python)
  - Détail 4 analyses extraites (Sweet-Spot, VO2/Sleep, Outdoor, FTP)
  - Utilisation intelligence backfillée (charger, merger)
  - Troubleshooting (API key, no activities, confidence)
  - Customisation backfill pour analyses custom
- **Section "Contrôle PID Adaptatif"** (~400 lignes) :
  - Principe composantes PID (Proportionnel, Intégral, Dérivé)
  - Gains adaptatifs (calcul depuis intelligence)
  - Formule PID et traduction TSS
  - Règles calcul Kp/Ki/Kd détaillées avec exemples
  - Usage basique (correction simple)
  - Intégration TrainingIntelligence
  - Workflow hebdomadaire avec PID
  - Reset PID state (changement phase)
  - Anti-windup et saturation (détails techniques)
  - Troubleshooting PID (gains minimum, saturation, oscillations)
  - Limites système PID (feedback régulier, facteurs externes)
- **API Reference** : Ajout méthodes PID
  - `TrainingIntelligence.get_pid_correction()` : Correction PID intégrée
  - `PIDController.__init__()`, `compute()`, `reset()`, `get_action_recommendation()`
  - `compute_pid_gains_from_intelligence()` : Gains adaptatifs

**Poetry Configuration** (pyproject.toml):
- Script CLI `backfill-intelligence` : `magma_cycling.scripts.backfill_intelligence:main`

**Métriques Sprint R4++**:
- **Code** :
  - backfill_intelligence.py : 503 lignes
  - pid_controller.py : 305 lignes
  - training_intelligence.py : +58 lignes (get_pid_correction)
  - Total : 866 lignes
- **Tests** :
  - 44 tests intelligence total (19 R4 + 9 backfill + 16 PID)
  - 25 nouveaux tests Sprint R4++ (400% over-delivery vs 10 requis)
  - 100% passing (0 failures, 0 regressions)
- **Documentation** :
  - GUIDE_INTELLIGENCE.md : +770 lignes (2 sections + API Reference)
  - Total guide : 1692 lignes (v2.2.0)

**Impact**:
- **Onboarding Accéléré** : Backfill 2 ans données → 10+ learnings VALIDATED immédiatement
- **Progression FTP Automatisée** : PID controller ajuste TSS hebdo selon écart cible
- **Gains Adaptatifs** : Kp/Ki/Kd calculés depuis intelligence (conservateur → agressif selon knowledge)
- **Evidence-Based Training** : Patterns historiques détectés automatiquement (VO2/sommeil, outdoor overshoot)
- **Feedback Loop Complet** : Backfill → Intelligence → PID → Ajustement charge → Progression FTP


## [2.1.1] - 2026-01-02

### Fixed

**Intervals.icu API Client** (`magma_cycling/api/intervals_client.py`):
- Ajout méthode `delete_event(event_id)` : Suppression événements calendrier
- Ajout méthode `update_event(event_id, event_data)` : Mise à jour événements calendrier
- Support complet CRUD pour événements (Create, Read, Update, Delete)

**Session Status Tool** (`magma_cycling/update_session_status.py` v2.1.0):
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

**Training Intelligence** (`magma_cycling/intelligence/training_intelligence.py`):
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
- JSON persistence optionnelle (`~/magma-cycling-data/intelligence/`)
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

**Planning Manager** (`magma_cycling/planning/planning_manager.py`):
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

**Training Calendar** (`magma_cycling/planning/calendar.py`):
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

**VETO Logic** (`magma_cycling/utils/metrics_advanced.py`):
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

**Nouvelles Métriques** (`magma_cycling/utils/metrics_advanced.py`):
- `calculate_ctl()` : Chronic Training Load (fitness 42 jours)
- `calculate_tsb()` : Training Stress Balance (forme vs fatigue)
- `calculate_ramp_rate()` : Rampe CTL avec validation limites
- `assess_overtraining_risk()` : Évaluation risque surentraînement
  - Niveaux : LOW/MEDIUM/HIGH
  - Critères : TSB, CTL ramp rate, profil athlète
  - Recommandations personnalisées

**Athlete Profile** (`magma_cycling/config/athlete_profile.py`):
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
