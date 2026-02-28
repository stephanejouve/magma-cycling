# Guide Planification Entraînement

Guide complet du système de planification (Sprint R3).

## 📋 Table des Matières

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Planning Manager](#planning-manager)
4. [Training Calendar](#training-calendar)
5. [Exemples Complets](#exemples-complets)
6. [Contraintes Master Athletes](#contraintes-master-athletes)
7. [API Reference](#api-reference)

## Introduction

Le module `planning` fournit deux composants principaux :

- **PlanningManager** : Gestion de plans d'entraînement (4-12 semaines)
- **TrainingCalendar** : Calendrier hebdomadaire avec séances et repos

### Architecture

```
planning/
├── planning_manager.py  # Plans, objectifs, validation
├── calendar.py          # Calendrier ISO, séances, summaries
└── __init__.py          # Exports publics
```

**Caractéristiques** :
- 100% in-memory (Dict storage)
- Intégration `AthleteProfile` (config.py)
- ISO week handling (semaines 1-53)
- Contraintes master/senior athletes

## Installation

Le module est déjà installé avec le package :

```bash
poetry install
```

### Configuration Profil Athlète

Créer/éditer `.env` :

```bash
# Profil athlète
ATHLETE_AGE=54
ATHLETE_CATEGORY=master  # ou senior
ATHLETE_FTP=220
ATHLETE_WEIGHT=83.8
ATHLETE_RECOVERY_CAPACITY=good  # good/average/poor
ATHLETE_SLEEP_DEPENDENT=true    # true/false
```

## Planning Manager

### Création de Plan

```python
from datetime import date
from magma_cycling.planning import PlanningManager

# Initialiser
manager = PlanningManager()

# Créer plan 8 semaines
plan = manager.create_training_plan(
    name="Build Printemps 2026",
    start_date=date(2026, 3, 1),
    end_date=date(2026, 4, 26),  # 8 semaines
    weekly_tss_targets=[250, 270, 290, 310, 320, 300, 280, 250],
    notes="Phase build progressive avec taper final"
)

print(f"Plan créé : {plan.name}")
print(f"Durée : {plan.duration_weeks()} semaines")
```

### Ajout d'Objectifs

```python
from magma_cycling.planning import PriorityLevel, ObjectiveType

# Objectif principal (événement)
objective1 = manager.add_deadline(
    plan_name="Build Printemps 2026",
    deadline_date=date(2026, 5, 10),
    event_name="Gran Fondo Alpes",
    priority=PriorityLevel.HIGH,
    objective_type=ObjectiveType.EVENT,
    notes="180km / 3500m D+"
)

# Objectif FTP intermédiaire
objective2 = manager.add_deadline(
    plan_name="Build Printemps 2026",
    deadline_date=date(2026, 4, 15),
    event_name="Test FTP",
    priority=PriorityLevel.MEDIUM,
    objective_type=ObjectiveType.FTP_TARGET,
    target_value=230.0,  # Objectif 230W
    current_value=220.0,  # Actuel 220W
    notes="Test 20min après 3 semaines build"
)

print(f"Progression FTP : {objective2.progress_percent():.1f}%")
```

### Timeline et Milestones

```python
# Récupérer timeline complète
timeline = manager.get_plan_timeline("Build Printemps 2026")

print(f"Plan : {timeline['plan_summary']['name']}")
print(f"Objectifs : {timeline['plan_summary']['total_objectives']}")
print(f"Dates critiques : {len(timeline['critical_dates'])}")

# Afficher deadlines
for deadline in timeline['deadlines']:
    print(f"  - {deadline['date']} : {deadline['name']} [{deadline['priority']}]")
    print(f"    Jours restants : {deadline['days_remaining']}")

# Afficher breakdown hebdomadaire
for week in timeline['weeks_breakdown']:
    print(f"Semaine {week['week_num']} : TSS {week['target_tss']}")
    if week['objectives']:
        for obj in week['objectives']:
            print(f"  → {obj}")
```

### Validation Faisabilité

```python
# Valider plan vs profil athlète
validation = manager.validate_plan_feasibility(
    plan_name="Build Printemps 2026",
    current_ctl=55.0  # CTL actuel
)

print(f"✅ Faisable : {validation['feasible']}")

# Erreurs (bloquantes)
if validation['errors']:
    print("\n❌ ERREURS :")
    for error in validation['errors']:
        print(f"  - {error}")

# Warnings (non-bloquants)
if validation['warnings']:
    print("\n⚠️  WARNINGS :")
    for warning in validation['warnings']:
        print(f"  - {warning}")

# Recommandations
print("\n💡 RECOMMANDATIONS :")
for rec in validation['recommendations']:
    print(f"  - {rec}")
```

**Critères de validation** :
- Durée : 4-12 semaines
- TSS hebdomadaire : max 380 (master) / 450 (senior)
- Rampe CTL : max 7 points/semaine (master) / 10 (senior)
- Nombre d'objectifs CRITICAL/HIGH : recommandé < 3

## Training Calendar

### Génération Calendrier Hebdomadaire

```python
from magma_cycling.planning import TrainingCalendar

# Initialiser calendrier 2026
calendar = TrainingCalendar(year=2026)

# Générer semaine 3 (ISO week)
week_dates = calendar.generate_weekly_calendar(week_num=3)

print(f"Semaine 3/2026 :")
for i, day in enumerate(week_dates):
    day_name = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"][i]
    print(f"  {day_name} {day.strftime('%d/%m')}")
```

**ISO Week Rules** :
- Semaine 1 contient toujours le 4 janvier
- Semaines 1-53
- Lundi = jour 0, Dimanche = jour 6

### Configuration Jours de Repos

```python
# Master athlete : dimanche obligatoire (défaut)
print(f"Repos configurés : {calendar.rest_days}")  # [6]

# Ajouter mercredi
calendar.mark_rest_days([3, 6])  # Mercredi + Dimanche
print(f"Repos mis à jour : {calendar.rest_days}")  # [3, 6]

# Réinitialiser (dimanche uniquement pour master)
calendar.mark_rest_days()
```

### Ajout de Séances

```python
from magma_cycling.planning import WorkoutType

# Séance endurance (lundi)
session1 = calendar.add_session(
    session_date=date(2026, 1, 12),  # Lundi semaine 3
    workout_type=WorkoutType.ENDURANCE,
    planned_tss=60.0,
    duration_min=90,
    intensity_pct=70.0,
    notes="Z2 base, FC < 145"
)

# Séance threshold (mercredi)
session2 = calendar.add_session(
    session_date=date(2026, 1, 14),  # Mercredi semaine 3
    workout_type=WorkoutType.THRESHOLD,
    planned_tss=85.0,
    duration_min=90,
    intensity_pct=95.0,
    notes="3x10min FTP @ 95%"
)

# ❌ ERREUR : séance sur jour de repos
try:
    calendar.add_session(
        session_date=date(2026, 1, 18),  # Dimanche (repos)
        workout_type=WorkoutType.ENDURANCE,
        planned_tss=50.0
    )
except ValueError as e:
    print(f"Erreur : {e}")
    # Erreur : Cannot add session on Sunday (2026-01-18): configured as rest day
```

### Résumé Hebdomadaire

```python
# Récupérer summary semaine 3
summary = calendar.get_week_summary(week_num=3)

print(f"Semaine {summary.week_num} ({summary.start_date} → {summary.end_date})")
print(f"TSS total : {summary.total_tss:.1f}")
print(f"Séances : {summary.sessions_count}")
print(f"Repos : {summary.rest_days_count}")
print(f"Intensité moy : {summary.avg_intensity:.1f}%")

# TSS par type
print("\nTSS par type :")
for workout_type, tss in summary.tss_by_type.items():
    print(f"  {workout_type} : {tss:.1f}")
```

### Marquer Séance Réalisée

```python
# Récupérer séance
session = calendar.sessions[date(2026, 1, 12)]

# Marquer comme complétée (TSS réel)
session.completed = True
session.actual_tss = 58.0  # TSS réel (vs 60 planifié)

print(f"TSS effectif : {session.get_effective_tss()}")  # 58.0 (réel)

# Le summary utilisera TSS réel
summary = calendar.get_week_summary(week_num=3)
print(f"TSS total (avec réel) : {summary.total_tss}")  # 58.0 + 85.0 = 143.0
```

## Exemples Complets

### Exemple 1 : Plan 8 Semaines Build

```python
from datetime import date
from magma_cycling.planning import (
    PlanningManager, TrainingCalendar,
    PriorityLevel, ObjectiveType, WorkoutType
)

# 1. Créer plan
manager = PlanningManager()
plan = manager.create_training_plan(
    name="Build Base Hiver",
    start_date=date(2026, 1, 12),  # Semaine 3
    end_date=date(2026, 3, 8),     # Semaine 10 (8 semaines)
    weekly_tss_targets=[250, 270, 290, 310, 320, 310, 300, 280],
    notes="Build progressif Z2/Z3 avec pics FTP semaines 5-6"
)

# 2. Ajouter objectifs
manager.add_deadline(
    plan_name="Build Base Hiver",
    deadline_date=date(2026, 2, 16),  # Semaine 7
    event_name="Test FTP",
    priority=PriorityLevel.CRITICAL,
    objective_type=ObjectiveType.FTP_TARGET,
    target_value=230.0,
    current_value=220.0
)

manager.add_deadline(
    plan_name="Build Base Hiver",
    deadline_date=date(2026, 3, 8),  # Fin plan
    event_name="Checkpoint CTL",
    priority=PriorityLevel.MEDIUM,
    objective_type=ObjectiveType.CTL_TARGET,
    target_value=75.0,
    current_value=55.0
)

# 3. Valider faisabilité
validation = manager.validate_plan_feasibility("Build Base Hiver", current_ctl=55.0)
if not validation['feasible']:
    print("⚠️  PLAN NON FAISABLE !")
    for error in validation['errors']:
        print(f"  - {error}")
else:
    print("✅ Plan validé")

# 4. Planifier semaine 3 (première semaine)
calendar = TrainingCalendar(year=2026)
calendar.mark_rest_days([6])  # Dimanche repos

# Lundi : Endurance longue
calendar.add_session(
    date(2026, 1, 12), WorkoutType.ENDURANCE, 80.0, 120, 68.0,
    "Z2 sortie longue 2h"
)

# Mercredi : Tempo
calendar.add_session(
    date(2026, 1, 14), WorkoutType.TEMPO, 75.0, 90, 85.0,
    "3x15min Z3 @ 85%"
)

# Vendredi : Threshold
calendar.add_session(
    date(2026, 1, 16), WorkoutType.THRESHOLD, 85.0, 90, 95.0,
    "4x8min FTP @ 95-100%"
)

# Samedi : Endurance récup
calendar.add_session(
    date(2026, 1, 17), WorkoutType.ENDURANCE, 50.0, 75, 65.0,
    "Récupération active Z2"
)

# 5. Vérifier summary
summary = calendar.get_week_summary(week_num=3)
print(f"\nSemaine {summary.week_num} :")
print(f"  TSS planifié : {summary.total_tss} (objectif: 250)")
print(f"  Séances : {summary.sessions_count}")
print(f"  Intensité moyenne : {summary.avg_intensity:.1f}%")

if summary.total_tss > 260:
    print("  ⚠️  TSS trop élevé pour semaine 1")
```

### Exemple 2 : Timeline Complète

```python
# Récupérer timeline
timeline = manager.get_plan_timeline("Build Base Hiver")

# Affichage formaté
print(f"📅 PLAN : {timeline['plan_summary']['name']}")
print(f"📆 Durée : {timeline['plan_summary']['duration_weeks']} semaines")
print(f"🎯 Objectifs : {timeline['plan_summary']['total_objectives']}")
print()

# Dates critiques
if timeline['critical_dates']:
    print("🚨 DATES CRITIQUES :")
    for critical in timeline['critical_dates']:
        print(f"  {critical['date']} : {critical['name']}")
    print()

# Breakdown hebdomadaire
print("📊 BREAKDOWN HEBDOMADAIRE :")
for week in timeline['weeks_breakdown']:
    print(f"  Semaine {week['week_num']} : {week['target_tss']} TSS")
    if week['objectives']:
        for obj in week['objectives']:
            print(f"    → {obj}")
```

## Contraintes Master Athletes

Les athlètes master (54 ans) ont des contraintes spécifiques :

### TSS Hebdomadaire

```python
# Master : max 380 TSS/semaine
weekly_tss_targets = [250, 270, 290, 310, 320, 300, 280, 250]  # ✅ OK

# ❌ ERREUR : > 380
weekly_tss_targets = [400, 420, 440, 460]  # Warning lors de validate_plan_feasibility()
```

### Rampe CTL

```python
# Master : max +7 points/semaine
# Exemple : CTL 55 → 62 en 1 semaine = OK
# CTL 55 → 70 en 1 semaine = ❌ ERREUR (15 points)

validation = manager.validate_plan_feasibility(
    plan_name="Mon Plan",
    current_ctl=55.0
)

# Si rampe excessive :
# validation['feasible'] == False
# validation['errors'] == ["CTL ramp rate (15.0 points/week) exceeds safe limit (7.0)"]
```

### Jour de Repos Obligatoire

```python
# Master : dimanche (jour 6) OBLIGATOIRE
calendar = TrainingCalendar(year=2026)  # athlete_profile.category == "master"
print(calendar.rest_days)  # [6] (dimanche configuré automatiquement)

# Tentative ajout séance dimanche → ValueError
try:
    calendar.add_session(
        date(2026, 1, 18),  # Dimanche
        WorkoutType.ENDURANCE,
        50.0
    )
except ValueError as e:
    print(f"Bloqué : {e}")
```

### Récupération

- **Sommeil** : `ATHLETE_SLEEP_DEPENDENT=true`
- **Capacité** : `ATHLETE_RECOVERY_CAPACITY=good`
- Impact sur `assess_overtraining_risk()` (Sprint R2.1)

## API Reference

### PlanningManager

```python
class PlanningManager:
    def __init__(self, athlete_profile: Optional[AthleteProfile] = None)

    def create_training_plan(
        self,
        name: str,
        start_date: date,
        end_date: date,
        objectives: List[TrainingObjective] = [],
        weekly_tss_targets: List[float] = [],
        notes: str = ""
    ) -> TrainingPlan

    def add_deadline(
        self,
        plan_name: str,
        deadline_date: date,
        event_name: str,
        priority: PriorityLevel,
        objective_type: ObjectiveType = ObjectiveType.EVENT,
        target_value: Optional[float] = None,
        current_value: Optional[float] = None,
        notes: str = ""
    ) -> TrainingObjective

    def get_plan_timeline(self, plan_name: str) -> Dict[str, Any]

    def validate_plan_feasibility(
        self,
        plan_name: str,
        current_ctl: float = 0.0
    ) -> Dict[str, Any]
```

### TrainingCalendar

```python
class TrainingCalendar:
    def __init__(
        self,
        year: int,
        start_week: int = 1,
        athlete_profile: Optional[AthleteProfile] = None
    )

    def generate_weekly_calendar(self, week_num: int) -> List[date]

    def mark_rest_days(self, days: Optional[List[int]] = None) -> None

    def add_session(
        self,
        session_date: date,
        workout_type: WorkoutType,
        planned_tss: float,
        duration_min: int = 60,
        intensity_pct: float = 70.0,
        notes: str = ""
    ) -> TrainingSession

    def get_week_summary(self, week_num: int) -> WeeklySummary
```

### Enums

```python
class PriorityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ObjectiveType(Enum):
    EVENT = "event"
    FTP_TARGET = "ftp_target"
    CTL_TARGET = "ctl_target"
    WEIGHT_TARGET = "weight_target"
    MILESTONE = "milestone"

class WorkoutType(Enum):
    ENDURANCE = "endurance"
    TEMPO = "tempo"
    THRESHOLD = "threshold"
    VO2MAX = "vo2max"
    RECOVERY = "recovery"
    REST = "rest"
```

### Dataclasses

```python
@dataclass
class TrainingObjective:
    name: str
    target_date: date
    objective_type: ObjectiveType
    priority: PriorityLevel
    target_value: Optional[float] = None
    current_value: Optional[float] = None
    notes: str = ""

    def progress_percent(self) -> Optional[float]
    def days_remaining(self, from_date: date = None) -> int

@dataclass
class TrainingPlan:
    name: str
    start_date: date
    end_date: date
    objectives: List[TrainingObjective] = field(default_factory=list)
    athlete_profile: Optional[AthleteProfile] = None
    weekly_tss_targets: List[float] = field(default_factory=list)
    notes: str = ""

    def duration_weeks(self) -> int
    def get_objectives_by_priority(self, priority: PriorityLevel) -> List[TrainingObjective]
    def to_dict(self) -> Dict[str, Any]

@dataclass
class TrainingSession:
    date: date
    workout_type: WorkoutType
    planned_tss: float
    duration_min: int = 60
    intensity_pct: float = 70.0
    completed: bool = False
    actual_tss: Optional[float] = None
    notes: str = ""

    def get_effective_tss(self) -> float
    def to_dict(self) -> Dict[str, Any]

@dataclass
class WeeklySummary:
    week_num: int
    year: int
    start_date: date
    end_date: date
    total_tss: float = 0.0
    sessions_count: int = 0
    rest_days_count: int = 0
    tss_by_type: Dict[str, float] = field(default_factory=dict)
    avg_intensity: float = 0.0

    def to_dict(self) -> Dict[str, Any]
```

## Tests

Le module planning inclut 41 tests unitaires :

```bash
# Tests planning_manager (21 tests)
poetry run pytest tests/planning/test_planning_manager.py -v

# Tests calendar (20 tests)
poetry run pytest tests/planning/test_calendar.py -v

# Tous les tests planning
poetry run pytest tests/planning/ -v
```

**Couverture** : 100% des fonctions principales

## Troubleshooting

### Erreur : "Plan duration too short"

```python
# ❌ ERREUR
plan = manager.create_training_plan(
    "Mon Plan",
    date(2026, 1, 1),
    date(2026, 1, 14)  # Seulement 2 semaines
)
# ValueError: Plan duration too short (2 weeks). Minimum: 4 weeks
```

**Solution** : Plans doivent durer 4-12 semaines.

### Erreur : "CTL ramp rate exceeds safe limit"

```python
# Plan trop agressif pour master athlete
validation = manager.validate_plan_feasibility("Mon Plan", current_ctl=40.0)
# validation['feasible'] == False
# validation['errors'] == ["CTL ramp rate (18.0 points/week) exceeds safe limit (7.0)"]
```

**Solution** : Réduire TSS hebdomadaires ou augmenter durée plan.

### Erreur : "Cannot add session on rest day"

```python
# Tentative ajout séance sur dimanche (master athlete)
calendar.add_session(date(2026, 1, 18), WorkoutType.ENDURANCE, 50.0)
# ValueError: Cannot add session on Sunday (2026-01-18): configured as rest day
```

**Solution** : Changer date ou modifier `calendar.rest_days`.

### Erreur : "Invalid week_num"

```python
calendar.generate_weekly_calendar(week_num=54)
# ValueError: Invalid week_num: 54 (must be 1-53)
```

**Solution** : ISO weeks vont de 1 à 53 (certaines années n'ont que 52).

---

**Version Guide :** 1.0
**Sprint :** R3 - Planning Manager & Calendar
**Date :** 2026-01-01
**Tests :** 41/41 passing (100%)
