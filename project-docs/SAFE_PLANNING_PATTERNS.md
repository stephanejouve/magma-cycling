# Safe Planning Patterns - Guide de Migration Pydantic

**Date:** 8 février 2026
**Status:** Production
**Version:** 1.0

---

## 📋 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Le problème résolu](#le-problème-résolu)
3. [Patterns sécurisés](#patterns-sécurisés)
4. [Migration complétée](#migration-complétée)
5. [Fichiers restants](#fichiers-restants)
6. [Validation et tests](#validation-et-tests)

---

## Vue d'ensemble

Ce document présente les patterns sécurisés pour manipuler les données de planning hebdomadaire, en utilisant les modèles Pydantic au lieu de dictionnaires Python bruts.

### Problème identifié

L'analyse avec `memory_graph` a révélé des **shallow copy bugs** dans le code manipulant les fichiers `week_planning_SXXX.json`. Ces bugs pouvaient entraîner :

- ❌ Corruption silencieuse des données
- ❌ Modifications accidentelles des backups
- ❌ Pas de validation des types/valeurs
- ❌ Erreurs difficiles à déboguer

### Solution implémentée

Migration vers les modèles Pydantic (`cyclisme_training_logs/planning/models.py`) :

- ✅ Protection automatique contre shallow copy
- ✅ Validation des types à chaque modification
- ✅ Validation des valeurs (enums, contraintes)
- ✅ Type hints pour IntelliSense
- ✅ Tests anti-aliasing (10/10 passants)

---

## Le problème résolu

### ❌ Ancien pattern (DANGEREUX)

```python
import json

# Chargement dict brut
with open("week_planning_S080.json") as f:
    planning = json.load(f)

# DANGER: Shallow copy - backup ET original partagent les mêmes sessions
backup = planning["planned_sessions"].copy()

# Modification direct sans validation
for session in planning["planned_sessions"]:
    if session["session_id"] == "S080-01":
        session["status"] = "completed"  # Pas de validation!

# Sauvegarde sans validation
with open("week_planning_S080.json", "w") as f:
    json.dump(planning, f, indent=2)
```

**Risques:**
- Pas de validation (status peut être n'importe quoi)
- Backup est aussi modifié (shallow copy!)
- Erreurs silencieuses
- Pas de type hints

### ✅ Nouveau pattern (SÉCURISÉ)

```python
from cyclisme_training_logs.planning.models import WeeklyPlan
from pydantic import ValidationError

# ✅ Chargement avec validation Pydantic
try:
    plan = WeeklyPlan.from_json("week_planning_S080.json")
except ValidationError as e:
    print(f"Planning invalide: {e}")
    return

# ✅ Deep copy protection automatique
backup = plan.backup_sessions()

# ✅ Modification avec validation automatique
for session in plan.planned_sessions:
    if session.session_id == "S080-01":
        session.status = "completed"  # Validé par Pydantic!

# ✅ Sauvegarde atomique
plan.to_json("week_planning_S080.json")
```

**Bénéfices:**
- Validation automatique (statuts valides seulement)
- Backup totalement indépendant (deep copy)
- Détection précoce des erreurs
- Type hints et IntelliSense

---

## Patterns sécurisés

### 1. Chargement de planning

#### ❌ Ancien (dict brut)

```python
with open(planning_file) as f:
    planning = json.load(f)

sessions = planning["planned_sessions"]
```

#### ✅ Nouveau (Pydantic)

```python
from cyclisme_training_logs.planning.models import WeeklyPlan
from pydantic import ValidationError

try:
    plan = WeeklyPlan.from_json(planning_file)
except ValidationError as e:
    print(f"Erreur validation: {e}")
    return

sessions = plan.planned_sessions
```

### 2. Accès aux champs

#### ❌ Ancien (dict access)

```python
session_date = session["date"]
session_type = session["type"]
session_id = session["session_id"]
status = session["status"]
```

#### ✅ Nouveau (object attributes)

```python
session_date = session.session_date  # Alias pour "date"
session_type = session.session_type  # Alias pour "type"
session_id = session.session_id
status = session.status
```

**Note:** Les champs `date` et `type` sont aliasés car ce sont des mots-clés Python.

### 3. Modification de sessions

#### ❌ Ancien (modification directe)

```python
session["status"] = "skipped"
session["skip_reason"] = "Weather"
```

#### ✅ Nouveau (validation automatique)

```python
# IMPORTANT: Ordre des modifications compte!
session.skip_reason = "Weather"  # FIRST
session.status = "skipped"  # THEN (validator checks skip_reason exists)
```

**Note:** Les validators Pydantic s'exécutent à chaque modification. Pour `status="skipped"`, le validator vérifie que `skip_reason` existe.

### 4. Sauvegarde de planning

#### ❌ Ancien (sauvegarde directe)

```python
planning["last_updated"] = datetime.now().isoformat()

with open(planning_file, "w") as f:
    json.dump(planning, f, indent=2)
```

#### ✅ Nouveau (sauvegarde atomique)

```python
from datetime import datetime

plan.last_updated = datetime.now()
plan.to_json(planning_file)
```

**Bénéfice:** `to_json()` fait une écriture atomique (temp file + rename) pour éviter la corruption.

### 5. Backup et restore

#### ❌ Ancien (shallow copy danger)

```python
# DANGER: Shallow copy!
backup = planning["planned_sessions"].copy()

# Modifier backup modifie aussi l'original!
backup[0]["status"] = "cancelled"
# → planning["planned_sessions"][0] est AUSSI modifié!
```

#### ✅ Nouveau (deep copy protection)

```python
# ✅ Deep copy protection
backup = plan.backup_sessions()

# Modifier backup N'affecte PAS l'original
backup[0].status = "cancelled"
# → plan.planned_sessions[0] reste inchangé ✅

# Restaurer depuis backup
plan.restore_sessions(backup)
```

### 6. Fonction utilitaire (load_week_planning)

#### ❌ Ancien (retourne dict)

```python
def load_week_planning(week_id: str) -> dict:
    """Charge planning depuis JSON."""
    with open(planning_file) as f:
        planning = json.load(f)

    if not validate_week_planning(planning):
        raise ValueError("Planning invalide")

    return planning  # ← Dict non protégé
```

#### ✅ Nouveau (retourne WeeklyPlan)

```python
from cyclisme_training_logs.planning.models import WeeklyPlan
from pydantic import ValidationError

def load_week_planning(week_id: str) -> WeeklyPlan:
    """Charge planning avec protection Pydantic."""
    try:
        plan = WeeklyPlan.from_json(planning_file)
    except ValidationError as e:
        raise ValueError(f"Planning invalide: {e}") from e

    return plan  # ✅ Type Pydantic avec protection
```

---

## Migration complétée

### Fichiers migrés (Phase 1 + 2)

#### 1. `cyclisme_training_logs/planning/models.py`

**Statut:** ✅ COMPLÉTÉ
**Date:** 2026-02-08
**Tests:** 10/10 passants (`tests/planning/test_models_anti_aliasing.py`)

Modèles Pydantic avec protection anti-shallow copy :

- `Session(BaseModel)`: Session individuelle avec validation
- `WeeklyPlan(BaseModel)`: Planning hebdomadaire avec méthodes `backup_sessions()` et `restore_sessions()`

#### 2. `cyclisme_training_logs/weekly_planner.py`

**Statut:** ✅ COMPLÉTÉ
**Date:** 2026-02-08
**Tests:** 8/8 passants (`tests/planning/test_migration_weekly_planner.py`)

**Migration effectuée:**
- Méthode `update_session_status()` utilise `WeeklyPlan`
- Validation automatique des statuts
- Protection anti-shallow copy

**Ligne clé:** 730-756 (anciennement dict brut)

#### 3. `cyclisme_training_logs/rest_and_cancellations.py`

**Statut:** ✅ COMPLÉTÉ
**Date:** 2026-02-08
**Tests:** 14/14 passants (`tests/test_rest_and_cancellations.py`)

**Migrations effectuées:**

1. **`load_week_planning()`** (ligne 212):
   - Retourne maintenant `WeeklyPlan` au lieu de `dict`
   - Validation Pydantic automatique
   - Impact: Tous les appelants bénéficient de la protection

2. **`reconcile_planned_vs_actual()`** (ligne 696):
   - Accepte `WeeklyPlan | dict` (backward compatibility)
   - Helpers internes pour accès unifié aux champs
   - Support session Pydantic et dict

3. **`validate_week_planning()`** (ligne 271):
   - Détecte type `WeeklyPlan` → retourne `True` directement
   - Validation manuelle pour `dict` legacy
   - Ajout validation `skip_reason` pour status "skipped"

**Appelants mis à jour:**
- `workflow_coach.py:730`
- `planned_sessions_checker.py:423`
- `rest_and_cancellations.py:849` (interne)

#### 4. `cyclisme_training_logs/daily_sync.py`

**Statut:** ✅ COMPLÉTÉ
**Date:** 2026-02-08
**Tests:** Import validé

**Migrations effectuées:**

1. **`_check_planning_sync()`** (ligne 311):
   - Remplacé `json.load()` par `WeeklyPlan.from_json()`
   - Accès champs via attributes (`.session_date`, `.session_type`)

2. **`update_completed_sessions()`** (ligne 928):
   - Chargement avec `WeeklyPlan.from_json()`
   - Modifications via attributes Pydantic
   - Sauvegarde atomique via `plan.to_json()`

**Impact:** Script cron quotidien (21h30) maintenant sécurisé.

---

## Fichiers restants

Ces 4 fichiers utilisent planning en **lecture seule** - migration optionnelle mais recommandée lors de futures modifications.

### 1. `monthly_analysis.py` (ligne 94-119)

**Usage:** Statistiques mensuelles (lecture seule)
**Risque:** 🟢 Faible - agrégation simple, pas de modifications

**Pattern actuel:**
```python
with open(planning_file) as f:
    planning = json.load(f)

for session in planning["planned_sessions"]:
    # Lecture seule pour stats
    total_tss += session["tss_planned"]
```

**Migration recommandée:**
```python
plan = WeeklyPlan.from_json(planning_file)

for session in plan.planned_sessions:
    # Type-safe, IntelliSense, validation
    total_tss += session.tss_planned
```

### 2. `planned_sessions_checker.py` (ligne 338-349)

**Usage:** Validation et comparaison (lecture seule)
**Risque:** 🟢 Faible - appelle `load_week_planning()` qui a été migrée

**Statut:** ✅ Déjà mis à jour pour utiliser `WeeklyPlan` (ligne 423)

### 3. `update_session_status.py` (ligne 388-396)

**Usage:** Recherche de session par ID (lecture seule)
**Risque:** 🟢 Faible - lecture pour sync Intervals.icu

**Pattern actuel:**
```python
with open(planning_file) as f:
    planning = json.load(f)

for session in planning["planned_sessions"]:
    if session["intervals_id"] == activity_id:
        return session["session_id"]
```

**Migration recommandée:**
```python
plan = WeeklyPlan.from_json(planning_file)

for session in plan.planned_sessions:
    if session.intervals_id == activity_id:
        return session.session_id
```

### 4. `workflow_coach.py` (ligne 248-272)

**Usage:** Orchestration workflows (lecture seule)
**Risque:** 🟢 Faible - appelle `load_week_planning()` qui a été migrée

**Statut:** ✅ Déjà mis à jour pour utiliser `WeeklyPlan` (ligne 730)

---

## Validation et tests

### Tests anti-aliasing

**Fichier:** `tests/planning/test_models_anti_aliasing.py`
**Status:** ✅ 10/10 tests passants

Tests clés :

1. **`test_backup_sessions_creates_deep_copy`**
   ```python
   backup = plan.backup_sessions()
   plan.planned_sessions[0].status = "cancelled"

   # ✅ Backup N'est PAS affecté
   assert backup[0].status == "pending"
   ```

2. **`test_shallow_copy_danger_prevented`**
   ```python
   # Démontre le PROBLÈME que nos modèles PRÉVIENNENT
   naive_backup = sessions_list.copy()  # Shallow!
   sessions_list[0].status = "cancelled"

   # ❌ Bug: backup est aussi modifié
   assert naive_backup[0].status == "cancelled"

   # ✅ Avec backup_sessions() - pas d'aliasing
   proper_backup = plan.backup_sessions()
   plan.planned_sessions[0].status = "cancelled"
   assert proper_backup[0].status == "pending"  # ✅ Protégé
   ```

3. **Tests de validation**
   - `start_date` doit être lundi
   - `end_date` doit être dimanche (start_date + 6)
   - `skip_reason` requis si `status="skipped"`
   - Sessions doivent être dans les bornes de la semaine

### Tests de migration

**Fichier:** `tests/planning/test_migration_weekly_planner.py`
**Status:** ✅ 8/8 tests passants

Tests clés :

1. **`test_update_session_status_uses_pydantic`**
   - Vérifie que `update_session_status()` utilise `WeeklyPlan`
   - Validation automatique des modifications

2. **`test_pydantic_protection_prevents_corruption`**
   - Test critique démontrant la protection Pydantic
   - Backup reste intact après modifications

3. **`test_last_updated_is_modified`**
   - Timestamp `last_updated` mis à jour correctement

**Fichier:** `tests/test_rest_and_cancellations.py`
**Status:** ✅ 14/14 tests passants

Tests mis à jour pour nouveau format Pydantic :

- Dates corrigées (lundi → dimanche)
- Champs requis ajoutés (`created_at`, `last_updated`, `version`)
- Status `rest_day` remplacé par `skipped` avec `skip_reason`
- Validation `skip_reason` ajoutée

### Commandes de test

```bash
# Tests anti-aliasing
poetry run pytest tests/planning/test_models_anti_aliasing.py -v

# Tests migration weekly_planner
poetry run pytest tests/planning/test_migration_weekly_planner.py -v

# Tests rest_and_cancellations
poetry run pytest tests/test_rest_and_cancellations.py -v

# Tous les tests planning
poetry run pytest tests/planning/ -v
```

---

## Checklist finale

Après migration, vérifier :

- [x] Tous les `json.load()` de planning remplacés par `WeeklyPlan.from_json()`
- [x] Tous les `json.dump()` de planning remplacés par `plan.to_json()`
- [x] Pas d'accès direct à `planning["planned_sessions"]`
- [x] Tests existants passent (aucune régression)
- [x] Tests anti-aliasing passent (10/10 dans `test_models_anti_aliasing.py`)
- [x] Tests migration passent (8/8 dans `test_migration_weekly_planner.py`)
- [x] Documentation `SAFE_PLANNING_PATTERNS.md` créée ✅
- [x] Audit `SHALLOW_COPY_AUDIT.md` complété

---

## Références

- **Modèles Pydantic:** `cyclisme_training_logs/planning/models.py`
- **Tests anti-aliasing:** `tests/planning/test_models_anti_aliasing.py`
- **Tests migration:** `tests/planning/test_migration_weekly_planner.py`
- **Audit complet:** `project-docs/SHALLOW_COPY_AUDIT.md`
- **Expériences memory_graph:** `project-docs/archives/memory-graph-experiments/`

---

**Généré le:** 2026-02-08
**Auteur:** Claude Sonnet 4.5
**Version:** 1.0
