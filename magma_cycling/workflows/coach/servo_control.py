"""Servo control (planning modification) methods for WorkflowCoach."""

import subprocess

from magma_cycling.planning.control_tower import planning_tower
from magma_cycling.planning.session_formatter import format_remaining_sessions_compact
from magma_cycling.prompts.prompt_builder import build_prompt, load_current_metrics
from magma_cycling.utils.ai_response_parser import parse_ai_modifications
from magma_cycling.utils.date_helpers import extract_day_number


class ServoControlMixin:
    """Planning servo control: load sessions, apply AI-recommended modifications."""

    def _update_planning_json(
        self, week_id: str, date: str, new_workout: dict, old_workout: str, reason: str
    ) -> bool:
        """Met à jour week_planning_SXXX.json avec historique.

        Args:
            week_id: ID semaine
            date: Date modification
            new_workout: Dict nouveau workout (code, type, tss, description)
            old_workout: Code workout remplacé
            reason: Raison modification

        Returns:
            bool: True si succès.
        """
        try:
            # 🚦 MODIFY VIA CONTROL TOWER (automatic backup + audit)
            with planning_tower.modify_week(
                week_id,
                requesting_script="workflow-coach",
                reason=f"AI Coach modification: {old_workout} → {new_workout['code']} ({reason})",
            ) as plan:
                # Find session to modify
                session_found = False
                for session in plan.planned_sessions:
                    if str(session.session_date) == date:
                        # Update session fields
                        # (History tracked by Control Tower audit log)
                        session.session_id = new_workout.get("session_id", session.session_id)
                        session.name = new_workout.get("name", session.name)
                        session.session_type = new_workout["type"]
                        session.tss_planned = new_workout["tss"]
                        session.description = new_workout["description"]
                        session.status = "modified"

                        session_found = True
                        break

                if not session_found:
                    print(f"⚠️  Session non trouvée pour date {date}")
                    return False

                # Auto-saved by Control Tower with backup + audit log

            return True

        except FileNotFoundError:
            print(f"⚠️  Planning {week_id} non trouvé")
            return False
        except Exception as e:
            print(f"⚠️  Erreur mise à jour planning : {e}")
            return False

    def _apply_lighten(self, mod: dict, week_id: str):
        """Applique allégement séance via template.

        Args:
            mod: Modification dict avec template_id
            week_id: ID semaine.
        """
        import sys

        from magma_cycling.config import get_data_config

        template_id = mod["template_id"]

        if template_id not in self.workout_templates:
            print(f"❌ Template inconnu: {template_id}")
            return

        template = self.workout_templates[template_id]

        print(f"\n🔄 Allégement via '{template['name']}'")
        print(f"   Date : {mod['target_date']}")
        print(f"   {template['tss']} TSS, {template['duration_minutes']}min")
        print(f"   Raison : {mod['reason']}")

        # Check if non-interactive mode (LaunchAgent or auto_mode)
        is_non_interactive = self.auto_mode or not sys.stdin.isatty()

        if is_non_interactive:
            # Non-interactive mode: Log recommendation but don't apply
            print("   ℹ️  Mode automatique : recommandation enregistrée (pas d'application)")
            print("   💡 Lancer manuellement : poetry run workflow-coach --servo-mode")
            # Store recommendation for email notification
            if not hasattr(self, "_servo_recommendations"):
                self._servo_recommendations = []
            self._servo_recommendations.append(
                {
                    "date": mod["target_date"],
                    "template": template["name"],
                    "tss": template["tss"],
                    "reason": mod["reason"],
                    "status": "pending_manual_application",
                }
            )
            return

        # Interactive mode: Ask for confirmation (CRITICAL)
        confirm = input("   Appliquer ? (o/n) : ").strip().lower()
        if confirm != "o":
            print("   ❌ Ignoré")
            return

        # 1. Générer workout code depuis template
        config = get_data_config()
        day_num = extract_day_number(mod["target_date"], week_id, config.week_planning_dir)
        workout_code = template["workout_code_pattern"].format(week_id=week_id, day_num=day_num)

        # 2. Supprimer ancien workout Intervals.icu
        old_workout_id = self._get_workout_id_intervals(mod["target_date"])
        if old_workout_id:
            if self._delete_workout_intervals(old_workout_id):
                print("   🗑️  Ancien workout supprimé")
            else:
                print("   ⚠️  Échec suppression ancien workout")

        # 3. Upload nouveau workout
        if self._upload_workout_intervals(
            date=mod["target_date"], code=workout_code, structure=template["intervals_icu_format"]
        ):
            print("   ⬆️  Nouveau workout uploadé")
        else:
            print("   ⚠️  Échec upload nouveau workout")
            return

        # 4. Mettre à jour planning JSON
        if self._update_planning_json(
            week_id=week_id,
            date=mod["target_date"],
            new_workout={
                "code": workout_code,
                "type": template["type"],
                "tss": template["tss"],
                "description": template["description"],
            },
            old_workout=mod["current_workout"],
            reason=mod["reason"],
        ):
            print("   📝 Planning JSON mis à jour")
            print("   ✅ Modification appliquée")
        else:
            print("   ⚠️  Échec mise à jour planning JSON")

    def apply_planning_modifications(self, modifications: list, week_id: str):
        """Applique modifications planning.

        Args:
            modifications: Liste modifications AI
            week_id: ID semaine.
        """
        if not modifications:
            print("\n✅ Planning maintenu tel quel")
            return

        print(f"\n📋 {len(modifications)} modification(s) détectée(s)")

        for mod in modifications:
            action = mod.get("action", "unknown")

            if action == "lighten":
                self._apply_lighten(mod, week_id)
            elif action == "cancel":
                # TODO: Implémenter cancel si nécessaire
                print(f"⚠️  Action 'cancel' non implémentée: {mod}")
            elif action == "reschedule":
                # TODO: Implémenter reschedule si nécessaire
                print(f"⚠️  Action 'reschedule' non implémentée: {mod}")
            else:
                print(f"⚠️  Action inconnue: {action}")

    def step_6b_servo_control(self):
        """Étape 6b : Asservissement planning (si --servo-mode activé)."""
        self.clear_screen()

        subtitle = "Étape 6b/7 : Asservissement Planning (Servo Mode)"
        if self.activity_name:
            subtitle += f"\n🚴 {self.activity_name}"

        self.print_header("🔄 Asservissement Planning", subtitle)

        print("Le mode asservissement est activé.")
        print("Vérification si le coach AI recommande des ajustements au planning...")
        print()

        # Detect week_id from activity or ask user
        if not self.week_id:
            week_id_input = input("Identifiant semaine (ex: S072) : ").strip().upper()
            if not week_id_input.startswith("S"):
                week_id_input = "S" + week_id_input
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
            date = session["date"]
            session_id = session["session_id"]
            name = session["name"]
            workout_type = session["type"]
            tss = session.get("tss_planned", 0)
            # Construct workout code
            code = f"{session_id}-{workout_type}-{name}-{session.get('version', 'V001')}"
            if session.get("status") == "rest_day":
                print(f"   • {date}: REPOS")
            else:
                print(f"   • {date}: {code} ({tss} TSS)")
        print()

        # Ask user if they want to request AI recommendations
        print("Le coach AI peut analyser le planning restant et proposer des ajustements.")
        print()
        request_mods = input("Demander recommandations au coach AI ? (o/n) : ").strip().lower()

        if request_mods != "o":
            print("✅ Planning maintenu sans modification")
            self.wait_user()
            return

        # Extract metrics from analysis
        print()
        print("🔍 Extraction des métriques de la séance analysée...")
        metrics = self._extract_metrics_from_analysis()

        # Prompt for sleep if missing
        if metrics["sleep_hours"] is not None and metrics["sleep_hours"] == 0.0:
            metrics["sleep_hours"] = self._prompt_sleep_if_missing(metrics["sleep_hours"])

        # Format metrics for prompt
        tsb_str = f"{metrics['tsb']:+d}" if metrics["tsb"] is not None else "N/A"
        sleep_str = (
            f"{metrics['sleep_hours']:.1f}h"
            if metrics["sleep_hours"] is not None and metrics["sleep_hours"] > 0
            else "Non disponible"
        )
        rpe_str = f"{metrics['rpe']}/10" if metrics["rpe"] is not None else "Non fourni"
        decoupling_str = (
            f"{metrics['decoupling']:.1f}%"
            if metrics["decoupling"] is not None
            else "Non disponible"
        )
        hr_str = f"{metrics['avg_hr']}bpm" if metrics["avg_hr"] is not None else "Non disponible"

        # Generate supplementary prompt for AI
        planning_context = format_remaining_sessions_compact(remaining_sessions)

        supplementary_prompt = f"""# ASSERVISSEMENT PLANNING - Demande Coach AI.

Contexte : Tu viens d'analyser la séance du jour (DÉJÀ RÉALISÉE).

## Métriques de la séance analysée
- TSB pré-séance : {tsb_str}
- Sommeil : {sleep_str}
- RPE : {rpe_str}
- Découplage cardiovasculaire : {decoupling_str}
- FC moyenne : {hr_str}

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

Basé sur l'analyse de la séance du jour et les métriques réelles ci-dessus, **recommandes-tu des ajustements au planning FUTUR ?**

Critères de décision:
- HRV < -10% → Envisager allégement
- RPE > 8/10 en zone endurance → Signal alarme
- Découplage > 7.5% → Fatigue cardiaque
- Sommeil < 7h → Vulnérabilité accrue

**RÈGLES STRICTES:**
1. **NE MODIFIER QUE LES SÉANCES FUTURES** (listées dans "Planning Restant" ci-dessus)
2. **NE JAMAIS modifier une séance de type TEST (TST)** - Préserver comparabilité historique
3. **Semaine de tests:** NE RIEN MODIFIER sauf fatigue critique (TSB < -15, découplage > 15%, RPE > 9)
4. **Séance du jour:** DÉJÀ réalisée, impossible à modifier rétroactivement
5. Utilise UNIQUEMENT les valeurs de métriques fournies ci-dessus
6. Si une métrique est "Non disponible", ne PAS inventer de valeur
7. Justifier les recommandations avec les métriques RÉELLES

**Format JSON si modification recommandée** :
```json
{{"modifications": [{{
  "action": "lighten",
  "target_date": "YYYY-MM-DD",
  "current_workout": "CODE",
  "template_id": "recovery_active_30tss",
  "reason": "Découplage 11.2%, prioriser récupération"
}}]}}
```

**Si aucune modification nécessaire** : Ne rien ajouter (pas de JSON).

Réponds maintenant."""
        # Get AI response - Use provider directly if available (fix Issue #2)

        ai_response = None

        if self.current_provider != "clipboard":
            # Use AI provider directly
            print()
            print(f"🤖 Appel AI provider: {self.current_provider}")
            print("   Génération des recommandations en cours...")
            print()

            try:
                # Build system_prompt for AI framing
                current_metrics = load_current_metrics()
                system_prompt, _ = build_prompt(
                    mission="daily_feedback",
                    current_metrics=current_metrics,
                    workflow_data="",
                )
                # Call AI provider with supplementary prompt
                ai_response = self.ai_analyzer.analyze_session(
                    prompt=supplementary_prompt,
                    dataset=None,
                    system_prompt=system_prompt,
                )
                import logging

                logger = logging.getLogger(__name__)
                logger.info(f"AI provider responded: {len(ai_response)} chars")

            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"AI provider failed: {e}")
                print(f"⚠️  Erreur provider {self.current_provider}: {e}")
                print("   Basculement vers mode clipboard...")
                ai_response = None

        # Fallback to clipboard if no provider or provider failed
        if ai_response is None:
            print()
            print("📋 Mode manuel (clipboard)")
            print()

            try:
                # Copy prompt to clipboard
                process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                process.communicate(input=supplementary_prompt.encode("utf-8"))

                print("✅ Prompt asservissement copié dans le presse-papier")
                print()
                print("📋 INSTRUCTIONS :")
                print("1. Retourne dans ton IA (même conversation)")
                print("2. Colle le prompt supplémentaire (Cmd+V)")
                print("3. Envoie le message")
                print("4. Copie la réponse complète")
                print()

                self.wait_user("Appuyer sur ENTRÉE une fois la réponse copiée...")

                # Get AI response from clipboard
                clipboard = subprocess.run(["pbpaste"], capture_output=True, text=True, check=True)
                ai_response = clipboard.stdout

            except Exception as e:
                print(f"⚠️  Erreur clipboard workflow : {e}")
                self.wait_user()
                return

        if not ai_response or not ai_response.strip():
            print("⚠️  Réponse AI vide")
            self.wait_user()
            return

        # Display AI recommendations to user before parsing
        self.clear_screen()
        self.print_header(
            "📊 Recommandations Coach IA",
            "Asservissement Planning - Analyse Complète",
        )
        print("Voici l'analyse complète du coach IA pour le planning restant :")
        print()
        self.print_separator()
        print()

        # Display full AI response
        lines = ai_response.split("\n")
        for line in lines:
            print(line)

        print()
        self.print_separator()
        print()

        # Show stats
        word_count = len(ai_response.split())
        char_count = len(ai_response)
        print(f"📊 Statistiques : {word_count} mots, {char_count} caractères")
        print()

        self.wait_user("Appuyer sur ENTRÉE pour analyser les modifications recommandées...")
        self.clear_screen()
        self.print_header("🔍 Analyse des Modifications", "Asservissement Planning - Parsing JSON")

        # Parse modifications from AI response
        modifications = parse_ai_modifications(ai_response)

        if not modifications:
            print()
            print("✅ Aucune modification recommandée par le coach AI")
            print("   Le planning est maintenu tel quel")
        else:
            # Apply modifications (with user confirmation for each)
            self.apply_planning_modifications(modifications, week_id)

        print()
        self.wait_user()
