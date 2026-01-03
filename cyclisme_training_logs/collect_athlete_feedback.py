#!/usr/bin/env python3
"""
collect_athlete_feedback.py - Collecte le retour de l'athlète après séance

Ce script :
1. Pose des questions structurées à l'athlète
2. Collecte RPE, ressenti, difficultés, points positifs
3. Sauvegarde dans un fichier temporaire JSON
4. prepare_analysis.py l'intègre automatiquement au prompt

Usage:
    python3 cyclisme_training_logs/collect_athlete_feedback.py
    python3 cyclisme_training_logs/collect_athlete_feedback.py --quick  # Mode rapide (RPE + ressenti uniquement)
    python3 cyclisme_training_logs/collect_athlete_feedback.py --clear  # Effacer le feedback en attente.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


class AthleteFeedbackCollector:
    """Collecteur de feedback athlète."""

    def __init__(self, temp_dir=".athlete_feedback", activity_context=None, batch_position=None):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
        self.feedback_file = self.temp_dir / "last_feedback.json"
        self.activity_context = activity_context or {}
        self.batch_position = batch_position  # Tuple (current, total) ex: (1, 3)

    def display_activity_context(self):
        """Afficher le contexte de l'activité en cours d'analyse."""
        if not self.activity_context and not self.batch_position:
            return

        print("\n" + "=" * 60)

        # Position batch si disponible
        if self.batch_position:
            current, total = self.batch_position
            print(f"📊 SÉANCE {current}/{total}")
            print("=" * 60)
            print()

        # Titre
        if not self.batch_position:
            print("📊 SÉANCE EN COURS D'ANALYSE")
            print("=" * 60)
            print()

        # Nom de la séance
        if self.activity_context.get("name"):
            print(f"🚴 {self.activity_context['name']}")

        # Détails ligne par ligne (plus lisible)
        if self.activity_context.get("date"):
            print(f"📅 Date : {self.activity_context['date']}")
        if self.activity_context.get("duration_min"):
            print(f"⏱️  Durée : {self.activity_context['duration_min']}min")
        if self.activity_context.get("tss"):
            print(f"📈 TSS : {self.activity_context['tss']:.0f}")
        if self.activity_context.get("if_value"):
            print(f"💪 IF : {self.activity_context['if_value']:.2f}")

        print("\n" + "=" * 60)
        print()

    def prompt_rpe(self):
        """Demander le RPE (1-10)."""
        while True:
            try:
                print("\n📊 RPE (Rate of Perceived Exertion)")
                print("   1-2  : Très facile")
                print("   3-4  : Facile")
                print("   5-6  : Modéré")
                print("   7-8  : Difficile")
                print("   9-10 : Très difficile / Maximal")
                print()
                rpe_input = input("   RPE (1-10) : ").strip()

                if not rpe_input:
                    return None

                rpe = int(rpe_input)
                if 1 <= rpe <= 10:
                    return rpe
                else:
                    print("   ⚠️  RPE doit être entre 1 et 10")
            except ValueError:
                print("   ⚠️  Entrer un nombre entre 1 et 10")
            except KeyboardInterrupt:
                print("\n❌ Annulé")
                sys.exit(0)

    def prompt_text(self, question, optional=True):
        """Poser une question texte."""
        try:
            suffix = " (Entrée pour passer)" if optional else ""
            response = input(f"\n{question}{suffix}\n→ ").strip()
            return response if response else None
        except KeyboardInterrupt:
            print("\n❌ Annulé")
            sys.exit(0)

    def prompt_multiline(self, question, optional=True):
        """Poser une question avec réponse multi-lignes."""
        try:
            print(f"\n{question}")
            if optional:
                print("   (Entrée vide pour terminer)")
            print()

            lines = []
            while True:
                line = input("   ")
                if not line:
                    break
                lines.append(line)

            return "\n".join(lines) if lines else None
        except KeyboardInterrupt:
            print("\n❌ Annulé")
            sys.exit(0)

    def prompt_yes_no(self, question, default=True):
        """Poser une question oui/non."""
        try:
            default_str = "O/n" if default else "o/N"
            response = input(f"\n{question} ({default_str}) : ").strip().lower()

            if not response:
                return default

            return response in ["o", "oui", "y", "yes"]
        except KeyboardInterrupt:
            print("\n❌ Annulé")
            sys.exit(0)

    def collect_quick_feedback(self):
        """Mode rapide : RPE + ressenti uniquement."""
        print("🚴 Collecte Retour Athlète - Mode Rapide")
        print("=" * 60)

        # Afficher le contexte de la séance si disponible
        self.display_activity_context()

        feedback = {
            "timestamp": datetime.now().isoformat(),
            "mode": "quick",
            "rpe": self.prompt_rpe(),
            "ressenti_general": self.prompt_text("💭 Ressenti général en quelques mots"),
        }

        return feedback

    def collect_full_feedback(self):
        """Mode complet : toutes les questions."""
        print("🚴 Collecte Retour Athlète - Mode Complet")
        print("=" * 60)

        # Afficher le contexte de la séance si disponible
        self.display_activity_context()

        feedback = {
            "timestamp": datetime.now().isoformat(),
            "mode": "full",
        }

        # RPE
        feedback["rpe"] = self.prompt_rpe()

        # Ressenti général
        feedback["ressenti_general"] = self.prompt_text(
            "💭 Ressenti général (fatigue, forme, motivation)"
        )

        # Difficultés
        if self.prompt_yes_no("❓ Difficultés rencontrées durant la séance ?", default=False):
            feedback["difficultes"] = self.prompt_multiline("📝 Décrivez les difficultés")
        else:
            feedback["difficultes"] = None

        # Points positifs
        if self.prompt_yes_no("✨ Points positifs à noter ?", default=True):
            feedback["points_positifs"] = self.prompt_multiline("📝 Décrivez les points positifs")
        else:
            feedback["points_positifs"] = None

        # Contexte particulier
        feedback["contexte"] = self.prompt_text(
            "🔍 Contexte particulier ? (sommeil, nutrition, stress, météo...)"
        )

        # Sensations physiques
        sensations = []
        print("\n🦵 Sensations physiques particulières ?")
        print("   (Entrée vide pour terminer)")

        options = [
            "Douleurs musculaires",
            "Jambes lourdes",
            "Bonne récupération",
            "Fatigue générale",
            "Tension/raideur",
            "Autre",
        ]

        for opt in options:
            if self.prompt_yes_no(f"   - {opt} ?", default=False):
                if opt == "Autre":
                    detail = self.prompt_text("      Précisez")
                    if detail:
                        sensations.append(detail)
                else:
                    sensations.append(opt)

        feedback["sensations_physiques"] = sensations if sensations else None

        # Notes libres
        feedback["notes_libres"] = self.prompt_multiline(
            "📝 Notes libres / Observations additionnelles"
        )

        return feedback

    def save_feedback(self, feedback):
        """Sauvegarder le feedback."""
        with open(self.feedback_file, "w", encoding="utf-8") as f:
            json.dump(feedback, f, ensure_ascii=False, indent=2)

        print("\n✅ Feedback sauvegardé !")
        print(f"   Fichier : {self.feedback_file}")

    def load_feedback(self):
        """Charger le dernier feedback."""
        if not self.feedback_file.exists():
            return None

        with open(self.feedback_file, encoding="utf-8") as f:
            return json.load(f)

    def clear_feedback(self):
        """Effacer le feedback en attente."""
        if self.feedback_file.exists():
            self.feedback_file.unlink()
            print("✅ Feedback effacé")
        else:
            print("ℹ️  Aucun feedback en attente")

    def display_feedback(self, feedback):
        """Afficher le résumé du feedback."""
        print("\n" + "=" * 60)
        print("📋 RÉSUMÉ DU FEEDBACK")
        print("=" * 60)

        if feedback.get("rpe"):
            print(f"\n📊 RPE : {feedback['rpe']}/10")

        if feedback.get("ressenti_general"):
            print(f"\n💭 Ressenti : {feedback['ressenti_general']}")

        if feedback.get("difficultes"):
            print("\n❌ Difficultés :")
            for line in feedback["difficultes"].split("\n"):
                print(f"   {line}")

        if feedback.get("points_positifs"):
            print("\n✅ Points positifs :")
            for line in feedback["points_positifs"].split("\n"):
                print(f"   {line}")

        if feedback.get("contexte"):
            print(f"\n🔍 Contexte : {feedback['contexte']}")

        if feedback.get("sensations_physiques"):
            print(f"\n🦵 Sensations : {', '.join(feedback['sensations_physiques'])}")

        if feedback.get("notes_libres"):
            print("\n📝 Notes libres :")
            for line in feedback["notes_libres"].split("\n"):
                print(f"   {line}")

        print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Collecter le retour athlète après séance")

    parser.add_argument(
        "--quick", action="store_true", help="Mode rapide (RPE + ressenti uniquement)"
    )
    parser.add_argument("--clear", action="store_true", help="Effacer le feedback en attente")
    parser.add_argument("--show", action="store_true", help="Afficher le feedback en attente")
    parser.add_argument(
        "--temp-dir",
        default=".athlete_feedback",
        help="Répertoire temporaire (défaut: .athlete_feedback/)",
    )
    parser.add_argument("--activity-name", help="Nom de la séance en cours d'analyse (mode batch)")
    parser.add_argument("--activity-date", help="Date de la séance (ex: 2025-11-21)")
    parser.add_argument("--activity-duration", type=int, help="Durée de la séance en minutes")
    parser.add_argument("--activity-tss", type=float, help="TSS de la séance")
    parser.add_argument("--activity-if", type=float, help="IF (Intensity Factor) de la séance")
    parser.add_argument("--batch-position", help="Position dans le batch (format: 1/3, 2/3, etc.)")

    args = parser.parse_args()

    # Construire le contexte activité si fourni
    activity_context = {}
    if args.activity_name:
        activity_context["name"] = args.activity_name
    if args.activity_date:
        activity_context["date"] = args.activity_date
    if args.activity_duration:
        activity_context["duration_min"] = args.activity_duration
    if args.activity_tss:
        activity_context["tss"] = args.activity_tss
    if args.activity_if:
        activity_context["if_value"] = args.activity_if

    # Parser batch position (format: "1/3")
    batch_position = None
    if args.batch_position and "/" in args.batch_position:
        try:
            current, total = args.batch_position.split("/")
            batch_position = (int(current), int(total))
        except (ValueError, AttributeError):
            pass

    collector = AthleteFeedbackCollector(
        temp_dir=args.temp_dir,
        activity_context=activity_context if activity_context else None,
        batch_position=batch_position,
    )

    # Effacer feedback
    if args.clear:
        collector.clear_feedback()
        sys.exit(0)

    # Afficher feedback
    if args.show:
        feedback = collector.load_feedback()
        if feedback:
            collector.display_feedback(feedback)
        else:
            print("ℹ️  Aucun feedback en attente")
        sys.exit(0)

    # Collecter feedback
    try:
        if args.quick:
            feedback = collector.collect_quick_feedback()
        else:
            feedback = collector.collect_full_feedback()

        # Afficher résumé
        collector.display_feedback(feedback)

        # Confirmer sauvegarde
        if collector.prompt_yes_no("\n💾 Sauvegarder ce feedback ?", default=True):
            collector.save_feedback(feedback)

            print("\n📝 PROCHAINE ÉTAPE :")
            print("   Exécuter prepare_analysis.py pour générer le prompt")
            print("   Le feedback sera automatiquement intégré !")
            print()
            print("   ./cyclisme_training_logs/prepare_analysis.py")
        else:
            print("\n❌ Feedback non sauvegardé")

    except KeyboardInterrupt:
        print("\n\n❌ Collecte annulée")
        sys.exit(1)


if __name__ == "__main__":
    main()
