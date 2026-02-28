# Audit Shallow Copies - Projet Cyclisme Training Logs

**Date:** 8 février 2026
**Outil:** Grep + Analyse manuelle
**Objectif:** Identifier les fichiers manipulant des planning JSON sans protection Pydantic

---

## 📊 Résumé

- **Fichiers analysés:** 7 fichiers Python
- **Fichiers à risque ÉLEVÉ:** 2 (modifications directes)
- **Fichiers à risque MOYEN:** 1 (utilisation intensive)
- **Fichiers à risque FAIBLE:** 4 (lecture seule)

### Par sévérité

- 🔴 **ÉLEVÉ (2 fichiers):** Modifications directes de `planning["planned_sessions"]`
- 🟡 **MOYEN (1 fichier):** Utilisation intensive sans modifications
- 🟢 **FAIBLE (4 fichiers):** Lecture seule pour statistiques/validation

---

## 🔴 Risque ÉLEVÉ - Migrations Prioritaires

### 1. `weekly_planner.py` (ligne 730-756)

**Pattern détecté:**
```python
with open(json_file, encoding="utf-8") as f:
    planning = json.load(f)  # ← Dict brut

# MODIFICATION DIRECTE (DANGEREUX)
for session in planning["planned_sessions"]:
    if session["session_id"] == session_id:
        session["status"] = status  # ← Pas de validation!
        if reason:
            session["skip_reason"] = reason

# Sauvegarde sans validation
with open(json_file, "w", encoding="utf-8") as f:
    json.dump(planning, f, indent=2)
```

**Risques:**
- ❌ Pas de validation des types
- ❌ Pas de validation des valeurs (status peut être n'importe quoi)
- ❌ Pas de protection contre shallow copy
- ❌ Corruption silencieuse possible

**Recommandation:**
```python
from magma_cycling.planning.models import WeeklyPlan

# Chargement sécurisé
plan = WeeklyPlan.from_json(json_file)

# Modification validée
for session in plan.planned_sessions:
    if session.session_id == session_id:
        session.status = status  # ← Validation auto par Pydantic!
        if reason:
            session.skip_reason = reason

# Sauvegarde atomique
plan.to_json(json_file)
```

---

### 2. `rest_and_cancellations.py` (ligne 203-248)

**Pattern détecté:**
```python
def load_week_planning(week_id: str) -> dict:  # ← Retourne dict brut!
    """Charge planning depuis JSON."""
    with open(planning_file, encoding="utf-8") as f:
        planning = json.load(f)

    # Validation manuelle basique
    if not validate_week_planning(planning):
        raise ValueError("Planning invalide")

    return planning  # ← Dict non protégé!
```

**Risques:**
- ❌ Fonction utilisée partout dans le projet
- ❌ Retourne un dict mutable sans protection
- ❌ Validation manuelle incomplète
- ❌ Tous les appelants héritent du risque

**Impact:** Cette fonction est appelée par:
- `workflow_coach.py`
- `planned_sessions_checker.py`
- Potentiellement d'autres modules

**Recommandation:**
```python
from magma_cycling.planning.models import WeeklyPlan

def load_week_planning(week_id: str) -> WeeklyPlan:  # ← Type Pydantic!
    """Charge planning avec validation Pydantic."""
    planning_file = get_planning_path(week_id)
    return WeeklyPlan.from_json(planning_file)  # ← Protection auto!
```

---

## 🟡 Risque MOYEN - Migration Recommandée

### 3. `daily_sync.py` (ligne 311-326)

**Pattern détecté:**
```python
with open(planning_file) as f:
    planning_data = json.load(f)  # ← Dict brut

# Lecture seule, mais utilisé TOUS LES JOURS (21h30)
for session_data in planning_data["planned_sessions"]:
    session_date = date.fromisoformat(session_data["date"])
    # ... utilisation lecture seule ...
```

**Risques:**
- ⚠️ Pas de validation des données chargées
- ⚠️ Pas de type hints (IntelliSense absent)
- ⚠️ Erreurs silencieuses possibles si structure change
- ✅ MAIS: Lecture seule (pas de modifications)

**Priorité:** Moyenne (fonctionne mais fragile)

**Recommandation:**
```python
from magma_cycling.planning.models import WeeklyPlan

plan = WeeklyPlan.from_json(planning_file)  # ← Validation auto

# Type hints automatiques, IntelliSense, validation
for session in plan.planned_sessions:
    session_date = session.session_date  # ← Type-safe!
    # ...
```

---

## 🟢 Risque FAIBLE - Migration Optionnelle

### 4. `monthly_analysis.py` (ligne 94-119)
**Usage:** Statistiques mensuelles (lecture seule)
**Risque:** Faible - agrégation simple, pas de modifications

### 5. `planned_sessions_checker.py` (ligne 338-349)
**Usage:** Validation et comparaison (lecture seule)
**Risque:** Faible - appelle `load_week_planning()` qui sera migrée

### 6. `update_session_status.py` (ligne 388-396)
**Usage:** Recherche de session par ID (lecture seule)
**Risque:** Faible - lecture pour sync Intervals.icu

### 7. `workflow_coach.py` (ligne 248-272)
**Usage:** Orchestration workflows (lecture seule)
**Risque:** Faible - appelle `load_week_planning()` qui sera migrée

---

## 🎯 Plan de Migration Recommandé

### Phase 1: Fichiers Critiques (2-3 heures)

**Ordre prioritaire:**

1. **rest_and_cancellations.py** (30 min)
   - Migrer `load_week_planning()` → retourner `WeeklyPlan`
   - Impact: Toutes les fonctions appelantes bénéficient automatiquement
   - Tests: Vérifier que tous les appelants compilent

2. **weekly_planner.py** (1h)
   - Migrer méthode de mise à jour statut
   - Remplacer modifications directes par méthodes Pydantic
   - Tests: Vérifier que la sauvegarde préserve la structure

3. **daily_sync.py** (1h)
   - Migrer chargement vers `WeeklyPlan.from_json()`
   - Profiter des type hints pour IntelliSense
   - Tests: Vérifier que le sync quotidien fonctionne

### Phase 2: Fichiers Lecture Seule (Optionnel)

Migration progressive des 4 autres fichiers lors de futures modifications.

---

## ✅ Critères de Validation

Après migration, vérifier:

- [ ] Tous les `json.load()` de planning remplacés par `WeeklyPlan.from_json()`
- [ ] Tous les `json.dump()` de planning remplacés par `plan.to_json()`
- [ ] Pas d'accès direct à `planning["planned_sessions"]`
- [ ] Tests existants passent (aucune régression)
- [ ] Tests anti-aliasing passent (10/10 dans `test_models_anti_aliasing.py`)
- [ ] Documentation `SAFE_PLANNING_PATTERNS.md` créée

---

## 📈 Bénéfices Attendus

**Sécurité:**
- ✅ Protection automatique contre shallow copy
- ✅ Validation des types à chaque modification
- ✅ Validation des valeurs (enums, contraintes)
- ✅ Détection précoce des erreurs

**Maintenabilité:**
- ✅ Type hints → IntelliSense dans IDE
- ✅ Code auto-documenté
- ✅ Refactoring sûr
- ✅ Moins de bugs en production

**Performance:**
- ✅ Pas d'impact (Pydantic v2 est très rapide)
- ✅ Deep copy uniquement quand nécessaire (via `backup_sessions()`)

---

**Généré le:** 2026-02-08
**Outil:** Grep + Analyse manuelle
**Protection déjà en place:** `magma_cycling/planning/models.py` (10/10 tests)
