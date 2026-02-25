# Projet : Système d'Asservissement Coach AI Cyclisme

## Contexte Global

Système automatisé d'entraînement cyclisme avec analyse quotidienne par AI et ajustement adaptatif du planning hebdomadaire. L'objectif est d'implémenter une **boucle d'asservissement** permettant au coach AI de détecter les signaux de fatigue et d'ajuster automatiquement les séances futures de la semaine.

**Athlète** : Stéphane, 54 ans, FTP actuel 220W, objectif 260W
**Stack** : Python 3.11, Poetry, API Intervals.icu, Git
**Repo** : `~/cyclisme-training-logs/`

---

## Structure Actuelle Repo
````
~/cyclisme-training-logs/
├── pyproject.toml                    # Package Poetry, 15 scripts configurés
├── poetry.lock
├── .gitignore
├── README.md
├── COMMANDS.md
├── ALIASES.md
│
├── cyclisme_training_logs/           # Package Python principal
│   ├── __init__.py
│   ├── workflow_coach.py            # ⭐ Orchestrateur principal (À MODIFIER)
│   ├── weekly_analysis.py           # Analyse hebdomadaire
│   ├── upload_workouts.py           # Upload workouts Intervals.icu
│   ├── prepare_analysis.py          # Préparation données
│   ├── collect_athlete_feedback.py  # Collecte feedback
│   ├── intervals_api.py             # Client API Intervals.icu
│   ├── rest_and_cancellations.py    # Gestion repos/annulations
│   ├── planned_sessions_checker.py  # Vérification planning
│   ├── workout_state.py             # État workflow
│   └── ... (25 autres modules)
│
├── data/                             # ⚠️ À CRÉER
│   ├── week_planning/               # ⚠️ À CRÉER - Planning JSON hebdo
│   │   └── week_planning_S0XX.json
│   └── workout_templates/           # 🆕 À CRÉER - Catalogue templates
│       ├── recovery_active_30tss.json
│       ├── recovery_active_25tss.json
│       ├── recovery_short_20tss.json
│       ├── endurance_light_35tss.json
│       ├── endurance_short_40tss.json
│       └── sweetspot_short_50tss.json
│
├── logs/
│   ├── workouts-history.md          # Historique complet séances
│   └── weekly_reports/
│       ├── S070/                    # 6 fichiers .md par semaine
│       └── S071/
│
└── ~/.intervals_config.json         # Config API (hors repo)
````

---

## Objectif Implémentation

### Analogie Asservissement

**Type** : Boucle de rétroaction négative (feedback loop stabilisant)
````
┌─────────────────────────────────────┐
│  OBJECTIF : FTP 220W → 260W         │
│  Contraintes : Sommeil, Discipline  │
└──────────────┬──────────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │  PLANIFICATION       │
    │  Semaine S0XX        │
    │  TSS, Intensités     │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │  EXÉCUTION           │
    │  Séances réalisées   │
    │  Métriques captées   │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │  MESURE (AI Coach)   │◄─── 🆕 PLANNING RESTANT
    │  ∆HRV, ∆TSB, RPE     │
    │  Découplage, FC      │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │  DÉCISION            │
    │  Maintenir / Alléger │◄─── 🆕 CATALOGUE TEMPLATES
    │  Annuler / Reporter  │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │  CORRECTION          │◄─── 🆕 MODIFICATION AUTO
    │  Upload Intervals    │     Planning JSON
    │  Update logs         │
    └──────┬───────────────┘
           │
           └──────────► RETOUR OBJECTIF (nouveau cycle)
````

### Flux Actuel (Boucle Ouverte) ❌
````
1. Collecte données séance
2. Analyse AI
3. Sauvegarde logs
4. Git commit
````

**Problème** : Pas de correction automatique si fatigue détectée

### Flux Cible (Boucle Fermée) ✅
````
1. Collecte données séance
2. Chargement planning restant semaine
3. Analyse AI enrichie (avec contexte planning)
4. Détection recommandations modifications
5. Application modifications si nécessaire :
   - Suppression ancien workout Intervals.icu
   - Upload nouveau workout depuis catalogue
   - Mise à jour week_planning_SXXX.json
6. Sauvegarde logs
7. Git commit (mentionner modifications)
````

---

## Tâches Implémentation Détaillées

### 1. Créer Structure Données

#### A. Dossiers
````bash
mkdir -p data/week_planning
mkdir -p data/workout_templates
````

#### B. Planning Hebdomadaire Type

**Fichier** : `data/week_planning/week_planning_S072.json`

**Structure** (voir `example_week_planning.json` uploadé) :
````json
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
    }
  ]
}
````

**Points clés** :
- `status` : `planned` | `modified` | `cancelled` | `rest_day`
- `history[]` : Traçabilité modifications (timestamp, action, reason)
- `version` : Incrémenté à chaque modification

#### C. Templates Workouts

**6 fichiers à créer** dans `data/workout_templates/` (voir examples uploadés) :

1. `recovery_active_30tss.json` - Récupération 45min (30 TSS)
2. `recovery_active_25tss.json` - Récupération 40min (25 TSS)
3. `recovery_short_20tss.json` - Récupération 30min (20 TSS)
4. `endurance_light_35tss.json` - Endurance légère 50min (35 TSS)
5. `endurance_short_40tss.json` - Endurance courte 55min (40 TSS)
6. `sweetspot_short_50tss.json` - Sweet-Spot court 50min (50 TSS)

**Structure template** :
````json
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
````

**Points clés** :
- `workout_code_pattern` : Template Python format string avec {week_id} et {day_num:02d}
- `intervals_icu_format` : Format texte Intervals.icu (pas XML)
- `use_cases[]` : Quand utiliser ce template
- `prerequisites` : Conditions TSB/HRV recommandées

---

### 2. Modifier `workflow_coach.py`

#### A. Chargement Planning Restant

**Ajouter méthode** :
````python
def load_remaining_sessions(self, week_id):
    """Charge séances planifiées futures de la semaine

    Args:
        week_id: ID semaine (ex: S072)

    Returns:
        list: Séances futures (date >= aujourd'hui)
    """
    planning_file = self.project_root / "data" / "week_planning" / f"week_planning_{week_id}.json"

    if not planning_file.exists():
        print(f"⚠️  Planning {week_id} non trouvé")
        return []

    with open(planning_file, 'r') as f:
        planning = json.load(f)

    today = datetime.now().date()

    remaining = []
    for session in planning['sessions']:
        session_date = datetime.strptime(session['day'], '%Y-%m-%d').date()
        if session_date >= today:
            remaining.append(session)

    return remaining
````

**Ajouter méthode** :
````python
def format_remaining_sessions_compact(self, remaining_sessions):
    """Format compact planning pour prompt AI (cible ~150 tokens)

    Returns:
        str: Planning formaté
    """
    if not remaining_sessions:
        return ""

    lines = [f"\n## PLANNING RESTANT ({len(remaining_sessions)} séances)\n"]

    for session in remaining_sessions:
        date = session['day']
        code = session['workout_code']
        tss = session['tss_planned']

        if session.get('status') == 'rest_day':
            lines.append(f"{date}: REPOS")
        else:
            lines.append(f"{date}: {code} ({tss} TSS)")

    return "\n".join(lines)
````

---

#### B. Chargement Catalogue Templates

**Ajouter méthode** :
````python
def load_workout_templates(self):
    """Charge catalogue templates au démarrage

    Returns:
        dict: Templates indexés par ID
    """
    templates = {}
    templates_dir = self.project_root / "data" / "workout_templates"

    if not templates_dir.exists():
        print("⚠️  Dossier workout_templates absent")
        return templates

    for template_file in templates_dir.glob("*.json"):
        with open(template_file) as f:
            template = json.load(f)
            templates[template['id']] = template

    print(f"✅ {len(templates)} templates chargés")
    return templates
````

**Modifier `__init__()`** :
````python
def __init__(self, ...):
    # ... code existant ...

    # 🆕 Charger catalogue templates
    self.workout_templates = self.load_workout_templates()
````

---

#### C. Enrichissement Prompt AI

**Modifier méthode** `build_ai_prompt()` :
````python
def build_ai_prompt(self, session_data, week_context, remaining_sessions):
    """Construit prompt AI avec planning restant

    Args:
        session_data: Données séance du jour
        week_context: Contexte semaine (CTL/ATL/TSB, historique)
        remaining_sessions: Séances planifiées futures
    """

    # Planning restant (format compact ~150 tokens)
    planning_section = self.format_remaining_sessions_compact(remaining_sessions)

    # Instructions catalogue (~180 tokens)
    catalogue_instructions = """
## CATALOGUE WORKOUTS REMPLACEMENT

Si modification planning nécessaire, utilisez templates prédéfinis :

**RÉCUPÉRATION** (remplacement END/INT léger) :
- `recovery_active_30tss` : 45min Z1-Z2 (30 TSS)
- `recovery_active_25tss` : 40min Z1-Z2 (25 TSS)
- `recovery_short_20tss` : 30min Z1 (20 TSS)

**ENDURANCE ALLÉGÉE** (remplacement END normal) :
- `endurance_light_35tss` : 50min Z2 (35 TSS)
- `endurance_short_40tss` : 55min Z2 (40 TSS)

**INTENSITÉ RÉDUITE** (remplacement Sweet-Spot/VO2) :
- `sweetspot_short_50tss` : 2x10min 88% (50 TSS)

**Sélection** : Choisir template adapté selon TSS cible et type original.

**Format JSON si modification** :
```json
{"modifications": [{
  "action": "lighten",
  "target_date": "YYYY-MM-DD",
  "current_workout": "CODE",
  "template_id": "recovery_active_30tss",
  "reason": "HRV -15%, prioriser récupération"
}]}
```

**Si aucune modification** : Ne rien ajouter (pas de JSON).
"""

    prompt = f"""
{self.base_system_prompt}

{catalogue_instructions}

## CONTEXTE SEMAINE EN COURS

### Séances Réalisées
{self._format_completed_sessions(week_context['completed'])}

{planning_section}

### Métriques Actuelles
- CTL: {week_context['ctl']}
- ATL: {week_context['atl']}
- TSB: {week_context['tsb']}
- TSS Cumulé: {week_context['tss_week']}/{week_context['tss_planned']}

## SÉANCE DU JOUR

{self._format_session_data(session_data)}
"""

    return prompt
````

---

#### D. Parsing Modifications AI

**Ajouter méthode** :
````python
def parse_ai_modifications(self, ai_response):
    """Parse modifications planning depuis réponse AI

    Args:
        ai_response: Texte réponse AI complet

    Returns:
        list: Modifications à appliquer (vide si aucune)
    """
    import re

    # Chercher bloc JSON modifications
    json_match = re.search(
        r'```json\s*\n(\{.*?"modifications".*?\})\s*\n```',
        ai_response,
        re.DOTALL
    )

    if not json_match:
        return []  # Pas de modification = comportement normal

    try:
        data = json.loads(json_match.group(1))
        return data.get('modifications', [])
    except json.JSONDecodeError as e:
        print(f"⚠️  JSON modifications invalide : {e}")
        return []
````

---

#### E. Application Modifications

**Ajouter méthode principale** :
````python
def apply_planning_modifications(self, modifications, week_id):
    """Applique modifications planning

    Args:
        modifications: Liste modifications AI
        week_id: ID semaine
    """
    if not modifications:
        print("\n✅ Planning maintenu tel quel")
        return

    print(f"\n📋 {len(modifications)} modification(s) détectée(s)")

    for mod in modifications:
        action = mod['action']

        if action == 'lighten':
            self._apply_lighten(mod, week_id)
        elif action == 'cancel':
            self._apply_cancel(mod, week_id)
        # Autres actions possibles : reschedule, add
````

**Ajouter méthode** :
````python
def _apply_lighten(self, mod, week_id):
    """Applique allégement séance via template

    Args:
        mod: Modification dict avec template_id
        week_id: ID semaine
    """
    template_id = mod['template_id']

    if template_id not in self.workout_templates:
        print(f"❌ Template inconnu: {template_id}")
        return

    template = self.workout_templates[template_id]

    print(f"\n🔄 Allégement via '{template['name']}'")
    print(f"   Date : {mod['target_date']}")
    print(f"   {template['tss']} TSS, {template['duration_minutes']}min")
    print(f"   Raison : {mod['reason']}")

    # Confirmation utilisateur
    confirm = input("   Appliquer ? (o/n) : ").strip().lower()
    if confirm != 'o':
        print("   ❌ Ignoré")
        return

    # 1. Générer workout code depuis template
    day_num = self._extract_day_number(mod['target_date'], week_id)
    workout_code = template['workout_code_pattern'].format(
        week_id=week_id,
        day_num=day_num
    )

    # 2. Supprimer ancien workout Intervals.icu
    old_workout_id = self._get_workout_id_intervals(mod['target_date'])
    if old_workout_id:
        self._delete_workout_intervals(old_workout_id)
        print("   🗑️  Ancien workout supprimé")

    # 3. Upload nouveau workout
    self._upload_workout_intervals(
        date=mod['target_date'],
        code=workout_code,
        structure=template['intervals_icu_format']
    )
    print("   ⬆️  Nouveau workout uploadé")

    # 4. Mettre à jour planning JSON
    self._update_planning_json(
        week_id=week_id,
        date=mod['target_date'],
        new_workout={
            'code': workout_code,
            'type': template['type'],
            'tss': template['tss'],
            'description': template['description']
        },
        old_workout=mod['current_workout'],
        reason=mod['reason']
    )
    print("   📝 Planning JSON mis à jour")
    print("   ✅ Modification appliquée")
````

**Ajouter méthodes auxiliaires** :
````python
def _get_workout_id_intervals(self, date):
    """Récupère ID workout Intervals.icu pour une date

    Args:
        date: Date YYYY-MM-DD

    Returns:
        str: ID workout ou None
    """
    url = f"https://intervals.icu/api/v1/athlete/{self.athlete_id}/events"
    params = {
        'oldest': date,
        'newest': date,
        'category': 'WORKOUT'
    }

    response = self.session.get(url, params=params)
    response.raise_for_status()
    events = response.json()

    return events[0]['id'] if events else None

def _delete_workout_intervals(self, workout_id):
    """Supprime workout Intervals.icu

    Args:
        workout_id: ID workout à supprimer
    """
    url = f"https://intervals.icu/api/v1/athlete/{self.athlete_id}/events/{workout_id}"
    response = self.session.delete(url)
    response.raise_for_status()

def _upload_workout_intervals(self, date, code, structure):
    """Upload nouveau workout Intervals.icu

    Args:
        date: Date YYYY-MM-DD
        code: Workout code (ex: S072-03-REC-V001)
        structure: Format texte Intervals.icu
    """
    event = {
        "category": "WORKOUT",
        "start_date_local": f"{date}T06:00:00",
        "name": code,
        "description": code,
        "workout_doc": structure
    }

    url = f"https://intervals.icu/api/v1/athlete/{self.athlete_id}/events"
    response = self.session.post(url, json=event)
    response.raise_for_status()

def _update_planning_json(self, week_id, date, new_workout, old_workout, reason):
    """Met à jour week_planning_SXXX.json avec historique

    Args:
        week_id: ID semaine
        date: Date modification
        new_workout: Dict nouveau workout
        old_workout: Code workout remplacé
        reason: Raison modification
    """
    planning_file = self.project_root / "data" / "week_planning" / f"week_planning_{week_id}.json"

    with open(planning_file, 'r') as f:
        planning = json.load(f)

    # Trouver session à modifier
    for i, session in enumerate(planning['sessions']):
        if session['day'] == date:
            # Sauvegarder dans historique
            timestamp = datetime.now().isoformat()

            history_entry = {
                "timestamp": timestamp,
                "action": "modified_by_ai_coach",
                "previous_workout": old_workout,
                "previous_tss": session['tss_planned'],
                "new_workout": new_workout['code'],
                "new_tss": new_workout['tss'],
                "reason": reason
            }

            # Mettre à jour session
            planning['sessions'][i].update({
                "workout_code": new_workout['code'],
                "type": new_workout['type'],
                "tss_planned": new_workout['tss'],
                "description": new_workout['description'],
                "status": "modified"
            })

            if 'history' not in planning['sessions'][i]:
                planning['sessions'][i]['history'] = []
            planning['sessions'][i]['history'].append(history_entry)

            break

    # Update metadata planning
    planning['last_updated'] = datetime.now().isoformat()
    planning['version'] = planning.get('version', 1) + 1

    # Sauvegarder
    with open(planning_file, 'w', encoding='utf-8') as f:
        json.dump(planning, f, indent=2, ensure_ascii=False)

def _extract_day_number(self, date_str, week_id):
    """Extrait numéro jour (1-7) depuis date

    Args:
        date_str: "2025-12-18"
        week_id: "S072"

    Returns:
        int: Numéro jour 1-7
    """
    planning_file = self.project_root / "data" / "week_planning" / f"week_planning_{week_id}.json"
    with open(planning_file) as f:
        planning = json.load(f)

    start_date = datetime.strptime(planning['start_date'], '%Y-%m-%d').date()
    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()

    delta = (target_date - start_date).days
    return delta + 1  # Jour 1-7
````

---

#### F. Modifier Workflow Principal

**Modifier méthode** `run_daily_workflow()` :
````python
def run_daily_workflow(self):
    """Workflow quotidien avec boucle asservissement intégrée"""

    print("\n" + "="*70)
    print("  🤖 WORKFLOW COACH AI - Analyse Quotidienne")
    print("="*70)

    # 1. Collecte données séance
    session_data = self.collect_session_data()

    # 2. Détection semaine
    week_id = self.detect_week_id(session_data['date'])
    print(f"\n📅 Semaine : {week_id}")

    # 3. Chargement contexte semaine
    week_context = self.load_week_context(week_id)

    # 🆕 4. Chargement planning restant
    remaining_sessions = self.load_remaining_sessions(week_id)
    print(f"📋 Planning restant : {len(remaining_sessions)} séances")

    # 5. Construction prompt AI enrichi
    ai_prompt = self.build_ai_prompt(
        session_data,
        week_context,
        remaining_sessions  # 🆕 Contexte planning
    )

    # 6. Appel AI
    print("\n🤖 Analyse AI en cours...")
    ai_response = self.call_ai_analysis(ai_prompt)

    # 7. Sauvegarde analyse
    self.save_analysis(ai_response, session_data, week_id)

    # 🆕 8. Parsing modifications
    modifications = self.parse_ai_modifications(ai_response)

    # 🆕 9. Application modifications planning
    if modifications:
        self.apply_planning_modifications(modifications, week_id)
    else:
        print("\n✅ Planning maintenu tel quel")

    # 10. Git commit
    if not self.skip_git:
        self.git_commit(
            session_data,
            week_id,
            has_modifications=bool(modifications)
        )

    # 11. Résumé
    self.print_summary(session_data, modifications)

    print("\n✅ WORKFLOW TERMINÉ")
````

---

### 3. Tests à Créer

**Fichier** : `tests/test_asservissement.py`
````python
import pytest
from datetime import datetime
from cyclisme_training_logs.workflow_coach import WorkflowCoach

def test_load_remaining_sessions():
    """Test chargement planning restant"""
    coach = WorkflowCoach()
    remaining = coach.load_remaining_sessions("S072")
    assert len(remaining) > 0
    assert 'day' in remaining[0]
    assert 'workout_code' in remaining[0]

def test_format_remaining_sessions_compact():
    """Test format compact planning"""
    coach = WorkflowCoach()
    remaining = [
        {"day": "2025-12-18", "workout_code": "S072-03-END-V001", "tss_planned": 45},
        {"day": "2025-12-19", "workout_code": "S072-04-INT-V001", "tss_planned": 55}
    ]
    formatted = coach.format_remaining_sessions_compact(remaining)
    assert "S072-03-END-V001" in formatted
    assert "45 TSS" in formatted

def test_load_workout_templates():
    """Test chargement catalogue templates"""
    coach = WorkflowCoach()
    templates = coach.load_workout_templates()
    assert len(templates) == 6
    assert "recovery_active_30tss" in templates

def test_parse_modifications_empty():
    """Test parsing sans modification"""
    coach = WorkflowCoach()
    ai_response = "# Analyse\n\nTout va bien, planning maintenu."
    mods = coach.parse_ai_modifications(ai_response)
    assert mods == []

def test_parse_modifications_valid():
    """Test parsing avec modification valide"""
    coach = WorkflowCoach()
    ai_response = """
# Analyse

## Recommandations
```json
{"modifications": [{
  "action": "lighten",
  "target_date": "2025-12-18",
  "current_workout": "S072-03-END-V001",
  "template_id": "recovery_active_30tss",
  "reason": "HRV -15%"
}]}
```
"""
    mods = coach.parse_ai_modifications(ai_response)
    assert len(mods) == 1
    assert mods[0]['action'] == 'lighten'
    assert mods[0]['template_id'] == 'recovery_active_30tss'
````

---

## API Intervals.icu

### Configuration

**Fichier** : `~/.intervals_config.json`
````json
{
  "athlete_id": "iXXXXXX",
  "api_key": "your_api_key_here"
}
````

### Endpoints Utilisés
````python
# Base URL
BASE_URL = "https://intervals.icu/api/v1"

# Headers
headers = {
    "Authorization": f"Basic {base64.b64encode(f'API_KEY:{api_key}'.encode()).decode()}"
}

# Récupérer workouts planifiés
GET /athlete/{athlete_id}/events
Params: oldest={date}, newest={date}, category=WORKOUT

# Supprimer workout
DELETE /athlete/{athlete_id}/events/{workout_id}

# Créer workout
POST /athlete/{athlete_id}/events
Body: {
  "category": "WORKOUT",
  "start_date_local": "YYYY-MM-DDTHH:MM:SS",
  "name": "workout_code",
  "description": "description",
  "workout_doc": "intervals_icu_format"
}
````

---

## Workflow Usage Final

### Commande
````bash
cd ~/cyclisme-training-logs
poetry run workflow-coach
````

Ou avec alias ZSH :
````bash
train
````

### Sortie Attendue (Cas Normal - Pas de Modification)
````
🤖 WORKFLOW COACH AI - Analyse Quotidienne
======================================================================

📅 Semaine : S072
📋 Planning restant : 5 séances

🤖 Analyse AI en cours...

✅ Planning maintenu tel quel

💾 Sauvegarde logs/S072/S072-02-analysis.md...
🎯 Git commit...

✅ WORKFLOW TERMINÉ
````

### Sortie Attendue (Cas Modification Détectée)
````
🤖 WORKFLOW COACH AI - Analyse Quotidienne
======================================================================

📅 Semaine : S072
📋 Planning restant : 5 séances

🤖 Analyse AI en cours...

📋 1 modification(s) détectée(s)

🔄 Allégement via 'Récupération Active 30 TSS'
   Date : 2025-12-18
   30 TSS, 45min
   Raison : HRV -15%, prioriser récupération

   Appliquer ? (o/n) : o

   🗑️  Ancien workout supprimé
   ⬆️  Nouveau workout uploadé
   📝 Planning JSON mis à jour
   ✅ Modification appliquée

💾 Sauvegarde logs/S072/S072-02-analysis.md...
🎯 Git commit (avec modifications)...

✅ WORKFLOW TERMINÉ
````

---

## Impact Coût

### Tokens Ajoutés

| Élément | Tokens | Fréquence |
|---------|--------|-----------|
| Planning restant compact | 150 | Quotidien |
| Instructions catalogue | 180 | 1× (système prompt) |
| **TOTAL par analyse** | **+330** | **+15%** |

### Coût Annuel

- **Baseline actuel** : $5.85/an
- **Avec asservissement** : $6.63/an
- **Delta** : +$0.78/an (+13%)

### ROI

**Gains temps humain** : 33 heures/an × 15€/h = **495€/an**

**ROI** : (495 - 0.78) / 0.78 = **634:1**

---

## Points d'Attention Critiques

### 1. Confirmation Utilisateur Obligatoire

**Toujours** demander confirmation avant modification :
````python
confirm = input("   Appliquer ? (o/n) : ").strip().lower()
if confirm != 'o':
    print("   ❌ Ignoré")
    return
````

### 2. Gestion Erreurs API

**Try/except** sur tous appels Intervals.icu :
````python
try:
    response = self.session.delete(url)
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    print(f"❌ Erreur API : {e}")
    return
````

### 3. Logging Informatif

**Print** à chaque étape pour traçabilité :
````python
print("   🗑️  Ancien workout supprimé")
print("   ⬆️  Nouveau workout uploadé")
print("   📝 Planning JSON mis à jour")
````

### 4. Git Commits Descriptifs

**Mentionner** modifications dans message commit :
````python
if has_modifications:
    commit_msg = f"feat: Analyse {workout_code} avec modification planning"
else:
    commit_msg = f"feat: Analyse {workout_code}"
````

### 5. Validation Templates

**Vérifier** existence template avant utilisation :
````python
if template_id not in self.workout_templates:
    print(f"❌ Template inconnu: {template_id}")
    return
````

---

## Checklist Validation Complète

### Structure Données

- [ ] Dossier `data/week_planning/` créé
- [ ] Dossier `data/workout_templates/` créé
- [ ] 6 templates JSON créés et validés syntaxe
- [ ] Exemple `week_planning_S072.json` créé

### Code `workflow_coach.py`

- [ ] Méthode `load_remaining_sessions()` ajoutée
- [ ] Méthode `format_remaining_sessions_compact()` ajoutée
- [ ] Méthode `load_workout_templates()` ajoutée
- [ ] Méthode `build_ai_prompt()` modifiée
- [ ] Méthode `parse_ai_modifications()` ajoutée
- [ ] Méthode `apply_planning_modifications()` ajoutée
- [ ] Méthode `_apply_lighten()` ajoutée
- [ ] Méthode `_get_workout_id_intervals()` ajoutée
- [ ] Méthode `_delete_workout_intervals()` ajoutée
- [ ] Méthode `_upload_workout_intervals()` ajoutée
- [ ] Méthode `_update_planning_json()` ajoutée
- [ ] Méthode `_extract_day_number()` ajoutée
- [ ] Méthode `run_daily_workflow()` modifiée
- [ ] `__init__()` modifié (chargement templates)

### Tests

- [ ] `test_load_remaining_sessions()` créé
- [ ] `test_format_remaining_sessions_compact()` créé
- [ ] `test_load_workout_templates()` créé
- [ ] `test_parse_modifications_empty()` créé
- [ ] `test_parse_modifications_valid()` créé
- [ ] Tous tests passent (`poetry run pytest`)

### Validation Fonctionnelle

- [ ] Workflow manuel testé (sans modification)
- [ ] Workflow manuel testé (avec modification simulée)
- [ ] API Intervals.icu testée (GET events)
- [ ] API Intervals.icu testée (DELETE workout)
- [ ] API Intervals.icu testée (POST workout)
- [ ] Planning JSON correctement updaté
- [ ] Historique JSON correctement tracé

### Documentation

- [ ] Git commit avec message descriptif
- [ ] README mis à jour
- [ ] COMMANDS.md mis à jour si nécessaire

---

## Exemples Réponses AI Attendues

### Cas 1 : Aucune Modification
````markdown
# ANALYSE S072-02 - Endurance Progressive

## Exécution Technique
- IF: 0.72 ✅
- Découplage: 4.8% (<7.5%) ✅
- Cadence: 86 rpm ✅

## Observations Physiologiques
Séance bien exécutée, récupération normale.

## Recommandations
- Hydratation standard (500ml/h)
- Maintenir Sweet-Spot jeudi selon planning
````

### Cas 2 : Allégement Recommandé
````markdown
# ANALYSE S072-02 - Endurance Progressive

## Exécution Technique
- IF: 0.72 ✅
- Découplage: 4.8% ✅
- RPE: 8/10 ⚠️

## Observations Physiologiques
⚠️ **Signaux alarme** :
- HRV -15% ce matin (43ms vs 51ms)
- RPE anormalement élevé pour Z2
- FC +8 bpm vs attendu

## Recommandations
Allégement séance demain nécessaire pour optimiser récupération.
```json
{"modifications": [{
  "action": "lighten",
  "target_date": "2025-12-18",
  "current_workout": "S072-03-END-EnduranceProgressive-V001",
  "template_id": "recovery_active_30tss",
  "reason": "HRV -15%, RPE élevé (8/10 en Z2), FC anormalement haute → prioriser récupération"
}]}
```
````

---

## Résumé Technique

### Modifications Codebase

| Fichier | Lignes Ajoutées | Type Modification |
|---------|-----------------|-------------------|
| `data/week_planning/*.json` | N/A | Création structure |
| `data/workout_templates/*.json` | N/A | Création 6 templates |
| `workflow_coach.py` | ~350 | Ajout méthodes |
| `tests/test_asservissement.py` | ~60 | Création tests |
| **TOTAL** | **~410 lignes** | **Fonctionnalités** |

### Dépendances Externes

- ✅ Requests (déjà installé)
- ✅ JSON (stdlib)
- ✅ Datetime (stdlib)
- ✅ Pathlib (stdlib)

**Aucune nouvelle dépendance requise** ✅

---

## Prochaines Étapes Après Implémentation

1. **Tester manuellement** workflow complet
2. **Créer premier planning** `week_planning_S072.json`
3. **Valider templates** avec vraie séance
4. **Documenter learnings** dans logs
5. **Itérer** selon feedback terrain

---

**FIN DES INSTRUCTIONS PROJET**
