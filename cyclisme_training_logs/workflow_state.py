#!/usr/bin/env python3
"""
workflow_state.py - Gestion de l'état du workflow d'analyse

Ce module permet de tracker :
- La dernière activité analysée
- Les activités non analysées (gap detection)
- Le nombre total d'analyses effectuées

Usage:
    from workflow_state import WorkflowState

    state = WorkflowState()
    state.mark_analyzed('i107779437')

    unanalyzed = state.get_unanalyzed_activities(all_activities)
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict


class WorkflowState:
    """Gestion de l'état du workflow d'analyse"""

    STATE_FILE = Path(".workflow_state.json")

    def __init__(self, project_root: Path = None):
        """
        Initialiser le gestionnaire d'état

        Args:
            project_root: Racine du projet (défaut: répertoire courant)
        """
        self.project_root = project_root or Path.cwd()
        self.state_file = self.project_root / self.STATE_FILE
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """Charger l'état depuis le fichier JSON"""
        if not self.state_file.exists():
            return {
                "last_analyzed_activity_id": None,
                "last_analyzed_date": None,
                "total_analyses": 0,
                "history": []
            }

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Erreur lecture state file: {e}")
            return {
                "last_analyzed_activity_id": None,
                "last_analyzed_date": None,
                "total_analyses": 0,
                "history": []
            }

    def _save_state(self):
        """Sauvegarder l'état dans le fichier JSON"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"⚠️  Erreur sauvegarde state file: {e}")

    def mark_analyzed(self, activity_id: str, activity_date: str = None):
        """
        Marquer une activité comme analysée

        Args:
            activity_id: ID de l'activité analysée
            activity_date: Date de l'activité (ISO format)
        """
        self.state["last_analyzed_activity_id"] = activity_id
        self.state["last_analyzed_date"] = datetime.now().isoformat()
        self.state["total_analyses"] = self.state.get("total_analyses", 0) + 1

        # Ajouter à l'historique (garder les 50 dernières)
        history = self.state.get("history", [])
        history.append({
            "activity_id": activity_id,
            "activity_date": activity_date,
            "analyzed_at": datetime.now().isoformat()
        })
        self.state["history"] = history[-50:]  # Garder seulement les 50 dernières

        self._save_state()

    def get_last_analyzed_id(self) -> Optional[str]:
        """Récupérer l'ID de la dernière activité analysée"""
        return self.state.get("last_analyzed_activity_id")

    @staticmethod
    def is_valid_activity(activity: Dict) -> bool:
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
        moving_time = activity.get('moving_time', 0)
        if moving_time < 120:  # 120 secondes = 2 minutes
            return False

        # Ignorer activités sans charge d'entraînement (TSS = 0)
        training_load = activity.get('icu_training_load', 0)
        if training_load == 0:
            return False

        # Ignorer activités sans données de puissance
        average_watts = activity.get('average_watts')
        if average_watts is None:
            return False

        return True

    def get_unanalyzed_activities(self, all_activities: List[Dict]) -> List[Dict]:
        """
        Détecter les activités non analysées

        Args:
            all_activities: Liste de toutes les activités récentes (triées par date décroissante)

        Returns:
            Liste des activités non analysées (filtrées pour exclure activités invalides)
        """
        unanalyzed = []
        filtered_count = 0

        for activity in all_activities:
            activity_id = activity.get('id')

            # Filtrer activités invalides (fantômes)
            if not self.is_valid_activity(activity):
                filtered_count += 1
                # Debug info pour activités filtrées
                name = activity.get('name', 'N/A')
                duration_min = activity.get('moving_time', 0) // 60
                tss = activity.get('icu_training_load', 0)
                # Note: Info silencieuse - pas d'affichage pour ne pas polluer l'output
                continue

            # Vérifier dans l'historique si cette activité a déjà été analysée
            if not self.is_activity_analyzed(activity_id):
                unanalyzed.append(activity)

        # Info si des activités ont été filtrées (optionnel)
        if filtered_count > 0:
            pass  # Peut être activé plus tard si nécessaire pour debug

        return unanalyzed

    def get_stats(self) -> Dict:
        """Récupérer les statistiques du workflow"""
        return {
            "total_analyses": self.state.get("total_analyses", 0),
            "last_analyzed_id": self.state.get("last_analyzed_activity_id"),
            "last_analyzed_date": self.state.get("last_analyzed_date"),
            "history_count": len(self.state.get("history", []))
        }

    def is_activity_analyzed(self, activity_id: str) -> bool:
        """Vérifier si une activité a déjà été analysée"""
        # Vérifier dans l'historique
        history = self.state.get("history", [])
        return any(h["activity_id"] == activity_id for h in history)

    def reset(self):
        """Réinitialiser l'état (debug/test)"""
        self.state = {
            "last_analyzed_activity_id": None,
            "last_analyzed_date": None,
            "total_analyses": 0,
            "history": []
        }
        self._save_state()


def main():
    """Test du module"""
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
    if input("Marquer une activité test ? (o/n) : ").lower() == 'o':
        activity_id = input("ID activité : ")
        state.mark_analyzed(activity_id, datetime.now().isoformat())
        print("✅ Activité marquée comme analysée")
        print()
        print("Nouvel état:")
        print(json.dumps(state.state, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
