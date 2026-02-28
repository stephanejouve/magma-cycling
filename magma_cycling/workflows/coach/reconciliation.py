"""Week reconciliation methods for WorkflowCoach."""

from datetime import datetime

from magma_cycling.config import get_data_config
from magma_cycling.rest_and_cancellations import (
    load_week_planning,
    reconcile_planned_vs_actual,
)


class ReconciliationMixin:
    """Batch reconciliation of planned vs actual sessions."""

    def _display_reconciliation_report(self, result: dict):
        """Affiche le rapport de réconciliation.

        Args:
            result: Résultat de reconcile_planned_vs_actual().
        """
        print("\n" + "=" * 70)

        print("📊 RAPPORT RÉCONCILIATION")
        print("=" * 70)

        sessions_planned = len(self.planning["planned_sessions"])
        print(f"\nSessions planifiées   : {sessions_planned}")
        print(f"Sessions exécutées    : {len(result['matched'])}")
        print(f"Repos planifiés       : {len(result['rest_days'])}")
        print(f"Séances annulées      : {len(result['cancelled'])}")

        if result.get("unplanned"):
            print(f"⚠️  Activités non planifiées : {len(result['unplanned'])}")

        # Détail par catégorie
        if result["matched"]:
            print("\n✅ Séances exécutées :")
            for match in result["matched"]:
                session = match["session"]
                print(f"   - {session['session_id']} ({session['date']})")

        if result["rest_days"]:
            print("\n💤 Repos planifiés :")
            for rest in result["rest_days"]:
                print(f"   - {rest['session_id']} ({rest['date']})")

        if result["cancelled"]:
            print("\n❌ Séances annulées :")
            for cancelled in result["cancelled"]:
                reason = cancelled.get("cancellation_reason", "Non spécifié")[:50]
                print(f"   - {cancelled['session_id']} ({cancelled['date']}) - {reason}...")

        if result.get("unplanned"):
            print("\n⚠️  Activités non planifiées :")
            for unplanned in result["unplanned"]:
                name = unplanned.get("name", "Sans nom")[:40]
                date = unplanned["start_date_local"][:10]
                print(f"   - {name} ({date})")

        print("=" * 70)

    def reconcile_week(self, week_id: str):
        """Mode réconciliation batch pour séances sautées/annulées.

        Args:
            week_id: ID semaine (ex: S070).
        """
        self.clear_screen()

        self.print_header("🤖 WORKFLOW COACH AI - Réconciliation Batch", f"Semaine {week_id}")

        # 0. Initialiser API (centralized, Sprint R9.B Phase 2)
        try:
            api = self._get_api()
        except ValueError:
            print("❌ Credentials Intervals.icu non trouvées")
            print("   Vérifier ~/.intervals_config.json ou variables d'environnement")
            return

        # 1. Charger planning JSON local
        config = get_data_config()
        planning_dir = config.week_planning_dir
        try:
            planning = load_week_planning(week_id, planning_dir)
            print(f"✅ Planning chargé: {week_id}")
            print(f"   Période: {planning.start_date} → {planning.end_date}")
            print(f"   Sessions: {len(planning.planned_sessions)}")
        except FileNotFoundError:
            print(f"❌ Fichier planning non trouvé: week_planning_{week_id}.json")
            print(f"   Vérifier: {planning_dir}")
            return
        except Exception as e:
            print(f"❌ Erreur chargement planning: {e}")
            return

        # 2. Récupérer activités réalisées depuis API
        print("\n🔍 Récupération activités depuis Intervals.icu...")
        try:
            activities = api.get_activities(oldest=planning.start_date, newest=planning.end_date)
            print(f"✅ {len(activities)} activité(s) trouvée(s)")
        except Exception as e:
            print(f"❌ Erreur récupération activités: {e}")
            return

        # 3. Réconcilier planifié vs réalisé
        print("\n⚙️  Réconciliation en cours...")
        try:
            reconciliation = reconcile_planned_vs_actual(planning, activities)
        except Exception as e:
            print(f"❌ Erreur réconciliation: {e}")
            import traceback

            traceback.print_exc()
            return

        # 4. Afficher résumé réconciliation
        print(f"\n{'=' * 70}")
        print(f"📊 RÉSUMÉ RÉCONCILIATION - {week_id}")
        print(f"{'=' * 70}")
        print(f"✅ Complétées       : {len(reconciliation['matched'])}")
        print(f"⏭️  Sautées         : {len(reconciliation['skipped'])}")
        print(f"❌ Annulées        : {len(reconciliation['cancelled'])}")
        print(f"💤 Repos planifiés : {len(reconciliation['rest_days'])}")
        print(f"{'=' * 70}\n")

        # Compteurs pour rapport final
        updated_count = 0
        skipped_count = 0

        # 5. Traiter séances sautées
        if reconciliation["skipped"]:
            print(f"\n⏭️  SÉANCES SAUTÉES À TRAITER ({len(reconciliation['skipped'])})")
            print("=" * 70)

            for session in reconciliation["skipped"]:
                print(f"\n📌 Séance: {session['session_id']}")
                print(f"   Date: {session['date']}")
                print(f"   Nom: {session.get('name', 'N/A')}")
                print(f"   Type: {session['type']}")
                print(f"   TSS planifié: {session.get('tss_planned', 0)}")

                # Vérifier si déjà marquée comme sautée
                if session.get("status") == "skipped":
                    print("   ℹ️  Déjà marquée comme sautée")
                    skipped_count += 1
                    continue

                # Prompt utilisateur
                print("\n💡 Actions possibles:")
                print("   [1] Marquer comme sautée (oubli)")
                print("   [2] Marquer comme annulée (raison manuelle)")
                print("   [3] Ignorer (garder status actuel)")

                choice = input("\n   Choix (1-3): ").strip()

                if choice == "1":
                    reason = input("   Raison (optionnel): ").strip()
                    if not reason:
                        reason = "Séance sautée - réconciliation batch"

                    # Mettre à jour la session
                    session["status"] = "skipped"
                    if "history" not in session:
                        session["history"] = []
                    session["history"].append(
                        {
                            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                            "action": "reconciled_skipped",
                            "reason": reason,
                        }
                    )

                    # Supprimer le workout de Intervals.icu si présent
                    workout_id = self._get_workout_id_intervals(session["date"])
                    if workout_id:
                        print(f"   🗑️  Suppression workout Intervals.icu (ID: {workout_id})...")
                        if self._delete_workout_intervals(workout_id):
                            print("   ✅ Workout supprimé de l'API")
                        else:
                            print("   ⚠️  Échec suppression workout API")

                    updated_count += 1
                    print("   ✅ Marquée comme sautée")

                elif choice == "2":
                    reason = input("   Raison annulation: ").strip()
                    if not reason:
                        reason = "Séance annulée - réconciliation batch"

                    # Mettre à jour la session
                    session["status"] = "cancelled"
                    session["cancellation_reason"] = reason
                    if "history" not in session:
                        session["history"] = []
                    session["history"].append(
                        {
                            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                            "action": "reconciled_cancelled",
                            "reason": reason,
                        }
                    )
                    updated_count += 1
                    print("   ✅ Marquée comme annulée")

                else:
                    print("   ⏭️  Ignorée")

        # 6. Traiter séances annulées (déjà marquées comme cancelled)
        if reconciliation["cancelled"]:
            print(f"\n\n❌ SÉANCES ANNULÉES ({len(reconciliation['cancelled'])})")
            print("=" * 70)

            for session in reconciliation["cancelled"]:
                print(f"\n📌 Séance: {session['session_id']}")
                print(f"   Date: {session['date']}")
                print(f"   Nom: {session.get('name', 'N/A')}")
                print(f"   Raison: {session.get('cancellation_reason', 'Non spécifiée')}")
                print("   ℹ️  Déjà marquée comme annulée")

        # 7. Afficher repos planifiés (informatif)
        if reconciliation["rest_days"]:
            print(f"\n\n💤 REPOS PLANIFIÉS ({len(reconciliation['rest_days'])})")
            print("=" * 70)

            for session in reconciliation["rest_days"]:
                print(f"   • {session['date']}: {session.get('name', 'Repos')}")

        # 8. Sauvegarder planning mis à jour
        if updated_count > 0:
            print("\n\n💾 Sauvegarde planning mis à jour...")

            # Update metadata (planning is WeeklyPlan object)
            planning.last_updated = datetime.now().isoformat() + "Z"

            # Sauvegarder via Pydantic (planning is WeeklyPlan object)
            planning_file = planning_dir / f"week_planning_{week_id}.json"
            try:
                # ✅ Sauvegarde via Pydantic.to_json()
                planning.to_json(planning_file)
                print(f"✅ Planning sauvegardé: {planning_file.name}")
                print(f"   Version: {planning.version}")

                # 📋 LOG TO AUDIT (reconciliation interactive)
                from magma_cycling.planning.audit_log import (
                    OperationStatus,
                    OperationType,
                    audit_log,
                )

                audit_log.log_operation(
                    operation=OperationType.MODIFY,
                    week_id=week_id,
                    status=OperationStatus.SUCCESS,
                    tool="workflow-coach",
                    description=f"Interactive reconciliation: {updated_count} sessions updated",
                    reason="Batch reconciliation of skipped/cancelled sessions",
                    files_modified=[f"week_planning_{week_id}.json"],
                    file_timestamp=planning.last_updated,
                )
            except Exception as e:
                print(f"❌ Erreur sauvegarde: {e}")
                return

        # 9. Rapport final
        print(f"\n{'=' * 70}")
        print(f"✅ RÉCONCILIATION {week_id} TERMINÉE")
        print(f"{'=' * 70}")
        print(f"📝 Sessions mises à jour : {updated_count}")
        print(f"⏭️  Déjà marquées sautées : {skipped_count}")
        print(f"❌ Déjà annulées         : {len(reconciliation['cancelled'])}")
        print(f"💤 Repos planifiés       : {len(reconciliation['rest_days'])}")
        print(f"{'=' * 70}\n")

        if updated_count > 0:
            print("💡 Prochaine étape: Committer les modifications")
            print(f"   git add {planning_file}")
            print(f"   git commit -m 'fix: Réconciliation {week_id}'")
