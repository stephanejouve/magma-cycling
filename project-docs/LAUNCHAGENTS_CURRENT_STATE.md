# 📊 LaunchAgents - État Actuel (Documentation)

**Date**: 25 janvier 2026
**Statut**: Documentation pré-migration

---

## 🔄 WORKFLOW QUOTIDIEN

### Pipeline Automatique (Chaque Jour)

```
21:30 → daily-sync              (Rapport activités + email)
22:00 → workout_adherence       (Collecte adherence)
23:00 → pid_evaluation          (Intelligence AI) [NON CHARGÉ]
```

---

## 📋 INVENTAIRE COMPLET DES LAUNCHAGENTS

### 1. Daily Sync - Rapport Quotidien (21h30)

**Fichier**: `~/Library/LaunchAgents/com.traininglogs.dailysync.plist`

**Identité**:
- Label: `com.traininglogs.dailysync`
- Catégorie: **REPORTING**
- Séquence: **10** (Premier dans la chaîne quotidienne)

**Configuration**:
```xml
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>21</integer>
    <key>Minute</key>
    <integer>30</integer>
</dict>
```

**Command**:
```bash
poetry run daily-sync --send-email --ai-analysis --auto-servo
```

**Fonction**:
- Détecte nouvelles activités Intervals.icu
- Génère analyses AI avec Claude
- Envoie rapport quotidien par email (Brevo)
- Tracks activités analysées (évite duplicatas)

**Outputs**:
- Email quotidien 21h30
- Logs: `~/Library/Logs/traininglogs-dailysync.log`
- Tracking: `~/data/tracking/analyzed_activities.json`

**Dépendances**:
- Brevo API (email)
- Claude API (analyses AI)
- Intervals.icu API (activités)

**Status**: ✅ **ACTIF** (chargé et fonctionnel)

---

### 2. Workout Adherence - Collecte Métriques (22h00)

**Fichier**: `~/Library/LaunchAgents/com.cyclisme.workout_adherence.plist`

**Identité**:
- Label: `com.cyclisme.workout_adherence`
- Catégorie: **MONITORING**
- Séquence: **20** (Après daily-sync)

**Configuration**:
```xml
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>22</integer>
    <key>Minute</key>
    <integer>0</integer>
</dict>
```

**Command**:
```bash
./scripts/monitoring/run_adherence_check.sh
→ poetry run python scripts/monitoring/check_workout_adherence.py
```

**Fonction**:
- Compare planning JSON vs activités Intervals.icu
- Détecte: COMPLETED, SKIPPED, REPLACED, CANCELLED
- Enregistre adherence quotidienne

**Outputs**:
- Dataset: `~/data/monitoring/workout_adherence.jsonl` (append)
- Logs: `~/data/monitoring/launchd.stdout.log`

**Dépendances**:
- Planning JSON (`logs/planning/SXXX_planning.json`)
- Intervals.icu API (activités)

**Status**: ✅ **ACTIF** (chargé et fonctionnel)

---

### 3. PID Evaluation - Intelligence AI (23h00)

**Fichier**: `scripts/monitoring/com.cyclisme.pid_evaluation.plist` (repo)

**Identité**:
- Label: `com.cyclisme.pid_evaluation`
- Catégorie: **ANALYSIS**
- Séquence: **30** (Après adherence)

**Configuration**:
```xml
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>23</integer>
    <key>Minute</key>
    <integer>0</integer>
</dict>
```

**Command**:
```bash
./scripts/monitoring/run_pid_evaluation.sh
→ poetry run pid-daily-evaluation --days-back 7
```

**Fonction**:
- Analyse 7 derniers jours (adherence, TSS, TSB, CV coupling)
- Génère learnings, patterns, adaptations
- Détecte opportunités tests FTP
- Crée recommandations TrainingIntelligence

**Outputs**:
- Intelligence: `~/data/intelligence.json`
- Logs: `~/data/monitoring/pid_evaluation.stdout.log`
- Journal: `~/data/monitoring/pid_evaluation.jsonl`

**Dépendances**:
- workout_adherence.jsonl (données 7j)
- Intervals.icu API (TSS, TSB, wellness)

**Status**: ❌ **NON CHARGÉ** (existe mais pas dans ~/Library/LaunchAgents)

**Note**: Fichier .plist existe dans repo mais n'est pas déployé

---

### 4. End-of-Week - Workflow Hebdomadaire (Dimanche 20h00)

**Fichier**: `~/Library/LaunchAgents/com.traininglogs.endofweek.plist`

**Identité**:
- Label: `com.traininglogs.endofweek`
- Catégorie: **WORKFLOW**
- Séquence: **00** (Hebdomadaire, pas quotidien)

**Configuration**:
```xml
<key>StartCalendarInterval</key>
<dict>
    <key>Weekday</key>
    <integer>0</integer>  <!-- Dimanche -->
    <key>Hour</key>
    <integer>20</integer>
    <key>Minute</key>
    <integer>0</integer>
</dict>
```

**Command**:
```bash
poetry run end-of-week --auto-calculate --provider claude_api --auto
```

**Fonction**:
- Analyse semaine écoulée (weekly-analysis)
- Génération planning semaine suivante (Claude API)
- Parsing + validation workouts
- Upload Intervals.icu
- Archive optionnelle

**Outputs**:
- Planning: `logs/planning/SXXX_planning.json`
- Analyses: `logs/weekly_reports/SXXX/`
- Logs: `~/Library/Logs/traininglogs-endofweek.log`

**Dépendances**:
- Claude API (génération workouts)
- Intervals.icu API (upload)
- WeekReferenceConfig (calcul week-ids)

**Status**: ✅ **ACTIF** (chargé et fonctionnel)

---

### 5. Project Cleaner - Nettoyage (24h)

**Fichier**: `~/Library/LaunchAgents/com.cyclisme.project-cleaner.plist`

**Identité**:
- Label: `com.cyclisme.project-cleaner`
- Catégorie: **MAINTENANCE**
- Séquence: **10**

**Configuration**:
```xml
<key>StartInterval</key>
<integer>86400</integer>  <!-- 24h -->
<key>RunAtLoad</key>
<true/>
```

**Command**:
```bash
cd ~/magma-cycling && poetry run project-clean
```

**Fonction**:
- Nettoyage fichiers temporaires
- Suppression anciens logs
- Maintenance projet

**Outputs**:
- Logs: `~/Library/Logs/project-cleaner.log`

**Status**: ✅ **ACTIF** (chargé et fonctionnel)

---

### 6. Sync Docs iCloud - Synchronisation (1h)

**Fichier**: `~/Library/LaunchAgents/com.cyclisme.sync-docs-icloud.plist`

**Identité**:
- Label: `com.cyclisme.sync-docs-icloud`
- Catégorie: **MAINTENANCE**
- Séquence: **20**

**Configuration**:
```xml
<key>StartInterval</key>
<integer>3600</integer>  <!-- 1h -->
<key>RunAtLoad</key>
<true/>
```

**Command**:
```bash
./scripts/maintenance/sync_docs_icloud.sh
```

**Fonction**:
- Rsync docs MOA vers iCloud Drive
- Options optimisées pour iCloud (--inplace, --no-perms)

**Outputs**:
- Logs: `~/Library/Logs/sync-docs-icloud.log`

**Status**: ✅ **ACTIF** (chargé et fonctionnel)

---

### 7. Rsync Sites - Docs Web (1h)

**Fichier**: `~/Library/LaunchAgents/com.user.sync.cyclisme.plist`

**Identité**:
- Label: `com.user.sync.cyclisme`
- Catégorie: **MAINTENANCE**
- Séquence: **30**

**Configuration**:
```xml
<key>StartInterval</key>
<integer>3600</integer>  <!-- 1h -->
<key>RunAtLoad</key>
<true/>
```

**Command**:
```bash
rsync -av --delete ~/magma-cycling/docs/_build/html/ ~/Sites/magma-cycling/
```

**Fonction**:
- Sync documentation Sphinx vers local web server

**Outputs**:
- Logs: `/tmp/com.user.sync.cyclisme.log`

**Status**: ✅ **ACTIF** (chargé et fonctionnel)

---

## 📊 SYNTHÈSE ARCHITECTURE ACTUELLE

### Par Catégorie

```
REPORTING (Email/Rapports)
  ├─ com.traininglogs.dailysync                [21:30 daily]  ✅ ACTIF

MONITORING (Collecte Données)
  ├─ com.cyclisme.workout_adherence            [22:00 daily]  ✅ ACTIF

ANALYSIS (Intelligence AI)
  ├─ com.cyclisme.pid_evaluation               [23:00 daily]  ❌ NON CHARGÉ

WORKFLOW (Processus Complets)
  ├─ com.traininglogs.endofweek                [Dim 20:00]    ✅ ACTIF

MAINTENANCE (Nettoyage/Sync)
  ├─ com.cyclisme.project-cleaner              [24h]          ✅ ACTIF
  ├─ com.cyclisme.sync-docs-icloud             [1h]           ✅ ACTIF
  ├─ com.user.sync.cyclisme                    [1h]           ✅ ACTIF
```

### Chronologie Quotidienne

```
20:00 (Dimanche) → end-of-week             (planning semaine)
21:30            → daily-sync               (email rapport)
22:00            → workout_adherence        (collecte adherence)
23:00            → [pid_evaluation]         (NON ACTIF!)
```

### Problèmes Identifiés

1. **❌ Naming incohérent**:
   - `com.traininglogs.*` (2 agents)
   - `com.cyclisme.*` (4 agents)
   - `com.user.sync.*` (1 agent)

2. **❌ Séquencement illisible**:
   - Impossible de comprendre l'ordre sans lire chaque .plist
   - Pas de convention numérotation

3. **❌ pid_evaluation non déployé**:
   - Fichier existe dans repo mais pas chargé
   - Intelligence AI quotidienne non fonctionnelle

4. **❌ Catégorisation absente**:
   - Mélange reporting/monitoring/maintenance sans structure

---

## 🎯 PROCHAINE ÉTAPE: MIGRATION

Voir `LAUNCHAGENTS_MIGRATION_PLAN.md` pour:
- Nouvelle convention de nommage
- Mapping ancien → nouveau
- Script de migration
- Validation post-migration

---

**Généré par**: Claude Code
**Contexte**: Sprint R9.F - Documentation workflow existant
