#!/usr/bin/env python3
"""
demo_rest_handling.py - Démonstration de la gestion repos/annulations

Ce script démontre l'utilisation du module rest_and_cancellations
avec l'exemple de la semaine S070.

Usage:
    python3 scripts/demo_rest_handling.py
"""

import json
from pathlib import Path
from rest_and_cancellations import (
    load_week_planning,
    validate_week_planning,
    generate_rest_day_entry,
    generate_cancelled_session_entry,
    reconcile_planned_vs_actual,
)


def print_separator(title=""):
    """Affiche un séparateur stylisé"""
    if title:
        print(f"\n{'=' * 70}")
        print(f"  {title}")
        print(f"{'=' * 70}\n")
    else:
        print(f"\n{'-' * 70}\n")


def demo_load_and_validate():
    """Démo 1 : Chargement et validation du planning"""
    print_separator("DÉMO 1 : Chargement et Validation du Planning S070")

    # Charger le planning
    planning = load_week_planning("S070")

    print(f"✓ Planning chargé : {planning['week_id']}")
    print(f"  Période : {planning['start_date']} → {planning['end_date']}")
    print(f"  Sessions planifiées : {len(planning['planned_sessions'])}")
    print(f"  TSS cible : {planning['tss_target']}")

    # Afficher détails sessions
    print("\n📋 Sessions planifiées :")
    for i, session in enumerate(planning['planned_sessions'], 1):
        date = session['date']
        sid = session['session_id']
        name = session['name']
        status = session['status']
        tss = session.get('tss_planned', 0)

        status_icon = {
            'completed': '✅',
            'cancelled': '❌',
            'rest_day': '💤',
            'replaced': '🔄'
        }.get(status, '❓')

        print(f"  {i}. {status_icon} [{date}] {sid} - {name} (TSS {tss}) - {status}")

    # Validation
    print("\n🔍 Validation du planning...")
    is_valid = validate_week_planning(planning)
    print(f"  Résultat : {'✓ Valide' if is_valid else '✗ Invalide'}")

    return planning


def demo_generate_rest_day(planning):
    """Démo 2 : Génération markdown repos planifié"""
    print_separator("DÉMO 2 : Génération Markdown Repos Planifié (S070-07)")

    # Trouver la session repos
    rest_session = next(
        (s for s in planning['planned_sessions'] if s['status'] == 'rest_day'),
        None
    )

    if not rest_session:
        print("⚠️  Aucune session repos trouvée dans le planning")
        return

    print(f"Session : {rest_session['session_id']} - {rest_session['name']}")
    print(f"Date : {rest_session['date']}")
    print(f"Raison : {rest_session.get('rest_reason', 'N/A')}")

    # Métriques (simulation)
    metrics_pre = {"ctl": 50, "atl": 35, "tsb": 15}
    metrics_post = {"ctl": 50, "atl": 35, "tsb": 15}
    feedback = {
        "sleep_duration": "6h12min",
        "sleep_score": 78,
        "hrv": 66,
        "resting_hr": 44
    }

    # Générer markdown
    markdown = generate_rest_day_entry(
        rest_session,
        metrics_pre,
        metrics_post,
        feedback
    )

    print("\n📝 Markdown généré :")
    print_separator()
    # Afficher un extrait
    lines = markdown.split('\n')
    for line in lines[:30]:  # Afficher les 30 premières lignes
        print(line)
    print("...")
    print(f"\n✓ Markdown complet : {len(markdown)} caractères, {len(lines)} lignes")


def demo_generate_cancelled(planning):
    """Démo 3 : Génération markdown séance annulée"""
    print_separator("DÉMO 3 : Génération Markdown Séance Annulée (S070-04)")

    # Trouver la session annulée
    cancelled_session = next(
        (s for s in planning['planned_sessions'] if s['status'] == 'cancelled'),
        None
    )

    if not cancelled_session:
        print("⚠️  Aucune session annulée trouvée dans le planning")
        return

    print(f"Session : {cancelled_session['session_id']} - {cancelled_session['name']}")
    print(f"Date : {cancelled_session['date']}")
    print(f"Raison : {cancelled_session.get('cancellation_reason', 'N/A')}")

    # Métriques (simulation)
    metrics_pre = {
        "ctl": 51,
        "atl": 33,
        "tsb": 17,
        "sleep_duration": "7h29min",
        "sleep_score": 65
    }

    # Générer markdown
    markdown = generate_cancelled_session_entry(
        cancelled_session,
        metrics_pre,
        cancelled_session['cancellation_reason']
    )

    print("\n📝 Markdown généré :")
    print_separator()
    # Afficher un extrait
    lines = markdown.split('\n')
    for line in lines[:25]:  # Afficher les 25 premières lignes
        print(line)
    print("...")
    print(f"\n✓ Markdown complet : {len(markdown)} caractères, {len(lines)} lignes")


def demo_reconciliation(planning):
    """Démo 4 : Réconciliation planning vs activités"""
    print_separator("DÉMO 4 : Réconciliation Planning vs Activités")

    # Créer des activités fictives pour la démo
    fake_activities = [
        {
            "id": "i107424849",
            "start_date_local": "2025-12-02T08:00:00",
            "name": "S070-01 EnduranceBase"
        },
        {
            "id": "i107424850",
            "start_date_local": "2025-12-03T10:00:00",
            "name": "S070-02 TechniqueCadence"
        },
        {
            "id": "i107424851",
            "start_date_local": "2025-12-04T09:00:00",
            "name": "S070-03 RecuperationActive"
        },
        # S070-04 annulée → pas d'activité
        {
            "id": "i107424852",
            "start_date_local": "2025-12-06T08:30:00",
            "name": "S070-05 SweetSpotIntro"
        },
        {
            "id": "i107424853",
            "start_date_local": "2025-12-07T10:00:00",
            "name": "S070-06 EnduranceVolume"
        },
        # S070-07 repos planifié → pas d'activité
    ]

    print(f"📊 Activités Intervals.icu : {len(fake_activities)}")
    for act in fake_activities:
        date = act['start_date_local'][:10]
        print(f"  • [{date}] {act['name']}")

    print("\n🔄 Réconciliation en cours...")
    result = reconcile_planned_vs_actual(planning, fake_activities)

    print("\n📈 RÉSULTATS :")
    print(f"  ✅ Matched (planifiées + exécutées) : {len(result['matched'])}")
    print(f"  ❌ Cancelled (annulées) : {len(result['cancelled'])}")
    print(f"  💤 Rest days (repos planifiés) : {len(result['rest_days'])}")
    print(f"  ❓ Unplanned (non planifiées) : {len(result['unplanned'])}")

    # Détails matched
    if result['matched']:
        print("\n  Sessions exécutées :")
        for match in result['matched']:
            session = match['session']
            activity = match['activity']
            print(f"    • {session['session_id']} ← {activity['name']}")

    # Détails cancelled
    if result['cancelled']:
        print("\n  Sessions annulées :")
        for session in result['cancelled']:
            reason = session.get('cancellation_reason', 'Raison non spécifiée')
            print(f"    • {session['session_id']} : {reason[:60]}...")

    # Détails rest days
    if result['rest_days']:
        print("\n  Repos planifiés :")
        for session in result['rest_days']:
            reason = session.get('rest_reason', 'Repos planifié')
            print(f"    • {session['session_id']} : {reason[:60]}...")


def demo_export_markdown():
    """Démo 5 : Export complet markdown"""
    print_separator("DÉMO 5 : Export Complet Markdown")

    output_file = Path("data/week_planning/demo_output_S070.md")

    print(f"📝 Génération fichier markdown complet...")
    print(f"   Fichier : {output_file}")

    # Charger planning
    planning = load_week_planning("S070")

    # Générer toutes les entrées
    entries = []

    for session in planning['planned_sessions']:
        status = session['status']

        # Métriques par défaut
        metrics_pre = {"ctl": 50, "atl": 35, "tsb": 15}
        metrics_post = {"ctl": 50, "atl": 35, "tsb": 15}

        if status == 'rest_day':
            markdown = generate_rest_day_entry(
                session,
                metrics_pre,
                metrics_post,
                {"sleep_duration": "7h00", "sleep_score": 75, "hrv": 65, "resting_hr": 45}
            )
            entries.append(markdown)

        elif status == 'cancelled':
            markdown = generate_cancelled_session_entry(
                session,
                metrics_pre,
                session['cancellation_reason']
            )
            entries.append(markdown)

    # Écrire dans le fichier
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# Semaine {planning['week_id']} - Repos et Annulations\n\n")
        f.write(f"Période : {planning['start_date']} → {planning['end_date']}\n\n")
        f.write("---\n\n")
        for entry in entries:
            f.write(entry)
            f.write("\n")

    print(f"\n✓ Fichier généré : {output_file}")
    print(f"  Entrées : {len(entries)}")
    print(f"  Taille : {output_file.stat().st_size} octets")


def main():
    """Exécute toutes les démos"""
    print("\n" + "=" * 70)
    print("  DÉMONSTRATION GESTION REPOS ET ANNULATIONS")
    print("  Module : rest_and_cancellations.py")
    print("  Exemple : Semaine S070")
    print("=" * 70)

    try:
        # Démo 1 : Chargement
        planning = demo_load_and_validate()

        # Démo 2 : Repos
        demo_generate_rest_day(planning)

        # Démo 3 : Annulation
        demo_generate_cancelled(planning)

        # Démo 4 : Réconciliation
        demo_reconciliation(planning)

        # Démo 5 : Export
        demo_export_markdown()

        # Résumé final
        print_separator("DÉMONSTRATION TERMINÉE")
        print("✅ Toutes les fonctionnalités ont été testées avec succès")
        print("\n📚 Prochaines étapes :")
        print("  1. Intégrer dans workflow_coach.py")
        print("  2. Ajouter support API réelle Intervals.icu")
        print("  3. Tester avec données réelles")
        print("\n💡 Fichiers générés :")
        print("  • data/week_planning/demo_output_S070.md")
        print("\n" + "=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Erreur durant la démonstration : {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
