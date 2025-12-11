#!/usr/bin/env python3
"""
mark_cancelled.py - Helper pour marquer une session comme annulée

Ce script met à jour le fichier week_planning.json pour marquer
une session comme annulée avec la raison fournie.

Usage:
    python3 scripts/mark_cancelled.py SESSION_ID 'Raison annulation'

Exemples:
    python3 scripts/mark_cancelled.py S071-04 'Problème matériel'
    python3 scripts/mark_cancelled.py S071-06 'Fatigue excessive'
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def mark_cancelled(session_id: str, reason: str, planning_dir: Path = None) -> bool:
    """
    Marque une session comme annulée dans week_planning.json

    Args:
        session_id: Ex "S071-04"
        reason: Raison annulation
        planning_dir: Répertoire plannings (optionnel)

    Returns:
        True si succès, False sinon
    """
    # Répertoire plannings
    if planning_dir is None:
        planning_dir = Path.cwd() / "data" / "week_planning"

    # Extraire week_id
    try:
        week_id = session_id.split('-')[0]
    except Exception:
        print(f"❌ Format session_id invalide : {session_id}")
        print("   Format attendu : SXXX-JJ (ex: S071-04)")
        return False

    planning_file = planning_dir / f"week_planning_{week_id}.json"

    # Vérifier existence
    if not planning_file.exists():
        print(f"❌ Planning {week_id} introuvable")
        print(f"   Cherché : {planning_file}")
        print(f"\n💡 Crée d'abord le planning avec upload_workouts.py")
        return False

    # Charger planning
    try:
        with open(planning_file, 'r', encoding='utf-8') as f:
            planning = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Erreur lecture JSON : {e}")
        return False

    # Trouver session
    found = False
    for session in planning['planned_sessions']:
        if session['session_id'] == session_id:
            # Sauvegarder état précédent
            previous_status = session.get('status', 'unknown')

            # Mettre à jour
            session['status'] = 'cancelled'
            session['cancellation_reason'] = reason
            session['cancellation_timestamp'] = datetime.now().isoformat()
            session['previous_status'] = previous_status
            found = True
            break

    if not found:
        print(f"❌ Session {session_id} non trouvée dans planning")
        available = [s['session_id'] for s in planning['planned_sessions']]
        print(f"\n📋 Sessions disponibles : {', '.join(available)}")
        return False

    # Sauvegarder
    try:
        with open(planning_file, 'w', encoding='utf-8') as f:
            json.dump(planning, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Erreur écriture JSON : {e}")
        return False

    # Confirmation
    print("\n" + "="*70)
    print(f"✅ {session_id} marquée comme annulée")
    print("="*70)
    print(f"📝 Raison        : {reason}")
    print(f"🔄 Statut ancien : {previous_status}")
    print(f"🔄 Statut nouveau: cancelled")
    print(f"📁 Fichier       : {planning_file}")
    print(f"🕐 Timestamp     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")

    return True


def mark_rest_day(session_id: str, reason: str = None, planning_dir: Path = None) -> bool:
    """
    Marque une session comme repos planifié

    Args:
        session_id: Ex "S071-07"
        reason: Raison repos (optionnel)
        planning_dir: Répertoire plannings (optionnel)

    Returns:
        True si succès, False sinon
    """
    if planning_dir is None:
        planning_dir = Path.cwd() / "data" / "week_planning"

    # Extraire week_id
    try:
        week_id = session_id.split('-')[0]
    except Exception:
        print(f"❌ Format session_id invalide : {session_id}")
        return False

    planning_file = planning_dir / f"week_planning_{week_id}.json"

    if not planning_file.exists():
        print(f"❌ Planning {week_id} introuvable")
        return False

    # Charger planning
    try:
        with open(planning_file, 'r', encoding='utf-8') as f:
            planning = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Erreur lecture JSON : {e}")
        return False

    # Trouver session
    found = False
    for session in planning['planned_sessions']:
        if session['session_id'] == session_id:
            previous_status = session.get('status', 'unknown')
            session['status'] = 'rest_day'
            if reason:
                session['rest_reason'] = reason
            session['rest_timestamp'] = datetime.now().isoformat()
            session['previous_status'] = previous_status
            found = True
            break

    if not found:
        print(f"❌ Session {session_id} non trouvée")
        return False

    # Sauvegarder
    try:
        with open(planning_file, 'w', encoding='utf-8') as f:
            json.dump(planning, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Erreur écriture : {e}")
        return False

    # Confirmation
    print(f"\n✅ {session_id} marquée comme repos planifié")
    if reason:
        print(f"📝 Raison : {reason}")
    print(f"📁 Fichier : {planning_file}\n")

    return True


def main():
    """Point d'entrée CLI"""

    if len(sys.argv) < 2:
        print("\n" + "="*70)
        print("MARK CANCELLED - Helper Gestion Planning")
        print("="*70)
        print("\nUsage :")
        print("  python3 scripts/mark_cancelled.py SESSION_ID 'Raison annulation'\n")
        print("Options :")
        print("  --rest : Marquer comme repos planifié au lieu d'annulation\n")
        print("Exemples :")
        print("  python3 scripts/mark_cancelled.py S071-04 'Problème matériel'")
        print("  python3 scripts/mark_cancelled.py S071-06 'Fatigue excessive'")
        print("  python3 scripts/mark_cancelled.py S071-07 'Repos dimanche' --rest\n")
        print("="*70 + "\n")
        sys.exit(1)

    # Parser arguments
    is_rest = '--rest' in sys.argv
    if is_rest:
        sys.argv.remove('--rest')

    if len(sys.argv) < 2:
        print("❌ Session ID manquant\n")
        sys.exit(1)

    session_id = sys.argv[1]
    reason = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else None

    # Validation format session_id
    if not session_id.startswith('S') or '-' not in session_id:
        print(f"❌ Format session_id invalide : {session_id}")
        print("   Format attendu : SXXX-JJ (ex: S071-04)")
        sys.exit(1)

    # Validation raison pour cancelled
    if not is_rest and not reason:
        print("❌ Raison obligatoire pour annulation")
        print("   Usage : mark_cancelled.py SESSION_ID 'Raison'")
        sys.exit(1)

    # Exécution
    if is_rest:
        success = mark_rest_day(session_id, reason)
    else:
        success = mark_cancelled(session_id, reason)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
