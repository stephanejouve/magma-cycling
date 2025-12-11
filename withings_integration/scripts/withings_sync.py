"""
Synchronisation automatique Withings → Intervals.icu
À exécuter quotidiennement (ou via cron/automation)
"""

import json
import os
import sys
from datetime import datetime, timedelta

# Ajouter le repertoire parent au PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from withings_integration import (
    WithingsIntegration,
    sync_weight_to_intervals,
    sync_sleep_to_intervals
)

# Configuration
CREDENTIALS_FILE = 'withings_credentials.json'
INTERVALS_API_KEY = os.getenv('INTERVALS_API_KEY', 'REDACTED_INTERVALS_KEY')
INTERVALS_ATHLETE_ID = os.getenv('INTERVALS_ATHLETE_ID', 'i151223')

CLIENT_ID = "c5e8820a701242a8708c54ee9fcc83915f02270f2ae0930b9a5917bbb3d21278"
CLIENT_SECRET = os.getenv('WITHINGS_SECRET')
CALLBACK_URI = "https://4f3c-2a01-cb14-8513-df00-2031-d098-d697-75c1.ngrok-free.app/auth/withings/callback"


def load_withings_api():
    """Charge l'API Withings avec credentials sauvegardés"""
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            f"Fichier credentials introuvable: {CREDENTIALS_FILE}\n"
            "Exécutez d'abord withings_setup.py"
        )
    
    with open(CREDENTIALS_FILE, 'r') as f:
        credentials = json.load(f)
    
    withings = WithingsIntegration(CLIENT_ID, CLIENT_SECRET, CALLBACK_URI)
    withings.load_credentials(credentials)
    
    return withings


def sync_daily_data(days_back: int = 1):
    """
    Synchronise les données Withings vers Intervals.icu
    
    Args:
        days_back: Nombre de jours à synchroniser (défaut: 1 = aujourd'hui uniquement)
    """
    print("\n" + "="*70)
    print(f"SYNCHRONISATION WITHINGS → INTERVALS.ICU")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    # Charger API Withings
    try:
        withings = load_withings_api()
        print("✓ Connexion Withings établie")
    except Exception as e:
        print(f"✗ Erreur connexion Withings: {e}")
        return
    
    # Définir la période
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    print(f"\nPériode: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
    print("-" * 70 + "\n")
    
    # 1. SYNCHRONISER LE POIDS
    print("📊 SYNCHRONISATION POIDS")
    print("-" * 70)
    
    try:
        weight_data_list = withings.get_weight_data(start_date, end_date)
        
        if weight_data_list:
            print(f"Trouvé {len(weight_data_list)} mesure(s) de poids:\n")
            
            for weight_data in weight_data_list:
                print(f"  • {weight_data['date']}: {weight_data['weight_kg']}kg")
                
                # Synchroniser vers Intervals.icu
                try:
                    sync_weight_to_intervals(
                        weight_data,
                        INTERVALS_API_KEY,
                        INTERVALS_ATHLETE_ID
                    )
                except Exception as e:
                    print(f"    ⚠ Erreur sync: {e}")
            
            print()
        else:
            print("  ℹ Aucune mesure de poids sur cette période\n")
            
    except Exception as e:
        print(f"  ✗ Erreur récupération poids: {e}\n")
    
    # 2. SYNCHRONISER LE SOMMEIL
    print("😴 SYNCHRONISATION SOMMEIL")
    print("-" * 70)
    
    try:
        sleep_data_list = withings.get_sleep_data(
            start_date.date(),
            end_date.date()
        )
        
        if sleep_data_list:
            print(f"Trouvé {len(sleep_data_list)} session(s) de sommeil:\n")
            
            for sleep_data in sleep_data_list:
                print(f"  • {sleep_data['date']}:")
                print(f"    Durée: {sleep_data['total_sleep_hours']}h")
                print(f"    Score: {sleep_data['sleep_score']}/100")
                print(f"    Profond: {sleep_data['deep_sleep_minutes']}min")
                print(f"    Réveils: {sleep_data['wakeup_count']}")
                
                # Évaluation pour entraînement
                assessment = withings.get_sleep_quality_assessment(sleep_data)
                
                print(f"\n    🎯 RECOMMANDATIONS ENTRAÎNEMENT:")
                for rec in assessment['recommendations']:
                    print(f"       → {rec}")
                
                # Synchroniser vers Intervals.icu
                try:
                    sync_sleep_to_intervals(
                        sleep_data,
                        INTERVALS_API_KEY,
                        INTERVALS_ATHLETE_ID
                    )
                except Exception as e:
                    print(f"    ⚠ Erreur sync: {e}")
                
                print()
            
        else:
            print("  ℹ Aucune session de sommeil sur cette période\n")
            
    except Exception as e:
        print(f"  ✗ Erreur récupération sommeil: {e}\n")
    
    # 3. RÉSUMÉ FINAL
    print("="*70)
    print("SYNCHRONISATION TERMINÉE")
    print("="*70)
    
    # Récupérer la dernière nuit pour affichage final
    try:
        last_sleep = withings.get_last_night_sleep()
        if last_sleep:
            assessment = withings.get_sleep_quality_assessment(last_sleep)
            
            print(f"\n📋 STATUT ACTUEL POUR ENTRAÎNEMENT:")
            print(f"   Sommeil: {last_sleep['total_sleep_hours']}h")
            print(f"   Score: {last_sleep['sleep_score']}/100")
            print(f"   Intensité recommandée: {assessment['recommended_intensity'].upper()}")
            
            if assessment['ready_for_vo2']:
                print(f"   ✅ CONDITIONS OPTIMALES POUR VO2 MAX")
            else:
                print(f"   ⚠️  VO2 max déconseillé")
    except:
        pass
    
    print()


def get_training_readiness():
    """
    Évalue la disponibilité pour entraînement intensif
    Retourne un dict avec recommandations
    """
    withings = load_withings_api()
    
    # Récupérer dernière nuit
    sleep = withings.get_last_night_sleep()
    
    if not sleep:
        return {
            'ready': False,
            'reason': 'Pas de données de sommeil',
            'recommendation': 'recovery_only'
        }
    
    assessment = withings.get_sleep_quality_assessment(sleep)
    
    return {
        'ready': assessment['ready_for_vo2'],
        'sleep_hours': sleep['total_sleep_hours'],
        'sleep_score': sleep['sleep_score'],
        'deep_sleep': sleep['deep_sleep_minutes'],
        'recommendation': assessment['recommended_intensity'],
        'details': assessment['recommendations']
    }


def display_weekly_summary():
    """Affiche un résumé de la semaine écoulée"""
    withings = load_withings_api()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    print("\n" + "="*70)
    print("RÉSUMÉ HEBDOMADAIRE")
    print("="*70 + "\n")
    
    # Sommeil sur 7 jours
    sleep_data = withings.get_sleep_data(start_date.date(), end_date.date())
    
    if sleep_data:
        total_hours = sum(s['total_sleep_hours'] for s in sleep_data if s['total_sleep_hours'])
        avg_hours = total_hours / len(sleep_data)
        avg_score = sum(s['sleep_score'] for s in sleep_data if s['sleep_score']) / len(sleep_data)
        
        nights_above_7h = sum(1 for s in sleep_data if s['total_sleep_hours'] and s['total_sleep_hours'] >= 7)
        
        print(f"😴 SOMMEIL (7 derniers jours)")
        print(f"   Moyenne: {avg_hours:.1f}h/nuit")
        print(f"   Score moyen: {avg_score:.0f}/100")
        print(f"   Nuits >7h: {nights_above_7h}/7")
        
        # Dette de sommeil
        target_hours = 7 * 7  # 7h par nuit × 7 nuits
        actual_hours = total_hours
        sleep_debt = target_hours - actual_hours
        
        print(f"   Dette de sommeil: {sleep_debt:.1f}h")
        
        if sleep_debt > 5:
            print(f"   ⚠️  DETTE IMPORTANTE - Prioriser récupération")
        elif sleep_debt > 0:
            print(f"   ⚠️  Légère dette - Attention charge entraînement")
        else:
            print(f"   ✅ Sommeil optimal")
    
    print()
    
    # Poids sur 7 jours
    weight_data = withings.get_weight_data(start_date, end_date)
    
    if weight_data:
        first_weight = weight_data[0]['weight_kg']
        last_weight = weight_data[-1]['weight_kg']
        delta = last_weight - first_weight
        
        print(f"📊 POIDS (7 derniers jours)")
        print(f"   Début semaine: {first_weight}kg")
        print(f"   Fin semaine: {last_weight}kg")
        print(f"   Variation: {delta:+.1f}kg")
    
    print()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'summary':
            display_weekly_summary()
        elif command == 'readiness':
            readiness = get_training_readiness()
            print(f"\n🎯 DISPONIBILITÉ ENTRAÎNEMENT:")
            print(f"   Sommeil: {readiness.get('sleep_hours', 'N/A')}h")
            print(f"   Score: {readiness.get('sleep_score', 'N/A')}/100")
            print(f"   Recommandation: {readiness.get('recommendation', 'N/A').upper()}")
            
            if readiness['ready']:
                print(f"   ✅ OK pour VO2 max")
            else:
                print(f"   ⚠️  {readiness.get('reason', 'Conditions sous-optimales')}")
            print()
        elif command == 'sync':
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 1
            sync_daily_data(days_back=days)
        else:
            print(f"Commande inconnue: {command}")
            print("\nUtilisation:")
            print("  python withings_sync.py sync [days]  - Synchroniser N derniers jours")
            print("  python withings_sync.py readiness    - Vérifier disponibilité")
            print("  python withings_sync.py summary      - Résumé hebdomadaire")
    else:
        # Par défaut: sync quotidien
        sync_daily_data(days_back=1)
