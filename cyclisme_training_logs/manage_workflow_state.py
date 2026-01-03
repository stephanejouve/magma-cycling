#!/usr/bin/env python3
"""
Outil de gestion de l'état du workflow
Utilitaire CLI pour inspecter et manipuler le fichier .workflow_state.json
qui track les activités analysées. Permet d'afficher l'état, lister l'historique,
supprimer des entrées spécifiques ou réinitialiser complètement le state.

Examples:
    Command-line usage::

        # Afficher l'état actuel du workflow
        poetry run manage-state --show

        # Lister les 20 dernières activités analysées
        poetry run manage-state --list
        poetry run manage-state --list 50

        # Supprimer une activité spécifique du state
        poetry run manage-state --remove i113782165

        # Reset complet du workflow state
        poetry run manage-state --reset

    Programmatic usage::

        from cyclisme_training_logs.workflow_state import WorkflowState

        # Initialisation
        state = WorkflowState()

        # Récupération statistiques
        stats = state.get_stats()
        print(f"Total: {stats['total_analyses']}")

        # Vérification activité
        if state.is_analyzed("i113782165"):
            print("Déjà analysé")

        # Ajout nouvelle activité
        state.mark_analyzed(
            activity_id="i113782165",
            activity_date="2024-08-15"
        )

Author: Claude Code
Created: 2024-12-20
Updated: 2025-12-26 (Added Gartner TIME tags)

Metadata:
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: I
    Status: Production
    Priority: P1
    Version: v2
"""

import argparse
import sys
from datetime import datetime

from cyclisme_training_logs.workflow_state import WorkflowState


def show_state(state: WorkflowState):
    """Afficher l'état du workflow"""
    stats = state.get_stats()

    print()
    print("=" * 70)
    print("📊 ÉTAT DU WORKFLOW")
    print("=" * 70)
    print()
    print(f"Total analyses effectuées : {stats['total_analyses']}")
    print(f"Dernière activité analysée : {stats['last_analyzed_id']}")
    print(f"Date dernière analyse      : {stats['last_analyzed_date']}")
    print(f"Entrées dans l'historique  : {stats['history_count']}")
    print()

    # Afficher sessions spéciales documentées
    specials = state.get_documented_specials()
    if specials:
        print("📋 Sessions spéciales documentées :")
        for key, data in specials.items():
            print(f"  • {data['session_id']} [{data['date']}] - Type: {data['type']}")
        print()


def list_activities(state: WorkflowState, count: int = 10):
    """Lister les dernières activités analysées"""
    history = state.state.get("history", [])

    print()
    print("=" * 70)
    print(f"📝 DERNIÈRES ACTIVITÉS ANALYSÉES (max {count})")
    print("=" * 70)
    print()

    if not history:
        print("Aucune activité dans l'historique")
        return

    # Prendre les N dernières
    recent = history[-count:]

    for i, entry in enumerate(reversed(recent), 1):
        activity_id = entry.get("activity_id", "N/A")
        activity_date = entry.get("activity_date", "N/A")
        analyzed_at = entry.get("analyzed_at", "N/A")

        # Formater analyzed_at
        if analyzed_at != "N/A":
            try:
                dt = datetime.fromisoformat(analyzed_at)
                analyzed_at = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass

        print(f"{i:2d}. {activity_id:15s} | Séance: {activity_date} | Analysé: {analyzed_at}")

    print()


def remove_activity(state: WorkflowState, activity_id: str):
    """Supprimer une activité de l'historique"""
    print()
    print(f"🔍 Recherche de l'activité {activity_id}...")

    history = state.state.get("history", [])
    matching = [h for h in history if h["activity_id"] == activity_id]

    if not matching:
        print(f"❌ Activité {activity_id} non trouvée dans l'historique")
        return False

    print(f"✓ Trouvé {len(matching)} occurrence(s)")

    # Afficher les occurrences
    for entry in matching:
        print(f"  • Date séance: {entry.get('activity_date', 'N/A')}")
        print(f"    Analysé le: {entry.get('analyzed_at', 'N/A')}")

    # Confirmer
    print()
    confirm = input("⚠️  Confirmer la suppression ? (o/n) : ").strip().lower()

    if confirm != "o":
        print("❌ Suppression annulée")
        return False

    # Supprimer toutes les occurrences
    state.state["history"] = [h for h in history if h["activity_id"] != activity_id]

    # Mettre à jour last_analyzed si c'était la dernière
    if state.state.get("last_analyzed_activity_id") == activity_id:
        if state.state["history"]:
            last = state.state["history"][-1]
            state.state["last_analyzed_activity_id"] = last["activity_id"]
            state.state["last_analyzed_date"] = last["analyzed_at"]
        else:
            state.state["last_analyzed_activity_id"] = None
            state.state["last_analyzed_date"] = None

    state._save_state()

    print()
    print(f"✅ Activité {activity_id} supprimée avec succès")
    print("   L'activité sera de nouveau détectée comme non analysée")
    print()

    return True


def reset_state(state: WorkflowState):
    """Reset complet du workflow state"""
    print()
    print("⚠️  ATTENTION : Reset complet du workflow state")
    print()
    print("Cela va :")
    print("  • Supprimer TOUTES les activités de l'historique")
    print("  • Réinitialiser les compteurs")
    print("  • Supprimer les sessions spéciales documentées")
    print()

    confirm = input("⚠️  Confirmer le reset COMPLET ? (o/n) : ").strip().lower()

    if confirm != "o":
        print("❌ Reset annulé")
        return False

    state.reset()

    print()
    print("✅ Workflow state réinitialisé avec succès")
    print()

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Outil de gestion du workflow state",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Afficher l'état actuel
  poetry run manage-state --show

  # Lister les 15 dernières activités
  poetry run manage-state --list 15

  # Supprimer une activité spécifique
  poetry run manage-state --remove i113782165

  # Reset complet (attention!)
  poetry run manage-state --reset

  # Combinaisons
  poetry run manage-state --remove i113782165 --show
        """,
    )

    parser.add_argument("--show", action="store_true", help="Afficher l'état actuel du workflow")

    parser.add_argument(
        "--list",
        type=int,
        metavar="N",
        nargs="?",
        const=10,
        help="Lister les N dernières activités (défaut: 10)",
    )

    parser.add_argument(
        "--remove", type=str, metavar="ACTIVITY_ID", help="Supprimer une activité de l'historique"
    )

    parser.add_argument(
        "--reset", action="store_true", help="Reset complet du workflow state (DANGER!)"
    )

    args = parser.parse_args()

    # Au moins une action requise
    if not any([args.show, args.list, args.remove, args.reset]):
        parser.print_help()
        sys.exit(1)

    # Charger le workflow state
    try:
        state = WorkflowState()
    except Exception as e:
        print(f"❌ Erreur chargement workflow state: {e}")
        sys.exit(1)

    # Exécuter les actions dans l'ordre logique
    success = True

    # Reset en premier (destructif)
    if args.reset:
        success = reset_state(state) and success

    # Supprimer une activité
    if args.remove:
        success = remove_activity(state, args.remove) and success

    # Afficher l'état (en dernier pour voir les changements)
    if args.show:
        show_state(state)

    # Lister les activités
    if args.list is not None:
        list_activities(state, count=args.list)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
