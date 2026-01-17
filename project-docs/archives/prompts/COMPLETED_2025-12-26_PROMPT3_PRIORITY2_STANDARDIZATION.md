# 📚 PROMPT CLAUDE CODE - STANDARDISATION DOCSTRINGS V2 (PRIORITY 2)

**Phase :** Prompt 3 - Priority 2 (Standardisation Suite)
**Objectif :** Standardiser 10 fichiers critiques P1-P2 avec docstrings v2 + tags Gartner TIME
**Durée estimée :** 2-3 heures
**Priorité :** 🎯 HIGH (après ou parallèle Prompt 2 Phase 1)

---

## 🎯 MISSION

Standardiser 10 fichiers critiques (Priority 1-2) en ajoutant :

1. **Tags Gartner TIME** complets (I/T/M/E + metadata)
2. **Docstrings v2** avec section Examples (minimum 2 code blocks)
3. **Validation** automatique via script
4. **Tests** aucune régression

**Cibles :** Fichiers Intervals.icu integration (4) + AI providers (3) + Analytics (3)

---

## 📁 CONTEXTE PROJET

### **État Actuel**
```
Location: ~/cyclisme-training-logs/
Gartner tags: 7/45 (15.5%) ← Priority 1 complété
Tests: 273/273 passing
Git: Clean (commit 5dc8fb4)
```

### **Objectif Priority 2**
```
Fichiers à standardiser: 10 (P1-P2)
Coverage cible: 17/45 (37.8%)
Distribution:
  - Intervals.icu integration: 4 fichiers
  - AI providers: 3 fichiers
  - Analytics: 3 fichiers
```

### **Templates Disponibles**
```
Documentation: DOCSTRING_TEMPLATE_V2_GARTNER.md
Validation: scripts/validate_gartner_tags.py
Référence: 7 fichiers déjà standardisés (Priority 1)
```

---

## 📋 FICHIERS CIBLES (10 FICHIERS)

### **Groupe 1 : Intervals.icu Integration (4 fichiers P1-P2)**

#### **1. `sync_intervals.py` (I/P1)**

**Classification :**
```
GARTNER_TIME: I
STATUS: Production
PRIORITY: P1
```

**Raison I (Invest) :**
- Intégration API Intervals.icu centrale
- Synchronisation activités quotidienne
- Fetch métriques forme (CTL/ATL/TSB)
- Utilisé par workflow_coach.py

**Docstring v2 à ajouter :**

```python
"""
Intervals.icu API integration for activity sync and metrics fetching.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Intègre l'API Intervals.icu pour synchronisation activités, fetch métriques
forme (CTL/ATL/TSB), et wellness data. Utilisé quotidiennement par le
workflow principal.

Examples:
    Sync recent activities::

        from cyclisme_training_logs.sync_intervals import IntervalsAPI

        # Initialiser API
        api = IntervalsAPI()

        # Sync dernières 7 jours
        activities = api.sync_recent_activities(days=7)

        for activity in activities:
            print(f"{activity['start_date']}: {activity['name']}")

    Fetch fitness metrics::

        # Récupérer métriques forme aujourd'hui
        wellness = api.get_wellness_today()

        print(f"CTL: {wellness['ctl']}")
        print(f"ATL: {wellness['atl']}")
        print(f"TSB: {wellness['tsb']}")

    Get specific activity::

        # Fetch activité par ID
        activity = api.get_activity('i123456')

        print(f"TSS: {activity['training_load']}")
        print(f"IF: {activity['if']:.2f}")
        print(f"NP: {activity['normalized_power']}W")

Author: Stéphane Jouve
Created: 2024-09-XX
Updated: 2025-12-26 (Standardization Prompt 3 Priority 2)
"""
```

---

#### **2. `upload_workouts.py` (I/P1)**

**Classification :**
```
GARTNER_TIME: I
STATUS: Production
PRIORITY: P1
```

**Raison I (Invest) :**
- Upload workouts .zwo vers Intervals.icu
- Planification entraînement centralisée
- Conversion formats automatique
- Utilisé régulièrement

**Docstring v2 à ajouter :**

```python
"""
Upload Zwift workout files (.zwo) to Intervals.icu calendar.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Upload fichiers workouts Zwift (.zwo) vers calendrier Intervals.icu.
Convertit format Zwift en format Intervals.icu et planifie séances
automatiquement.

Examples:
    Upload single workout::

        from cyclisme_training_logs.upload_workouts import upload_workout
        from pathlib import Path

        # Upload fichier .zwo
        workout_file = Path("S073-01-INT-SweetSpot-V001.zwo")

        result = upload_workout(
            workout_file,
            target_date="2025-01-06"
        )

        if result.success:
            print(f"Uploaded: {result.workout_id}")

    Batch upload week::

        from cyclisme_training_logs.upload_workouts import upload_week

        # Upload semaine complète
        week_dir = Path("workouts/S073-Semaine73")

        results = upload_week(
            week_dir,
            start_date="2025-01-06"
        )

        print(f"Uploaded {len(results)} workouts")

    CLI usage::

        # Command-line upload
        poetry run upload-workouts --file S073-01-INT-SweetSpot-V001.zwo --date 2025-01-06

        # Upload entire week
        poetry run upload-workouts --week S073 --start-date 2025-01-06

Author: Stéphane Jouve
Created: 2024-10-XX
Updated: 2025-12-26 (Standardization Prompt 3 Priority 2)
"""
```

---

#### **3. `planned_sessions_checker.py` (I/P2)**

**Classification :**
```
GARTNER_TIME: I
STATUS: Production
PRIORITY: P2
```

**Raison I (Invest) :**
- Validation workouts planifiés vs exécutés
- Détection écarts planning
- Reporting compliance hebdomadaire
- Utilisé analyses weekly

**Docstring v2 à ajouter :**

```python
"""
Validate planned workouts vs executed activities compliance.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P2
DOCSTRING: v2

Vérifie conformité entre workouts planifiés (Intervals.icu) et activités
réalisées. Détecte écarts, sessions manquées, et génère rapports de
compliance hebdomadaire.

Examples:
    Check weekly compliance::

        from cyclisme_training_logs.planned_sessions_checker import check_week

        # Vérifier semaine S073
        compliance = check_week(
            week="S073",
            start_date="2025-01-06"
        )

        print(f"Completed: {compliance['completed']}/7")
        print(f"Missed: {compliance['missed']}")
        print(f"Compliance: {compliance['rate']:.1f}%")

    Detailed session comparison::

        from cyclisme_training_logs.planned_sessions_checker import compare_sessions

        # Comparer séance planifiée vs exécutée
        comparison = compare_sessions(
            planned_id="workout_123",
            activity_id="i654321"
        )

        if comparison['tss_delta'] > 10:
            print("Warning: TSS mismatch")

    CLI usage::

        # Check current week
        poetry run check-planned --week current

        # Generate weekly report
        poetry run check-planned --week S073 --report

Author: Stéphane Jouve
Created: 2024-11-XX
Updated: 2025-12-26 (Standardization Prompt 3 Priority 2)
"""
```

---

#### **4. `intervals_format_validator.py` (I/P2)**

**Classification :**
```
GARTNER_TIME: I
STATUS: Production
PRIORITY: P2
```

**Raison I (Invest) :**
- Validation format workouts Intervals.icu
- Conversion syntax checking
- Prévention erreurs upload
- Utilisé pre-upload validation

**Docstring v2 à ajouter :**

```python
"""
Validate Intervals.icu workout format syntax and structure.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P2
DOCSTRING: v2

Valide syntaxe et structure workouts format Intervals.icu avant upload.
Vérifie cohérence durées, pourcentages FTP, format répétitions, et
génère warnings si problèmes détectés.

Examples:
    Validate workout syntax::

        from cyclisme_training_logs.intervals_format_validator import validate_workout

        workout_text = '''
        Warmup
        - 10m 50-75% 85rpm

        Main set 4x
        - 8m 90% 90rpm
        - 3m 65% 85rpm
        '''

        result = validate_workout(workout_text)

        if result.valid:
            print("✅ Valid Intervals.icu format")
        else:
            print(f"❌ Errors: {result.errors}")

    Check file before upload::

        from pathlib import Path

        # Valider fichier .txt avant conversion
        workout_file = Path("S073-01-workout.txt")

        result = validate_workout(workout_file.read_text())

        # Afficher warnings
        for warning in result.warnings:
            print(f"⚠️  {warning}")

    CLI validation::

        # Validate all workouts in directory
        poetry run validate-workouts --dir workouts/S073/

        # Validate single file
        poetry run validate-workouts --file S073-01-workout.txt

Author: Stéphane Jouve
Created: 2024-11-XX
Updated: 2025-12-26 (Standardization Prompt 3 Priority 2)
"""
```

---

### **Groupe 2 : AI Providers (3 fichiers P2)**

#### **5. `ai_providers/__init__.py` (I/P2)**

**Classification :**
```
GARTNER_TIME: I
STATUS: Production
PRIORITY: P2
```

**Docstring v2 à ajouter :**

```python
"""
AI providers factory for multi-provider analysis support.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P2
DOCSTRING: v2

Factory pattern pour support multi-providers IA (Claude, Mistral, OpenAI,
Gemini, Ollama). Fournit interface unifiée pour analyses workouts avec
fallback automatique entre providers.

Examples:
    Get AI provider::

        from cyclisme_training_logs.ai_providers import get_provider

        # Provider par défaut (Claude)
        provider = get_provider()

        # Provider spécifique
        mistral = get_provider('mistral')
        openai = get_provider('openai')

    Analyze with fallback::

        # Essayer Claude, fallback Mistral
        providers = ['claude', 'mistral']

        for provider_name in providers:
            try:
                provider = get_provider(provider_name)
                analysis = provider.analyze(workout_data)
                break
            except Exception as e:
                print(f"{provider_name} failed: {e}")
                continue

    List available providers::

        from cyclisme_training_logs.ai_providers import list_providers

        providers = list_providers()
        print(f"Available: {', '.join(providers)}")

Author: Claude Code
Created: 2024-11-XX
Updated: 2025-12-26 (Standardization Prompt 3 Priority 2)
"""
```

---

#### **6. `ai_providers/mistral_api.py` (I/P2)**

**Classification :**
```
GARTNER_TIME: I
STATUS: Production
PRIORITY: P2
```

**Docstring v2 à ajouter :**

```python
"""
Mistral AI provider implementation for workout analysis.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P2
DOCSTRING: v2

Implémentation provider Mistral AI pour analyses workouts. Utilise modèle
mistral-large avec support streaming et retry automatique. Fallback
principal après Claude.

Examples:
    Basic analysis::

        from cyclisme_training_logs.ai_providers.mistral_api import MistralProvider

        provider = MistralProvider()

        analysis = provider.analyze(
            prompt="Analyser séance S073-01",
            workout_data={"tss": 45, "if": 1.2}
        )

        print(analysis)

    Streaming response::

        # Analyse avec streaming
        for chunk in provider.analyze_stream(prompt, workout_data):
            print(chunk, end='', flush=True)

    Error handling::

        from cyclisme_training_logs.ai_providers.mistral_api import MistralProvider

        provider = MistralProvider(max_retries=3)

        try:
            analysis = provider.analyze(prompt, data)
        except Exception as e:
            print(f"Mistral failed: {e}")
            # Fallback to another provider

Author: Claude Code
Created: 2024-11-XX
Updated: 2025-12-26 (Standardization Prompt 3 Priority 2)
"""
```

---

#### **7. `ai_providers/claude_api.py` (I/P2)**

**Classification :**
```
GARTNER_TIME: I
STATUS: Production
PRIORITY: P2
```

**Docstring v2 à ajouter :**

```python
"""
Claude AI provider implementation (Anthropic API).

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P2
DOCSTRING: v2

Implémentation provider Claude AI (Anthropic) pour analyses workouts.
Utilise claude-sonnet-4-20250514 comme provider principal avec support
thinking blocks et artifacts.

Examples:
    Standard analysis::

        from cyclisme_training_logs.ai_providers.claude_api import ClaudeProvider

        provider = ClaudeProvider()

        analysis = provider.analyze(
            prompt="Analyser découplage cardiovasculaire",
            workout_data={"hr_avg": 120, "power_avg": 180}
        )

    With thinking enabled::

        # Activer extended thinking
        provider = ClaudeProvider(enable_thinking=True)

        result = provider.analyze(prompt, data)

        # Accéder thinking blocks
        if result.thinking:
            print("Reasoning:", result.thinking)

    Batch analysis::

        # Analyser plusieurs workouts
        workouts = [workout1, workout2, workout3]

        analyses = provider.batch_analyze(
            prompts=[...],
            workouts_data=workouts
        )

Author: Claude Code
Created: 2024-11-XX
Updated: 2025-12-26 (Standardization Prompt 3 Priority 2)
"""
```

---

### **Groupe 3 : Analytics (3 fichiers P2-P3)**

#### **8. `rest_and_cancellations.py` (I/P2)**

**Classification :**
```
GARTNER_TIME: I
STATUS: Production
PRIORITY: P2
```

**Raison I (Invest) :**
- Tracking repos et séances annulées
- Impact métriques forme (TSB/ATL)
- Documentation raisons cancellation
- Utilisé analyses weekly

**Docstring v2 à ajouter :**

```python
"""
Track rest days and canceled sessions with impact analysis.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P2
DOCSTRING: v2

Suivi jours de repos et séances annulées avec analyse impact sur métriques
forme (CTL/ATL/TSB). Documentation raisons cancellation et recommandations
adaptations planning.

Examples:
    Log rest day::

        from cyclisme_training_logs.rest_and_cancellations import log_rest

        # Logger repos programmé
        log_rest(
            date="2025-01-12",
            reason="Recovery week",
            planned=True
        )

    Log canceled session::

        # Logger séance annulée
        log_cancellation(
            date="2025-01-10",
            session_id="S073-04",
            reason="Fatigue excessive",
            reschedule=True
        )

    Analyze impact on metrics::

        # Calculer impact sur TSB
        impact = analyze_rest_impact(
            rest_dates=["2025-01-12", "2025-01-13"],
            current_ctl=65,
            current_atl=58
        )

        print(f"TSB après repos: {impact['tsb_after']}")

Author: Stéphane Jouve
Created: 2024-10-XX
Updated: 2025-12-26 (Standardization Prompt 3 Priority 2)
"""
```

---

#### **9. `workflow_state.py` (I/P1)**

**Classification :**
```
GARTNER_TIME: I
STATUS: Production
PRIORITY: P1
```

**Raison I (Invest) :**
- État workflow persistant (similaire manage_workflow_state.py)
- Tracking étapes complétées
- Prévention duplicates
- Utilisé par workflow_coach.py

**Docstring v2 à ajouter :**

```python
"""
Workflow state management and persistence.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Gestion état workflow persistant entre exécutions. Tracking étapes
complétées, prévention duplicates, et validation cohérence pipeline
d'analyse quotidien.

Examples:
    Load workflow state::

        from cyclisme_training_logs.workflow_state import WorkflowState

        # Charger état
        state = WorkflowState.load()

        # Vérifier étapes complétées
        if state.is_completed('fetch_activity'):
            print("Activity already fetched")

    Update state::

        # Marquer étape complétée
        state.mark_completed(
            step='generate_analysis',
            metadata={'activity_id': 'i123456'}
        )

        # Persister
        state.save()

    Reset for new day::

        # Reset état pour nouveau jour
        state.reset()
        state.save()

Author: Stéphane Jouve
Created: 2024-09-XX
Updated: 2025-12-26 (Standardization Prompt 3 Priority 2)
"""
```

---

#### **10. `stats.py` (T/P3)**

**Classification :**
```
GARTNER_TIME: T
STATUS: Production (Legacy)
PRIORITY: P3
REPLACEMENT: analyzers/weekly_analyzer.py (Planned Phase 2)
```

**Raison T (Tolerate) :**
- Fonctionnel mais legacy
- Sera remplacé par weekly_analyzer.py (Phase 2)
- Utilisé temporairement
- Maintenance minimale

**Docstring v2 à ajouter :**

```python
"""
Legacy statistics computation (use analyzers/weekly_analyzer.py for new code).

GARTNER_TIME: T
STATUS: Production (Legacy)
LAST_REVIEW: 2025-12-26
PRIORITY: P3
REPLACEMENT: analyzers/weekly_analyzer.py (Planned Phase 2)
DEPRECATION_PLAN: Replace after Prompt 2 Phase 2 (weekly analysis system)
DOCSTRING: v2

⚠️  LEGACY - Calculs statistiques basiques workouts. Utilisé temporairement
en attendant weekly_analyzer.py (Prompt 2 Phase 2). Pour nouveau code,
utiliser analyzers/weekly_analyzer.py.

Examples:
    Basic stats (legacy)::

        from cyclisme_training_logs.stats import compute_weekly_stats

        # ⚠️  Legacy - à remplacer
        stats = compute_weekly_stats(
            week="S073",
            activities=[...]
        )

        print(f"Total TSS: {stats['total_tss']}")

    Migration to new system::

        # ✅ NOUVEAU (Phase 2) - À utiliser pour nouveau code
        from cyclisme_training_logs.analyzers.weekly_analyzer import WeeklyAnalyzer

        analyzer = WeeklyAnalyzer(week="S073")
        analysis = analyzer.analyze()

        # 6 reports générés automatiquement
        print(analysis['reports'])

    CLI (legacy)::

        # ⚠️  Legacy command
        poetry run stats --week S073

        # ✅ NOUVEAU (Phase 2)
        poetry run weekly-analysis --week S073

Author: Stéphane Jouve
Created: 2024-08-XX
Updated: 2025-12-26 (Standardization Prompt 3 Priority 2 - Marked as Legacy)
"""
```

---

## ✅ CRITÈRES DE SUCCÈS

### **Fichiers Modifiés (10)**
- [ ] `sync_intervals.py` - Docstring v2 + tag I/P1
- [ ] `upload_workouts.py` - Docstring v2 + tag I/P1
- [ ] `planned_sessions_checker.py` - Docstring v2 + tag I/P2
- [ ] `intervals_format_validator.py` - Docstring v2 + tag I/P2
- [ ] `ai_providers/__init__.py` - Docstring v2 + tag I/P2
- [ ] `ai_providers/mistral_api.py` - Docstring v2 + tag I/P2
- [ ] `ai_providers/claude_api.py` - Docstring v2 + tag I/P2
- [ ] `rest_and_cancellations.py` - Docstring v2 + tag I/P2
- [ ] `workflow_state.py` - Docstring v2 + tag I/P1
- [ ] `stats.py` - Docstring v2 + tag T/P3 (Legacy)

### **Validation**
- [ ] Tous tests passent : `poetry run pytest` (273 tests ✅)
- [ ] Validation tags : `poetry run python scripts/validate_gartner_tags.py`
- [ ] 10/10 fichiers valid ✅
- [ ] HTML report généré : `validation_report_priority2.html`

### **Qualité Docstrings**
- [ ] Tous fichiers : Minimum 2 Examples avec code exécutable
- [ ] Imports explicites dans Examples
- [ ] Code Examples réalistes et complets
- [ ] Comments si nécessaire clarté
- [ ] Tags Gartner TIME corrects (format exact)

### **Git**
- [ ] Commit message descriptif
- [ ] Push to origin/main
- [ ] Tag version `v2.0.2-standardization-priority2`

---

## 📊 RÉSULTATS ATTENDUS

### **Avant Prompt 3 Priority 2**
```
Docstring v2: 7/45 (15.5%)
Gartner I: 5 files (11%)
Gartner T: 0 files (0%)
Priority P1: 4/5 (80%)
Priority P2: 0/10 (0%)
```

### **Après Prompt 3 Priority 2**
```
Docstring v2: 17/45 (37.8%) ← +10 fichiers
Gartner I: 14 files (31%) ← +9 fichiers
Gartner T: 1 file (2%) ← stats.py
Priority P1: 6/6 (100%) ✅
Priority P2: 8/10 (80%) ✅
Priority P3: 1/5 (20%)
```

### **Distribution Finale**
```
🟢 I (Invest):   14 files (31%) ← Stratégiques
🟡 T (Tolerate):  1 file  (2%)  ← stats.py legacy
🔵 M (Migrate):   2 files (4%)  ← Unchanged (Phase 1)
⚠️  None:        28 files (62%) ← À standardiser
```

---

## 🎯 RÈGLES D'EXÉCUTION

### **Template Gartner TIME Tags**

**Pour fichiers I (Invest) :**
```python
"""
[One-line description]

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1|P2
DOCSTRING: v2

[French description 2-3 phrases]

Examples:
    [Minimum 2 code blocks exécutables]

Author: [Nom]
Created: YYYY-MM-XX
Updated: 2025-12-26 (Standardization Prompt 3 Priority 2)
"""
```

**Pour fichiers T (Tolerate) - stats.py :**
```python
"""
[One-line description]

GARTNER_TIME: T
STATUS: Production (Legacy)
LAST_REVIEW: 2025-12-26
PRIORITY: P3
REPLACEMENT: analyzers/weekly_analyzer.py (Planned Phase 2)
DEPRECATION_PLAN: Replace after Prompt 2 Phase 2
DOCSTRING: v2

⚠️  LEGACY - [Description avec warning]
[Instructions migration vers nouveau système]

Examples:
    [Minimum 2 code blocks : legacy + nouveau système]

Author: [Nom]
Created: YYYY-MM-XX
Updated: 2025-12-26 (Standardization Prompt 3 Priority 2 - Marked as Legacy)
"""
```

### **Règles Examples Section**

**Obligatoire :**
1. Minimum 2 code blocks exécutables
2. Imports explicites (`from cyclisme_training_logs.module import Class`)
3. Code complet (pas de `...` ou placeholders)
4. Cas d'usage réalistes
5. Comments si aide compréhension

**Bon exemple :**
```python
Examples:
    Basic usage::

        from cyclisme_training_logs.sync_intervals import IntervalsAPI

        api = IntervalsAPI()
        activities = api.sync_recent_activities(days=7)

        for activity in activities:
            print(f"{activity['start_date']}: {activity['name']}")

    Advanced with error handling::

        from cyclisme_training_logs.sync_intervals import IntervalsAPI

        api = IntervalsAPI()

        try:
            wellness = api.get_wellness_today()
            print(f"CTL: {wellness['ctl']}")
        except Exception as e:
            print(f"Error: {e}")
```

**Mauvais exemple :**
```python
Examples:
    # ❌ Pas d'import explicite
    api = IntervalsAPI()

    # ❌ Code incomplet
    activities = api.sync_recent_activities(...)
```

---

## 🚀 ORDRE D'EXÉCUTION

### **Recommandé : Par groupe thématique**

**1. Intervals.icu Integration (30min)**
- sync_intervals.py
- upload_workouts.py
- planned_sessions_checker.py
- intervals_format_validator.py

**2. AI Providers (20min)**
- ai_providers/__init__.py
- ai_providers/mistral_api.py
- ai_providers/claude_api.py

**3. Analytics (20min)**
- rest_and_cancellations.py
- workflow_state.py
- stats.py (Legacy T)

**4. Validation (30min)**
- Run pytest
- Run validate_gartner_tags.py
- Generate HTML report
- Review errors/warnings

**5. Git Commit (10min)**
- Commit avec message descriptif
- Push to origin/main
- Tag version

---

## 📝 NOTES IMPORTANTES

### **Préserver Code Existant**

**RÈGLE CRITIQUE :**
- ✅ AJOUTER docstring v2 au début fichier
- ✅ MODIFIER première ligne docstring existante si nécessaire
- ❌ NE PAS modifier code fonctionnel
- ❌ NE PAS modifier imports
- ❌ NE PAS modifier signatures fonctions

**Exemple modification :**
```python
# AVANT
"""Sync activities from Intervals.icu"""

import requests
from pathlib import Path

class IntervalsAPI:
    # ... code existant ...

# APRÈS
"""
Intervals.icu API integration for activity sync and metrics fetching.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Intègre l'API Intervals.icu pour synchronisation activités...

Examples:
    Basic sync::
        # ... examples ...

Author: Stéphane Jouve
Created: 2024-09-XX
Updated: 2025-12-26 (Standardization Prompt 3 Priority 2)
"""

import requests  # ← INCHANGÉ
from pathlib import Path

class IntervalsAPI:  # ← INCHANGÉ
    # ... code existant INCHANGÉ ...
```

### **Validation Continue**

**Après chaque fichier modifié :**
```bash
# Tester le fichier spécifique
poetry run pytest tests/test_[nom_module].py -v

# Valider tags Gartner
poetry run python scripts/validate_gartner_tags.py --file cyclisme_training_logs/[nom_fichier].py
```

**Après tous fichiers :**
```bash
# Tests complets
poetry run pytest

# Validation complète
poetry run python scripts/validate_gartner_tags.py

# HTML report
poetry run python scripts/validate_gartner_tags.py --html validation_report_priority2.html
```

---

## 🎯 COMMIT MESSAGE TEMPLATE

```
feat: standardize 10 critical files with Gartner TIME tags (Priority 2)

Add docstrings v2 and Gartner TIME classification to:

Intervals.icu Integration (4 files):
- sync_intervals.py (I/P1)
- upload_workouts.py (I/P1)
- planned_sessions_checker.py (I/P2)
- intervals_format_validator.py (I/P2)

AI Providers (3 files):
- ai_providers/__init__.py (I/P2)
- ai_providers/mistral_api.py (I/P2)
- ai_providers/claude_api.py (I/P2)

Analytics (3 files):
- rest_and_cancellations.py (I/P2)
- workflow_state.py (I/P1)
- stats.py (T/P3 - marked as legacy)

All docstrings include:
- Complete Gartner TIME tags (I/T + metadata)
- Minimum 2 executable Examples with explicit imports
- French descriptions
- Author and update timestamps

Validation:
- 10/10 files passing Gartner validation
- 273/273 tests passing (no regression)
- Coverage v2: 15.5% → 37.8% (+22 points)

Distribution:
- Priority P1: 6/6 (100%)
- Priority P2: 8/10 (80%)
- Gartner I: 14 files (31%)
- Gartner T: 1 file (2% - stats.py legacy)
```

---

## 📈 PROGRESSION TRACKING

### **Coverage Evolution**
```
Priority 1 (6 files):
  AVANT: 4/6 (67%)
  APRÈS: 6/6 (100%) ✅

Priority 2 (10 files):
  AVANT: 0/10 (0%)
  APRÈS: 8/10 (80%) ✅

Overall v2 Coverage:
  AVANT: 7/45 (15.5%)
  APRÈS: 17/45 (37.8%) ✅

Gartner Distribution:
  I (Invest): 5 → 14 (+9 files)
  T (Tolerate): 0 → 1 (stats.py)
  M (Migrate): 2 (unchanged)
  None: 38 → 28 (-10 files)
```

### **Prochaines Étapes**

**Après validation Priority 2 :**
1. **Prompt 2 Phase 2** : Weekly analysis system (6 reports)
2. **Prompt 3 Priority 3** : 10-15 fichiers additionnels
3. **Prompt 3 Priority 4** : Tests standardization

**Objectif Final :**
- Coverage v2 : 100% (45/45 fichiers)
- Gartner I : 80% (36 fichiers)
- Gartner T/E : <5% (2 fichiers)
- Gartner M : 0% (dette résolue)

---

## 🎯 RÉSUMÉ MISSION

**Tu dois :**

1. ✅ Modifier 10 fichiers avec docstrings v2
2. ✅ Ajouter tags Gartner TIME corrects (I ou T)
3. ✅ Minimum 2 Examples exécutables par fichier
4. ✅ Valider 10/10 fichiers passing
5. ✅ Tests 273/273 passing (aucune régression)
6. ✅ HTML report généré
7. ✅ Git commit + push + tag

**Temps estimé :** 2-3 heures

**Résultat attendu :**
- 10 fichiers P1-P2 standardisés ✅
- Coverage v2 : 37.8% (+22 points) ✅
- Priority P1 : 100% complété ✅
- Priority P2 : 80% complété ✅

---

**Prêt à exécuter ?** 🚀
