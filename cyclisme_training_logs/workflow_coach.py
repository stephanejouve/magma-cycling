#!/usr/bin/env python3
"""
workflow_coach.py - Orchestrateur du workflow d'analyse de séance

Ce script guide l'utilisateur à travers tout le processus d'analyse :
1. Détection du type de session Claude (nouveau/existant/projet)
2. Guidage pour l'initialisation du contexte si nécessaire
3. Collecte optionnelle du feedback athlète
4. Préparation du prompt d'analyse
5. Instructions pour Claude.ai
6. Validation de la réponse
7. Insertion de l'analyse
8. Commit git optionnel

Usage:
    python3 cyclisme_training_logs/workflow_coach.py [--skip-feedback] [--skip-git]
    python3 cyclisme_training_logs/workflow_coach.py --activity-id i123456
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import json
import requests
from cyclisme_training_logs.workflow_state import WorkflowState
from cyclisme_training_logs.rest_and_cancellations import (
    load_week_planning,
    validate_week_planning,
    generate_rest_day_entry,
    generate_cancelled_session_entry,
    reconcile_planned_vs_actual
)
from cyclisme_training_logs.planned_sessions_checker import PlannedSessionsChecker


class WorkflowCoach:
    """Orchestrateur du workflow d'analyse de séance"""

    def __init__(self, skip_feedback=False, skip_git=False, activity_id=None, week_id=None, servo_mode=False):
        self.skip_feedback = skip_feedback
        self.skip_git = skip_git
        self.activity_id = activity_id
        self.week_id = week_id
        self.servo_mode = servo_mode
        self.project_root = Path.cwd()
        self.scripts_dir = self.project_root / "cyclisme_training_logs"
        self.activity_name = None
        # Nouveaux attributs pour gestion planning
        self.planning = None
        self.reconciliation = None
        self.planning_mode = False
        # Gaps détectés par step_1b
        self.unanalyzed_activities = None
        # Séances planifiées sautées
        self.skipped_sessions = None
        # Servo control attributes
        self.workout_templates = {}

        # Load workout templates if servo mode enabled
        if self.servo_mode:
            self.workout_templates = self.load_workout_templates()

    def load_credentials(self):
        """Charger credentials Intervals.icu de manière robuste"""
        import os
        import json
        from pathlib import Path

        config_path = Path.home() / ".intervals_config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    athlete_id = config.get('athlete_id')
                    api_key = config.get('api_key')
                    if athlete_id and api_key:
                        return athlete_id, api_key
            except Exception as e:
                print(f"⚠️  Erreur config : {e}")

        athlete_id = os.getenv('VITE_INTERVALS_ATHLETE_ID')
        api_key = os.getenv('VITE_INTERVALS_API_KEY')
        if athlete_id and api_key:
            return athlete_id, api_key

        return None, None

    def load_workout_templates(self):
        """Charge catalogue templates au démarrage

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
                with open(template_file, 'r', encoding='utf-8') as f:
                    template = json.load(f)
                    templates[template['id']] = template

            if templates:
                print(f"✅ {len(templates)} templates chargés")
            else:
                print("⚠️  Aucun template trouvé dans workout_templates/")

        except Exception as e:
            print(f"⚠️  Erreur chargement templates : {e}")

        return templates

    def load_remaining_sessions(self, week_id: str) -> list:
        """Charge séances planifiées futures de la semaine

        Args:
            week_id: ID semaine (ex: "S072")

        Returns:
            list: Séances futures (date >= aujourd'hui)
        """
        planning_file = self.project_root / "data" / "week_planning" / f"week_planning_{week_id}.json"

        if not planning_file.exists():
            print(f"⚠️  Planning {week_id} non trouvé: {planning_file}")
            return []

        try:
            with open(planning_file, 'r', encoding='utf-8') as f:
                planning = json.load(f)

            today = datetime.now().date()

            remaining = []
            for session in planning.get('planned_sessions', []):
                session_date = datetime.strptime(session['date'], '%Y-%m-%d').date()
                if session_date >= today:
                    remaining.append(session)

            return remaining

        except Exception as e:
            print(f"⚠️  Erreur lecture planning : {e}")
            return []

    def format_remaining_sessions_compact(self, remaining_sessions: list) -> str:
        """Format compact planning pour prompt AI (cible ~150 tokens)

        Args:
            remaining_sessions: Liste de sessions futures

        Returns:
            str: Planning formaté pour inclusion dans prompt
        """
        if not remaining_sessions:
            return ""

        lines = [f"\n## PLANNING RESTANT ({len(remaining_sessions)} séances)\n"]

        for session in remaining_sessions:
            date = session['date']
            session_id = session['session_id']
            name = session['name']
            workout_type = session['type']
            tss = session.get('tss_planned', 0)

            # Construct workout code
            workout_code = f"{session_id}-{workout_type}-{name}-{session.get('version', 'V001')}"

            if session.get('status') == 'rest_day':
                lines.append(f"{date}: REPOS")
            else:
                lines.append(f"{date}: {workout_code} ({tss} TSS)")

        return "\n".join(lines)

    def parse_ai_modifications(self, ai_response: str) -> list:
        """Parse modifications planning depuis réponse AI

        Args:
            ai_response: Texte réponse AI complet

        Returns:
            list: Modifications à appliquer (vide si aucune)
        """
        import re

        # Chercher bloc JSON modifications
        json_match = re.search(
            r'```json\s*\n(\{.*?"modifications".*?\})\s*\n```',
            ai_response,
            re.DOTALL
        )

        if not json_match:
            return []  # Pas de modification = comportement normal

        try:
            data = json.loads(json_match.group(1))
            return data.get('modifications', [])
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON modifications invalide : {e}")
            return []

    def _extract_day_number(self, date_str: str, week_id: str) -> int:
        """Extrait numéro jour (1-7) depuis date

        Args:
            date_str: "2025-12-18"
            week_id: "S072"

        Returns:
            int: Numéro jour 1-7
        """
        planning_file = self.project_root / "data" / "week_planning" / f"week_planning_{week_id}.json"

        try:
            with open(planning_file, 'r', encoding='utf-8') as f:
                planning = json.load(f)

            start_date = datetime.strptime(planning['start_date'], '%Y-%m-%d').date()
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()

            delta = (target_date - start_date).days
            return delta + 1  # Jour 1-7

        except Exception as e:
            print(f"⚠️  Erreur extraction day_number : {e}")
            return 1  # Fallback

    def _get_workout_id_intervals(self, date: str):
        """Récupère ID workout Intervals.icu pour une date

        Args:
            date: Date YYYY-MM-DD

        Returns:
            str: ID workout ou None
        """
        try:
            # Import IntervalsAPI from prepare_analysis
            from cyclisme_training_logs.prepare_analysis import IntervalsAPI

            # Load credentials
            athlete_id, api_key = self.load_credentials()
            if not athlete_id or not api_key:
                print("⚠️  Credentials non disponibles")
                return None

            # Create API client
            api = IntervalsAPI(athlete_id=athlete_id, api_key=api_key)

            # Get events for the date
            events = api.get_events(oldest=date, newest=date)

            # Filter for WORKOUT category
            for event in events:
                if event.get('category') == 'WORKOUT':
                    return event.get('id')

            return None

        except Exception as e:
            print(f"⚠️  Erreur get_workout_id : {e}")
            return None

    def _delete_workout_intervals(self, workout_id: str) -> bool:
        """Supprime workout Intervals.icu

        Args:
            workout_id: ID workout à supprimer

        Returns:
            bool: True si succès
        """
        try:
            # Import IntervalsAPI
            from cyclisme_training_logs.prepare_analysis import IntervalsAPI

            # Load credentials
            athlete_id, api_key = self.load_credentials()
            if not athlete_id or not api_key:
                return False

            # Create API client
            api = IntervalsAPI(athlete_id=athlete_id, api_key=api_key)

            # DELETE request
            url = f"{api.BASE_URL}/athlete/{athlete_id}/events/{workout_id}"
            response = api.session.delete(url)
            response.raise_for_status()

            return True

        except Exception as e:
            print(f"⚠️  Erreur suppression workout : {e}")
            return False

    def _upload_workout_intervals(self, date: str, code: str, structure: str) -> bool:
        """Upload nouveau workout Intervals.icu

        Args:
            date: Date YYYY-MM-DD
            code: Workout code (ex: S072-03-REC-V001)
            structure: Format texte Intervals.icu

        Returns:
            bool: True si succès
        """
        try:
            # Import IntervalsAPI
            from cyclisme_training_logs.prepare_analysis import IntervalsAPI

            # Load credentials
            athlete_id, api_key = self.load_credentials()
            if not athlete_id or not api_key:
                return False

            # Create API client
            api = IntervalsAPI(athlete_id=athlete_id, api_key=api_key)

            # Prepare event data
            event = {
                "category": "WORKOUT",
                "start_date_local": f"{date}T06:00:00",
                "name": code,
                "description": structure  # Format Intervals.icu (corrigé P0 #6)
            }

            # Create event using existing method
            result = api.create_event(event)

            return result is not None

        except Exception as e:
            print(f"⚠️  Erreur upload workout : {e}")
            return False

    def _update_planning_json(self, week_id: str, date: str, new_workout: dict, old_workout: str, reason: str) -> bool:
        """Met à jour week_planning_SXXX.json avec historique

        Args:
            week_id: ID semaine
            date: Date modification
            new_workout: Dict nouveau workout (code, type, tss, description)
            old_workout: Code workout remplacé
            reason: Raison modification

        Returns:
            bool: True si succès
        """
        planning_file = self.project_root / "data" / "week_planning" / f"week_planning_{week_id}.json"

        try:
            # Load planning
            with open(planning_file, 'r', encoding='utf-8') as f:
                planning = json.load(f)

            # Find session to modify
            for i, session in enumerate(planning['planned_sessions']):
                if session['date'] == date:
                    # Save to history
                    timestamp = datetime.now().isoformat()

                    history_entry = {
                        "timestamp": timestamp,
                        "action": "modified_by_ai_coach",
                        "previous_workout": old_workout,
                        "previous_tss": session['tss_planned'],
                        "new_workout": new_workout['code'],
                        "new_tss": new_workout['tss'],
                        "reason": reason
                    }

                    # Update session
                    planning['planned_sessions'][i].update({
                        "session_id": new_workout.get('session_id', session['session_id']),
                        "name": new_workout.get('name', session['name']),
                        "type": new_workout['type'],
                        "tss_planned": new_workout['tss'],
                        "description": new_workout['description'],
                        "status": "modified"
                    })

                    if 'history' not in planning['planned_sessions'][i]:
                        planning['planned_sessions'][i]['history'] = []
                    planning['planned_sessions'][i]['history'].append(history_entry)

                    break

            # Update metadata
            planning['last_updated'] = datetime.now().isoformat()
            planning['version'] = planning.get('version', 1) + 1

            # Save
            with open(planning_file, 'w', encoding='utf-8') as f:
                json.dump(planning, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"⚠️  Erreur mise à jour planning : {e}")
            return False

    def _apply_lighten(self, mod: dict, week_id: str):
        """Applique allégement séance via template

        Args:
            mod: Modification dict avec template_id
            week_id: ID semaine
        """
        template_id = mod['template_id']

        if template_id not in self.workout_templates:
            print(f"❌ Template inconnu: {template_id}")
            return

        template = self.workout_templates[template_id]

        print(f"\n🔄 Allégement via '{template['name']}'")
        print(f"   Date : {mod['target_date']}")
        print(f"   {template['tss']} TSS, {template['duration_minutes']}min")
        print(f"   Raison : {mod['reason']}")

        # Confirmation utilisateur (CRITIQUE)
        confirm = input("   Appliquer ? (o/n) : ").strip().lower()
        if confirm != 'o':
            print("   ❌ Ignoré")
            return

        # 1. Générer workout code depuis template
        day_num = self._extract_day_number(mod['target_date'], week_id)
        workout_code = template['workout_code_pattern'].format(
            week_id=week_id,
            day_num=day_num
        )

        # 2. Supprimer ancien workout Intervals.icu
        old_workout_id = self._get_workout_id_intervals(mod['target_date'])
        if old_workout_id:
            if self._delete_workout_intervals(old_workout_id):
                print("   🗑️  Ancien workout supprimé")
            else:
                print("   ⚠️  Échec suppression ancien workout")

        # 3. Upload nouveau workout
        if self._upload_workout_intervals(
            date=mod['target_date'],
            code=workout_code,
            structure=template['intervals_icu_format']
        ):
            print("   ⬆️  Nouveau workout uploadé")
        else:
            print("   ⚠️  Échec upload nouveau workout")
            return

        # 4. Mettre à jour planning JSON
        if self._update_planning_json(
            week_id=week_id,
            date=mod['target_date'],
            new_workout={
                'code': workout_code,
                'type': template['type'],
                'tss': template['tss'],
                'description': template['description']
            },
            old_workout=mod['current_workout'],
            reason=mod['reason']
        ):
            print("   📝 Planning JSON mis à jour")
            print("   ✅ Modification appliquée")
        else:
            print("   ⚠️  Échec mise à jour planning JSON")

    def apply_planning_modifications(self, modifications: list, week_id: str):
        """Applique modifications planning

        Args:
            modifications: Liste modifications AI
            week_id: ID semaine
        """
        if not modifications:
            print("\n✅ Planning maintenu tel quel")
            return

        print(f"\n📋 {len(modifications)} modification(s) détectée(s)")

        for mod in modifications:
            action = mod.get('action', 'unknown')

            if action == 'lighten':
                self._apply_lighten(mod, week_id)
            elif action == 'cancel':
                # TODO: Implémenter cancel si nécessaire
                print(f"⚠️  Action 'cancel' non implémentée: {mod}")
            elif action == 'reschedule':
                # TODO: Implémenter reschedule si nécessaire
                print(f"⚠️  Action 'reschedule' non implémentée: {mod}")
            else:
                print(f"⚠️  Action inconnue: {action}")

    def reconcile_week(self, week_id: str):
        """Mode réconciliation batch pour séances sautées/annulées

        Workflow:
        1. Charge planning JSON local
        2. Récupère activités réalisées depuis API
        3. Appelle reconcile_planned_vs_actual()
        4. Affiche séances à réconcilier
        5. Prompt utilisateur pour chaque séance
        6. Met à jour JSON avec historique
        7. Sauvegarde planning

        Args:
            week_id: ID semaine (ex: S070)
        """
        self.clear_screen()
        self.print_header(
            "🤖 WORKFLOW COACH AI - Réconciliation Batch",
            f"Semaine {week_id}"
        )

        # 0. Initialiser API
        from cyclisme_training_logs.prepare_analysis import IntervalsAPI

        athlete_id, api_key = self.load_credentials()
        if not athlete_id or not api_key:
            print("❌ Credentials Intervals.icu non trouvées")
            print("   Vérifier ~/.intervals_config.json ou variables d'environnement")
            return

        api = IntervalsAPI(athlete_id=athlete_id, api_key=api_key)

        # 1. Charger planning JSON local
        planning_dir = self.project_root / "data" / "week_planning"
        try:
            planning = load_week_planning(week_id, planning_dir)
            print(f"✅ Planning chargé: {week_id}")
            print(f"   Période: {planning['start_date']} → {planning['end_date']}")
            print(f"   Sessions: {len(planning['planned_sessions'])}")
        except FileNotFoundError:
            print(f"❌ Fichier planning non trouvé: week_planning_{week_id}.json")
            print(f"   Vérifier: {planning_dir}")
            return
        except Exception as e:
            print(f"❌ Erreur chargement planning: {e}")
            return

        # 2. Récupérer activités réalisées depuis API
        print(f"\n🔍 Récupération activités depuis Intervals.icu...")
        try:
            activities = api.get_activities(
                oldest=planning['start_date'],
                newest=planning['end_date']
            )
            print(f"✅ {len(activities)} activité(s) trouvée(s)")
        except Exception as e:
            print(f"❌ Erreur récupération activités: {e}")
            return

        # 3. Réconcilier planifié vs réalisé
        print(f"\n⚙️  Réconciliation en cours...")
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
        if reconciliation['skipped']:
            print(f"\n⏭️  SÉANCES SAUTÉES À TRAITER ({len(reconciliation['skipped'])})")
            print("=" * 70)

            for session in reconciliation['skipped']:
                print(f"\n📌 Séance: {session['session_id']}")
                print(f"   Date: {session['date']}")
                print(f"   Nom: {session.get('name', 'N/A')}")
                print(f"   Type: {session['type']}")
                print(f"   TSS planifié: {session.get('tss_planned', 0)}")

                # Vérifier si déjà marquée comme sautée
                if session.get('status') == 'skipped':
                    print(f"   ℹ️  Déjà marquée comme sautée")
                    skipped_count += 1
                    continue

                # Prompt utilisateur
                print(f"\n💡 Actions possibles:")
                print(f"   [1] Marquer comme sautée (oubli)")
                print(f"   [2] Marquer comme annulée (raison manuelle)")
                print(f"   [3] Ignorer (garder status actuel)")

                choice = input(f"\n   Choix (1-3): ").strip()

                if choice == '1':
                    reason = input(f"   Raison (optionnel): ").strip()
                    if not reason:
                        reason = "Séance sautée - réconciliation batch"

                    # Mettre à jour la session
                    session['status'] = 'skipped'
                    if 'history' not in session:
                        session['history'] = []
                    session['history'].append({
                        'timestamp': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                        'action': 'reconciled_skipped',
                        'reason': reason
                    })

                    # Supprimer le workout de Intervals.icu si présent (évite boucle infinie)
                    workout_id = self._get_workout_id_intervals(session['date'])
                    if workout_id:
                        print(f"   🗑️  Suppression workout Intervals.icu (ID: {workout_id})...")
                        if self._delete_workout_intervals(workout_id):
                            print(f"   ✅ Workout supprimé de l'API")
                        else:
                            print(f"   ⚠️  Échec suppression workout API")

                    updated_count += 1
                    print(f"   ✅ Marquée comme sautée")

                elif choice == '2':
                    reason = input(f"   Raison annulation: ").strip()
                    if not reason:
                        reason = "Séance annulée - réconciliation batch"

                    # Mettre à jour la session
                    session['status'] = 'cancelled'
                    session['cancellation_reason'] = reason
                    if 'history' not in session:
                        session['history'] = []
                    session['history'].append({
                        'timestamp': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                        'action': 'reconciled_cancelled',
                        'reason': reason
                    })
                    updated_count += 1
                    print(f"   ✅ Marquée comme annulée")

                else:
                    print(f"   ⏭️  Ignorée")

        # 6. Traiter séances annulées (déjà marquées comme cancelled)
        if reconciliation['cancelled']:
            print(f"\n\n❌ SÉANCES ANNULÉES ({len(reconciliation['cancelled'])})")
            print("=" * 70)

            for session in reconciliation['cancelled']:
                print(f"\n📌 Séance: {session['session_id']}")
                print(f"   Date: {session['date']}")
                print(f"   Nom: {session.get('name', 'N/A')}")
                print(f"   Raison: {session.get('cancellation_reason', 'Non spécifiée')}")
                print(f"   ℹ️  Déjà marquée comme annulée")

        # 7. Afficher repos planifiés (informatif)
        if reconciliation['rest_days']:
            print(f"\n\n💤 REPOS PLANIFIÉS ({len(reconciliation['rest_days'])})")
            print("=" * 70)

            for session in reconciliation['rest_days']:
                print(f"   • {session['date']}: {session.get('name', 'Repos')}")

        # 8. Sauvegarder planning mis à jour
        if updated_count > 0:
            print(f"\n\n💾 Sauvegarde planning mis à jour...")

            # Incrémenter version
            planning['version'] = planning.get('version', 1) + 1
            planning['last_updated'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

            # Sauvegarder
            planning_file = planning_dir / f"week_planning_{week_id}.json"
            try:
                with open(planning_file, 'w', encoding='utf-8') as f:
                    json.dump(planning, f, indent=2, ensure_ascii=False)
                print(f"✅ Planning sauvegardé: {planning_file.name}")
                print(f"   Version: {planning['version']}")
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
            print(f"💡 Prochaine étape: Committer les modifications")
            print(f"   git add {planning_file}")
            print(f"   git commit -m 'fix: Réconciliation {week_id}'")

    def clear_screen(self):
        """Nettoyer l'écran"""
        os.system('clear' if os.name == 'posix' else 'cls')

    def print_header(self, title, subtitle=None):
        """Afficher un header stylisé"""
        print("\n" + "=" * 70)
        print(f"  {title}")
        if subtitle:
            print(f"  {subtitle}")
        print("=" * 70 + "\n")

    def print_separator(self):
        """Afficher un séparateur"""
        print("\n" + "-" * 70 + "\n")

    def wait_user(self, message="Appuyer sur ENTRÉE pour continuer..."):
        """Attendre l'utilisateur"""
        input(f"\n{message}")

    def step_1_welcome(self):
        """Étape 1 : Message de bienvenue"""
        self.clear_screen()
        self.print_header(
            "🎯 WORKFLOW COACH - Analyse de Séance",
            "Orchestrateur intelligent pour l'analyse cyclisme"
        )

        print("Ce workflow va te guider à travers 6 étapes :")
        print()
        print("1. ✅ Bienvenue et présentation")
        print("2. 💭 Collecte feedback athlète (optionnel)")
        print("3. 📝 Préparation prompt d'analyse")
        print("4. 🤖 Envoi à Claude.ai")
        print("5. ✅ Validation de l'analyse")
        print("6. 💾 Insertion dans les logs")
        print("7. 💾 Commit git (optionnel)")
        print()
        print("⏱️  Temps total estimé : 4-5 minutes")
        print()
        print("💡 Le prompt généré contient automatiquement :")
        print("   • Ton profil athlète et tes objectifs (project_prompt_v2_1_revised.md)")
        print("   • L'historique de tes séances récentes (workouts-history.md)")
        print("   • Les concepts d'entraînement cyclisme (cycling_training_concepts.md)")
        print("     → Zones Z1-Z7, Sweet Spot, métriques TSS/IF/NP, critères validation")
        print("   • Les données de ta séance depuis Intervals.icu")
        print("   • Le workout planifié (si disponible)")
        print("   • Ton feedback subjectif (si collecté)")
        print()
        print("👉 Aucun upload de fichier nécessaire !")
        print()

        self.wait_user("Appuyer sur ENTRÉE pour démarrer...")

    def step_1b_detect_all_gaps(self):
        """Étape 1b : Détection unifiée de tous les gaps (exécutées + repos + annulations)

        Returns:
            str: Choix utilisateur ("single_executed", "batch_specials", "batch_all", "exit")
        """
        # Skip si activity_id fourni (bypass détection gaps)
        if self.activity_id:
            return "single_executed"

        self.clear_screen()
        self.print_header(
            "🔍 Détection Gaps",
            "Étape 1b/7 : Détection séances à documenter"
        )

        # === PARTIE 1 : Détecter activités exécutées non analysées ===
        state = WorkflowState(project_root=self.project_root)

        # Charger config API
        config_path = Path.home() / ".intervals_config.json"
        if not config_path.exists():
            print("⚠️  Config API non trouvée → Skip détection")
            self.wait_user()
            return "exit"

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)

            athlete_id = config.get('athlete_id')
            api_key = config.get('api_key')

            if not athlete_id or not api_key:
                print("⚠️  Credentials invalides → Skip détection")
                self.wait_user()
                return "exit"

            # Connexion API
            session = requests.Session()
            session.auth = ("API_KEY", api_key)
            session.headers.update({"Content-Type": "application/json"})

            # Récupérer activités récentes
            last_analyzed_id = state.get_last_analyzed_id()

            if last_analyzed_id:
                oldest_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            else:
                oldest_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

            newest_date = datetime.now().strftime('%Y-%m-%d')

            url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/activities"
            response = session.get(url, params={'oldest': oldest_date, 'newest': newest_date})
            response.raise_for_status()
            activities = response.json()

            # Filtrer activités non analysées
            activities.sort(key=lambda x: x['start_date_local'], reverse=True)
            unanalyzed = state.get_unanalyzed_activities(activities)
            self.unanalyzed_activities = unanalyzed if unanalyzed else None

        except Exception as e:
            print(f"⚠️  Erreur API : {e}")
            self.unanalyzed_activities = None

        # === PARTIE 1B : Détecter séances planifiées sautées ===
        skipped_sessions = []

        try:
            # Utiliser le nouveau checker pour détecter séances sautées
            checker = PlannedSessionsChecker(
                athlete_id=athlete_id,
                api_key=api_key
            )

            # Chercher dans même période que activités
            skipped_sessions = checker.detect_skipped_sessions(
                start_date=oldest_date,
                end_date=newest_date,
                exclude_future=True  # Ignorer workouts futurs
            )

            self.skipped_sessions = skipped_sessions if skipped_sessions else None

        except Exception as e:
            print(f"⚠️  Détection séances sautées impossible : {e}")
            print("   Continuer avec détection activités exécutées uniquement")
            self.skipped_sessions = None

        # === PARTIE 2 : Charger planning si disponible ===
        rest_days = []
        cancelled_sessions = []

        if self.week_id:
            planning_dir = self.project_root / "data" / "week_planning"
            planning_file = planning_dir / f"week_planning_{self.week_id}.json"

            if planning_file.exists():
                try:
                    with open(planning_file, 'r', encoding='utf-8') as f:
                        self.planning = json.load(f)

                    if validate_week_planning(self.planning):
                        # Réconciliation
                        from cyclisme_training_logs.prepare_analysis import IntervalsAPI
                        api = IntervalsAPI(athlete_id=athlete_id, api_key=api_key)

                        planning_activities = api.get_activities(
                            oldest=self.planning['start_date'],
                            newest=self.planning['end_date']
                        )

                        self.reconciliation = reconcile_planned_vs_actual(
                            self.planning,
                            planning_activities
                        )

                        rest_days = self.reconciliation.get('rest_days', [])
                        cancelled_sessions = self.reconciliation.get('cancelled', [])

                except Exception as e:
                    print(f"⚠️  Erreur chargement planning : {e}")

        # === PARTIE 3 : Afficher résumé unifié ===
        print("\n" + "=" * 70)
        print("📊 RÉSUMÉ GAPS DÉTECTÉS")
        print("=" * 70)

        count_executed = len(self.unanalyzed_activities) if self.unanalyzed_activities else 0
        count_rest = len(rest_days)
        count_cancelled = len(cancelled_sessions)
        count_skipped = len(self.skipped_sessions) if self.skipped_sessions else 0
        total_gaps = count_executed + count_rest + count_cancelled + count_skipped

        if total_gaps == 0:
            print("\n✅ Aucun gap détecté !")
            print("   Toutes les séances récentes sont documentées.")
            print("   Aucune séance planifiée sautée.")
            print()
            self.wait_user()
            return "exit"

        # Détails séances exécutées
        if count_executed > 0:
            print(f"\n🚴 Séances exécutées non analysées : {count_executed}")
            for i, act in enumerate(self.unanalyzed_activities[:3], 1):
                date = act['start_date_local'][:10]
                name = act.get('name', 'Séance')[:40]
                print(f"   {i}. [{date}] {name}")
            if count_executed > 3:
                print(f"   ... et {count_executed - 3} autres")

        # Détails repos
        if count_rest > 0:
            print(f"\n💤 Repos planifiés non documentés : {count_rest}")
            for rest in rest_days[:3]:
                date = rest['date']
                session_id = rest['session_id']
                reason = rest.get('rest_reason', 'Repos planifié')[:40]
                print(f"   • [{date}] {session_id} - {reason}")
            if count_rest > 3:
                print(f"   ... et {count_rest - 3} autres")

        # Détails annulations
        if count_cancelled > 0:
            print(f"\n❌ Séances annulées non documentées : {count_cancelled}")
            for cancelled in cancelled_sessions[:3]:
                date = cancelled['date']
                session_id = cancelled['session_id']
                reason = cancelled.get('cancellation_reason', 'Annulée')[:40]
                print(f"   • [{date}] {session_id} - {reason}")
            if count_cancelled > 3:
                print(f"   ... et {count_cancelled - 3} autres")

        # Détails séances sautées (planifiées mais non exécutées)
        if count_skipped > 0:
            print(f"\n⏭️  Séances planifiées sautées : {count_skipped}")
            for skipped in self.skipped_sessions[:3]:
                date = skipped['planned_date']
                name = skipped['planned_name'][:40]
                tss = skipped['planned_tss']
                days = skipped['days_ago']
                print(f"   • [{date}] {name} ({tss} TSS, il y a {days}j)")
            if count_skipped > 3:
                print(f"   ... et {count_skipped - 3} autres")

        # === PARTIE 4 : Menu de choix ===
        print("\n" + "=" * 70)
        print("💡 QUE VEUX-TU FAIRE ?")
        print("=" * 70)
        print()

        options = []
        if count_executed > 0:
            print("  [1] Traiter UNE séance exécutée (workflow classique)")
            options.append("1")

        if count_rest > 0 or count_cancelled > 0 or count_skipped > 0:
            special_label = []
            if count_rest > 0:
                special_label.append("repos")
            if count_cancelled > 0:
                special_label.append("annulations")
            if count_skipped > 0:
                special_label.append("sautées")
            print(f"  [2] Traiter {'/'.join(special_label)} en batch")
            options.append("2")

        if count_executed > 0 and (count_rest > 0 or count_cancelled > 0 or count_skipped > 0):
            print("  [3] Traiter TOUT en batch (exécutées + repos + annulations + sautées)")
            options.append("3")

        print("  [0] Quitter")
        print()

        while True:
            choice = input("Ton choix : ").strip()

            if choice == "0":
                return "exit"
            elif choice == "1" and "1" in options:
                return "single_executed"
            elif choice == "2" and "2" in options:
                return "batch_specials"
            elif choice == "3" and "3" in options:
                return "batch_all"
            else:
                print("❌ Choix invalide, réessaye.")

    def step_2_collect_feedback(self):
        """Étape 2 : Collecter le feedback athlète"""
        if self.skip_feedback:
            self.clear_screen()
            self.print_header(
                "⏭️  Feedback Athlète (Skip)",
                "Étape 2/7 : Collecte feedback (optionnel)"
            )
            print("Le feedback athlète a été skippé (--skip-feedback).")
            print("L'analyse sera basée uniquement sur les métriques objectives.")
            self.wait_user()
            return

        self.clear_screen()
        self.print_header(
            "💭 Collecte Feedback Athlète",
            "Étape 2/7 : Ressenti subjectif (optionnel)"
        )

        print("Veux-tu enrichir l'analyse avec ton ressenti sur la séance ?")
        print()
        print("✅ Avantages :")
        print("   • Claude croise métriques objectives + ressenti subjectif")
        print("   • Analyse plus personnalisée et pertinente")
        print("   • Détection des écarts perception/réalité")
        print()
        print("⏱️  Temps estimé : 30 secondes (quick) ou 2-3 min (full)")
        print()

        collect = input("Collecter le feedback ? (o/n) : ").strip().lower()

        if collect != 'o':
            print()
            print("⏭️  Feedback skippé. L'analyse sera basée sur les métriques.")
            self.wait_user()
            return

        # Choisir le mode
        print()
        print("Mode feedback :")
        print("  1 - Quick (30s) : RPE + ressenti général")
        print("  2 - Full (2-3min) : RPE + ressenti + difficultés + contexte + sensations")
        mode_choice = input("Choix (1/2) : ").strip()

        print()
        mode_str = "quick" if mode_choice == '1' else "full"
        print(f"Lancement de collect_athlete_feedback.py (mode {mode_str})...")
        self.print_separator()

# Lancer le script de collecte AVEC contexte
        try:
            from cyclisme_training_logs.prepare_analysis import IntervalsAPI

            # Vérifier si des gaps ont été détectés en step_1b
            if not self.unanalyzed_activities or len(self.unanalyzed_activities) == 0:
                print()
                print("ℹ️  Aucun gap détecté → Skip feedback")
                print("   Toutes les séances récentes sont déjà analysées")
                print()
                self.wait_user()
                return

            # FIX: Charger credentials
            athlete_id, api_key = self.load_credentials()

            if not athlete_id or not api_key:
                print()
                print("ℹ️  Credentials non trouvés")
                print("   → Feedback sans contexte")
                raise ValueError("No credentials")

            api = IntervalsAPI(athlete_id=athlete_id, api_key=api_key)

            # Utiliser les gaps détectés par step_1b au lieu de requêter last 24h
            activity = None
            if self.unanalyzed_activities and len(self.unanalyzed_activities) > 0:
                # Prendre la première activité non analysée détectée
                activity = self.unanalyzed_activities[0]
                print()
                print(f"✓ Contexte : {activity.get('name', 'Séance')} du {activity.get('start_date_local', '')[:10]}")

            if activity:

                # Commande avec contexte
                cmd = [
                    "python3",
                    str(self.scripts_dir / "collect_athlete_feedback.py"),
                    "--activity-name", activity.get('name', 'Séance'),
                    "--activity-date", activity.get('start_date_local', ''),
                    "--activity-duration", str(activity.get('moving_time', 0) // 60),
                    "--activity-tss", str(int(activity.get('icu_training_load', 0))),
                ]

                # Ajouter IF si disponible
                if activity.get('icu_intensity'):
                    if_value = activity.get('icu_intensity', 0) / 100.0
                    cmd.extend(["--activity-if", f"{if_value:.2f}"])

                # Mode quick
                if mode_choice == '1':
                    cmd.append("--quick")

                result = subprocess.run(cmd)
            else:
                # Fallback sans contexte
                print()
                print("⚠️  Impossible de récupérer le contexte de la séance")
                cmd = ["python3", str(self.scripts_dir / "collect_athlete_feedback.py")]
                if mode_choice == '1':
                    cmd.append("--quick")
                result = subprocess.run(cmd)

        except Exception as e:
            print()
            print(f"⚠️  Erreur lors de la récupération du contexte : {e}")
            print("   → Collecte feedback sans contexte activité")
            # Fallback sans contexte
            cmd = ["python3", str(self.scripts_dir / "collect_athlete_feedback.py")]
            if mode_choice == '1':
                cmd.append("--quick")
            result = subprocess.run(cmd)

        # Résultat
        if result.returncode != 0:
            print()
            print("⚠️  Erreur lors de la collecte du feedback.")
            print("    L'analyse continuera sans feedback.")
            self.wait_user()
        else:
            print()
            print("✅ Feedback collecté et sauvegardé !")
            self.wait_user()
    def step_3_prepare_analysis(self):
        """Étape 3 : Préparer le prompt d'analyse"""
        self.clear_screen()
        self.print_header(
            "📝 Préparation Prompt d'Analyse",
            "Étape 3/7 : Génération du prompt"
        )

        print("Récupération de la séance depuis Intervals.icu...")
        print("Génération du prompt optimisé pour Claude...")
        print()
        print("⏱️  Temps estimé : 10 secondes")
        self.print_separator()

        # Construire la commande
        cmd = ["python3", str(self.scripts_dir / "prepare_analysis.py")]
        if self.activity_id:
            cmd.extend(["--activity-id", self.activity_id])

        result = subprocess.run(cmd)

        if result.returncode != 0:
            print()
            print("❌ Erreur lors de la préparation du prompt.")
            print("   Vérifier la configuration Intervals.icu et réessayer.")
            sys.exit(1)

        print()
        print("✅ Prompt copié dans le presse-papier !")

        # Extraire le nom de l'activité depuis le clipboard
        try:
            clipboard = subprocess.run(
                ['pbpaste'],
                capture_output=True,
                text=True
            )
            # Chercher la ligne "- **Nom** : ..."
            for line in clipboard.stdout.split('\n'):
                if line.strip().startswith('- **Nom** :'):
                    self.activity_name = line.split(':', 1)[1].strip()
                    break
        except:
            pass

        # Afficher le nom de la séance si trouvé
        if self.activity_name:
            print()
            print("=" * 70)
            print(f"🚴 SÉANCE EN COURS D'ANALYSE")
            print("=" * 70)
            print(f"\n{self.activity_name}\n")
            print("=" * 70)

        self.wait_user()

    # ========================================================================
    # NOUVELLES MÉTHODES POUR GESTION PLANNING HEBDOMADAIRE
    # ========================================================================

    def _detect_week_id(self) -> str:
        """Détecte ou demande le week_id

        Returns:
            Week ID (ex: "S070")
        """
        # Si week_id fourni en argument CLI
        if self.week_id:
            return self.week_id

        # Sinon, demander à l'utilisateur
        print("\n💡 Pour le mode réconciliation, un identifiant de semaine est requis")
        week_id = input("Identifiant semaine (ex: S070) : ").strip().upper()

        if not week_id.startswith('S'):
            week_id = 'S' + week_id

        return week_id

    def _check_planning_available(self) -> bool:
        """Vérifie si un planning hebdomadaire est disponible

        Returns:
            True si planning trouvé, False sinon
        """
        if not self.week_id:
            week_id = self._detect_week_id()
        else:
            week_id = self.week_id

        planning_dir = self.project_root / "data" / "week_planning"
        planning_file = planning_dir / f"week_planning_{week_id}.json"

        return planning_file.exists()

    def _display_reconciliation_report(self, result: dict):
        """Affiche le rapport de réconciliation

        Args:
            result: Résultat de reconcile_planned_vs_actual()
        """
        print("\n" + "=" * 70)
        print("📊 RAPPORT RÉCONCILIATION")
        print("=" * 70)

        sessions_planned = len(self.planning['planned_sessions'])
        print(f"\nSessions planifiées   : {sessions_planned}")
        print(f"Sessions exécutées    : {len(result['matched'])}")
        print(f"Repos planifiés       : {len(result['rest_days'])}")
        print(f"Séances annulées      : {len(result['cancelled'])}")

        if result.get('unplanned'):
            print(f"⚠️  Activités non planifiées : {len(result['unplanned'])}")

        # Détail par catégorie
        if result['matched']:
            print("\n✅ Séances exécutées :")
            for match in result['matched']:
                session = match['session']
                print(f"   - {session['session_id']} ({session['date']})")

        if result['rest_days']:
            print("\n💤 Repos planifiés :")
            for rest in result['rest_days']:
                print(f"   - {rest['session_id']} ({rest['date']})")

        if result['cancelled']:
            print("\n❌ Séances annulées :")
            for cancelled in result['cancelled']:
                reason = cancelled.get('cancellation_reason', 'Non spécifié')[:50]
                print(f"   - {cancelled['session_id']} ({cancelled['date']}) - {reason}...")

        if result.get('unplanned'):
            print("\n⚠️  Activités non planifiées :")
            for unplanned in result['unplanned']:
                name = unplanned.get('name', 'Sans nom')[:40]
                date = unplanned['start_date_local'][:10]
                print(f"   - {name} ({date})")

        print("=" * 70)

    def _collect_rest_feedback(self, session_data: dict) -> dict:
        """Collecte feedback athlète pour jour de repos

        Args:
            session_data: Session info

        Returns:
            Dict avec sleep_duration, sleep_score, hrv, resting_hr
        """
        print(f"\n📝 Feedback pour {session_data['session_id']} (repos planifié)")
        print("   (Laisser vide pour ignorer)")

        sleep = input("   Sommeil (format 7h30) : ").strip() or "N/A"
        sleep_score = input("   Score sommeil (0-100) : ").strip()
        hrv = input("   VFC (ms) : ").strip()
        resting_hr = input("   FC repos (bpm) : ").strip()

        return {
            "sleep_duration": sleep,
            "sleep_score": int(sleep_score) if sleep_score else None,
            "hrv": int(hrv) if hrv else None,
            "resting_hr": int(resting_hr) if resting_hr else None
        }

    def _preview_markdowns(self, markdowns: list):
        """Affiche preview des markdowns générés

        Args:
            markdowns: Liste de tuples (date, markdown_text)
        """
        print("\n" + "=" * 70)
        print("👁️  PREVIEW MARKDOWNS GÉNÉRÉS")
        print("=" * 70)

        for i, (date, markdown) in enumerate(markdowns, 1):
            lines = markdown.split('\n')
            chars = len(markdown)
            title = lines[0] if lines else "Sans titre"

            print(f"\n📄 Markdown {i}/{len(markdowns)}")
            print(f"   Date    : {date}")
            print(f"   Titre   : {title}")
            print(f"   Lignes  : {len(lines)}")
            print(f"   Chars   : {chars}")
            print(f"\n   Début :")
            for line in lines[:10]:
                print(f"   {line}")
            if len(lines) > 10:
                print(f"   ... ({len(lines) - 10} lignes suivantes)")

        print("\n" + "=" * 70)

    def _copy_to_clipboard(self, markdowns: list) -> bool:
        """Copie markdowns dans clipboard macOS

        Args:
            markdowns: Liste de tuples (date, markdown_text)

        Returns:
            True si succès, False sinon
        """
        # Combiner tous les markdowns
        combined = "\n\n".join(markdown for _, markdown in markdowns)

        try:
            # Copier via pbcopy (macOS)
            process = subprocess.Popen(
                ['pbcopy'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            process.communicate(input=combined.encode('utf-8'))

            if process.returncode == 0:
                print(f"\n✅ {len(markdowns)} markdowns copiés dans le presse-papier")
                print(f"   Total : {len(combined)} caractères")
                return True
            else:
                print("\n❌ Erreur lors de la copie")
                return False

        except Exception as e:
            print(f"\n❌ Erreur : {e}")
            return False

    def _export_markdowns(self, markdowns: list, week_id: str) -> bool:
        """Export markdowns vers fichier

        Args:
            markdowns: Liste de tuples (date, markdown_text)
            week_id: ID semaine (ex: S070)

        Returns:
            True si succès, False sinon
        """
        output_dir = self.project_root / "data" / "week_planning"
        output_file = output_dir / f"special_sessions_{week_id}.md"

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# Sessions Spéciales - Semaine {week_id}\n\n")
                f.write(f"Généré le : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")

                for date, markdown in markdowns:
                    f.write(markdown)
                    f.write("\n\n")

            print(f"\n✅ Export réussi : {output_file}")
            print(f"   {len(markdowns)} sessions documentées")
            return True

        except Exception as e:
            print(f"\n❌ Erreur export : {e}")
            return False

    def _insert_to_history(self, markdowns: list) -> bool:
        """Insère markdowns dans workouts-history.md

        Args:
            markdowns: Liste de tuples (date, markdown_text)

        Returns:
            True si succès, False sinon
        """
        history_file = self.project_root / "logs" / "workouts-history.md"

        if not history_file.exists():
            print(f"\n❌ Fichier introuvable : {history_file}")
            return False

        try:
            # Lire fichier existant
            with open(history_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Pour simplifier Phase 3, on append à la fin
            # TODO Phase 4 : Insertion chronologique intelligente
            with open(history_file, 'a', encoding='utf-8') as f:
                f.write("\n\n")
                for date, markdown in markdowns:
                    f.write(markdown)
                    f.write("\n\n")

            print(f"\n✅ Insertion réussie dans {history_file}")
            print(f"   {len(markdowns)} sessions ajoutées")
            print("\n⚠️  Note : Les entrées ont été ajoutées à la fin du fichier")
            print("   Tu peux les réorganiser manuellement si besoin")
            return True

        except Exception as e:
            print(f"\n❌ Erreur insertion : {e}")
            return False

    def _show_special_sessions(self):
        """Génère et affiche les sessions spéciales (repos/annulations)"""
        if not self.reconciliation:
            return

        print("\n" + "=" * 70)
        print("📝 GÉNÉRATION SESSIONS SPÉCIALES")
        print("=" * 70)

        # Métriques par défaut (TODO: récupérer depuis API wellness)
        metrics_default = {"ctl": 50, "atl": 35, "tsb": 15}

        markdowns_generated = []

        # Générer repos planifiés
        if self.reconciliation['rest_days']:
            print(f"\n💤 Génération {len(self.reconciliation['rest_days'])} repos planifiés...")
            for rest in self.reconciliation['rest_days']:
                print(f"\n   → {rest['session_id']} - {rest['name']}")

                # Collecter feedback
                feedback = self._collect_rest_feedback(rest)

                # Générer markdown
                markdown = generate_rest_day_entry(
                    session_data=rest,
                    metrics_pre=metrics_default,
                    metrics_post=metrics_default,
                    athlete_feedback=feedback
                )
                markdowns_generated.append((rest['date'], markdown))
                print(f"      ✓ Généré ({len(markdown)} chars)")

        # Générer séances annulées
        if self.reconciliation['cancelled']:
            print(f"\n❌ Génération {len(self.reconciliation['cancelled'])} séances annulées...")
            for cancelled in self.reconciliation['cancelled']:
                print(f"\n   → {cancelled['session_id']} - {cancelled['name']}")

                reason = cancelled.get('cancellation_reason', 'Non spécifié')

                # Générer markdown
                markdown = generate_cancelled_session_entry(
                    session_data=cancelled,
                    metrics_pre=metrics_default,
                    reason=reason
                )
                markdowns_generated.append((cancelled['date'], markdown))
                print(f"      ✓ Généré ({len(markdown)} chars)")

        if not markdowns_generated:
            print("\n⚠️  Aucune session spéciale à documenter")
            return

        # Trier par date
        markdowns_generated.sort(key=lambda x: x[0])

        print(f"\n✅ {len(markdowns_generated)} markdowns générés")

        # Preview
        self._preview_markdowns(markdowns_generated)

        # Menu actions
        print("\n" + "=" * 70)
        print("💡 Que veux-tu faire avec ces markdowns ?")
        print("=" * 70)
        print("  [1] Enrichir avec Claude.ai (analyse coach)")
        print("  [2] Insérer tel quel dans workouts-history.md")
        print("  [3] Export fichier seulement")
        print("  [4] Copier dans presse-papier")
        print("  [0] Retour menu réconciliation")

        action = input("\nTon choix (0/1/2/3/4) : ").strip()

        if action == "0":
            print("\n→ Retour menu réconciliation")
            return "exit_workflow"

        elif action == "1":
            # Enrichissement Claude.ai
            print("\n🤖 Génération prompt d'enrichissement Coach IA...")
            if self._generate_coach_prompt(markdowns_generated):
                print("\n✅ Prompt copié dans le presse-papier")
                print("\n→ Continuation workflow pour enrichissement...")
                print("   Étapes suivantes :")
                print("   • Coller dans Claude.ai")
                print("   • Récupérer analyse enrichie")
                print("   • Valider et insérer")
                # Sauvegarder markdowns pour référence
                self._markdowns_generated = markdowns_generated
                return "continue_workflow"
            else:
                print("\n❌ Erreur génération prompt")
                return "exit_workflow"

        elif action == "2":
            # Insertion directe
            confirm = input("\n⚠️  Confirmer insertion directe (sans enrichissement) ? (o/n) : ").strip().lower()
            if confirm == 'o':
                self._insert_to_history(markdowns_generated)
                print("\n✅ Sessions documentées")
            else:
                print("\n→ Insertion annulée")
            return "exit_workflow"

        elif action == "3":
            # Export fichier
            self._export_markdowns(markdowns_generated, self.planning['week_id'])
            return "exit_workflow"

        elif action == "4":
            # Copier clipboard
            self._copy_to_clipboard(markdowns_generated)
            return "exit_workflow"

        else:
            print("\n⚠️  Choix invalide")
            return "exit_workflow"

    def _handle_rest_cancellations(self):
        """Handler pour traiter repos/annulations en batch

        Returns:
            str: Action à effectuer ("exit" ou "continue")
        """
        if not self.reconciliation:
            print("\n⚠️  Aucune réconciliation disponible")
            self.wait_user()
            return "exit"

        result = self._show_special_sessions()

        if result == "continue_workflow":
            # Enrichissement Claude.ai → continuer vers step 4
            return "continue"
        else:
            # Export/Copie/Insertion → terminé
            return "exit"

    def _handle_batch_all(self):
        """Handler pour traiter TOUT en batch (exécutées + repos + annulations)

        TODO: Implémenter traitement batch complet
        - Générer markdowns repos/annulations
        - Générer analyses séances exécutées
        - Tout insérer en batch
        - Commit git global

        Returns:
            str: Action à effectuer
        """
        print("\n" + "=" * 70)
        print("⚠️  MODE BATCH COMPLET")
        print("=" * 70)
        print("\n🚧 Fonctionnalité en développement")
        print("\nCette fonctionnalité permettra de :")
        print("  • Générer analyses pour TOUTES les séances exécutées")
        print("  • Générer markdowns pour repos/annulations")
        print("  • Insérer tout en batch dans workouts-history.md")
        print("  • Commit git global")
        print()
        print("Pour l'instant, utilise :")
        print("  → Choix [1] pour traiter une séance à la fois")
        print("  → Choix [2] pour traiter repos/annulations")
        print()
        self.wait_user()
        return "exit"

    def _generate_coach_prompt(self, markdowns: list) -> bool:
        """Génère prompt d'enrichissement Coach IA pour repos/annulations

        Args:
            markdowns: Liste de tuples (date, markdown_text)

        Returns:
            True si succès, False sinon
        """
        try:
            # 1. Charger prompt projet
            project_prompt_file = self.project_root / "references" / "project_prompt_v2_1_revised.md"
            if not project_prompt_file.exists():
                print(f"\n⚠️  Prompt projet non trouvé : {project_prompt_file}")
                return False

            with open(project_prompt_file, 'r', encoding='utf-8') as f:
                project_prompt = f.read()

            # 2. Charger historique récent (5 dernières séances)
            history_file = self.project_root / "logs" / "workouts-history.md"
            recent_history = ""

            if history_file.exists():
                with open(history_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extraire les 5 dernières séances (regex simple)
                import re
                sessions = re.findall(r'###\s+S\d+-\d+.*?(?=###\s+S\d+-\d+|\Z)', content, re.DOTALL)
                recent_sessions = sessions[-5:] if len(sessions) >= 5 else sessions

                if recent_sessions:
                    recent_history = "\n".join(recent_sessions)
                else:
                    recent_history = "(Pas d'historique récent disponible)"

            # 3. Construire markdowns combinés
            combined_markdowns = "\n\n---\n\n".join(
                markdown for _, markdown in markdowns
            )

            # 4. Construire prompt enrichissement
            enrichment_prompt = f"""# Mission Coach IA : Enrichissement Sessions Spéciales

Tu es un coach cyclisme expert. J'ai généré des analyses automatiques pour des sessions spéciales (repos planifiés et séances annulées).

**Ta mission :** Enrichir ces analyses avec ton expertise de coach.

## Contexte Athlète

{project_prompt}

## Historique Récent (5 dernières séances)

{recent_history}

## Analyses à Enrichir

{combined_markdowns}

---

## Instructions Coach

Pour CHAQUE session ci-dessus :

### Si REPOS planifié :
1. **Valider la stratégie de repos** :
   - Est-ce le bon moment dans le cycle d'entraînement ?
   - TSB/CTL/ATL cohérents avec besoin de récupération ?

2. **Enrichir les recommandations** :
   - Activités légères recommandées (marche, yoga, etc.) ?
   - Points de vigilance pour la prochaine séance ?
   - Nutrition/hydratation spécifiques ?

3. **Contextualiser dans la progression** :
   - Impact sur objectifs semaine/mois ?
   - Adaptation du plan si nécessaire ?

### Si SÉANCE ANNULÉE :
1. **Analyser l'impact** :
   - Gravité de l'interruption (technique vs physiologique) ?
   - Effet sur progression planifiée ?

2. **Proposer alternatives** :
   - Report possible ? Quand ?
   - Adaptation charge semaine ?
   - Séance de remplacement recommandée ?

3. **Prévention** :
   - Comment éviter la cause (si applicable) ?
   - Points d'attention matériel/préparation ?

---

## Format de Réponse

Retourne chaque session enrichie dans LE MÊME FORMAT MARKDOWN mais avec :
- Sections existantes conservées
- Analyses enrichies avec ton expertise
- Recommandations coach ajoutées/améliorées
- Ton professionnel et bienveillant

**IMPORTANT :** Retourne UNIQUEMENT les markdowns enrichis, pas de texte explicatif autour.
"""

            # 5. Copier dans clipboard
            process = subprocess.Popen(
                ['pbcopy'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            process.communicate(input=enrichment_prompt.encode('utf-8'))

            if process.returncode == 0:
                return True
            else:
                return False

        except Exception as e:
            print(f"\n❌ Erreur : {e}")
            import traceback
            traceback.print_exc()
            return False

    def step_4_paste_prompt(self):
        """Étape 4 : Instructions pour coller le prompt dans Claude"""
        self.clear_screen()

        # Afficher le nom de la séance dans le header
        subtitle = "Étape 4/7 : Envoi du prompt"
        if self.activity_name:
            subtitle += f"\n🚴 {self.activity_name}"

        self.print_header(
            "🤖 Analyse par Claude.ai",
            subtitle
        )

        print("Le prompt est prêt dans ton presse-papier.")
        print()
        print("📋 INSTRUCTIONS :")
        print()
        print("1. Ouvrir Claude.ai (nouveau chat ou conversation existante)")
        print("   → https://claude.ai")
        print()
        print("2. Coller le prompt (Cmd+V ou Ctrl+V)")
        print()
        print("3. Envoyer le message")
        print()
        print("4. Attendre la réponse de Claude (~30-60 secondes)")
        print()
        print("5. Copier UNIQUEMENT le bloc markdown de l'analyse")
        print("   → Du premier ### jusqu'à la dernière ligne")
        print("   → Ne pas inclure le texte explicatif de Claude")
        print()
        print("⏱️  Temps estimé : 1-2 minutes")
        print()
        print("⚠️  IMPORTANT : Ne copier que le markdown, pas le texte autour !")
        print()

        self.wait_user("Appuyer sur ENTRÉE une fois la réponse copiée...")

    def step_5_validate_analysis(self):
        """Étape 5 : Valider la réponse de Claude"""
        self.clear_screen()

        # Afficher le nom de la séance dans le header
        subtitle = "Étape 5/7 : Vérification qualité"
        if self.activity_name:
            subtitle += f"\n🚴 {self.activity_name}"

        self.print_header(
            "✅ Validation de l'Analyse",
            subtitle
        )

        print("Avant d'insérer l'analyse dans les logs, vérifie que :")
        print()
        print("✓ Tu as copié UNIQUEMENT le bloc markdown")
        print("✓ Le format commence par ### [Nom Séance]")
        print("✓ Toutes les sections sont présentes :")
        print("  • Métriques Pré-séance")
        print("  • Exécution")
        print("  • Exécution Technique")
        print("  • Charge d'Entraînement")
        print("  • Validation Objectifs")
        print("  • Points d'Attention")
        print("  • Recommandations Progression")
        print("  • Métriques Post-séance")
        print()
        print("✓ Le contenu est cohérent et factuel")
        print()

        while True:
            valid = input("✓ L'analyse est-elle valide et prête ? (o/n) : ").strip().lower()
            if valid in ['o', 'n']:
                break
            print("⚠️  Répondre 'o' ou 'n'")

        if valid != 'o':
            print()
            print("⚠️  Analyse non validée.")
            print()
            print("💡 Actions possibles :")
            print("   • Corriger la réponse dans Claude et recopier")
            print("   • Demander à Claude de régénérer l'analyse")
            print("   • Relancer ce script après correction")
            print()
            print("Workflow interrompu.")
            sys.exit(0)

        print()
        print("✅ Analyse validée !")
        self.wait_user()

    def step_6_insert_analysis(self):
        """Étape 6 : Insérer l'analyse dans les logs"""
        self.clear_screen()

        # Afficher le nom de la séance dans le header
        subtitle = "Étape 6/7 : Mise à jour workouts-history.md"
        if self.activity_name:
            subtitle += f"\n🚴 {self.activity_name}"

        self.print_header(
            "💾 Insertion dans les Logs",
            subtitle
        )

        print("Insertion de l'analyse depuis le presse-papier...")
        print()
        print("⏱️  Temps estimé : 5 secondes")
        self.print_separator()

        # Lancer le script d'insertion
        cmd = ["python3", str(self.scripts_dir / "insert_analysis.py")]
        result = subprocess.run(cmd)

        if result.returncode != 0:
            print()
            print("❌ Erreur lors de l'insertion de l'analyse.")
            print("   Vérifier le format et réessayer.")
            sys.exit(1)

        print()
        print("✅ Analyse insérée dans logs/workouts-history.md !")
        self.wait_user()

    def step_6b_servo_control(self):
        """Étape 6b : Asservissement planning (si --servo-mode activé)

        Cette étape:
        1. Charge le planning restant de la semaine
        2. Parse la réponse AI pour détecter modifications recommandées
        3. Applique les modifications après confirmation utilisateur
        """
        self.clear_screen()

        subtitle = "Étape 6b/7 : Asservissement Planning (Servo Mode)"
        if self.activity_name:
            subtitle += f"\n🚴 {self.activity_name}"

        self.print_header(
            "🔄 Asservissement Planning",
            subtitle
        )

        print("Le mode asservissement est activé.")
        print("Vérification si le coach AI recommande des ajustements au planning...")
        print()

        # Detect week_id from activity or ask user
        if not self.week_id:
            week_id_input = input("Identifiant semaine (ex: S072) : ").strip().upper()
            if not week_id_input.startswith('S'):
                week_id_input = 'S' + week_id_input
            week_id = week_id_input
        else:
            week_id = self.week_id

        print(f"📅 Semaine : {week_id}")
        print()

        # Load remaining sessions
        remaining_sessions = self.load_remaining_sessions(week_id)

        if not remaining_sessions:
            print("⚠️  Aucune séance future trouvée dans le planning")
            print("   Asservissement désactivé pour cette séance")
            self.wait_user()
            return

        print(f"📋 {len(remaining_sessions)} séances restantes dans le planning:")
        for session in remaining_sessions:
            date = session['date']
            session_id = session['session_id']
            name = session['name']
            workout_type = session['type']
            tss = session.get('tss_planned', 0)
            # Construct workout code
            code = f"{session_id}-{workout_type}-{name}-{session.get('version', 'V001')}"
            if session.get('status') == 'rest_day':
                print(f"   • {date}: REPOS")
            else:
                print(f"   • {date}: {code} ({tss} TSS)")
        print()

        # Ask user if they want to request AI recommendations
        print("Le coach AI peut analyser le planning restant et proposer des ajustements.")
        print()
        request_mods = input("Demander recommandations au coach AI ? (o/n) : ").strip().lower()

        if request_mods != 'o':
            print("✅ Planning maintenu sans modification")
            self.wait_user()
            return

        # Generate supplementary prompt for AI
        planning_context = self.format_remaining_sessions_compact(remaining_sessions)

        supplementary_prompt = f"""# ASSERVISSEMENT PLANNING - Demande Coach AI

Contexte : Tu viens d'analyser la séance du jour.
{planning_context}

## Catalogue Workouts Remplacement

Si modification planning nécessaire, utilise ces templates prédéfinis :

**RÉCUPÉRATION** (remplacement END/INT léger) :
- `recovery_active_30tss` : 45min Z1-Z2 (30 TSS)
- `recovery_active_25tss` : 40min Z1-Z2 (25 TSS)
- `recovery_short_20tss` : 30min Z1 (20 TSS)

**ENDURANCE ALLÉGÉE** (remplacement END normal) :
- `endurance_light_35tss` : 50min Z2 (35 TSS)
- `endurance_short_40tss` : 55min Z2 (40 TSS)

**INTENSITÉ RÉDUITE** (remplacement Sweet-Spot/VO2) :
- `sweetspot_short_50tss` : 2x10min 88% (50 TSS)

## Instructions

Basé sur l'analyse de la séance du jour et les métriques (HRV, RPE, découplage, FC), **recommandes-tu des ajustements au planning restant ?**

Critères de décision:
- HRV < -10% → Envisager allégement
- RPE > 8/10 en zone endurance → Signal alarme
- Découplage > 7.5% → Fatigue cardiaque
- Sommeil < 7h → Vulnérabilité accrue

**Format JSON si modification recommandée** :
```json
{{"modifications": [{{
  "action": "lighten",
  "target_date": "YYYY-MM-DD",
  "current_workout": "CODE",
  "template_id": "recovery_active_30tss",
  "reason": "HRV -15%, prioriser récupération"
}}]}}
```

**Si aucune modification nécessaire** : Ne rien ajouter (pas de JSON).

Réponds maintenant."""

        # Copy supplementary prompt to clipboard
        try:
            process = subprocess.Popen(
                ['pbcopy'],
                stdin=subprocess.PIPE
            )
            process.communicate(input=supplementary_prompt.encode('utf-8'))

            print()
            print("✅ Prompt asservissement copié dans le presse-papier")
            print()
            print("📋 INSTRUCTIONS :")
            print("1. Retourne dans Claude.ai (même conversation)")
            print("2. Colle le prompt supplémentaire (Cmd+V)")
            print("3. Envoie le message")
            print("4. Copie la réponse complète")
            print()

            self.wait_user("Appuyer sur ENTRÉE une fois la réponse copiée...")

        except Exception as e:
            print(f"⚠️  Erreur copie prompt : {e}")
            self.wait_user()
            return

        # Get AI response from clipboard
        try:
            clipboard = subprocess.run(
                ['pbpaste'],
                capture_output=True,
                text=True,
                check=True
            )
            ai_response = clipboard.stdout
        except Exception as e:
            print(f"⚠️  Impossible de lire le presse-papier : {e}")
            self.wait_user()
            return

        # Parse modifications from AI response
        modifications = self.parse_ai_modifications(ai_response)

        if not modifications:
            print()
            print("✅ Aucune modification recommandée par le coach AI")
            print("   Le planning est maintenu tel quel")
        else:
            # Apply modifications (with user confirmation for each)
            self.apply_planning_modifications(modifications, week_id)

        print()
        self.wait_user()

    def step_7_git_commit(self):
        """Étape 7 : Commit git optionnel"""
        if self.skip_git:
            self.clear_screen()
            self.print_header(
                "⏭️  Git Commit (Skip)",
                "Étape 7/7 : Sauvegarde (optionnel)"
            )
            print("Le commit git a été skippé (--skip-git).")
            print()
            print("Pour commiter manuellement plus tard :")
            print("  git add logs/workouts-history.md")
            print('  git commit -m "Analyse: Séance du [DATE]"')
            self.wait_user()
            return

        self.clear_screen()
        self.print_header(
            "💾 Sauvegarde Git",
            "Étape 7/7 : Commit (optionnel)"
        )

        print("Veux-tu commiter cette analyse maintenant ?")
        print()
        print("✅ Avantages :")
        print("   • Historique versionné de toutes tes analyses")
        print("   • Sauvegarde automatique")
        print("   • Synchronisation possible avec remote")
        print()

        commit = input("Commiter maintenant ? (o/n) : ").strip().lower()

        if commit != 'o':
            print()
            print("⏭️  Commit skippé.")
            print()
            print("Pour commiter manuellement plus tard :")
            print("  git add logs/workouts-history.md")
            print('  git commit -m "Analyse: Séance du [DATE]"')
            self.wait_user()
            return

        print()

        # Extraire le nom court de l'activité pour le message de commit
        if self.activity_name:
            # Nettoyer le nom (garder les 30 premiers caractères max)
            short_name = self.activity_name[:30]
        else:
            # Fallback sur la date
            short_name = datetime.now().strftime('%Y-%m-%d')

        print(f"Nom de séance détecté : {short_name}")
        custom = input("Utiliser ce nom ? (o pour oui, ou taper un nom personnalisé) : ").strip()

        if custom.lower() != 'o' and custom:
            short_name = custom

        # Construire le message de commit
        commit_msg = f"Analyse: {short_name}\n\n🤖 Generated with Claude Code\n\nCo-Authored-By: Claude <noreply@anthropic.com>"

        print()
        print("Commit en cours...")

        # Ajouter et commiter
        try:
            subprocess.run(['git', 'add', 'logs/workouts-history.md'], check=True)
            subprocess.run(
                ['git', 'commit', '-m', commit_msg],
                check=True
            )
            print()
            print("✅ Commit réussi !")

            # Proposer le push
            print()
            push = input("Pousser vers remote ? (o/n) : ").strip().lower()
            if push == 'o':
                subprocess.run(['git', 'push'], check=True)
                print()
                print("✅ Push réussi !")

        except subprocess.CalledProcessError as e:
            print()
            print(f"⚠️  Erreur git : {e}")
            print("    Tu peux commiter manuellement si nécessaire.")

        self.wait_user()

    def show_summary(self):
        """Afficher le résumé final"""
        self.clear_screen()
        self.print_header(
            "🎉 Workflow Terminé !",
            "Analyse de séance complète"
        )

        print("✅ RÉCAPITULATIF :")
        print()
        print(f"   Feedback collecté : {'Non' if self.skip_feedback else 'Oui'}")
        print(f"   Analyse insérée : Oui")
        print(f"   Git commit : {'Non' if self.skip_git else 'Oui'}")
        if self.activity_name:
            print(f"   Séance analysée : {self.activity_name}")
        print()
        print("📊 FICHIERS MIS À JOUR :")
        print()
        print("   • logs/workouts-history.md (nouvelle analyse)")
        print()
        print("💡 PROCHAINES ÉTAPES :")
        print()
        print("   • Relire l'analyse dans workouts-history.md")
        print("   • Suivre les recommandations pour la prochaine séance")
        print("   • Réutiliser ce workflow pour la prochaine analyse")
        print()
        print("📖 DOCUMENTATION :")
        print()
        print("   docs/WORKFLOW_GUIDE.md")
        print("   docs/QUICKSTART.md")
        print()
        print("=" * 70)
        print()

    def _optional_git_commit(self, default_message):
        """Proposer commit git optionnel (version simplifiée sans clear_screen)

        Args:
            default_message: Message de commit par défaut
        """
        print()
        print("─" * 70)
        print("💾 Commit Git")
        print("─" * 70)

        commit = input("Commiter les modifications ? (o/n) : ").strip().lower()

        if commit != 'o':
            print("   ⏭️  Commit skippé")
            return

        # Message de commit
        commit_msg = f"{default_message}\n\n🤖 Generated with Claude Code\n\nCo-Authored-By: Claude <noreply@anthropic.com>"

        try:
            subprocess.run(['git', 'add', 'logs/workouts-history.md'], check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True, capture_output=True)
            print("   ✅ Commit réussi !")

            # Proposer push
            push = input("Pousser vers remote ? (o/n) : ").strip().lower()
            if push == 'o':
                subprocess.run(['git', 'push'], check=True, capture_output=True)
                print("   ✅ Push réussi !")

        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Erreur git : {e}")

        print("─" * 70)

    def run(self):
        """Orchestrer le workflow complet avec détection unifiée des gaps (mode boucle)"""
        try:
            # Étape 1 : Accueil (une seule fois)
            self.step_1_welcome()

            # === BOUCLE PRINCIPALE : Traiter gaps jusqu'à épuisement ===
            while True:
                # Étape 1b : Détection unifiée gaps (exécutées + repos + annulations)
                choice = self.step_1b_detect_all_gaps()

                # === FLUX SELON CHOIX ===

                if choice == "exit":
                    # Plus de gaps ou choix "0" explicite
                    print("\n✅ Tous les gaps traités !")
                    print("   Le workflow est terminé.")
                    break  # Sort de la boucle

                elif choice == "single_executed":
                    # Workflow classique : traiter UNE séance exécutée
                    self.step_2_collect_feedback()
                    self.step_3_prepare_analysis()
                    self.step_4_paste_prompt()
                    self.step_5_validate_analysis()
                    self.step_6_insert_analysis()

                    # Servo control integration
                    if self.servo_mode:
                        self.step_6b_servo_control()

                    self.step_7_git_commit()
                    self.show_summary()

                    # Message retour boucle
                    print("\n" + "═" * 70)
                    print("🔄 Retour détection gaps pour sessions restantes...")
                    print("═" * 70)
                    input("\nAppuyer sur ENTRÉE pour continuer...")
                    # Continue la boucle → retour step_1b pour gaps restants

                elif choice == "batch_specials":
                    # Traiter repos/annulations en batch
                    result = self._handle_rest_cancellations()

                    if result == "continue":
                        # Enrichissement Claude.ai choisi → continuer workflow
                        self.step_4_paste_prompt()
                        self.step_5_validate_analysis()
                        self.step_6_insert_analysis()
                        self.step_7_git_commit()
                        self.show_summary()
                    else:
                        # Actions terminées (export/copie/insertion directe)
                        # Proposer commit git optionnel
                        if not self.skip_git:
                            self._optional_git_commit("Sessions spéciales documentées")
                        print("\n✅ Sessions spéciales documentées")

                    # Message retour boucle
                    print("\n" + "═" * 70)
                    print("🔄 Retour détection gaps pour sessions restantes...")
                    print("═" * 70)
                    input("\nAppuyer sur ENTRÉE pour continuer...")
                    # Continue la boucle → retour step_1b pour gaps restants

                elif choice == "batch_all":
                    # Traiter TOUT en batch (exécutées + repos + annulations)
                    self._handle_batch_all()
                    # Continue la boucle → retour step_1b (si implémenté un jour)

                else:
                    # Choix inconnu
                    print(f"\n⚠️  Choix non géré : {choice}")
                    break  # Sort de la boucle par sécurité

        except KeyboardInterrupt:
            print("\n\n⚠️  Workflow interrompu par l'utilisateur (Ctrl+C).")
            print("   Tu peux relancer le script quand tu veux.")
            sys.exit(0)

        except Exception as e:
            print(f"\n\n❌ Erreur inattendue : {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Orchestrateur du workflow d'analyse de séance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Workflow complet interactif
  python3 cyclisme_training_logs/workflow_coach.py

  # Mode réconciliation avec planning hebdomadaire
  python3 cyclisme_training_logs/workflow_coach.py --week-id S070

  # Skip le feedback athlète
  python3 cyclisme_training_logs/workflow_coach.py --skip-feedback

  # Skip le git commit
  python3 cyclisme_training_logs/workflow_coach.py --skip-git

  # Analyser une séance spécifique
  python3 cyclisme_training_logs/workflow_coach.py --activity-id i123456

  # Mode rapide (pas de feedback ni git)
  python3 cyclisme_training_logs/workflow_coach.py --skip-feedback --skip-git

  # Mode réconciliation + rapide
  python3 cyclisme_training_logs/workflow_coach.py --week-id S070 --skip-feedback --skip-git
        """
    )

    parser.add_argument(
        '--skip-feedback',
        action='store_true',
        help="Ne pas collecter le feedback athlète"
    )

    parser.add_argument(
        '--skip-git',
        action='store_true',
        help="Ne pas proposer le commit git"
    )

    parser.add_argument(
        '--activity-id',
        help="ID de l'activité spécifique à analyser (sinon prend la dernière)"
    )

    parser.add_argument(
        '--week-id',
        help="ID semaine pour mode réconciliation planning (ex: S070)"
    )

    parser.add_argument(
        '--servo-mode',
        action='store_true',
        help="Activer le mode asservissement (modifications planning AI)"
    )

    parser.add_argument(
        '--reconcile',
        action='store_true',
        help="Mode réconciliation batch pour séances sautées/annulées (requiert --week-id)"
    )

    args = parser.parse_args()

    # Validation --reconcile requiert --week-id
    if args.reconcile and not args.week_id:
        print("❌ Erreur: --reconcile requiert --week-id")
        print("   Exemple: poetry run workflow-coach --reconcile --week-id S070")
        sys.exit(1)

    # Vérifier qu'on est dans le bon répertoire
    if not Path('logs/workouts-history.md').exists():
        print("❌ Erreur: Ce script doit être lancé depuis la racine du projet.")
        print("   Répertoire courant:", Path.cwd())
        print()
        print("   cd ~/cyclisme-training-logs")
        print("   python3 cyclisme_training_logs/workflow_coach.py")
        sys.exit(1)

    # Lancer le workflow
    coach = WorkflowCoach(
        skip_feedback=args.skip_feedback,
        skip_git=args.skip_git,
        activity_id=args.activity_id,
        week_id=args.week_id,
        servo_mode=args.servo_mode
    )

    # Mode réconciliation batch
    if args.reconcile:
        coach.reconcile_week(args.week_id)
    else:
        coach.run()


if __name__ == '__main__':
    main()
