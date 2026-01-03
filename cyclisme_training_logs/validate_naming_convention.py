#!/usr/bin/env python3
"""
validate_naming_convention.py - Validation stricte conventions nommage weekly_reports

Ce script valide :
1. Répertoires : format SXXX (S majuscule + 3 chiffres)
2. Fichiers : format nom_SXXX.md (S majuscule dans numéro semaine)
3. Détection minuscules (sXXX)
4. Détection formats invalides

Usage:
    # Validation complète
    python3 cyclisme_training_logs/validate_naming_convention.py

    # Mode verbeux (affiche tous les fichiers)
    python3 cyclisme_training_logs/validate_naming_convention.py --verbose

    # JSON output (pour intégration CI)
    python3 cyclisme_training_logs/validate_naming_convention.py --json

Exit codes:
    0 : Tous conforme
    1 : Problèmes détectés
    2 : Erreur exécution.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, cast


class NamingValidator:
    """Validateur de conventions de nommage weekly_reports."""

    # Convention stricte : SXXX (S majuscule + 3 chiffres)
    DIR_PATTERN = re.compile(r"^S\d{3}$")
    FILE_PATTERN = re.compile(r"^[a-z_]+_S\d{3}(?:_S\d{3})?\.md$")

    # Patterns invalides à détecter
    LOWERCASE_DIR = re.compile(r"^s\d{3}$")
    LOWERCASE_FILE = re.compile(r"_s\d{3}")

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.weekly_dir = self.project_root / "logs" / "weekly_reports"
        self.issues: list[dict[str, Any]] = []

    def validate_directory_name(self, dir_name: str) -> dict[str, Any]:
        """Valider nom de répertoire."""
        result: dict[str, Any] = {
            "type": "directory",
            "name": dir_name,
            "valid": True,
            "issues": [],
        }
        issues = cast(list[str], result["issues"])

        # Vérifier minuscule
        if self.LOWERCASE_DIR.match(dir_name):
            result["valid"] = False
            issues.append(f"Minuscule détecté : {dir_name} → devrait être {dir_name.upper()}")

        # Vérifier format
        elif not self.DIR_PATTERN.match(dir_name):
            result["valid"] = False
            issues.append(f"Format invalide : {dir_name} (attendu: SXXX)")

        return result

    def validate_file_name(self, file_name: str, parent_dir: str) -> dict[str, Any]:
        """Valider nom de fichier."""
        result: dict[str, Any] = {
            "type": "file",
            "name": file_name,
            "parent": parent_dir,
            "valid": True,
            "issues": [],
        }
        issues = cast(list[str], result["issues"])

        # Vérifier minuscule dans numéro semaine
        if self.LOWERCASE_FILE.search(file_name):
            # Proposer correction
            corrected = re.sub(r"_s(\d{3})", r"_S\1", file_name)
            result["valid"] = False
            issues.append(f"Minuscule détecté : {file_name} → devrait être {corrected}")

        # Vérifier format global
        elif not self.FILE_PATTERN.match(file_name):
            result["valid"] = False
            issues.append(f"Format invalide : {file_name} (attendu: nom_SXXX.md)")

        return result

    def validate_structure(self) -> bool:
        """Valider toute la structure."""
        if not self.weekly_dir.exists():
            print(f"❌ Répertoire non trouvé : {self.weekly_dir}")
            return False

        all_valid = True

        # Valider tous les répertoires
        for item in sorted(self.weekly_dir.iterdir()):
            if not item.is_dir():
                continue

            # Valider nom répertoire
            dir_result = self.validate_directory_name(item.name)
            if not dir_result["valid"]:
                all_valid = False
                self.issues.append(dir_result)

            # Valider fichiers dans répertoire
            for file_path in sorted(item.glob("*.md")):
                file_result = self.validate_file_name(file_path.name, item.name)
                if not file_result["valid"]:
                    all_valid = False
                    self.issues.append(file_result)

        return all_valid

    def print_report(self, verbose: bool = False):
        """Afficher rapport de validation."""
        print("\n" + "=" * 70)
        print("🔍 VALIDATION CONVENTIONS NOMMAGE WEEKLY REPORTS")
        print("=" * 70)
        print()

        if not self.weekly_dir.exists():
            print(f"❌ Répertoire non trouvé : {self.weekly_dir}")
            return

        # Compter éléments
        dirs = [d for d in self.weekly_dir.iterdir() if d.is_dir()]
        files = list(self.weekly_dir.rglob("*.md"))

        print("📊 Éléments analysés :")
        print(f"   Répertoires : {len(dirs)}")
        print(f"   Fichiers .md : {len(files)}")
        print()

        # Afficher problèmes
        if not self.issues:
            print("✅ TOUS CONFORME")
            print()
            print("Convention respectée :")
            print("   • Répertoires : SXXX (S majuscule + 3 chiffres)")
            print("   • Fichiers : nom_SXXX.md (S majuscule dans numéro)")
            print()
        else:
            print(f"❌ {len(self.issues)} PROBLÈME(S) DÉTECTÉ(S)")
            print()

            # Grouper par type
            dir_issues = [i for i in self.issues if i["type"] == "directory"]
            file_issues = [i for i in self.issues if i["type"] == "file"]

            if dir_issues:
                print(f"📁 Répertoires ({len(dir_issues)}) :")
                for issue in dir_issues:
                    print(f"   ❌ {issue['name']}")
                    for msg in issue["issues"]:
                        print(f"      → {msg}")
                print()

            if file_issues:
                print(f"📄 Fichiers ({len(file_issues)}) :")
                for issue in file_issues:
                    print(f"   ❌ {issue['parent']}/{issue['name']}")
                    for msg in issue["issues"]:
                        print(f"      → {msg}")
                print()

        # Mode verbeux : lister tous les fichiers
        if verbose and not self.issues:
            print("📋 Détail structure conforme :")
            for directory in sorted(dirs):
                files_in_dir = sorted(directory.glob("*.md"))
                print(f"\n   {directory.name}/ ({len(files_in_dir)} fichiers)")
                for f in files_in_dir:
                    print(f"      ✅ {f.name}")

        print("=" * 70)

    def get_json_report(self) -> str:
        """Générer rapport JSON."""
        dirs = (
            [d.name for d in self.weekly_dir.iterdir() if d.is_dir()]
            if self.weekly_dir.exists()
            else []
        )
        files = (
            [str(f.relative_to(self.weekly_dir)) for f in self.weekly_dir.rglob("*.md")]
            if self.weekly_dir.exists()
            else []
        )

        report = {
            "valid": len(self.issues) == 0,
            "weekly_reports_path": str(self.weekly_dir),
            "stats": {"directories": len(dirs), "files": len(files), "issues": len(self.issues)},
            "issues": self.issues,
        }

        return json.dumps(report, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description="Valider conventions nommage weekly_reports (SXXX strict)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Mode verbeux : afficher tous les fichiers"
    )

    parser.add_argument("--json", action="store_true", help="Output JSON (pour CI/CD)")

    parser.add_argument(
        "--project-root", default=".", help="Racine du projet (défaut: répertoire courant)"
    )

    args = parser.parse_args()

    validator = NamingValidator(args.project_root)

    try:
        is_valid = validator.validate_structure()

        if args.json:
            print(validator.get_json_report())
        else:
            validator.print_report(verbose=args.verbose)

        # Exit code selon validation
        sys.exit(0 if is_valid else 1)

    except Exception as e:
        print(f"❌ Erreur validation : {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
