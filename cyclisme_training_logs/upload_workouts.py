#!/usr/bin/env python3
"""
Upload Zwift workout files (.zwo) to Intervals.icu calendar.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Upload fichiers workouts Zwift (.zwo) vers calendrier Intervals.icu.
Convertit format Zwift en format Intervals.icu et planifie séances
automatiquement.

Examples:
    Upload single workout::

        from cyclisme_training_logs.upload_workouts import upload_workout
        from pathlib import Path

        # Upload fichier .zwo
        workout_file = Path("S073-01-INT-SweetSpot-V001.zwo")

        result = upload_workout(
            workout_file,
            target_date="2025-01-06"
        )

        if result.success:
            print(f"Uploaded: {result.workout_id}")

    Batch upload week::

        from cyclisme_training_logs.upload_workouts import upload_week

        # Upload semaine complète
        week_dir = Path("workouts/S073-Semaine73")

        results = upload_week(
            week_dir,
            start_date="2025-01-06"
        )

        print(f"Uploaded {len(results)} workouts")

    CLI usage::

        # Command-line upload
        poetry run upload-workouts --file S073-01-INT-SweetSpot-V001.zwo --date 2025-01-06

        # Upload entire week
        poetry run upload-workouts --week S073 --start-date 2025-01-06

Author: Stéphane Jouve
Created: 2024-10-XX
Updated: 2025-12-26 (Standardization Prompt 3 Priority 2)
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
                raise ValueError("Credentials API manquants")

            self.api = IntervalsAPI(athlete_id, api_key)
            print("✅ API Intervals.icu connectée")
        except Exception as e:
            print(f"❌ Erreur connexion API : {e}")
            sys.exit(1)
    
    def parse_workouts_file(self, filepath: Path) -> List[Dict]:
        """Parser un fichier contenant les workouts"""
        print(f"\n📄 Lecture fichier : {filepath}")
        
        if not filepath.exists():
            print(f"❌ Fichier non trouvé : {filepath}")
            return []
        
        content = filepath.read_text(encoding='utf-8')
        pattern = r'=== WORKOUT (.*?) ===\n(.*?)\n=== FIN WORKOUT ==='
        matches = re.findall(pattern, content, re.DOTALL)
        
        # Mode single workout : utiliser date exacte
        single_workout_mode = len(matches) == 1
        if single_workout_mode:
            print("  ℹ️  Mode single workout détecté - utilisation date exacte")
        
        workouts = []
        for workout_name, workout_content in matches:
            day_match = re.search(r'-(\d{2})-', workout_name)
            if not day_match:
                print(f"⚠️ Format invalide : {workout_name}")
                continue
            
            day_num = int(day_match.group(1))
            
            # Si single workout, utiliser start_date directement
            if single_workout_mode:
                workout_date = self.start_date
                print(f"  📌 Workout sera uploadé le {workout_date.strftime('%d/%m/%Y')} (date explicite)")
            else:
                workout_date = self.start_date + timedelta(days=day_num - 1)
            
            # FIX: Extraire le nom descriptif (première ligne du contenu)
            first_line = workout_content.strip().split('\n')[0]
            
            # FIX: Utiliser workout_name (depuis délimiteur) comme nom principal
            # Et first_line comme description courte
            workout_display_name = workout_name.strip()
            
            workouts.append({
                'filename': workout_name.strip(),
                'day': day_num,
                'date': workout_date.strftime('%Y-%m-%d'),
                'name': workout_display_name,  # ← FIX: Utiliser le nom du délimiteur
                'description': workout_content.strip()
            })
            
            print(f"  ✅ Jour {day_num:02d} ({workout_date.strftime('%d/%m')}) : {workout_name}")
        
        print(f"\n📊 Total : {len(workouts)} workout(s) détectés")
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
        
        pattern = r'=== WORKOUT (.*?) ===\n(.*?)\n=== FIN WORKOUT ==='
        matches = re.findall(pattern, content, re.DOTALL)
        
        # Mode single workout : utiliser date exacte
        single_workout_mode = len(matches) == 1
        if single_workout_mode:
            print("  ℹ️  Mode single workout détecté - utilisation date exacte")
        
        workouts = []
        for workout_name, workout_content in matches:
            day_match = re.search(r'-(\d{2})-', workout_name)
            if not day_match:
                continue
            
            day_num = int(day_match.group(1))
            
            # Si single workout, utiliser start_date directement
            if single_workout_mode:
                workout_date = self.start_date
                print(f"  📌 Workout sera uploadé le {workout_date.strftime('%d/%m/%Y')} (date explicite)")
            else:
                workout_date = self.start_date + timedelta(days=day_num - 1)
            
            # FIX: Extraire le nom descriptif (première ligne du contenu)
            first_line = workout_content.strip().split('\n')[0]
            
            # FIX: Utiliser workout_name (depuis délimiteur) comme nom principal
            workout_display_name = workout_name.strip()
            
            workouts.append({
                'filename': workout_name.strip(),
                'day': day_num,
                'date': workout_date.strftime('%Y-%m-%d'),
                'name': workout_display_name,  # ← FIX: Utiliser le nom du délimiteur
                'description': workout_content.strip()
            })
            
            print(f"  ✅ Jour {day_num:02d} ({workout_date.strftime('%d/%m')}) : {workout_name}")
        
        print(f"\n📊 Total : {len(workouts)} workout(s) dans le presse-papier")
        return workouts
    
    def upload_workout(self, workout: Dict) -> bool:
        """Uploader un workout sur Intervals.icu"""
        try:
            # Déterminer l'heure de début selon le jour de la semaine
            workout_date = datetime.strptime(workout['date'], '%Y-%m-%d')
            day_of_week = workout_date.weekday()  # 0=Lundi, 5=Samedi, 6=Dimanche

            # Samedi (5) → 09:00, autres jours → 17:00
            start_time = "09:00:00" if day_of_week == 5 else "17:00:00"

            event_data = {
                "category": "WORKOUT",
                "type": "VirtualRide",
                "name": workout['name'],
                "description": workout['description'],
                "start_date_local": f"{workout['date']}T{start_time}"
            }
            
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
        """Uploader tous les workouts"""
        print("\n" + "=" * 70)
        print("📤 UPLOAD WORKOUTS VERS INTERVALS.ICU")
        print(f"Semaine : {self.week_number}")
        print(f"Période : {self.start_date.strftime('%d/%m/%Y')} → {(self.start_date + timedelta(days=6)).strftime('%d/%m/%Y')}")
        print(f"Mode : {'DRY RUN (simulation)' if dry_run else 'RÉEL'}")
        print("=" * 70)
        
        stats = {'success': 0, 'failed': 0, 'skipped': 0}
        
        for workout in workouts:
            print(f"\n📅 Jour {workout['day']:02d} - {workout['date']}")
            print(f"   {workout['filename']}")
            
            if 'REPOS' in workout['filename'].upper():
                print("  ⭐ Ignoré (jour de repos)")
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
        
        print("\n" + "=" * 70)
        print("📊 RÉSUMÉ")
        print("=" * 70)
        print(f"✅ Succès   : {stats['success']}")
        print(f"❌ Échecs   : {stats['failed']}")
        print(f"⭐️  Ignorés  : {stats['skipped']}")
        print(f"📝 Total    : {len(workouts)}")
        print("=" * 70)
        
        return stats


def main():
    """Point d'entrée du script"""
    parser = argparse.ArgumentParser(description="Uploader des workouts sur Intervals.icu")
    parser.add_argument('--week-id', type=str, required=True, help='Numéro de semaine (format SXXX, ex: S072)')
    parser.add_argument('--start-date', type=str, required=True, 
                       help='Date de début - LUNDI pour semaine complète, date exacte pour single workout')
    parser.add_argument('--file', type=str, help='Fichier contenant les workouts')
    parser.add_argument('--dry-run', action='store_true', help='Simulation sans upload réel')
    
    args = parser.parse_args()
    
    if not args.week_id.startswith('S') or len(args.week_id) != 4:
        print(f"❌ Format semaine invalide : {args.week_id}")
        sys.exit(1)

    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    except ValueError:
        print(f"❌ Format date invalide : {args.start_date}")
        sys.exit(1)

    uploader = WorkoutUploader(args.week_id, start_date)
    
    if args.file:
        workouts = uploader.parse_workouts_file(Path(args.file))
    else:
        workouts = uploader.parse_clipboard()
    
    if not workouts:
        print("\n❌ Aucun workout détecté")
        sys.exit(1)
    
    if not args.dry_run:
        print(f"\n⚠️  ATTENTION : Upload RÉEL sur Intervals.icu")
        print(f"   {len(workouts)} workout(s) seront créés pour {args.week_id}")
        response = input("\nContinuer ? (o/n) : ")
        if response.lower() != 'o':
            print("❌ Upload annulé")
            sys.exit(0)
    
    stats = uploader.upload_all(workouts, dry_run=args.dry_run)
    
    if stats['failed'] > 0:
        sys.exit(1)
    else:
        print("\n✅ Upload terminé avec succès !")
        sys.exit(0)


if __name__ == '__main__':
    main()
