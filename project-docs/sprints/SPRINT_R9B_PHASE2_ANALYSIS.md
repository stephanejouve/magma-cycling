# Sprint R9.B Phase 2 - Analyse Duplications DRY

**Date analyse:** 18 janvier 2026
**Analyste:** Claude Code (Sonnet 4.5)
**Objectif:** Identifier duplications restantes et proposer plan refactoring

---

## 📊 État Initial

### Métriques Projet
- **LOC total:** 27,973 lignes
- **Tests passing:** 598/598 (100%)
- **Coverage:** 29%
- **Fichiers Python:** 70 fichiers production

### Phase 1 Résumé (Commit 6e39e6a)
**Déjà fait:**
- ✅ Création `config_base.py` helpers centralisés
  - `create_intervals_client()` - Factory IntervalsClient
  - `load_json_config()` - Generic JSON loader
- ✅ Refactoring 2 fichiers:
  - `upload_workouts.py` (23 LOC → ~10 LOC)
  - `workflow_coach.py` (39 LOC → partiel)
- ✅ Tests validés (117/117 passing)

**Résultat Phase 1:**
- +141 LOC (helpers centralisés)
- -52 LOC (duplications éliminées)
- **Net: +89 LOC** (investissement helpers)

**Note:** Le message commit indique "Future: 12+ additional files can be refactored" - c'est l'objectif Phase 2.

---

## 🔍 Duplications Détectées Phase 2

### Pattern Duplication Principal

**Code dupliqué (répété 16× dans 11 fichiers):**
```python
# Pattern 1: Chargement credentials depuis config
config = get_intervals_config()
athlete_id = config.athlete_id
api_key = config.api_key
client = IntervalsClient(athlete_id=athlete_id, api_key=api_key)

# Pattern 2: Chargement credentials depuis .env
athlete_id = os.getenv("VITE_INTERVALS_ATHLETE_ID")
api_key = os.getenv("VITE_INTERVALS_API_KEY")
if not athlete_id or not api_key:
    raise ValueError("Credentials not configured")
client = IntervalsClient(athlete_id=athlete_id, api_key=api_key)
```

**Devrait être:**
```python
# Pattern unifié avec helper centralisé
from magma_cycling.config import create_intervals_client

client = create_intervals_client()  # 1 ligne
```

**Gain par remplacement:** ~5-7 LOC → 1 LOC = **~5 LOC économisés**

---

### Fichiers à Refactoriser (11 fichiers, 16 occurrences)

#### 🔴 Priorité P0 - Fichiers critiques (5 fichiers, 9 occurrences)

**1. `workflow_coach.py` (3,652 LOC) - 5 occurrences**
   - Ligne 199-201: `load_credentials()` method
   - Ligne 421: `step_1b_detect_all_gaps()`
   - Ligne 456: `_upload_workout_intervals()`
   - Ligne 490: `_upload_workout_intervals()` (autre appel)
   - Ligne 702: `step_6b_servo_control()`
   - Ligne 1114: `_get_7_day_planning_data()`

   **Refactoring:** Créer `self.api = create_intervals_client()` dans `__init__()`, réutiliser partout

   **Gain estimé:** 30-35 LOC → 2 LOC = **~30 LOC**

   **Risques:**
   - 108 tests impactés (vérification mocking nécessaire)
   - Méthode `load_credentials()` peut être simplifiée

   **Tests impactés:** `tests/workflows/test_workflow_coach.py` (mocking `create_intervals_client` au lieu de `IntervalsClient`)

**2. `analyzers/weekly_aggregator.py` (910 LOC) - 1 occurrence**
   - Ligne 152-158: Pattern config + IntervalsClient

   **Gain estimé:** ~7 LOC → 1 LOC = **~6 LOC**

   **Risques:** Aucun (déjà bien testé)

**3. `weekly_planner.py` (880 LOC) - 1 occurrence**
   - Ligne 74-78: Validation credentials + IntervalsClient

   **Gain estimé:** ~5 LOC → 1 LOC = **~4 LOC**

   **Risques:** Aucun

**4. `update_session_status.py` (433 LOC) - 1 occurrence**
   - Ligne 404: Pattern credentials + IntervalsClient

   **Gain estimé:** ~5 LOC → 1 LOC = **~4 LOC**

   **Risques:** Aucun

**5. `rest_and_cancellations.py` - 1 occurrence**
   - Ligne 816: Pattern credentials + IntervalsClient

   **Gain estimé:** ~5 LOC → 1 LOC = **~4 LOC**

   **Risques:** Aucun

---

#### 🟡 Priorité P1 - Scripts secondaires (6 fichiers, 7 occurrences)

**6. `scripts/backfill_intelligence.py` - 1 occurrence**
   - Ligne 76: IntervalsClient dans `__init__()`

   **Gain:** ~4 LOC

**7. `scripts/monitoring/check_workout_adherence.py` - 1 occurrence**
   - Ligne 46-48: Pattern config + IntervalsClient

   **Gain:** ~5 LOC

**8. `scripts/maintenance/clear_week_planning.py` - 1 occurrence**
   - Ligne 145-154: Chargement credentials + IntervalsClient

   **Gain:** ~10 LOC (beaucoup de validation)

**9. `planned_sessions_checker.py` - 1 occurrence**
   - Ligne 79: IntervalsClient dans `__init__()`

   **Gain:** ~4 LOC

**10. `check_activity_sources.py` - 1 occurrence**
   - Ligne 87: Pattern credentials + IntervalsClient

   **Gain:** ~5 LOC

**11. `debug_detection.py` - 1 occurrence**
   - Ligne 32: Pattern credentials + IntervalsClient

   **Gain:** ~5 LOC

---

## 📈 Gain Total Estimé

### Par Priorité

**P0 (fichiers critiques):**
- workflow_coach.py: ~30 LOC
- weekly_aggregator.py: ~6 LOC
- weekly_planner.py: ~4 LOC
- update_session_status.py: ~4 LOC
- rest_and_cancellations.py: ~4 LOC
- **Subtotal P0:** **~48 LOC**

**P1 (scripts secondaires):**
- backfill_intelligence.py: ~4 LOC
- check_workout_adherence.py: ~5 LOC
- clear_week_planning.py: ~10 LOC
- planned_sessions_checker.py: ~4 LOC
- check_activity_sources.py: ~5 LOC
- debug_detection.py: ~5 LOC
- **Subtotal P1:** **~33 LOC**

### Total Phase 2

**Total gain:** **~81 LOC éliminés**
**LOC avant:** 27,973
**LOC après:** ~27,892
**Réduction:** **0.29%**

---

## 🎯 Plan Refactoring Proposé

### Option A: Refactoring Complet (Recommandé)

**Scope:** P0 + P1 (11 fichiers, 16 occurrences)

**Timeline:**
- **Jour 1 matin (3h):**
  - Refactoring P0 critical (workflow_coach.py + 4 autres)
  - Tests validation P0

- **Jour 1 après-midi (2h):**
  - Refactoring P1 scripts (6 fichiers)
  - Tests validation P1

- **Jour 2 matin (2h):**
  - Tests complets (598+ tests)
  - Validation CI/CD
  - Coverage check (≥29%)

- **Jour 2 après-midi (1h):**
  - Documentation updates
  - Rapport MOA
  - Tag release v2.3.2

**Total:** ~8 heures développement

**Livrables:**
- ✅ 11 fichiers refactorisés
- ✅ ~81 LOC éliminés
- ✅ 598+ tests passing
- ✅ CI/CD verte
- ✅ Coverage ≥29%
- ✅ Release v2.3.2

---

### Option B: Refactoring MVP (Alternatif)

**Scope:** P0 uniquement (5 fichiers, 9 occurrences)

**Timeline:**
- **Jour 1:** Refactoring P0 + tests
- **Jour 2:** Validation CI/CD + documentation

**Total:** ~5 heures développement

**Livrables:**
- ✅ 5 fichiers refactorisés (critiques)
- ✅ ~48 LOC éliminés
- ✅ 598+ tests passing
- ✅ CI/CD verte
- ⏸ P1 reporté à R10

---

## ⚠️ Risques Identifiés

### Risque 1: Tests Mocking (workflow_coach.py)

**Impact:** MOYEN
**Probabilité:** HAUTE

**Description:**
- `workflow_coach.py` a 108 tests avec mocking `IntervalsClient`
- Après refactoring, il faudra mocker `create_intervals_client` au lieu
- Risque: Tests cassés si mocking incorrect

**Mitigation:**
1. Analyser pattern mocking existant dans tests
2. Créer helper test `mock_create_intervals_client()`
3. Remplacer tous mocks progressivement
4. Valider chaque changement (pytest après chaque commit)

**Validation:**
```bash
pytest tests/workflows/test_workflow_coach.py -v
# Doit rester 108/108 passing
```

---

### Risque 2: Breaking Change API Publique

**Impact:** FAIBLE
**Probabilité:** FAIBLE

**Description:**
- Si classes publiques exposent `IntervalsClient` dans signatures
- Utilisateurs externes (hors projet) pourraient être impactés

**Mitigation:**
- Vérifier aucune classe expose `IntervalsClient` dans API publique
- Garder backward compatibility pour méthodes `load_credentials()`
- Documenter migration si nécessaire

**Validation:**
- Aucune classe publique détectée exposant IntervalsClient
- Projet usage interne uniquement
- ✅ Risque considéré nul

---

### Risque 3: Coverage Baisse

**Impact:** MOYEN
**Probabilité:** FAIBLE

**Description:**
- Refactoring peut réduire nombre lignes testées
- Coverage pourrait baisser de 29% à 28.5%

**Mitigation:**
1. Exécuter coverage avant/après
2. Si baisse >0.5%, ajouter tests manquants
3. Target: Maintenir ≥29% minimum

**Validation:**
```bash
poetry run pytest tests/ --cov=magma_cycling --cov-report=term
# Coverage doit rester ≥29%
```

---

## ✅ Critères Acceptation MOA

### Must-Have (Bloquants)

1. **✅ CI/CD Verte**
   - 598+ tests passing
   - 0 failures, 0 errors
   - Pre-commit hooks passent

2. **✅ Coverage ≥29%**
   - Maintien niveau actuel minimum
   - Aucune baisse significative

3. **✅ LOC Réduits**
   - Objectif: -50 LOC minimum
   - Estimé: -81 LOC (dépassé ✅)

4. **✅ Aucune Régression Fonctionnelle**
   - Tests end-to-end passent
   - Workflow coach fonctionne
   - API Intervals.icu OK

5. **✅ CODING_STANDARDS Respectés**
   - PEP 257 (docstrings)
   - PEP 8 (style)
   - Google Style (docstrings)
   - 0 violations pre-commit

### Nice-to-Have (Optionnels)

1. **⭐ Coverage +1%** (29% → 30%)
   - Si refactoring simplifie tests
   - Bonus mais pas requis

2. **⭐ Complexité Réduite**
   - Moins de branches conditionnelles
   - Code plus linéaire

3. **⭐ Type Hints Améliorés**
   - Meilleur typage config helpers
   - MyPy score maintenu

---

## 🚀 Recommandation PO/MOA

**Recommandation:** ✅ **APPROUVER Option A (Refactoring Complet)**

**Justification:**

1. **ROI Excellent**
   - 8h développement → -81 LOC permanents
   - Maintenance future simplifiée
   - Consistent avec objectif R9.B DRY

2. **Risques Maîtrisés**
   - Mitigation claire pour chaque risque
   - Tests complets existants (598 tests)
   - Aucun breaking change API

3. **Timeline Raisonnable**
   - 2 jours développement
   - Compatible planning R10 MVP
   - Pas de blocage identifié

4. **Impact Positif Long-Terme**
   - Code plus maintenable
   - Onboarding développeurs simplifié
   - Bugs futurs réduits (1 source vérité)

---

## 📋 Actions Requises

**Claude Code attend validation MOA/PO pour:**

1. **Option choisie:** A (complet) ou B (MVP) ?
2. **Go/No-Go exécution:** OK pour démarrer refactoring ?
3. **Priorités ajustées:** P0/P1 OK ou modifier ?

**Format réponse attendu:**
```
✅ GO Sprint R9.B Phase 2
Option: A (Refactoring Complet)
Priorités: P0 + P1 (11 fichiers)
Timeline: 2 jours (18-19 janvier)
Tag release: v2.3.2

Commentaires PO/MOA:
[Vos commentaires optionnels]
```

---

## 📊 Annexe: Fichiers par Taille

| Fichier | LOC | Occurrences | Gain Estimé | Priorité |
|---------|-----|-------------|-------------|----------|
| workflow_coach.py | 3,652 | 5 | ~30 LOC | P0 |
| weekly_aggregator.py | 910 | 1 | ~6 LOC | P0 |
| weekly_planner.py | 880 | 1 | ~4 LOC | P0 |
| update_session_status.py | 433 | 1 | ~4 LOC | P0 |
| rest_and_cancellations.py | ~400 | 1 | ~4 LOC | P0 |
| backfill_intelligence.py | ~300 | 1 | ~4 LOC | P1 |
| check_workout_adherence.py | ~200 | 1 | ~5 LOC | P1 |
| clear_week_planning.py | ~200 | 1 | ~10 LOC | P1 |
| planned_sessions_checker.py | ~150 | 1 | ~4 LOC | P1 |
| check_activity_sources.py | ~100 | 1 | ~5 LOC | P1 |
| debug_detection.py | ~50 | 1 | ~5 LOC | P1 |
| **TOTAL** | **~7,275** | **16** | **~81 LOC** | **P0+P1** |

---

**Rapport préparé par:** Claude Code (Sonnet 4.5)
**Date:** 18 janvier 2026, 12:15 UTC+1
**Sprint:** R9.B Phase 2 - DRY Refactoring
**Status:** ⏸ En attente validation MOA/PO
