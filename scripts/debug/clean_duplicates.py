#!/usr/bin/env python3
"""
Script de nettoyage des doublons dans workouts-history.md

Supprime les entrées dupliquées en gardant seulement les premières occurrences.
Supporte plusieurs emplacements de fichier.
"""

import re
import sys
from datetime import datetime
from pathlib import Path


def find_workout_entries(content: str) -> list[dict]:
    """Trouve toutes les entrées de séances avec leurs positions."""
    entries = []

    # Regex pour détecter le début d'une séance
    pattern = r"^### (S\d{3}-\d{2}(?:-\w+)*(?:-V\d{3})?)\s*$"

    lines = content.split("\n")
    current_entry = None
    current_lines = []

    for i, line in enumerate(lines):
        match = re.match(pattern, line)

        if match:
            # Sauver l'entrée précédente si elle existe
            if current_entry:
                entries.append(
                    {
                        "id": current_entry,
                        "start_line": start_line,
                        "end_line": i - 1,
                        "lines": current_lines,
                    }
                )

            # Nouvelle entrée
            current_entry = match.group(1)
            start_line = i
            current_lines = [line]
        elif current_entry:
            current_lines.append(line)

    # Sauver la dernière entrée
    if current_entry:
        entries.append(
            {
                "id": current_entry,
                "start_line": start_line,
                "end_line": len(lines) - 1,
                "lines": current_lines,
            }
        )

    return entries


def analyze_duplicates(entries: list[dict]) -> dict:
    """Analyse les doublons."""
    seen = {}
    duplicates = []

    for entry in entries:
        entry_id = entry["id"]
        if entry_id in seen:
            duplicates.append({"id": entry_id, "first": seen[entry_id], "duplicate": entry})
        else:
            seen[entry_id] = entry

    return {"unique": seen, "duplicates": duplicates}


def find_workouts_history_files() -> list[Path]:
    """Trouve tous les fichiers workouts-history.md possibles."""
    candidates = [
        Path("~/training-logs/workouts-history.md"),
        Path("~/cyclisme-training-logs/logs/workouts-history.md"),
    ]

    existing = []
    for path in candidates:
        expanded = path.expanduser()
        if expanded.exists():
            existing.append(expanded)

    return existing


def select_file(files: list[Path]) -> Path:
    """Permet à l'utilisateur de choisir un fichier."""
    if not files:
        print("❌ Aucun fichier workouts-history.md trouvé!")
        print("\nEmplacements recherchés:")
        print("  - ~/training-logs/workouts-history.md")
        print("  - ~/cyclisme-training-logs/logs/workouts-history.md")
        sys.exit(1)

    if len(files) == 1:
        print(f"📁 Fichier trouvé: {files[0]}")
        return files[0]

    print(f"\n📁 {len(files)} fichiers trouvés:\n")
    for i, file_path in enumerate(files, 1):
        size = file_path.stat().st_size / 1024  # KB
        print(f"  {i}. {file_path}")
        print(f"     Taille: {size:.1f} KB")

    while True:
        try:
            choice = (
                input(f"\n❓ Choisir le fichier à nettoyer (1-{len(files)}) ou 'all' pour tous: ")
                .strip()
                .lower()
            )

            if choice == "all":
                return "all"

            choice_num = int(choice)
            if 1 <= choice_num <= len(files):
                return files[choice_num - 1]
            else:
                print(f"⚠️  Entrer un nombre entre 1 et {len(files)}")
        except ValueError:
            print("⚠️  Entrer un nombre valide ou 'all'")


def clean_file(file_path: Path, auto_confirm: bool = False) -> bool:
    """Nettoie un fichier de ses doublons."""
    print(f"\n{'='*70}")
    print(f"📁 Traitement: {file_path}")
    print(f"{'='*70}\n")

    print("📖 Lecture du fichier...")
    content = file_path.read_text(encoding="utf-8")

    print("🔍 Analyse des entrées...")
    entries = find_workout_entries(content)

    print(f"📊 Trouvé {len(entries)} entrées au total")

    # Analyser les doublons
    analysis = analyze_duplicates(entries)
    duplicates = analysis["duplicates"]

    if not duplicates:
        print("✅ Aucun doublon trouvé!")
        return True

    print(f"\n⚠️  {len(duplicates)} doublon(s) détecté(s):")
    for dup in duplicates:
        print(f"\n  {dup['id']}:")
        print(
            f"    Première occurrence: lignes {dup['first']['start_line']+1}-{dup['first']['end_line']+1}"
        )
        print(
            f"    Doublon à supprimer: lignes {dup['duplicate']['start_line']+1}-{dup['duplicate']['end_line']+1}"
        )

    # Confirmation
    print("\n🔧 Action proposée:")
    print(f"   - Garder les {len(analysis['unique'])} premières occurrences")
    print(f"   - Supprimer {len(duplicates)} doublons")

    if not auto_confirm:
        response = input("\n❓ Procéder au nettoyage? (y/N): ").strip().lower()
        if response != "y":
            print("❌ Annulé")
            return False
    else:
        print("\n✅ Auto-confirmation (mode 'all')")

    # Créer backup
    backup_path = (
        file_path.parent / f"workouts-history.BACKUP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    )
    print(f"\n💾 Création backup: {backup_path.name}")
    backup_path.write_text(content, encoding="utf-8")

    # Supprimer les doublons
    print("🧹 Suppression des doublons...")
    lines = content.split("\n")

    # Marquer les lignes à supprimer
    lines_to_remove = set()
    for dup in duplicates:
        for line_num in range(dup["duplicate"]["start_line"], dup["duplicate"]["end_line"] + 1):
            lines_to_remove.add(line_num)

    # Construire nouveau contenu
    cleaned_lines = [line for i, line in enumerate(lines) if i not in lines_to_remove]
    cleaned_content = "\n".join(cleaned_lines)

    # Écrire le fichier nettoyé
    print("💾 Écriture du fichier nettoyé...")
    file_path.write_text(cleaned_content, encoding="utf-8")

    print("\n✅ Nettoyage terminé!")
    print(f"   Backup: {backup_path}")
    print(f"   Lignes supprimées: {len(lines_to_remove)}")
    print(f"   Doublons supprimés: {len(duplicates)}")

    return True


def main():
    print("🔍 Recherche des fichiers workouts-history.md...\n")

    files = find_workouts_history_files()
    selected = select_file(files)

    if selected == "all":
        print(f"\n🔄 Nettoyage de {len(files)} fichiers...\n")
        success_count = 0
        for file_path in files:
            if clean_file(file_path, auto_confirm=True):
                success_count += 1

        print(f"\n{'='*70}")
        print(f"✅ Terminé: {success_count}/{len(files)} fichiers nettoyés")
        print(f"{'='*70}")
    else:
        clean_file(selected)

    return 0


if __name__ == "__main__":
    exit(main())
