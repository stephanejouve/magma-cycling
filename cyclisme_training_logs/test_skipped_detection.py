#!/usr/bin/env python3
"""
test_skipped_detection.py - Test du système de détection des séances sautées

Ce script permet de :
1. Tester la détection des workouts planifiés
2. Comparer avec activités réalisées
3. Afficher rapport détaillé des séances sautées
4. Générer exemples de markdown

Usage:
    python3 cyclisme_training_logs/test_skipped_detection.py
    python3 cyclisme_training_logs/test_skipped_detection.py --days 14
    python3 cyclisme_training_logs/test_skipped_detection.py --generate-markdown
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from cyclisme_training_logs.planned_sessions_checker import PlannedSessionsChecker


def load_credentials():
    """Charger credentials depuis config"""
    config_path = Path.home() / ".intervals_config.json"
    
    if not config_path.exists():
        print("❌ Fichier config non trouvé : ~/.intervals_config.json")
        print("\nCréer le fichier avec :")
        print('{')
        print('  "athlete_id": "i123456",')
        print('  "api_key": "votre_clé_api"')
        print('}')
        return None, None
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        athlete_id = config.get('athlete_id')
        api_key = config.get('api_key')
        
        if not athlete_id or not api_key:
            print("❌ Credentials invalides dans config")
            return None, None
        
        return athlete_id, api_key
        
    except Exception as e:
        print(f"❌ Erreur lecture config : {e}")
        return None, None


def print_header(title):
    """Afficher header stylisé"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_skipped_details(skipped_sessions):
    """Afficher détails des séances sautées"""
    if not skipped_sessions:
        print("✅ Aucune séance sautée détectée !\n")
        return
    
    print(f"⚠️  {len(skipped_sessions)} séance(s) sautée(s) détectée(s) :\n")
    
    # Grouper par date
    skipped_by_date = {}
    for session in skipped_sessions:
        date = session['planned_date']
        if date not in skipped_by_date:
            skipped_by_date[date] = []
        skipped_by_date[date].append(session)
    
    # Afficher par ordre chronologique
    for date in sorted(skipped_by_date.keys()):
        sessions = skipped_by_date[date]
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        day_name = date_obj.strftime('%A')
        days_ago = (datetime.now() - date_obj).days
        
        print(f"📅 {date} ({day_name}) - il y a {days_ago} jour(s)")
        
        for session in sessions:
            name = session['planned_name']
            tss = session['planned_tss']
            duration_min = session['planned_duration'] // 60
            
            print(f"   ⏭️  {name}")
            print(f"       TSS prévu : {tss}")
            print(f"       Durée prévue : {duration_min}min")
            
            if session.get('planned_description'):
                desc = session['planned_description'][:60]
                print(f"       Description : {desc}...")
            
            print()


def generate_markdown_examples(skipped_sessions):
    """Générer exemples de markdown pour séances sautées"""
    if not skipped_sessions:
        print("Aucune séance sautée → Pas de markdown à générer\n")
        return
    
    print_header("EXEMPLES MARKDOWN GÉNÉRÉS")
    
    # Prendre première séance sautée comme exemple
    session = skipped_sessions[0]
    
    # Générer markdown
    from planned_sessions_checker import PlannedSessionsChecker
    checker = PlannedSessionsChecker("", "")  # Dummy pour appel méthode
    
    markdown = checker.generate_skipped_session_markdown(
        skipped_session=session,
        metrics_pre={
            'ctl': 55,
            'atl': 48,
            'tsb': 7
        }
    )
    
    print("📝 Exemple markdown pour 1ère séance sautée :\n")
    print(markdown)
    
    print("\n💡 Ce markdown peut être inséré dans workouts-history.md")
    print("   via le workflow batch ou manuellement\n")


def calculate_impact(skipped_sessions):
    """Calculer impact des séances sautées"""
    if not skipped_sessions:
        return
    
    print_header("IMPACT SUR PROGRESSION")
    
    total_tss_lost = sum(s['planned_tss'] for s in skipped_sessions)
    total_duration_lost = sum(s['planned_duration'] for s in skipped_sessions)
    total_duration_hours = total_duration_lost / 3600
    
    print(f"TSS total perdu : {total_tss_lost}")
    print(f"Durée totale perdue : {total_duration_hours:.1f}h")
    print(f"Nombre séances : {len(skipped_sessions)}")
    print()
    
    # Impact CTL estimé (approximation)
    # CTL baisse ~7 points par semaine sans entraînement
    days_span = max(s['days_ago'] for s in skipped_sessions)
    estimated_ctl_impact = -(days_span / 7) * 7  # Approximation simplifiée
    
    print(f"Impact CTL estimé : {estimated_ctl_impact:.1f} points")
    print(f"(basé sur {days_span} jours max sans entraînement)")
    print()
    
    # Recommandations
    print("📋 Recommandations :")
    print()
    
    if total_tss_lost > 200:
        print("⚠️  PERTE TSS IMPORTANTE")
        print("   → Ajuster objectifs CTL semaine")
        print("   → Considérer report séances critiques")
        print()
    
    if len(skipped_sessions) >= 3:
        print("⚠️  PATTERN RÉCURRENT")
        print("   → Analyser causes des sauts")
        print("   → Ajuster planning si surcharge")
        print()
    
    print("✅ Actions suggérées :")
    print("   1. Documenter raisons des sauts")
    print("   2. Évaluer cohérence planning vs disponibilité")
    print("   3. Ajuster objectifs si besoin")
    print()


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="Test détection séances planifiées sautées"
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Nombre de jours à analyser (défaut: 7)'
    )
    parser.add_argument(
        '--generate-markdown',
        action='store_true',
        help='Générer exemples de markdown'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Mode verbose (debug)'
    )
    
    args = parser.parse_args()
    
    # Header
    print_header("TEST DÉTECTION SÉANCES SAUTÉES")
    
    # Charger credentials
    print("🔐 Chargement credentials...")
    athlete_id, api_key = load_credentials()
    
    if not athlete_id or not api_key:
        print("\n❌ Impossible de continuer sans credentials valides")
        return 1
    
    print(f"✅ Credentials chargés (athlete: {athlete_id})")
    
    # Définir période
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days)
    
    print(f"\n📅 Période analysée :")
    print(f"   Du : {start_date.strftime('%Y-%m-%d')}")
    print(f"   Au : {end_date.strftime('%Y-%m-%d')}")
    print(f"   ({args.days} jours)")
    
    # Créer checker
    print("\n🔍 Initialisation détecteur...")
    checker = PlannedSessionsChecker(
        athlete_id=athlete_id,
        api_key=api_key
    )
    
    # Détection
    print("\n🔎 Recherche séances sautées...")
    
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    skipped_sessions = checker.detect_skipped_sessions(
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        exclude_future=True
    )
    
    # Résultats
    print_header("RÉSULTATS")
    print_skipped_details(skipped_sessions)
    
    # Impact
    if skipped_sessions:
        calculate_impact(skipped_sessions)
    
    # Markdown si demandé
    if args.generate_markdown and skipped_sessions:
        generate_markdown_examples(skipped_sessions)
    
    # Conclusion
    print_header("CONCLUSION")
    
    if not skipped_sessions:
        print("✅ Excellent ! Toutes les séances planifiées ont été exécutées.")
        print("   Continuez sur cette lancée !\n")
        return 0
    else:
        print(f"⚠️  {len(skipped_sessions)} séance(s) à documenter")
        print("   Utiliser workflow_coach.py pour traiter en batch\n")
        return 0


if __name__ == '__main__':
    exit(main())
