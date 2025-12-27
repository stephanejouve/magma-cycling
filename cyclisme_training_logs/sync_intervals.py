#!/usr/bin/env python3
"""
Intervals.icu API integration for activity sync and metrics fetching.
Intègre l'API Intervals.icu pour synchronisation activités, fetch métriques
forme (CTL/ATL/TSB), et wellness data. Utilisé quotidiennement par le
workflow principal.

Examples:
    Sync recent activities::

        from cyclisme_training_logs.sync_intervals import IntervalsAPI

        # Initialiser API
        api = IntervalsAPI()

        # Sync dernières 7 jours
        activities = api.sync_recent_activities(days=7)

        for activity in activities:
            print(f"{activity['start_date']}: {activity['name']}")

    Fetch fitness metrics::

        # Récupérer métriques forme aujourd'hui
        wellness = api.get_wellness_today()

        print(f"CTL: {wellness['ctl']}")
        print(f"ATL: {wellness['atl']}")
        print(f"TSB: {wellness['tsb']}")

    Get specific activity::

        # Fetch activité par ID
        activity = api.get_activity('i123456')

        print(f"TSS: {activity['training_load']}")
        print(f"IF: {activity['if']:.2f}")
        print(f"NP: {activity['normalized_power']}W")

Author: Stéphane Jouve
Created: 2024-09-XX
Updated: 2025-12-26 (Standardization Prompt 3 Priority 2)

Metadata:
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: I
    Status: Production
    Priority: P1
    Version: v2
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
import requests

class IntervalsAPI:
    """Client pour l'API Intervals.icu"""
    
    BASE_URL = "https://intervals.icu/api/v1"
    
    def __init__(self, athlete_id, api_key):
        self.athlete_id = athlete_id
        self.session = requests.Session()
        self.session.auth = (f"API_KEY", api_key)
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_athlete(self):
        """Récupérer les infos de l'athlète"""
        response = self.session.get(f"{self.BASE_URL}/athlete/{self.athlete_id}")
        response.raise_for_status()
        return response.json()
    
    def get_wellness(self, oldest=None, newest=None):
        """Récupérer les données wellness (CTL/ATL/TSB, poids, sommeil)"""
        url = f"{self.BASE_URL}/athlete/{self.athlete_id}/wellness"
        params = {}
        if oldest:
            params['oldest'] = oldest
        if newest:
            params['newest'] = newest
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_activities(self, oldest=None, newest=None):
        """Récupérer les activités (séances)"""
        url = f"{self.BASE_URL}/athlete/{self.athlete_id}/activities"
        params = {}
        if oldest:
            params['oldest'] = oldest
        if newest:
            params['newest'] = newest
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_activity(self, activity_id):
        """Récupérer les détails d'une activité spécifique"""
        url = f"{self.BASE_URL}/activity/{activity_id}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()


class WorkoutLogger:
    """Gestionnaire de mise à jour des logs"""

    def __init__(self, logs_dir=None):
        """
        Initialize WorkoutLogger.

        Args:
            logs_dir: Legacy parameter, use data repo config instead
        """
        from cyclisme_training_logs.config import get_data_config

        # Use data repo config if available
        if logs_dir is None:
            try:
                config = get_data_config()
                self.logs_dir = config.data_repo_path
                self.workouts_file = config.workouts_history_path
                self.metrics_file = config.data_repo_path / "metrics-evolution.md"
            except FileNotFoundError:
                # Fallback to default logs directory (legacy)
                self.logs_dir = Path.cwd() / 'logs'
                self.workouts_file = self.logs_dir / "workouts-history.md"
                self.metrics_file = self.logs_dir / "metrics-evolution.md"
        else:
            # Legacy: explicit logs_dir provided
            self.logs_dir = Path(logs_dir)
            self.workouts_file = self.logs_dir / "workouts-history.md"
            self.metrics_file = self.logs_dir / "metrics-evolution.md"
    
    def format_workout_entry(self, activity, wellness_pre, wellness_post):
        """Formater une entrée de séance pour workouts-history.md"""
        
        # Extraire les données
        date = datetime.fromisoformat(activity['start_date_local'].replace('Z', '+00:00'))
        date_str = date.strftime('%d/%m/%Y')
        
        # Type de séance depuis le nom ou type
        workout_type = activity.get('type', 'Cyclisme')
        name = activity.get('name', 'Séance')
        
        # Métriques
        duration_min = activity.get('moving_time', 0) // 60
        tss = activity.get('icu_training_load', 0)
        intensity = activity.get('icu_intensity', 0) / 100.0  # Convertir % en ratio (0-1)
        avg_power = activity.get('icu_average_watts', 0)  # Corrigé: icu_average_watts
        np = activity.get('icu_weighted_avg_watts', 0)  # Corrigé: icu_weighted_avg_watts (= NP)
        avg_cadence = activity.get('average_cadence', 0)
        avg_hr = activity.get('average_heartrate', 0)
        max_hr = activity.get('max_heartrate', 0)
        
        # Découplage (si disponible)
        decoupling = activity.get('decoupling', None)
        decoupling_str = f"{decoupling:.1f}%" if decoupling else "N/A"
        
        # CTL/ATL/TSB
        ctl_pre = wellness_pre.get('ctl', 0) if wellness_pre else 0
        atl_pre = wellness_pre.get('atl', 0) if wellness_pre else 0
        tsb_pre = ctl_pre - atl_pre  # Calculé: TSB = CTL - ATL
        
        ctl_post = wellness_post.get('ctl', 0) if wellness_post else 0
        atl_post = wellness_post.get('atl', 0) if wellness_post else 0
        tsb_post = ctl_post - atl_post  # Calculé: TSB = CTL - ATL
        
        # Template markdown
        entry = f"""
### {name}
Date : {date_str}

#### Métriques Pré-séance
- CTL : {ctl_pre:.0f}
- ATL : {atl_pre:.0f}
- TSB : {tsb_pre:+.0f}

#### Description
{workout_type} - Données synchronisées depuis Intervals.icu

#### Exécution
- Durée réalisée : {duration_min}min
- IF : {intensity:.2f}
- TSS : {tss:.0f}
- Puissance moyenne : {avg_power:.0f}W
- Puissance normalisée : {np:.0f}W
- Cadence moyenne : {avg_cadence:.0f}rpm
- FC moyenne : {avg_hr:.0f}bpm
- RPE : _[À remplir manuellement]_
- Découplage cardiovasculaire : {decoupling_str}

#### Métriques Post-séance
- CTL : {ctl_post:.0f}
- ATL : {atl_post:.0f}
- TSB : {tsb_post:+.0f}

#### Retour Athlète
_[À remplir : Ressenti général, points positifs, difficultés rencontrées]_

#### Notes Coach
_[À remplir : Observations techniques, validations, points d'attention]_

---
"""
        return entry
    
    def update_workouts_history(self, activities, wellness_data):
        """Mettre à jour workouts-history.md"""
        
        print(f"📝 Mise à jour de {self.workouts_file.name}...")
        
        # Lire le fichier existant
        if self.workouts_file.exists():
            with open(self.workouts_file, 'r', encoding='utf-8') as f:
                existing_content = f.read()
        else:
            existing_content = "# Historique des Entraînements\n\n"
        
        # Créer un index des wellness par date
        wellness_by_date = {w['id']: w for w in wellness_data}
        
        # Générer les nouvelles entrées
        new_entries = []
        for activity in activities:
            date = activity['start_date_local'][:10]  # YYYY-MM-DD
            
            # Wellness pré (jour même)
            wellness_pre = wellness_by_date.get(date)
            
            # Wellness post (jour suivant approximatif)
            # Note: En réalité, il faudrait calculer le CTL/ATL/TSB post-séance
            # Pour l'instant, on utilise les données du jour
            wellness_post = wellness_pre
            
            entry = self.format_workout_entry(activity, wellness_pre, wellness_post)
            new_entries.append(entry)
        
        # Insérer les nouvelles entrées
        # TODO: Détecter les doublons et ne pas re-ajouter
        insert_position = existing_content.find("## Historique")
        if insert_position == -1:
            insert_position = len(existing_content)
        
        updated_content = (
            existing_content[:insert_position] +
            "\n## Historique\n\n" +
            "\n".join(new_entries) +
            existing_content[insert_position:]
        )
        
        # Écrire le fichier mis à jour
        with open(self.workouts_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print(f"✅ {len(new_entries)} séance(s) ajoutée(s)")
    
    def update_metrics_evolution(self, athlete_data, wellness_data):
        """Mettre à jour metrics-evolution.md"""
        
        print(f"📊 Mise à jour de {self.metrics_file.name}...")
        
        # FTP actuel
        current_ftp = athlete_data.get('ftp', 220) or 220
        weight = athlete_data.get('weight', 83.8) or 83.8
        w_kg = current_ftp / weight if weight and weight > 0 else 0
        
        # CTL/ATL/TSB actuels (dernier jour)
        latest_wellness = wellness_data[0] if wellness_data else {}
        ctl = latest_wellness.get('ctl', 0)
        atl = latest_wellness.get('atl', 0)
        tsb = ctl - atl  # Calculé: TSB = CTL - ATL
        
        # TODO: Mettre à jour les tableaux existants plutôt que tout écraser
        # Pour l'instant, juste afficher un résumé
        
        summary = f"""
# Métriques Actuelles (Synchronisées)

**Dernière synchronisation** : {datetime.now().strftime('%d/%m/%Y %H:%M')}

## État Actuel

| Métrique | Valeur | Notes |
|----------|--------|-------|
| FTP | {current_ftp:.0f}W | {w_kg:.2f} W/kg |
| Poids | {weight:.1f}kg | - |
| CTL (Fitness) | {ctl:.0f} | - |
| ATL (Fatigue) | {atl:.0f} | - |
| TSB (Form) | {tsb:+.0f} | - |

---

_Le reste du fichier metrics-evolution.md reste inchangé._
_Pour une mise à jour complète des tableaux, voir le fichier original._
"""
        
        # Pour l'instant, on crée un fichier séparé
        summary_file = self.logs_dir / "metrics_sync_summary.md"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        print(f"✅ Résumé créé dans {summary_file.name}")
        print(f"   FTP: {current_ftp:.0f}W ({w_kg:.2f} W/kg)")
        print(f"   CTL/ATL/TSB: {ctl:.0f}/{atl:.0f}/{tsb:+.0f}")


def load_config(config_file):
    """Charger la configuration depuis un fichier JSON"""
    config_path = Path(config_file).expanduser()
    if not config_path.exists():
        return None
    
    with open(config_path, 'r') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Synchroniser les logs d'entraînement avec Intervals.icu"
    )
    
    parser.add_argument(
        '--athlete-id',
        help="ID de l'athlète Intervals.icu (ex: i123456)"
    )
    parser.add_argument(
        '--api-key',
        help="Clé API Intervals.icu"
    )
    parser.add_argument(
        '--config',
        default='~/.intervals_config.json',
        help="Fichier de configuration JSON (défaut: ~/.intervals_config.json)"
    )
    parser.add_argument(
        '--last-days',
        type=int,
        default=7,
        help="Nombre de jours à synchroniser (défaut: 7)"
    )
    parser.add_argument(
        '--logs-dir',
        default=None,
        help="Répertoire des logs (défaut: utilise config.py)"
    )
    
    args = parser.parse_args()
    
    # Charger la config depuis le fichier ou les arguments
    config = load_config(args.config)
    
    athlete_id = args.athlete_id or (config and config.get('athlete_id'))
    api_key = args.api_key or (config and config.get('api_key'))
    
    if not athlete_id or not api_key:
        print("❌ Erreur: athlete_id et api_key requis")
        print("\nOptions:")
        print("  1. Passer --athlete-id et --api-key en arguments")
        print(f"  2. Créer {args.config} avec:")
        print('     {"athlete_id": "i123456", "api_key": "YOUR_KEY"}')
        print("\nObtenir l'API key:")
        print("  https://intervals.icu → Settings → Developer Settings → API Key")
        sys.exit(1)
    
    # Calculer la plage de dates
    newest = datetime.now()
    oldest = newest - timedelta(days=args.last_days)
    
    oldest_str = oldest.strftime('%Y-%m-%d')
    newest_str = newest.strftime('%Y-%m-%d')
    
    print(f"🔄 Synchronisation Intervals.icu")
    print(f"   Athlète: {athlete_id}")
    print(f"   Période: {oldest_str} → {newest_str}")
    print()
    
    try:
        # Connexion à l'API
        api = IntervalsAPI(athlete_id, api_key)
        
        # Récupérer les données
        print("📥 Récupération des données...")
        athlete_data = api.get_athlete()
        wellness_data = api.get_wellness(oldest=oldest_str, newest=newest_str)
        activities = api.get_activities(oldest=oldest_str, newest=newest_str)
        
        print(f"   ✅ {len(activities)} activité(s) trouvée(s)")
        print(f"   ✅ {len(wellness_data)} jour(s) de wellness")
        print()
        
        # Mettre à jour les logs
        logger = WorkoutLogger(args.logs_dir)
        
        if activities:
            logger.update_workouts_history(activities, wellness_data)
        
        logger.update_metrics_evolution(athlete_data, wellness_data)
        
        print()
        print("✅ Synchronisation terminée avec succès !")
        print()
        print("⚠️  N'oubliez pas de remplir manuellement:")
        print("   - RPE (perception effort)")
        print("   - Retour athlète (ressenti)")
        print("   - Notes coach (observations)")
        print()
        print("📤 Pour enregistrer les changements:")
        print("   git add logs/")
        print('   git commit -m "Sync: Séances depuis Intervals.icu"')
        print("   git push")
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ Erreur API: {e}")
        if e.response.status_code == 401:
            print("   → Vérifier l'API key et l'athlete_id")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
