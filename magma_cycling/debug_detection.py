#!/usr/bin/env python3
"""Script de debug détection multi-séances - VERSION DEBUG AVANCÉE."""
from datetime import datetime, timedelta

from magma_cycling.config import create_intervals_client
from magma_cycling.utils.cli import cli_main
from magma_cycling.workflow_state import WorkflowState


@cli_main
def main():
    """Command-line entry point for debugging gap detection."""
    # Init API via centralized config
    api = create_intervals_client()

    print(f"✅ Credentials OK (Athlete: {api.athlete_id})\n")

    # Init state
    state = WorkflowState()

    print("═══════════════════════════════════════════")
    print("DIAGNOSTIC DÉTECTION MULTI-SÉANCES (DEBUG)")
    print("═══════════════════════════════════════════\n")

    # 1. État workflow actuel
    print("1️⃣  ÉTAT WORKFLOW :")
    print(f"   Last timestamp : {state.state.get('last_analyzed_timestamp')}")
    print(f"   Analyzed count : {len(state.state.get('analyzed_activities', []))}")

    # 🔍 NOUVEAU : Afficher l'historique complet
    history = state.state.get("history", [])
    print(f"   History count  : {len(history)}")

    if history:
        print("   Last 3 entries : ")
        for entry in history[-3:]:
            print(f"      - {entry}")

    print()

    # 2. Récupération API (24h)
    oldest_date = datetime.now() - timedelta(days=1)
    newest_date = datetime.now()

    print("2️⃣  RÉCUPÉRATION API (24h) :")
    print(f"   Oldest : {oldest_date.strftime('%Y-%m-%d')}")
    print(f"   Newest : {newest_date.strftime('%Y-%m-%d')}")

    activities = api.get_activities(
        oldest=oldest_date.strftime("%Y-%m-%d"), newest=newest_date.strftime("%Y-%m-%d")
    )

    print(f"   → {len(activities)} activité(s) récupérée(s)")
    print()

    # 3. Détails activités + DEBUG
    print("3️⃣  DÉTAILS ACTIVITÉS (avec debug) :")

    if not activities:
        print("   ⚠️  Aucune activité récupérée")
    else:
        for i, act in enumerate(activities[:10], 1):  # Max 10
            activity_id = act.get("id")
            name = act.get("name", "Sans nom")
            start = act.get("start_date_local", "N/A")

            # 🔍 NOUVEAU : Détail du check
            is_analyzed = state.is_activity_analyzed(activity_id)

            print(f"   {i}. {name[:50]}")
            print(f"      ID      : {activity_id}")
            print(f"      Start   : {start}")
            print(f"      Analysé : {'✅ OUI' if is_analyzed else '❌ NON'}")

            # 🔍 NOUVEAU : Vérifier pourquoi c'est analysé
            if is_analyzed:
                # Chercher dans l'historique
                for entry in history:
                    if entry.get("activity_id") == activity_id:
                        print(f"      → Trouvé dans history: {entry.get('date')}")
                        break

            print()

    # 4. Filtrage non analysées
    print("4️⃣  APPEL get_unanalyzed_activities() :")

    # 🔍 NOUVEAU : Debug avant l'appel
    print(f"   Input : {len(activities)} activités")

    unanalyzed = state.get_unanalyzed_activities(activities)

    # 🔍 NOUVEAU : Debug après l'appel
    print(f"   Output : {len(unanalyzed)} activités")
    print()

    print("5️⃣  ACTIVITÉS NON ANALYSÉES :")
    print(f"   Total : {len(unanalyzed)}")

    if unanalyzed:
        for act in unanalyzed:
            print(f"   - {act.get('name')} ({act.get('start_date_local')})")
    else:
        print("   ✅ Toutes les activités ont été analysées")

    print("\n═══════════════════════════════════════════")


if __name__ == "__main__":
    main()  # pragma: no cover
