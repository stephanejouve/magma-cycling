"""Special sessions handling (rest days, cancellations, skipped) for WorkflowCoach."""

import subprocess
from datetime import datetime

from magma_cycling.rest_and_cancellations import (
    generate_cancelled_session_entry,
    generate_rest_day_entry,
)


class SpecialSessionsMixin:
    """Handle rest days, cancelled sessions, and skipped sessions in batch."""

    def _collect_rest_feedback(self, session_data: dict) -> dict:
        """Collect feedback athlète pour jour de repos.

        Args:
            session_data: Session info

        Returns:
            Dict avec sleep_duration, sleep_score, hrv, resting_hr.
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
            "resting_hr": int(resting_hr) if resting_hr else None,
        }

    def _show_special_sessions(self):
        """Génère et affiche les sessions spéciales (repos/annulations)."""
        if not self.reconciliation:
            return

        print("\n" + "=" * 70)
        print("📝 GÉNÉRATION SESSIONS SPÉCIALES")
        print("=" * 70)

        # Métriques par défaut (TODO: récupérer depuis API wellness)
        metrics_default = {"ctl": 50, "atl": 35, "tsb": 15}

        markdowns_generated = []

        # Générer repos planifiés
        if self.reconciliation["rest_days"]:
            print(f"\n💤 Génération {len(self.reconciliation['rest_days'])} repos planifiés...")
            for rest in self.reconciliation["rest_days"]:
                print(f"\n   → {rest['session_id']} - {rest['name']}")

                # Collecter feedback
                feedback = self._collect_rest_feedback(rest)

                # Générer markdown
                markdown = generate_rest_day_entry(
                    session_data=rest,
                    metrics_pre=metrics_default,
                    metrics_post=metrics_default,
                    athlete_feedback=feedback,
                )
                markdowns_generated.append((rest["date"], markdown))
                print(f"      ✓ Généré ({len(markdown)} chars)")

        # Générer séances annulées
        if self.reconciliation["cancelled"]:
            print(f"\n❌ Génération {len(self.reconciliation['cancelled'])} séances annulées...")
            for cancelled in self.reconciliation["cancelled"]:
                print(f"\n   → {cancelled['session_id']} - {cancelled['name']}")

                reason = cancelled.get("cancellation_reason", "Non spécifié")

                # Générer markdown
                markdown = generate_cancelled_session_entry(
                    session_data=cancelled, metrics_pre=metrics_default, reason=reason
                )
                markdowns_generated.append((cancelled["date"], markdown))
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
        print("  [1] Enrichir avec IA (analyse coach)")
        print("  [2] Insérer tel quel dans workouts-history.md")
        print("  [3] Export fichier seulement")
        print("  [4] Copier dans presse-papier")
        print("  [0] Retour menu réconciliation")

        action = input("\nTon choix (0/1/2/3/4) : ").strip()

        if action == "0":
            print("\n→ Retour menu réconciliation")
            return "exit_workflow"

        elif action == "1":
            # Enrichissement IA
            print("\n🤖 Génération prompt d'enrichissement Coach IA...")
            if self._generate_coach_prompt(markdowns_generated):
                print("\n✅ Prompt copié dans le presse-papier")
                print("\n→ Continuation workflow pour enrichissement...")
                print("   Étapes suivantes :")
                print("   • Coller dans votre IA")
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
            confirm = (
                input("\n⚠️  Confirmer insertion directe (sans enrichissement) ? (o/n) : ")
                .strip()
                .lower()
            )
            if confirm == "o":
                self._insert_to_history(markdowns_generated)
                print("\n✅ Sessions documentées")
            else:
                print("\n→ Insertion annulée")
            return "exit_workflow"

        elif action == "3":
            # Export fichier
            self._export_markdowns(markdowns_generated, self.planning["week_id"])
            return "exit_workflow"

        elif action == "4":
            # Copier clipboard
            self._copy_to_clipboard(markdowns_generated)
            return "exit_workflow"

        else:
            print("\n⚠️  Choix invalide")
            return "exit_workflow"

    def _handle_rest_cancellations(self):
        """Handle pour traiter repos/annulations en batch.

        Returns:
            str: Action à effectuer ("exit" ou "continue")
        """
        if not self.reconciliation:
            print("\n⚠️  Aucune réconciliation disponible")
            self.wait_user()
            return "exit"

        result = self._show_special_sessions()

        if result == "continue_workflow":
            # Enrichissement IA → continuer vers step 4
            return "continue"
        else:
            # Export/Copie/Insertion → terminé
            return "exit"

    def _handle_skipped_sessions(self, skipped_sessions: list) -> str:
        """Handle dédié pour traiter séances sautées en batch.

        Args:
            skipped_sessions: Liste sessions sautées détectées

        Returns:
            str: Action ("exit" après traitement ou "continue" si enrichissement)
        """
        if not skipped_sessions:
            print("\n⚠️  Aucune séance sautée à traiter")
            self.wait_user()
            return "exit"

        print("\n" + "=" * 70)
        print("📝 GÉNÉRATION SÉANCES SAUTÉES")
        print("=" * 70)

        print(f"\n⏭️  {len(skipped_sessions)} séance(s) sautée(s) à documenter...")

        # Générer markdowns pour chaque sautée
        markdowns_generated = []

        for skipped in skipped_sessions:
            # Extraire session_id (SXXX-XX)
            planned_name = skipped.get("planned_name", "")
            if " - " in planned_name:
                session_id = planned_name.split(" - ")[0]
            else:
                parts = planned_name.split("-")
                session_id = f"{parts[0]}-{parts[1]}" if len(parts) >= 2 else planned_name

            date = skipped.get("planned_date", "")

            print(f"\n   → {session_id} [{date}]")

            # Demander raison saut
            print("   Raison (fatigue/météo/emploi du temps/autre) : ", end="")
            reason = input().strip()
            if not reason:
                reason = "Non spécifié"

            # Générer markdown simple pour sautée
            markdown = self._generate_skipped_markdown(skipped, reason)
            markdowns_generated.append((date, markdown))
            print(f"      ✓ Généré ({len(markdown)} chars)")

        if not markdowns_generated:
            print("\n⚠️  Aucun markdown généré")
            self.wait_user()
            return "exit"

        print(f"\n✅ {len(markdowns_generated)} markdowns générés")

        # Preview
        self._preview_markdowns(markdowns_generated)

        # Menu actions
        print("\n" + "=" * 70)
        print("💡 Que veux-tu faire avec ces markdowns ?")
        print("=" * 70)
        print("  [1] Enrichir avec IA (analyse coach)")
        print("  [2] Insérer tel quel dans workouts-history.md")
        print("  [3] Export fichier seulement")
        print("  [4] Copier dans presse-papier")
        print("  [0] Retour menu principal")

        action = input("\nTon choix (0/1/2/3/4) : ").strip()

        if action == "0":
            print("\n→ Retour menu principal")
            return "exit"

        elif action == "1":
            # Enrichissement IA
            print("\n🤖 Génération prompt d'enrichissement Coach IA...")
            if self._generate_coach_prompt(markdowns_generated):
                print("\n✅ Prompt copié dans le presse-papier")
                print("\n→ Continuation workflow pour enrichissement...")
                self._markdowns_generated = markdowns_generated
                return "continue"
            else:
                print("\n❌ Erreur génération prompt")
                return "exit"

        elif action == "2":
            # Insertion directe
            confirm = (
                input("\n⚠️  Confirmer insertion directe (sans enrichissement) ? (o/n) : ")
                .strip()
                .lower()
            )
            if confirm == "o":
                self._insert_to_history(markdowns_generated)
                print("\n✅ Séances sautées documentées")
            else:
                print("\n→ Insertion annulée")
            return "exit"

        elif action == "3":
            # Export fichier
            self._export_markdowns(markdowns_generated, "skipped_sessions")
            return "exit"

        elif action == "4":
            # Copier clipboard
            self._copy_to_clipboard(markdowns_generated)
            return "exit"

        else:
            print("\n⚠️  Choix invalide")
            return "exit"

    def _generate_skipped_markdown(self, skipped: dict, reason: str) -> str:
        """Generate markdown pour séance sautée.

        Args:
            skipped: Dict session sautée (planned_name, planned_date, etc.)
            reason: Raison saut fournie par user

        Returns:
            str: Markdown formaté.
        """
        # Extraire session_id (SXXX-XX)

        planned_name = skipped.get("planned_name", "")
        if " - " in planned_name:
            session_id = planned_name.split(" - ")[0]
        else:
            parts = planned_name.split("-")
            session_id = f"{parts[0]}-{parts[1]}" if len(parts) >= 2 else planned_name

        date_obj = datetime.strptime(skipped.get("planned_date", ""), "%Y-%m-%d")
        date_formatted = date_obj.strftime("%d/%m/%Y")
        name = planned_name

        markdown = f"""### {session_id}.

Date : {date_formatted}

#### Statut
**⏭️  SÉANCE SAUTÉE**

#### Workout Planifié
- Nom : {name}
- TSS prévu : {skipped.get('planned_tss', 0)}

#### Raison
{reason}

#### Notes
Session planifiée non réalisée. Aucune donnée d'exécution disponible.
"""
        return markdown

    def _handle_batch_all(self):
        """Handle pour traiter TOUT en batch (exécutées + repos + annulations).

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
        """Génère prompt d'enrichissement Coach IA pour repos/annulations.

        Args:
            markdowns: Liste de tuples (date, markdown_text)

        Returns:
            True si succès, False sinon.
        """
        try:
            # 1. Charger prompt projet
            project_prompt_file = (
                self.project_root / "references" / "project_prompt_v2_1_revised.md"
            )
            if not project_prompt_file.exists():
                print(f"\n⚠️  Prompt projet non trouvé : {project_prompt_file}")
                return False

            with open(project_prompt_file, encoding="utf-8") as f:
                project_prompt = f.read()

            # 2. Charger historique récent (5 dernières séances)
            # Always use data repo config
            if self.config:
                history_file = self.config.workouts_history_path
            else:
                from magma_cycling.config import get_data_config

                history_file = get_data_config().workouts_history_path
            recent_history = ""

            if history_file.exists():
                with open(history_file, encoding="utf-8") as f:
                    content = f.read()

                # Extraire les 5 dernières séances (regex simple)
                import re

                sessions = re.findall(r"###\s+S\d+-\d+.*?(?=###\s+S\d+-\d+|\Z)", content, re.DOTALL)
                recent_sessions = sessions[-5:] if len(sessions) >= 5 else sessions

                if recent_sessions:
                    recent_history = "\n".join(recent_sessions)
                else:
                    recent_history = "(Pas d'historique récent disponible)"

            # 3. Construire markdowns combinés
            combined_markdowns = "\n\n---\n\n".join(markdown for _, markdown in markdowns)

            # 4. Construire prompt enrichissement
            enrichment_prompt = f"""# Mission Coach IA : Enrichissement Sessions Spéciales.

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
                ["pbcopy"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            process.communicate(input=enrichment_prompt.encode("utf-8"))

            if process.returncode == 0:
                return True
            else:
                return False

        except Exception as e:
            print(f"\n❌ Erreur : {e}")
            import traceback

            traceback.print_exc()
            return False
