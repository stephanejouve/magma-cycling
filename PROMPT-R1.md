---

### 🎯 SPRINT R1 - Unification IntervalsAPI (P0 - CRITIQUE)

**Contexte :**
Le projet contient 3 implémentations différentes de la classe `IntervalsAPI` dispersées dans le code, causant :
- Bugs de maintenance (exemple : `get_events()` manquant dans sync_intervals.py le 30/12)
- Incohérences comportementales entre fichiers
- ~200 lignes de code dupliqué sur 16 fichiers consommateurs

**Objectif du Sprint :**
Créer un client API unifié et migrer tous les consommateurs vers ce nouveau module.

**Fichiers concernés (3 implémentations existantes à analyser) :**
1. `prepare_analysis.py` (lignes 68-187) - **Version la plus complète** ✅
2. `sync_intervals.py` (lignes 60-122) - Version partielle
3. `check_activity_sources.py` (lignes 21-43) - Version minimale

**Livrables attendus :**

**Phase 1 - Création du module unifié**
```
cyclisme_training_logs/api/
├── __init__.py
└── intervals_client.py
```

Le module `intervals_client.py` doit implémenter une classe `IntervalsClient` avec :
- **Méthodes essentielles** : `get_athlete()`, `get_activities()`, `get_activity()`, `get_wellness()`, `get_events()`, `create_event()`, `get_planned_workout()`
- **Authentification** : Via `requests.Session` avec pattern API_KEY existant
- **Type hints** : Complets (typing.Optional, typing.List, typing.Dict, etc.)
- **Docstrings** : Google Style (déjà adopté dans le projet)
- **Gestion d'erreurs** : `response.raise_for_status()` systématique

**Phase 2 - Migration progressive**

Identifier et migrer les 16 fichiers consommateurs vers `IntervalsClient` :
```python
# AVANT
from cyclisme_training_logs.sync_intervals import IntervalsAPI
api = IntervalsAPI(athlete_id, api_key)

# APRÈS
from cyclisme_training_logs.api.intervals_client import IntervalsClient
client = IntervalsClient(athlete_id, api_key)
```

**Fichiers à migrer (liste non exhaustive) :**
- `weekly_aggregator.py`
- `weekly_planner.py`
- `workflow_coach.py`
- `rest_and_cancellations.py`
- `upload_workouts.py`
- `backfill_history.py`
- `insert_analysis.py`
- `planned_sessions_checker.py`
- + autres importateurs à identifier

**Phase 3 - Tests et validation**

Créer les tests unitaires :
```
tests/api/
└── test_intervals_client.py
```

Tests minimum :
- `test_intervals_client_authentication()` - Vérifier session setup
- `test_get_activities()` - Avec/sans paramètres oldest/newest
- `test_get_wellness()` - Parsing correct des métriques
- `test_get_events()` - Filtrage par dates
- `test_create_event()` - Création workout planifié
- `test_error_handling()` - Gestion HTTP errors

**Phase 4 - Cleanup**

Au choix du dev :
- **Option A (recommandée)** : Supprimer complètement les 3 anciennes implémentations
- **Option B (conservative)** : Créer des wrappers avec deprecation warnings

**Critères de succès :**
- [ ] Module `api/intervals_client.py` créé et documenté
- [ ] Tous les imports migrés vers `IntervalsClient`
- [ ] Tests unitaires passent (nouveaux + existants préservés)
- [ ] Aucune régression fonctionnelle sur workflows wa/wp/wu
- [ ] Code legacy géré (supprimé ou wrappers)

**Points de vigilance :**
- ⚠️ Ne PAS casser les workflows existants (wa, wp, wu, servo-mode)
- ⚠️ Préserver exactement le comportement API Intervals.icu actuel
- ⚠️ Vérifier que TOUS les consommateurs sont migrés avant cleanup final
- ⚠️ Tester sur données réelles S074 si possible

**Questions pour le dev :**
1. Vois-tu des risques de régression non identifiés dans ce plan ?
2. Préfères-tu une migration big-bang ou progressive (fichier par fichier) ?
3. Faut-il créer des wrappers de compatibilité temporaires ou cleanup direct ?
4. Estimation de charge : combien de sessions de travail pour R1 complet ?

**Livrable attendu :**
- Archive `.tar.gz` du code refactoré
- Commentaire final du dev avec :
  - Décisions techniques prises
  - Difficultés rencontrées
  - Points d'attention pour R2-R5
  - Résultats des tests

---

