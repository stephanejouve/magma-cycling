#!/usr/bin/env python3
"""
Helper script to update session status in planning JSON.
Script helper pour mettre à jour le statut des séances dans le JSON de planning.

Usage:
    # Cancel a session
    python update_session_status.py --week S074 --session S074-01 --status cancelled --reason "Contrainte extra-sportive"

    # Mark as completed
    python update_session_status.py --week S074 --session S074-03 --status completed

    # Skip a session
    python update_session_status.py --week S074 --session S074-05 --status skipped --reason "Fatigue"
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from weekly_planner import WeeklyPlanner


def main():
    parser = argparse.ArgumentParser(
        description="Mettre à jour le statut d'une séance dans le planning JSON"
    )
    parser.add_argument(
        '--week',
        type=str,
        required=True,
        help='Numéro de semaine (ex: S074)'
    )
    parser.add_argument(
        '--session',
        type=str,
        required=True,
        help='ID de la séance (ex: S074-01)'
    )
    parser.add_argument(
        '--status',
        type=str,
        required=True,
        choices=['completed', 'cancelled', 'skipped', 'rest_day', 'replaced', 'modified'],
        help='Nouveau statut'
    )
    parser.add_argument(
        '--reason',
        type=str,
        help='Raison de l\'annulation/modification (optionnel)'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        help='Date de début de semaine (YYYY-MM-DD) - optionnel si JSON existe déjà'
    )

    args = parser.parse_args()

    # Parse start date if provided
    if args.start_date:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    else:
        # Try to infer from existing JSON or use default
        start_date = datetime.now()  # Fallback

    # Create planner instance
    project_root = Path(__file__).parent.parent
    planner = WeeklyPlanner(args.week, start_date, project_root)

    # Update session status
    success = planner.update_session_status(
        session_id=args.session,
        status=args.status,
        reason=args.reason
    )

    if success:
        print(f"\n✅ Planning JSON mis à jour avec succès")
        sys.exit(0)
    else:
        print(f"\n❌ Échec de la mise à jour")
        sys.exit(1)


if __name__ == '__main__':
    main()
