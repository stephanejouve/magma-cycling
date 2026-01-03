#!/usr/bin/env python3
"""
Workflow state management and persistence.
Gestion état workflow persistant entre exécutions. Tracking étapes
complétées, prévention duplicates, et validation cohérence pipeline
d'analyse quotidien.

Examples:
    Load workflow state::

        from cyclisme_training_logs.workflow_state import WorkflowState

        # Charger état
        state = WorkflowState.load()

        # Vérifier étapes complétées
        if state.is_completed('fetch_activity'):
            print("Activity already fetched")

    Update state::

        # Marquer étape complétée
        state.mark_completed(
            step='generate_analysis',
            metadata={'activity_id': 'i123456'}
        )

        # Persister
        state.save()

    Reset for new day::

        # Reset état pour nouveau jour
        state.reset()
        state.save()

Author: Stéphane Jouve
Created: 2024-09-XX
Updated: 2025-12-26 (Standardization Prompt 3 Priority 2)

Metadata:
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: I
    Status: Production
    Priority: P1
    Version: v2
"""

import json
from datetime import datetime
from pathlib import Path

from cyclisme_training_logs.config import get_data_config


class WorkflowState:
    """Gestion de l'état du workflow d'analyse"""

    STATE_FILE = Path(".workflow_state.json")

    def __init__(self, project_root: Path | None = None):
        """
        Initialiser le gestionnaire d'état

        Args:
            project_root: Racine du projet (legacy, use data repo config instead).
        """
        # Use data repo config if available, fallback to project_root
        if project_root is None:
            try:
                config = get_data_config()
                self.state_file = config.workflow_state_path
            except FileNotFoundError:
                # Fallback to current directory (legacy behavior)
                self.project_root = Path.cwd()
                self.state_file = self.project_root / self.STATE_FILE
        else:
            # Legacy: explicit project_root provided (mainly for tests)
            self.project_root = project_root
            self.state_file = self.project_root / self.STATE_FILE

        self.state = self._load_state()

    def _load_state(self) -> dict:
        """Charger l'état depuis le fichier JSON."""
        if not self.state_file.exists():
            return {
                "last_analyzed_activity_id": None,
                "last_analyzed_date": None,
                "total_analyses": 0,
                "history": [],
            }

        try:
            with open(self.state_file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"⚠️  Erreur lecture state file: {e}")
            return {
                "last_analyzed_activity_id": None,
                "last_analyzed_date": None,
                "total_analyses": 0,
                "history": [],
            }

    def _save_state(self):
        """Sauvegarder l'état dans le fichier JSON."""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"⚠️  Erreur sauvegarde state file: {e}")

    def mark_analyzed(self, activity_id: str, activity_date: str | None = None):
        """
        Marquer une activité comme analysée

        Args:
            activity_id: ID de l'activité analysée
            activity_date: Date de l'activité (ISO format).
        """
        self.state["last_analyzed_activity_id"] = activity_id
        self.state["last_analyzed_date"] = datetime.now().isoformat()
        self.state["total_analyses"] = self.state.get("total_analyses", 0) + 1

        # Ajouter à l'historique (garder les 50 dernières)
        history = self.state.get("history", [])
        history.append(
            {
                "activity_id": activity_id,
                "activity_date": activity_date,
                "analyzed_at": datetime.now().isoformat(),
            }
        )
        self.state["history"] = history[-50:]  # Garder seulement les 50 dernières

        self._save_state()

    def get_last_analyzed_id(self) -> str | None:
        """Récupérer l'ID de la dernière activité analysée."""
        return self.state.get("last_analyzed_activity_id")

    @staticmethod
    def is_valid_activity(activity: dict) -> bool:
        """
        Filtre activités valides pour analyse

        Ignore les activités "fantômes" :
        - Durée < 2 minutes
        - TSS = 0
        - Pas de données de puissance

        Args:
            activity: Activité Intervals.icu

        Returns:
            True si activité valide pour analyse
        """
        # Ignorer activités trop courtes (< 2 minutes)
        moving_time = activity.get("moving_time", 0)
        if moving_time < 120:  # 120 secondes = 2 minutes
            return False

        # Ignorer activités sans charge d'entraînement (TSS = 0)
        training_load = activity.get("icu_training_load", 0)
        if training_load == 0:
            return False

        # Ignorer activités sans données de puissance
        # Vérifier icu_average_watts (Intervals.icu) OU average_watts (legacy)
        average_watts = activity.get("icu_average_watts") or activity.get("average_watts")
        if average_watts is None or average_watts == 0:
            return False

        return True

    def get_unanalyzed_activities(self, all_activities: list[dict]) -> list[dict]:
        """
        Détecter les activités non analysées

        Args:
            all_activities: Liste de toutes les activités récentes (triées par date décroissante)

        Returns:
            Liste des activités non analysées (filtrées pour exclure activités invalides).
        """
        unanalyzed = []
        filtered_count = 0

        for activity in all_activities:
            activity_id = activity.get("id")

            # Filtrer activités invalides (fantômes)
            if not self.is_valid_activity(activity):
                filtered_count += 1
                # Debug info pour activités filtrées
                activity.get("name", "N/A")
                activity.get("moving_time", 0) // 60
                activity.get("icu_training_load", 0)
                # Note: Info silencieuse - pas d'affichage pour ne pas polluer l'output
                continue

            # Skip if activity_id is None
            if activity_id is None:
                continue

            # Vérifier dans l'historique si cette activité a déjà été analysée
            if not self.is_activity_analyzed(str(activity_id)):
                unanalyzed.append(activity)

        # Info si des activités ont été filtrées (optionnel)
        if filtered_count > 0:
            pass  # Peut être activé plus tard si nécessaire pour debug

        return unanalyzed

    def get_stats(self) -> dict:
        """Récupérer les statistiques du workflow."""
        return {
            "total_analyses": self.state.get("total_analyses", 0),
            "last_analyzed_id": self.state.get("last_analyzed_activity_id"),
            "last_analyzed_date": self.state.get("last_analyzed_date"),
            "history_count": len(self.state.get("history", [])),
        }

    def is_activity_analyzed(self, activity_id: str) -> bool:
        """Vérifier si une activité a déjà été analysée."""
        # Vérifier dans l'historique
        history = self.state.get("history", [])
        return any(h["activity_id"] == activity_id for h in history)

    # === TRACKING SESSIONS SPÉCIALES (PHASE 4) ===

    def mark_special_session_documented(self, session_id: str, session_type: str, date: str):
        """Marquer une session spéciale comme documentée.

        Args:
            session_id: ID session (ex: S072-07)
            session_type: Type ("rest", "cancelled", "skipped")
            date: Date session (YYYY-MM-DD)
        """
        if "documented_specials" not in self.state:
            self.state["documented_specials"] = {}

        key = f"{session_id}_{date}"
        self.state["documented_specials"][key] = {
            "session_id": session_id,
            "type": session_type,
            "date": date,
            "documented_at": datetime.now().isoformat(),
        }
        self._save_state()

    def is_special_session_documented(self, session_id: str, date: str) -> bool:
        """Vérifier si session spéciale déjà documentée.

        Args:
            session_id: ID session (ex: S072-07)
            date: Date session (YYYY-MM-DD)

        Returns:
            True si déjà documentée, False sinon.
        """
        if not session_id or not date:
            return False

        key = f"{session_id}_{date}"
        return key in self.state.get("documented_specials", {})

    def get_documented_specials(self) -> dict:
        """Récupérer toutes les sessions spéciales documentées.

        Returns:
            Dict avec clés session_id_date et valeurs metadata.
        """
        return self.state.get("documented_specials", {})

    # === PERSISTENCE FEEDBACK ATHLÈTE (PHASE 4) ===

    def save_session_feedback(self, activity_id: str, feedback: dict):
        """Sauvegarder feedback athlète pour une session.

        Args:
            activity_id: ID activité Intervals.icu
            feedback: Dict avec keys 'rpe', 'comments', 'sleep_quality', etc.
        """
        if "feedbacks" not in self.state:
            self.state["feedbacks"] = {}

        self.state["feedbacks"][activity_id] = {
            "feedback": feedback,
            "timestamp": datetime.now().isoformat(),
        }
        self._save_state()

    def get_session_feedback(self, activity_id: str) -> dict | None:
        """Récupérer feedback existant pour une session.

        Args:
            activity_id: ID activité Intervals.icu

        Returns:
            Dict avec 'feedback' et 'timestamp' ou None si absent.
        """
        feedbacks = self.state.get("feedbacks", {})
        return feedbacks.get(activity_id)

    def has_session_feedback(self, activity_id: str) -> bool:
        """Vérifier si feedback existe pour cette session.

        Args:
            activity_id: ID activité Intervals.icu

        Returns:
            True si feedback existe, False sinon.
        """
        return activity_id in self.state.get("feedbacks", {})

    def reset(self):
        """Réinitialiser l'état (debug/test)."""
        self.state = {
            "last_analyzed_activity_id": None,
            "last_analyzed_date": None,
            "total_analyses": 0,
            "history": [],
        }
        self._save_state()


def main():
    """Test du module."""
    state = WorkflowState()

    print("📊 État actuel du workflow:")
    print()
    stats = state.get_stats()
    print(f"Total analyses : {stats['total_analyses']}")
    print(f"Dernière analysée : {stats['last_analyzed_id']}")
    print(f"Date dernière analyse : {stats['last_analyzed_date']}")
    print(f"Entrées historique : {stats['history_count']}")
    print()

    # Test: marquer une activité
    if input("Marquer une activité test ? (o/n) : ").lower() == "o":
        activity_id = input("ID activité : ")
        state.mark_analyzed(activity_id, datetime.now().isoformat())
        print("✅ Activité marquée comme analysée")
        print()
        print("Nouvel état:")
        print(json.dumps(state.state, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
