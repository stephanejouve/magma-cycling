# Week Planning - Configuration Hebdomadaire

Ce répertoire contient les fichiers de configuration JSON pour la planification hebdomadaire des entraînements.

## Quick Start

### 1. Créer un nouveau planning

```bash
# Copier le template
cp week_planning_template.json week_planning_S071.json

# Éditer avec vos données
nano week_planning_S071.json
```

### 2. Structure minimale

```json
{
  "week_id": "S071",
  "start_date": "2025-12-09",
  "end_date": "2025-12-15",
  "athlete_id": "i151223",
  "tss_target": 250,
  "planned_sessions": [
    {
      "session_id": "S071-01",
      "date": "2025-12-09",
      "type": "END",
      "name": "EnduranceBase",
      "version": "V001",
      "duration_min": 60,
      "tss_planned": 45,
      "status": "completed"
    }
  ]
}
```

### 3. Utiliser dans le code

```python
from rest_and_cancellations import load_week_planning

planning = load_week_planning("S071")
print(f"Semaine {planning['week_id']} : {len(planning['planned_sessions'])} sessions")
```

## Statuts de session

| Statut | Description | Champs requis |
|--------|-------------|---------------|
| `completed` | Séance exécutée | Aucun |
| `cancelled` | Séance annulée | `cancellation_reason` |
| `rest_day` | Repos planifié | `rest_reason` (optionnel) |
| `replaced` | Séance de remplacement | `original_session_id` |

## Exemples de sessions

### Session normale (exécutée)

```json
{
  "session_id": "S071-01",
  "date": "2025-12-09",
  "type": "END",
  "name": "EnduranceBase",
  "version": "V001",
  "duration_min": 60,
  "tss_planned": 45,
  "status": "completed"
}
```

### Session annulée

```json
{
  "session_id": "S071-02",
  "date": "2025-12-10",
  "type": "INT",
  "name": "SweetSpot",
  "version": "V001",
  "duration_min": 50,
  "tss_planned": 55,
  "status": "cancelled",
  "cancellation_reason": "Météo défavorable (tempête)",
  "impact_notes": "Report vendredi"
}
```

### Repos planifié

```json
{
  "session_id": "S071-07",
  "date": "2025-12-15",
  "type": "REC",
  "name": "ReposObligatoire",
  "version": "V001",
  "duration_min": 0,
  "tss_planned": 0,
  "status": "rest_day",
  "rest_reason": "Protocole repos dimanche",
  "physiological_notes": "Récupération complète"
}
```

## Types de séance

| Code | Type | Description |
|------|------|-------------|
| `END` | Endurance | Zones Z1-Z3, développement aérobie |
| `INT` | Intervalles | Zones Z4-Z7, intensité élevée |
| `REC` | Récupération | Z1, récupération active ou repos |
| `CAD` | Cadence | Travail technique de vélocité |
| `TEC` | Technique | Travail spécifique technique |
| `FOR` | Force | Travail musculation/force |

## Validation

Le système valide automatiquement :

- ✅ Champs obligatoires présents
- ✅ Statuts valides
- ✅ Dates au format ISO (YYYY-MM-DD)
- ✅ Raison obligatoire si `cancelled`
- ✅ Pas de doublons session_id
- ✅ Cohérence dates (semaine = 7 jours)

## Fichiers disponibles

| Fichier | Description |
|---------|-------------|
| `week_planning_template.json` | Template vierge à copier |
| `week_planning_S070.json` | Exemple semaine S070 complète |
| `demo_output_S070.md` | Exemple output markdown généré |
| `README.md` | Ce fichier |

## Workflow type

### 1. Début de semaine (lundi)

```bash
# Créer planning
cp week_planning_template.json week_planning_S071.json

# Planifier les 7 jours
nano week_planning_S071.json
```

### 2. Pendant la semaine

Si une séance est annulée :

```json
// Éditer le fichier
{
  "session_id": "S071-03",
  "status": "cancelled",  // Changer de completed à cancelled
  "cancellation_reason": "Raison de l'annulation"
}
```

### 3. Fin de semaine (dimanche)

```bash
# Générer rapport complet
python3 scripts/demo_rest_handling.py

# Vérifier réconciliation
python3 -c "
from rest_and_cancellations import load_week_planning, reconcile_planned_vs_actual
planning = load_week_planning('S071')
# ... récupérer activités API ...
# result = reconcile_planned_vs_actual(planning, activities)
"
```

## Commandes utiles

```bash
# Valider un planning
python3 -c "
from rest_and_cancellations import load_week_planning, validate_week_planning
p = load_week_planning('S071')
print('Valide' if validate_week_planning(p) else 'Invalide')
"

# Lister sessions planifiées
python3 -c "
from rest_and_cancellations import load_week_planning
p = load_week_planning('S071')
for s in p['planned_sessions']:
    print(f\"{s['date']} : {s['session_id']} - {s['status']}\")
"

# Calculer TSS planifié
python3 -c "
from rest_and_cancellations import load_week_planning
p = load_week_planning('S071')
tss = sum(s.get('tss_planned', 0) for s in p['planned_sessions'])
print(f'TSS total planifié : {tss}')
"
```

## Bonnes pratiques

### Nommage

- **Week ID** : Format `SXXX` (ex: S070, S071)
- **Session ID** : Format `SXXX-DD` où DD = jour de la semaine (01-07)
- **Fichier** : `week_planning_SXXX.json`

### Structure

- Une semaine = 7 jours (lundi → dimanche)
- Dates ISO 8601 (YYYY-MM-DD)
- Session ID unique par semaine
- Version : V001, V002, etc.

### Maintenance

- Créer le planning en début de semaine
- Mettre à jour statuts au fil de l'eau
- Documenter raisons annulations
- Archiver plannings passés (optionnel)

## Troubleshooting

### Erreur : "Planning non trouvé"

```bash
# Vérifier que le fichier existe
ls -l data/week_planning/week_planning_S071.json

# Vérifier le format du nom
# Correct : week_planning_S071.json
# Incorrect : planning_S071.json, S071.json
```

### Erreur : "Planning invalide"

```bash
# Valider JSON
python3 -c "import json; json.load(open('data/week_planning/week_planning_S071.json'))"

# Vérifier structure
python3 -c "
from rest_and_cancellations import load_week_planning
try:
    planning = load_week_planning('S071')
    print('✓ Planning valide')
except Exception as e:
    print(f'✗ Erreur : {e}')
"
```

### Erreur : "Raison obligatoire pour cancelled"

Si vous avez une session avec `status: "cancelled"` :

```json
{
  "status": "cancelled",
  "cancellation_reason": "Obligatoire ! Raison de l'annulation"
}
```

## Exemples avancés

### Planning avec report

```json
{
  "planned_sessions": [
    {
      "session_id": "S071-03",
      "date": "2025-12-11",
      "status": "cancelled",
      "cancellation_reason": "Météo",
      "impact_notes": "Reporté au vendredi"
    },
    {
      "session_id": "S071-05",
      "date": "2025-12-13",
      "type": "END",
      "name": "EnduranceBase",
      "status": "replaced",
      "original_session_id": "S071-03",
      "tss_planned": 45
    }
  ]
}
```

### Planning semaine de récupération

```json
{
  "week_id": "S072",
  "tss_target": 120,
  "planned_sessions": [
    {"status": "rest_day"},
    {"type": "REC", "tss_planned": 30, "status": "completed"},
    {"status": "rest_day"},
    {"type": "REC", "tss_planned": 35, "status": "completed"},
    {"status": "rest_day"},
    {"type": "END", "tss_planned": 55, "status": "completed"},
    {"status": "rest_day"}
  ],
  "week_summary": {
    "notes": "Semaine récupération post-bloc intense"
  }
}
```

## Documentation complète

- 📖 Guide complet : `docs/GESTION_REPOS_ANNULATIONS.md`
- 🔧 Guide intégration : `docs/INTEGRATION_WORKFLOW.md`
- 💻 Module Python : `scripts/rest_and_cancellations.py`
- ✅ Tests : `scripts/test_rest_and_cancellations.py`
- 🎬 Démo : `scripts/demo_rest_handling.py`

## Support

Questions ? Consulter la documentation complète ou exécuter la démo :

```bash
python3 scripts/demo_rest_handling.py
```

---

**Version :** 1.0
**Dernière MAJ :** Décembre 2025
**Auteur :** Implémenté avec Claude Code
