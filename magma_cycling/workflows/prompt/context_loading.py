"""Context loading methods for PromptGenerator."""

import json


class ContextLoadingMixin:
    """File and API context loading for prompt generation."""

    def load_athlete_context(self):
        """Load le contexte athlète depuis project_prompt_v2_1_revised.md."""
        prompt_file = self.references_dir / "project_prompt_v2_1_revised.md"

        if prompt_file.exists():
            with open(prompt_file, encoding="utf-8") as f:
                return f.read()
        return None

    def load_recent_workouts(self, limit=5):
        """Load les N dernières séances depuis workouts-history.md."""
        history_file = self.logs_dir / "workouts-history.md"

        if not history_file.exists():
            return None

        with open(history_file, encoding="utf-8") as f:
            content = f.read()

        # Extraire les dernières entrées (simplifié)
        # On cherche les sections ### et prend les N premières après "## Historique"
        sections = content.split("###")
        recent = []
        count = 0
        for section in sections:
            if count >= limit:
                break
            if section.strip() and "Date :" in section:
                recent.append("###" + section)
                count += 1

        return "\n".join(recent) if recent else None

    def load_cycling_concepts(self):
        """Load les concepts d'entraînement cyclisme."""
        concepts_file = self.references_dir / "cycling_training_concepts.md"

        if concepts_file.exists():
            with open(concepts_file, encoding="utf-8") as f:
                return f.read()
        return None

    def load_periodization_context(self, wellness_data: dict | None = None) -> dict | None:
        """Load periodization context (macro/micro-cycle position).

        Provides strategic context about training phase, CTL progression,
        and PID controller state for more coherent AI analysis.

        Args:
            wellness_data: Wellness data containing CTL metrics

        Returns:
            Dict with periodization context or None if unavailable

        Examples:
            >>> context = generator.load_periodization_context(wellness_data)
            >>> print(context['phase'])  # "RECONSTRUCTION_BASE"
            >>> print(context['ctl_target'])  # 73.0
        """
        from magma_cycling.config.athlete_profile import AthleteProfile
        from magma_cycling.planning.peaks_phases import determine_training_phase
        from magma_cycling.workflows.pid_peaks_integration import (
            ControlMode,
            compute_integrated_correction,
        )

        try:
            # Load athlete profile
            profile = AthleteProfile.from_env()

            # Extract CTL from wellness data
            if not wellness_data:
                return None

            from magma_cycling.utils.metrics import extract_wellness_metrics

            metrics = extract_wellness_metrics(wellness_data)
            ctl_current = metrics["ctl"]

            if ctl_current == 0:
                return None

            # Determine training phase
            phase_rec = determine_training_phase(
                ctl_current=ctl_current,
                ftp_current=profile.ftp,
                ftp_target=profile.ftp_target,
                athlete_age=profile.age,
            )

            # Compute PID integration status
            integrated = compute_integrated_correction(
                ctl_current=ctl_current,
                ftp_current=profile.ftp,
                ftp_target=profile.ftp_target,
                athlete_age=profile.age,
            )

            # Determine PID status
            if integrated.override_active:
                pid_status = "Override Peaks (CTL < 50 - reconstruction urgente)"
            elif integrated.mode == ControlMode.PID_CONSTRAINED:
                pid_status = "Actif avec contraintes Peaks"
            else:
                pid_status = "Actif (autonome)"

            # Calculate weeks to rebuild (approximate)
            weeks_to_target = phase_rec.weeks_to_rebuild if phase_rec.weeks_to_rebuild > 0 else 0

            # Format phase label
            phase_labels = {
                "reconstruction_base": "RECONSTRUCTION BASE",
                "consolidation": "CONSOLIDATION",
                "development_ftp": "DÉVELOPPEMENT FTP",
            }
            phase_label = phase_labels.get(phase_rec.phase.value, phase_rec.phase.value.upper())

            return {
                "phase": phase_label,
                "phase_raw": phase_rec.phase.value,
                "ctl_current": ctl_current,
                "ctl_target": phase_rec.ctl_target,
                "ctl_deficit": phase_rec.ctl_deficit,
                "ftp_current": profile.ftp,
                "ftp_target": profile.ftp_target,
                "weeks_to_target": weeks_to_target,
                "pid_status": pid_status,
                "pid_override_active": integrated.override_active,
                "weekly_tss_load": phase_rec.weekly_tss_load,
                "weekly_tss_recovery": phase_rec.weekly_tss_recovery,
                "recovery_week_frequency": phase_rec.recovery_week_frequency,
                "rationale": phase_rec.rationale,
            }

        except Exception as e:
            # Fail gracefully if periodization context unavailable
            print(f"⚠️  Impossible de charger le contexte de périodisation : {e}")
            return None

    def load_athlete_feedback(self):
        """Load le feedback athlète s'il existe."""
        if not self.feedback_file.exists():
            return None

        try:
            with open(self.feedback_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Erreur lecture feedback : {e}")
            return None
