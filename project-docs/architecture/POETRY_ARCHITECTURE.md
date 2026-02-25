# Architecture Poetry - Contexte Technique Complet

## Configuration Poetry Actuelle

### pyproject.toml - Scripts Configurés
```toml
[tool.poetry.scripts]
workflow-coach = "cyclisme_training_logs.workflow_coach:main"
weekly-analysis = "cyclisme_training_logs.weekly_analysis:main"
upload-workouts = "cyclisme_training_logs.upload_workouts:main"
prepare-analysis = "cyclisme_training_logs.prepare_analysis:main"
collect-athlete-feedback = "cyclisme_training_logs.collect_athlete_feedback:main"
sync-intervals = "cyclisme_training_logs.sync_intervals:main"
stats = "cyclisme_training_logs.stats:main"
planned-checker = "cyclisme_training_logs.planned_sessions_checker:main"
insert-analysis = "cyclisme_training_logs.insert_analysis:main"
organize-report = "cyclisme_training_logs.organize_report:main"
setup-week = "cyclisme_training_logs.setup_week:main"
check-rest = "cyclisme_training_logs.rest_and_cancellations:main"
validate-state = "cyclisme_training_logs.workout_state:main"
gen-week = "cyclisme_training_logs.generate_week_workouts:main"
intervals-api = "cyclisme_training_logs.intervals_api:main"
```

## Package cyclisme_training_logs/

### Structure (33 modules Python)
```
cyclisme_training_logs/
├── __init__.py
├── workflow_coach.py           # ⭐ ORCHESTRATEUR PRINCIPAL
├── intervals_api.py            # Client API Intervals.icu
├── weekly_analysis.py
├── upload_workouts.py
└── ... (28 autres modules)
```

## Patterns Imports - OBLIGATOIRES

### ✅ Correct
```python
from cyclisme_training_logs.intervals_api import IntervalsAPI
from cyclisme_training_logs.workout_state import WorkoutState
```

### ❌ Incorrect
```python
from intervals_api import IntervalsAPI        # ❌
from .intervals_api import IntervalsAPI      # ❌
```

## Gestion Paths
```python
from pathlib import Path

class WorkflowCoach:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.data_dir = self.project_root / "data"
        self.planning_dir = self.data_dir / "week_planning"
```

## Configuration API

**Fichier** : `~/.intervals_config.json`
```json
{
  "athlete_id": "iXXXXXX",
  "api_key": "your_api_key_here"
}
```

## Client API - Référence

Voir `cyclisme_training_logs/intervals_api.py` pour patterns complets.

### Endpoints Principaux
```python
# GET événements
events = api.get_events(oldest="2025-12-16", newest="2025-12-22", category="WORKOUT")

# DELETE événement
success = api.delete_event(event_id="12345")

# POST événement
event = api.create_event({
    "category": "WORKOUT",
    "start_date_local": "2025-12-18T08:00:00",
    "name": "S072-03-REC-RecuperationActive-V001",
    "workout_doc": "Warmup\n- 10m ramp 50-60%..."
})
```

## Gestion Erreurs
```python
try:
    response = self.session.delete(url)
    response.raise_for_status()
    return True
except requests.exceptions.RequestException as e:
    print(f"❌ Erreur API : {e}")
    return False
```

## Tests
```bash
# Tous tests
poetry run pytest

# Tests spécifiques
poetry run pytest tests/test_asservissement.py -v

# Avec couverture
poetry run pytest --cov=cyclisme_training_logs
```

## Commandes Utiles
```bash
# Exécuter script
poetry run workflow-coach    # ou alias: train

# Info environnement
poetry env info --path
poetry env list

# Dépendances
poetry show --tree
```

## Points Critiques

### ❌ À Éviter
- Imports relatifs
- Paths absolus hardcodés
- Oublier try/except API
- Créer nouveau script Poetry

### ✅ À Faire
- Imports absolus package
- Paths relatifs pathlib
- Gestion erreurs complète
- Intégrer dans workflow_coach.py

---

**Référence complète pour intégration système asservissement**
