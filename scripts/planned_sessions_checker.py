#!/usr/bin/env python3
"""
planned_sessions_checker.py - Détection des séances planifiées non exécutées

Ce module permet de :
1. Récupérer les workouts planifiés depuis Intervals.icu
2. Comparer avec les activités réellement effectuées
3. Détecter les séances sautées (planifiées mais non exécutées)
4. Intégrer cette détection dans le workflow principal

Usage:
    from planned_sessions_checker import PlannedSessionsChecker
    
    checker = PlannedSessionsChecker(athlete_id, api_key)
    skipped = checker.detect_skipped_sessions(start_date, end_date)
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from prepare_analysis import IntervalsAPI

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class PlannedSessionsChecker:
    """Détecteur de séances planifiées mais non exécutées"""

    def __init__(self, athlete_id: str, api_key: str):
        """
        Initialiser le checker avec credentials API

        Args:
            athlete_id: ID athlète Intervals.icu
            api_key: Clé API Intervals.icu
        """
        self.api = IntervalsAPI(athlete_id=athlete_id, api_key=api_key)
        self.athlete_id = athlete_id

    def get_planned_workouts(
        self, 
        start_date: str, 
        end_date: str,
        category: str = "WORKOUT"
    ) -> List[Dict]:
        """
        Récupérer les workouts planifiés depuis l'API events

        Args:
            start_date: Date début (format YYYY-MM-DD)
            end_date: Date fin (format YYYY-MM-DD)
            category: Catégorie événement (défaut: WORKOUT)

        Returns:
            Liste des workouts planifiés dans la période
        """
        try:
            events = self.api.get_events(oldest=start_date, newest=end_date)
            
            # Filtrer uniquement les workouts
            workouts = [
                e for e in events 
                if e.get('category') == category
            ]
            
            logger.info(f"Workouts planifiés trouvés : {len(workouts)}")
            return workouts
            
        except Exception as e:
            logger.error(f"Erreur récupération workouts planifiés : {e}")
            return []

    def _find_matching_activity(
        self,
        workout: Dict,
        activities: List[Dict],
        tolerance_hours: int = 6
    ) -> Optional[Dict]:
        """
        Chercher une activité correspondant à un workout planifié

        Critères de correspondance :
        1. Date dans tolérance (défaut ±6h)
        2. Nom similaire (workout name dans activity name)
        3. Type compatible si disponible

        Args:
            workout: Workout planifié
            activities: Liste des activités réalisées
            tolerance_hours: Tolérance temporelle en heures

        Returns:
            Activité correspondante ou None
        """
        workout_date = datetime.fromisoformat(
            workout['start_date_local'].replace('Z', '+00:00')
        )
        workout_name = workout.get('name', '').upper()
        
        # Extraction code séance si présent (ex: S070-01)
        workout_code = None
        if '-' in workout_name:
            parts = workout_name.split('-')
            if len(parts) >= 2:
                workout_code = f"{parts[0]}-{parts[1]}"  # Ex: "S070-01"

        for activity in activities:
            activity_date = datetime.fromisoformat(
                activity['start_date_local'].replace('Z', '+00:00')
            )
            
            # Check 1: Tolérance temporelle
            time_diff = abs((activity_date - workout_date).total_seconds() / 3600)
            if time_diff > tolerance_hours:
                continue
            
            # Check 2: Correspondance nom
            activity_name = activity.get('name', '').upper()
            
            # Méthode 1: Code séance présent dans les deux
            if workout_code and workout_code in activity_name:
                logger.debug(
                    f"Match trouvé (code) : {workout_code} → "
                    f"{activity.get('id')}"
                )
                return activity
            
            # Méthode 2: Nom workout dans nom activité
            if workout_name and workout_name in activity_name:
                logger.debug(
                    f"Match trouvé (nom) : {workout_name[:30]}... → "
                    f"{activity.get('id')}"
                )
                return activity
            
            # Méthode 3: Activité dans nom workout (inversé)
            if activity_name and activity_name in workout_name:
                logger.debug(
                    f"Match trouvé (inverse) : {activity_name[:30]}... → "
                    f"{activity.get('id')}"
                )
                return activity

        return None

    def detect_skipped_sessions(
        self,
        start_date: str,
        end_date: str,
        exclude_future: bool = True
    ) -> List[Dict]:
        """
        Détecter les séances planifiées mais non exécutées

        Algorithme :
        1. Récupérer workouts planifiés (API events)
        2. Récupérer activités réalisées (API activities)
        3. Pour chaque workout planifié :
           - Si date future ET exclude_future → skip
           - Chercher activité correspondante
           - Si absente → SKIPPED
        4. Retourner liste des skipped avec contexte

        Args:
            start_date: Date début recherche (YYYY-MM-DD)
            end_date: Date fin recherche (YYYY-MM-DD)
            exclude_future: Exclure workouts futurs (défaut: True)

        Returns:
            Liste des séances sautées avec métadonnées
        """
        logger.info(f"\n{'=' * 70}")
        logger.info(f"DÉTECTION SÉANCES PLANIFIÉES SAUTÉES")
        logger.info(f"{'=' * 70}")
        logger.info(f"Période : {start_date} → {end_date}")
        
        # 1. Récupérer workouts planifiés
        planned_workouts = self.get_planned_workouts(start_date, end_date)
        
        if not planned_workouts:
            logger.info("Aucun workout planifié trouvé")
            return []
        
        # 2. Récupérer activités réalisées
        try:
            activities = self.api.get_activities(
                oldest=start_date,
                newest=end_date
            )
            logger.info(f"Activités réalisées trouvées : {len(activities)}")
        except Exception as e:
            logger.error(f"Erreur récupération activités : {e}")
            return []
        
        # 3. Comparer planifié vs réalisé
        now = datetime.now()
        skipped_sessions = []
        
        for workout in planned_workouts:
            workout_date = datetime.fromisoformat(
                workout['start_date_local'].replace('Z', '+00:00')
            )
            
            # Skip si futur et exclude_future activé
            if exclude_future and workout_date > now:
                logger.debug(
                    f"Skip (futur) : {workout.get('name', 'N/A')} "
                    f"[{workout_date.date()}]"
                )
                continue
            
            # Chercher correspondance
            matched_activity = self._find_matching_activity(
                workout,
                activities,
                tolerance_hours=6
            )
            
            if not matched_activity:
                # Séance planifiée mais non exécutée
                skipped_sessions.append({
                    'planned_id': workout.get('id'),
                    'planned_date': workout_date.strftime('%Y-%m-%d'),
                    'planned_date_iso': workout['start_date_local'],
                    'planned_name': workout.get('name', 'Séance sans nom'),
                    'planned_tss': workout.get('load', 0),
                    'planned_duration': workout.get('duration', 0),
                    'planned_description': workout.get('description', ''),
                    'status': 'SKIPPED',
                    'day_of_week': workout_date.strftime('%A'),
                    'days_ago': (now - workout_date).days
                })
                
                logger.warning(
                    f"⏭️  SKIPPED : {workout.get('name', 'N/A')[:40]} "
                    f"[{workout_date.date()}]"
                )
        
        # 4. Rapport final
        logger.info(f"\n{'=' * 70}")
        logger.info(f"RÉSUMÉ DÉTECTION")
        logger.info(f"{'=' * 70}")
        logger.info(f"Workouts planifiés : {len(planned_workouts)}")
        logger.info(f"Activités réalisées : {len(activities)}")
        logger.info(f"Séances sautées : {len(skipped_sessions)}")
        logger.info(f"{'=' * 70}\n")
        
        return skipped_sessions

    def generate_skipped_session_markdown(
        self,
        skipped_session: Dict,
        metrics_pre: Optional[Dict] = None
    ) -> str:
        """
        Générer bloc markdown pour séance sautée

        Args:
            skipped_session: Données séance sautée
            metrics_pre: Métriques pré-séance (CTL/ATL/TSB)

        Returns:
            Bloc markdown formaté
        """
        # Extraire données
        session_name = skipped_session['planned_name']
        date_str = datetime.strptime(
            skipped_session['planned_date'], 
            '%Y-%m-%d'
        ).strftime('%d/%m/%Y')
        
        day_of_week = skipped_session['day_of_week']
        days_ago = skipped_session['days_ago']
        planned_tss = skipped_session['planned_tss']
        planned_duration = skipped_session['planned_duration']
        
        # Métriques pré-séance
        ctl_pre = metrics_pre.get('ctl', 'N/A') if metrics_pre else 'N/A'
        atl_pre = metrics_pre.get('atl', 'N/A') if metrics_pre else 'N/A'
        tsb_pre = metrics_pre.get('tsb', 'N/A') if metrics_pre else 'N/A'
        
        # Construire markdown
        markdown = f"""### {session_name} [SAUTÉE]
Date : {date_str} ({day_of_week})

#### Métriques Pré-séance
- CTL : {ctl_pre}
- ATL : {atl_pre}
- TSB : {tsb_pre}

#### Séance Planifiée
- Charge prévue : {planned_tss} TSS
- Durée prévue : {planned_duration // 60}min
- Non exécutée (il y a {days_ago} jour{'s' if days_ago > 1 else ''})

#### Impact
- TSS non réalisé : {planned_tss}
- Ajustement CTL : Aucun (séance sautée)
- Ajustement ATL : Aucun (séance sautée)

#### Notes Coach
Séance planifiée non exécutée. Raison à documenter.
Évaluer impact sur progression semaine et ajuster planning si nécessaire.

---
"""
        return markdown


def main():
    """Test du module"""
    import json
    from pathlib import Path
    
    # Charger credentials
    config_path = Path.home() / ".intervals_config.json"
    if not config_path.exists():
        print("❌ Config API non trouvée")
        return
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    athlete_id = config.get('athlete_id')
    api_key = config.get('api_key')
    
    if not athlete_id or not api_key:
        print("❌ Credentials invalides")
        return
    
    # Test détection
    checker = PlannedSessionsChecker(athlete_id, api_key)
    
    # Dernières 7 jours
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    print(f"\n🔍 Test détection séances sautées")
    print(f"Période : {start_date} → {end_date}\n")
    
    skipped = checker.detect_skipped_sessions(start_date, end_date)
    
    if skipped:
        print(f"\n⚠️  {len(skipped)} séance(s) sautée(s) détectée(s) :\n")
        for session in skipped:
            print(f"  • {session['planned_date']} : {session['planned_name']}")
            print(f"    TSS prévu : {session['planned_tss']}")
            print()
    else:
        print("✅ Aucune séance sautée détectée")


if __name__ == '__main__':
    main()
