# Analyse Dette Technique: workflow_coach.py

**Date**: 2026-02-19
**Statut**: Proposition
**Auteur**: Claude Sonnet 4.5

## 📊 Métriques Actuelles

- **Lignes de code**: 3669 lignes
- **Nombre de méthodes**: 62 méthodes dans 1 classe
- **Couverture de test**: 49%
- **Lignes non couvertes**: 952 lignes

## 🚨 Problèmes Identifiés

### 1. God Class (Violation SRP)

La classe `WorkflowCoach` a **trop de responsabilités** :

- ✅ Orchestration du workflow
- ❌ Gestion UI/Console
- ❌ Appels API Intervals.icu
- ❌ Manipulation planning JSON
- ❌ Détection d'activités
- ❌ Parsing de réponses AI
- ❌ Modifications de planning
- ❌ Réconciliation planning/activités

**Principe violé** : Single Responsibility Principle (SRP)

### 2. Méthodes Trop Longues

Méthodes dépassant 100 lignes :
- `reconcile_week()` : ~210 lignes
- `step_1b_detect_all_gaps()` : ~100 lignes
- `apply_planning_modifications()` : ~30 lignes mais complexe

### 3. Code Dupliqué

- Appels répétés à `self.api.get_*()` (IntervalsClient)
- Chargement planning JSON répété
- Format/validation sessions similaire

## 🎯 Proposition de Refactoring

### Phase 1: Extraction Classes Helper

#### 1.1 `ConsoleUI` (UI/Présentation)
```python
class ConsoleUI:
    """Gestion affichage console."""

    @staticmethod
    def clear_screen():
        """Clear console."""

    @staticmethod
    def print_header(title, subtitle=None):
        """Affiche header."""

    @staticmethod
    def print_separator():
        """Affiche séparateur."""

    @staticmethod
    def wait_user(message="..."):
        """Attend entrée utilisateur."""
```

**Bénéfices**:
- ✅ Testable unitairement
- ✅ Réutilisable dans d'autres scripts
- ✅ Découplage UI/logique métier

**Localisation**: `cyclisme_training_logs/core/console_ui.py`

---

#### 1.2 `PlanningModifier` (Modifications Planning)
```python
class PlanningModifier:
    """Applique modifications planning JSON."""

    def apply_lighten(self, session_id: str, percentage: int):
        """Allège séance."""

    def apply_cancel(self, session_id: str, reason: str):
        """Annule séance."""

    def apply_replace(self, session_id: str, new_code: str):
        """Remplace séance."""

    def apply_modifications(self, modifications: list):
        """Applique batch modifications."""
```

**Bénéfices**:
- ✅ Logique métier isolée
- ✅ Tests unitaires faciles
- ✅ Réutilisable (API, CLI, etc.)

**Localisation**: `cyclisme_training_logs/planning/modifier.py`

---

#### 1.3 `IntervalsAPIHelper` (Wrapper API)
```python
class IntervalsAPIHelper:
    """Helper méthodes courantes API Intervals.icu."""

    def __init__(self, client: IntervalsClient):
        self.client = client

    def get_workout_id(self, date: str) -> str | None:
        """Récupère workout ID pour date."""

    def delete_workout(self, workout_id: str) -> bool:
        """Supprime workout."""

    def upload_workout(self, date: str, code: str, structure: str) -> bool:
        """Upload nouveau workout."""
```

**Bénéfices**:
- ✅ Encapsule logique API
- ✅ Cache/retry logic centralisé
- ✅ Mock facile pour tests

**Localisation**: `cyclisme_training_logs/api/intervals_helper.py`

---

#### 1.4 `ActivityDetector` (Détection)
```python
class ActivityDetector:
    """Détecte gaps planning/activités."""

    def detect_unanalyzed_activities(self) -> list:
        """Activités non analysées."""

    def detect_skipped_sessions(self, week_id: str) -> list:
        """Sessions sautées."""

    def filter_documented_sessions(self, sessions: list) -> list:
        """Filtre sessions documentées."""

    def detect_rest_and_cancelled(self, week_id: str) -> tuple:
        """Repos et annulations."""
```

**Bénéfices**:
- ✅ Logique détection centralisée
- ✅ Réutilisable (daily-sync, etc.)
- ✅ Tests ciblés

**Localisation**: `cyclisme_training_logs/planning/activity_detector.py`

---

### Phase 2: Simplification WorkflowCoach

Après extraction, `WorkflowCoach` devient :

```python
class WorkflowCoach:
    """Orchestrateur workflow (logique métier pure)."""

    def __init__(self, ...):
        self.ui = ConsoleUI()
        self.planning_modifier = PlanningModifier()
        self.api_helper = IntervalsAPIHelper(...)
        self.detector = ActivityDetector()
        # ...

    def run(self):
        """Workflow principal."""
        self.step_1_welcome()
        self.step_2_detect_gaps()
        self.step_3_collect_feedback()
        self.step_4_analyze()
        self.step_5_insert()
        self.step_6_commit()

    # Méthodes workflow uniquement (orchestration)
```

**Résultat estimé**:
- WorkflowCoach : ~1000-1500 lignes (vs 3669)
- 5 classes helpers : ~500 lignes chacune
- **Couverture totale visée**: 70-80%

---

### Phase 3: Tests

Une fois refactoré, les tests deviennent **simples** :

```python
# Test ConsoleUI (pur, sans dépendances)
def test_print_header():
    ui = ConsoleUI()
    output = ui.print_header("Test", "Subtitle")
    assert "Test" in output

# Test PlanningModifier (logique métier isolée)
def test_apply_lighten():
    modifier = PlanningModifier()
    session = {...}
    result = modifier.apply_lighten(session, 20)
    assert result["tss_planned"] == 40  # 50 * 0.8

# Test ActivityDetector (détection pure)
def test_detect_skipped_sessions():
    detector = ActivityDetector()
    skipped = detector.detect_skipped_sessions("S081")
    assert len(skipped) == 2
```

---

## 📅 Plan d'Exécution

### Priorité 1 (Critique)
1. ✅ Extraire `PlanningModifier` (réutilisé par daily-sync, API)
2. ✅ Extraire `ActivityDetector` (réutilisé partout)

**Impact**: 40-50% réduction taille workflow_coach.py

### Priorité 2 (Important)
3. ✅ Extraire `ConsoleUI` (UI/logique découplée)
4. ✅ Extraire `IntervalsAPIHelper` (cache/retry centralisé)

**Impact**: 60-70% réduction taille workflow_coach.py

### Priorité 3 (Amélioration)
5. ⏸️ Simplifier `reconcile_week()` (210 lignes → 50 lignes)
6. ⏸️ Tests unitaires classes helpers (facile)
7. ⏸️ Tests intégration WorkflowCoach (orchestration)

---

## 🎁 Bénéfices Attendus

### Avant Refactoring
- workflow_coach.py : 3669 lignes
- 1 classe God Class
- 62 méthodes
- Tests difficiles (dépendances complexes)
- Couverture : 49%

### Après Refactoring
- workflow_coach.py : ~1200 lignes ✅
- 6 classes bien séparées ✅
- ~15 méthodes par classe (moyenne) ✅
- Tests faciles (SRP respected) ✅
- Couverture visée : 75-80% ✅

### Réutilisabilité
- `PlanningModifier` → Utilisé par daily-sync, API, CLI
- `ActivityDetector` → Utilisé par daily-sync, end-of-week
- `ConsoleUI` → Utilisé par tous les scripts CLI
- `IntervalsAPIHelper` → Utilisé partout

---

## ⚠️ Risques & Mitigation

### Risque 1: Breaking Changes
**Mitigation**:
- Garder workflow_coach.py API publique inchangée
- Refactoring interne uniquement
- Tests de régression

### Risque 2: Temps Investissement
**Estimation**: 4-6 heures de refactoring
**Mitigation**:
- Phase 1 d'abord (impact maximum)
- Phase 2-3 si temps disponible

### Risque 3: Nouveaux Bugs
**Mitigation**:
- Tests unitaires systématiques
- Tests intégration existants passent
- Review code ligne par ligne

---

## 🚀 Recommandation

**Action immédiate**: Commencer Phase 1 (PlanningModifier + ActivityDetector)

**Raisons**:
1. Impact maximal (40-50% réduction)
2. Réutilisabilité immédiate (daily-sync, API)
3. Tests faciles après extraction
4. Pas de breaking changes

**Alternative**: Continuer tests actuels workflow_coach.py
- ❌ Tests complexes (dépendances)
- ❌ Couverture partielle (max 60%)
- ❌ Dette technique persiste
- ❌ Maintenance difficile

---

## 📝 Notes

Cette analyse montre que **refactorer d'abord** est plus rentable que **tester le code actuel**.

Le ratio effort/bénéfice du refactoring est **bien meilleur** :
- Refactoring : 4-6h → Code maintenable + Tests faciles + Réutilisabilité
- Tests actuels : 3-4h → Couverture 60% + Dette persiste + Tests fragiles
