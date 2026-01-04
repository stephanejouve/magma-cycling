#!/usr/bin/env python3
"""
normalize_weekly_reports_casing.py - Normaliser la casse des répertoires de semaine

Ce script :
1. Scanne logs/weekly_reports/
2. Détecte les incohérences de casse (s067 vs S067)
3. Renomme automatiquement en majuscules (standard: S067)
4. Crée un backup avant modification
5. Génère un rapport des changements

Usage:
    python3 cyclisme_training_logs/normalize_weekly_reports_casing.py [--dry-run] [--force].
"""
import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


class CasingNormalizer:
    """Normalisateur de casse pour répertoires weekly_reports."""

    def __init__(self, project_root, dry_run=False, force=False):
        """Initialize casing normalizer.

        Args:
            project_root: Project root directory path
            dry_run: If True, only simulate changes without applying
            force: If True, skip confirmation prompts
        """
        self.project_root = Path(project_root)
        self.weekly_reports_dir = self.project_root / "logs" / "weekly_reports"
        self.dry_run = dry_run
        self.force = force
        self.changes = []
        self.errors = []

    def scan_directories(self):
        """Scanner les répertoires de semaine et détecter incohérences."""
        if not self.weekly_reports_dir.exists():
            print(f"❌ Erreur: Répertoire introuvable: {self.weekly_reports_dir}")
            return []

        directories = []
        for item in self.weekly_reports_dir.iterdir():
            if item.is_dir() and item.name.startswith(("s0", "S0")):
                # Extraire le numéro de semaine
                week_num = item.name[1:]  # Enlever 's' ou 'S'
                expected_name = f"S{week_num}"

                needs_change = item.name != expected_name

                directories.append(
                    {
                        "path": item,
                        "current": item.name,
                        "expected": expected_name,
                        "needs_change": needs_change,
                    }
                )

        return sorted(directories, key=lambda x: x["current"])

    def create_backup(self):
        """Create un backup du répertoire weekly_reports."""
        if self.dry_run:
            print("🔍 Mode dry-run: backup simulé")
            return True

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"weekly_reports.backup.casing_{timestamp}"
        backup_path = self.weekly_reports_dir.parent / backup_name

        try:
            print(f"💾 Création backup: {backup_name}")
            shutil.copytree(self.weekly_reports_dir, backup_path)
            print(f"   ✅ Backup créé: {backup_path}")
            return True
        except Exception as e:
            print(f"   ❌ Erreur backup: {e}")
            return False

    def normalize_directory(self, dir_info):
        """Renommer un répertoire selon le standard."""
        current_path = dir_info["path"]
        new_name = dir_info["expected"]
        new_path = current_path.parent / new_name

        try:
            if self.dry_run:
                print(f"   🔍 Dry-run: {dir_info['current']} → {new_name}")
                self.changes.append(
                    {"from": dir_info["current"], "to": new_name, "status": "simulated"}
                )
                return True

            # Vérifier si cible existe déjà
            if new_path.exists() and not self.force:
                error_msg = f"Cible existe déjà: {new_name}"
                print(f"   ⚠️  {error_msg}")
                self.errors.append({"directory": dir_info["current"], "error": error_msg})
                return False

            # Renommer
            current_path.rename(new_path)
            print(f"   ✅ Renommé: {dir_info['current']} → {new_name}")

            self.changes.append({"from": dir_info["current"], "to": new_name, "status": "success"})
            return True

        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ Erreur: {error_msg}")
            self.errors.append({"directory": dir_info["current"], "error": error_msg})
            return False

    def print_summary(self, directories):
        """Display le résumé de l'analyse."""
        print("\n" + "=" * 70)
        print("📊 RÉSUMÉ ANALYSE")
        print("=" * 70)

        total = len(directories)
        needs_change = sum(1 for d in directories if d["needs_change"])
        correct = total - needs_change

        print(f"\n✅ Répertoires corrects : {correct}")
        print(f"⚠️  Répertoires à corriger : {needs_change}")
        print(f"📁 Total répertoires : {total}")

        if needs_change > 0:
            print("\n🔧 CORRECTIONS NÉCESSAIRES :")
            print("-" * 70)
            for d in directories:
                if d["needs_change"]:
                    print(f"   {d['current']:15s} → {d['expected']:15s}")

        print()

    def print_report(self):
        """Display le rapport final."""
        print("\n" + "=" * 70)
        print("📋 RAPPORT FINAL")
        print("=" * 70)

        if self.changes:
            print(f"\n✅ Modifications réussies : {len(self.changes)}")
            for change in self.changes:
                status_icon = "🔍" if change["status"] == "simulated" else "✅"
                print(f"   {status_icon} {change['from']} → {change['to']}")

        if self.errors:
            print(f"\n❌ Erreurs rencontrées : {len(self.errors)}")
            for error in self.errors:
                print(f"   ❌ {error['directory']}: {error['error']}")

        if not self.changes and not self.errors:
            print("\n✨ Aucune modification nécessaire")
            print("   Tous les répertoires sont déjà au bon format")

        print()

    # === HELPER METHODS FOR RUN (Refactored from C-15 complexity) ===

    def _display_header(self):
        """Display run mode header and settings."""
        print("\n" + "=" * 70)
        print("🔧 NORMALISATION CASSE - Weekly Reports")
        print("=" * 70)

        if self.dry_run:
            print("\n🔍 MODE DRY-RUN (simulation, pas de modifications)")

        if self.force:
            print("\n⚠️  MODE FORCE (écrasement si collision)")

        print()

    def _validate_and_get_directories(self) -> tuple[list[dict] | None, list[dict] | None]:
        """Scan directories and validate result.

        Returns:
            Tuple of (all_directories, to_change_directories) or (None, None) if scan failed.
        """
        print("🔍 Analyse des répertoires...")
        directories = self.scan_directories()

        if not directories:
            print("❌ Aucun répertoire de semaine trouvé")
            return None, None

        print(f"   ✅ {len(directories)} répertoire(s) trouvé(s)")

        # Display summary
        self.print_summary(directories)

        # Filter directories that need changes
        to_change = [d for d in directories if d["needs_change"]]

        if not to_change:
            print("✨ Tous les répertoires sont déjà normalisés")
            return directories, []

        return directories, to_change

    def _get_user_confirmation(self) -> bool:
        """Get user confirmation for normalization if needed.

        Returns:
            True if should proceed, False if cancelled.
        """
        if self.dry_run or self.force:
            return True

        print("⚠️  ATTENTION : Les répertoires vont être renommés")
        print("   Un backup sera créé automatiquement")
        print()
        response = input("Continuer ? (o/n) : ").strip().lower()

        if response not in ["o", "oui", "y", "yes"]:
            print("❌ Annulé par l'utilisateur")
            return False

        return True

    def _display_recommendations(self):
        """Display post-normalization recommendations."""
        if not self.changes or self.dry_run:
            return

        print("💡 PROCHAINES ÉTAPES :")
        print("   1. Vérifier que tout fonctionne correctement")
        print("   2. Tester vos scripts sur les nouveaux chemins")
        print("   3. Si OK, commit les changements:")
        print("      git add logs/weekly_reports/")
        print('      git commit -m "fix: Normalisation casse répertoires weekly_reports"')
        print("      git push")
        print()
        print("   En cas de problème, restaurer le backup:")

        backup_dirs = list((self.weekly_reports_dir.parent).glob("weekly_reports.backup.casing_*"))
        if backup_dirs:
            latest_backup = max(backup_dirs, key=lambda p: p.name)
            print("      rm -rf logs/weekly_reports")
            print(f"      cp -r logs/{latest_backup.name} logs/weekly_reports")
        print()

    def run(self):
        """Execute la normalisation complète.

        Refactored from C-15 complexity using 4 helper methods for better separation of concerns.
        """
        # Step 1: Display header
        self._display_header()

        # Step 2: Scan and validate directories
        directories, to_change = self._validate_and_get_directories()
        if directories is None:
            return False
        if not to_change:
            return True

        # Step 3: Get user confirmation
        if not self._get_user_confirmation():
            return False

        # Step 4: Create backup
        print()
        if not self.create_backup():
            print("❌ Échec backup, abandon")
            return False

        # Step 5: Normalize directories
        print()
        print("🔧 Normalisation en cours...")
        for d in to_change:
            self.normalize_directory(d)

        # Step 6: Display final report
        self.print_report()

        # Step 7: Display recommendations
        self._display_recommendations()

        return len(self.errors) == 0


def main():
    """Command-line entry point for normalizing weekly reports directory casing."""
    parser = argparse.ArgumentParser(
        description="Normaliser la casse des répertoires weekly_reports"
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Simuler les changements sans les appliquer"
    )

    parser.add_argument(
        "--force", action="store_true", help="Forcer le renommage même si la cible existe"
    )

    parser.add_argument(
        "--project-root", default=".", help="Racine du projet (défaut: répertoire courant)"
    )

    args = parser.parse_args()

    # Créer le normalisateur
    normalizer = CasingNormalizer(
        project_root=args.project_root, dry_run=args.dry_run, force=args.force
    )

    # Exécuter
    success = normalizer.run()

    # Code de sortie
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
