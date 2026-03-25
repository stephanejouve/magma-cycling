#!/usr/bin/env python3
"""
Insertion de l'analyse IA dans workouts-history.md.

Insère l'analyse générée par IA dans le fichier workouts-history.md en
respectant l'ordre chronologique via TimelineInjector. Remplace le système
append-only par une injection intelligente basée sur les dates de workout.

Examples:
    CLI usage::

        # Insertion depuis presse-papier (workflow manuel)
        poetry run insert-analysis

        # Test sans modification
        poetry run insert-analysis --dry-run

        # Insertion depuis fichier
        poetry run insert-analysis --file analysis.md

        # Mode auto (pour backfill)
        poetry run insert-analysis --yes

    Programmatic usage with TimelineInjector::

        from magma_cycling.core.timeline_injector import TimelineInjector
        from magma_cycling.config import get_data_config

        # Initialisation injector avec config.py (recommandé)
        config = get_data_config()
        injector = TimelineInjector(
            history_file=config.workouts_history_path
        )

        # Injection chronologique
        result = injector.inject_chronologically(
            workout_entry=analysis_text,
            workout_date=date(2024, 8, 15)
        )

        if result.success:
            print(f"Injected at line {result.line_number}")
        else:
            print(f"Error: {result.error}")

Author: Claude Code
Created: 2024-11-15
Updated: 2025-12-26 (Migrated to TimelineInjector - chronological injection)

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
from pathlib import Path

from magma_cycling.config import get_data_config
from magma_cycling.inserter.clipboard import ClipboardReader
from magma_cycling.inserter.history import WorkoutHistoryManager
from magma_cycling.inserter.parser import AnalysisParser
from magma_cycling.utils.cli import cli_main

# Re-export pour backward compatibility
__all__ = [
    "AnalysisParser",
    "ClipboardReader",
    "WorkoutHistoryManager",
    "get_data_config",
    "main",
]


@cli_main
def main():
    """Command-line entry point for inserting analysis into weekly reports."""
    parser = argparse.ArgumentParser(
        description="Insérer l'analyse Claude.ai dans workouts-history.md"
    )

    parser.add_argument("--dry-run", action="store_true", help="Mode test : affiche sans modifier")
    parser.add_argument("--file", help="Lire depuis un fichier au lieu du presse-papier")
    parser.add_argument(
        "--logs-dir", default=None, help="Répertoire des logs (défaut: utilise config.py)"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirmer automatiquement l'insertion (mode non-interactif)",
    )

    args = parser.parse_args()

    print("📋 Insertion de l'analyse dans workouts-history.md")
    print()

    # Lire l'analyse
    if args.file:
        print(f"📂 Lecture depuis {args.file}...")
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ Fichier non trouvé : {args.file}")
            sys.exit(1)
        with open(file_path, encoding="utf-8") as f:
            raw_text = f.read()
    else:
        print("📋 Lecture du presse-papier...")
        raw_text = ClipboardReader.read_clipboard()
        if not raw_text:
            print("❌ Presse-papier vide")
            sys.exit(1)

    print("   ✅ Contenu récupéré")
    print()

    # Parser l'analyse
    print("🔍 Extraction du bloc markdown...")
    analysis = AnalysisParser.extract_markdown_block(raw_text)

    if not analysis:
        print("❌ Impossible d'extraire l'analyse")
        sys.exit(1)

    print("   ✅ Bloc extrait")
    print()

    # Valider
    print("✓  Validation de l'analyse...")
    num_sessions = AnalysisParser.count_sessions(analysis)

    if not AnalysisParser.validate_analysis(analysis):
        print()
        response = input("   Continuer malgré les avertissements ? (y/N) : ")
        if response.lower() != "y":
            print("❌ Insertion annulée")
            sys.exit(1)
    else:
        print("   ✅ Format valide")

    # Message si mode batch
    if num_sessions > 1:
        print(f"   🔄 Mode BATCH : {num_sessions} sessions seront insérées ensemble")
    print()

    # Afficher un aperçu
    lines = analysis.split("\n")
    preview_lines = lines[:10] if len(lines) > 10 else lines
    print("📄 Aperçu de l'analyse :")
    print("-" * 60)
    for line in preview_lines:
        print(line)
    if len(lines) > 10:
        print(f"... ({len(lines) - 10} lignes supplémentaires)")
    print("-" * 60)
    print()

    if args.dry_run:
        print("🧪 Mode DRY-RUN : Aucune modification effectuée")
        print("   L'analyse est valide et prête à être insérée")
        sys.exit(0)

    # Confirmer
    if args.yes:
        print("✓ Insertion automatique activée (--yes)")
        response = "y"
    else:
        response = input("Insérer cette analyse ? (Y/n) : ")
        if response.lower() == "n":
            print("❌ Insertion annulée")
            sys.exit(0)

    print()

    # Insérer
    print("✍️  Insertion dans workouts-history.md...")
    manager = WorkoutHistoryManager(args.logs_dir, yes_confirm=args.yes)

    if manager.insert_analysis(analysis):
        print("   ✅ Analyse insérée avec succès !")
        print()

        # Afficher le diff
        print("📊 Vérification des modifications...")
        manager.show_diff()

        print()
        print("=" * 60)
        print("✅ INSERTION TERMINÉE")
        print("=" * 60)
        print()
        print("📝 ÉTAPES SUIVANTES :")
        print()
        print("1. Vérifier les modifications :")
        print(f"   git diff {args.logs_dir}/workouts-history.md")
        print()
        print("2. Ajouter au commit :")
        print(f"   git add {args.logs_dir}/workouts-history.md")
        print()
        print("3. Commit :")
        date = AnalysisParser.extract_date_from_analysis(analysis)
        print(f'   git commit -m "Analyse: Séance du {date}"')
        print()
        print("4. Push (optionnel) :")
        print("   git push")
        print()
        print("=" * 60)

    else:
        print("❌ Échec de l'insertion")
        sys.exit(1)


if __name__ == "__main__":
    main()
