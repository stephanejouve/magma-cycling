#!/usr/bin/env python3
"""
Orchestrateur du workflow d'analyse de séance.

Guide l'utilisateur à travers le processus complet d'analyse de séance cyclisme :
détection du type de session, collecte du feedback athlète, préparation du prompt IA,
exécution de l'analyse (multi-provider support), validation, insertion dans l'historique,
et commit git automatique.

Examples:
    Command-line usage::

        # Analyse interactive avec détection automatique
        poetry run workflow-coach

        # Analyse d'une activité spécifique
        poetry run workflow-coach --activity-id i113782165

        # Utiliser un provider IA spécifique
        poetry run workflow-coach --activity-id i113782165 --provider mistral_api

        # Mode automatique sans feedback ni git
        poetry run workflow-coach --activity-id i113782165 --skip-feedback --skip-git

    Programmatic usage::

        from magma_cycling.workflow_coach import WorkflowCoach

        # Initialisation et exécution workflow
        coach = WorkflowCoach(
            skip_feedback=False,
            skip_git=False,
            activity_id="i113782165",
            provider="mistral_api"
        )
        coach.run()

Author: Claude Code
Created: 2024-11-15
"""

import argparse
import hashlib
import logging
import sys

from magma_cycling.ai_providers import AIProviderFactory
from magma_cycling.config import get_ai_config, get_data_config
from magma_cycling.paths import get_project_root
from magma_cycling.utils.cli import cli_main
from magma_cycling.workflows.coach._ui import UIHelpersMixin
from magma_cycling.workflows.coach.ai_analysis import AIAnalysisMixin
from magma_cycling.workflows.coach.feedback import FeedbackMixin
from magma_cycling.workflows.coach.gap_detection import GapDetectionMixin
from magma_cycling.workflows.coach.git_ops import GitOpsMixin
from magma_cycling.workflows.coach.history import HistoryMixin
from magma_cycling.workflows.coach.intervals_api import IntervalsAPIMixin
from magma_cycling.workflows.coach.reconciliation import ReconciliationMixin
from magma_cycling.workflows.coach.servo_control import ServoControlMixin
from magma_cycling.workflows.coach.session_display import SessionDisplayMixin
from magma_cycling.workflows.coach.special_sessions import SpecialSessionsMixin

logger = logging.getLogger(__name__)


class WorkflowCoach(
    UIHelpersMixin,
    GapDetectionMixin,
    FeedbackMixin,
    AIAnalysisMixin,
    SessionDisplayMixin,
    HistoryMixin,
    SpecialSessionsMixin,
    ServoControlMixin,
    IntervalsAPIMixin,
    GitOpsMixin,
    ReconciliationMixin,
):
    """Orchestrateur du workflow d'analyse de séance."""

    def __init__(
        self,
        skip_feedback=False,
        skip_git=False,
        activity_id=None,
        week_id=None,
        servo_mode=False,
        provider=None,
        auto_mode=False,
    ):
        """Initialize the workflow coach.

        Args:
            skip_feedback: Skip feedback collection step
            skip_git: Skip git commit step
            activity_id: Specific activity ID to analyze (bypass detection)
            week_id: Specific week ID for context
            servo_mode: Enable servo mode for session management
            provider: AI provider to use (openai, claude, mistral, ollama, clipboard)
            auto_mode: Enable automatic mode (minimal prompts)
        """
        self.skip_feedback = skip_feedback
        self.skip_git = skip_git
        self.activity_id = activity_id
        self.week_id = week_id
        self.servo_mode = servo_mode
        self.provider_name = provider
        self.auto_mode = auto_mode
        self.project_root = get_project_root()
        self.scripts_dir = self.project_root / "magma_cycling"
        self.activity_name = None

        # Use data repo config if available
        try:
            self.config = get_data_config()
            self.data_repo_path = self.config.data_repo_path
        except FileNotFoundError:
            # Fallback: use project_root/logs (legacy)
            self.config = None
            self.data_repo_path = self.project_root / "logs"

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

        # API client (lazy initialization via _get_api())
        self.api = None

        # Load workout templates if servo mode enabled
        if self.servo_mode:
            self.workout_templates = self.load_workout_templates()

        # AI Provider Setup
        self.ai_config = get_ai_config()

        # Determine provider to use
        if provider is None:
            # Auto-detect: use first available provider in fallback chain
            available = self.ai_config.get_available_providers()
            provider = available[0] if available else "clipboard"
            logger.info(f"Auto-selected AI provider: {provider}")
        else:
            logger.info(f"Using specified AI provider: {provider}")

        # Validate and initialize provider
        if not self.ai_config.is_provider_configured(provider):
            logger.warning(f"Provider {provider} not configured, falling back to clipboard")
            provider = "clipboard"

        provider_config = self.ai_config.get_provider_config(provider)
        self.ai_analyzer = AIProviderFactory.create(provider, provider_config)
        self.current_provider = provider

        logger.info(f"AI Analyzer initialized: {self.ai_analyzer.__class__.__name__}")

    def step_1_welcome(self):
        """Étape 1 : Message de bienvenue."""
        self.clear_screen()

        self.print_header(
            "🎯 WORKFLOW COACH - Analyse de Séance",
            "Orchestrateur intelligent pour l'analyse cyclisme",
        )

        print("Ce workflow va te guider à travers 6 étapes :")
        print()
        print("1. ✅ Bienvenue et présentation")
        print("2. 💭 Collecte feedback athlète (optionnel)")
        print("3. 📝 Préparation prompt d'analyse")
        print("4. 🤖 Analyse par IA")
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

    def _compute_gaps_signature(self, gaps_data: dict) -> str:
        """Calculate signature unique des gaps actuels pour détecter changements.

        Args:
            gaps_data: Dict avec listes unanalyzed, skipped, rest_days, cancelled

        Returns:
            str: Hash MD5 des IDs de toutes sessions détectées.
        """
        ids = []

        # Activités non analysées
        for act in gaps_data.get("unanalyzed", []):
            ids.append(f"act_{act.get('id', '')}")

        # Séances sautées
        for skip in gaps_data.get("skipped", []):
            planned_name = skip.get("planned_name", "")
            session_id = planned_name.split(" - ")[0] if " - " in planned_name else planned_name
            date = skip.get("planned_date", "")
            ids.append(f"skip_{session_id}_{date}")

        # Repos planifiés
        for rest in gaps_data.get("rest_days", []):
            ids.append(f"rest_{rest.get('session_id', '')}_{rest.get('date', '')}")

        # Annulations
        for cancel in gaps_data.get("cancelled", []):
            ids.append(f"cancel_{cancel.get('session_id', '')}_{cancel.get('date', '')}")

        # Trier et hasher
        ids_sorted = sorted(ids)
        signature = hashlib.md5("|".join(ids_sorted).encode()).hexdigest()
        return signature

    def run(self):
        """Orchestrer le workflow complet avec détection unifiée des gaps (mode boucle)."""
        try:
            # Étape 1 : Accueil (une seule fois)
            self.step_1_welcome()

            # PHASE 4: Tracking signature gaps pour sortie intelligente
            seen_gaps_signature = None
            iteration_count = 0

            # === BOUCLE PRINCIPALE : Traiter gaps jusqu'à épuisement ===
            while True:
                iteration_count += 1

                # Étape 1b : Détection unifiée gaps (exécutées + repos + annulations)
                choice, gaps_data = self.step_1b_detect_all_gaps()

                # PHASE 4: Calculer signature gaps actuels
                current_signature = self._compute_gaps_signature(gaps_data)

                # PHASE 4: Vérifier si nouveaux gaps détectés
                if seen_gaps_signature is not None:
                    if current_signature == seen_gaps_signature:
                        print("\n" + "=" * 70)
                        print("✅ TOUS LES GAPS TRAITÉS !")
                        print("=" * 70)
                        print("   Aucun nouveau gap détecté après traitement.")
                        print(f"   Itérations effectuées : {iteration_count - 1}")
                        print()
                        break  # SORTIE : Pas de nouveaux gaps

                # Mettre à jour signature
                seen_gaps_signature = current_signature

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

                    # Step 4 only for clipboard provider (manual paste)
                    # API providers already completed analysis in step 3
                    if self.current_provider == "clipboard":
                        self.step_4_paste_prompt()

                    # Display analysis to athlete (both clipboard and API providers)
                    self.step_4b_display_analysis()

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
                    self.wait_user("\nAppuyer sur ENTRÉE pour continuer...")
                    # Continue la boucle → retour step_1b pour gaps restants

                elif choice == "batch_rest_cancelled":
                    # P2 FIX: Traiter repos/annulations uniquement
                    result = self._handle_rest_cancellations()

                    if result == "continue":
                        # Enrichissement IA choisi → continuer workflow
                        # Step 4 only for clipboard provider
                        if self.current_provider == "clipboard":
                            self.step_4_paste_prompt()
                        # Display analysis to athlete
                        self.step_4b_display_analysis()
                        self.step_5_validate_analysis()
                        self.step_6_insert_analysis()
                        self.step_7_git_commit()
                        self.show_summary()
                    else:
                        # Actions terminées (export/copie/insertion directe)
                        # Proposer commit git optionnel
                        if not self.skip_git:
                            self._optional_git_commit("Sessions repos/annulations documentées")
                        print("\n✅ Sessions repos/annulations documentées")

                    # Message retour boucle
                    print("\n" + "═" * 70)
                    print("🔄 Retour détection gaps pour sessions restantes...")
                    print("═" * 70)
                    self.wait_user("\nAppuyer sur ENTRÉE pour continuer...")
                    # Continue la boucle → retour step_1b pour gaps restants

                elif choice == "batch_skipped":
                    # P2 FIX: Traiter séances sautées uniquement
                    result = self._handle_skipped_sessions(gaps_data["skipped"])

                    if result == "continue":
                        # Enrichissement IA choisi → continuer workflow
                        # Step 4 only for clipboard provider
                        if self.current_provider == "clipboard":
                            self.step_4_paste_prompt()
                        # Display analysis to athlete
                        self.step_4b_display_analysis()
                        self.step_5_validate_analysis()
                        self.step_6_insert_analysis()
                        self.step_7_git_commit()
                        self.show_summary()
                    else:
                        # Actions terminées (export/copie/insertion directe)
                        # Proposer commit git optionnel
                        if not self.skip_git:
                            self._optional_git_commit("Sessions sautées documentées")
                        print("\n✅ Sessions sautées documentées")

                    # Message retour boucle
                    print("\n" + "═" * 70)
                    print("🔄 Retour détection gaps pour sessions restantes...")
                    print("═" * 70)
                    self.wait_user("\nAppuyer sur ENTRÉE pour continuer...")
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


@cli_main
def main():
    """Command-line entry point for workout analysis workflow coach."""
    parser = argparse.ArgumentParser(
        description="Orchestrateur du workflow d'analyse de séance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:

  # Workflow complet interactif
  python3 magma_cycling/workflow_coach.py

  # Mode réconciliation avec planning hebdomadaire
  python3 magma_cycling/workflow_coach.py --week-id S070

  # Skip le feedback athlète
  python3 magma_cycling/workflow_coach.py --skip-feedback

  # Skip le git commit
  python3 magma_cycling/workflow_coach.py --skip-git

  # Analyser une séance spécifique
  python3 magma_cycling/workflow_coach.py --activity-id i123456

  # Mode rapide (pas de feedback ni git)
  python3 magma_cycling/workflow_coach.py --skip-feedback --skip-git

  # Mode réconciliation + rapide
  python3 magma_cycling/workflow_coach.py --week-id S070 --skip-feedback --skip-git.
        """,
    )

    parser.add_argument(
        "--skip-feedback", action="store_true", help="Ne pas collecter le feedback athlète"
    )

    parser.add_argument("--skip-git", action="store_true", help="Ne pas proposer le commit git")

    parser.add_argument(
        "--activity-id", help="ID de l'activité spécifique à analyser (sinon prend la dernière)"
    )

    parser.add_argument("--week-id", help="ID semaine pour mode réconciliation planning (ex: S070)")

    parser.add_argument(
        "--servo-mode",
        action="store_true",
        help="Activer le mode asservissement (modifications planning AI)",
    )

    parser.add_argument(
        "--provider",
        type=str,
        choices=["clipboard", "claude_api", "mistral_api", "openai", "ollama"],
        default=None,
        help="AI provider à utiliser (défaut: auto-détection)",
    )

    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="Lister les providers AI disponibles et quitter",
    )

    parser.add_argument(
        "--reconcile",
        action="store_true",
        help="Mode réconciliation batch pour séances sautées/annulées (requiert --week-id)",
    )

    parser.add_argument(
        "--auto",
        action="store_true",
        help="Mode automatique non-interactif (skip tous les wait/input)",
    )

    args = parser.parse_args()

    # Handle --list-providers
    if args.list_providers:
        config = get_ai_config()

        print("\n📋 AI PROVIDERS DISPONIBLES\n")
        all_providers = {
            "clipboard": "Manual copy/paste (gratuit, sans API)",
            "claude_api": "Claude Sonnet 4 ($3/1M entrée, $15/1M sortie)",
            "mistral_api": "Mistral Large ($2/1M entrée, $6/1M sortie)",
            "openai": "GPT-4 Turbo ($10/1M entrée, $30/1M sortie)",
            "ollama": "LLMs locaux (gratuit, requiert Ollama installé)",
        }

        available = config.get_available_providers()
        for provider, description in all_providers.items():
            status = "✅" if provider in available else "❌"
            print(f"{status} {provider:15} - {description}")

        print(f"\n🔧 Provider par défaut : {config.default_provider}")
        print(f"🔄 Fallback activé : {config.enable_fallback}")
        print()
        sys.exit(0)

    # Validation --reconcile requiert --week-id
    if args.reconcile and not args.week_id:
        print("❌ Erreur: --reconcile requiert --week-id")
        print("   Exemple: poetry run workflow-coach --reconcile --week-id S070")
        sys.exit(1)

    # Note: CWD check removed - config.py handles paths automatically
    # Works from both code repo and data repo

    # Lancer le workflow
    coach = WorkflowCoach(
        skip_feedback=args.skip_feedback,
        skip_git=args.skip_git,
        activity_id=args.activity_id,
        week_id=args.week_id,
        servo_mode=args.servo_mode,
        provider=args.provider,
        auto_mode=args.auto,
    )

    # Mode réconciliation batch
    if args.reconcile:
        coach.reconcile_week(args.week_id)
    else:
        coach.run()


if __name__ == "__main__":
    main()
