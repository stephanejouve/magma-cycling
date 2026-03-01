"""Archive and summary methods for EndOfWeekWorkflow."""


class ArchiveMixin:
    """Archivage, commit et résumé de fin de workflow."""

    def _step6_archive_and_commit(self):
        """Step 6: Archive and commit (optional)."""
        print("\n" + "=" * 80)
        print("📦 STEP 6/7: Archivage et Commit")
        print("=" * 80)
        print()

        if self.dry_run:
            print("🔍 DRY-RUN: Simulation archivage")
            return

        print("  ℹ️  Fonctionnalité en développement")
        print("  💡 Commitez manuellement avec:")
        print(f"     git add {self.reports_dir}/{self.week_completed}/ {self.planning_dir}/")
        print(
            f'     git commit -m "feat: Complete end-of-week {self.week_completed} → {self.week_next}"'
        )
        print()

    def _print_success_summary(self):
        """Print success summary."""
        print("\n" + "=" * 80)
        print("✅ WORKFLOW TERMINÉ AVEC SUCCÈS")
        print("=" * 80)
        print()
        print(f"  📊 Semaine analysée   : {self.week_completed}")
        print(f"  📅 Semaine planifiée  : {self.week_next}")
        print(f"  🤖 Provider utilisé   : {self.provider}")
        if self.workouts_file:
            print(f"  📁 Fichier workouts   : {self.workouts_file}")
        print()
        print("  🎯 Prochaines étapes:")
        print("     1. Vérifiez les workouts dans Intervals.icu")
        print("     2. Ajustez si nécessaire avec workflow-coach en servo-mode")
        print("     3. Commitez les changements (si --archive non utilisé)")
        print()
        print("=" * 80)
