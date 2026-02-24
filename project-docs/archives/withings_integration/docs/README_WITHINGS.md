# Intégration Withings → Intervals.icu

## Vue d'ensemble

Ce système synchronise automatiquement vos données Withings (sommeil et poids) vers Intervals.icu pour optimiser votre suivi d'entraînement cycliste.

### Fonctionnalités

✅ **Synchronisation automatique**
- Poids quotidien
- Données de sommeil détaillées (durée, qualité, sommeil profond)
- Mise à jour automatique dans Intervals.icu

✅ **Analyse intelligente**
- Évaluation de la disponibilité pour entraînement intensif
- Recommandations basées sur la qualité du sommeil
- Détection de la dette de sommeil
- Alertes avant séances VO2 max

✅ **Rapports**
- Résumé hebdomadaire sommeil/poids
- Tendances et variations
- Recommandations d'intensité

## Installation

### 1. Prérequis

```bash
pip install withings-api requests python-dotenv
```

### 2. Configuration Withings Developer

Vous avez déjà créé l'application dans le Developer Dashboard :
- **Application**: Sync Withings Intervals
- **ClientID**: `your_withings_client_id_here`
- **Secret**: (à récupérer du Dashboard)
- **Callback URL**: `https://your-ngrok-url.ngrok-free.app/auth/withings/callback`

### 3. Setup initial (une seule fois)

```bash
# Définir le secret Withings
export WITHINGS_SECRET="votre_secret_depuis_dashboard"

# Exécuter le script de setup
python withings_setup.py
```

Ce script va :
1. Ouvrir votre navigateur pour autoriser l'application
2. Récupérer automatiquement le code d'autorisation
3. Échanger le code contre des tokens d'accès
4. Sauvegarder les credentials dans `withings_credentials.json`
5. Créer le fichier `.env.withings` avec votre configuration

**⚠️ Important**: Gardez `withings_credentials.json` **privé** et ne le commitez JAMAIS !

## Utilisation

### Synchronisation quotidienne

```bash
# Synchroniser les données d'aujourd'hui
python withings_sync.py sync

# Synchroniser les 7 derniers jours
python withings_sync.py sync 7
```

### Vérifier la disponibilité pour entraînement

```bash
python withings_sync.py readiness
```

**Sortie exemple:**
```
🎯 DISPONIBILITÉ ENTRAÎNEMENT:
   Sommeil: 7.2h
   Score: 82/100
   Recommandation: ALL_SYSTEMS_GO
   ✅ OK pour VO2 max
```

### Résumé hebdomadaire

```bash
python withings_sync.py summary
```

**Sortie exemple:**
```
😴 SOMMEIL (7 derniers jours)
   Moyenne: 6.8h/nuit
   Score moyen: 78/100
   Nuits >7h: 4/7
   Dette de sommeil: 1.4h
   ⚠️  Légère dette - Attention charge entraînement

📊 POIDS (7 derniers jours)
   Début semaine: 86.2kg
   Fin semaine: 85.8kg
   Variation: -0.4kg
```

## Automatisation

### Avec cron (Linux/Mac)

Ajoutez à votre crontab (`crontab -e`) :

```bash
# Synchronisation quotidienne à 7h du matin
0 7 * * * cd /path/to/project && python withings_sync.py sync

# Résumé hebdomadaire le dimanche à 20h
0 20 * * 0 cd /path/to/project && python withings_sync.py summary
```

### Avec Windows Task Scheduler

1. Créer une tâche planifiée
2. Programme: `python`
3. Arguments: `C:\path\to\withings_sync.py sync`
4. Déclencheur: Quotidien à 7h00

## Intégration avec votre workflow coaching

### Vérification avant séance VO2 max

```python
from withings_sync import get_training_readiness

readiness = get_training_readiness()

if readiness['ready']:
    print("✅ Conditions optimales - VO2 max autorisé")
    # Exécuter la séance
else:
    print(f"⚠️ {readiness['reason']}")
    print(f"Recommandation: {readiness['recommendation']}")
    # Adapter la séance
```

### Dans votre script de planification

```python
from withings_integration import WithingsIntegration
import json

# Charger API
with open('withings_credentials.json') as f:
    creds = json.load(f)

withings = WithingsIntegration(CLIENT_ID, CLIENT_SECRET, CALLBACK_URI)
withings.load_credentials(creds)

# Vérifier sommeil dernière nuit
sleep = withings.get_last_night_sleep()
assessment = withings.get_sleep_quality_assessment(sleep)

# Adapter l'entraînement
if assessment['recommended_intensity'] == 'recovery_only':
    print("⚠️ VETO séance intensive")
    # Forcer récupération active
elif assessment['recommended_intensity'] == 'all_systems_go':
    print("✅ Feu vert pour intensité maximale")
    # Autoriser VO2 max
```

## Structure des données

### Données de sommeil

```python
{
    'date': '2025-01-15',
    'total_sleep_hours': 7.2,
    'deep_sleep_minutes': 85,
    'light_sleep_minutes': 245,
    'rem_sleep_minutes': 102,
    'wakeup_count': 2,
    'sleep_score': 82,
    'breathing_disturbances': 5
}
```

### Données de poids

```python
{
    'date': '2025-01-15',
    'weight_kg': 85.8,
    'datetime': '2025-01-15T07:30:00',
    'timestamp': 1736928600
}
```

### Assessment entraînement

```python
{
    'ready_for_vo2': True,
    'sufficient_duration': True,
    'target_duration': 7.2,
    'sleep_score': 82,
    'deep_sleep_ok': True,
    'recommended_intensity': 'all_systems_go',
    'recommendations': [
        'Conditions optimales pour séance intensive'
    ]
}
```

## Critères de décision

### Recommandations d'intensité

| Sommeil | Score | Intensité | VO2 max |
|---------|-------|-----------|---------|
| < 5.5h | - | `recovery_only` | ❌ VETO |
| 5.5-7h | - | `endurance_max` | ❌ Non |
| ≥ 7h | < 75 | `moderate` | ⚠️ Déconseillé |
| ≥ 7h | ≥ 75 | `all_systems_go` | ✅ OK |

**Conditions supplémentaires pour VO2 max:**
- Sommeil profond ≥ 60min
- Score sommeil ≥ 75
- Durée totale ≥ 7h

## Dépannage

### Erreur "Credentials expired"

Les tokens se rafraîchissent automatiquement. Si ça échoue :

```bash
# Refaire l'authentification
python withings_setup.py
```

### Erreur "No data found"

Vérifiez que :
- Votre balance/tracker Withings est synchronisé
- Les données sont visibles dans l'app Withings
- Les autorisations app incluent bien `USER_METRICS` et `USER_ACTIVITY`

### Problème de callback

Si le callback ne fonctionne pas :
1. Vérifiez que ngrok/tunnel est actif
2. Vérifiez que l'URL dans Developer Dashboard correspond exactement
3. Vérifiez les ports (80/443)

## Fichiers importants

- `withings_integration.py` - Module principal API
- `withings_setup.py` - Configuration initiale
- `withings_sync.py` - Synchronisation quotidienne
- `withings_credentials.json` - Tokens (PRIVÉ, ne pas commiter)
- `.env.withings` - Configuration (PRIVÉ)

## Sécurité

❗ **Ne commitez JAMAIS** :
- `withings_credentials.json`
- `.env.withings`
- Tout fichier contenant le Secret Withings

Ajoutez au `.gitignore` :
```
withings_credentials.json
.env.withings
*.secret
```

## Support

En cas de problème :
1. Vérifier les logs de synchronisation
2. Tester manuellement `python withings_sync.py readiness`
3. Vérifier Developer Dashboard Withings
4. Régénérer credentials si nécessaire

## Évolutions futures

- [ ] Notifications push avant séances
- [ ] Intégration FC repos matinale
- [ ] Dashboard web visualisation
- [ ] Export rapport PDF hebdomadaire
- [ ] Analyse tendances long terme
