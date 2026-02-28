"""Intervals.icu API interaction methods for WorkflowCoach."""

import json
import logging
from datetime import datetime

from magma_cycling.planning.control_tower import planning_tower

logger = logging.getLogger(__name__)


class IntervalsAPIMixin:
    """Methods for interacting with Intervals.icu API."""

    def load_credentials(self):
        """Load credentials Intervals.icu de manière robuste.

        Uses centralized config loading (Sprint R9.B - DRY).
        Tries .intervals_config.json first (backward compatibility),
        then environment variables.
        """
        from magma_cycling.config import get_intervals_config, load_json_config

        # Try .intervals_config.json first (backward compatibility)
        config_file = load_json_config("~/.intervals_config.json")
        if config_file:
            athlete_id = config_file.get("athlete_id")
            api_key = config_file.get("api_key")
            if athlete_id and api_key:
                return athlete_id, api_key

        # Fallback to environment variables via centralized config
        intervals_config = get_intervals_config()
        if intervals_config.is_configured():
            return intervals_config.athlete_id, intervals_config.api_key

        return None, None

    def _get_api(self):
        """Get or create Intervals.icu API client (lazy initialization).

        Returns:
            IntervalsClient: Configured API client

        Raises:
            ValueError: If credentials not configured
        """
        if self.api is None:
            from magma_cycling.config import create_intervals_client

            try:
                self.api = create_intervals_client()
            except ValueError as e:
                print(f"❌ {e}")
                raise

        return self.api

    def load_workout_templates(self):
        """Charge catalogue templates au démarrage.

        Returns:
            dict: Templates indexés par ID (ex: {"recovery_active_30tss": {...}})
        """
        templates = {}

        templates_dir = self.project_root / "data" / "workout_templates"

        if not templates_dir.exists():
            print("⚠️  Dossier workout_templates absent")
            print(f"   Chemin: {templates_dir}")
            return templates

        try:
            for template_file in templates_dir.glob("*.json"):
                with open(template_file, encoding="utf-8") as f:
                    template = json.load(f)
                    templates[template["id"]] = template

            if templates:
                print(f"✅ {len(templates)} templates chargés")
            else:
                print("⚠️  Aucun template trouvé dans workout_templates/")

        except Exception as e:
            print(f"⚠️  Erreur chargement templates : {e}")

        return templates

    def load_remaining_sessions(self, week_id: str) -> list:
        """Charge séances planifiées futures de la semaine.

        Args:
            week_id: ID semaine (ex: "S072")

        Returns:
            list: Séances futures (date >= aujourd'hui)
        """
        try:
            # 🚦 READ-ONLY ACCESS via Control Tower
            plan = planning_tower.read_week(week_id)

            today = datetime.now().date()

            remaining = []
            # Convert Session objects to dict for backward compatibility
            for session in plan.planned_sessions:
                session_date = session.session_date
                if session_date >= today:
                    # Convert Session to dict
                    remaining.append(
                        {
                            "session_id": session.session_id,
                            "date": str(session.session_date),
                            "name": session.name,
                            "type": session.session_type,
                            "version": session.version,
                            "tss_planned": session.tss_planned,
                            "duration_min": session.duration_min,
                            "description": session.description,
                            "status": session.status,
                        }
                    )

            return remaining

        except FileNotFoundError:
            print(f"⚠️  Planning {week_id} non trouvé")
            return []
        except Exception as e:
            print(f"⚠️  Erreur lecture planning : {e}")
            return []

    def _get_workout_id_intervals(self, date: str):
        """Récupère ID workout Intervals.icu pour une date.

        Args:
            date: Date YYYY-MM-DD

        Returns:
            str: ID workout ou None.
        """
        try:
            # Get API client (centralized, Sprint R9.B Phase 2)
            api = self._get_api()

            # Get events for the date
            events = api.get_events(oldest=date, newest=date)

            # Filter for WORKOUT category
            for event in events:
                if event.get("category") == "WORKOUT":
                    return event.get("id")

            return None

        except Exception as e:
            print(f"⚠️  Erreur get_workout_id : {e}")
            return None

    def _delete_workout_intervals(self, workout_id: str) -> bool:
        """Supprime workout Intervals.icu.

        Args:
            workout_id: ID workout à supprimer

        Returns:
            bool: True si succès.
        """
        try:
            # Get API client (centralized, Sprint R9.B Phase 2)
            api = self._get_api()

            # DELETE request
            url = f"{api.BASE_URL}/athlete/{api.athlete_id}/events/{workout_id}"
            response = api.session.delete(url)
            response.raise_for_status()

            return True

        except Exception as e:
            print(f"⚠️  Erreur suppression workout : {e}")
            return False

    def _upload_workout_intervals(self, date: str, code: str, structure: str) -> bool:
        """Upload nouveau workout Intervals.icu.

        Args:
            date: Date YYYY-MM-DD
            code: Workout code (ex: S072-03-REC-V001)
            structure: Format texte Intervals.icu

        Returns:
            bool: True si succès.
        """
        try:
            # Get API client (centralized, Sprint R9.B Phase 2)
            api = self._get_api()

            # Prepare event data
            event = {
                "category": "WORKOUT",
                "type": "VirtualRide",  # Required by Intervals.icu API
                "start_date_local": f"{date}T06:00:00",
                "name": code,
                "description": structure,  # Format Intervals.icu (corrigé P0 #6)
            }

            # Create event using existing method
            result = api.create_event(event)

            return result is not None

        except Exception as e:
            print(f"⚠️  Erreur upload workout : {e}")
            return False
