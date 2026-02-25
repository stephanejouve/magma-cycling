# Refactoring TODO - Cyclisme Training Logs

**Date d'analyse :** 30 décembre 2025
**Analysé par :** Claude Code
**Contexte :** Analyse post-livraison MOA 20251230

---

## 📊 Vue d'Ensemble

**Duplication totale identifiée :** ~590 lignes de code
**Fichiers concernés :** 16 fichiers Python
**Impact estimé du refactoring :** Réduction de 20-25% du code métier

---

## 🎯 Priorités de Refactoring

| ID | Composant | Fichiers | Lignes Dup. | Priorité | Complexité |
|----|-----------|----------|-------------|----------|------------|
| R0 | .env audit logging | 1 | ~50 | P0 | Faible |
| R1 | IntervalsAPI classes | 3 | ~200 | P0 | Moyenne |
| R2 | CTL/ATL/TSB handling | 9 | ~100 | P1 | Faible |
| R3 | JSON planning ops | 5 | ~150 | P1 | Moyenne |
| R4 | Date utilities | 11 | ~80 | P1 | Faible |
| R5 | Wellness fetching | 9 | ~60 | P2 | Faible |

---

## R0 - Surveillance Modifications .env (P0 - SÉCURITÉ CRITIQUE)

### Problème

**Le fichier `.env` contient des secrets critiques** et peut être modifié sans traçabilité :
- Clés API (Intervals.icu, Claude, Mistral, Brevo, Withings)
- Configuration athlète (FTP, seuils TSB, profil)
- Configuration MCP et Git

**Incident récent (23 février 2026) :**
- `.env` réduit à 10 lignes (210 octets vs 2.5KB) avec `VITE_INTERVALS_API_KEY=test_key`
- Restauration depuis Time Machine nécessaire
- `.env` restauré était obsolète (17 février) - manquait variables récentes
- Impact : `end-of-week` workflow incomplet, `week_planning_S082.json` non créé

### Impact

- **Sécurité** : Modifications non auditées de secrets
- **Fiabilité** : Variables manquantes cassent workflows
- **Debugging** : Impossible de savoir qui/quand/pourquoi .env modifié
- **Risque de fuite** : Pas de détection si secrets exposés

### Solution Recommandée

**Implémenter surveillance .env via Control Tower :**

1. **Pre-commit hook** `.git/hooks/pre-commit` :
   ```bash
   # Détecter modifications .env
   if git diff --cached --name-only | grep -q "^\.env$"; then
       echo "⚠️  .env modifié - audit requis"
       python scripts/audit_env_changes.py
   fi
   ```

2. **Script d'audit** `scripts/audit_env_changes.py` :
   ```python
   """Audit .env modifications avant commit."""
   import os
   from cyclisme_training_logs.planning.audit_log import AuditLog, OperationType

   def audit_env_change():
       # Comparer .env avec .env.backup
       # Logger dans Control Tower
       # Créer backup automatique
       audit_log.log_operation(
           operation=OperationType.MODIFY,
           week_id="N/A",
           status=OperationStatus.SUCCESS,
           tool="pre-commit-hook",
           description=".env modified",
           backup_path=".env.backup-YYYYMMDD-HHMMSS",
           username=os.getenv("USER")
       )
   ```

3. **Backup automatique** :
   - Créer `.env.backup-YYYYMMDD-HHMMSS` à chaque modification
   - Garder 10 backups les plus récents
   - Logger dans `.env_audit.jsonl`

4. **Validation** :
   - Vérifier que variables critiques existent : `VITE_INTERVALS_API_KEY`, `ATHLETE_FTP`, etc.
   - Warning si clé API = "test_key" ou similaire
   - Error si variables obligatoires manquantes

### Fichiers à créer

```
scripts/
├── audit_env_changes.py       # Script d'audit
└── validate_env.py            # Validation .env complet

.git/hooks/
└── pre-commit                 # Hook git (ou via pre-commit config)

.env.backup-template           # Template avec toutes variables
.env_audit.jsonl              # Log des modifications .env
```

### Livrable

✅ Détection automatique modifications .env
✅ Backup automatique avant chaque modification
✅ Validation variables critiques
✅ Audit trail complet dans Control Tower
✅ Restauration facile depuis backups

### Effort Estimé

- **Développement** : 2-3 heures
- **Tests** : 1 heure
- **Documentation** : 30 minutes
- **Total** : ~4 heures

### Status

🔴 **Non implémenté** - À faire en priorité absolue

**Date identification** : 23 février 2026
**Identifié par** : Claude Code (session hot reload)
**Contexte** : Incident .env corrompu lors développement MCP hot reload

---

## R1 - Unifier les Classes IntervalsAPI (P0 - CRITIQUE)

### Problème

**3 implémentations différentes de IntervalsAPI :**

1. **prepare_analysis.py** (lignes 68-187) - 120 lignes
   - VERSION LA PLUS COMPLÈTE
   - Méthodes : get_activities, get_activity, get_wellness, get_events, get_planned_workout, create_event

2. **sync_intervals.py** (lignes 60-122) - 78 lignes
   - Version partielle avec get_athlete, get_wellness, get_activities, get_activity, get_events

3. **check_activity_sources.py** (lignes 21-43) - 23 lignes
   - Version minimale avec seulement get_activities

### Impact

- Maintenance : Bugs doivent être corrigés en 3 endroits
- Incohérence : Comportements légèrement différents
- Confusion : Quelle version utiliser ?
- Exemple récent : get_events() manquait dans sync_intervals.py → bug corrigé le 30/12

### Solution Recommandée

**Créer un module unifié :**

```
cyclisme_training_logs/api/
├── __init__.py
└── intervals_client.py  (nouveau)
```

**Code proposé : intervals_client.py**

```python
"""
Unified Intervals.icu API Client
Client API unifié pour Intervals.icu
"""

import requests
from typing import Optional, List, Dict, Any
from datetime import datetime


class IntervalsClient:
    """
    Client API unifié pour Intervals.icu.

    Usage:
        client = IntervalsClient(athlete_id="iXXXXXX", api_key="...")
        activities = client.get_activities(oldest="2025-12-22", newest="2025-12-28")
        wellness = client.get_wellness(oldest="2025-12-22", newest="2025-12-28")
    """

    BASE_URL = "https://intervals.icu/api/v1"

    def __init__(self, athlete_id: str, api_key: str):
        self.athlete_id = athlete_id
        self.api_key = api_key
        self.session = requests.Session()
        self.session.auth = (f"API_KEY", self.api_key)

    def get_athlete(self) -> Dict[str, Any]:
        """Récupérer le profil athlète."""
        url = f"{self.BASE_URL}/athlete/{self.athlete_id}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_activities(
        self,
        oldest: Optional[str] = None,
        newest: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupérer les activités.

        Args:
            oldest: Date au format YYYY-MM-DD (optionnel)
            newest: Date au format YYYY-MM-DD (optionnel)

        Returns:
            Liste d'activités
        """
        url = f"{self.BASE_URL}/athlete/{self.athlete_id}/activities"
        params = {}
        if oldest:
            params['oldest'] = oldest
        if newest:
            params['newest'] = newest

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_activity(self, activity_id: str) -> Dict[str, Any]:
        """
        Récupérer les détails complets d'une activité.

        Args:
            activity_id: ID de l'activité

        Returns:
            Détails de l'activité avec métriques complètes
        """
        url = f"{self.BASE_URL}/activity/{activity_id}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_wellness(
        self,
        oldest: Optional[str] = None,
        newest: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupérer les données de wellness (CTL, ATL, TSB, sommeil, etc.).

        Args:
            oldest: Date au format YYYY-MM-DD (optionnel)
            newest: Date au format YYYY-MM-DD (optionnel)

        Returns:
            Liste de données wellness par jour
        """
        url = f"{self.BASE_URL}/athlete/{self.athlete_id}/wellness"
        params = {}
        if oldest:
            params['oldest'] = oldest
        if newest:
            params['newest'] = newest

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_events(
        self,
        oldest: Optional[str] = None,
        newest: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupérer les événements du calendrier (workouts planifiés, notes, etc.).

        Args:
            oldest: Date au format YYYY-MM-DD (optionnel)
            newest: Date au format YYYY-MM-DD (optionnel)

        Returns:
            Liste d'événements
        """
        url = f"{self.BASE_URL}/athlete/{self.athlete_id}/events"
        params = {}
        if oldest:
            params['oldest'] = oldest
        if newest:
            params['newest'] = newest

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def create_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Créer un événement (workout planifié) sur Intervals.icu.

        Args:
            event_data: Données de l'événement au format Intervals.icu

        Returns:
            Événement créé avec son ID
        """
        url = f"{self.BASE_URL}/athlete/{self.athlete_id}/events"
        response = self.session.post(url, json=event_data)
        response.raise_for_status()
        return response.json()

    def get_planned_workout(
        self,
        activity_id: str,
        activity_date: str
    ) -> Optional[Dict[str, Any]]:
        """
        Trouver le workout planifié associé à une activité.

        Args:
            activity_id: ID de l'activité réalisée
            activity_date: Date de l'activité (YYYY-MM-DD)

        Returns:
            Workout planifié ou None si non trouvé
        """
        events = self.get_events(oldest=activity_date, newest=activity_date)

        for event in events:
            if event.get('category') == 'WORKOUT':
                workout_id = event.get('workout_doc', {}).get('id')
                return event

        return None
```

### Plan de Migration

**Étape 1 : Créer le module unifié**
- [ ] Créer `cyclisme_training_logs/api/__init__.py`
- [ ] Créer `cyclisme_training_logs/api/intervals_client.py`
- [ ] Copier l'implémentation la plus complète (prepare_analysis.py)
- [ ] Ajouter les méthodes manquantes des autres versions

**Étape 2 : Migrer les imports (16 fichiers)**
```python
# AVANT
from cyclisme_training_logs.sync_intervals import IntervalsAPI
from cyclisme_training_logs.prepare_analysis import IntervalsAPI

# APRÈS
from cyclisme_training_logs.api.intervals_client import IntervalsClient
```

**Fichiers à modifier :**
- weekly_aggregator.py
- weekly_planner.py
- sync_intervals.py (garder comme wrapper legacy)
- prepare_analysis.py (garder comme wrapper legacy)
- workflow_coach.py
- rest_and_cancellations.py
- upload_workouts.py
- backfill_history.py
- insert_analysis.py
- check_activity_sources.py
- planned_sessions_checker.py
- + autres importateurs

**Étape 3 : Tests**
- [ ] Tester get_activities()
- [ ] Tester get_wellness()
- [ ] Tester get_events()
- [ ] Tester create_event()
- [ ] Tester authentification

**Étape 4 : Cleanup**
- [ ] Supprimer IntervalsAPI de sync_intervals.py (ou laisser wrapper)
- [ ] Supprimer IntervalsAPI de prepare_analysis.py (ou laisser wrapper)
- [ ] Supprimer IntervalsAPI de check_activity_sources.py

### Risques

- **Moyen** : Changements d'import dans 16 fichiers
- Mitigation : Garder wrappers legacy temporairement

### Gain Estimé

- **Lignes éliminées :** ~200
- **Maintenance :** Bug fixes en 1 seul endroit
- **Clarté :** API client unique et documenté

---

## R2 - Créer Utilities Métriques (P1)

### Problème

**Pattern CTL/ATL/TSB répété 56 fois dans 9 fichiers :**

```python
# Répété partout :
ctl = wellness.get('ctl', 0)
atl = wellness.get('atl', 0)
tsb = ctl - atl
```

**Fichiers concernés :**
- `analyzers/weekly_aggregator.py` (multiple occurrences)
- `weekly_planner.py` (lignes 107-109)
- `workflow_coach.py`
- `rest_and_cancellations.py` (lignes 180-186, 246-252)
- `sync_intervals.py` (lignes 180-186)
- `prepare_analysis.py` (lignes 346-352, 529-531)
- `weekly_analysis.py` (multiple)
- `planned_sessions_checker.py`
- `analyzers/daily_aggregator.py`

### Solution Recommandée

**Créer module utilities :**

```
cyclisme_training_logs/utils/
├── __init__.py
└── metrics.py  (nouveau)
```

**Code proposé : metrics.py**

```python
"""
Utilities pour extraction et manipulation des métriques.
Utilities for metrics extraction and manipulation.
"""

from typing import Dict, Optional, Any


def extract_fitness_metrics(wellness: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """
    Extraire CTL, ATL, TSB d'un objet wellness avec gestion des None.

    Args:
        wellness: Objet wellness d'Intervals.icu (peut être None)

    Returns:
        Dict avec ctl, atl, tsb (0.0 si données manquantes)

    Examples:
        >>> metrics = extract_fitness_metrics(wellness)
        >>> print(f"CTL: {metrics['ctl']}, TSB: {metrics['tsb']}")
    """
    if not wellness:
        return {'ctl': 0.0, 'atl': 0.0, 'tsb': 0.0}

    ctl = wellness.get('ctl')
    atl = wellness.get('atl')

    # Gestion explicite des None
    ctl = ctl if ctl is not None else 0.0
    atl = atl if atl is not None else 0.0

    return {
        'ctl': float(ctl),
        'atl': float(atl),
        'tsb': float(ctl - atl)
    }


def extract_sleep_metrics(wellness: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """
    Extraire les métriques de sommeil avec gestion des None.

    Args:
        wellness: Objet wellness d'Intervals.icu (peut être None)

    Returns:
        Dict avec sleep_hours, sleep_quality, sleep_seconds

    Examples:
        >>> sleep = extract_sleep_metrics(wellness)
        >>> print(f"Sommeil: {sleep['sleep_hours']}h, qualité: {sleep['sleep_quality']}")
    """
    if not wellness:
        return {
            'sleep_hours': 0.0,
            'sleep_quality': 0.0,
            'sleep_seconds': 0
        }

    sleep_seconds = wellness.get('sleepSecs')
    sleep_quality = wellness.get('sleepQuality')

    sleep_seconds = sleep_seconds if sleep_seconds is not None else 0
    sleep_quality = sleep_quality if sleep_quality is not None else 0.0

    return {
        'sleep_seconds': int(sleep_seconds),
        'sleep_hours': float(sleep_seconds / 3600) if sleep_seconds > 0 else 0.0,
        'sleep_quality': float(sleep_quality)
    }


def extract_weight_hrv(wellness: Optional[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    """
    Extraire poids et HRV avec gestion des None.

    Args:
        wellness: Objet wellness d'Intervals.icu

    Returns:
        Dict avec weight (kg) et hrv (ms)
    """
    if not wellness:
        return {'weight': None, 'hrv': None}

    return {
        'weight': wellness.get('weight'),
        'hrv': wellness.get('hrv')
    }


def calculate_ramp_rate(ctl: float, atl: float) -> float:
    """
    Calculer le ramp rate (taux de rampe).

    Args:
        ctl: Chronic Training Load
        atl: Acute Training Load

    Returns:
        Ramp rate (ATL/CTL ratio)

    Notes:
        - < 0.8 : Désentraînement
        - 0.8-1.5 : Zone optimale
        - > 1.5 : Surcharge excessive
    """
    if ctl == 0 or ctl is None:
        return 0.0

    return float(atl / ctl)


def format_metrics_summary(metrics: Dict[str, float]) -> str:
    """
    Formater un résumé des métriques pour affichage.

    Args:
        metrics: Dict avec ctl, atl, tsb

    Returns:
        String formaté pour affichage

    Examples:
        >>> summary = format_metrics_summary({'ctl': 45.6, 'atl': 37.7, 'tsb': 7.9})
        >>> print(summary)
        CTL: 45.6 | ATL: 37.7 | TSB: +7.9
    """
    tsb = metrics.get('tsb', 0)
    tsb_sign = '+' if tsb >= 0 else ''

    return f"CTL: {metrics.get('ctl', 0):.1f} | ATL: {metrics.get('atl', 0):.1f} | TSB: {tsb_sign}{tsb:.1f}"
```

### Plan de Migration

**Étape 1 : Créer le module**
- [ ] Créer `cyclisme_training_logs/utils/__init__.py`
- [ ] Créer `cyclisme_training_logs/utils/metrics.py`

**Étape 2 : Remplacer dans weekly_aggregator.py**
```python
# AVANT (lignes 395-407)
ctl = wellness.get('ctl')
atl = wellness.get('atl')
tsb = wellness.get('tsb')
metrics.append({
    'ctl': ctl if ctl is not None else 0,
    'atl': atl if atl is not None else 0,
    'tsb': tsb if tsb is not None else 0
})

# APRÈS
from cyclisme_training_logs.utils.metrics import extract_fitness_metrics
metrics.append(extract_fitness_metrics(wellness))
```

**Étape 3 : Migrer les 8 autres fichiers**

**Étape 4 : Tests**
- [ ] Test extract_fitness_metrics avec wellness=None
- [ ] Test extract_fitness_metrics avec ctl=None
- [ ] Test extract_sleep_metrics
- [ ] Test calculate_ramp_rate avec ctl=0

### Gain Estimé

- **Lignes éliminées :** ~100
- **Bugs évités :** Gestion None centralisée
- **Tests :** Logique métrique testable unitairement

---

## R3 - Créer Planning Manager (P1)

### Problème

**5 fichiers accèdent au JSON planning différemment :**

1. **weekly_planner.py** (lignes 633-726)
   - Méthodes : save_planning_json(), update_session_status()

2. **workflow_coach.py** (lignes 494-500+)
   - Méthode : _update_planning_json()

3. **rest_and_cancellations.py** (lignes 80-124)
   - Méthode : validate_week_planning()

4. **planned_sessions_checker.py**
   - Load planning pour vérification

5. **test_rest_and_cancellations.py**
   - Mocks de planning

**Incohérences :**
- Différentes façons de construire le path
- Gestion d'erreurs différente
- Validation différente
- Pas de gestion atomique des écritures

### Solution Recommandée

**Créer module planning :**

```
cyclisme_training_logs/planning/
├── __init__.py
└── manager.py  (nouveau)
```

**Code proposé : manager.py**

```python
"""
Gestionnaire centralisé pour les fichiers JSON de planning.
Centralized manager for planning JSON files.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from cyclisme_training_logs.config import get_data_config

logger = logging.getLogger(__name__)


class WeekPlanningManager:
    """
    Gestionnaire pour les opérations sur les fichiers week_planning_SXXX.json.

    Fournit des opérations atomiques, validation, et gestion d'erreurs centralisée.
    """

    def __init__(self, planning_dir: Optional[Path] = None):
        """
        Initialiser le manager.

        Args:
            planning_dir: Répertoire des plannings (optionnel, utilise config si None)
        """
        if planning_dir is None:
            config = get_data_config()
            self.planning_dir = config.week_planning_dir
        else:
            self.planning_dir = Path(planning_dir)

        # Créer le répertoire si nécessaire
        self.planning_dir.mkdir(parents=True, exist_ok=True)

    def get_planning_path(self, week_id: str) -> Path:
        """Obtenir le path du fichier JSON pour une semaine."""
        return self.planning_dir / f"week_planning_{week_id}.json"

    def exists(self, week_id: str) -> bool:
        """Vérifier si un planning existe."""
        return self.get_planning_path(week_id).exists()

    def load(self, week_id: str) -> Dict[str, Any]:
        """
        Charger un planning avec validation.

        Args:
            week_id: ID de la semaine (ex: S074)

        Returns:
            Planning chargé et validé

        Raises:
            FileNotFoundError: Planning introuvable
            ValueError: Planning invalide
        """
        path = self.get_planning_path(week_id)

        if not path.exists():
            raise FileNotFoundError(f"Planning {week_id} introuvable: {path}")

        try:
            with open(path, 'r', encoding='utf-8') as f:
                planning = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Planning {week_id} invalide (JSON): {e}")

        # Validation basique
        self._validate_planning(planning, week_id)

        return planning

    def save(
        self,
        week_id: str,
        planning: Dict[str, Any],
        update_timestamp: bool = True
    ) -> None:
        """
        Sauvegarder un planning de manière atomique.

        Args:
            week_id: ID de la semaine
            planning: Données du planning
            update_timestamp: Mettre à jour last_updated (défaut: True)
        """
        if update_timestamp:
            planning['last_updated'] = datetime.now().isoformat()

        # Validation avant sauvegarde
        self._validate_planning(planning, week_id)

        path = self.get_planning_path(week_id)

        # Écriture atomique (via fichier temporaire)
        temp_path = path.with_suffix('.json.tmp')
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(planning, f, indent=2, ensure_ascii=False)

            # Renommer atomiquement
            temp_path.replace(path)
            logger.info(f"Planning {week_id} sauvegardé: {path}")

        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise IOError(f"Erreur sauvegarde planning {week_id}: {e}")

    def update_session_status(
        self,
        week_id: str,
        session_id: str,
        status: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        Mettre à jour le statut d'une séance.

        Args:
            week_id: ID de la semaine (ex: S074)
            session_id: ID de la séance (ex: S074-01)
            status: Nouveau statut (completed, cancelled, skipped, etc.)
            reason: Raison de l'annulation/modification (optionnel)

        Returns:
            True si mise à jour réussie, False sinon
        """
        try:
            planning = self.load(week_id)
        except FileNotFoundError:
            logger.error(f"Planning {week_id} introuvable")
            return False

        # Trouver la séance
        session_found = False
        for session in planning.get('planned_sessions', []):
            if session.get('session_id') == session_id:
                session['status'] = status

                # Ajouter reason selon le statut
                if reason:
                    if status == 'cancelled':
                        session['cancellation_reason'] = reason
                        session['cancellation_date'] = datetime.now().isoformat()
                    elif status == 'rest_day':
                        session['rest_reason'] = reason
                    elif status == 'modified':
                        session['modification_reason'] = reason
                    elif status == 'replaced':
                        session['replacement_reason'] = reason

                session_found = True
                logger.info(f"Séance {session_id} mise à jour: {status}")
                break

        if not session_found:
            logger.error(f"Séance {session_id} introuvable dans {week_id}")
            return False

        # Sauvegarder
        self.save(week_id, planning, update_timestamp=True)
        return True

    def get_session(self, week_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupérer une séance spécifique.

        Args:
            week_id: ID de la semaine
            session_id: ID de la séance

        Returns:
            Données de la séance ou None si introuvable
        """
        try:
            planning = self.load(week_id)
        except FileNotFoundError:
            return None

        for session in planning.get('planned_sessions', []):
            if session.get('session_id') == session_id:
                return session

        return None

    def get_sessions_by_status(
        self,
        week_id: str,
        status: str
    ) -> List[Dict[str, Any]]:
        """
        Récupérer toutes les séances avec un statut donné.

        Args:
            week_id: ID de la semaine
            status: Statut recherché (planned, completed, cancelled, etc.)

        Returns:
            Liste des séances correspondantes
        """
        try:
            planning = self.load(week_id)
        except FileNotFoundError:
            return []

        return [
            session for session in planning.get('planned_sessions', [])
            if session.get('status') == status
        ]

    def _validate_planning(self, planning: Dict[str, Any], week_id: str) -> None:
        """
        Valider la structure d'un planning.

        Raises:
            ValueError: Si validation échoue
        """
        required_fields = ['week_id', 'start_date', 'end_date', 'planned_sessions']

        for field in required_fields:
            if field not in planning:
                raise ValueError(f"Champ requis manquant: {field}")

        if planning['week_id'] != week_id:
            raise ValueError(
                f"Incohérence week_id: attendu {week_id}, "
                f"trouvé {planning['week_id']}"
            )

        if not isinstance(planning['planned_sessions'], list):
            raise ValueError("planned_sessions doit être une liste")
```

### Plan de Migration

**Étape 1 : Créer le module**
- [ ] Créer `cyclisme_training_logs/planning/__init__.py`
- [ ] Créer `cyclisme_training_logs/planning/manager.py`

**Étape 2 : Migrer weekly_planner.py**
```python
# AVANT
def save_planning_json(self, workouts_data: list = None):
    json_file = self.planning_dir / f"week_planning_{self.week_number}.json"
    # ... 40 lignes de code

# APRÈS
from cyclisme_training_logs.planning.manager import WeekPlanningManager

def save_planning_json(self, workouts_data: list = None):
    manager = WeekPlanningManager(self.planning_dir)
    manager.save(self.week_number, self._build_planning_dict(workouts_data))
```

**Étape 3 : Migrer les 4 autres fichiers**

**Étape 4 : Tests**
- [ ] Test save + load
- [ ] Test écriture atomique
- [ ] Test validation
- [ ] Test update_session_status

### Gain Estimé

- **Lignes éliminées :** ~150
- **Robustesse :** Écriture atomique, validation centralisée
- **Tests :** Logique planning testable unitairement

---

## R4 - Créer Date Utilities (P1)

### Problème

**Calculs de dates répétés dans 11 fichiers :**

```python
# Pattern 1 : Week ID parsing
week_int = int(week_number[1:])  # S073 -> 73
next_week = f"S{week_int + 1:03d}"  # S074

# Pattern 2 : Date parsing
start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
end_date = start_date + timedelta(days=6)

# Pattern 3 : Week calculation from reference
reference_date = datetime(2024, 1, 1)
weeks_offset = week_int - 1
start_date = reference_date + timedelta(weeks=weeks_offset)
```

**Fichiers concernés :**
- weekly_planner.py (ligne 809)
- weekly_analysis.py (lignes 119-125)
- upload_workouts.py
- rest_and_cancellations.py
- workflow_coach.py
- prepare_analysis.py
- backfill_history.py
- + 4 autres

### Solution Recommandée

**Ajouter au module utilities :**

```
cyclisme_training_logs/utils/
├── __init__.py
├── metrics.py
└── dates.py  (nouveau)
```

**Code proposé : dates.py**

```python
"""
Utilities pour manipulation des dates et semaines.
Utilities for date and week manipulation.
"""

from datetime import datetime, timedelta
from typing import Tuple, Optional


# Date de référence pour calculs de semaines
REFERENCE_DATE = datetime(2024, 1, 1)  # Semaine S001 commence le 1er janvier 2024


def parse_week_id(week_id: str) -> int:
    """
    Parser un ID de semaine.

    Args:
        week_id: ID au format SXXX (ex: S073, S074)

    Returns:
        Numéro de semaine (int)

    Raises:
        ValueError: Si format invalide

    Examples:
        >>> parse_week_id("S073")
        73
        >>> parse_week_id("S001")
        1
    """
    if not week_id.startswith('S') or len(week_id) != 4:
        raise ValueError(f"Format week_id invalide: {week_id} (attendu: SXXX)")

    try:
        return int(week_id[1:])
    except ValueError:
        raise ValueError(f"Week_id non numérique: {week_id}")


def format_week_id(week_number: int) -> str:
    """
    Formater un numéro de semaine en ID.

    Args:
        week_number: Numéro de semaine (int)

    Returns:
        Week ID au format SXXX

    Examples:
        >>> format_week_id(73)
        'S073'
        >>> format_week_id(1)
        'S001'
    """
    if week_number < 1 or week_number > 999:
        raise ValueError(f"Numéro de semaine invalide: {week_number}")

    return f"S{week_number:03d}"


def next_week_id(week_id: str) -> str:
    """
    Calculer le week_id suivant.

    Args:
        week_id: ID de semaine actuelle (ex: S073)

    Returns:
        Week ID suivant (ex: S074)

    Examples:
        >>> next_week_id("S073")
        'S074'
        >>> next_week_id("S099")
        'S100'
    """
    week_num = parse_week_id(week_id)
    return format_week_id(week_num + 1)


def previous_week_id(week_id: str) -> str:
    """Calculer le week_id précédent."""
    week_num = parse_week_id(week_id)
    if week_num <= 1:
        raise ValueError("Pas de semaine précédente pour S001")
    return format_week_id(week_num - 1)


def week_to_dates(
    week_id: str,
    reference_date: Optional[datetime] = None
) -> Tuple[datetime, datetime]:
    """
    Convertir un week_id en dates (start_date, end_date).

    Args:
        week_id: ID de semaine (ex: S073)
        reference_date: Date de référence (défaut: 2024-01-01)

    Returns:
        Tuple (start_date, end_date) pour la semaine

    Examples:
        >>> start, end = week_to_dates("S001")
        >>> print(start.strftime('%Y-%m-%d'))
        2024-01-01
        >>> print(end.strftime('%Y-%m-%d'))
        2024-01-07
    """
    if reference_date is None:
        reference_date = REFERENCE_DATE

    week_num = parse_week_id(week_id)
    weeks_offset = week_num - 1

    start_date = reference_date + timedelta(weeks=weeks_offset)
    end_date = start_date + timedelta(days=6)

    return start_date, end_date


def dates_to_week_id(
    date: datetime,
    reference_date: Optional[datetime] = None
) -> str:
    """
    Trouver le week_id correspondant à une date.

    Args:
        date: Date à convertir
        reference_date: Date de référence (défaut: 2024-01-01)

    Returns:
        Week ID (ex: S073)

    Examples:
        >>> dates_to_week_id(datetime(2024, 12, 25))
        'S052'
    """
    if reference_date is None:
        reference_date = REFERENCE_DATE

    delta = date - reference_date
    week_num = (delta.days // 7) + 1

    return format_week_id(week_num)


def parse_iso_date(date_str: str) -> datetime:
    """
    Parser une date ISO (YYYY-MM-DD).

    Args:
        date_str: Date au format YYYY-MM-DD

    Returns:
        Objet datetime

    Raises:
        ValueError: Si format invalide

    Examples:
        >>> date = parse_iso_date("2025-12-30")
        >>> print(date.year)
        2025
    """
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError as e:
        raise ValueError(f"Format date invalide (attendu YYYY-MM-DD): {date_str}")


def parse_french_date(date_str: str) -> datetime:
    """
    Parser une date française (DD/MM/YYYY).

    Args:
        date_str: Date au format DD/MM/YYYY

    Returns:
        Objet datetime

    Raises:
        ValueError: Si format invalide
    """
    try:
        return datetime.strptime(date_str, '%d/%m/%Y')
    except ValueError as e:
        raise ValueError(f"Format date invalide (attendu DD/MM/YYYY): {date_str}")


def format_iso_date(date: datetime) -> str:
    """
    Formater une date en ISO (YYYY-MM-DD).

    Args:
        date: Objet datetime

    Returns:
        String au format YYYY-MM-DD
    """
    return date.strftime('%Y-%m-%d')
```

### Plan de Migration

**Étape 1 : Créer le module**
- [ ] Créer `cyclisme_training_logs/utils/dates.py`

**Étape 2 : Remplacer dans weekly_planner.py**
```python
# AVANT (ligne 809)
week_int = int(self.week_number[1:])
next_week = f"S{week_int + 1:03d}"

# APRÈS
from cyclisme_training_logs.utils.dates import next_week_id
next_week = next_week_id(self.week_number)
```

**Étape 3 : Migrer les 10 autres fichiers**

**Étape 4 : Tests unitaires**
- [ ] Test parse_week_id avec formats invalides
- [ ] Test week_to_dates pour S001 et S073
- [ ] Test next_week_id et previous_week_id
- [ ] Test parse_iso_date et parse_french_date

### Gain Estimé

- **Lignes éliminées :** ~80
- **Robustesse :** Validation centralisée
- **Tests :** Logique dates testable unitairement

---

## R5 - Créer Data Fetching Facade (P2)

### Problème

**Pattern wellness fetching répété 9 fois :**

```python
# Répété partout :
wellness = api.get_wellness(oldest=date_str, newest=date_str)
wellness = wellness[0] if wellness else None

if wellness:
    ctl = wellness.get('ctl', 0)
    atl = wellness.get('atl', 0)
```

**Fichiers concernés :**
- prepare_analysis.py
- sync_intervals.py
- weekly_planner.py
- weekly_analysis.py
- workflow_coach.py
- rest_and_cancellations.py
- etc.

### Solution Recommandée

**Créer module data :**

```
cyclisme_training_logs/data/
├── __init__.py
└── fetcher.py  (nouveau)
```

**Code proposé : fetcher.py**

```python
"""
Facade pour récupération de données depuis Intervals.icu.
Facade for fetching data from Intervals.icu.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime

from cyclisme_training_logs.api.intervals_client import IntervalsClient
from cyclisme_training_logs.utils.metrics import extract_fitness_metrics, extract_sleep_metrics
from cyclisme_training_logs.utils.dates import format_iso_date


class IntervalsFetcher:
    """
    Facade haut niveau pour récupération de données Intervals.icu.

    Fournit des méthodes avec cache, extraction automatique de métriques,
    et gestion d'erreurs.
    """

    def __init__(self, client: IntervalsClient):
        """
        Args:
            client: Client API Intervals.icu initialisé
        """
        self.client = client
        self._cache = {}

    def fetch_wellness_for_date(
        self,
        date: datetime
    ) -> Dict[str, Any]:
        """
        Récupérer wellness pour une date avec extraction de métriques.

        Args:
            date: Date à récupérer

        Returns:
            Dict avec wellness + fitness_metrics + sleep_metrics extraits

        Examples:
            >>> data = fetcher.fetch_wellness_for_date(datetime(2025, 12, 30))
            >>> print(data['fitness_metrics']['ctl'])
            45.6
        """
        date_str = format_iso_date(date)

        # Check cache
        cache_key = f"wellness_{date_str}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Fetch from API
        wellness_list = self.client.get_wellness(oldest=date_str, newest=date_str)
        wellness = wellness_list[0] if wellness_list else None

        # Extract metrics
        result = {
            'raw': wellness,
            'fitness_metrics': extract_fitness_metrics(wellness),
            'sleep_metrics': extract_sleep_metrics(wellness),
            'date': date_str
        }

        # Cache
        self._cache[cache_key] = result

        return result

    def fetch_week_data(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Récupérer toutes les données pour une semaine.

        Args:
            start_date: Début de semaine
            end_date: Fin de semaine

        Returns:
            Dict avec activities, wellness, events pour la semaine
        """
        start_str = format_iso_date(start_date)
        end_str = format_iso_date(end_date)

        activities = self.client.get_activities(oldest=start_str, newest=end_str)
        wellness = self.client.get_wellness(oldest=start_str, newest=end_str)
        events = self.client.get_events(oldest=start_str, newest=end_str)

        return {
            'activities': activities,
            'wellness': wellness,
            'events': events,
            'start_date': start_str,
            'end_date': end_str
        }

    def fetch_activity_details(self, activity_id: str) -> Dict[str, Any]:
        """
        Récupérer détails enrichis d'une activité.

        Args:
            activity_id: ID de l'activité

        Returns:
            Activité avec métriques extraites (TSS, IF, NP, etc.)
        """
        activity = self.client.get_activity(activity_id)

        return {
            'raw': activity,
            'id': activity_id,
            'tss': activity.get('icu_training_load', 0),
            'if': activity.get('icu_intensity', 0) / 100.0 if activity.get('icu_intensity') else 0,
            'np': activity.get('icu_np', 0),
            'duration_seconds': activity.get('moving_time', 0),
            'date': activity.get('start_date_local', '')[:10]
        }

    def clear_cache(self):
        """Vider le cache."""
        self._cache.clear()
```

### Plan de Migration

**Étape 1 : Créer le module**
- [ ] Créer `cyclisme_training_logs/data/__init__.py`
- [ ] Créer `cyclisme_training_logs/data/fetcher.py`

**Étape 2 : Migrer prepare_analysis.py**
```python
# AVANT
wellness_list = api.get_wellness(oldest=date_str, newest=date_str)
wellness = wellness_list[0] if wellness_list else None
ctl = wellness.get('ctl', 0) if wellness else 0

# APRÈS
from cyclisme_training_logs.data.fetcher import IntervalsFetcher
fetcher = IntervalsFetcher(api)
data = fetcher.fetch_wellness_for_date(date)
ctl = data['fitness_metrics']['ctl']
```

**Étape 3 : Migrer les 8 autres fichiers**

### Gain Estimé

- **Lignes éliminées :** ~60
- **Cache :** Optimisation requêtes API
- **Clarté :** Séparation client API / logique métier

---

## 📋 Plan d'Implémentation Global

### Phase 1 : Fondations (P0 + Utilities de base)
**Durée estimée :** 1-2 sessions

- [ ] R1 : Créer `api/intervals_client.py` (unified IntervalsAPI)
- [ ] R4 : Créer `utils/dates.py`
- [ ] R2 : Créer `utils/metrics.py`
- [ ] Tests unitaires pour ces 3 modules
- [ ] Commit : "refactor: Create unified API client and utilities"

### Phase 2 : Planning Manager (P1)
**Durée estimée :** 1 session

- [ ] R3 : Créer `planning/manager.py`
- [ ] Migrer weekly_planner.py
- [ ] Migrer workflow_coach.py
- [ ] Tests unitaires planning manager
- [ ] Commit : "refactor: Create centralized planning manager"

### Phase 3 : Migration Massive (P1 + P2)
**Durée estimée :** 2-3 sessions

- [ ] Migrer 16 fichiers vers IntervalsClient
- [ ] Migrer 9 fichiers vers metrics utilities
- [ ] Migrer 11 fichiers vers dates utilities
- [ ] R5 : Créer data/fetcher.py
- [ ] Tests d'intégration end-to-end
- [ ] Commit : "refactor: Migrate all files to unified utilities"

### Phase 4 : Cleanup (Final)
**Durée estimée :** 1 session

- [ ] Supprimer anciens IntervalsAPI (ou créer wrappers deprecation)
- [ ] Supprimer code dupliqué
- [ ] Mettre à jour documentation
- [ ] Commit : "refactor: Remove duplicated code and finalize cleanup"

---

## 🧪 Stratégie de Tests

### Tests Unitaires à Créer

**api/intervals_client.py :**
```python
def test_intervals_client_get_activities()
def test_intervals_client_get_wellness()
def test_intervals_client_authentication()
def test_intervals_client_error_handling()
```

**utils/metrics.py :**
```python
def test_extract_fitness_metrics_with_none()
def test_extract_fitness_metrics_valid()
def test_extract_sleep_metrics()
def test_calculate_ramp_rate_zero_ctl()
```

**utils/dates.py :**
```python
def test_parse_week_id_valid()
def test_parse_week_id_invalid()
def test_week_to_dates()
def test_next_week_id()
def test_parse_iso_date_invalid()
```

**planning/manager.py :**
```python
def test_planning_manager_save_load()
def test_planning_manager_atomic_write()
def test_planning_manager_validation()
def test_planning_manager_update_session()
```

### Tests d'Intégration

- [ ] Test workflow complet wa + wp + wu
- [ ] Test réconciliation avec nouveau planning manager
- [ ] Test servo-mode avec nouvelles utilities

---

## ⚠️ Risques et Mitigations

### Risques Identifiés

1. **Régression fonctionnelle**
   - Risque : Changements cassent fonctionnalités existantes
   - Mitigation : Tests exhaustifs, migration progressive

2. **Imports circulaires**
   - Risque : Nouveau modules créent dépendances circulaires
   - Mitigation : Architecture en couches (api → utils → data → planning)

3. **Performance**
   - Risque : Nouveaux layers ajoutent latence
   - Mitigation : Profiling avant/après, cache dans fetcher

4. **Adoption**
   - Risque : Code legacy continue d'utiliser anciennes méthodes
   - Mitigation : Deprecation warnings, migration forcée

### Plan de Rollback

Si problème majeur après refactoring :
1. Git revert des commits de refactoring
2. Retour à la version stable (current MOA 20251230)
3. Analyse post-mortem
4. Re-planification avec leçons apprises

---

## 📚 Références

### Standards de Code

- **PEP 8** : Style guide Python
- **Google Style Docstrings** : Déjà adopté dans le projet
- **Type Hints** : Utiliser typing pour nouvelles utilities

### Architecture

- **Layered Architecture** : api → utils → data → business logic
- **DRY Principle** : Don't Repeat Yourself
- **Single Responsibility** : Un module = une responsabilité

---

## ✅ Checklist Avant Refactoring

Avant de démarrer le refactoring, vérifier :

- [ ] Tous les tests actuels passent
- [ ] Git status clean (pas de WIP)
- [ ] Backup/tag de la version stable actuelle
- [ ] Review de ce document par MOA
- [ ] Planning des sessions de refactoring
- [ ] Décision sur migration big-bang vs progressive

---

## 📝 Notes de Session

### 30 Décembre 2025

**Analyse effectuée par :** Claude Code
**Méthodologie :**
- Glob pour trouver tous les fichiers Python
- Grep pour identifier patterns de duplication
- Read pour analyser implémentations détaillées
- Comparaison manuelle des 3 IntervalsAPI

**Constats principaux :**
1. Duplication ~590 lignes (significatif pour codebase <10k lignes)
2. IntervalsAPI en 3 versions = bug source (exemple: get_events manquant)
3. None handling patterns répétés = risque bugs futurs
4. JSON operations pas atomiques = risque corruption

**Recommandation MOA :** Documentation pour référence future (ce document)

---

**Document créé le :** 30 décembre 2025
**Dernière mise à jour :** 30 décembre 2025
**Statut :** Documentation de référence (non implémenté)
**Prochaine revue suggérée :** Avant planning S076 ou si nouveaux bugs de duplication
