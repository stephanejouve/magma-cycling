#!/usr/bin/env python3
"""
fix_weekly_reports_casing.py - Correction automatique casse weekly_reports.

Ce script corrige les problèmes de casse dans logs/weekly_reports/ :
- Supprime doublon s067 (identique à S067)
- Renomme s070 → S070
- Avec backup, validation, rollback possible

Usage:
    # Dry-run (simulation sans modifications)
    python3 magma_cycling/fix_weekly_reports_casing.py --dry-run

    # Exécution réelle (demande confirmation)
    python3 magma_cycling/fix_weekly_reports_casing.py

    # Force (sans confirmation - DANGEREUX)
    python3 magma_cycling/fix_weekly_reports_casing.py --force

    # Rollback (restaurer backup)
    python3 magma_cycling/fix_weekly_reports_casing.py --rollback.
"""
import argparse
import shutil
from datetime import datetime
from pathlib import Path

from magma_cycling.utils.cli import cli_main


class WeeklyReportsFixing:
    """Correcteur de casse pour weekly_reports."""

    def __init__(self, project_root="."):
        """Initialize weekly reports casing fixer.

        Args:
            project_root: Project root directory path (default: current directory).
        """
        self.project_root = Path(project_root)

        self.weekly_dir = self.project_root / "logs" / "weekly_reports"
        self.backup_dir = None
        self.log_file = self.project_root / "fix_weekly_reports.log"
        self.changes = []

    def log(self, message):
        """Logger message console + fichier."""
        print(message)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")

    def backup_weekly_reports(self):
        """Create backup complet avant modifications."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        backup_name = f"weekly_reports.backup.{timestamp}"
        self.backup_dir = self.weekly_dir.parent / backup_name

        print("\n" + "=" * 70)
        print("📦 BACKUP")
        print("=" * 70)
        print(f"Source : {self.weekly_dir}")
        print(f"Backup : {self.backup_dir}")
        print()

        try:
            shutil.copytree(self.weekly_dir, self.backup_dir)
            self.log(f"✅ Backup créé : {self.backup_dir}")

            # Vérifier backup
            backup_files = sum(1 for _ in self.backup_dir.rglob("*") if _.is_file())
            source_files = sum(1 for _ in self.weekly_dir.rglob("*") if _.is_file())

            print(f"   Fichiers source : {source_files}")
            print(f"   Fichiers backup : {backup_files}")

            if backup_files != source_files:
                raise Exception(f"Backup incomplet : {backup_files} != {source_files}")

            print("   ✅ Backup vérifié")
            return True

        except Exception as e:
            self.log(f"❌ Erreur backup : {e}")
            return False

    def audit_structure(self):
        """Auditer structure actuelle et retourner problèmes."""
        print("\n" + "=" * 70)

        print("🔍 AUDIT STRUCTURE")
        print("=" * 70)

        if not self.weekly_dir.exists():
            print(f"❌ Répertoire non trouvé : {self.weekly_dir}")
            return None

        dirs = sorted([d.name for d in self.weekly_dir.iterdir() if d.is_dir()])

        print(f"\nRépertoires trouvés : {len(dirs)}")
        for d in dirs:
            files_count = len(list((self.weekly_dir / d).glob("*.md")))
            status = "✅" if d[0].isupper() else "❌"
            print(f"  {status} {d} ({files_count} fichiers)")

        # Identifier problèmes
        problems = {"lowercase": [d for d in dirs if d[0].islower()], "duplicates": []}

        # Détecter doublons (ex: S067 et s067)
        for d in problems["lowercase"]:
            upper_version = d.upper()
            if upper_version in dirs:
                problems["duplicates"].append((d, upper_version))

        print("\n📊 Problèmes détectés :")
        print(f"  • Casse incorrecte : {len(problems['lowercase'])}")
        print(f"  • Doublons : {len(problems['duplicates'])}")

        return problems

    def fix_duplicate(self, lower_dir, upper_dir, dry_run=False):
        """Corriger doublon (supprimer version minuscule)."""
        lower_path = self.weekly_dir / lower_dir

        upper_path = self.weekly_dir / upper_dir

        print(f"\n🔧 Correction doublon : {lower_dir} / {upper_dir}")

        # Comparer contenus
        lower_files = {(lower_path / f).name for f in lower_path.glob("*.md")}
        upper_files = {(upper_path / f).name for f in upper_path.glob("*.md")}

        print(f"   {lower_dir} : {len(lower_files)} fichiers")
        print(f"   {upper_dir} : {len(upper_files)} fichiers")

        # Vérifier dates modification
        lower_mtime = lower_path.stat().st_mtime
        upper_mtime = upper_path.stat().st_mtime

        if upper_mtime > lower_mtime:
            print(f"   → {upper_dir} plus récent (garder)")
            print(f"   → {lower_dir} plus ancien (supprimer)")
            action = f"Supprimer {lower_dir}"
        else:
            print(f"   ⚠️  {lower_dir} plus récent que {upper_dir}")
            print("   → Recommandation manuelle requise")
            return False

        if dry_run:
            print(f"   🧪 DRY-RUN : {action}")
            return True

        # Exécution réelle
        try:
            shutil.rmtree(lower_path)
            self.log(f"✅ Supprimé : {lower_dir}")
            self.changes.append(f"Supprimé doublon : {lower_dir}")
            print(f"   ✅ {action}")
            return True
        except Exception as e:
            self.log(f"❌ Erreur suppression {lower_dir} : {e}")
            return False

    def fix_lowercase(self, lower_dir, dry_run=False):
        """Renommer répertoire minuscule → majuscule."""
        lower_path = self.weekly_dir / lower_dir

        upper_name = lower_dir.upper()
        upper_path = self.weekly_dir / upper_name

        print(f"\n🔧 Correction casse : {lower_dir} → {upper_name}")

        # Vérifier que majuscule n'existe pas déjà
        if upper_path.exists():
            print(f"   ⚠️  {upper_name} existe déjà")
            print("   → Utiliser fix_duplicate() pour gérer doublon")
            return False

        files_count = len(list(lower_path.glob("*.md")))
        print(f"   Fichiers à déplacer : {files_count}")

        if dry_run:
            print(f"   🧪 DRY-RUN : Renommer {lower_dir} → {upper_name}")
            return True

        # Exécution réelle
        try:
            lower_path.rename(upper_path)
            self.log(f"✅ Renommé : {lower_dir} → {upper_name}")
            self.changes.append(f"Renommé : {lower_dir} → {upper_name}")
            print("   ✅ Renommé")
            return True
        except Exception as e:
            self.log(f"❌ Erreur renommage {lower_dir} : {e}")
            return False

    def validate_final_structure(self):
        """Validate structure finale après corrections."""
        print("\n" + "=" * 70)

        print("✓  VALIDATION FINALE")
        print("=" * 70)

        dirs = sorted([d.name for d in self.weekly_dir.iterdir() if d.is_dir()])

        # Vérifier aucune minuscule
        lowercase = [d for d in dirs if d[0].islower()]
        if lowercase:
            print(f"❌ Minuscules restantes : {lowercase}")
            return False

        # Vérifier format
        invalid = [d for d in dirs if not (d[0] == "S" and len(d) == 4 and d[1:].isdigit())]
        if invalid:
            print(f"❌ Format invalide : {invalid}")
            return False

        # Compter fichiers
        total_files = sum(1 for _ in self.weekly_dir.rglob("*.md"))

        print("\n✅ Structure valide")
        print(f"   Répertoires : {len(dirs)}")
        print(f"   Fichiers .md : {total_files}")
        print(f"   Format : {'✅ Tous SXXX' if not invalid else '❌'}")
        print(f"   Casse : {'✅ Tous majuscules' if not lowercase else '❌'}")

        return True

    def run_fixes(self, dry_run=False):
        """Execute toutes les corrections."""
        print("\n" + "=" * 70)

        print("🔧 CORRECTIONS" + (" (DRY-RUN)" if dry_run else ""))
        print("=" * 70)

        problems = self.audit_structure()
        if not problems:
            return False

        success_count = 0
        total_fixes = len(problems["duplicates"]) + len(problems["lowercase"])

        # Traiter doublons d'abord
        for lower, upper in problems["duplicates"]:
            if self.fix_duplicate(lower, upper, dry_run):
                success_count += 1
                # Retirer de la liste des minuscules (déjà traité)
                if lower in problems["lowercase"]:
                    problems["lowercase"].remove(lower)

        # Traiter minuscules restantes (sans doublon)
        for lower_dir in problems["lowercase"]:
            if self.fix_lowercase(lower_dir, dry_run):
                success_count += 1

        print(f"\n📊 Résumé : {success_count}/{total_fixes} corrections réussies")

        if not dry_run:
            self.log(f"Corrections terminées : {success_count}/{total_fixes}")

        return success_count == total_fixes

    def rollback(self):
        """Restore depuis backup le plus récent."""
        print("\n" + "=" * 70)

        print("⏮️  ROLLBACK")
        print("=" * 70)

        # Trouver backup le plus récent
        backups = sorted(self.weekly_dir.parent.glob("weekly_reports.backup.*"))

        if not backups:
            print("❌ Aucun backup trouvé")
            return False

        latest_backup = backups[-1]
        print(f"Backup le plus récent : {latest_backup}")
        print()

        confirm = input("⚠️  Restaurer ce backup (écrasera l'actuel) ? (yes/no) : ").strip().lower()

        if confirm != "yes":
            print("❌ Rollback annulé")
            return False

        try:
            # Supprimer actuel
            shutil.rmtree(self.weekly_dir)

            # Restaurer backup
            shutil.copytree(latest_backup, self.weekly_dir)

            self.log(f"✅ Rollback réussi depuis : {latest_backup}")
            print("\n✅ Rollback terminé")
            return True

        except Exception as e:
            self.log(f"❌ Erreur rollback : {e}")
            print(f"❌ Erreur : {e}")
            return False


@cli_main
def main():
    """Command-line entry point for fixing weekly reports casing."""
    parser = argparse.ArgumentParser(
        description="Corriger casse weekly_reports avec backup/rollback",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--dry-run", action="store_true", help="Simulation sans modifications")

    parser.add_argument(
        "--force", action="store_true", help="Exécuter sans confirmation (DANGEREUX)"
    )

    parser.add_argument(
        "--rollback", action="store_true", help="Restaurer depuis backup le plus récent"
    )

    args = parser.parse_args()

    fixer = WeeklyReportsFixing()

    # Mode rollback
    if args.rollback:
        fixer.rollback()
        return 0

    # Audit initial
    problems = fixer.audit_structure()

    if not problems or (not problems["lowercase"] and not problems["duplicates"]):
        print("\n✅ Aucun problème détecté")
        return 0

    # Dry-run
    if args.dry_run:
        fixer.run_fixes(dry_run=True)
        print("\n🧪 DRY-RUN terminé (aucune modification effectuée)")
        return 0

    # Confirmation utilisateur
    if not args.force:
        print("\n" + "=" * 70)
        print("⚠️  CONFIRMATION")
        print("=" * 70)
        print("\nCorrections à effectuer :")
        print(f"  • Doublons : {len(problems['duplicates'])}")
        print(f"  • Casse incorrecte : {len(problems['lowercase'])}")
        print()
        print("Un backup sera créé automatiquement.")
        print()

        confirm = input("Continuer avec les corrections ? (yes/no) : ").strip().lower()

        if confirm != "yes":
            print("\n❌ Corrections annulées")
            return 0

    # Backup
    if not fixer.backup_weekly_reports():
        print("\n❌ Backup échoué → Abandon")
        return 1

    # Corrections
    success = fixer.run_fixes(dry_run=False)

    # Validation
    if success:
        if fixer.validate_final_structure():
            print("\n" + "=" * 70)
            print("✅ CORRECTIONS TERMINÉES")
            print("=" * 70)
            print("\nChangements effectués :")
            for change in fixer.changes:
                print(f"  • {change}")
            print()
            print(f"Backup disponible : {fixer.backup_dir}")
            print(f"Log détaillé : {fixer.log_file}")
            return 0
        else:
            print("\n❌ Validation finale échouée")
            print(f"⚠️  Utilisez --rollback pour restaurer : {fixer.backup_dir}")
            return 1
    else:
        print("\n❌ Corrections incomplètes")
        print(f"⚠️  Backup disponible : {fixer.backup_dir}")
        return 1


if __name__ == "__main__":
    main()  # pragma: no cover
