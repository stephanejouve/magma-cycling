# Guide d'Intégration - Gestion Repos/Annulations dans Workflow

## Vue d'ensemble

Ce guide explique comment intégrer le module `rest_and_cancellations.py` dans le workflow existant `workflow_coach.py`.

## Architecture actuelle vs. nouvelle

### Workflow actuel (simplifié)

```python
# workflow_coach.py
def run():
    1. Welcome
    2. Detect gaps
    3. Collect feedback
    4. Prepare analysis  → API Intervals.icu
    5. Paste to Claude
    6. Validate
    7. Insert analysis
    8. Git commit
```

### Nouveau workflow (avec planning)

```python
# workflow_coach.py + rest_and_cancellations.py
def run():
    1. Welcome
    1b. Load week planning (si disponible)
    1c. Detect gaps vs planning
    2. Collect feedback
    3. Prepare analysis + check planning
    4. Paste to Claude (ou auto-generate pour repos/annulations)
    5. Validate
    6. Insert analysis
    6b. Generate rest/cancelled entries
    7. Git commit avec résumé semaine
```

## Modifications à apporter

### 1. Ajouter imports dans workflow_coach.py

```python
# En haut du fichier workflow_coach.py
from rest_and_cancellations import (
    load_week_planning,
    validate_week_planning,
    generate_rest_day_entry,
    generate_cancelled_session_entry,
    reconcile_planned_vs_actual,
)
```

### 2. Ajouter argument --week-planning

```python
# Dans main()
parser.add_argument(
    '--week-planning',
    help="Fichier planning JSON (ex: data/week_planning/week_planning_S070.json)"
)

parser.add_argument(
    '--week-id',
    help="ID semaine pour auto-load planning (ex: S070)"
)
```

### 3. Modifier __init__ de WorkflowCoach

```python
def __init__(self, skip_feedback=False, skip_git=False,
             activity_id=None, week_planning=None, week_id=None):
    self.skip_feedback = skip_feedback
    self.skip_git = skip_git
    self.activity_id = activity_id
    self.week_planning_file = week_planning
    self.week_id = week_id
    self.planning = None
    self.reconciliation = None
    # ... reste identique
```

### 4. Nouvelle étape : Chargement planning

```python
def step_1b_load_planning(self):
    """Étape 1b : Charger le planning hebdomadaire si disponible"""
    if not self.week_id and not self.week_planning_file:
        return  # Mode standard sans planning

    self.clear_screen()
    self.print_header(
        "📋 Chargement Planning Hebdomadaire",
        "Étape 1b/8 : Gestion repos et annulations"
    )

    try:
        if self.week_id:
            self.planning = load_week_planning(self.week_id)
            print(f"✓ Planning chargé : {self.week_id}")
        elif self.week_planning_file:
            # Charger depuis fichier custom
            import json
            from pathlib import Path
            with open(Path(self.week_planning_file), 'r') as f:
                self.planning = json.load(f)
            print(f"✓ Planning chargé : {self.week_planning_file}")

        # Validation
        if not validate_week_planning(self.planning):
            print("⚠️  Planning invalide, mode standard activé")
            self.planning = None
            return

        # Afficher résumé
        print(f"  Période : {self.planning['start_date']} → {self.planning['end_date']}")
        print(f"  Sessions : {len(self.planning['planned_sessions'])}")

        # Compter par statut
        statuses = {}
        for s in self.planning['planned_sessions']:
            status = s['status']
            statuses[status] = statuses.get(status, 0) + 1

        print(f"  Exécutées : {statuses.get('completed', 0)}")
        print(f"  Annulées : {statuses.get('cancelled', 0)}")
        print(f"  Repos : {statuses.get('rest_day', 0)}")

    except Exception as e:
        print(f"⚠️  Erreur chargement planning : {e}")
        print("   Mode standard activé")
        self.planning = None

    self.wait_user()
```

### 5. Modifier step_1c_detect_gaps (intégrer réconciliation)

```python
def step_1c_detect_gaps(self):
    """Étape 1c : Détecter gaps avec support planning"""

    # Si pas de planning, comportement actuel
    if not self.planning:
        self.step_1b_detect_gaps()  # Méthode existante
        return

    # Avec planning : réconciliation
    self.clear_screen()
    self.print_header(
        "🔍 Réconciliation Planning vs Activités",
        "Étape 1c/8 : Comparaison planifié/réalisé"
    )

    # Récupérer activités
    config_path = Path.home() / ".intervals_config.json"
    if not config_path.exists():
        print("⚠️  Config API non trouvée, skip réconciliation")
        self.wait_user()
        return

    with open(config_path, 'r') as f:
        config = json.load(f)

    from prepare_analysis import IntervalsAPI
    api = IntervalsAPI(
        athlete_id=config['athlete_id'],
        api_key=config['api_key']
    )

    activities = api.get_activities(
        oldest=self.planning['start_date'],
        newest=self.planning['end_date']
    )

    # Réconcilier
    self.reconciliation = reconcile_planned_vs_actual(
        self.planning,
        activities
    )

    # Afficher résumé
    print(f"📊 RÉCONCILIATION {self.planning['week_id']}")
    print()
    print(f"✅ Exécutées : {len(self.reconciliation['matched'])}")
    print(f"❌ Annulées : {len(self.reconciliation['cancelled'])}")
    print(f"💤 Repos : {len(self.reconciliation['rest_days'])}")
    print(f"❓ Non planifiées : {len(self.reconciliation['unplanned'])}")

    # Détails
    if self.reconciliation['cancelled']:
        print("\n⚠️  Sessions annulées à documenter :")
        for s in self.reconciliation['cancelled']:
            print(f"  • {s['session_id']} - {s['name']}")

    if self.reconciliation['rest_days']:
        print("\n💤 Repos planifiés à documenter :")
        for s in self.reconciliation['rest_days']:
            print(f"  • {s['session_id']} - {s['name']}")

    self.wait_user()
```

### 6. Nouvelle étape : Génération auto repos/annulations

```python
def step_6b_generate_special_entries(self):
    """Étape 6b : Générer entrées repos/annulations automatiquement"""

    if not self.reconciliation:
        return  # Pas de planning, skip

    if (not self.reconciliation['rest_days'] and
        not self.reconciliation['cancelled']):
        return  # Rien à générer

    self.clear_screen()
    self.print_header(
        "🤖 Génération Automatique Repos/Annulations",
        "Étape 6b/8 : Entrées markdown spéciales"
    )

    print("Génération automatique des entrées pour :")
    print(f"  💤 Repos planifiés : {len(self.reconciliation['rest_days'])}")
    print(f"  ❌ Séances annulées : {len(self.reconciliation['cancelled'])}")
    print()

    # Récupérer métriques (depuis API wellness)
    # TODO: Implémenter récupération vraies métriques
    # Pour l'instant, métriques par défaut
    metrics_default = {"ctl": 50, "atl": 35, "tsb": 15}

    entries_generated = []

    # Générer repos
    for session in self.reconciliation['rest_days']:
        print(f"Génération repos : {session['session_id']}...")
        markdown = generate_rest_day_entry(
            session_data=session,
            metrics_pre=metrics_default,
            metrics_post=metrics_default,
            athlete_feedback=None  # TODO: récupérer depuis wellness
        )
        entries_generated.append((session['date'], markdown))

    # Générer annulations
    for session in self.reconciliation['cancelled']:
        print(f"Génération annulation : {session['session_id']}...")
        markdown = generate_cancelled_session_entry(
            session_data=session,
            metrics_pre=metrics_default,
            reason=session['cancellation_reason']
        )
        entries_generated.append((session['date'], markdown))

    # Insérer dans workouts-history.md
    history_file = self.project_root / "logs" / "workouts-history.md"

    # Trier par date
    entries_generated.sort(key=lambda x: x[0])

    # Insérer
    for date, markdown in entries_generated:
        # TODO: Implémenter insertion intelligente
        # Pour l'instant, append
        with open(history_file, 'a', encoding='utf-8') as f:
            f.write(markdown)
            f.write("\n")

    print()
    print(f"✓ {len(entries_generated)} entrées générées et insérées")
    self.wait_user()
```

### 7. Mettre à jour run()

```python
def run(self):
    """Orchestrer le workflow complet"""
    try:
        self.step_1_welcome()
        self.step_1b_load_planning()      # NOUVEAU
        self.step_1c_detect_gaps()        # MODIFIÉ (avec réconciliation)
        self.step_2_collect_feedback()
        self.step_3_prepare_analysis()
        self.step_4_paste_prompt()
        self.step_5_validate_analysis()
        self.step_6_insert_analysis()
        self.step_6b_generate_special_entries()  # NOUVEAU
        self.step_7_git_commit()
        self.show_summary()
    except KeyboardInterrupt:
        # ... identique
```

## Usage après intégration

### Mode standard (sans planning)

```bash
# Comportement actuel inchangé
python3 scripts/workflow_coach.py
```

### Mode avec planning

```bash
# Auto-load planning par week-id
python3 scripts/workflow_coach.py --week-id S070

# Load planning custom
python3 scripts/workflow_coach.py \
    --week-planning data/week_planning/week_planning_S070.json

# Combiné avec autres options
python3 scripts/workflow_coach.py \
    --week-id S070 \
    --skip-feedback \
    --skip-git
```

## Workflow semaine type

### 1. Lundi : Créer planning semaine

```bash
# Copier template
cp data/week_planning/week_planning_template.json \
   data/week_planning/week_planning_S071.json

# Éditer et planifier
nano data/week_planning/week_planning_S071.json
```

### 2. Pendant la semaine : Analyser au fil de l'eau

```bash
# Après chaque séance
python3 scripts/workflow_coach.py --week-id S071
```

Le script :
- Détecte automatiquement quelle séance analyser
- Propose repos/annulations si nécessaire
- Met à jour le tracking

### 3. Dimanche soir : Bilan semaine

```bash
# Génération complète
python3 scripts/workflow_coach.py --week-id S071

# Commit final avec résumé
git commit -m "Semaine S071 complète

- 5/7 séances exécutées
- 1 annulation (matériel)
- 1 repos planifié
- TSS: 215/262 (82%)

🤖 Generated with Claude Code"
```

## Fallback et compatibilité

### Garanties de compatibilité

1. **Sans planning** : Comportement actuel 100% préservé
2. **Planning invalide** : Fallback automatique mode standard
3. **Erreur chargement** : Warning + continuation mode standard
4. **API indisponible** : Skip réconciliation, workflow continue

### Tests de régression

```bash
# Vérifier que le mode standard fonctionne toujours
python3 scripts/workflow_coach.py --skip-feedback --skip-git

# Vérifier avec planning
python3 scripts/workflow_coach.py --week-id S070 --skip-git

# Tests unitaires
python3 scripts/test_rest_and_cancellations.py
```

## Roadmap intégration

### Phase 1 : Intégration basique ✅

- [x] Module rest_and_cancellations.py
- [x] Tests unitaires
- [x] Documentation

### Phase 2 : Intégration workflow_coach (À faire)

- [ ] Ajouter arguments CLI
- [ ] Implémenter step_1b_load_planning()
- [ ] Modifier step_1c_detect_gaps()
- [ ] Implémenter step_6b_generate_special_entries()
- [ ] Mettre à jour run()
- [ ] Tests intégration

### Phase 3 : Amélioration métriques (À faire)

- [ ] Récupération métriques wellness depuis API
- [ ] Cache métriques pour performance
- [ ] Support feedback athlète pour repos
- [ ] Historique métriques TSB/CTL/ATL

### Phase 4 : Reporting (À faire)

- [ ] Génération rapport hebdomadaire
- [ ] Statistiques TSS completion
- [ ] Export CSV métriques
- [ ] Visualisations (optionnel)

## Exemple intégration minimale

Si vous voulez intégrer rapidement sans modifier workflow_coach.py :

### Script standalone : `process_week_planning.py`

```python
#!/usr/bin/env python3
"""
Script standalone pour traiter un planning hebdomadaire
Usage: python3 scripts/process_week_planning.py --week-id S070
"""

import argparse
from pathlib import Path
from rest_and_cancellations import process_week_with_rest_handling
import json

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--week-id', required=True)
    args = parser.parse_args()

    # Charger config API
    config_path = Path.home() / ".intervals_config.json"
    with open(config_path, 'r') as f:
        config = json.load(f)

    # Charger planning
    from rest_and_cancellations import load_week_planning
    planning = load_week_planning(args.week_id)

    # Traiter
    result = process_week_with_rest_handling(
        week_id=args.week_id,
        start_date=planning['start_date'],
        end_date=planning['end_date'],
        athlete_id=config['athlete_id'],
        api_key=config['api_key'],
        output_file=Path('logs/workouts-history.md')
    )

    print(f"\n✓ Semaine {args.week_id} traitée")
    print(f"  TSS: {result['tss_completed']}/{result['tss_planned']}")

if __name__ == '__main__':
    main()
```

Usage :

```bash
python3 scripts/process_week_planning.py --week-id S070
```

## Support

### Debug

```python
# Activer logging verbose
import logging
logging.basicConfig(level=logging.DEBUG)

# Tester chargement planning
from rest_and_cancellations import load_week_planning
planning = load_week_planning("S070")
print(planning)
```

### Questions fréquentes

**Q: Que se passe-t-il si j'oublie de créer le planning ?**
R: Le workflow fonctionne en mode standard comme avant.

**Q: Puis-je modifier le planning après avoir commencé la semaine ?**
R: Oui, éditez simplement le JSON. La réconciliation s'adapte.

**Q: Comment marquer une séance comme annulée après coup ?**
R: Éditez le JSON, changez status à "cancelled", ajoutez cancellation_reason.

**Q: Les métriques sont-elles récupérées automatiquement ?**
R: Pas encore dans v1.0, métriques par défaut. À venir en v1.1.

---

**Prochaine étape :** Implémenter les modifications dans workflow_coach.py
**Statut :** Module prêt, intégration à faire
**Contact :** Voir documentation principale
