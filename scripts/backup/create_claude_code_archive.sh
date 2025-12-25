#!/bin/bash

# Script de création d'archive complète pour Claude Code
# Projet: Système d'Asservissement Coach AI Cyclisme
# Version: 2.0 avec architecture Poetry complète

set -e  # Exit on error

cd ~/cyclisme-training-logs

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
ARCHIVE_DIR="/tmp/claude-code-context_${TIMESTAMP}"

echo "=== Création structure archive ==="
mkdir -p "${ARCHIVE_DIR}"

echo "=== Copie fichiers racine ==="
cp pyproject.toml "${ARCHIVE_DIR}/"
cp poetry.lock "${ARCHIVE_DIR}/"
cp .gitignore "${ARCHIVE_DIR}/"
cp README.md "${ARCHIVE_DIR}/"
cp COMMANDS.md "${ARCHIVE_DIR}/"
cp ALIASES.md "${ARCHIVE_DIR}/"

echo "=== Copie modules Python ==="
mkdir -p "${ARCHIVE_DIR}/cyclisme_training_logs"
cp cyclisme_training_logs/*.py "${ARCHIVE_DIR}/cyclisme_training_logs/"

echo "=== Copie logs ==="
mkdir -p "${ARCHIVE_DIR}/logs"
cp logs/workouts-history.md "${ARCHIVE_DIR}/logs/" 2>/dev/null || echo "⚠️  workouts-history.md absent"

mkdir -p "${ARCHIVE_DIR}/logs/weekly_reports/S070"
cp logs/weekly_reports/S070/*.md "${ARCHIVE_DIR}/logs/weekly_reports/S070/" 2>/dev/null || echo "⚠️  S070 absent"

mkdir -p "${ARCHIVE_DIR}/logs/weekly_reports/S071"
cp logs/weekly_reports/S071/*.md "${ARCHIVE_DIR}/logs/weekly_reports/S071/" 2>/dev/null || echo "⚠️  S071 absent"

echo "=== Création exemples structures ==="
mkdir -p "${ARCHIVE_DIR}/examples/planning"
mkdir -p "${ARCHIVE_DIR}/examples/templates"

cat > "${ARCHIVE_DIR}/examples/planning/example_week_planning.json" << 'EOFPLANNING'
{
  "week_id": "S072",
  "start_date": "2025-12-16",
  "end_date": "2025-12-22",
  "created_at": "2025-12-15T10:00:00",
  "last_updated": "2025-12-15T10:00:00",
  "version": 1,
  "sessions": [
    {
      "day": "2025-12-16",
      "workout_code": "S072-01-INT-SweetSpot-V001",
      "type": "INT",
      "tss_planned": 60,
      "description": "Sweet-Spot 3x10min 88-90% FTP",
      "status": "planned",
      "history": []
    },
    {
      "day": "2025-12-17",
      "workout_code": "S072-02-END-EnduranceBase-V001",
      "type": "END",
      "tss_planned": 45,
      "description": "Endurance 60min Z2",
      "status": "planned",
      "history": []
    },
    {
      "day": "2025-12-18",
      "workout_code": "S072-03-END-EnduranceProgressive-V001",
      "type": "END",
      "tss_planned": 50,
      "description": "Endurance progressive 65min",
      "status": "planned",
      "history": []
    },
    {
      "day": "2025-12-19",
      "workout_code": "S072-04-INT-SweetSpotCourt-V001",
      "type": "INT",
      "tss_planned": 55,
      "description": "Sweet-Spot 2x12min",
      "status": "planned",
      "history": []
    },
    {
      "day": "2025-12-20",
      "workout_code": "S072-05-REC-RecuperationActive-V001",
      "type": "REC",
      "tss_planned": 30,
      "description": "Récupération active 45min",
      "status": "planned",
      "history": []
    },
    {
      "day": "2025-12-21",
      "workout_code": "S072-06-INT-VO2MaxCourt-V001",
      "type": "INT",
      "tss_planned": 65,
      "description": "VO2 Max 5x3min 106% FTP",
      "status": "planned",
      "history": []
    },
    {
      "day": "2025-12-22",
      "workout_code": "REPOS",
      "type": "REST",
      "tss_planned": 0,
      "description": "Repos hebdomadaire obligatoire",
      "status": "rest_day",
      "history": []
    }
  ]
}
EOFPLANNING

cat > "${ARCHIVE_DIR}/examples/templates/recovery_active_30tss.json" << 'EOFTEMPLATE1'
{
  "id": "recovery_active_30tss",
  "name": "Récupération Active 30 TSS",
  "type": "REC",
  "tss": 30,
  "duration_minutes": 45,
  "description": "Récupération active 45min Z1-Z2",
  "workout_code_pattern": "{week_id}-{day_num:02d}-REC-RecuperationActive-V001",
  "intervals_icu_format": "Warmup\n- 10m ramp 50-60% 85rpm\n\nMain set\n- 25m 60% 85rpm cadence libre\n\nCooldown\n- 10m ramp 60-50% 85rpm",
  "use_cases": ["lighten_from_endurance", "lighten_from_sweetspot", "emergency_recovery"],
  "prerequisites": {
    "min_tsb": -15,
    "max_tsb": 999,
    "min_hrv_drop": -20,
    "max_hrv_drop": 0
  }
}
EOFTEMPLATE1

cat > "${ARCHIVE_DIR}/examples/templates/recovery_active_25tss.json" << 'EOFTEMPLATE2'
{
  "id": "recovery_active_25tss",
  "name": "Récupération Active 25 TSS",
  "type": "REC",
  "tss": 25,
  "duration_minutes": 40,
  "description": "Récupération active 40min Z1",
  "workout_code_pattern": "{week_id}-{day_num:02d}-REC-RecuperationCourte-V001",
  "intervals_icu_format": "Warmup\n- 8m ramp 45-55% 85rpm\n\nMain set\n- 24m 55% 85rpm cadence libre\n\nCooldown\n- 8m ramp 55-45% 85rpm",
  "use_cases": ["lighten_from_endurance_base", "recovery_between_intensity"],
  "prerequisites": {
    "min_tsb": -20,
    "max_tsb": 999
  }
}
EOFTEMPLATE2

cat > "${ARCHIVE_DIR}/examples/templates/recovery_short_20tss.json" << 'EOFTEMPLATE3'
{
  "id": "recovery_short_20tss",
  "name": "Récupération Courte 20 TSS",
  "type": "REC",
  "tss": 20,
  "duration_minutes": 30,
  "description": "Récupération courte 30min Z1",
  "workout_code_pattern": "{week_id}-{day_num:02d}-REC-RecuperationUltraLegere-V001",
  "intervals_icu_format": "Warmup\n- 5m ramp 45-50% 85rpm\n\nMain set\n- 20m 50% 85rpm cadence libre\n\nCooldown\n- 5m ramp 50-45% 85rpm",
  "use_cases": ["emergency_recovery", "extreme_fatigue", "hrv_drop_severe"],
  "prerequisites": {
    "min_tsb": -25,
    "max_tsb": 999,
    "min_hrv_drop": -25,
    "max_hrv_drop": -10
  }
}
EOFTEMPLATE3

cat > "${ARCHIVE_DIR}/examples/templates/endurance_light_35tss.json" << 'EOFTEMPLATE4'
{
  "id": "endurance_light_35tss",
  "name": "Endurance Légère 35 TSS",
  "type": "END",
  "tss": 35,
  "duration_minutes": 50,
  "description": "Endurance légère 50min Z2 bas",
  "workout_code_pattern": "{week_id}-{day_num:02d}-END-EnduranceLegere-V001",
  "intervals_icu_format": "Warmup\n- 10m ramp 50-65% 85rpm\n\nMain set\n- 30m 65% 85-90rpm cadence libre\n\nCooldown\n- 10m ramp 65-50% 85rpm",
  "use_cases": ["lighten_from_endurance_normal", "maintain_volume_reduce_load"],
  "prerequisites": {
    "min_tsb": -10,
    "max_tsb": 999
  }
}
EOFTEMPLATE4

cat > "${ARCHIVE_DIR}/examples/templates/endurance_short_40tss.json" << 'EOFTEMPLATE5'
{
  "id": "endurance_short_40tss",
  "name": "Endurance Courte 40 TSS",
  "type": "END",
  "tss": 40,
  "duration_minutes": 55,
  "description": "Endurance courte 55min Z2",
  "workout_code_pattern": "{week_id}-{day_num:02d}-END-EnduranceCourte-V001",
  "intervals_icu_format": "Warmup\n- 10m ramp 50-70% 85rpm\n\nMain set\n- 35m 70% 85-90rpm cadence libre\n\nCooldown\n- 10m ramp 70-50% 85rpm",
  "use_cases": ["lighten_from_sweetspot", "reduce_volume_maintain_quality"],
  "prerequisites": {
    "min_tsb": -5,
    "max_tsb": 999
  }
}
EOFTEMPLATE5

cat > "${ARCHIVE_DIR}/examples/templates/sweetspot_short_50tss.json" << 'EOFTEMPLATE6'
{
  "id": "sweetspot_short_50tss",
  "name": "Sweet-Spot Court 50 TSS",
  "type": "INT",
  "tss": 50,
  "duration_minutes": 50,
  "description": "Sweet-Spot court 2x10min 88-90% FTP",
  "workout_code_pattern": "{week_id}-{day_num:02d}-INT-SweetSpotCourt-V001",
  "intervals_icu_format": "Warmup\n- 10m ramp 50-75% 85rpm\n- 5m 75% 90rpm\n\nMain set 2x\n- 10m 90% 90rpm\n- 4m 60% 85rpm\n\nCooldown\n- 10m ramp 65-50% 85rpm",
  "use_cases": ["lighten_from_sweetspot_long", "lighten_from_vo2", "maintain_quality_reduce_volume"],
  "prerequisites": {
    "min_tsb": 0,
    "max_tsb": 999,
    "min_hrv_drop": -10,
    "max_hrv_drop": 5
  }
}
EOFTEMPLATE6

echo "=== Création documentation complète ==="

cat > "${ARCHIVE_DIR}/POETRY_ARCHITECTURE.md" << 'EOFPOETRY'
# Architecture Poetry - Contexte Technique Complet

## Configuration Poetry Actuelle

### pyproject.toml
```toml
[tool.poetry]
name = "cyclisme-training-logs"
version = "0.1.0"
description = "Système automatisé d'analyse d'entraînement cyclisme"

[tool.poetry.dependencies]
python = "^3.11"
anthropic = "^0.39.0"
requests = "^2.32.3"
python-dotenv = "^1.0.1"

[tool.poetry.scripts]
workflow-coach = "cyclisme_training_logs.workflow_coach:main"
weekly-analysis = "cyclisme_training_logs.weekly_analysis:main"
upload-workouts = "cyclisme_training_logs.upload_workouts:main"
# ... 12 autres scripts
```

## Package cyclisme_training_logs/

### Structure (33 modules)
```
cyclisme_training_logs/
├── __init__.py
├── workflow_coach.py           # ⭐ À MODIFIER (~350 lignes)
├── intervals_api.py            # Référence API
├── weekly_analysis.py
└── ... (30 autres modules)
```

## Patterns Imports - À SUIVRE OBLIGATOIREMENT

### ✅ Imports Absolus (CORRECT)
```python
from cyclisme_training_logs.intervals_api import IntervalsAPI
from cyclisme_training_logs.workout_state import WorkoutState
```

### ❌ Imports Relatifs (INCORRECT)
```python
from intervals_api import IntervalsAPI        # ❌
from .intervals_api import IntervalsAPI      # ❌
```

## Pattern Point d'Entrée main()
```python
def main():
    """Point d'entrée script Poetry"""
    coach = WorkflowCoach()
    coach.run_daily_workflow()

if __name__ == "__main__":
    main()
```

## Gestion Paths avec pathlib
```python
from pathlib import Path

class WorkflowCoach:
    def __init__(self):
        # Root projet
        self.project_root = Path(__file__).parent.parent
        
        # Chemins relatifs
        self.data_dir = self.project_root / "data"
        self.templates_dir = self.data_dir / "workout_templates"
```

## Configuration API Intervals.icu

**Fichier** : `~/.intervals_config.json`
```json
{
  "athlete_id": "i151223",
  "api_key": "REDACTED_INTERVALS_KEY"
}
```

**Chargement** :
```python
config_path = Path.home() / ".intervals_config.json"
with open(config_path) as f:
    config = json.load(f)
```

## Session Requests avec Auth
```python
import requests
import base64

session = requests.Session()
auth_string = f"API_KEY:{api_key}"
auth_b64 = base64.b64encode(auth_string.encode()).decode()

session.headers.update({
    "Authorization": f"Basic {auth_b64}",
    "Content-Type": "application/json"
})
```

## Référence intervals_api.py
```python
class IntervalsAPI:
    def get_events(self, oldest, newest, category="WORKOUT"):
        """GET /athlete/{id}/events"""
        url = f"{self.base_url}/athlete/{self.athlete_id}/events"
        params = {"oldest": oldest, "newest": newest, "category": category}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def delete_event(self, event_id):
        """DELETE /athlete/{id}/events/{event_id}"""
        url = f"{self.base_url}/athlete/{self.athlete_id}/events/{event_id}"
        response = self.session.delete(url)
        response.raise_for_status()
        return True
    
    def create_event(self, event_data):
        """POST /athlete/{id}/events"""
        url = f"{self.base_url}/athlete/{self.athlete_id}/events"
        response = self.session.post(url, json=event_data)
        response.raise_for_status()
        return response.json()
```

## Gestion Erreurs API
```python
def _delete_workout_intervals(self, workout_id):
    """Supprime workout avec gestion erreurs"""
    try:
        response = self.session.delete(url)
        response.raise_for_status()
        return True
    except requests.exceptions.HTTPError as e:
        print(f"❌ Erreur HTTP : {e}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur réseau : {e}")
        return False
```

## Tests avec Poetry

### Structure tests/
```
tests/
├── __init__.py
├── test_asservissement.py     # 🆕 À CRÉER
└── conftest.py
```

### Exemple test
```python
from cyclisme_training_logs.workflow_coach import WorkflowCoach

def test_load_workout_templates():
    coach = WorkflowCoach()
    templates = coach.load_workout_templates()
    assert len(templates) == 6
```

### Exécution
```bash
poetry run pytest
poetry run pytest tests/test_asservissement.py -v
```

## Commandes Poetry Utiles
```bash
# Installer projet
poetry install

# Exécuter script
poetry run workflow-coach

# Tests
poetry run pytest

# Shell avec virtualenv
poetry shell

# Info virtualenv
poetry env info --path
```

## Points Critiques

### ❌ À NE PAS FAIRE

1. Créer nouveau script Poetry (tout dans workflow_coach.py)
2. Imports relatifs
3. Hardcoder paths absolus
4. Oublier try/except API

### ✅ À FAIRE

1. Imports absolus package
2. Paths relatifs pathlib
3. Gestion erreurs complète
4. Logging informatif

## Workflow Modification

1. Ajouter méthodes à workflow_coach.py (~350 lignes)
2. Pas de nouveau script Poetry
3. Tests dans tests/test_asservissement.py
4. Exécuter : `poetry run workflow-coach`

## Dépendances

**Aucune nouvelle dépendance** ✅
- requests : Déjà installé
- json, pathlib, datetime : Stdlib

---

**Référence complète architecture Poetry pour Claude Code**
EOFPOETRY

cat > "${ARCHIVE_DIR}/IMPLEMENTATION_BRIEF.md" << 'EOFBRIEF'
# Brief Implémentation - Système Asservissement Coach AI

## 📚 Documents à Lire dans l'Ordre

1. **POETRY_ARCHITECTURE.md** (PRIORITÉ 1) ⭐
   - Architecture technique Poetry
   - Patterns imports obligatoires
   - Référence intervals_api.py
   - Gestion erreurs

2. **IMPLEMENTATION_BRIEF.md** (ce document)
   - Vision système asservissement
   - Modifications code détaillées

3. **CURRENT_STATE.md**
   - État actuel projet
   - Problèmes connus

4. **README_ARCHIVE.md**
   - Guide utilisation archive

## Vision du Projet

Transformer workflow actuel (boucle ouverte) en système d'asservissement automatique (boucle fermée).

## Architecture Cible
```
┌─────────────────────────────────────┐
│  OBJECTIF : FTP 220W → 260W         │
└──────────────┬──────────────────────┘
               ▼
    ┌──────────────────────┐
    │  PLANIFICATION       │
    │  Upload S0XX         │
    └──────┬───────────────┘
           ▼
    ┌──────────────────────┐
    │  EXÉCUTION           │
    │  Séances réalisées   │
    └──────┬───────────────┘
           ▼
    ┌──────────────────────┐
    │  MESURE              │◄─── 🆕 Planning restant
    │  AI analyse          │
    └──────┬───────────────┘
           ▼
    ┌──────────────────────┐
    │  DÉCISION            │◄─── 🆕 Catalogue templates
    │  AI propose modif    │
    └──────┬───────────────┘
           ▼
    ┌──────────────────────┐
    │  CORRECTION          │◄─── 🆕 Modification auto
    │  DELETE/POST API     │
    │  Update JSON         │
    └──────┬───────────────┘
           └──────────► Nouvelle itération
```

## Modifications workflow_coach.py (~350 lignes)

### Nouvelles Méthodes
```python
# Chargement planning
def load_remaining_sessions(self, week_id)
def format_remaining_sessions_compact(self, remaining_sessions)

# Catalogue templates
def load_workout_templates(self)

# Prompt AI enrichi
def build_ai_prompt(self, session_data, week_context, remaining_sessions)

# Parsing modifications
def parse_ai_modifications(self, ai_response)

# Application modifications
def apply_planning_modifications(self, modifications, week_id)
def _apply_lighten(self, mod, week_id)
def _get_workout_id_intervals(self, date)
def _delete_workout_intervals(self, workout_id)
def _upload_workout_intervals(self, date, code, structure)
def _update_planning_json(self, week_id, date, new_workout, old, reason)
def _extract_day_number(self, date_str, week_id)
```

### Modifications Méthodes Existantes
```python
def __init__(self):
    # ... existant ...
    self.workout_templates = self.load_workout_templates()  # 🆕

def run_daily_workflow(self):
    # ... étapes 1-3 existantes ...
    remaining = self.load_remaining_sessions(week_id)  # 🆕
    prompt = self.build_ai_prompt(data, ctx, remaining)  # 🆕
    # ... analyse AI ...
    mods = self.parse_ai_modifications(ai_response)  # 🆕
    if mods:
        self.apply_planning_modifications(mods, week_id)  # 🆕
```

## Structures Données à Créer

### data/week_planning/week_planning_S0XX.json
```json
{
  "week_id": "S072",
  "sessions": [
    {
      "day": "2025-12-16",
      "workout_code": "S072-01-INT-SweetSpot-V001",
      "tss_planned": 60,
      "status": "planned",
      "history": []
    }
  ]
}
```

### data/workout_templates/*.json (6 fichiers)

Voir examples/templates/ pour structures complètes.

## Prompt AI Enrichi (+330 tokens)
```markdown
## PLANNING RESTANT (5 séances)
2025-12-18: S072-03-END (45 TSS)
...

## CATALOGUE TEMPLATES
**RÉCUPÉRATION** :
- recovery_active_30tss : 45min Z1-Z2 (30 TSS)
...

**Format JSON si modification** :
{"modifications": [{"action": "lighten", ...}]}
```

## Tests à Créer
```python
# tests/test_asservissement.py
def test_load_remaining_sessions()
def test_load_workout_templates()
def test_parse_modifications_empty()
def test_parse_modifications_valid()
```

## Workflow Usage
```bash
poetry run workflow-coach
# ou
train
```

## Checklist

- [ ] Structure data/ créée
- [ ] 6 templates JSON validés
- [ ] workflow_coach.py modifié
- [ ] Tests créés
- [ ] Workflow testé

## Impact

- Coût : +$0.78/an
- Gain : 495€/an
- ROI : 634:1

---

**Lire POETRY_ARCHITECTURE.md pour patterns techniques détaillés**
EOFBRIEF

cat > "${ARCHIVE_DIR}/CURRENT_STATE.md" << 'EOFSTATE'
# État Actuel du Projet

## Métriques

- FTP : 220W
- Poids : ~84kg
- CTL : ~54-56
- TSS hebdo : 320-380

## Scripts Poetry (15 total)
```bash
workflow-coach          # Orchestrateur
weekly-analysis         # Analyse hebdo
upload-workouts         # Upload Intervals.icu
prepare-analysis        # Préparation données
collect-athlete-feedback # Feedback
sync-intervals          # Sync API
... (9 autres)
```

## Alias ZSH
```bash
train='cd ~/cyclisme-training-logs && poetry run workflow-coach'
wa='poetry run weekly-analysis'
wu='poetry run upload-workouts'
```

## Problèmes Connus

- Dossier data/week_planning/ absent
- Fichiers planning JSON absents
- Séances sautées non réconciliées :
  - S070-04-END (2025-12-04)
  - S071-05-INT (2025-12-12)

## Config API

`~/.intervals_config.json` configuré

## Dernières Modifs

- Migration Poetry complète
- Imports absolus corrigés
- Alias ZSH configurés
EOFSTATE

cat > "${ARCHIVE_DIR}/README_ARCHIVE.md" << 'EOFREADME'
# Archive Contexte Complet - Claude Code

## 📖 ORDRE DE LECTURE OBLIGATOIRE

1. **POETRY_ARCHITECTURE.md** ⭐⭐⭐
   - Architecture technique détaillée
   - Patterns imports (CRITIQUE)
   - Référence intervals_api.py
   - Gestion erreurs API

2. **IMPLEMENTATION_BRIEF.md**
   - Vision asservissement
   - Modifications ~350 lignes

3. **CURRENT_STATE.md**
   - État actuel
   - Problèmes connus

## Contenu Archive

### Documentation
- POETRY_ARCHITECTURE.md (nouveau)
- IMPLEMENTATION_BRIEF.md
- CURRENT_STATE.md
- README_ARCHIVE.md

### Code Source
- pyproject.toml
- poetry.lock
- cyclisme_training_logs/ (33 modules)
  - workflow_coach.py ⭐
  - intervals_api.py (référence)

### Logs
- logs/workouts-history.md
- logs/weekly_reports/S070/
- logs/weekly_reports/S071/

### Exemples
- examples/planning/example_week_planning.json
- examples/templates/*.json (6 templates)

### Config
- README.md
- COMMANDS.md
- ALIASES.md
- .gitignore

## Utilisation
```bash
# Extraire
tar -xzf claude-code-context_*.tar.gz
cd claude-code-context_*

# Lire dans l'ordre
cat POETRY_ARCHITECTURE.md
cat IMPLEMENTATION_BRIEF.md
cat CURRENT_STATE.md
```

## Structure Cible
```
~/cyclisme-training-logs/
├── data/                    # 🆕 À CRÉER
│   ├── week_planning/
│   └── workout_templates/
└── cyclisme_training_logs/
    └── workflow_coach.py    # À MODIFIER
```

## Points Critiques

1. ⚠️ Lire POETRY_ARCHITECTURE.md AVANT tout
2. ⚠️ Imports absolus obligatoires
3. ⚠️ Référence intervals_api.py pour API
4. ⚠️ Gestion erreurs try/except
5. ⚠️ Pas de nouveau script Poetry

## Checklist

- [ ] POETRY_ARCHITECTURE.md lu
- [ ] Structure data/ créée
- [ ] workflow_coach.py modifié
- [ ] Tests créés
- [ ] `poetry run pytest` OK

---

**COMMENCER PAR POETRY_ARCHITECTURE.md** 🚀
EOFREADME

echo "=== Création archive tar.gz ==="
cd /tmp
tar -czf "claude-code-context_${TIMESTAMP}.tar.gz" "claude-code-context_${TIMESTAMP}/"
mv "claude-code-context_${TIMESTAMP}.tar.gz" ~/

echo ""
echo "✅ Archive créée avec ARCHITECTURE POETRY complète !"
echo ""
echo "📦 Fichier : ~/claude-code-context_${TIMESTAMP}.tar.gz"
echo ""
echo "📊 Taille :"
du -h ~/claude-code-context_${TIMESTAMP}.tar.gz
echo ""
echo "📋 Fichiers principaux :"
echo "   1️⃣  POETRY_ARCHITECTURE.md (PRIORITÉ ABSOLUE)"
echo "   2️⃣  IMPLEMENTATION_BRIEF.md"
echo "   3️⃣  CURRENT_STATE.md"
echo "   4️⃣  README_ARCHIVE.md"
echo ""
echo "🎯 Prêt pour Claude Code avec architecture Poetry complète"

rm -rf "${ARCHIVE_DIR}"

exit 0
