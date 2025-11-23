#!/usr/bin/env python3
"""
Script d'Upload des Workouts vers Intervals.icu
Parse les workouts générés par Claude et les upload via API
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

try:
    from prepare_analysis import IntervalsAPI
except ImportError:
    print("❌ Erreur : prepare_analysis.py non trouvé")
    sys.exit(1)


class WorkoutUploader:
    """Upload des workouts vers Intervals.icu"""
    
    def __init__(self, week_number: str, start_date: datetime):
        self.week_number = week_number
        self.start_date = start_date
        self.api = None
        self._init_api()
    
    def _init_api(self):
        """Initialiser l'API Intervals.icu"""
        import os

        try:
            # Charger credentials depuis config ou env
            config_path = Path.home() / ".intervals_config.json"

            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    athlete_id = config.get('athlete_id')
                    api_key = config.get('api_key')
            else:
                athlete_id = os.getenv('VITE_INTERVALS_ATHLETE_ID')
                api_key = os.getenv('VITE_INTERVALS_API_KEY')

            if not athlete_id or not api_key:
                raise ValueError("Credentials API manquants. Configurer ~/.intervals_config.json ou variables d'environnement")

            self.api = IntervalsAPI(athlete_id, api_key)
            print("✅ API Intervals.icu connectée")
        except Exception as e:
            print(f"❌ Erreur connexion API : {e}")
            sys.exit(1)
    
    def parse_workouts_file(self, filepath: Path) -> List[Dict]:
        """
        Parser un fichier contenant les workouts générés par Claude
        Format attendu :
        
        === WORKOUT S069-01-END-EnduranceBase-V001 ===
        [contenu]
        === FIN WORKOUT ===
        """
        print(f"\n📄 Lecture fichier : {filepath}")
        
        if not filepath.exists():
            print(f"❌ Fichier non trouvé : {filepath}")
            return []
        
        content = filepath.read_text(encoding='utf-8')
        
        # Pattern pour extraire les workouts
        pattern = r'=== WORKOUT (.*?) ===\n(.*?)\n=== FIN WORKOUT ==='
        matches = re.findall(pattern, content, re.DOTALL)
        
        workouts = []
        for workout_name, workout_content in matches:
            # Extraire le numéro du jour (01-07)
            day_match = re.search(r'-(\d{2})-', workout_name)
            if not day_match:
                print(f"⚠️ Format invalide : {workout_name}")
                continue
            
            day_num = int(day_match.group(1))
            
            # Calculer la date pour ce jour
            workout_date = self.start_date + timedelta(days=day_num - 1)
            
            # Extraire le nom de la première ligne si disponible
            first_line = workout_content.strip().split('\n')[0]
            
            workouts.append({
                'filename': workout_name.strip(),
                'day': day_num,
                'date': workout_date.strftime('%Y-%m-%d'),
                'name': first_line if first_line else workout_name.strip(),
                'description': workout_content.strip()
            })
            
            print(f"  ✅ Jour {day_num:02d} ({workout_date.strftime('%d/%m')}) : {workout_name}")
        
        print(f"\n📊 Total : {len(workouts)} workout(s) détecté(s)")
        return workouts
    
    def parse_clipboard(self) -> List[Dict]:
        """Parser les workouts depuis le presse-papier"""
        import subprocess
        
        print("\n📋 Lecture presse-papier...")
        
        try:
            result = subprocess.run(['pbpaste'], capture_output=True, text=True, check=True)
            content = result.stdout
        except Exception as e:
            print(f"❌ Erreur lecture presse-papier : {e}")
            return []
        
        # Utiliser même pattern que parse_workouts_file
        pattern = r'=== WORKOUT (.*?) ===\n(.*?)\n=== FIN WORKOUT ==='
        matches = re.findall(pattern, content, re.DOTALL)
        
        workouts = []
        for workout_name, workout_content in matches:
            day_match = re.search(r'-(\d{2})-', workout_name)
            if not day_match:
                continue
            
            day_num = int(day_match.group(1))
            workout_date = self.start_date + timedelta(days=day_num - 1)
            first_line = workout_content.strip().split('\n')[0]
            
            workouts.append({
                'filename': workout_name.strip(),
                'day': day_num,
                'date': workout_date.strftime('%Y-%m-%d'),
                'name': first_line if first_line else workout_name.strip(),
                'description': workout_content.strip()
            })
            
            print(f"  ✅ Jour {day_num:02d} ({workout_date.strftime('%d/%m')}) : {workout_name}")
        
        print(f"\n📊 Total : {len(workouts)} workout(s) dans le presse-papier")
        return workouts
    
    def upload_workout(self, workout: Dict) -> bool:
        """
        Uploader un workout sur Intervals.icu
        
        API Endpoint : POST /api/v1/athlete/{id}/events
        Format : {
            "category": "WORKOUT",
            "name": "Nom",
            "description": "Contenu Intervals.icu",
            "start_date_local": "2024-11-24"
        }
        """
        try:
            # Préparer les données pour l'API
            event_data = {
                "category": "WORKOUT",
                "name": workout['name'],
                "description": workout['description'],
                "start_date_local": workout['date']
            }
            
            # Appel API
            response = self.api.create_event(event_data)
            
            if response:
                print(f"  ✅ Uploadé : {workout['name']} ({workout['date']})")
                return True
            else:
                print(f"  ❌ Échec : {workout['name']}")
                return False
                
        except Exception as e:
            print(f"  ❌ Erreur upload {workout['name']} : {e}")
            return False
    
    def upload_all(self, workouts: List[Dict], dry_run: bool = False) -> Dict:
        """
        Uploader tous les workouts
        
        Args:
            workouts: Liste des workouts à uploader
            dry_run: Si True, simule l'upload sans réellement envoyer
        
        Returns:
            Dictionnaire avec statistiques (success, failed, skipped)
        """
        print("\n" + "=" * 70)
        print(f"📤 UPLOAD WORKOUTS VERS INTERVALS.ICU")
        print(f"Semaine : {self.week_number}")
        print(f"Période : {self.start_date.strftime('%d/%m/%Y')} → {(self.start_date + timedelta(days=6)).strftime('%d/%m/%Y')}")
        print(f"Mode : {'DRY RUN (simulation)' if dry_run else 'RÉEL'}")
        print("=" * 70)
        
        stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
        
        for workout in workouts:
            print(f"\n📅 Jour {workout['day']:02d} - {workout['date']}")
            print(f"   {workout['filename']}")
            
            # Vérifier si c'est un jour de repos
            if 'REPOS' in workout['filename'].upper():
                print("  ⏭️  Ignoré (jour de repos)")
                stats['skipped'] += 1
                continue
            
            if dry_run:
                print("  🔍 DRY RUN - Upload simulé")
                stats['success'] += 1
            else:
                if self.upload_workout(workout):
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
        
        # Résumé
        print("\n" + "=" * 70)
        print("📊 RÉSUMÉ")
        print("=" * 70)
        print(f"✅ Succès   : {stats['success']}")
        print(f"❌ Échecs   : {stats['failed']}")
        print(f"⏭️  Ignorés  : {stats['skipped']}")
        print(f"📝 Total    : {len(workouts)}")
        print("=" * 70)
        
        return stats


def main():
    """Point d'entrée du script"""
    parser = argparse.ArgumentParser(
        description="Uploader des workouts sur Intervals.icu"
    )
    parser.add_argument(
        'week',
        type=str,
        help='Numéro de semaine (ex: S069)'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        required=True,
        help='Date de début (lundi) au format YYYY-MM-DD'
    )
    parser.add_argument(
        '--file',
        type=str,
        help='Fichier contenant les workouts (si non spécifié, lit le presse-papier)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulation sans upload réel'
    )
    
    args = parser.parse_args()
    
    # Validation format semaine
    if not args.week.startswith('S') or len(args.week) != 4:
        print(f"❌ Format semaine invalide : {args.week}")
        print("   Utiliser le format SXXX (ex: S069)")
        sys.exit(1)
    
    # Parsing date
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    except ValueError:
        print(f"❌ Format date invalide : {args.start_date}")
        print("   Utiliser le format YYYY-MM-DD (ex: 2024-11-24)")
        sys.exit(1)
    
    # Initialiser uploader
    uploader = WorkoutUploader(args.week, start_date)
    
    # Parser workouts
    if args.file:
        filepath = Path(args.file)
        workouts = uploader.parse_workouts_file(filepath)
    else:
        workouts = uploader.parse_clipboard()
    
    if not workouts:
        print("\n❌ Aucun workout détecté")
        print("\nFormat attendu :")
        print("=== WORKOUT S069-01-END-NomExercice-V001 ===")
        print("[contenu]")
        print("=== FIN WORKOUT ===")
        sys.exit(1)
    
    # Confirmation avant upload
    if not args.dry_run:
        print("\n⚠️  ATTENTION : Upload RÉEL sur Intervals.icu")
        print(f"   {len(workouts)} workout(s) seront créés pour {args.week}")
        response = input("\nContinuer ? (o/n) : ")
        if response.lower() != 'o':
            print("❌ Upload annulé")
            sys.exit(0)
    
    # Upload
    stats = uploader.upload_all(workouts, dry_run=args.dry_run)
    
    # Résultat final
    if stats['failed'] > 0:
        sys.exit(1)
    else:
        print("\n✅ Upload terminé avec succès !")
        sys.exit(0)


if __name__ == '__main__':
    main()
