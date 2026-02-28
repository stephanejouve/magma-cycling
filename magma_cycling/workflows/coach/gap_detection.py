"""Gap detection methods for WorkflowCoach."""

import json
from datetime import datetime, timedelta

from magma_cycling.config import get_data_config
from magma_cycling.planned_sessions_checker import PlannedSessionsChecker
from magma_cycling.rest_and_cancellations import (
    reconcile_planned_vs_actual,
    validate_week_planning,
)
from magma_cycling.workflow_state import WorkflowState


class GapDetectionMixin:
    """Detection of unanalyzed activities, skipped sessions, rest days, and cancellations."""

    def _detect_unanalyzed_activities(
        self, state: "WorkflowState", oldest_date: str, newest_date: str
    ) -> list[dict] | None:
        """Detect executed activities that haven't been analyzed yet.

        Args:
            state: WorkflowState instance for tracking
            oldest_date: Start date for activity search (YYYY-MM-DD)
            newest_date: End date for activity search (YYYY-MM-DD)

        Returns:
            List of unanalyzed activities or None if error/not found.
        """
        try:
            api = self._get_api()
            activities = api.get_activities(oldest=oldest_date, newest=newest_date)

            # Filter unanalyzed activities
            activities.sort(key=lambda x: x["start_date_local"], reverse=True)
            unanalyzed = state.get_unanalyzed_activities(activities)

            return unanalyzed if unanalyzed else None

        except Exception as e:
            print(f"⚠️  Erreur API : {e}")
            return None

    def _detect_skipped_sessions(self, oldest_date: str, newest_date: str) -> list[dict] | None:
        """Detect planned sessions that were skipped (not executed).

        Args:
            oldest_date: Start date for search (YYYY-MM-DD)
            newest_date: End date for search (YYYY-MM-DD)

        Returns:
            List of skipped sessions or None if error/not found.
        """
        try:
            checker = PlannedSessionsChecker(client=self._get_api())

            skipped_sessions = checker.detect_skipped_sessions(
                start_date=oldest_date,
                end_date=newest_date,
                exclude_future=True,
            )

            return skipped_sessions if skipped_sessions else None

        except Exception as e:
            print(f"⚠️  Détection séances sautées impossible : {e}")
            print("   Continuer avec détection activités exécutées uniquement")
            return None

    def _filter_documented_sessions(
        self, sessions: list[dict], state: "WorkflowState", session_type: str
    ) -> list[dict]:
        """Filter out sessions that have already been documented.

        Args:
            sessions: List of sessions to filter
            state: WorkflowState instance for checking documentation status
            session_type: Type of session ("skipped", "rest", "cancelled")

        Returns:
            Filtered list excluding already documented sessions
        """
        if not sessions:
            return []

        original_count = len(sessions)
        filtered = []

        for session in sessions:
            # Extract session_id based on session type
            if session_type == "skipped":
                planned_name = session.get("planned_name", "")
                # Format: "S072-05 - Name" or "S072-05-TEC-TechniqueCadence-V001"
                if " - " in planned_name:
                    session_id = planned_name.split(" - ")[0]
                else:
                    parts = planned_name.split("-")
                    session_id = f"{parts[0]}-{parts[1]}" if len(parts) >= 2 else planned_name
                date = session.get("planned_date", "")
            else:  # rest or cancelled
                session_id = session.get("session_id", "")
                date = session.get("date", "")

            # Check if already documented
            if not state.is_special_session_documented(session_id, date):
                filtered.append(session)

        # Log filtering if sessions were removed
        filtered_count = original_count - len(filtered)
        if filtered_count > 0:
            type_label = {
                "skipped": "séance(s) sautée(s)",
                "rest": "repos planifié(s)",
                "cancelled": "annulation(s)",
            }.get(session_type, "session(s)")
            print(f"[INFO] {filtered_count} {type_label} déjà documentée(s) - ignorée(s)")

        return filtered

    def _detect_rest_and_cancelled_sessions(self) -> tuple[list[dict], list[dict]]:
        """Detect rest days and cancelled sessions from planning.

        Returns:
            Tuple of (rest_days, cancelled_sessions).
        """
        rest_days: list[dict] = []

        cancelled_sessions: list[dict] = []

        if not self.week_id:
            return rest_days, cancelled_sessions

        try:
            config = get_data_config()
            planning_dir = config.week_planning_dir
            planning_file = planning_dir / f"week_planning_{self.week_id}.json"

            if not planning_file.exists():
                return rest_days, cancelled_sessions

            with open(planning_file, encoding="utf-8") as f:
                self.planning = json.load(f)

            if not validate_week_planning(self.planning):
                return rest_days, cancelled_sessions

            # Reconciliation (centralized API client, Sprint R9.B Phase 2)
            api = self._get_api()

            planning_activities = api.get_activities(
                oldest=self.planning["start_date"], newest=self.planning["end_date"]
            )

            self.reconciliation = reconcile_planned_vs_actual(self.planning, planning_activities)

            rest_days = self.reconciliation.get("rest_days", [])
            cancelled_sessions = self.reconciliation.get("cancelled", [])

        except Exception as e:
            print(f"⚠️  Erreur chargement planning : {e}")

        return rest_days, cancelled_sessions

    def _display_gaps_summary(self, gaps_data: dict) -> int:
        """Display unified summary of all detected gaps.

        Args:
            gaps_data: Dict with 'unanalyzed', 'skipped', 'rest_days', 'cancelled' lists

        Returns:
            Total number of gaps detected.
        """
        print("\n" + "=" * 70)

        print("📊 RÉSUMÉ GAPS DÉTECTÉS")
        print("=" * 70)

        unanalyzed = gaps_data.get("unanalyzed", [])
        skipped = gaps_data.get("skipped", [])
        rest_days = gaps_data.get("rest_days", [])
        cancelled = gaps_data.get("cancelled", [])

        count_executed = len(unanalyzed)
        count_skipped = len(skipped)
        count_rest = len(rest_days)
        count_cancelled = len(cancelled)
        total_gaps = count_executed + count_skipped + count_rest + count_cancelled

        if total_gaps == 0:
            print("\n✅ Aucun gap détecté !")
            print("   Toutes les séances récentes sont documentées.")
            print("   Aucune séance planifiée sautée.")
            print()
            return 0

        # Display executed activities
        if count_executed > 0:
            print(f"\n🚴 Séances exécutées non analysées : {count_executed}")
            for i, act in enumerate(unanalyzed[:3], 1):
                date = act["start_date_local"][:10]
                name = act.get("name", "Séance")[:40]
                print(f"   {i}. [{date}] {name}")
            if count_executed > 3:
                print(f"   ... et {count_executed - 3} autres")

        # Display rest days
        if count_rest > 0:
            print(f"\n💤 Repos planifiés non documentés : {count_rest}")
            for rest in rest_days[:3]:
                date = rest["date"]
                session_id = rest["session_id"]
                reason = rest.get("rest_reason", "Repos planifié")[:40]
                print(f"   • [{date}] {session_id} - {reason}")
            if count_rest > 3:
                print(f"   ... et {count_rest - 3} autres")

        # Display cancelled sessions
        if count_cancelled > 0:
            print(f"\n❌ Séances annulées non documentées : {count_cancelled}")
            for cancel in cancelled[:3]:
                date = cancel["date"]
                session_id = cancel["session_id"]
                reason = cancel.get("cancellation_reason", "Annulée")[:40]
                print(f"   • [{date}] {session_id} - {reason}")
            if count_cancelled > 3:
                print(f"   ... et {count_cancelled - 3} autres")

        # Display skipped sessions
        if count_skipped > 0:
            print(f"\n⏭️  Séances planifiées sautées : {count_skipped}")
            for skip in skipped[:3]:
                date = skip["planned_date"]
                name = skip["planned_name"][:40]
                tss = skip["planned_tss"]
                days = skip["days_ago"]
                print(f"   • [{date}] {name} ({tss} TSS, il y a {days}j)")
            if count_skipped > 3:
                print(f"   ... et {count_skipped - 3} autres")

        return total_gaps

    def _prompt_user_choice(self, gaps_data: dict) -> str:
        """Display menu and prompt user for action choice.

        Args:
            gaps_data: Dict with 'unanalyzed', 'skipped', 'rest_days', 'cancelled' lists

        Returns:
            Action choice string (e.g., "single_executed", "batch_all", "exit")
        """
        unanalyzed = gaps_data.get("unanalyzed", [])

        skipped = gaps_data.get("skipped", [])
        rest_days = gaps_data.get("rest_days", [])
        cancelled = gaps_data.get("cancelled", [])

        count_executed = len(unanalyzed)
        count_skipped = len(skipped)
        count_rest = len(rest_days)
        count_cancelled = len(cancelled)

        print("\n" + "=" * 70)
        print("💡 QUE VEUX-TU FAIRE ?")
        print("=" * 70)
        print()

        options = []
        option_mapping = {}

        # Option [1]: Executed activities
        if count_executed > 0:
            print("  [1] Traiter UNE séance exécutée (workflow classique)")
            options.append("1")
            option_mapping["1"] = "single_executed"

        next_option_num = 2

        # Option [2]: Rest/Cancellations (if present)
        if count_rest > 0 or count_cancelled > 0:
            rest_cancel_label = []
            if count_rest > 0:
                rest_cancel_label.append("repos")
            if count_cancelled > 0:
                rest_cancel_label.append("annulations")
            print(f"  [{next_option_num}] Traiter {'/'.join(rest_cancel_label)} en batch")
            options.append(str(next_option_num))
            option_mapping[str(next_option_num)] = "batch_rest_cancelled"
            next_option_num += 1

        # Option: Skipped sessions (if present)
        if count_skipped > 0:
            print(f"  [{next_option_num}] Traiter séances sautées en batch")
            options.append(str(next_option_num))
            option_mapping[str(next_option_num)] = "batch_skipped"
            next_option_num += 1

        # Option: ALL in batch (if mixed)
        if count_executed > 0 and ((count_rest > 0 or count_cancelled > 0) or count_skipped > 0):
            print(f"  [{next_option_num}] Traiter TOUT en batch (exécutées + spéciales)")
            options.append(str(next_option_num))
            option_mapping[str(next_option_num)] = "batch_all"

        print("  [0] Quitter")
        print()

        # Get user choice
        while True:
            if self.auto_mode:
                choice = "1"
                print(f"\n[AUTO MODE] Choix automatique : {choice}")
            else:
                choice = input("Ton choix : ").strip()

            if choice == "0":
                return "exit"
            elif choice in option_mapping:
                return option_mapping[choice]
            else:
                if self.auto_mode:
                    print("❌ Aucune option valide disponible")
                    return "exit"
                print("❌ Choix invalide, réessaye.")

    def step_1b_detect_all_gaps(self):
        """Étape 1b : Détection unifiée de tous les gaps.

        Returns:
            tuple: (choice: str, gaps_data: dict)
        """
        # Skip si activity_id fourni (bypass détection gaps)

        if self.activity_id:
            gaps_data = {"unanalyzed": [], "skipped": [], "rest_days": [], "cancelled": []}
            return "single_executed", gaps_data

        self.clear_screen()
        self.print_header("🔍 Détection Gaps", "Étape 1b/7 : Détection séances à documenter")

        # Initialize state
        state = WorkflowState(project_root=self.project_root)

        # Check API config
        try:
            self._get_api()
        except (ValueError, Exception) as e:
            print(f"⚠️  Config API non trouvée : {e} → Skip détection")
            self.wait_user()
            return "exit", {"unanalyzed": [], "skipped": [], "rest_days": [], "cancelled": []}

        # Determine date range
        last_analyzed_id = state.get_last_analyzed_id()
        if last_analyzed_id:
            oldest_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        else:
            oldest_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        newest_date = datetime.now().strftime("%Y-%m-%d")

        # 1. Detect unanalyzed executed activities
        self.unanalyzed_activities = self._detect_unanalyzed_activities(
            state, oldest_date, newest_date
        )

        # 2. Detect skipped sessions
        skipped = self._detect_skipped_sessions(oldest_date, newest_date)

        # 3. Filter out already documented skipped sessions
        self.skipped_sessions = self._filter_documented_sessions(skipped or [], state, "skipped")
        if not self.skipped_sessions:
            self.skipped_sessions = None

        # 4. Detect rest days and cancelled sessions from planning
        rest_days, cancelled_sessions = self._detect_rest_and_cancelled_sessions()

        # 5. Filter out already documented rest/cancelled sessions
        rest_days = self._filter_documented_sessions(rest_days, state, "rest")
        cancelled_sessions = self._filter_documented_sessions(
            cancelled_sessions, state, "cancelled"
        )

        # Prepare gaps data
        gaps_data = {
            "unanalyzed": self.unanalyzed_activities or [],
            "skipped": self.skipped_sessions or [],
            "rest_days": rest_days,
            "cancelled": cancelled_sessions,
        }

        # 6. Display unified summary
        total_gaps = self._display_gaps_summary(gaps_data)

        if total_gaps == 0:
            self.wait_user()
            return "exit", gaps_data

        # 7. Prompt user for action choice
        action = self._prompt_user_choice(gaps_data)

        return action, gaps_data
