# Session Sprint R8 - Tests workflow_coach.py

**Date:** 11 janvier 2026
**Durée:** ~2.5h
**Objectif:** Augmenter coverage workflow_coach.py de 10% → 50%
**Résultat:** ✅ 10% → 19% (+9%, 44 tests créés)

---

## 🎯 Objectifs & Résultats

### Objectif Initial
- **Target:** workflow_coach.py 50% coverage (~100 tests)
- **Fichier:** 1,822 lignes, 58 méthodes
- **Coverage initial:** 10% (182 lignes)

### Résultats Atteints
- **Coverage final:** 19% (338 lignes)
- **Amélioration:** +9% (+156 lignes)
- **Tests créés:** 44 tests (38% de l'objectif)
- **Commits:** 2 commits (5a5c304, e3bdfbe)
- **Bugs fixés:** 1 (test_weekly_aggregator.py)

---

## 📋 Travail Effectué

### Option C: Fix Test Failed (10 min)
**Fichier:** `tests/test_weekly_aggregator.py`

**Problème:**
```python
# Test line 114-116 (AVANT)
activities = [
    {"training_load": 85, "if": 1.1},  # ❌ Mauvaise clé
    {"training_load": 90, "if": 1.15},
    {"training_load": 45, "if": 0.8},
]
```

**Solution:**
```python
# Test line 114-116 (APRÈS)
activities = [
    {"tss": 85, "if": 1.1},  # ✅ Clé correcte
    {"tss": 90, "if": 1.15},
    {"tss": 45, "if": 0.8},
]
```

**Cause:** Implementation expects `tss` key (line 710), test provided `training_load`

**Résultat:** ✅ Test passe (1/1)

---

### Option A: Reconnaissance workflow_coach.py (30 min)

**Analyse complète:**
- **58 méthodes** cataloguées
- **12 groupes fonctionnels** identifiés
- **Stratégie de test** définie (3 phases)

**Groupes Fonctionnels:**
1. Initialization & Setup (4 methods)
2. Parsing & Formatting (4 methods)
3. Intervals.icu API Operations (4 methods)
4. Planning & Modifications (5 methods)
5. UI/Display (5 methods)
6. Gap Detection (7 methods)
7. Feedback Collection (5 methods)
8. Analysis Preparation (4 methods)
9. Markdown Generation & Export (6 methods)
10. Special Session Handling (4 methods)
11. AI Analysis Workflow (4 methods)
12. Final Steps (6 methods)

**Stratégie de Test:**
- **Phase 1 (HIGH):** 30 tests - Core Logic (Parsing, Planning, Init, Gaps)
- **Phase 2 (MEDIUM):** 40 tests - Integration (Feedback, Analysis, Markdowns, Special)
- **Phase 3 (LOW):** 30 tests - UI & External (UI, API, AI, Git)

**Rapport:** `/tmp/workflow_coach_method_catalog.md`

---

### Option B Phase 1: Core Logic Tests (1h)

**Fichier:** `tests/workflows/test_workflow_coach.py` (26 tests créés)

#### 1. Parsing & Formatting (8 tests)
```python
class TestParsingAndFormatting:
    test_parse_ai_modifications_valid_json_markdown()      # ✅
    test_parse_ai_modifications_valid_json_plain()         # ✅
    test_parse_ai_modifications_empty_response()           # ✅
    test_parse_ai_modifications_no_json()                  # ✅
    test_parse_ai_modifications_invalid_json()             # ✅
    test_format_remaining_sessions_compact_empty()         # ✅
    test_format_remaining_sessions_compact_multiple()      # ✅
    test_extract_day_number_success()                      # ✅
```

**Méthodes testées:**
- `parse_ai_modifications()` - Parse JSON depuis réponse IA (markdown/plain/edge cases)
- `format_remaining_sessions_compact()` - Format sessions pour prompt IA
- `_extract_day_number()` - Extraction numéro jour depuis date

#### 2. Initialization (5 tests)
```python
class TestInitialization:
    test_init_default_params()           # ✅
    test_init_skip_flags()               # ✅
    test_init_servo_mode()               # ✅
    test_load_credentials_from_env()     # ✅
    test_load_credentials_missing()      # ✅
```

**Méthodes testées:**
- `__init__()` - Init avec différents modes (default, servo, auto)
- `load_credentials()` - Chargement credentials depuis env/config

#### 3. Planning Modifications (6 tests)
```python
class TestPlanningModifications:
    test_update_planning_json_success()                  # ✅
    test_update_planning_json_file_not_found()           # ✅
    test_apply_planning_modifications_empty()            # ✅
    test_apply_planning_modifications_unknown_action()   # ✅
    test_compute_gaps_signature_simple()                 # ✅
    test_compute_gaps_signature_all_types()              # ✅
```

**Méthodes testées:**
- `_update_planning_json()` - Mise à jour planning avec historique
- `apply_planning_modifications()` - Application modifications IA
- `_compute_gaps_signature()` - Calcul signature MD5 pour détection changements

#### 4. Gap Detection Logic (7 tests)
```python
class TestGapDetectionLogic:
    test_detect_unanalyzed_activities_no_config()        # ✅
    test_detect_unanalyzed_activities_success()          # ✅
    test_detect_unanalyzed_activities_api_error()        # ✅
    test_filter_documented_sessions_empty()              # ✅
    test_filter_documented_sessions_skipped()            # ✅
    test_filter_documented_sessions_rest()               # ✅
    test_filter_documented_sessions_all_documented()     # ✅
```

**Méthodes testées:**
- `_detect_unanalyzed_activities()` - Détection activités non analysées via API
- `_filter_documented_sessions()` - Filtrage sessions déjà documentées

**Coverage Impact:** 10% → 14% (+4%, +80 lignes)

**Commit:** 5a5c304 (Phase 1)

---

### Option B Phase 2: Integration Tests (1h)

**Fichier:** `tests/workflows/test_workflow_coach.py` (+18 tests, total 44)

#### 5. Feedback Collection (8 tests)
```python
class TestFeedbackCollection:
    test_validate_feedback_collection_skip_flag()           # ✅
    test_validate_feedback_collection_no_gaps()             # ✅
    test_validate_feedback_collection_should_collect()      # ✅
    test_prepare_feedback_context_success()                 # ✅
    test_prepare_feedback_context_no_credentials()          # ✅
    test_execute_feedback_collection_with_activity()        # ✅
    test_execute_feedback_collection_quick_mode()           # ✅
    test_collect_rest_feedback_valid()                      # ✅
```

**Méthodes testées:**
- `_validate_feedback_collection()` - Validation si feedback doit être collecté
- `_prepare_feedback_context()` - Préparation contexte (credentials + activity)
- `_execute_feedback_collection()` - Exécution subprocess collect_athlete_feedback
- `_collect_rest_feedback()` - Collection feedback repos (sleep, HRV, resting HR)

#### 6. Markdown Generation (6 tests)
```python
class TestMarkdownGeneration:
    test_preview_markdowns_single()                      # ✅
    test_copy_to_clipboard_success()                     # ✅
    test_copy_to_clipboard_failure()                     # ✅
    test_detect_session_type_from_markdown_normal()      # ✅
    test_detect_session_type_from_markdown_rest()        # ✅
    test_detect_session_type_from_markdown_cancelled()   # ✅
```

**Méthodes testées:**
- `_preview_markdowns()` - Affichage preview markdowns générés
- `_copy_to_clipboard()` - Copie markdowns via pbcopy (subprocess.Popen)
- `_detect_session_type_from_markdown()` - Détection type session (rest/cancelled/skipped/None)

#### 7. UI Helpers (4 tests)
```python
class TestUIHelpers:
    test_clear_screen()          # ✅
    test_print_header()          # ✅
    test_print_separator()       # ✅
    test_wait_user()             # ✅
```

**Méthodes testées:**
- `clear_screen()` - os.system('clear')
- `print_header()` - Print formatted header
- `print_separator()` - Print separator line
- `wait_user()` - Wait for enter key

**Coverage Impact:** 14% → 19% (+5%, +76 lignes)

**Commit:** e3bdfbe (Phase 2)

---

## 🔧 Patterns de Test Utilisés

### Mocking Patterns
```python
# File I/O
@patch("builtins.open", new_callable=mock_open, read_data='...')
@patch("json.load", return_value={...})
@patch("json.dump")

# Subprocess
@patch("subprocess.run")
@patch("subprocess.Popen")

# User Input
@patch("builtins.input", return_value="...")
@patch("builtins.input", side_effect=["val1", "val2", ...])

# System Calls
@patch("os.system")

# External API
@patch("requests.Session")
@patch("pathlib.Path.exists", return_value=True)

# Config
@patch("magma_cycling.workflow_coach.get_data_config")
@patch.dict("os.environ", {"KEY": "value"})
```

### Test Organization
```python
class TestCategoryName:
    """Test description of category."""

    def test_method_name_scenario(self):
        """Test method_name does X when Y."""
        # Arrange
        coach = WorkflowCoach(skip_feedback=True, skip_git=True)

        # Act
        result = coach.method_name(...)

        # Assert
        assert result == expected
```

---

## 📊 Métriques Finales

### Coverage Evolution
| Metric | Before | After Phase 1 | After Phase 2 | Improvement |
|--------|--------|---------------|---------------|-------------|
| Lines covered | 182 | 262 | 338 | +156 (+85.7%) |
| Coverage % | 10% | 14% | 19% | +9% |
| Tests total | 597 | 623 | 641 | +44 |

### Tests Breakdown
- **Phase 1:** 26 tests (Parsing 8, Init 5, Planning 6, Gaps 7)
- **Phase 2:** 18 tests (Feedback 8, Markdown 6, UI 4)
- **Total:** 44 tests créés
- **Success rate:** 100% (44/44 passing)

### File Stats
- **Test file:** `tests/workflows/test_workflow_coach.py`
- **Lines:** 728 lignes
- **Classes:** 7 test classes
- **Methods:** 44 test methods
- **Coverage target file:** `magma_cycling/workflow_coach.py` (1,822 lignes)

---

## 🚧 Travail Restant (Future Sprints)

### Pour atteindre 50% coverage

**Remaining:** +31% coverage (~568 lignes), ~56 tests

**Priority Groups:**

#### HIGH Priority (20 tests, +10%)
- Analysis Preparation (8 tests)
  - `step_3_prepare_analysis()` - 3 tests (modes)
  - `_detect_week_id()` - 2 tests
  - `_check_planning_available()` - 2 tests
  - `_ask_fallback_consent()` - 1 test

- Special Session Handling (12 tests)
  - `_show_special_sessions()` - 2 tests
  - `_handle_rest_cancellations()` - 3 tests
  - `_handle_skipped_sessions()` - 4 tests
  - `_handle_batch_all()` - 3 tests

#### MEDIUM Priority (20 tests, +10%)
- Intervals.icu API Operations (10 tests)
  - `_get_workout_id_intervals()` - 3 tests
  - `_delete_workout_intervals()` - 2 tests
  - `_upload_workout_intervals()` - 3 tests
  - `_post_analysis_to_intervals()` - 2 tests

- AI Analysis Workflow (10 tests)
  - `_generate_coach_prompt()` - 3 tests
  - `step_4_paste_prompt()` - 2 tests
  - `step_4b_display_analysis()` - 2 tests
  - `step_5_validate_analysis()` - 3 tests

#### LOW Priority (16 tests, +11%)
- Markdown Export (6 tests)
  - `_export_markdowns()` - 3 tests
  - `_insert_to_history()` - 3 tests

- Git Operations (5 tests)
  - `step_7_git_commit()` - 2 tests
  - `_optional_git_commit()` - 2 tests
  - Integration test - 1 test

- Orchestration (5 tests)
  - `step_1_welcome()` - 2 tests
  - `step_1b_detect_all_gaps()` - 2 tests
  - `run()` - 1 integration test

---

## 📝 Commits Détails

### Commit 1: Phase 1 (5a5c304)
```bash
test: Sprint R8 Phase 1 - workflow_coach.py core logic tests (+4% coverage)

Sprint R8 Goal: Increase workflow_coach.py coverage from 10% → 50%
Phase 1: Core Logic Tests (26 tests)

Tests Created:
- Parsing & Formatting: 8 tests
- Initialization: 5 tests
- Planning Modifications: 6 tests
- Gap Detection Logic: 7 tests

Coverage Impact:
- workflow_coach.py: 10% → 14% (+4%, +80 lines)
- All 26 tests passing ✅

Bug Fix:
- test_weekly_aggregator.py: Fixed test_extract_training_learnings
  - Changed test data key from 'training_load' to 'tss'
```

### Commit 2: Phase 2 (e3bdfbe)
```bash
test: Sprint R8 Phase 2 - workflow_coach.py integration tests (+5% coverage)

Sprint R8 Goal: Increase workflow_coach.py coverage from 10% → 50%
Phase 2: Integration Tests (18 tests)

Tests Created:
- Feedback Collection: 8 tests
- Markdown Generation: 6 tests
- UI Helpers: 4 tests

Coverage Impact:
- workflow_coach.py: 14% → 19% (+5%, +76 lines)
- Total tests: 26 → 44 (+18 tests)
```

---

## 🎓 Lessons Learned

### Efficacité
- **Vitesse:** 44 tests en 2.5h = 17.6 tests/h (excellent)
- **Qualité:** 100% tests passing dès la première exécution (après fixes mineurs)
- **Organisation:** Reconnaissance préalable (Option A) très payante

### Patterns Efficaces
1. **Mocking systématique** des dépendances externes (API, file I/O, subprocess)
2. **Tests unitaires purs** pour core logic (Phase 1)
3. **Tests d'intégration** avec mocks pour external calls (Phase 2)
4. **Fixtures implicites** via `WorkflowCoach(skip_feedback=True, skip_git=True)`

### Pièges Évités
- ❌ Ne pas tester les valeurs de retour réelles (ex: `_detect_session_type_from_markdown` retourne `None` pour workouts normaux, pas `"workout"`)
- ❌ Mauvais mock de subprocess (utiliser `Popen` au lieu de `run` quand l'implémentation utilise `Popen`)
- ❌ Mock `builtins.input` doit utiliser `side_effect` pour inputs multiples

---

## 📋 Checklist Sprint R8

- [x] Option C: Fix test_weekly_aggregator.py failed test
- [x] Option A: Reconnaissance workflow_coach.py (58 methods cataloged)
- [x] Option B Phase 1: Core Logic tests (26 tests)
- [x] Option B Phase 2: Integration tests (18 tests)
- [x] Commit Phase 1 (5a5c304)
- [x] Commit Phase 2 (e3bdfbe)
- [x] Update CHANGELOG.md (si nécessaire)
- [x] Document session (ce fichier)
- [ ] Sprint R9: Continuer tests workflow_coach.py (56 tests restants)

---

## 🚀 Next Steps (Sprint R9)

**Objectif:** Continuer workflow_coach.py jusqu'à 50%

**Plan:**
1. Analysis Preparation tests (8 tests) - 1h
2. Special Session Handling tests (12 tests) - 1.5h
3. Intervals.icu API tests (10 tests) - 1h
4. AI Workflow tests (10 tests) - 1h
5. Remaining (16 tests) - 1.5h

**Estimation:** 6h pour atteindre 50% coverage (100 tests total)

---

**Session terminée:** 11 janvier 2026 - 22h30
**Status:** ✅ SUCCESS
**Prochaine session:** Sprint R9 - Continuer tests workflow_coach.py

🤖 Generated with [Claude Code](https://claude.com/claude-code)
