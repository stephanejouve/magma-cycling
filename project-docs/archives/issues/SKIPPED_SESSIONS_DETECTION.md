# Système de Détection des Séances Sautées

## Vue d'ensemble

Le système de détection des séances sautées permet d'identifier automatiquement les workouts planifiés dans Intervals.icu qui n'ont pas été exécutés. Cette fonctionnalité comble un gap critique : **détecter non seulement les séances réalisées mais non analysées, mais aussi les séances planifiées mais non réalisées**.

## Fichiers concernés

### Nouveaux fichiers

1. **`scripts/planned_sessions_checker.py`**
   - Module principal de détection
   - Classe `PlannedSessionsChecker`
   - Méthodes de comparaison planifié vs réalisé
   - Génération markdown pour séances sautées

2. **`scripts/test_skipped_detection.py`**
   - Script de test autonome
   - Validation du système
   - Exemples d'utilisation
   - Rapport d'impact TSS

3. **`patches/add_skipped_sessions_detection.patch`**
   - Patch pour `workflow_coach.py`
   - Intégration dans step_1b_detect_all_gaps()
   - Affichage unifié des gaps

4. **`patches/add_skipped_status_support.patch`**
   - Patch pour `rest_and_cancellations.py`
   - Support statut "skipped"
   - Génération markdown séances sautées

## Installation

### Étape 1 : Copier le nouveau module

```bash
# Le fichier planned_sessions_checker.py est déjà créé
# Aucune action nécessaire
```

### Étape 2 : Appliquer les patches

```bash
cd /path/to/cyclisme-training-logs

# Patch 1 : Intégration workflow_coach.py
git apply patches/add_skipped_sessions_detection.patch

# Patch 2 : Support rest_and_cancellations.py
git apply patches/add_skipped_status_support.patch
```

### Étape 3 : Vérifier l'installation

```bash
# Test basique
python3 scripts/test_skipped_detection.py

# Test sur 14 jours
python3 scripts/test_skipped_detection.py --days 14

# Test avec génération markdown
python3 scripts/test_skipped_detection.py --generate-markdown
```

## Utilisation

### Détection automatique dans le workflow

Le système est **automatiquement intégré** dans `workflow_coach.py` :

```bash
python3 scripts/workflow_coach.py
```

**Comportement :**
1. Détecte activités exécutées non analysées (existant)
2. Détecte repos planifiés (existant si JSON présent)
3. **NOUVEAU** : Détecte séances planifiées sautées via API
4. Affiche menu unifié avec toutes les options

**Exemple d'affichage :**

```
📊 RÉSUMÉ GAPS DÉTECTÉS
======================================================================

🚴 Séances exécutées non analysées : 2
   1. [2025-12-10] S070-02-INT-SweetSpotProgression-V001
   2. [2025-12-11] S070-03-REC-RecuperationActive-V001

⏭️  Séances planifiées sautées : 1
   • [2025-12-09] S070-01-END-EnduranceBase-V001 (54 TSS, il y a 4j)

💡 QUE VEUX-TU FAIRE ?
======================================================================

  [1] Traiter UNE séance exécutée (workflow classique)
  [2] Traiter repos/annulations/sautées en batch
  [3] Traiter TOUT en batch
  [0] Quitter
```

### Test manuel

Pour tester la détection sans passer par le workflow complet :

```bash
# Test derniers 7 jours
python3 scripts/test_skipped_detection.py

# Test personnalisé
python3 scripts/test_skipped_detection.py --days 14 --generate-markdown

# Mode debug
python3 scripts/test_skipped_detection.py --verbose
```

### Intégration dans scripts custom

```python
from planned_sessions_checker import PlannedSessionsChecker

# Initialiser
checker = PlannedSessionsChecker(
    athlete_id="i151223",
    api_key="votre_clé"
)

# Détecter séances sautées
skipped = checker.detect_skipped_sessions(
    start_date="2025-12-01",
    end_date="2025-12-13",
    exclude_future=True
)

# Traiter résultats
for session in skipped:
    print(f"Sautée : {session['planned_name']}")
    print(f"Date : {session['planned_date']}")
    print(f"TSS perdu : {session['planned_tss']}")
```

## Algorithme de détection

### Étape 1 : Récupération données

```
API Intervals.icu
├── GET /athlete/{id}/events
│   └── Filtre : category=WORKOUT
│   └── Résultat : Workouts planifiés
│
└── GET /athlete/{id}/activities
    └── Résultat : Activités réalisées
```

### Étape 2 : Matching

Pour chaque workout planifié :

1. **Vérifier date**
   - Si futur ET `exclude_future=True` → Skip
   - Sinon → Continuer

2. **Chercher activité correspondante**
   - Tolérance temporelle : ±6 heures
   - Correspondance par code (ex: S070-01)
   - Correspondance par nom
   - Correspondance inverse

3. **Classifier**
   - Si match trouvé → OK (séance exécutée)
   - Si pas de match → **SKIPPED**

### Étape 3 : Résultats

Structure des séances sautées :

```python
{
    'planned_id': 'xxx',
    'planned_date': '2025-12-09',
    'planned_date_iso': '2025-12-09T06:00:00Z',
    'planned_name': 'S070-01-END-EnduranceBase-V001',
    'planned_tss': 54,
    'planned_duration': 3600,  # secondes
    'planned_description': 'Endurance Z2 60min',
    'status': 'SKIPPED',
    'day_of_week': 'Monday',
    'days_ago': 4
}
```

## Format markdown généré

### Template séance sautée

```markdown
### S070-01-END-EnduranceBase-V001 [SAUTÉE]
Date : 09/12/2025 (Monday)

#### Métriques Pré-séance
- CTL : 55
- ATL : 48
- TSB : 7

#### Séance Planifiée
- Charge prévue : 54 TSS
- Durée prévue : 60 min
- Type : END

#### Statut
- ⏭️ **SÉANCE SAUTÉE**
- Non exécutée (il y a 4 jours)
- Raison : Raison non documentée

#### Impact sur Métriques
- TSS non réalisé : -54
- CTL : Aucun changement (séance non effectuée)
- ATL : Diminution naturelle du à l'absence de charge
- TSB : Amélioration probable (récupération passive)

#### Recommandations Coach
- Évaluer raison du saut
- Ajuster planning semaine si nécessaire
- Vérifier cohérence avec objectifs CTL visé
- Considérer report si séance critique
- Documenter pattern si saut récurrent

#### Notes
Séance planifiée non exécutée. Impact sur progression hebdomadaire à évaluer.

---
```

## Cas d'usage

### Cas 1 : Détection automatique

**Situation** : Tu lances le workflow lundi, tu as sauté une séance samedi

**Workflow :**
```bash
python3 scripts/workflow_coach.py
```

**Résultat :**
- Détecte la séance sautée de samedi
- Affiche dans le menu des gaps
- Propose traitement en batch

### Cas 2 : Analyse hebdomadaire

**Situation** : Fin de semaine, bilan complet

**Workflow :**
```bash
# Test détection
python3 scripts/test_skipped_detection.py --days 7 --generate-markdown

# Voir impact TSS
python3 scripts/test_skipped_detection.py --days 7
```

**Résultat :**
- Rapport détaillé séances sautées
- Impact TSS calculé
- Exemples markdown prêts

### Cas 3 : Planning JSON existant

**Situation** : Tu utilises déjà `week_planning_SXXX.json`

**Comportement :**
- Détection API **complète** la détection JSON
- API détecte séances planifiées Intervals.icu
- JSON gère repos/annulations manuelles
- Les deux systèmes coexistent

## Différences avec rest_and_cancellations.py

### Ancien système (JSON manuel)

**Limitations :**
- Nécessite création manuelle `week_planning.json`
- Maintenance laborieuse
- Pas de synchronisation auto avec Intervals.icu
- Détecte uniquement ce qui est dans le JSON

**Avantages :**
- Contrôle total du planning
- Support repos/annulations avec raisons détaillées
- Indépendant de l'API

### Nouveau système (API automatique)

**Avantages :**
- **100% automatique** : Aucun JSON à maintenir
- **Temps réel** : Toujours synchronisé avec Intervals.icu
- **Exhaustif** : Détecte tous les workouts planifiés
- **Tolérant** : Gère modifications de dernière minute

**Limitations :**
- Dépend de l'API Intervals.icu
- Pas de raisons détaillées (sauf si ajoutées manuellement)

### Coexistence

Les deux systèmes **coexistent parfaitement** :

```python
# Dans workflow_coach.py step_1b_detect_all_gaps()

# 1. Détection API (automatique)
skipped_sessions_api = checker.detect_skipped_sessions(...)

# 2. Détection JSON (manuel si présent)
if planning_json_exists:
    reconciliation = reconcile_planned_vs_actual(...)
    cancelled_json = reconciliation['cancelled']

# 3. Fusion résultats
all_gaps = {
    'executed': unanalyzed_activities,
    'skipped_api': skipped_sessions_api,
    'rest_json': rest_days,
    'cancelled_json': cancelled_sessions
}
```

## Troubleshooting

### Erreur : "Config API non trouvée"

**Solution :**
```bash
# Créer ~/.intervals_config.json
cat > ~/.intervals_config.json << EOF
{
  "athlete_id": "i151223",
  "api_key": "votre_clé_api"
}
EOF
```

### Erreur : "Détection séances sautées impossible"

**Causes possibles :**
1. API Intervals.icu indisponible
2. Credentials invalides
3. Pas de workouts planifiés dans la période

**Solution :**
```bash
# Vérifier API
curl -u "API_KEY:votre_clé" \
  "https://intervals.icu/api/v1/athlete/i151223/events"

# Si erreur → vérifier credentials
# Si vide → pas de workouts planifiés (normal)
```

### Faux positifs

**Problème :** Séances détectées comme sautées mais en réalité exécutées

**Causes :**
- Nom d'activité différent du nom workout planifié
- Décalage horaire >6h entre planifié et exécuté
- Activité uploadée manuellement sans lien au workout

**Solutions :**
1. **Respecter convention nommage** : Inclure code semaine-jour (S070-01)
2. **Exécuter à l'heure prévue** : ±6h du workout planifié
3. **Lier activité au workout** : Dans Intervals.icu après upload

## Métriques et KPIs

Le système permet de tracker :

### TSS perdu

```python
total_tss_lost = sum(s['planned_tss'] for s in skipped_sessions)
```

### Taux d'exécution

```python
planned_count = len(planned_workouts)
executed_count = len(matched_activities)
execution_rate = (executed_count / planned_count) * 100
```

### Impact CTL estimé

```python
# Approximation : CTL baisse ~7 points/semaine sans entraînement
days_without = max(s['days_ago'] for s in skipped_sessions)
ctl_impact = -(days_without / 7) * 7
```

## Évolutions futures

### Court terme

- [ ] Enrichir raisons saut (formulaire interactif)
- [ ] Notification email si séance sautée
- [ ] Dashboard séances sautées (stats mensuelles)

### Moyen terme

- [ ] ML : Prédire probabilité saut de séance
- [ ] Auto-ajustement planning si pattern récurrent
- [ ] Intégration calendrier Google/Apple

### Long terme

- [ ] Analyse corrélations (saut vs sommeil, stress, météo)
- [ ] Recommandations intelligentes report/annulation
- [ ] Système de "crédit" TSS reportable

## Support

### Documentation

- `scripts/planned_sessions_checker.py` : Docstrings complètes
- `scripts/test_skipped_detection.py` : Exemples d'utilisation
- Ce fichier : Guide complet

### Questions fréquentes

**Q : Les séances sautées apparaissent-elles dans workouts-history.md ?**

R : Oui, si tu utilises l'option [2] ou [3] du workflow batch. Elles sont marquées `[SAUTÉE]` et documentées avec impact TSS.

**Q : Puis-je désactiver la détection auto ?**

R : Actuellement non, mais elle est non-bloquante. Si API indisponible, le workflow continue normalement.

**Q : Faut-il supprimer les JSON manuels ?**

R : Non, ils sont complémentaires. JSON pour repos/annulations manuelles, API pour détection auto séances sautées.

## Changelog

### v1.0.0 (2025-12-13)

- ✨ Création module `planned_sessions_checker.py`
- ✨ Intégration `workflow_coach.py`
- ✨ Support statut "skipped" dans `rest_and_cancellations.py`
- ✨ Script de test `test_skipped_detection.py`
- 📝 Documentation complète
- ✅ Tests validés sur derniers 7 jours

## Auteur

Système développé pour répondre au besoin de détection automatique des séances planifiées non exécutées, identifié lors de l'analyse du workflow le 13/12/2025.
