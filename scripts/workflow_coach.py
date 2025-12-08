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
    python3 scripts/workflow_coach.py [--skip-feedback] [--skip-git]
    python3 scripts/workflow_coach.py --activity-id i123456
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import json
import requests
from workflow_state import WorkflowState
from rest_and_cancellations import (
    load_week_planning,
    validate_week_planning,
    generate_rest_day_entry,
    generate_cancelled_session_entry,
    reconcile_planned_vs_actual
)


class WorkflowCoach:
    """Orchestrateur du workflow d'analyse de séance"""

    def __init__(self, skip_feedback=False, skip_git=False, activity_id=None, week_id=None):
        self.skip_feedback = skip_feedback
        self.skip_git = skip_git
        self.activity_id = activity_id
        self.week_id = week_id
        self.project_root = Path.cwd()
        self.scripts_dir = self.project_root / "scripts"
        self.activity_name = None
        # Nouveaux attributs pour gestion planning
        self.planning = None
        self.reconciliation = None
        self.planning_mode = False
        # Gaps détectés par step_1b
        self.unanalyzed_activities = None

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
                        from prepare_analysis import IntervalsAPI
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
        total_gaps = count_executed + count_rest + count_cancelled

        if total_gaps == 0:
            print("\n✅ Aucun gap détecté !")
            print("   Toutes les séances récentes sont documentées.")
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

        # === PARTIE 4 : Menu de choix ===
        print("\n" + "=" * 70)
        print("💡 QUE VEUX-TU FAIRE ?")
        print("=" * 70)
        print()

        options = []
        if count_executed > 0:
            print("  [1] Traiter UNE séance exécutée (workflow classique)")
            options.append("1")

        if count_rest > 0 or count_cancelled > 0:
            print("  [2] Traiter repos/annulations en batch (génération markdowns)")
            options.append("2")

        if count_executed > 0 and (count_rest > 0 or count_cancelled > 0):
            print("  [3] Traiter TOUT en batch (exécutées + repos + annulations)")
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
            from prepare_analysis import IntervalsAPI

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
        print("   scripts/WORKFLOW_GUIDE.md")
        print("   scripts/QUICKSTART.md")
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
  python3 scripts/workflow_coach.py

  # Mode réconciliation avec planning hebdomadaire
  python3 scripts/workflow_coach.py --week-id S070

  # Skip le feedback athlète
  python3 scripts/workflow_coach.py --skip-feedback

  # Skip le git commit
  python3 scripts/workflow_coach.py --skip-git

  # Analyser une séance spécifique
  python3 scripts/workflow_coach.py --activity-id i123456

  # Mode rapide (pas de feedback ni git)
  python3 scripts/workflow_coach.py --skip-feedback --skip-git

  # Mode réconciliation + rapide
  python3 scripts/workflow_coach.py --week-id S070 --skip-feedback --skip-git
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

    args = parser.parse_args()

    # Vérifier qu'on est dans le bon répertoire
    if not Path('logs/workouts-history.md').exists():
        print("❌ Erreur: Ce script doit être lancé depuis la racine du projet.")
        print("   Répertoire courant:", Path.cwd())
        print()
        print("   cd /Users/stephanejouve/cyclisme-training-logs")
        print("   python3 scripts/workflow_coach.py")
        sys.exit(1)

    # Lancer le workflow
    coach = WorkflowCoach(
        skip_feedback=args.skip_feedback,
        skip_git=args.skip_git,
        activity_id=args.activity_id,
        week_id=args.week_id
    )

    coach.run()


if __name__ == '__main__':
    main()
