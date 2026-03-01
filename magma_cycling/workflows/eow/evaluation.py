"""PID evaluation and monthly analysis methods for EndOfWeekWorkflow."""

import sys


class EvaluationMixin:
    """Évaluation PID et analyse mensuelle automatique."""

    def _step1b_pid_evaluation(self) -> bool:
        """Step 1b: PID evaluation and intelligence learning."""
        print("\n" + "=" * 80)
        print("🧠 STEP 1b/7: Évaluation PID & Training Intelligence")
        print("=" * 80)
        print()

        if self.dry_run:
            print("🔍 DRY-RUN: Simulation évaluation PID")
            return True

        try:
            print("  ℹ️  Collecte des métriques d'entraînement...")
            print(f"  📅 Période: {self.completed_start_date} → {self.completed_end_date}")
            print()

            # Import and run PID evaluation
            from magma_cycling.scripts.pid_daily_evaluation import (
                PIDDailyEvaluator,
            )

            evaluator = PIDDailyEvaluator(dry_run=False)

            # Run evaluation for the completed week
            result = evaluator.run_daily_evaluation(days_back=7)

            print()
            print("  ✅ Évaluation PID terminée")
            print("  📊 Données sauvegardées dans ~/data/monitoring/pid_evaluation.jsonl")
            print("  🧠 Intelligence mise à jour dans ~/data/intelligence.json")

            # Display test recommendation if present
            test_rec = result.get("test_recommendation")
            if test_rec:
                print()
                print("  " + "=" * 76)
                print(f"  🎯 RECOMMANDATION DÉTECTÉE: {test_rec['status']}")
                print("  " + "=" * 76)
                print(f"  💡 {test_rec['message']}")
                print(f"  📅 {test_rec['timing']}")
                print(f"  ⏰ Dernier test: {test_rec['weeks_since_test']:.1f} semaines")
                print(f"  💪 TSB actuel: {test_rec['tsb']:.1f}")
                print("  " + "=" * 76)

            return True

        except Exception as e:
            print(f"  ⚠️  Erreur évaluation PID (non bloquant) : {e}")
            if "--verbose" in sys.argv:
                import traceback

                traceback.print_exc()
            # Non-blocking: continue workflow even if PID evaluation fails
            return True

    def _step1c_monthly_analysis_if_month_end(self) -> bool:
        """Step 1c: Generate monthly analysis if month transition detected."""
        # Detect month transition
        completed_month = self.completed_start_date.strftime("%Y-%m")
        next_month = self.next_start_date.strftime("%Y-%m")

        if completed_month == next_month:
            # No month transition - skip
            return True

        # Month transition detected!
        print("\n" + "=" * 80)
        print(f"📊 STEP 1c/7: Analyse Mensuelle Automatique - {completed_month}")
        print("=" * 80)
        print()
        print(f"  🎯 Transition de mois détectée: {completed_month} → {next_month}")
        print(f"  📅 Génération rapport mensuel pour {completed_month}")
        print()

        if self.dry_run:
            print("🔍 DRY-RUN: Simulation analyse mensuelle")
            return True

        try:
            # Import monthly analyzer
            from magma_cycling.monthly_analysis import MonthlyAnalyzer

            # Generate monthly report
            analyzer = MonthlyAnalyzer(
                month=completed_month, provider=self.provider, no_ai=(self.provider == "clipboard")
            )

            report = analyzer.run()

            if not report:
                print()
                print("  ⚠️  Rapport vide - aucune donnée disponible")
                return True

            # Save report to file
            report_file = self.reports_dir / f"monthly_report_{completed_month}.md"
            report_file.write_text(report, encoding="utf-8")

            print()
            print("  ✅ Rapport mensuel généré et sauvegardé")
            print(f"  📁 {report_file}")
            print()

            return True

        except Exception as e:
            print()
            print(f"  ⚠️  Erreur génération rapport mensuel (non bloquant) : {e}")
            if "--verbose" in sys.argv:
                import traceback

                traceback.print_exc()
            # Non-blocking: continue workflow even if monthly analysis fails
            return True
