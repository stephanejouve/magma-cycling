#!/usr/bin/env python3
"""
check_activity_sources.py - Vérifier les sources des activités récentes

Ce script affiche la liste des activités récentes avec leur source
pour identifier rapidement celles qui viennent de Strava (données limitées)

Usage:
    python3 cyclisme_training_logs/check_activity_sources.py
    python3 cyclisme_training_logs/check_activity_sources.py --last-days 14
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

from cyclisme_training_logs.api.intervals_client import IntervalsClient


def load_config(config_file):
    """Charger la configuration depuis un fichier JSON"""
    config_path = Path(config_file).expanduser()
    if not config_path.exists():
        return None

    with open(config_path) as f:
        return json.load(f)


def format_source_icon(source):
    """Retourner un icône selon la source"""
    icons = {
        "STRAVA": "⚠️  ",
        "MANUAL": "✍️  ",
        "FILE_UPLOAD": "📤 ",
        "INTERVALS": "✅ ",
    }
    return icons.get(source, "❓ ")


def main():
    parser = argparse.ArgumentParser(description="Vérifier les sources des activités récentes")

    parser.add_argument("--athlete-id", help="ID de l'athlète Intervals.icu (ex: i123456)")
    parser.add_argument("--api-key", help="Clé API Intervals.icu")
    parser.add_argument(
        "--config",
        default="~/.intervals_config.json",
        help="Fichier de configuration JSON (défaut: ~/.intervals_config.json)",
    )
    parser.add_argument(
        "--last-days", type=int, default=7, help="Nombre de jours à vérifier (défaut: 7)"
    )

    args = parser.parse_args()

    # Charger la config
    config = load_config(args.config)

    athlete_id = args.athlete_id or (config and config.get("athlete_id"))
    api_key = args.api_key or (config and config.get("api_key"))

    if not athlete_id or not api_key:
        print("❌ Erreur: athlete_id et api_key requis")
        print("\nCréer ~/.intervals_config.json avec:")
        print('{"athlete_id": "i123456", "api_key": "YOUR_KEY"}')
        sys.exit(1)

    # Calculer la plage de dates
    newest = datetime.now()
    oldest = newest - timedelta(days=args.last_days)

    oldest_str = oldest.strftime("%Y-%m-%d")
    newest_str = newest.strftime("%Y-%m-%d")

    print("🔍 Vérification des sources d'activités")
    print(f"   Période: {oldest_str} → {newest_str}")
    print()

    try:
        # Connexion à l'API
        api = IntervalsClient(athlete_id=athlete_id, api_key=api_key)

        # Récupérer les activités
        print("📥 Récupération des activités...")
        activities = api.get_activities(oldest=oldest_str, newest=newest_str)

        if not activities:
            print("❌ Aucune activité trouvée")
            sys.exit(0)

        print(f"   ✅ {len(activities)} activité(s) trouvée(s)")
        print()

        # Compter par source
        sources_count = {}
        for activity in activities:
            source = activity.get("source", "Unknown")
            sources_count[source] = sources_count.get(source, 0) + 1

        # Afficher le résumé
        print("📊 Résumé par source :")
        print("-" * 60)
        for source, count in sorted(sources_count.items(), key=lambda x: x[1], reverse=True):
            icon = format_source_icon(source)
            print(f"   {icon}{source:15s} : {count:2d} activité(s)")
        print("-" * 60)
        print()

        # Afficher les détails
        print("📋 Détail des activités :")
        print("=" * 80)

        strava_count = 0
        for activity in reversed(activities):  # Plus récente en premier
            date_str = activity["start_date_local"][:10]
            date = datetime.fromisoformat(date_str)
            date_formatted = date.strftime("%d/%m/%Y")

            name = activity.get("name", "Séance")
            source = activity.get("source", "Unknown")
            activity_type = activity.get("type", "Cyclisme")
            activity_id = activity.get("id", "N/A")

            icon = format_source_icon(source)

            # Métriques
            tss = activity.get("icu_training_load", 0)
            duration_min = activity.get("moving_time", 0) // 60
            avg_power = activity.get("icu_average_watts", 0)

            # Warning pour Strava
            warning = ""
            if source == "STRAVA":
                strava_count += 1
                warning = " ⚠️  DONNÉES LIMITÉES"

            print(f"{icon}{date_formatted} | {name[:35]:35s} | {source:10s}")
            print(
                f"   Type: {activity_type:15s} | TSS: {tss:3.0f} | Durée: {duration_min:3d}min | Power: {avg_power:3.0f}W"
            )
            print(f"   ID: {activity_id}{warning}")
            print("-" * 80)

        print()

        # Avertissement final si Strava
        if strava_count > 0:
            print("⚠️  AVERTISSEMENT :")
            print(f"   {strava_count} activité(s) Strava détectée(s)")
            print("   Les données API sont limitées pour ces activités")
            print("   Les métriques de puissance peuvent être manquantes")
            print()
            print("💡 SOLUTION :")
            print("   Utiliser prepare_analysis.py qui gère automatiquement ces cas")
            print("   Le prompt généré indiquera les limitations à Claude.ai")
            print()

    except requests.exceptions.HTTPError as e:
        print(f"❌ Erreur API: {e}")
        if e.response.status_code == 401:
            print("   → Vérifier l'API key et l'athlete_id")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
