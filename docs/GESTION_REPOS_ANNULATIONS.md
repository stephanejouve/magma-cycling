# Gestion des Repos et Annulations de Séances

## Vue d'ensemble

Cette fonctionnalité permet de gérer explicitement les jours de repos planifiés et les séances annulées/reportées dans le workflow d'analyse d'entraînement cyclisme.

## Cas d'usage

### 1. Repos Planifié (Type A)
**Exemple :** Dimanche S070-07 - Repos obligatoire selon protocole

- Pas d'activité Intervals.icu
- Génération entrée markdown spécifique "Repos"
- Documentation : TSS=0, métriques stables, justification protocole

### 2. Séance Annulée/Reportée (Type B)
**Exemple :** Jeudi S070-04 - Problème matériel

- Pas d'activité Intervals.icu
- Génération entrée markdown "Séance Non Réalisée"
- Documentation : Raison annulation, impact planning, TSS=0

### 3. Séance Exécutée Hors Plan (Type C)
**Exemple :** Séance de remplacement après report

- Activité Intervals.icu présente
- Analyse standard + mention contexte remplacement
- Cross-référence avec séance initiale annulée

## Architecture

### Fichiers créés

```
scripts/
├── rest_and_cancellations.py     # Module principal
├── test_rest_and_cancellations.py # Tests unitaires
└── demo_rest_handling.py          # Script de démonstration

data/
└── week_planning/
    ├── week_planning_S070.json    # Exemple semaine S070
    ├── week_planning_template.json # Template vierge
    └── demo_output_S070.md         # Exemple output
```

### Module principal : `rest_and_cancellations.py`

**Fonctions disponibles :**

- `load_week_planning(week_id, planning_dir)` : Charge planning JSON
- `validate_week_planning(planning)` : Valide structure planning
- `generate_rest_day_entry(...)` : Génère markdown repos
- `generate_cancelled_session_entry(...)` : Génère markdown annulation
- `reconcile_planned_vs_actual(...)` : Compare planning vs activités
- `process_week_with_rest_handling(...)` : Workflow complet

## Format de Configuration

### Structure JSON

```json
{
  "week_id": "S070",
  "start_date": "2025-12-02",
  "end_date": "2025-12-08",
  "athlete_id": "i151223",
  "tss_target": 255,
  "planned_sessions": [
    {
      "session_id": "S070-04",
      "date": "2025-12-05",
      "type": "END",
      "name": "EnduranceProgressive",
      "version": "V001",
      "duration_min": 65,
      "tss_planned": 48,
      "status": "cancelled",
      "cancellation_reason": "Problème technique matériel",
      "impact_notes": "TSS nul, repos involontaire"
    },
    {
      "session_id": "S070-07",
      "date": "2025-12-08",
      "type": "REC",
      "name": "ReposObligatoire",
      "version": "V001",
      "duration_min": 0,
      "tss_planned": 0,
      "status": "rest_day",
      "rest_reason": "Protocole repos dimanche obligatoire",
      "physiological_notes": "Récupération complète"
    }
  ]
}
```

### Statuts valides

- `completed` : Séance exécutée (données Intervals.icu disponibles)
- `cancelled` : Séance annulée/reportée (raison obligatoire)
- `rest_day` : Repos planifié (raison optionnelle)
- `replaced` : Séance de remplacement

### Types de séance

- `END` : Endurance
- `INT` : Intervalles
- `REC` : Récupération
- `CAD` : Cadence
- `TEC` : Technique
- `FOR` : Force

## Utilisation

### 1. Créer un planning hebdomadaire

```bash
# Copier le template
cp data/week_planning/week_planning_template.json \
   data/week_planning/week_planning_S071.json

# Éditer avec vos données
nano data/week_planning/week_planning_S071.json
```

### 2. Utiliser dans le code

```python
from rest_and_cancellations import (
    load_week_planning,
    generate_rest_day_entry,
    reconcile_planned_vs_actual
)

# Charger planning
planning = load_week_planning("S071")

# Générer markdown repos
session = planning['planned_sessions'][0]
metrics = {"ctl": 50, "atl": 35, "tsb": 15}
markdown = generate_rest_day_entry(session, metrics, metrics)
```

### 3. Workflow complet

```python
from rest_and_cancellations import process_week_with_rest_handling

result = process_week_with_rest_handling(
    week_id="S071",
    start_date="2025-12-09",
    end_date="2025-12-15",
    athlete_id="i151223",
    api_key="votre_cle_api"
)
```

## Tests

### Exécuter les tests unitaires

```bash
# Avec pytest
python3 -m pytest scripts/test_rest_and_cancellations.py -v

# Sans pytest
python3 scripts/test_rest_and_cancellations.py
```

**Couverture :** 14 tests, 100% réussis

### Tests couverts

- Chargement planning valide
- Gestion planning absent
- Validation structure
- Validation statuts
- Validation raisons obligatoires
- Détection doublons
- Génération markdown repos
- Génération markdown annulation
- Réconciliation activités
- Gestion activités non planifiées
- Multiples activités même jour
- Edge cases (feedback manquant, etc.)

## Démonstration

```bash
# Lancer la démo avec l'exemple S070
python3 scripts/demo_rest_handling.py
```

Cette démo illustre :
1. Chargement et validation du planning S070
2. Génération markdown repos planifié (S070-07)
3. Génération markdown séance annulée (S070-04)
4. Réconciliation planning vs activités
5. Export complet markdown

## Format Output Markdown

### Template Repos Planifié

```markdown
### S070-07-REC-ReposObligatoire
Date : 08/12/2025

#### Métriques Pré-séance
- CTL : 50
- ATL : 35
- TSB : +15
- Sommeil : 6h12min (score 78, VFC 66ms)

#### Exécution
- Durée : 0min (repos complet planifié)
- TSS : 0

#### Exécution Technique
[Texte contextualisé repos]

#### Validation Objectifs
- ✅ Repos complet respecté
- ✅ Récupération physiologique optimisée

#### Recommandations Progression
1. [Recommandation séance suivante]
```

### Template Séance Annulée

```markdown
### S070-04-END-EnduranceProgressive-V001
Date : 05/12/2025

#### Métriques Pré-séance
- CTL : 51
- ATL : 33
- TSB : +17

#### Exécution
- Durée : 0min (séance non réalisée)
- TSS : 0 (prévu 48)
- Raison annulation : [Raison détaillée]

#### Impact Planning
[Analyse impact sur progression]

#### Validation Objectifs
- ❌ Séance non exécutée
- ⚠️ Interruption progression planifiée
```

## Intégration Workflow

### Workflow actuel (sans planning)

```
1. Récupérer activités Intervals.icu
2. Analyser chaque séance
3. Générer markdown
4. Insérer dans workouts-history.md
```

### Nouveau workflow (avec planning)

```
1. Charger planning hebdomadaire
2. Récupérer activités Intervals.icu
3. Réconcilier planifié vs réalisé
4. Pour chaque session :
   - Si exécutée : analyse standard
   - Si repos : template repos
   - Si annulée : template annulation
5. Insérer dans workouts-history.md (ordre chronologique)
6. Logger rapport réconciliation
```

### Fallback

Si le fichier planning n'existe pas, le système revient automatiquement au workflow standard (analyse pure Intervals.icu).

## Validation et Erreurs

### Validation automatique

Le système valide :
- Présence champs obligatoires
- Validité statuts
- Cohérence dates
- Présence raison pour cancelled
- Absence doublons session_id
- Format dates ISO 8601

### Gestion erreurs

```python
try:
    planning = load_week_planning("S071")
except FileNotFoundError:
    # Fallback workflow standard
    logger.warning("Planning non trouvé, mode standard")
except ValueError as e:
    # Planning invalide
    logger.error(f"Planning invalide : {e}")
```

## Exemples Concrets

### Exemple 1 : Semaine S070

**Contexte :** Semaine reprise avec 1 annulation + 1 repos

- **S070-01 à S070-03** : Séances exécutées normalement
- **S070-04** : Annulée (problème matériel cassette)
- **S070-05 à S070-06** : Séances exécutées
- **S070-07** : Repos planifié dimanche

**TSS :** 215 réalisé / 262 planifié (82%)

### Exemple 2 : Utilisation du module

```python
# 1. Charger planning
planning = load_week_planning("S070")

# 2. Valider
if not validate_week_planning(planning):
    raise ValueError("Planning invalide")

# 3. Récupérer activités API
from prepare_analysis import IntervalsAPI
api = IntervalsAPI(athlete_id="i151223", api_key="KEY")
activities = api.get_activities(oldest="2025-12-02", newest="2025-12-08")

# 4. Réconcilier
result = reconcile_planned_vs_actual(planning, activities)

# 5. Traiter sessions
for session in planning['planned_sessions']:
    if session['status'] == 'rest_day':
        markdown = generate_rest_day_entry(...)
    elif session['status'] == 'cancelled':
        markdown = generate_cancelled_session_entry(...)
```

## Roadmap

### Implémenté ✅

- [x] Chargement et validation planning
- [x] Génération markdown repos
- [x] Génération markdown annulation
- [x] Réconciliation activités
- [x] Tests unitaires (14 tests)
- [x] Documentation complète
- [x] Démonstration S070

### À implémenter 🚧

- [ ] Intégration workflow_coach.py
- [ ] Support API réelle Intervals.icu (récupération métriques)
- [ ] CLI pour créer/éditer plannings
- [ ] Validation schema JSON stricte
- [ ] Génération rapports hebdomadaires
- [ ] Support séances "replaced"
- [ ] Export statistiques TSS

## Support

### Documentation

- Ce fichier : `docs/GESTION_REPOS_ANNULATIONS.md`
- Module : `scripts/rest_and_cancellations.py` (docstrings complètes)
- Tests : `scripts/test_rest_and_cancellations.py`
- Démo : `scripts/demo_rest_handling.py`

### Ressources

- Template planning : `data/week_planning/week_planning_template.json`
- Exemple S070 : `data/week_planning/week_planning_S070.json`
- Output exemple : `data/week_planning/demo_output_S070.md`

### Commandes utiles

```bash
# Créer nouveau planning
cp data/week_planning/week_planning_template.json \
   data/week_planning/week_planning_SXXX.json

# Tester planning
python3 -c "from rest_and_cancellations import load_week_planning; \
            print(load_week_planning('SXXX'))"

# Exécuter tests
python3 scripts/test_rest_and_cancellations.py

# Démo complète
python3 scripts/demo_rest_handling.py
```

## Changelog

### Version 1.0 (Décembre 2025)

**Ajouté :**
- Module `rest_and_cancellations.py` avec 6 fonctions principales
- Support planning JSON hebdomadaire
- Génération markdown repos planifiés
- Génération markdown séances annulées
- Réconciliation planning vs activités réelles
- Suite tests unitaires (14 tests, 100% réussis)
- Script démonstration avec exemple S070
- Documentation complète
- Template JSON réutilisable

**Fonctionnalités :**
- Validation automatique structure planning
- Gestion fallback si planning absent
- Support métriques wellness (sommeil, HRV, FC repos)
- Détection activités non planifiées
- Gestion multiples activités même jour
- Logging structuré avec résumé réconciliation

---

**Auteur :** Implémenté avec Claude Code
**Date :** Décembre 2025
**Licence :** Projet personnel
