# Phase 1b - end_of_week.py Completion (52% → 80%)
## Prompt Développeur Claude Code

**Date:** 25 Janvier 2026
**Sprint:** R9.E - Phase 1b
**Objectif:** Coverage 52% → 80%+ (end_of_week.py)
**Durée estimée:** 4-6 heures

---

## 🎯 Contexte Projet

### État Actuel (Post Phase 1)
- ✅ **Fondation établie** : 29 tests passing, 52% coverage
- ✅ **Patterns validés** : Mock-based, dry-run modes, E2E flows
- ✅ **Livrables Phase 1** : Voir `sprint-r9e-20260125/SPRINT_R9E_REPORT.md`

### Objectif Phase 1b
**Mission:** Compléter la couverture test end_of_week.py pour atteindre 80%+

**Résultat attendu:**
- 17 tests failing → passing (corrections imports locaux)
- +15-20 nouveaux tests (paths non couverts)
- Coverage final: **80%+** (349/437 lignes minimum)
- Tests totaux: ~44 passing

---

## 📋 Tâches Développement

### Tâche 1: Fixer 17 Tests Failing ⚠️ (Priorité P0)

**Problème technique:** Imports locaux dans production code bloquent mocks

**Tests à corriger:**

#### A. WeeklyAnalysis Tests (9 tests)
```python
# Tests concernés (test_end_of_week.py lignes ~220-380)
- test_step1_weekly_analysis_execution_full
- test_step1_weekly_analysis_execution_error
- test_step1_weekly_analysis_with_context
- test_step1_weekly_analysis_metrics_validation
- test_step1_weekly_analysis_state_update
- test_step1_weekly_analysis_dry_run
- test_step1_weekly_analysis_with_multiple_activities
- test_step1_weekly_analysis_with_empty_week
- test_step1_weekly_analysis_with_invalid_metrics
```

**Solution technique:**
1. Identifier imports locaux dans `end_of_week.py`:
   ```python
   # Production code (lignes ~150-180)
   from magma_cycling.analysis.weekly_analysis import WeeklyAnalysis
   ```

2. Refactorer pour permettre mocking:
   ```python
   # Option A: Import au top-level
   from magma_cycling.analysis.weekly_analysis import WeeklyAnalysis

   # Option B: Dependency injection
   def step1_weekly_analysis(config, weekly_analysis_cls=None):
       if weekly_analysis_cls is None:
           from magma_cycling.analysis.weekly_analysis import WeeklyAnalysis
           weekly_analysis_cls = WeeklyAnalysis
   ```

3. Adapter tests pour mocker correctement:
   ```python
   @patch('magma_cycling.workflows.end_of_week.WeeklyAnalysis')
   def test_step1_weekly_analysis_execution_full(mock_weekly_analysis):
       # Test implementation
       pass
   ```

#### B. PIDDailyEvaluator Tests (6 tests)
```python
# Tests concernés (lignes ~385-520)
- test_step1b_pid_daily_evaluator_execution
- test_step1b_pid_daily_evaluator_error_handling
- test_step1b_pid_daily_evaluator_state_update
- test_step1b_pid_daily_evaluator_dry_run
- test_step1b_pid_daily_evaluator_with_multiple_days
- test_step1b_pid_daily_evaluator_with_invalid_data
```

**Solution:** Même approche que WeeklyAnalysis

#### C. CLI Testing (2 tests)
```python
# Tests concernés (lignes ~750-800)
- test_parse_args_with_sys_argv
- test_main_entry_point
```

**Solution:** Mocker `sys.argv` correctement:
```python
@patch('sys.argv', ['end_of_week.py', '--week', 'S078', '--dry-run'])
def test_parse_args_with_sys_argv():
    args = parse_args()
    assert args.week == 'S078'
    assert args.dry_run is True
```

---

### Tâche 2: Nouveaux Tests Paths Non Couverts (+15-20 tests)

**Objectif:** Couvrir les 48% restants (210 lignes non testées)

#### A. Step1 - Weekly Analysis (5 nouveaux tests)
```python
# Paths à couvrir:
# - end_of_week.py lignes 150-180 (import et instantiation)
# - Gestion erreurs WeeklyAnalysis.analyze()
# - Validation métriques output
# - State management après analyse
# - Dry-run mode step1

def test_step1_weekly_analysis_with_custom_config():
    """Test step1 avec config personnalisée"""
    pass

def test_step1_weekly_analysis_output_validation():
    """Test validation des métriques output WeeklyAnalysis"""
    pass

def test_step1_weekly_analysis_state_persistence():
    """Test sauvegarde state après analyse"""
    pass

def test_step1_weekly_analysis_error_recovery():
    """Test recovery après erreur analyse"""
    pass

def test_step1_weekly_analysis_with_missing_activities():
    """Test step1 avec semaine sans activités"""
    pass
```

#### B. Step1b - PID Daily Evaluator (4 nouveaux tests)
```python
# Paths à couvrir:
# - end_of_week.py lignes 185-215 (PID evaluation)
# - Gestion erreurs PIDDailyEvaluator
# - Validation recommandations output
# - Integration avec state step1

def test_step1b_pid_integration_with_step1():
    """Test intégration step1 → step1b"""
    pass

def test_step1b_pid_recommendations_validation():
    """Test validation format recommandations PID"""
    pass

def test_step1b_pid_with_edge_case_metrics():
    """Test PID avec métriques limites (TSB extrêmes)"""
    pass

def test_step1b_pid_state_update_after_evaluation():
    """Test mise à jour state après évaluation PID"""
    pass
```

#### C. Step4 - Validation Workouts Auto Mode (3 nouveaux tests)
```python
# Paths à couvrir:
# - end_of_week.py lignes 300-330 (validation auto)
# - Parsing AI workouts
# - Validation format .zwo

def test_step4_auto_validation_with_valid_workouts():
    """Test validation automatique workouts valides"""
    pass

def test_step4_auto_validation_with_invalid_format():
    """Test détection erreurs format .zwo"""
    pass

def test_step4_auto_validation_with_missing_fields():
    """Test validation champs obligatoires"""
    pass
```

#### D. Step5 - Upload Workouts Auto Mode (3 nouveaux tests)
```python
# Paths à couvrir:
# - end_of_week.py lignes 335-365 (upload auto)
# - WorkoutUploader integration
# - Error handling upload

def test_step5_auto_upload_with_workout_uploader():
    """Test upload automatique avec WorkoutUploader"""
    pass

def test_step5_auto_upload_error_handling():
    """Test gestion erreurs upload (API failures)"""
    pass

def test_step5_auto_upload_state_update():
    """Test mise à jour state après upload"""
    pass
```

---

### Tâche 3: Validation Coverage 80%+ (Checkpoint)

**Commandes validation:**
```bash
# Run tous les tests end_of_week
poetry run pytest tests/workflows/test_end_of_week.py -v

# Vérifier coverage
poetry run pytest tests/workflows/test_end_of_week.py \
  --cov=magma_cycling.workflows.end_of_week \
  --cov-report=term-missing \
  --cov-report=html

# Ouvrir rapport HTML
open htmlcov/index.html
```

**Critères validation:**
- ✅ **44+ tests passing** (29 existants + 15 nouveaux minimum)
- ✅ **0 tests failing** (17 tests corrigés)
- ✅ **Coverage ≥80%** (349/437 lignes minimum)
- ✅ **Paths critiques couverts** (step1, step1b, step4, step5 auto)

---

## 📁 Fichiers à Modifier

### 1. Production Code (Si nécessaire)
**Fichier:** `magma_cycling/workflows/end_of_week.py`

**Modifications potentielles:**
- Refactoring imports locaux (si Option A choisie)
- Ajout dependency injection (si Option B choisie)
- **IMPORTANT:** Minimal changes, préserver comportement existant

### 2. Test Suite (Principal)
**Fichier:** `tests/workflows/test_end_of_week.py`

**Modifications:**
- Fixer 17 tests failing (mocks adaptatifs)
- Ajouter 15-20 nouveaux tests (paths non couverts)
- Maintenir patterns Phase 1 (mock-based, dry-run, E2E)

---

## 🎯 Patterns de Test à Respecter

### Pattern 1: Mock-Based Testing
```python
from unittest.mock import patch, MagicMock

@patch('magma_cycling.workflows.end_of_week.WeeklyAnalysis')
@patch('magma_cycling.workflows.end_of_week.PIDDailyEvaluator')
def test_workflow_integration(mock_pid, mock_analysis):
    """Test avec mocks pour isolation complète"""
    mock_analysis.return_value.analyze.return_value = {...}
    mock_pid.return_value.evaluate.return_value = {...}
    # Test implementation
```

### Pattern 2: Dry-Run Mode Protection
```python
def test_step_with_dry_run_protection():
    """Test que dry-run ne modifie pas le système"""
    with patch('magma_cycling.workflows.end_of_week.commit_changes') as mock_commit:
        result = run_step(dry_run=True)
        mock_commit.assert_not_called()  # Protection simulation
```

### Pattern 3: State Management
```python
def test_state_persistence_across_steps():
    """Test que le state est correctement propagé"""
    state = {}
    step1(state)
    assert 'weekly_analysis' in state
    step1b(state)
    assert 'pid_recommendations' in state
```

### Pattern 4: Error Handling
```python
def test_error_recovery_with_cleanup():
    """Test que les erreurs sont gérées proprement"""
    with patch('...') as mock:
        mock.side_effect = Exception("Test error")
        with pytest.raises(Exception):
            step1(...)
        # Vérifier cleanup (fichiers temporaires, etc.)
```

---

## ✅ Checklist Développement

### Phase Préparation
- [ ] Lire `sprint-r9e-20260125/SPRINT_R9E_REPORT.md` (contexte)
- [ ] Analyser `sprint-r9e-20260125/test_end_of_week.py` (tests existants)
- [ ] Examiner `sprint-r9e-20260125/end_of_week-production.py` (code production)
- [ ] Identifier patterns Phase 1 à conserver

### Phase Développement
- [ ] **Tâche 1:** Fixer 17 tests failing
  - [ ] WeeklyAnalysis tests (9 tests)
  - [ ] PIDDailyEvaluator tests (6 tests)
  - [ ] CLI tests (2 tests)
- [ ] **Tâche 2:** Ajouter 15-20 nouveaux tests
  - [ ] Step1 tests (5 tests)
  - [ ] Step1b tests (4 tests)
  - [ ] Step4 auto tests (3 tests)
  - [ ] Step5 auto tests (3 tests)
- [ ] **Tâche 3:** Validation coverage 80%+
  - [ ] Run tests + coverage report
  - [ ] Vérifier ≥44 tests passing
  - [ ] Confirmer ≥80% coverage

### Phase Validation
- [ ] Tests passing: 44+ ✅
- [ ] Coverage: ≥80% ✅
- [ ] Paths critiques couverts ✅
- [ ] Patterns Phase 1 respectés ✅
- [ ] Production code minimal changes ✅

### Phase Livraison
- [ ] Commit avec message conventionnel
- [ ] Update ROADMAP.md (métriques)
- [ ] Créer rapport Phase 1b
- [ ] Archiver livrables

---

## 📊 Métriques Cibles Phase 1b

| Métrique | Avant (Phase 1) | Cible Phase 1b | Gain |
|----------|-----------------|----------------|------|
| Tests passing | 29/46 | **44+/46** | +15 tests |
| Tests failing | 17 | **0** | -17 |
| Coverage | 52% (227L) | **≥80%** (349L+) | +28% |
| Lignes sécurisées | 227 | **349+** | +122 lignes |

---

## 🚨 Points d'Attention

### Priorité P0 - Critique
1. **Ne pas casser tests Phase 1** : 29 tests passing doivent rester green
2. **Minimal changes production** : Préserver comportement existant
3. **Mock isolation complète** : Pas de dépendances externes (API, filesystem)

### Priorité P1 - Important
4. **Respecter patterns Phase 1** : Mock-based, dry-run, E2E flows
5. **Coverage paths critiques** : Step1, step1b, step4/5 auto modes
6. **Documentation inline** : Docstrings claires pour nouveaux tests

### Priorité P2 - Bonne Pratique
7. **Nommage conventionnel** : `test_stepX_feature_scenario`
8. **Assertion messages** : Messages clairs pour debugging
9. **Performance tests** : Éviter tests longs (timeout 5s max)

---

## 📝 Convention Commits

**Format:** `test(workflows): <description> [ROADMAP@sha]`

**Exemples:**
```bash
git commit -m "test(workflows): Fix 17 failing tests end_of_week.py [ROADMAP@fe868c5]"
git commit -m "test(workflows): Add 15 tests for step1/step1b coverage [ROADMAP@fe868c5]"
git commit -m "test(workflows): Reach 80% coverage end_of_week.py [ROADMAP@fe868c5]"
```

**ROADMAP sha:** `fe868c5` (référence Sprint R10 section)

---

## 🔗 Références Techniques

### Documentation Externe
- **pytest mocking:** https://docs.pytest.org/en/stable/how-to/monkeypatch.html
- **unittest.mock:** https://docs.python.org/3/library/unittest.mock.html
- **coverage.py:** https://coverage.readthedocs.io/

### Fichiers Projet
- **Production code:** `magma_cycling/workflows/end_of_week.py` (437 lignes)
- **Test suite Phase 1:** `tests/workflows/test_end_of_week.py` (815 lignes)
- **ROADMAP:** `project-docs/ROADMAP.md` (Sprint R10 ligne 2030+)

### Archives Sprint R9.E
- **Rapport Phase 1:** `sprint-r9e-20260125/SPRINT_R9E_REPORT.md`
- **Tests référence:** `sprint-r9e-20260125/test_end_of_week.py`
- **Code référence:** `sprint-r9e-20260125/end_of_week-production.py`

---

## 💡 Conseils Développement

### Approche Recommandée
1. **Commencer par Tâche 1** (fixer tests failing)
   - Plus de valeur immédiate (17 tests → passing)
   - Établir patterns pour Tâche 2

2. **Puis Tâche 2** (nouveaux tests)
   - Prioriser paths critiques (step1, step1b)
   - Atteindre 80% coverage progressivement

3. **Valider incrémentalement**
   - Run coverage après chaque groupe de tests
   - Ajuster stratégie selon progression

### Debugging Tests Failing
```bash
# Run un test spécifique
poetry run pytest tests/workflows/test_end_of_week.py::test_step1_weekly_analysis_execution_full -v

# Mode verbose avec output
poetry run pytest tests/workflows/test_end_of_week.py::test_step1_weekly_analysis_execution_full -vv -s

# Avec debugger
poetry run pytest tests/workflows/test_end_of_week.py::test_step1_weekly_analysis_execution_full --pdb
```

### Vérifier Coverage Incrementale
```bash
# Coverage sur un module spécifique
poetry run pytest tests/workflows/test_end_of_week.py \
  --cov=magma_cycling.workflows.end_of_week \
  --cov-report=term-missing | grep "end_of_week.py"

# Lignes non couvertes
poetry run pytest tests/workflows/test_end_of_week.py \
  --cov=magma_cycling.workflows.end_of_week \
  --cov-report=term-missing | grep "Missing"
```

---

## ✅ Validation Finale Phase 1b

**Avant de livrer, vérifier:**

1. ✅ **Tests passing:** `poetry run pytest tests/workflows/test_end_of_week.py -v`
   - Résultat attendu: 44+ passed, 0 failed

2. ✅ **Coverage 80%+:** `poetry run pytest ... --cov=... --cov-report=term`
   - Résultat attendu: Coverage ≥80%

3. ✅ **PEP 8 compliance:** `poetry run ruff check magma_cycling/`
   - Résultat attendu: 0 warnings

4. ✅ **Type checking:** `poetry run mypy magma_cycling/`
   - Résultat attendu: 0 errors

5. ✅ **Tests Phase 1 preservés:** 29 tests existants toujours green

---

## 📦 Livrables Attendus Phase 1b

1. **Code:**
   - `tests/workflows/test_end_of_week.py` (mis à jour, ~1000 lignes)
   - `magma_cycling/workflows/end_of_week.py` (minimal changes si nécessaire)

2. **Documentation:**
   - Rapport Phase 1b (métriques, coverage, commits)
   - Update `project-docs/ROADMAP.md` (métriques ligne 287-288, 323)

3. **Validation:**
   - Coverage report ≥80%
   - 44+ tests passing
   - 0 tests failing

---

## 🚀 Go/No-Go

**Question finale développeur:**
> Es-tu prêt à démarrer Phase 1b avec ces spécifications ?

**Estimation confirmation:** 4-6 heures développement

**Timing exécution:** Pendant pause stratégique S078-S079

---

**Préparé par:** MOA Claude Sonnet 4.5
**Pour:** Développeur Claude Code
**Date:** 25 Janvier 2026
**Validé PO:** ✅ (Release Phase 1 acceptée, Phase 1b différée validée)
