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


class WorkflowCoach:
    """Orchestrateur du workflow d'analyse de séance"""

    def __init__(self, skip_feedback=False, skip_git=False, activity_id=None):
        self.skip_feedback = skip_feedback
        self.skip_git = skip_git
        self.activity_id = activity_id
        self.project_root = Path.cwd()
        self.scripts_dir = self.project_root / "scripts"
        self.activity_name = None

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

    def step_1b_detect_gaps(self):
        """Étape 1b : Détecter les séances non analysées"""
        # Skip si activity_id fourni (bypass détection gaps)
        if self.activity_id:
            return

        # Charger état et config Intervals.icu
        state = WorkflowState(project_root=self.project_root)

        # Charger config API
        config_path = Path.home() / ".intervals_config.json"
        if not config_path.exists():
            # Pas de config, skip la détection
            return

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)

            athlete_id = config.get('athlete_id')
            api_key = config.get('api_key')

            if not athlete_id or not api_key:
                return

            # Connexion rapide à l'API pour détecter gaps
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

            # Trier et filtrer
            activities.sort(key=lambda x: x['start_date_local'], reverse=True)
            unanalyzed = state.get_unanalyzed_activities(activities)

            count = len(unanalyzed)

            if count > 1:
                # Plusieurs séances non analysées détectées
                self.clear_screen()
                self.print_header(
                    "🔍 Détection Multi-Séances",
                    "Étape 1b/7 : Gaps détectés"
                )

                print(f"📊 {count} séances non analysées détectées !")
                print()
                print("📝 Détails :")
                for i, act in enumerate(unanalyzed[:5], 1):  # Afficher max 5
                    date = act['start_date_local'][:10]
                    name = act.get('name', 'Séance')[:40]
                    print(f"   {i}. [{date}] {name}")
                if count > 5:
                    print(f"   ... et {count - 5} autres")
                print()
                print("💡 À l'étape suivante (Préparation Prompt), tu pourras :")
                print("   • Analyser la DERNIÈRE séance uniquement")
                print("   • Choisir UNE séance spécifique")
                print("   • Analyser TOUTES en mode batch")
                print()
                print("Le script prepare_analysis.py te proposera un menu interactif.")
                print()

                self.wait_user("Appuyer sur ENTRÉE pour continuer...")

        except Exception as e:
            # En cas d'erreur, skip silencieusement la détection
            pass

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
            import os
            
            # Récupérer la dernière activité pour le contexte
            api = IntervalsAPI(
                athlete_id=os.getenv('VITE_INTERVALS_ATHLETE_ID'),
                api_key=os.getenv('VITE_INTERVALS_API_KEY')
            )
            
            # Récupérer la dernière activité (1 jour)
            from datetime import datetime, timedelta
            oldest = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            newest = datetime.now().strftime('%Y-%m-%d')
            activities = api.get_activities(oldest=oldest, newest=newest) 
            if activities and len(activities) > 0:
                activity = activities[0]
                
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

    def run(self):
        """Orchestrer le workflow complet"""
        try:
            self.step_1_welcome()
            self.step_1b_detect_gaps()  # Nouvelle étape : détection gaps
            self.step_2_collect_feedback()
            self.step_3_prepare_analysis()
            self.step_4_paste_prompt()
            self.step_5_validate_analysis()
            self.step_6_insert_analysis()
            self.step_7_git_commit()
            self.show_summary()

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

  # Skip le feedback athlète
  python3 scripts/workflow_coach.py --skip-feedback

  # Skip le git commit
  python3 scripts/workflow_coach.py --skip-git

  # Analyser une séance spécifique
  python3 scripts/workflow_coach.py --activity-id i123456

  # Mode rapide (pas de feedback ni git)
  python3 scripts/workflow_coach.py --skip-feedback --skip-git
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
        activity_id=args.activity_id
    )

    coach.run()


if __name__ == '__main__':
    main()
