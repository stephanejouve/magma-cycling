"""Output methods for WeeklyPlanner."""

import subprocess
import sys
from datetime import UTC, datetime, timedelta

from pydantic import ValidationError

from magma_cycling.planning.control_tower import planning_tower
from magma_cycling.planning.models import WeeklyPlan


class OutputMixin:
    """Clipboard, session status updates, and JSON persistence."""

    def copy_to_clipboard(self, text: str) -> bool:
        """Copy le texte dans le presse-papier (macOS)."""
        try:
            subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
            return True
        except Exception as e:
            print(f"⚠️ Erreur copie presse-papier : {e}", file=sys.stderr)
            return False

    def update_session_status(self, session_id: str, status: str, reason: str | None = None):
        """Update le statut d'une séance dans le JSON avec protection Pydantic.

        Args:
            session_id: ID de la séance (ex: S074-01)
            status: Nouveau statut (completed, cancelled, skipped, etc.)
            reason: Raison de l'annulation/modification (optionnel).

        Returns:
            bool: True si succès, False si erreur

        Note:
            Migré vers Control Tower (2026-02-20).
            Utilise planning_tower.modify_week() pour backup + audit automatiques.
        """
        try:
            # 🚦 MODIFY VIA CONTROL TOWER (automatic backup + audit)
            with planning_tower.modify_week(
                self.week_number,
                requesting_script="weekly-planner",
                reason=f"Update session {session_id} to {status}: {reason or 'N/A'}",
            ) as plan:
                # Trouver et mettre à jour la séance
                session_found = False
                for session in plan.planned_sessions:
                    if session.session_id == session_id:
                        # ✅ Validation automatique par Pydantic (validate_assignment=True)
                        try:
                            # IMPORTANT: Définir skip_reason AVANT de changer le statut
                            # (validator Pydantic vérifie que skip_reason est présent pour skipped/cancelled/replaced)
                            if reason and status in ("skipped", "cancelled", "replaced"):
                                session.skip_reason = reason  # Défini AVANT statut

                            session.status = status  # Type-checked et validé!

                        except ValidationError as e:
                            print(f"⚠️ Valeur invalide pour le statut : {e}", file=sys.stderr)
                            return False

                        session_found = True
                        break

                if not session_found:
                    print(f"⚠️ Séance {session_id} non trouvée dans le planning", file=sys.stderr)
                    return False

                # Auto-saved by Control Tower with backup + audit log

            print(f"✅ Séance {session_id} mise à jour : {status}", file=sys.stderr)
            if reason:
                print(f"   Raison : {reason}", file=sys.stderr)

            return True

        except FileNotFoundError:
            print(f"⚠️ Planning JSON non trouvé pour {self.week_number}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"⚠️ Erreur mise à jour planning : {e}", file=sys.stderr)
            return False

    def save_planning_json(self, workouts_data: list | None = None):
        """Backup le planning au format JSON.

        Args:
            workouts_data: Liste des workouts générés (optionnel, créera template si None).

        Note:
            Migré vers Control Tower (2026-02-20).
            Crée un nouveau planning via WeeklyPlan.to_json() avec audit log.
        """
        # Si pas de workouts fournis, créer template basique
        if workouts_data is None:
            workouts_data = []
            for day in range(7):
                date = self.start_date + timedelta(days=day)
                session_num = day + 1
                workouts_data.append(
                    {
                        "session_id": f"{self.week_number}-{session_num:02d}",
                        "date": date.strftime("%Y-%m-%d"),
                        "name": f"Session{session_num}",
                        "type": "END",  # Default type
                        "version": "V001",
                        "tss_planned": 0,
                        "duration_min": 0,
                        "description": "À définir",
                        "status": "planned",
                    }
                )

        # Get athlete_id from config
        from magma_cycling.config import get_intervals_config

        intervals_config = get_intervals_config()

        planning_dict = {
            "week_id": self.week_number,
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "end_date": self.end_date.strftime("%Y-%m-%d"),
            "created_at": datetime.now(UTC).isoformat(),
            "last_updated": datetime.now(UTC).isoformat(),
            "version": 1,
            "athlete_id": intervals_config.athlete_id,
            "tss_target": sum(w.get("tss_planned", 0) for w in workouts_data),
            "source": "planner",
            "planned_sessions": workouts_data,
        }

        # ✅ Créer WeeklyPlan via Pydantic pour validation
        plan = WeeklyPlan(**planning_dict)

        # Sauvegarder via Pydantic
        json_file = self.planning_dir / f"week_planning_{self.week_number}.json"
        plan.to_json(json_file)

        # 📋 LOG TO AUDIT (création de planning)
        from magma_cycling.planning.audit_log import (
            OperationStatus,
            OperationType,
            audit_log,
        )

        audit_log.log_operation(
            operation=OperationType.CREATE,
            week_id=self.week_number,
            status=OperationStatus.SUCCESS,
            tool="weekly-planner",
            description=f"Created planning for {self.week_number}",
            reason="New week planning template created",
            files_modified=[f"week_planning_{self.week_number}.json"],
            file_timestamp=planning_dict["created_at"],
        )

        print(f"\n📄 Planning JSON sauvegardé : {json_file}", file=sys.stderr)
        return json_file
