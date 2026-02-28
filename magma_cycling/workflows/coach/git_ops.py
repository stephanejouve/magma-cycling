"""Git operations for WorkflowCoach."""

import subprocess
from datetime import datetime


class GitOpsMixin:
    """Git commit and push operations."""

    def step_7_git_commit(self):
        """Étape 7 : Commit git optionnel."""
        if self.skip_git:
            self.clear_screen()
            self.print_header("⏭️  Git Commit (Skip)", "Étape 7/7 : Sauvegarde (optionnel)")
            print("Le commit git a été skippé (--skip-git).")
            print()
            print("Pour commiter manuellement plus tard (dans ~/training-logs/) :")
            print("  git add workouts-history.md")
            print('  git commit -m "Analyse: Séance du [DATE]"')
            self.wait_user()
            return

        self.clear_screen()
        self.print_header("💾 Sauvegarde Git", "Étape 7/7 : Commit (optionnel)")

        print("Veux-tu commiter cette analyse maintenant ?")
        print()
        print("✅ Avantages :")
        print("   • Historique versionné de toutes tes analyses")
        print("   • Sauvegarde automatique")
        print("   • Synchronisation possible avec remote")
        print()

        commit = input("Commiter maintenant ? (o/n) : ").strip().lower()

        if commit != "o":
            print()
            print("⏭️  Commit skippé.")
            print()
            print("Pour commiter manuellement plus tard (dans ~/training-logs/) :")
            print("  git add workouts-history.md")
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
            short_name = datetime.now().strftime("%Y-%m-%d")

        print(f"Nom de séance détecté : {short_name}")
        custom = input("Utiliser ce nom ? (o pour oui, ou taper un nom personnalisé) : ").strip()

        if custom.lower() != "o" and custom:
            short_name = custom

        # Construire le message de commit
        commit_msg = f"Analyse: {short_name}\n\n🤖 Generated with Claude Code\n\nCo-Authored-By: Claude <noreply@anthropic.com>"

        # Ajouter et commiter
        try:
            # Check if there's something to commit FIRST
            status_check = subprocess.run(
                ["git", "status", "--short", "logs/workouts-history.md"],
                capture_output=True,
                text=True,
                check=True,
            )

            if not status_check.stdout.strip():
                print()
                print("✅ Fichier déjà à jour (rien à commiter)")
                self.wait_user()
                return

            # Only show "Commit en cours..." if there's actually something to commit
            print()
            print("Commit en cours...")

            # Stage changes
            subprocess.run(["git", "add", "logs/workouts-history.md"], check=True)

            # Commit
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            print()
            print("✅ Commit réussi !")

            # Proposer le push
            print()
            push = input("Pousser vers remote ? (o/n) : ").strip().lower()
            if push == "o":
                subprocess.run(["git", "push"], check=True)
                print()
                print("✅ Push réussi !")

        except subprocess.CalledProcessError as e:
            print()
            print(f"⚠️  Erreur git : {e}")
            print("    Tu peux commiter manuellement si nécessaire.")

        self.wait_user()

    def _optional_git_commit(self, default_message):
        """Proposer commit git optionnel (version simplifiée sans clear_screen).

        Args:
            default_message: Message de commit par défaut.
        """
        print()

        print("─" * 70)
        print("💾 Commit Git")
        print("─" * 70)

        commit = input("Commiter les modifications ? (o/n) : ").strip().lower()

        if commit != "o":
            print("   ⏭️  Commit skippé")
            return

        # Message de commit
        commit_msg = f"{default_message}\n\n🤖 Generated with Claude Code\n\nCo-Authored-By: Claude <noreply@anthropic.com>"

        try:
            # Check if there's something to commit
            status_check = subprocess.run(
                ["git", "status", "--short", "logs/workouts-history.md"],
                capture_output=True,
                text=True,
                check=True,
            )

            if not status_check.stdout.strip():
                print("   ℹ️  Fichier déjà à jour (rien à commiter)")
                return

            # Stage and commit
            subprocess.run(
                ["git", "add", "logs/workouts-history.md"], check=True, capture_output=True
            )
            subprocess.run(["git", "commit", "-m", commit_msg], check=True, capture_output=True)
            print("   ✅ Commit réussi !")

            # Proposer push
            push = input("Pousser vers remote ? (o/n) : ").strip().lower()
            if push == "o":
                subprocess.run(["git", "push"], check=True, capture_output=True)
                print("   ✅ Push réussi !")

        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Erreur git : {e}")

        print("─" * 70)
