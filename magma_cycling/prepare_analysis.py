#!/usr/bin/env python3
"""
Génération du prompt d'analyse pour IA Coach.

Prépare le prompt d'analyse de séance cyclisme pour traitement par IA.
Récupère les données depuis Intervals.icu, agrège le contexte athlète,
les zones de puissance, les logs récents, et génère un prompt structuré
optimisé pour analyse qualitative par LLM.

Examples:
    Command-line usage::

        # Analyse de la dernière activité
        poetry run prepare-analysis

        # Analyse d'une activité spécifique
        poetry run prepare-analysis --activity-id i113782165

        # Avec fichier config personnalisé
        poetry run prepare-analysis --config ~/.intervals_custom.json

    Programmatic usage::

        from magma_cycling.prepare_analysis import PromptGenerator
        from magma_cycling.prepare_analysis import IntervalsAPI

        # Initialisation API
        api = IntervalsAPI(
            athlete_id="iXXXXXX",
            api_key="your_api_key"
        )

        # Récupération activité
        activity = api.get_activity("i113782165")

        # Génération prompt
        generator = PromptGenerator(
            activity_data=activity,
            power_zones=power_zones,
            context_path="~/training-logs/context.md"
        )
        prompt = generator.generate_full_prompt()

Author: Claude Code
Created: 2024-11-15
Updated: 2025-12-26 (Added Gartner TIME tags)

Metadata:
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: I
    Status: Production
    Priority: P0
    Version: v2
"""
import argparse
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from magma_cycling.api.intervals_client import IntervalsClient
from magma_cycling.config import create_intervals_client, get_ai_config
from magma_cycling.paths import get_project_root
from magma_cycling.utils.cli import cli_main
from magma_cycling.workflow_state import WorkflowState
from magma_cycling.workflows.prompt.context_loading import ContextLoadingMixin
from magma_cycling.workflows.prompt.data_formatting import DataFormattingMixin
from magma_cycling.workflows.prompt.metric_helpers import MetricHelpersMixin
from magma_cycling.workflows.prompt.prompt_assembly import PromptAssemblyMixin


class PromptGenerator(
    ContextLoadingMixin,
    DataFormattingMixin,
    MetricHelpersMixin,
    PromptAssemblyMixin,
):
    """Générateur de prompt pour analyse IA."""

    def __init__(self, project_root=None):
        """
        Initialize PromptGenerator.

        Args:
            project_root: Legacy parameter, use data repo config instead
        """
        from magma_cycling.config import get_data_config

        # Use data repo config if available
        if project_root is None:
            try:
                config = get_data_config()
                self.data_repo_path = config.data_repo_path
                self.logs_dir = config.data_repo_path  # For backward compat
                # References dir stays in code repo
                self.project_root = get_project_root()
                self.references_dir = self.project_root / "references"
            except FileNotFoundError:
                # Fallback to code repo root (legacy)
                self.project_root = get_project_root()
                self.references_dir = self.project_root / "references"
                self.logs_dir = self.project_root / "logs"
        else:
            # Legacy: explicit project_root provided
            self.project_root = Path(project_root)
            self.references_dir = self.project_root / "references"
            self.logs_dir = self.project_root / "logs"

        self.feedback_dir = Path(".athlete_feedback")
        self.feedback_file = self.feedback_dir / "last_feedback.json"


def analyze_batch(api, unanalyzed_activities, generator, state, project_root):
    """Analyze plusieurs activités en mode batch.

    Args:
        api: Instance IntervalsAPI
        unanalyzed_activities: Liste des activités à analyser
        generator: Instance PromptGenerator
        state: Instance WorkflowState
        project_root: Racine du projet

    Returns:
        None.
    """
    total = len(unanalyzed_activities)

    print()
    print("=" * 60)
    print(f"🔄 MODE BATCH : {total} SÉANCES À ANALYSER")
    print("=" * 60)
    print()
    print("📝 Processus :")
    print("  1. Génération du prompt pour chaque séance")
    print("  2. Vous collez dans votre IA et copiez la réponse")
    print("  3. Proposition d'insertion automatique")
    print("  4. Passage à la séance suivante")
    print()
    input("Appuyez sur Entrée pour commencer...")

    for idx, activity in enumerate(unanalyzed_activities, 1):
        print()
        print("=" * 60)
        print(f"📊 SÉANCE {idx}/{total}")
        print("=" * 60)

        activity_id = activity["id"]
        activity_name = activity.get("name", "Séance")
        activity_date_str = activity["start_date_local"][:10]

        print()
        print(f"🚴 {activity_name}")
        print(f"   📅 {activity_date_str} | ID: {activity_id}")
        print()

        try:
            # Récupérer les détails complets
            print("📥 Récupération des détails...")
            full_activity = api.get_activity(activity_id)
            activity_date = datetime.fromisoformat(
                full_activity["start_date_local"].replace("Z", "+00:00")
            )
            date_str = activity_date_str

            # Wellness
            wellness_data = api.get_wellness(oldest=date_str, newest=date_str)
            wellness = wellness_data[0] if wellness_data else None

            # Workout planifié
            print("🔍 Recherche du workout planifié...")
            planned_workout = api.get_planned_workout(activity_id, activity_date)
            if planned_workout:
                print(f"   ✅ Workout planifié : {planned_workout.get('name', 'N/A')}")
            else:
                print("   ℹ️  Pas de workout planifié")

            # Proposer collecte feedback athlète
            print()
            collect_feedback = (
                input("💭 Collecter ton ressenti pour cette séance ? (o/n) : ").strip().lower()
            )

            if collect_feedback == "o":
                # Choisir le mode
                print()
                print("Mode feedback :")
                print("  1 - Quick (30s) : RPE + ressenti général")
                print("  2 - Full (2-3min) : RPE + ressenti + difficultés + contexte + sensations")
                mode_choice = input("Choix (1/2) : ").strip()

                feedback_mode = "--quick" if mode_choice == "1" else None

                print()
                print(
                    f"🔄 Lancement de la collecte feedback ({'quick' if feedback_mode else 'full'})..."
                )
                print()

                # Extraire les métriques de l'activité
                duration_min = full_activity.get("moving_time", 0) // 60
                tss = full_activity.get("icu_training_load", 0)
                if_value = (
                    full_activity.get("icu_intensity", 0) / 100.0
                    if full_activity.get("icu_intensity")
                    else 0
                )

                # Construire la commande avec contexte
                feedback_script = Path(project_root) / "scripts" / "collect_athlete_feedback.py"
                feedback_cmd = [
                    "python3",
                    str(feedback_script),
                    "--activity-name",
                    activity_name,
                    "--activity-date",
                    activity_date_str,
                    "--activity-duration",
                    str(duration_min),
                    "--activity-tss",
                    str(tss),
                    "--activity-if",
                    str(if_value),
                    "--batch-position",
                    f"{idx}/{total}",
                ]

                # Ajouter --quick si mode 1
                if feedback_mode:
                    feedback_cmd.insert(2, feedback_mode)

                result = subprocess.run(feedback_cmd)

                if result.returncode != 0:
                    print()
                    print("⚠️  Erreur lors de la collecte du feedback")
                    print("   L'analyse continuera sans feedback")
                else:
                    print()
                    print("✅ Feedback collecté !")

                print()

            # Charger contexte
            print("📖 Chargement du contexte...")
            athlete_context = generator.load_athlete_context()
            recent_workouts = generator.load_recent_workouts(limit=3)
            cycling_concepts = generator.load_cycling_concepts()
            athlete_feedback = generator.load_athlete_feedback()
            periodization_context = generator.load_periodization_context(wellness)

            if athlete_feedback:
                print("   ✅ Feedback athlète intégré au prompt")

            if periodization_context:
                print(f"   ✅ Contexte périodisation : Phase {periodization_context['phase']}")

            # Générer prompt
            print("✍️  Génération du prompt...")
            prompt = generator.generate_prompt(
                activity_data=generator.format_activity_data(full_activity),
                wellness_pre=wellness,
                wellness_post=wellness,
                athlete_context=athlete_context,
                recent_workouts=recent_workouts,
                athlete_feedback=athlete_feedback,
                planned_workout=planned_workout,
                cycling_concepts=cycling_concepts,
                periodization_context=periodization_context,
            )

            # Copier dans le presse-papier
            print("📋 Copie dans le presse-papier...")
            if not generator.copy_to_clipboard(prompt):
                print("   ⚠️  Échec de la copie, passage à la suivante...")
                continue

            print("   ✅ Prompt copié !")
            print()
            print("-" * 60)
            print("📝 ACTIONS UTILISATEUR :")
            print("-" * 60)
            print("1. Ouvrir votre IA (Claude.ai, ChatGPT, etc.)")
            print("2. Coller le prompt (Cmd+V)")
            print("3. Attendre l'analyse de votre IA")
            print("4. Copier UNIQUEMENT le bloc markdown généré")
            print("5. Revenir ici et appuyer sur Entrée")
            print("-" * 60)
            print()

            input("✋ Appuyez sur Entrée quand vous avez copié la réponse de votre IA...")

            # Proposer insertion automatique
            print()
            insert_choice = (
                input("Insérer automatiquement dans workouts-history.md ? (o/n) : ").strip().lower()
            )

            if insert_choice == "o":
                # Lancer insert_analysis.py
                print("🔄 Lancement de l'insertion...")
                insert_script = Path(project_root) / "scripts" / "insert_analysis.py"

                result = subprocess.run(
                    ["python3", str(insert_script)], capture_output=False, text=True
                )

                if result.returncode == 0:
                    print("   ✅ Insertion réussie")
                else:
                    print("   ⚠️  Erreur lors de l'insertion (vous pourrez réessayer manuellement)")

            # Marquer comme analysée
            state.mark_analyzed(activity_id, activity_date.strftime("%Y-%m-%d"))
            print(f"   ✅ Activité {activity_id} marquée comme analysée")

            # Effacer feedback si utilisé
            if athlete_feedback and generator.feedback_file.exists():
                generator.feedback_file.unlink()
                print("   ✅ Feedback athlète consommé")

            print()
            if idx < total:
                print(f"➡️  Passage à la séance {idx + 1}/{total}...")
                print()

        except Exception as e:
            print(f"❌ Erreur lors du traitement de l'activité {activity_id}: {e}")
            skip = input("Continuer avec les séances suivantes ? (o/n) : ").strip().lower()
            if skip != "o":
                print("❌ Mode batch interrompu")
                return

    print()
    print("=" * 60)
    print(f"✅ MODE BATCH TERMINÉ : {total} SÉANCES TRAITÉES")
    print("=" * 60)


def display_activity_menu(unanalyzed_activities):
    """Display le menu interactif pour sélectionner une activité.

    Args:
        unanalyzed_activities: Liste des activités non analysées

    Returns:
        Tuple (mode, selected_activity_id) où mode peut être:
        - 'single': analyser une seule activité (selected_activity_id fourni)
        - 'batch': analyser plusieurs activités (selected_activity_id = None)
        - 'cancel': annuler (selected_activity_id = None).
    """
    count = len(unanalyzed_activities)

    if count == 0:
        print("✅ Aucune activité non analysée !")
        print()
        return ("cancel", None)

    print()
    print("=" * 60)
    print(
        f"📊 {count} ACTIVITÉ{'S' if count > 1 else ''} NON ANALYSÉE{'S' if count > 1 else ''} DÉTECTÉE{'S' if count > 1 else ''}"
    )
    print("=" * 60)
    print()

    # Afficher les activités
    for i, activity in enumerate(unanalyzed_activities, 1):
        date = activity["start_date_local"][:10]
        name = activity.get("name", "Séance")
        activity_id = activity["id"]
        tss = activity.get("icu_training_load", 0)
        duration_min = activity.get("moving_time", 0) // 60
        print(f"{i}. [{date}] {name}")
        print(f"   ID: {activity_id} | Durée: {duration_min}min | TSS: {tss:.0f}")
        print()

    print("=" * 60)
    print()

    if count == 1:
        # Cas 1 activité : proposer d'analyser directement
        print("OPTIONS :")
        print("  1 - Analyser cette séance")
        print("  0 - Annuler")
        print()
        choice = input("Votre choix : ").strip()

        if choice == "1":
            return ("single", unanalyzed_activities[0]["id"])
        else:
            print("❌ Analyse annulée")
            return ("cancel", None)

    else:
        # Cas 2+ activités : menu complet
        print("OPTIONS :")
        print("  1 - Analyser la DERNIÈRE séance uniquement")
        print("  2 - Choisir UNE séance spécifique")
        print("  3 - Analyser TOUTES en mode batch")
        print("  0 - Annuler")
        print()
        choice = input("Votre choix : ").strip()

        if choice == "1":
            return ("single", unanalyzed_activities[0]["id"])

        elif choice == "2":
            print()
            selection = input(f"Numéro de la séance (1-{count}) : ").strip()
            try:
                idx = int(selection) - 1
                if 0 <= idx < count:
                    return ("single", unanalyzed_activities[idx]["id"])
                else:
                    print("❌ Numéro invalide")
                    return ("cancel", None)
            except ValueError:
                print("❌ Entrée invalide")
                return ("cancel", None)

        elif choice == "3":
            return ("batch", None)

        else:
            print("❌ Analyse annulée")
            return ("cancel", None)


@cli_main
def main():
    """Command-line entry point for preparing workout analysis."""
    parser = argparse.ArgumentParser(description="Préparer le prompt d'analyse pour IA")

    parser.add_argument("--athlete-id", help="ID de l'athlète Intervals.icu (ex: i123456)")
    parser.add_argument("--api-key", help="Clé API Intervals.icu")
    parser.add_argument(
        "--activity-id", help="ID de l'activité spécifique à analyser (sinon prend la dernière)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Lister les activités non analysées sans lancer l'analyse",
    )
    parser.add_argument(
        "--project-root", default=".", help="Racine du projet (défaut: répertoire courant)"
    )

    args = parser.parse_args()

    # Create client: CLI args override centralized config
    if args.athlete_id and args.api_key:
        api = IntervalsClient(athlete_id=args.athlete_id, api_key=args.api_key)
    else:
        api = create_intervals_client()

    # Initialiser WorkflowState
    state = WorkflowState(project_root=Path(args.project_root))

    print("🔄 Préparation du prompt d'analyse...")
    print()

    # Mode --activity-id : comportement existant préservé (bypass détection gaps)
    if args.activity_id:
        print(f"📥 Récupération de l'activité {args.activity_id}...")
        activity = api.get_activity(args.activity_id)
        activities = [activity]

    else:
        # Détection des activités non analysées
        print("🔍 Détection des séances non analysées...")

        # Récupérer les activités récentes depuis la dernière analyse (ou 7 jours si première fois)
        last_analyzed_id = state.get_last_analyzed_id()

        if last_analyzed_id:
            # Il y a eu des analyses précédentes : chercher depuis 30 jours max
            newest_date = datetime.now()
            oldest_date = newest_date - timedelta(days=30)
            print(f"   Dernière analyse : {last_analyzed_id}")
        else:
            # Première utilisation : chercher dans les 7 derniers jours
            newest_date = datetime.now()
            oldest_date = newest_date - timedelta(days=7)
            print("   Première utilisation (dernières 7 jours)")

        activities = api.get_activities(
            oldest=oldest_date.strftime("%Y-%m-%d"), newest=newest_date.strftime("%Y-%m-%d")
        )

        if not activities:
            print("❌ Aucune activité trouvée")
            sys.exit(1)

        # Trier par date décroissante (plus récente en premier)
        activities.sort(key=lambda x: x["start_date_local"], reverse=True)

        # Filtrer les activités non analysées
        unanalyzed = state.get_unanalyzed_activities(activities)

        # Mode --list : afficher et sortir
        if args.list:
            if not unanalyzed:
                print("✅ Aucune activité non analysée !")
            else:
                print()
                print(f"📋 {len(unanalyzed)} activité(s) non analysée(s) :")
                print()
                for i, act in enumerate(unanalyzed, 1):
                    date = act["start_date_local"][:10]
                    name = act.get("name", "Séance")
                    activity_id = act["id"]
                    tss = act.get("icu_training_load", 0)
                    duration_min = act.get("moving_time", 0) // 60
                    print(f"{i}. [{date}] {name}")
                    print(f"   ID: {activity_id} | Durée: {duration_min}min | TSS: {tss:.0f}")
                    print()
            sys.exit(0)

        # Afficher le menu interactif
        mode, selected_id = display_activity_menu(unanalyzed)

        if mode == "cancel":
            sys.exit(0)

        elif mode == "batch":
            # Mode batch : analyser toutes les séances
            generator = PromptGenerator(args.project_root)
            analyze_batch(api, unanalyzed, generator, state, args.project_root)
            sys.exit(0)

        elif mode == "single":
            # Analyser une seule activité
            print()
            print(f"📥 Récupération de l'activité {selected_id}...")
            activity = api.get_activity(selected_id)
            activities = [activity]

    # Date de l'activité
    date = activity["start_date_local"][:10]
    activity_date = datetime.fromisoformat(activity["start_date_local"].replace("Z", "+00:00"))

    # Récupérer wellness
    wellness_data = api.get_wellness(oldest=date, newest=date)
    wellness = wellness_data[0] if wellness_data else None

    # Récupérer le workout planifié si disponible
    print(f"   ✅ Activité : {activity.get('name', 'Séance')}")
    print(f"   📅 Date : {date}")

    print("🔍 Recherche du workout planifié...")
    planned_workout = api.get_planned_workout(activity["id"], activity_date)
    if planned_workout:
        print(f"   ✅ Workout planifié trouvé : {planned_workout.get('name', 'N/A')}")
    else:
        print("   ℹ️  Pas de workout planifié associé (séance libre)")

    # Vérifier si l'activité vient de Strava
    if activity.get("source") == "STRAVA":
        print()
        print("   ⚠️  ATTENTION : Cette activité vient de Strava")
        print("   Les données API sont limitées (restriction Strava)")
        print("   Certaines métriques peuvent être manquantes")
        print("   → Vérifier sur Intervals.icu web si besoin")

    print()

    # Générer le prompt
    generator = PromptGenerator(args.project_root)

    print("📖 Chargement du contexte...")
    athlete_context = generator.load_athlete_context()
    recent_workouts = generator.load_recent_workouts(limit=3)
    cycling_concepts = generator.load_cycling_concepts()
    periodization_context = generator.load_periodization_context(wellness)

    # Charger feedback athlète si disponible
    athlete_feedback = generator.load_athlete_feedback()
    if athlete_feedback:
        print("   ✅ Feedback athlète trouvé !")
        if athlete_feedback.get("rpe"):
            print(f"      RPE : {athlete_feedback['rpe']}/10")
        if athlete_feedback.get("ressenti_general"):
            print(f"      Ressenti : {athlete_feedback['ressenti_general'][:50]}...")
    else:
        print("   ℹ️  Pas de feedback athlète (optionnel)")
        print("      → Utiliser collect_athlete_feedback.py pour enrichir l'analyse")

    if periodization_context:
        print(f"   ✅ Contexte périodisation : Phase {periodization_context['phase']}")
        print(
            f"      CTL {periodization_context['ctl_current']:.1f} → {periodization_context['ctl_target']:.0f}"
        )

    print("✍️  Génération du prompt...")
    prompt = generator.generate_prompt(
        activity_data=generator.format_activity_data(activity),
        wellness_pre=wellness,
        wellness_post=wellness,  # Simplifié pour l'instant
        athlete_context=athlete_context,
        recent_workouts=recent_workouts,
        athlete_feedback=athlete_feedback,
        planned_workout=planned_workout,
        cycling_concepts=cycling_concepts,
        periodization_context=periodization_context,
    )

    # Copier dans le presse-papier
    print("📋 Copie dans le presse-papier...")
    if generator.copy_to_clipboard(prompt):
        print("   ✅ Prompt copié !")

        # NOTE: Activity will be marked as analyzed AFTER successful insertion
        # by insert_analysis.py or workflow_coach.py, not here!

        # Effacer le feedback après utilisation
        if athlete_feedback and generator.feedback_file.exists():
            generator.feedback_file.unlink()
            print("   ✅ Feedback athlète consommé et effacé")
    else:
        print("   ⚠️  Échec de la copie, affichage du prompt :")
        print()
        print(prompt)

    print()
    print("=" * 60)

    # Get active provider to show appropriate instructions
    ai_config = get_ai_config()
    provider = ai_config.default_provider

    # API providers list (automated workflow)
    API_PROVIDERS = ["claude_api", "mistral_api", "openai", "ollama"]

    if provider in API_PROVIDERS:
        # API providers - automated workflow
        print("✅ PROMPT GÉNÉRÉ ET ENVOYÉ À L'IA")
        print("=" * 60)
        print()
        print("⏳ Analyse en cours via API...")
        print("   Le résultat sera automatiquement disponible.")
        print()
    else:
        # Clipboard - manual workflow (generic)
        print("✅ PROMPT PRÊT POUR ANALYSE")
        print("=" * 60)
        print()
        print("📝 ÉTAPES SUIVANTES :")
        print()
        print("1. Ouvrir votre IA préférée dans votre navigateur")
        print("   Exemples : Claude.ai, ChatGPT, etc.")
        print("   → https://claude.ai (si vous utilisez Claude)")
        print()
        print("2. Coller le prompt (Cmd+V)")
        print()
        print("3. Attendre l'analyse de votre IA")
        print()
        print("4. Copier la réponse (UNIQUEMENT le bloc markdown)")
        print()
        print("5. Exécuter le script d'insertion :")
        print("   python3 magma_cycling/insert_analysis.py")
        print()

    print("=" * 60)


if __name__ == "__main__":
    main()
