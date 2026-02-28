"""Session display and validation methods for WorkflowCoach."""

import logging
import subprocess
import sys

logger = logging.getLogger(__name__)

# Provider display names for UI messages
PROVIDER_DISPLAY_NAMES = {
    "clipboard": "Claude.ai (manuel)",
    "mistral_api": "Mistral AI",
    "claude_api": "Claude API",
    "openai": "OpenAI",
    "ollama": "Ollama",
}


class SessionDisplayMixin:
    """Display analysis results, validation, and summary."""

    def step_4_paste_prompt(self):
        """Étape 4 : Instructions pour coller le prompt dans Claude."""
        self.clear_screen()

        # Afficher le nom de la séance dans le header
        # Get provider display name
        provider_name = PROVIDER_DISPLAY_NAMES.get(self.current_provider, "IA")

        subtitle = "Étape 4/7 : Envoi du prompt"
        if self.activity_name:
            subtitle += f"\n🚴 {self.activity_name}"

        self.print_header(f"🤖 Analyse par {provider_name}", subtitle)

        print("Le prompt est prêt dans ton presse-papier.")
        print()
        print("📋 INSTRUCTIONS :")
        print()
        print("1. Ouvrir votre IA (Claude.ai, ChatGPT, etc.)")
        print("   → https://claude.ai ou votre plateforme préférée")
        print()
        print("2. Coller le prompt (Cmd+V ou Ctrl+V)")
        print()
        print("3. Envoyer le message")
        print()
        print("4. Attendre la réponse de l'IA (~30-60 secondes)")
        print()
        print("5. Copier UNIQUEMENT le bloc markdown de l'analyse")
        print("   → Du premier ### jusqu'à la dernière ligne")
        print("   → Ne pas inclure le texte explicatif")
        print()
        print("⏱️  Temps estimé : 1-2 minutes")
        print()
        print("⚠️  IMPORTANT : Ne copier que le markdown, pas le texte autour !")
        print()

        self.wait_user("Appuyer sur ENTRÉE une fois la réponse copiée...")

    def step_4b_display_analysis(self):
        """Étape 4b : Afficher l'analyse générée à l'athlète."""
        self.clear_screen()

        # Afficher le nom de la séance dans le header
        subtitle = "Étape 4b/7 : Présentation de l'analyse"
        if self.activity_name:
            subtitle += f"\n🚴 {self.activity_name}"

        self.print_header("📊 Analyse Générée", subtitle)

        # Get analysis from clipboard or self.analysis_result
        analysis_text = None

        if hasattr(self, "analysis_result") and self.analysis_result:
            # API provider: use stored result
            analysis_text = self.analysis_result
        else:
            # Clipboard provider: read from clipboard
            try:
                result = subprocess.run(["pbpaste"], capture_output=True, text=True, check=True)
                analysis_text = result.stdout
            except Exception as e:
                logger.error(f"Failed to read from clipboard: {e}")
                print("⚠️  Impossible de lire l'analyse depuis le presse-papier")
                print("   L'affichage sera sauté")
                print()
                self.wait_user()
                return

        if not analysis_text or len(analysis_text.strip()) < 50:
            print("⚠️  Aucune analyse trouvée ou trop courte")
            print("   L'affichage sera sauté")
            print()
            self.wait_user()
            return

        # Display analysis with formatting
        print("Voici l'analyse générée par l'IA pour votre séance :")
        print()
        self.print_separator()
        print()

        # Display analysis (with word wrap for better readability)
        lines = analysis_text.split("\n")
        for line in lines:
            print(line)

        print()
        self.print_separator()
        print()

        # Show stats
        word_count = len(analysis_text.split())
        char_count = len(analysis_text)
        print(f"📊 Statistiques : {word_count} mots, {char_count} caractères")
        print()

        self.wait_user("Appuyer sur ENTRÉE pour continuer vers la validation...")

    def step_5_validate_analysis(self):
        """Étape 5 : Valider la réponse de Claude."""
        self.clear_screen()

        # Afficher le nom de la séance dans le header
        subtitle = "Étape 5/7 : Vérification qualité"
        if self.activity_name:
            subtitle += f"\n🚴 {self.activity_name}"

        self.print_header("✅ Validation de l'Analyse", subtitle)

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
            if self.auto_mode:
                # En mode auto, valider automatiquement
                valid = "o"
                print("\n[AUTO MODE] Validation automatique : oui")
            else:
                valid = input("✓ L'analyse est-elle valide et prête ? (o/n) : ").strip().lower()

            if valid in ["o", "n"]:
                break
            print("⚠️  Répondre 'o' ou 'n'")

        if valid != "o":
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

    def show_summary(self):
        """Display le résumé final."""
        self.clear_screen()

        self.print_header("🎉 Workflow Terminé !", "Analyse de séance complète")

        print("✅ RÉCAPITULATIF :")
        print()
        print(f"   Feedback collecté : {'Non' if self.skip_feedback else 'Oui'}")
        print("   Analyse insérée : Oui")
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
