#!/usr/bin/env python3
"""
organize_weekly_report.py - Organise les fichiers du bilan hebdomadaire

Ce script :
1. Lit les 6 fichiers depuis le presse-papier OU depuis des fichiers
2. Valide la présence des 6 fichiers obligatoires
3. Crée le répertoire bilans_hebdo/sXXX/
4. Sauvegarde chaque fichier au bon endroit
5. Affiche git diff pour vérification

Usage:
    # Depuis presse-papier (fichiers séparés par ---)
    python3 cyclisme_training_logs/organize_weekly_report.py --week 067

    # Depuis répertoire temporaire
    python3 cyclisme_training_logs/organize_weekly_report.py --week 067 --from-dir /tmp/bilans_s067

    # Mode dry-run (test sans écriture)
    python3 cyclisme_training_logs/organize_weekly_report.py --week 067 --dry-run.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


class WeeklyReportOrganizer:
    """Organisateur des fichiers de bilan hebdomadaire."""

    REQUIRED_FILES = [
        "workout_history_s{week}.md",
        "metrics_evolution_s{week}.md",
        "training_learnings_s{week}.md",
        "protocol_adaptations_s{week}.md",
        "transition_s{week}_s{next_week}.md",
        "bilan_final_s{week}.md",
    ]

    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        self.bilans_dir = self.project_root / "logs" / "weekly_reports"

    def read_clipboard(self):
        """Lire le presse-papier."""
        try:
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, check=True)
            return result.stdout
        except Exception as e:
            print(f"❌ Erreur lecture presse-papier : {e}")
            return None

    def parse_files_from_text(self, text):
        """Parser les fichiers depuis le texte (séparés par ---)."""
        files = {}

        # Stratégie 1 : Chercher les blocs avec # nom_fichier
        pattern = r"#\s+([\w_]+\.md)\s*\n(.*?)(?=\n#\s+\w+\.md|\Z)"
        matches = re.findall(pattern, text, re.DOTALL)

        if matches:
            for filename, content in matches:
                files[filename] = content.strip()
            return files

        # Stratégie 2 : Séparer par "---" ou "___"
        sections = re.split(r"\n---+\n|\n___+\n", text)

        for section in sections:
            section = section.strip()
            if not section:
                continue

            # Chercher le nom du fichier dans les premières lignes
            lines = section.split("\n")
            for i, line in enumerate(lines[:5]):
                # Pattern : # Titre ou **Fichier** : nom.md
                filename_match = re.search(
                    r"(workout_history|metrics_evolution|training_learnings|protocol_adaptations|transition|bilan_final)_s\d+.*?\.md",
                    line,
                    re.IGNORECASE,
                )
                if filename_match:
                    filename = filename_match.group(0)
                    # Prendre tout le contenu après la ligne du nom
                    content = "\n".join(lines[i + 1 :]).strip()
                    files[filename] = content
                    break

        return files if files else None

    def read_files_from_dir(self, directory):
        """Lire les fichiers depuis un répertoire."""
        files = {}
        dir_path = Path(directory)

        if not dir_path.exists():
            print(f"❌ Répertoire non trouvé : {directory}")
            return None

        for file_path in dir_path.glob("*.md"):
            with open(file_path, encoding="utf-8") as f:
                files[file_path.name] = f.read()

        return files if files else None

    def validate_files(self, files, week_number):
        """Valider la présence des 6 fichiers obligatoires."""
        week_str = f"{week_number:03d}"
        next_week_str = f"{week_number+1:03d}"

        expected = [
            f"workout_history_S{week_str}.md",
            f"metrics_evolution_S{week_str}.md",
            f"training_learnings_S{week_str}.md",
            f"protocol_adaptations_S{week_str}.md",
            f"transition_S{week_str}_S{next_week_str}.md",
            f"bilan_final_S{week_str}.md",
        ]

        found = []
        missing = []

        for expected_file in expected:
            # Chercher avec ou sans la semaine dans le nom
            found_match = False
            for filename in files.keys():
                if (
                    expected_file.lower() in filename.lower()
                    or filename.lower() in expected_file.lower()
                ):
                    found.append(expected_file)
                    found_match = True
                    break

            if not found_match:
                missing.append(expected_file)

        return found, missing

    def save_files(self, files, week_number, dry_run=False):
        """Sauvegarder les fichiers dans bilans_hebdo/SXXX/."""
        week_str = f"S{week_number:03d}"  # ✅ MAJUSCULE (convention SXXX)
        week_dir = self.bilans_dir / week_str

        if dry_run:
            print("🧪 Mode DRY-RUN : Aucun fichier ne sera écrit")
            print(f"   Répertoire cible : {week_dir}")
            print()
            return True

        # Créer le répertoire
        week_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Répertoire créé : {week_dir}")
        print()

        # Sauvegarder chaque fichier
        saved_count = 0
        for filename, content in files.items():
            file_path = week_dir / filename

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            print(f"   ✅ {filename} ({len(content)} caractères)")
            saved_count += 1

        print()
        print(f"✅ {saved_count} fichier(s) sauvegardé(s)")
        return True

    def show_git_diff(self, week_number):
        """Afficher le git diff"""
        week_str = f"s{week_number:03d}"
        week_dir = self.bilans_dir / week_str

        try:
            result = subprocess.run(
                ["git", "diff", "--stat", str(week_dir)],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            if result.stdout:
                print("\n" + "=" * 60)
                print("GIT DIFF STATS")
                print("=" * 60)
                print(result.stdout)

            return True
        except Exception as e:
            print(f"⚠️  Impossible d'afficher git diff : {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Organiser les fichiers du bilan hebdomadaire")

    parser.add_argument(
        "--week", type=int, required=True, help="Numéro de semaine (ex: 67 pour S067)"
    )
    parser.add_argument("--from-dir", help="Lire depuis un répertoire au lieu du presse-papier")
    parser.add_argument("--dry-run", action="store_true", help="Mode test : afficher sans écrire")
    parser.add_argument(
        "--project-root", default=".", help="Racine du projet (défaut: répertoire courant)"
    )

    args = parser.parse_args()

    week_number = args.week

    print(f"📦 Organisation bilan hebdomadaire S{week_number:03d}")
    print("=" * 60)
    print()

    organizer = WeeklyReportOrganizer(args.project_root)

    # Lire les fichiers
    if args.from_dir:
        print(f"📂 Lecture depuis {args.from_dir}...")
        files = organizer.read_files_from_dir(args.from_dir)
    else:
        print("📋 Lecture du presse-papier...")
        text = organizer.read_clipboard()
        if not text:
            print("❌ Presse-papier vide")
            sys.exit(1)

        print("🔍 Parsing des fichiers...")
        files = organizer.parse_files_from_text(text)

    if not files:
        print("❌ Aucun fichier détecté")
        print()
        print("💡 Assurez-vous que :")
        print("   - Les fichiers sont séparés par '---'")
        print("   - Chaque fichier commence par # nom_fichier.md")
        print("   - Ou utilisez --from-dir pour lire depuis un répertoire")
        sys.exit(1)

    print(f"   ✅ {len(files)} fichier(s) détecté(s)")
    print()

    # Afficher les fichiers trouvés
    print("📄 Fichiers détectés :")
    for filename in files.keys():
        size = len(files[filename])
        print(f"   - {filename} ({size} caractères)")
    print()

    # Valider
    print("✓  Validation des fichiers obligatoires...")
    found, missing = organizer.validate_files(files, week_number)

    if found:
        print(f"   ✅ {len(found)} fichier(s) validé(s)")

    if missing:
        print(f"   ⚠️  {len(missing)} fichier(s) manquant(s) :")
        for m in missing:
            print(f"      - {m}")
        print()

        response = input("   Continuer malgré les fichiers manquants ? (y/N) : ")
        if response.lower() != "y":
            print("❌ Organisation annulée")
            sys.exit(1)

    print()

    # Confirmer sauvegarde
    if not args.dry_run:
        response = input(f"💾 Sauvegarder dans bilans_hebdo/s{week_number:03d}/ ? (Y/n) : ")
        if response.lower() == "n":
            print("❌ Organisation annulée")
            sys.exit(0)

    print()

    # Sauvegarder
    organizer.save_files(files, week_number, dry_run=args.dry_run)

    if not args.dry_run:
        # Afficher git diff
        organizer.show_git_diff(week_number)

        print()
        print("=" * 60)
        print(f"✅ BILAN S{week_number:03d} ORGANISÉ")
        print("=" * 60)
        print()
        print("📝 ÉTAPES SUIVANTES :")
        print()
        print("1. Vérifier les fichiers :")
        print(f"   ls bilans_hebdo/s{week_number:03d}/")
        print()
        print("2. Vérifier le contenu :")
        print(f"   git diff bilans_hebdo/s{week_number:03d}/")
        print()
        print("3. Ajouter au commit :")
        print(f"   git add bilans_hebdo/s{week_number:03d}/")
        print()
        print("4. Commit :")
        print(f'   git commit -m "Bilan: Semaine S{week_number:03d}"')
        print()
        print("5. Push (optionnel) :")
        print("   git push")
        print()
        print("=" * 60)


if __name__ == "__main__":
    main()
