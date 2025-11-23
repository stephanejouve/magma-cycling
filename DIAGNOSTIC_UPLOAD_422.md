# Diagnostic Erreur 422 - Upload Workouts

## Problème Observé

Lors du premier test d'upload, **toutes les requêtes échouent** avec :
```
❌ Erreur HTTP : 422 Client Error: Unprocessable Entity
   Réponse : N/A
```

## Erreur HTTP 422 - Signification

L'erreur **422 Unprocessable Entity** signifie que :
- ✅ La requête HTTP est correcte (syntaxe OK)
- ✅ L'authentification est valide (pas d'erreur 401)
- ❌ **Les données ne sont pas au format attendu par l'API**

## Causes Probables

### 1. Format de Date Incomplet

**Problème** : `start_date_local` sans heure
```json
{
  "start_date_local": "2025-11-24"
}
```

**Solution possible** :
```json
{
  "start_date_local": "2025-11-24T00:00:00"
}
```

### 2. Format de Description Non Reconnu

**Problème** : Description en texte libre non acceptée

L'API Intervals.icu pourrait nécessiter :
- Un format Markdown spécifique
- Une structure JSON avec `workout_doc`
- Des champs additionnels comme `type`

### 3. Champs Manquants

Champs potentiellement requis :
- `type` : Type d'événement/workout
- `workout_doc` : Structure du workout au lieu de `description`
- `color` : Couleur dans le calendrier
- `athlete_id` : ID de l'athlète (redondant mais peut-être requis)

## Solutions à Tester

### Solution 1 : Ajouter l'Heure à la Date

Modifier `upload_workouts.py` ligne 151 :

```python
# AVANT
"start_date_local": workout['date']

# APRÈS
"start_date_local": f"{workout['date']}T08:00:00"
```

### Solution 2 : Ajouter le Champ Type

```python
event_data = {
    "category": "WORKOUT",
    "type": "Ride",  # ← NOUVEAU
    "name": workout['name'],
    "description": workout['description'],
    "start_date_local": workout['date']
}
```

### Solution 3 : Utiliser workout_doc

Au lieu de `description` texte, utiliser une structure :

```python
event_data = {
    "category": "WORKOUT",
    "name": workout['name'],
    "workout_doc": {
        "description": workout['description']
    },
    "start_date_local": workout['date']
}
```

### Solution 4 : Consulter l'API

Faire une requête GET pour voir le format exact d'un workout existant :

```bash
curl -u "API_KEY:YOUR_KEY" \
  "https://intervals.icu/api/v1/athlete/i151223/events?oldest=2025-11-01&newest=2025-11-30"
```

Cela montrera la structure exacte attendue.

## Actions Immédiates

### 1. Améliorer le Diagnostic

✅ **FAIT** : Modification de `create_event()` pour afficher plus de détails :
```python
if e.response is not None:
    try:
        error_detail = e.response.json()
        print(f"   Détail : {error_detail}")
    except:
        print(f"   Réponse : {e.response.text}")
print(f"   Données envoyées : {event_data}")
```

### 2. Tester avec Script de Diagnostic

✅ **CRÉÉ** : `scripts/test_create_event.py`

Usage :
```bash
python3 scripts/test_create_event.py
```

Ce script teste :
- Format minimal avec date seule
- Format avec date + heure

### 3. Consulter un Workout Existant

Créer un workout manuellement sur Intervals.icu, puis le récupérer via API pour voir la structure :

```python
from prepare_analysis import IntervalsAPI

api = IntervalsAPI(athlete_id, api_key)
events = api.get_events(oldest="2025-11-01", newest="2025-11-30")

# Trouver un workout
for event in events:
    if event.get('category') == 'WORKOUT':
        print(json.dumps(event, indent=2))
        break
```

## Prochaines Étapes

1. **Relancer upload avec logs améliorés** :
   ```bash
   python3 scripts/upload_workouts.py S069 \
       --start-date 2025-11-24 \
       --dry-run
   ```
   → Devrait afficher le détail de l'erreur

2. **Tester les solutions** :
   - Solution 1 : Date avec heure
   - Solution 2 : Ajouter `type: "Ride"`
   - Solution 3 : Consulter workout existant

3. **Documenter la solution** :
   Une fois trouvée, mettre à jour :
   - `upload_workouts.py`
   - `UPLOAD_WORKOUTS_GUIDE.md`
   - `API_METHOD_TO_ADD.md`

## Ressources

- Documentation API Intervals.icu : https://intervals.icu/api
- Forum Intervals.icu : https://forum.intervals.icu
- Support : support@intervals.icu

## Commit des Corrections

Une fois la solution trouvée, créer un commit :
```bash
git add scripts/prepare_analysis.py scripts/upload_workouts.py
git commit -m "Fix: Correction erreur 422 upload workouts"
```
