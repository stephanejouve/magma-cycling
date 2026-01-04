#!/usr/bin/env python3
"""
Clear Week Planning - Supprime les workouts planifiés erronés d'une semaine.

Script de maintenance pour supprimer tous les workouts planifiés (événements WORKOUT)
sur Intervals.icu pour une semaine donnée.

Usage:
    # Mode interactif (demande confirmation)
    python scripts/maintenance/clear_week_planning.py --week-id S075 --start-date 2026-01-05

    # Mode automatique (pas de confirmation)
    python scripts/maintenance/clear_week_planning.py --week-id S075 --start-date 2026-01-05 --yes

    # Mode dry-run (affiche ce qui serait supprimé sans supprimer)
    python scripts/maintenance/clear_week_planning.py --week-id S075 --start-date 2026-01-05 --dry-run

Examples:
    # Supprimer planning S075 avec confirmation
    python scripts/maintenance/clear_week_planning.py --week-id S075 --start-date 2026-01-05

    # Voir ce qui serait supprimé (simulation)
    python scripts/maintenance/clear_week_planning.py --week-id S075 --start-date 2026-01-05 --dry-run

Metadata:
    Created: 2026-01-04
    Author: Claude Code
    Category: M (Maintenance)
    Status: Production
    Priority: P2
"""

import argparse
import sys
from datetime import datetime, timedelta

from cyclisme_training_logs.api.intervals_client import IntervalsClient
from cyclisme_training_logs.config import get_intervals_config


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Supprimer workouts planifiés erronés d'une semaine sur Intervals.icu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:

  # Supprimer planning S075 (demande confirmation)
  python scripts/maintenance/clear_week_planning.py --week-id S075 --start-date 2026-01-05

  # Mode automatique sans confirmation
  python scripts/maintenance/clear_week_planning.py --week-id S075 --start-date 2026-01-05 --yes

  # Simulation (dry-run)
  python scripts/maintenance/clear_week_planning.py --week-id S075 --start-date 2026-01-05 --dry-run

Notes:
  - Supprime UNIQUEMENT les événements WORKOUT (workouts planifiés)
  - Ne touche PAS aux activités réalisées
  - Ne touche PAS aux notes de calendrier
  - Mode dry-run recommandé avant suppression réelle
        """,
    )

    parser.add_argument(
        "--week-id",
        type=str,
        required=True,
        help="ID de la semaine (format SXXX, ex: S075)",
    )

    parser.add_argument(
        "--start-date",
        type=str,
        required=True,
        help="Date de début de semaine (format YYYY-MM-DD)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mode simulation (affiche ce qui serait supprimé sans supprimer)",
    )

    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Mode automatique (pas de confirmation)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Mode verbose (affiche détails)",
    )

    return parser.parse_args()


def format_date(date_str: str) -> str:
    """Format date for display."""
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return date_str[:10]


def main():
    """Point d'entrée du script."""
    args = parse_args()

    # Parse dates
    try:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        end_date = start_date + timedelta(days=6)
    except ValueError as e:
        print(f"❌ Format de date invalide: {e}")
        print("   Format attendu: YYYY-MM-DD")
        return 1

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    print("\n" + "=" * 70)
    print(f"🗑️  CLEAR WEEK PLANNING - {args.week_id}")
    print("=" * 70)
    print()
    print(f"📅 Période: {format_date(start_str)} → {format_date(end_str)}")

    if args.dry_run:
        print("🔍 Mode: DRY-RUN (simulation)")
    elif args.yes:
        print("⚡ Mode: AUTOMATIQUE (pas de confirmation)")
    else:
        print("🤚 Mode: INTERACTIF (demande confirmation)")

    print()

    # Get Intervals.icu config
    try:
        config = get_intervals_config()
        athlete_id = config.athlete_id
        api_key = config.api_key
    except Exception as e:
        print(f"❌ Erreur configuration Intervals.icu: {e}")
        return 1

    # Initialize client
    try:
        client = IntervalsClient(athlete_id=athlete_id, api_key=api_key)
        print(f"✅ Connecté à Intervals.icu (athlete: {athlete_id})")
        print()
    except Exception as e:
        print(f"❌ Erreur connexion Intervals.icu: {e}")
        return 1

    # Fetch events for the week
    print("📥 Récupération des événements de la semaine...")
    try:
        events = client.get_events(oldest=start_str, newest=end_str)
        print(f"   ✅ {len(events)} événements trouvés")
    except Exception as e:
        print(f"❌ Erreur récupération événements: {e}")
        return 1

    # Filter WORKOUT events only
    workout_events = [e for e in events if e.get("category") == "WORKOUT"]

    if not workout_events:
        print()
        print("✅ Aucun workout planifié trouvé pour cette semaine")
        print("   La semaine est déjà vide ou n'a jamais été planifiée")
        return 0

    print()
    print(f"🎯 {len(workout_events)} workouts planifiés trouvés:")
    print()

    # Display workouts
    for i, event in enumerate(workout_events, 1):
        event_id = event.get("id")
        event_date = event.get("start_date_local", "")[:10]
        event_name = event.get("name", "Sans nom")

        # Get workout description if available
        workout = event.get("workout_doc", {})
        workout_name = workout.get("name", event_name)

        print(f"  {i}. [{format_date(event_date)}] {workout_name}")
        if args.verbose:
            print(f"     ID: {event_id}")
            if event.get("description"):
                desc = event.get("description", "")[:60]
                print(f"     Desc: {desc}...")

    print()
    print("=" * 70)

    # Confirmation
    if args.dry_run:
        print()
        print("🔍 DRY-RUN: Les événements ci-dessus SERAIENT supprimés")
        print("   Relancez sans --dry-run pour suppression réelle")
        return 0

    if not args.yes:
        print()
        print(f"⚠️  Vous allez supprimer {len(workout_events)} workouts planifiés")
        print("   Cette action est IRRÉVERSIBLE")
        print()
        response = input("Confirmer la suppression ? (oui/non): ").strip().lower()

        if response not in ["oui", "yes", "y", "o"]:
            print()
            print("❌ Suppression annulée par l'utilisateur")
            return 0

    # Delete workouts
    print()
    print("🗑️  Suppression en cours...")
    print()

    deleted_count = 0
    failed_count = 0

    for i, event in enumerate(workout_events, 1):
        event_id = event.get("id")
        event_date = event.get("start_date_local", "")[:10]
        workout = event.get("workout_doc", {})
        workout_name = workout.get("name", event.get("name", "Sans nom"))

        try:
            success = client.delete_event(event_id)

            if success:
                deleted_count += 1
                print(f"  ✅ [{i}/{len(workout_events)}] Supprimé: {workout_name}")
            else:
                failed_count += 1
                print(f"  ❌ [{i}/{len(workout_events)}] Échec: {workout_name}")

        except Exception as e:
            failed_count += 1
            print(f"  ❌ [{i}/{len(workout_events)}] Erreur: {workout_name}")
            if args.verbose:
                print(f"     Détail: {e}")

    # Summary
    print()
    print("=" * 70)
    print("📊 RÉSUMÉ")
    print("=" * 70)
    print()
    print(f"✅ Supprimés : {deleted_count}/{len(workout_events)}")
    if failed_count > 0:
        print(f"❌ Échecs    : {failed_count}/{len(workout_events)}")
    print()

    if deleted_count == len(workout_events):
        print(f"✅ Planning {args.week_id} complètement effacé !")
        print()
        print("💡 Prochaines étapes:")
        print(
            f"   1. Générer nouveau planning: wp --week-id {args.week_id} --start-date {start_str}"
        )
        print(f"   2. Uploader workouts: wu --week-id {args.week_id} --start-date {start_str}")
    elif failed_count > 0:
        print("⚠️  Certaines suppressions ont échoué")
        print("   Relancez le script pour nettoyer les événements restants")
    else:
        print("✅ Suppression terminée")

    print()
    print("=" * 70)

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
