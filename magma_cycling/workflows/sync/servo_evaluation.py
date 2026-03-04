"""ServoEvaluationMixin — metrics extraction, false-positive detection, servo triggering."""

from magma_cycling.planning.session_formatter import format_remaining_sessions_compact
from magma_cycling.utils.ai_response_parser import parse_ai_modifications
from magma_cycling.utils.intervals_scales import format_feel


class ServoEvaluationMixin:
    """Mixin for servo evaluation: metrics extraction, social ride detection, and servo mode."""

    def extract_metrics_from_activity(
        self, activity: dict, analysis: str | None, wellness_pre: dict | None
    ) -> dict:
        """
        Extract key metrics from activity data and analysis.

        Args:
            activity: Activity dict from Intervals.icu
            analysis: AI analysis text (if available)
            wellness_pre: Pre-workout wellness data

        Returns:
            Dict with extracted metrics for servo evaluation
        """
        metrics = {
            "tsb": None,
            "sleep_hours": None,
            "decoupling": None,
            "feel": None,
            "tss_planned": None,
            "tss_actual": None,
            "duration_planned_min": None,
            "duration_actual_min": None,
        }

        # Extract from wellness
        if wellness_pre:
            try:
                from magma_cycling.utils.metrics import (
                    extract_wellness_metrics,
                )

                wellness_metrics = extract_wellness_metrics(wellness_pre)
                metrics["tsb"] = wellness_metrics.get("tsb")

                # Sleep in hours
                sleep_secs = wellness_pre.get("sleepSecs", 0)
                if sleep_secs:
                    metrics["sleep_hours"] = sleep_secs / 3600.0

                # Feel (Intervals.icu 1-5 scale: 1=Excellent, 5=Poor)
                metrics["feel"] = activity.get("feel")
            except Exception as e:
                print(f"     ⚠️  Erreur extraction wellness: {e}")

        # Extract from activity
        metrics["tss_actual"] = activity.get("icu_training_load")
        metrics["duration_actual_min"] = activity.get("moving_time", 0) // 60
        metrics["decoupling"] = activity.get("decoupling")

        # Try to get planned values from session name (if it follows naming convention)
        # This would require looking up the planning JSON, but for now we'll skip
        # The servo will work without TSS comparison if not available

        return metrics

    def _is_low_effort_social_ride(self, activity: dict, metrics: dict) -> bool:
        """
        Detect false positive scenarios for decoupling alerts.

        Identifies social/accompaniment rides with frequent stops that
        generate artificially high decoupling values.

        Detection criteria:
        - Very low TSS (<30)
        - Very low avg power vs normalized power ratio (<0.5)
        - Keywords in notes: accompagnement, arrêts, attendre, partage, échange

        Args:
            activity: Activity dict with power metrics and notes
            metrics: Extracted metrics dict

        Returns:
            True if this is likely a low-effort social ride (false positive)
        """
        # Criterion 1: Very low TSS
        tss = activity.get("icu_training_load", 0)
        if tss >= 30:
            return False

        # Criterion 2: Very low power ratio (indicates frequent stops)
        avg_power = activity.get("average_watts", 0)
        normalized_power = activity.get("np", 0)
        if normalized_power > 0:
            power_ratio = avg_power / normalized_power
            if power_ratio < 0.5:  # Avg power < 50% of NP = many stops
                return True

        # Criterion 3: Keywords in notes/description
        description = activity.get("description", "").lower()
        keywords = [
            "accompagnement",
            "accompagner",
            "arrêts",
            "arrêt",
            "attendre",
            "attente",
            "partage",
            "partagé",
            "échange",
            "échangé",
            "initiation",
            "découvrir",
            "pied à terre",
            "mise à terre",
        ]

        if any(keyword in description for keyword in keywords):
            return True

        return False

    def should_trigger_servo(
        self, metrics: dict, activity: dict | None = None
    ) -> tuple[bool, list[str]]:
        """
        Evaluate if servo mode should be triggered based on metrics.

        Uses same criteria as workflow_coach servo-mode:
        - Découplage >7.5% (with false positive detection for social rides)
        - Sommeil <7h
        - Feel ≥4/5 (Passable/Mauvais) - Intervals.icu scale
        - TSB <-10

        Args:
            metrics: Dict with extracted metrics
            activity: Activity dict (optional, for false positive detection)

        Returns:
            Tuple of (should_trigger, reasons)
        """
        reasons = []

        # Criterion 1: Decoupling (with false positive detection)
        if metrics.get("decoupling") is not None:
            if metrics["decoupling"] > self.servo_criteria["decoupling_threshold"]:
                # Check for false positive scenarios
                if activity and self._is_low_effort_social_ride(activity, metrics):
                    print(
                        f"     ℹ️  Découplage élevé ({metrics['decoupling']:.1f}%) ignoré "
                        "(sortie sociale/accompagnement avec arrêts détectée)"
                    )
                else:
                    reasons.append(
                        f"Découplage élevé ({metrics['decoupling']:.1f}% > {self.servo_criteria['decoupling_threshold']}%)"
                    )

        # Criterion 2: Sleep
        if metrics.get("sleep_hours") is not None:
            if metrics["sleep_hours"] < self.servo_criteria["sleep_threshold_hours"]:
                reasons.append(
                    f"Sommeil insuffisant ({metrics['sleep_hours']:.1f}h < {self.servo_criteria['sleep_threshold_hours']}h)"
                )

        # Criterion 3: Feel (subjective) - Intervals.icu 1-5 scale
        if metrics.get("feel") is not None:
            if metrics["feel"] >= self.servo_criteria["feel_threshold"]:
                feel_label = format_feel(metrics["feel"])
                reasons.append(f"Ressenti négatif ({feel_label} - {metrics['feel']}/5)")

        # Criterion 4: TSB
        if metrics.get("tsb") is not None:
            if metrics["tsb"] < self.servo_criteria["tsb_threshold"]:
                reasons.append(
                    f"Forme dégradée (TSB {metrics['tsb']:+.0f} < {self.servo_criteria['tsb_threshold']})"
                )

        # Trigger if at least one strong signal
        should_trigger = len(reasons) > 0

        return should_trigger, reasons

    def run_servo_adjustment(
        self, week_id: str, activity: dict, metrics: dict, analysis: str | None
    ) -> dict | None:
        """
        Run servo mode to get AI recommendations for planning adjustments.

        Args:
            week_id: Week identifier (e.g., "S077")
            activity: Activity dict
            metrics: Extracted metrics
            analysis: AI analysis of the session

        Returns:
            Dict with servo recommendations or None if failed
        """
        try:
            print("\n" + "=" * 80)
            print("🔄 SERVO MODE AUTOMATIQUE - Ajustement Planning")
            print("=" * 80)
            print()

            # Load remaining sessions from planning
            from magma_cycling.workflow_coach import WorkflowCoach

            coach = WorkflowCoach(servo_mode=True)
            remaining_sessions = coach.load_remaining_sessions(week_id)

            if not remaining_sessions:
                print("  ⚠️  Aucune séance future dans le planning")
                return None

            print(f"📋 {len(remaining_sessions)} séance(s) restante(s) dans le planning")
            print()

            # Format metrics for prompt
            tsb_str = f"{metrics['tsb']:+.0f}" if metrics.get("tsb") is not None else "N/A"
            sleep_str = (
                f"{metrics['sleep_hours']:.1f}h"
                if metrics.get("sleep_hours") is not None
                else "Non disponible"
            )
            decoupling_str = (
                f"{metrics['decoupling']:.1f}%"
                if metrics.get("decoupling") is not None
                else "Non disponible"
            )
            feel_str = f"{metrics['feel']}/4" if metrics.get("feel") is not None else "Non fourni"

            # Generate servo prompt (same as workflow_coach)
            planning_context = format_remaining_sessions_compact(remaining_sessions)

            servo_prompt = f"""# ASSERVISSEMENT PLANNING - Demande Coach AI.

Contexte : Tu viens d'analyser la séance du jour (DÉJÀ RÉALISÉE).

## Métriques de la séance analysée
- TSB pré-séance : {tsb_str}
- Sommeil : {sleep_str}
- Ressenti (Feel) : {feel_str}
- Découplage cardiovasculaire : {decoupling_str}

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
- RPE > 8/10 en zone endurance → Signal alarme
- Découplage > 7.5% → Fatigue cardiaque
- Sommeil < 7h → Vulnérabilité accrue
- TSB < -10 → Forme dégradée

**RÈGLES STRICTES:**
1. **NE MODIFIER QUE LES SÉANCES FUTURES** (listées dans "Planning Restant" ci-dessus)
2. **NE JAMAIS modifier une séance de type TEST (TST)** - Préserver comparabilité historique
3. **Semaine de tests:** NE RIEN MODIFIER sauf fatigue critique (TSB < -15, découplage > 15%, Feel < 1.5/4)
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

            # Call AI analyzer
            print("🤖 Demande recommandations au coach AI...")
            ai_response = self.ai_analyzer.analyze_session(servo_prompt)

            if not ai_response:
                print("  ⚠️  Pas de réponse du coach AI")
                return None

            print(f"  ✅ Réponse reçue ({len(ai_response)} caractères)")
            print()

            # Parse modifications
            modifications = parse_ai_modifications(ai_response)

            result = {
                "ai_response": ai_response,
                "modifications": modifications,
                "remaining_sessions": remaining_sessions,
            }

            if modifications:
                print(f"📋 {len(modifications)} modification(s) recommandée(s)")
                for mod in modifications:
                    action = mod.get("action", "unknown")
                    target_date = mod.get("target_date", "N/A")
                    reason = mod.get("reason", "N/A")
                    print(f"  • {target_date}: {action} - {reason}")
            else:
                print("✅ Aucune modification recommandée - planning maintenu")

            print()
            print("=" * 80)

            return result

        except Exception as e:
            print(f"  ❌ Erreur servo mode: {e}")
            import traceback

            traceback.print_exc()
            return None
