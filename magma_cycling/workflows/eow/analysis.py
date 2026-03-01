"""Week analysis methods for EndOfWeekWorkflow."""

import sys


class AnalysisMixin:
    """Analyse de la semaine écoulée et chargement des rapports."""

    def _step1_analyze_completed_week(self) -> bool:
        """Step 1: Analyze completed week with weekly-analysis."""
        print("\n" + "=" * 80)
        print(f"📊 STEP 1/7: Analyse Semaine {self.week_completed}")
        print("=" * 80)
        print()

        if self.dry_run:
            print("🔍 DRY-RUN: Simulation analyse semaine")
            self.reports = {
                "bilan_final": "[DRY-RUN] Bilan final simulé",
                "transition": "[DRY-RUN] Transition simulée",
            }
            return True

        try:
            completed_week_file = (
                self.reports_dir
                / self.week_completed
                / f"bilan_final_{self.week_completed.lower()}.md"
            )

            # Check if analysis already exists
            if completed_week_file.exists():
                print(f"  ✅ Analyse {self.week_completed} déjà existante")
                print(f"  📁 {completed_week_file}")

                # Load existing reports
                self._load_existing_reports()
                return True
            else:
                # Analysis doesn't exist - run it automatically
                print(f"  ⚠️  Analyse {self.week_completed} introuvable")
                print("  🤖 Lancement automatique de weekly-analysis...")
                print()

                try:
                    from magma_cycling.workflows.workflow_weekly import (
                        run_weekly_analysis,
                    )

                    # Run weekly-analysis programmatically (Phase 2 - modern system)
                    run_weekly_analysis(
                        week=self.week_completed,
                        start_date=self.completed_start_date,
                        data_dir=self.data_dir,
                        ai_analysis=False,
                    )

                    # Verify that analysis was created
                    if completed_week_file.exists():
                        print()
                        print(f"  ✅ Analyse {self.week_completed} générée avec succès")
                        print(f"  📁 {completed_week_file}")

                        # Load newly created reports
                        self._load_existing_reports()
                        return True
                    else:
                        print()
                        print("  ❌ Erreur : fichier bilan_final non créé")
                        return False

                except Exception as e:
                    print()
                    print(f"  ❌ Erreur lors de weekly-analysis : {e}")
                    if "--verbose" in sys.argv:
                        import traceback

                        traceback.print_exc()
                    return False

        except Exception as e:
            print(f"  ❌ Erreur analyse : {e}")
            return False

    def _load_existing_reports(self):
        """Load existing reports from completed week."""
        report_files = {
            "bilan_final": f"bilan_final_{self.week_completed.lower()}.md",
            "transition": f"transition_{self.week_completed.lower()}.md",
            "workout_history": f"workout_history_{self.week_completed.lower()}.md",
            "metrics_evolution": f"metrics_evolution_{self.week_completed.lower()}.md",
        }

        week_dir = self.reports_dir / self.week_completed

        for key, filename in report_files.items():
            filepath = week_dir / filename
            if filepath.exists():
                self.reports[key] = filepath.read_text(encoding="utf-8")
            else:
                self.reports[key] = f"[{filename} non trouvé]"
