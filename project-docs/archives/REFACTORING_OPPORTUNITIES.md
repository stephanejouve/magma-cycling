# Refactoring Opportunities

Document des opportunités d'amélioration identifiées lors de l'analyse de qualité de code (2026-01-03).

## 🔴 Priorité Critique

### 1. WorkflowCoach.step_1b_detect_all_gaps()
**Fichier:** `cyclisme_training_logs/workflow_coach.py:930`
**Complexité:** F (48) - **Critique**
**Taille:** ~200+ lignes

**Problèmes:**
- Fonction monolithique faisant trop de choses
- Complexité cyclomatique très élevée (48)
- Difficile à tester et maintenir

**Refactoring proposé:**
```python
# Extraire en sous-fonctions :
def _detect_unanalyzed_activities(self) -> list
def _detect_skipped_sessions(self) -> list
def _filter_documented_sessions(self, sessions) -> list
def _detect_rest_days(self) -> list
def _detect_cancelled_sessions(self) -> list
def _display_gaps_summary(self, gaps_data) -> None
def _prompt_user_choice(self, gaps_data) -> str
```

**Impact:** Haute priorité - affecte maintenabilité du workflow principal

---

## 🟠 Priorité Haute

### 2. WorkflowCoach.step_2_collect_feedback()
**Fichier:** `cyclisme_training_logs/workflow_coach.py`
**Complexité:** C (17)

**Problèmes:**
- Logique de collecte de feedback mélangée avec affichage
- Gestion multiple de cas spéciaux

**Refactoring proposé:**
- Séparer collecte de données et présentation
- Extraire validation dans fonctions dédiées

---

### 3. CasingNormalizer.run()
**Fichier:** `cyclisme_training_logs/normalize_weekly_reports_casing.py:159`
**Complexité:** C (15)

**Problèmes:**
- Mélange logique métier et interaction utilisateur
- Plusieurs responsabilités dans une fonction

**Refactoring proposé:**
- Extraire logique de normalisation
- Séparer confirmation utilisateur
- Créer fonctions pour backup et application

---

## 🟡 Priorité Moyenne

### 4. WorkflowCoach._display_reconciliation_report()
**Complexité:** B (10)

**Refactoring proposé:**
- Extraire formatage des sections
- Simplifier logique de comparaison

### 5. WorkflowCoach.run()
**Complexité:** B (10)

**Refactoring proposé:**
- Simplifier orchestration des étapes
- Extraire gestion d'erreurs

---

## 📊 Métriques de Complexité

### Distribution par Niveau
- **A (1-5):** Acceptable - La majorité des fonctions
- **B (6-10):** Légèrement complexe - 8 fonctions
- **C (11-20):** Complexe - 4 fonctions
- **F (41+):** Critique - 1 fonction ⚠️

### Top 10 Fonctions Complexes
1. `WorkflowCoach.step_1b_detect_all_gaps` - F (48) 🔴
2. `WorkflowCoach.step_2_collect_feedback` - C (17)
3. `CasingNormalizer.run` - C (15)
4. `WorkflowCoach._show_special_sessions` - C (14)
5. `WorkflowCoach._display_reconciliation_report` - B (10)
6. `WorkflowCoach.run` - B (10)
7. `main` (upload_workouts.py) - B (9)
8. `WorkflowCoach.step_7_git_commit` - B (8)
9. `WorkflowCoach._generate_coach_prompt` - B (8)
10. `CasingNormalizer.print_report` - B (8)

---

## 📝 Documentation

### Issues pydocstyle: 396 problèmes

**Répartition par type:**
- **D400:** First line should end with a period (~250)
- **D107:** Missing docstring in __init__ (~50)
- **D205:** Blank line issues (~40)
- **D103:** Missing docstring in public function (~30)
- **Autres:** (~26)

**Actions recommandées:**
1. Script automatique pour ajouter periods (D400)
2. Template pour __init__ docstrings
3. Formatter pour blank lines
4. Review manuel pour fonctions publiques

---

## 🔍 Type Checking (mypy)

### 73 erreurs mypy

**Catégories principales:**
- Implicit Optional (PEP 484): ~15
- Missing type annotations: ~20
- Incompatible types: ~25
- Other (attr-defined, etc.): ~13

**Plan d'action:**
1. Fixer Implicit Optional avec regex search/replace
2. Ajouter annotations types variables
3. Corriger incompatibilités de types
4. Configurer mypy plus strict progressivement

---

## 🛠️ Stratégie de Refactoring

### Phase 1: Quick Wins (1-2h)
- [ ] Fixer D400 docstrings automatiquement
- [ ] Ajouter __init__ docstrings manquantes
- [ ] Fixer Implicit Optional (PEP 484)

### Phase 2: Moyenne Priorité (3-5h)
- [ ] Extraire sous-fonctions de `step_1b_detect_all_gaps`
- [ ] Simplifier `step_2_collect_feedback`
- [ ] Refactorer `CasingNormalizer.run`

### Phase 3: Amélioration Continue (ongoing)
- [ ] Réduire complexité des fonctions B/C
- [ ] Ajouter type annotations progressivement
- [ ] Améliorer couverture de tests

---

## 📈 Indicateurs de Suivi

### Objectifs
- **Complexité max:** Aucune fonction > C (20)
- **Doc coverage:** > 95% fonctions documentées
- **Type coverage:** > 80% avec annotations
- **Tests:** Maintenir 100% passing

### État Actuel (2026-01-03)
- ❌ Complexité: 1 fonction F (48)
- ⚠️ Doc: 396 issues pydocstyle
- ⚠️ Types: 73 erreurs mypy
- ✅ Tests: 326/326 passing

---

*Généré par analyse automatique - 2026-01-03*
