# Méthode API à Ajouter - IntervalsAPI

## Fichier à Modifier

`scripts/prepare_analysis.py` (dans ton répertoire local)

## Méthode à Ajouter à la Classe IntervalsAPI

```python
def create_event(self, event_data: Dict) -> Optional[Dict]:
    """
    Créer un événement (workout) sur Intervals.icu

    Args:
        event_data: Dictionnaire contenant :
            - category: "WORKOUT"
            - name: Nom du workout
            - description: Contenu au format Intervals.icu
            - start_date_local: Date au format YYYY-MM-DD

    Returns:
        Réponse API si succès, None sinon

    API Documentation:
        POST /api/v1/athlete/{id}/events
    """
    try:
        url = f"{self.base_url}/athlete/{self.athlete_id}/events"

        headers = {
            'Authorization': f'Basic {self._get_auth_token()}',
            'Content-Type': 'application/json'
        }

        response = requests.post(url, json=event_data, headers=headers)
        response.raise_for_status()

        return response.json()

    except requests.exceptions.HTTPError as e:
        print(f"❌ Erreur HTTP : {e}")
        print(f"   Réponse : {e.response.text if e.response else 'N/A'}")
        return None
    except Exception as e:
        print(f"❌ Erreur création événement : {e}")
        return None
```

## Emplacement dans la Classe

Ajouter après les méthodes existantes (`get_wellness`, `get_activities`, etc.)

## Test de la Méthode

```python
# Test basique
api = IntervalsAPI()

test_workout = {
    "category": "WORKOUT",
    "name": "Test Workout",
    "description": """Warmup
- 10m 50-65% 85rpm

Main set
- 20m 70% 90rpm

Cooldown
- 10m 65-50% 85rpm""",
    "start_date_local": "2025-11-24"
}

result = api.create_event(test_workout)
print(f"Résultat : {result}")
```

## Documentation API Intervals.icu

**Endpoint** : `POST /api/v1/athlete/{id}/events`

**Headers** :
```
Authorization: Basic {base64(API_KEY:)}
Content-Type: application/json
```

**Body** :
```json
{
  "category": "WORKOUT",
  "name": "Nom du workout",
  "description": "Contenu Intervals.icu format texte",
  "start_date_local": "2025-11-24"
}
```

**Réponse Succès** (201 Created) :
```json
{
  "id": 12345,
  "category": "WORKOUT",
  "name": "Nom du workout",
  "start_date_local": "2025-11-24",
  ...
}
```

**Réponse Erreur** (400/401/500) :
```json
{
  "error": "Message d'erreur"
}
```

## Alternative Si Méthode Manquante

Si tu ne veux pas modifier `prepare_analysis.py`, tu peux aussi créer une classe API locale dans `upload_workouts.py` :

```python
import requests
import base64
import os
from typing import Dict, Optional

class SimpleIntervalsAPI:
    """API minimale pour upload workouts"""

    def __init__(self):
        self.athlete_id = os.getenv('VITE_INTERVALS_ATHLETE_ID', 'i151223')
        self.api_key = os.getenv('VITE_INTERVALS_API_KEY')
        self.base_url = 'https://intervals.icu/api/v1'

        if not self.api_key:
            raise ValueError("API key manquante")

    def _get_auth_token(self) -> str:
        """Générer token Basic Auth"""
        credentials = f"API_KEY:{self.api_key}"
        return base64.b64encode(credentials.encode()).decode()

    def create_event(self, event_data: Dict) -> Optional[Dict]:
        """Créer un workout"""
        try:
            url = f"{self.base_url}/athlete/{self.athlete_id}/events"

            headers = {
                'Authorization': f'Basic {self._get_auth_token()}',
                'Content-Type': 'application/json'
            }

            response = requests.post(url, json=event_data, headers=headers)
            response.raise_for_status()

            return response.json()
        except Exception as e:
            print(f"❌ Erreur : {e}")
            return None
```

## Vérification Post-Implémentation

```bash
# Tester avec dry-run
python3 scripts/upload_workouts.py S069 \
    --start-date 2025-11-24 \
    --dry-run

# Si ça passe, tester upload réel
python3 scripts/upload_workouts.py S069 \
    --start-date 2025-11-24
```
