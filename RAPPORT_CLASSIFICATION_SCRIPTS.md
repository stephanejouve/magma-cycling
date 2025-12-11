# Classification Scripts Projet - 8 Décembre 2025

## 📊 Résumé Exécutif

**Total scripts analysés**: 39 fichiers Python
**Répartition**:
- **CORE (Production)**: 11 scripts
- **UTIL (Maintenance)**: 5 scripts
- **TEST (Validation)**: 13 scripts
- **DEPRECATED (Obsolètes)**: 2 scripts
- **MODULE (Bibliothèques)**: 5 scripts (withings_integration)
- **BACKUP (Archives)**: 2 scripts

---

## 📁 Inventaire Complet par Catégorie

### 🔵 Catégorie CORE (Production) - 11 scripts

Scripts essentiels au workflow quotidien/hebdomadaire d'analyse d'entraînement.

| Fichier | Lignes | Dernière Modif | Rôle Principal | Fréquence |
|---------|--------|----------------|----------------|-----------|
| **workflow_coach.py** | 1485 | 2025-12-08 | Orchestrateur workflow complet | **Quotidien** |
| **sync_intervals.py** | 381 | 2025-11-23 | Synchronisation Intervals.icu → logs | **Quotidien** |
| **prepare_analysis.py** | 1162 | 2025-11-23 | Génération prompt analyse Claude.ai | **Quotidien** |
| **insert_analysis.py** | 439 | 2025-12-08 | Insertion analyse dans workouts-history | **Quotidien** |
| **collect_athlete_feedback.py** | 418 | 2025-11-23 | Collecte feedback athlète pré-analyse | **Quotidien** |
| **weekly_analysis.py** | 729 | 2025-11-23 | Génération rapports hebdomadaires | **Hebdomadaire** |
| **prepare_weekly_report.py** | 366 | 2025-12-08 | Préparation prompt rapport hebdo | **Hebdomadaire** |
| **organize_weekly_report.py** | 329 | 2025-12-08 | Organisation fichiers rapport hebdo | **Hebdomadaire** |
| **weekly_planner.py** | 592 | 2025-11-25 | Planification semaine entraînement | **Hebdomadaire** |
| **upload_workouts.py** | 283 | 2025-11-25 | Upload séances planifiées → Intervals.icu | **Hebdomadaire** |
| **workflow_state.py** | 169 | 2025-11-23 | Gestion état workflow (détection gaps) | **Support** |

#### Détails CORE

**workflow_coach.py** (★ Script Principal)
```
Rôle: Orchestrateur du workflow complet d'analyse séance
Input: Intervals.icu API, feedback athlète, logs historiques
Output: Analyse complète insérée dans workouts-history.md
Dépendances: prepare_analysis.py, insert_analysis.py, workflow_state.py
Safety: Non-destructif (append-only logs)
```

**sync_intervals.py**
```
Rôle: Récupération automatique données Intervals.icu
Input: Intervals.icu API (/activities, /wellness)
Output: Mise à jour logs/ avec métriques quantitatives
Fréquence: Post-séance (déclenchement manuel ou automatique)
Safety: Non-destructif (append-only)
```

**prepare_analysis.py**
```
Rôle: Génération prompt optimisé pour Claude.ai
Input: Activité Intervals.icu + contexte athlète + logs récents
Output: Prompt markdown copié dans presse-papier
Dépendances: workflow_state.py, Intervals.icu API
```

**insert_analysis.py**
```
Rôle: Insertion analyse Claude.ai dans workouts-history.md
Input: Markdown analyse (presse-papier ou fichier)
Output: workouts-history.md mis à jour (append)
Validation: 9 sections obligatoires (séances exécutées)
Support: Batch multi-sessions (repos/annulations)
```

**weekly_analysis.py**
```
Rôle: Génération automatique 6 fichiers rapport hebdomadaire
Input: workouts-history.md, métriques semaine
Output: logs/weekly_reports/SXXX/*.md (6 fichiers)
Fichiers générés:
  - workout_history_SXXX.md
  - metrics_evolution_SXXX.md
  - training_learnings_SXXX.md
  - protocol_adaptations_SXXX.md
  - transition_SXXX_SYYY.md
  - bilan_final_SXXX.md
```

**weekly_planner.py**
```
Rôle: Planification semaine suivante basée sur progression
Input: Rapports hebdomadaires, état athlète actuel
Output: Plan semaine suivante (JSON + markdown)
```

**upload_workouts.py**
```
Rôle: Upload séances planifiées vers Intervals.icu
Input: Plan semaine (JSON/markdown)
Output: Séances créées dans calendrier Intervals.icu
API: POST /events (création événements calendrier)
```

---

### 🟡 Catégorie UTIL (Maintenance) - 5 scripts

Scripts utilitaires pour maintenance/administration ponctuelle.

| Fichier | Lignes | Dernière Modif | Rôle Principal | Usage |
|---------|--------|----------------|----------------|-------|
| **fix_weekly_reports_casing.py** | 393 | 2025-12-08 | Correction casse répertoires/fichiers | **Ponctuel** |
| **validate_naming_convention.py** | 251 | 2025-12-08 | Validation stricte conventions nommage | **On-demand** |
| **rest_and_cancellations.py** | 664 | Non versionné | Gestion repos/annulations dans workflow | **Support** |
| **check_activity_sources.py** | 207 | 2025-11-23 | Audit sources activités Intervals.icu | **Diagnostic** |
| **stats.py** | 130 | 2025-11-13 | Statistiques générales projet | **Reporting** |

#### Détails UTIL

**fix_weekly_reports_casing.py**
```
Rôle: Correction incohérences casse (minuscule → MAJUSCULE)
Input: logs/weekly_reports/ (structure existante)
Output: Structure corrigée + backup automatique
Safety: DESTRUCTIF (renommage) - Backup requis ✅
Rollback: Oui (backup timestamp préservé)
Usage: Exécution ponctuelle après détection problèmes
```

**validate_naming_convention.py**
```
Rôle: Vérification conformité structure weekly_reports
Input: logs/weekly_reports/ (read-only)
Output: Rapport console + exit code (0=pass, 1=fail)
Safety: Non-destructif (lecture seule)
Convention validée: SXXX format strict (répertoires + fichiers)
```

**rest_and_cancellations.py**
```
Rôle: Gestion repos planifiés et annulations séances
Input: Planning semaine, logs récents
Output: Markdowns repos/annulations formatés
Utilisation: Importé par workflow_coach.py
```

**check_activity_sources.py**
```
Rôle: Audit sources activités (Garmin, Zwift, manuel, etc.)
Input: Intervals.icu API (/activities avec metadata)
Output: Rapport sources par type, détection anomalies
Usage: Diagnostic qualité données
```

---

### 🔴 Catégorie TEST (Validation/Debug) - 13 scripts

Scripts tests, validation, debug temporaires ou développement.

| Fichier | Lignes | Status | Rôle | Peut Supprimer? |
|---------|--------|--------|------|-----------------|
| **test_rest_and_cancellations.py** | 468 | Non versionné | Tests module rest/cancellations | ⚠️ Si tests passent |
| **demo_rest_handling.py** | 334 | Non versionné | Démo fonctionnalité repos | ✅ Après doc |
| **mark_cancelled.py** | 228 | Non versionné | Marquage annulation unique | ⚠️ À intégrer CORE? |
| **debug_detection.py** | 124 | 2025-11-22 | Debug détection gaps workflow | ✅ Temporaire |
| **test_weekly_corrections.py** | 99 | Non versionné | Tests corrections rapports hebdo | ⚠️ Si tests passent |
| **test_weekly_parser.py** | 97 | Non versionné | Tests parser rapports hebdo | ⚠️ Si tests passent |
| **test_create_event.py** | 92 | Non versionné | Test création événement Intervals.icu | ✅ Obsolète |
| **test_activity_details.py** | 38 | Non versionné | Test détails activité API | ✅ Obsolète |
| **test_14nov.py** | 35 | Non versionné | Test spécifique date 14 nov | ✅ Temporaire |
| **test_7days.py** | 35 | Non versionné | Test récupération 7 jours | ✅ Obsolète |
| **test_filters.py** | 26 | Non versionné | Test filtres API | ✅ Obsolète |
| **test_all_fields.py** | 25 | Non versionné | Test tous champs API | ✅ Obsolète |
| **test_api.py** | 16 | Non versionné | Test basique API | ✅ Obsolète |
| **test_wellness.py** | 16 | Non versionné | Test endpoint wellness | ✅ Obsolète |

#### Analyse TEST

**Scripts à conserver (après nettoyage):**
- `test_rest_and_cancellations.py` : Tests unitaires fonctionnalité importante
- `test_weekly_parser.py` : Validation parsing rapports hebdo
- `test_weekly_corrections.py` : Tests corrections structure

**Scripts à supprimer (obsolètes/temporaires):**
- Tous les `test_*.py` minimalistes (API tests basiques déjà validés)
- `debug_detection.py` : Bug corrigé, script debug temporaire
- `demo_rest_handling.py` : Démo développement, peut être supprimé après doc

**Scripts ambigus:**
- `mark_cancelled.py` : Fonctionnalité potentiellement utile, à intégrer dans CORE (workflow_coach) ou supprimer si redondant

---

### ⚫ Catégorie DEPRECATED (Obsolètes) - 2 scripts

Scripts obsolètes dans dossier backups (migration antérieure).

| Fichier | Lignes | Date Backup | Raison Obsolescence |
|---------|--------|-------------|---------------------|
| backups/.../organize_weekly_report.py | ? | 2025-11-25 | Remplacé par version scripts/ |
| backups/.../prepare_weekly_report.py | ? | 2025-11-25 | Remplacé par version scripts/ |

**Action recommandée**: Vérifier différences avec versions actuelles, puis supprimer backup après 30 jours.

---

### 🟢 Catégorie MODULE (Bibliothèques) - 5 scripts

Module d'intégration Withings (balance connectée).

| Fichier | Lignes | Rôle |
|---------|--------|------|
| withings_integration/core/withings_integration.py | Modifié | API client Withings |
| withings_integration/scripts/withings_setup.py | Modifié | Setup automatique intégration |
| withings_integration/scripts/withings_setup_manual.py | Non versionné | Setup manuel alternatif |
| withings_integration/scripts/withings_sync.py | Modifié | Synchronisation poids/métriques |
| withings_integration/scripts/check_withings_install.py | Modifié | Vérification installation |
| withings_integration/__init__.py | Non versionné | Init module |
| withings_integration/core/__init__.py | Non versionné | Init sous-module |
| withings_integration/scripts/__init__.py | Non versionné | Init sous-module |

**Note**: Module séparé, pas de réorganisation nécessaire (déjà bien structuré).

---

### 🔧 Fichier Racine

| Fichier | Lignes | Catégorie | Rôle | Action |
|---------|--------|-----------|------|--------|
| inspect_workout.py | ? | TEST | Script inspect temporaire? | ⚠️ À classer |

---

## 🕸️ Graphe Dépendances

### Workflow Principal (CORE)

```
[Utilisateur]
    ↓
workflow_coach.py (Orchestrateur)
    ├─> workflow_state.py (Détection gaps)
    │   └─> logs/workouts-history.md (lecture)
    │
    ├─> collect_athlete_feedback.py (optionnel)
    │   └─> /tmp/athlete_feedback.txt
    │
    ├─> prepare_analysis.py
    │   ├─> Intervals.icu API (/activities)
    │   ├─> workflow_state.py
    │   ├─> logs/workouts-history.md
    │   ├─> logs/metrics-evolution.md
    │   └─> Presse-papier (output prompt)
    │
    ├─> [Claude.ai - Interaction Utilisateur]
    │
    └─> insert_analysis.py
        ├─> Presse-papier (input analyse)
        ├─> logs/workouts-history.md (append)
        └─> Git commit (optionnel)

[Utilisateur - Fin Semaine]
    ↓
weekly_analysis.py
    ├─> logs/workouts-history.md
    ├─> logs/metrics-evolution.md
    └─> logs/weekly_reports/SXXX/*.md (6 fichiers)

    ↓
prepare_weekly_report.py (génère prompt IA)
    └─> Presse-papier (prompt rapport hebdo)

    ↓
[Claude.ai - Génération 6 fichiers]

    ↓
organize_weekly_report.py (organisation fichiers)
    ├─> Presse-papier (6 fichiers markdown)
    └─> logs/weekly_reports/SXXX/*.md (écriture)
```

### Synchronisation Données (CORE)

```
sync_intervals.py
    ├─> Intervals.icu API
    │   ├─> /activities (séances)
    │   └─> /wellness (métriques quotidiennes)
    │
    └─> logs/
        ├─> workouts-history.md (append)
        └─> metrics-evolution.md (update)
```

### Planification Semaine (CORE)

```
weekly_planner.py
    ├─> logs/weekly_reports/SXXX/*.md (lecture)
    ├─> État athlète actuel
    └─> plan_semaine_SYYY.json (output)

    ↓
upload_workouts.py
    ├─> plan_semaine_SYYY.json (input)
    ├─> Intervals.icu API (POST /events)
    └─> Calendrier Intervals.icu (mise à jour)
```

### Maintenance (UTIL)

```
fix_weekly_reports_casing.py
    ├─> logs/weekly_reports/ (lecture structure)
    ├─> Backup automatique
    └─> logs/weekly_reports/ (renommages)

validate_naming_convention.py
    ├─> logs/weekly_reports/ (lecture seule)
    └─> Console (rapport validation)
```

---

## 🔍 Analyse Détaillée

### Scripts Non Versionnés (12 fichiers)

**Scripts TEST (à évaluer suppression):**
- test_rest_and_cancellations.py
- demo_rest_handling.py
- mark_cancelled.py
- test_weekly_corrections.py
- test_weekly_parser.py
- test_create_event.py
- test_activity_details.py
- test_14nov.py
- test_7days.py
- test_filters.py
- test_all_fields.py
- test_api.py
- test_wellness.py

**Scripts UTIL (à versionner):**
- rest_and_cancellations.py (module support CORE)

**Action requise**:
1. Versionner `rest_and_cancellations.py` (module actif)
2. Archiver ou supprimer scripts TEST obsolètes

### Patterns Détectés

#### ✅ Bonne Pratique
- Séparation claire workflow quotidien vs hebdomadaire
- Scripts modulaires réutilisables (workflow_state.py, rest_and_cancellations.py)
- Backups automatiques dans scripts UTIL destructifs
- Utilisation presse-papier pour interaction IA (évite fichiers temporaires)

#### ⚠️ Points Amélioration
- Trop de scripts TEST non versionnés (pollution)
- Pas de tests unitaires structurés (pytest, unittest)
- Chemins relatifs potentiellement fragiles
- Documentation inégale (certains scripts sans docstring détaillée)
- Pas de CI/CD pour validation automatique

---

## 📋 Recommandations

### Priorité 1 : Nettoyage Immédiat

**Supprimer après archivage:**
```bash
# Scripts TEST obsolètes (API basique déjà validée)
scripts/test_api.py
scripts/test_wellness.py
scripts/test_all_fields.py
scripts/test_filters.py
scripts/test_7days.py
scripts/test_14nov.py
scripts/test_activity_details.py
scripts/test_create_event.py
scripts/debug_detection.py  # Bug corrigé
```

**Archiver dans backups/ avant suppression:**
```bash
mkdir -p backups/tests_archive_20251208/
mv scripts/test_*.py backups/tests_archive_20251208/
mv scripts/debug_*.py backups/tests_archive_20251208/
mv scripts/demo_*.py backups/tests_archive_20251208/
```

### Priorité 2 : Versionner Scripts Actifs

```bash
git add scripts/rest_and_cancellations.py
git add scripts/mark_cancelled.py  # Si décision garder
git commit -m "chore: Versionner modules support workflow"
```

### Priorité 3 : Réorganisation Structure (Optionnel)

#### Option A : Structure Dossiers (Recommandé)

```
scripts/
├── core/                          # Production (11 scripts)
│   ├── workflow_coach.py          # ★ Orchestrateur
│   ├── sync_intervals.py
│   ├── prepare_analysis.py
│   ├── insert_analysis.py
│   ├── collect_athlete_feedback.py
│   ├── weekly_analysis.py
│   ├── prepare_weekly_report.py
│   ├── organize_weekly_report.py
│   ├── weekly_planner.py
│   ├── upload_workouts.py
│   └── workflow_state.py          # Module support
│
├── utils/                         # Maintenance (5 scripts)
│   ├── fix_weekly_reports_casing.py
│   ├── validate_naming_convention.py
│   ├── rest_and_cancellations.py
│   ├── check_activity_sources.py
│   └── stats.py
│
├── tests/                         # Tests (3 scripts conservés)
│   ├── test_rest_and_cancellations.py
│   ├── test_weekly_parser.py
│   └── test_weekly_corrections.py
│
└── deprecated/                    # Obsolètes
    └── [scripts archivés]
```

**Avantages:**
- Séparation claire responsabilités
- Facilite maintenance (ajout/suppression scripts)
- Prépare intégration CI/CD future
- Autodocumenté (structure = documentation)

**Inconvénients:**
- Nécessite correction imports relatifs
- Tests fonctionnalité post-déplacement
- Migration progressive (risque disruption workflow)

#### Option B : Tatouage Seul (Plus Sûr)

Ajouter headers standardisés SANS déplacer fichiers.

**Avantages:**
- Aucune disruption workflow existant
- Pas de correction imports nécessaire
- Réversible facilement
- Peut être fait graduellement

**Inconvénients:**
- scripts/ reste encombré (31 fichiers actuellement)
- Classification moins visible
- Maintenance plus difficile long terme

### Priorité 4 : Standardisation Headers

**Template header CORE:**
```python
#!/usr/bin/env python3
"""
[CORE] workflow_coach.py - Orchestrateur workflow analyse séances

METADATA:
  Category: CORE
  Purpose: Orchestration complète workflow quotidien (détection → analyse → insertion)
  Usage: python3 scripts/workflow_coach.py [--skip-feedback] [--activity-id XXX]
  Dependencies: prepare_analysis.py, insert_analysis.py, workflow_state.py, Intervals.icu API
  Last Updated: 2025-12-08
  Author: Stéphane Jouve / Claude Code

WORKFLOW POSITION:
  Input: Intervals.icu API, logs/workouts-history.md, feedback athlète (optionnel)
  Output: Analyse complète insérée dans workouts-history.md + git commit
  Frequency: Daily (post-séance)

SAFETY:
  Destructive: No (append-only)
  Backup Required: No (historique git)
  Rollback Available: Yes (git history)
"""

import argparse
import sys
from pathlib import Path
# ...
```

**Application progressive:**
1. Phase 1: Scripts CORE uniquement (11 scripts) - **Prioritaire**
2. Phase 2: Scripts UTIL (5 scripts)
3. Phase 3: Scripts TEST conservés (3 scripts)

### Priorité 5 : Documentation Centrale

**Créer `scripts/README.md`:**
```markdown
# Scripts Projet Cyclisme Training Logs

## Organisation

### Scripts Production (core/)
Scripts utilisés quotidiennement/hebdomadairement.
Voir détails: [RAPPORT_CLASSIFICATION_SCRIPTS.md]

### Scripts Maintenance (utils/)
Scripts ponctuels maintenance/admin.

### Scripts Tests (tests/)
Tests unitaires et validation.

## Workflow Quotidien

1. **workflow_coach.py** - Orchestrateur principal
   - Détecte gaps workouts-history.md
   - Guide analyse complète séance

2. **sync_intervals.py** - Synchronisation données (optionnel)

## Workflow Hebdomadaire

1. **weekly_analysis.py** - Génération 6 fichiers rapport
2. **weekly_planner.py** - Planification semaine suivante
3. **upload_workouts.py** - Upload plan vers Intervals.icu

## Conventions

### Chemins
Toujours utiliser chemins depuis PROJECT_ROOT:
```python
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
```

### Nommage
- CORE: Fonctionnalités production quotidienne/hebdo
- UTIL: Maintenance ponctuelle
- TEST: Validation/debug temporaire
```

---

## 🎯 Plan Exécution Proposé

### Phase 1 : Nettoyage (Sécurisé) - 30 min

```bash
# 1. Backup complet avant toute action
cp -R scripts/ scripts.backup.20251208/

# 2. Archiver scripts TEST obsolètes
mkdir -p backups/tests_archive_20251208/
mv scripts/test_api.py backups/tests_archive_20251208/
mv scripts/test_wellness.py backups/tests_archive_20251208/
mv scripts/test_all_fields.py backups/tests_archive_20251208/
mv scripts/test_filters.py backups/tests_archive_20251208/
mv scripts/test_7days.py backups/tests_archive_20251208/
mv scripts/test_14nov.py backups/tests_archive_20251208/
mv scripts/test_activity_details.py backups/tests_archive_20251208/
mv scripts/test_create_event.py backups/tests_archive_20251208/
mv scripts/debug_detection.py backups/tests_archive_20251208/
mv scripts/demo_rest_handling.py backups/tests_archive_20251208/

# 3. Commit nettoyage
git add scripts/ backups/
git commit -m "chore: Archiver scripts TEST obsolètes (10 fichiers)"
```

**Résultat**: scripts/ passe de 31 → 21 fichiers (-32%)

### Phase 2 : Tatouage Headers - 2h

1. Tatouage 11 scripts CORE (prioritaire)
2. Tatouage 5 scripts UTIL
3. Tatouage 3 scripts TEST conservés
4. Commit après chaque groupe

### Phase 3 : Réorganisation (Optionnel) - 4h

**Seulement si validation utilisateur:**

1. Création structure dossiers (core/utils/tests/)
2. Déplacement scripts CORE (11 fichiers)
3. Tests fonctionnalité (dry-run chaque script)
4. Correction imports si nécessaire
5. Déplacement scripts UTIL (5 fichiers)
6. Tests fonctionnalité
7. Déplacement scripts TEST (3 fichiers)
8. Validation complète workflow

### Phase 4 : Documentation - 1h

1. Création scripts/README.md
2. Mise à jour README.md racine projet
3. Documentation décisions classification

---

## 📊 Récapitulatif Classifications

### Résumé par Catégorie

| Catégorie | Nombre | % Total | Action Proposée |
|-----------|--------|---------|-----------------|
| **CORE** | 11 | 28% | Tatouage + Documentation ✅ |
| **UTIL** | 5 | 13% | Tatouage + Versionner rest_and_cancellations ✅ |
| **TEST** | 13 | 33% | **Archiver 10** + Conserver 3 ✅ |
| **DEPRECATED** | 2 | 5% | Supprimer après validation différences ⚠️ |
| **MODULE** | 5 | 13% | Aucune action (déjà bien structuré) ✅ |
| **Racine** | 1 | 3% | Classifier inspect_workout.py ⚠️ |
| **Backups** | 2 | 5% | Inclus dans DEPRECATED |
| **TOTAL** | 39 | 100% | |

### Scripts par Fréquence Utilisation

| Fréquence | Scripts | Catégorie |
|-----------|---------|-----------|
| **Quotidien** | 6 scripts | workflow_coach, sync_intervals, prepare_analysis, insert_analysis, collect_feedback, workflow_state |
| **Hebdomadaire** | 5 scripts | weekly_analysis, prepare_weekly_report, organize_weekly_report, weekly_planner, upload_workouts |
| **On-demand** | 5 scripts | fix_casing, validate_naming, check_sources, stats, rest_and_cancellations |
| **Tests** | 3 scripts | test_rest_and_cancellations, test_weekly_parser, test_weekly_corrections |
| **Obsolètes** | 20 scripts | À archiver/supprimer |

---

## ✅ Checklist Validation

Avant Phase 2 (Modifications), confirmer :

- [ ] **Nettoyage**: Valider archivage 10 scripts TEST obsolètes
- [ ] **Classification**: Valider catégorisation proposée (CORE/UTIL/TEST)
- [ ] **Structure**: Choisir Option A (dossiers) ou Option B (tatouage seul)
- [ ] **Scripts ambigus**:
  - [ ] `mark_cancelled.py` : Intégrer CORE ou supprimer ?
  - [ ] `inspect_workout.py` : Classer TEST ou UTIL ?
- [ ] **Versionner**: Confirmer ajout `rest_and_cancellations.py` au repo
- [ ] **Backups DEPRECATED**: Valider suppression après vérification différences

---

## 🚀 Prochaines Étapes

**En attente de validation utilisateur sur :**

1. ✅ Classification proposée correcte ?
2. ✅ Archivage 10 scripts TEST obsolètes ?
3. ⚠️ Structure : Option A (dossiers) ou Option B (tatouage seul) ?
4. ⚠️ `mark_cancelled.py` : Garder/intégrer ou supprimer ?
5. ⚠️ Niveau tatouage : Headers complets ou version minimale ?

---

**Généré le :** 8 décembre 2025
**Outil :** Claude Code - Classification Scripts Projet
**Status :** ⏸️ Phase 1 Audit Complète - En attente validation Phase 2
