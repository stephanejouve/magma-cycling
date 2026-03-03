"""Periodization context methods for WeeklyPlanner."""

import logging
import sys

logger = logging.getLogger(__name__)


class PeriodizationMixin:
    """Training phase, PID controller, mesocycle, and Zwift catalog."""

    def load_periodization_context(self) -> dict | None:
        """Load periodization context (macro/micro-cycle position).

        Provides strategic context about training phase, CTL progression,
        and PID controller state for coherent weekly planning aligned
        with long-term objectives.

        Returns:
            Dict with periodization context or None if unavailable

        Examples:
            >>> context = planner.load_periodization_context()
            >>> context['phase']  # "RECONSTRUCTION_BASE"
            >>> context['weekly_tss_load']  # 350
        """
        print("\n🎯 Chargement contexte périodisation...", file=sys.stderr)

        try:
            from magma_cycling.config.athlete_profile import AthleteProfile
            from magma_cycling.planning.peaks_phases import determine_training_phase
            from magma_cycling.workflows.pid_peaks_integration import (
                ControlMode,
                compute_integrated_correction,
            )

            # Load athlete profile
            profile = AthleteProfile.from_env()

            # Extract CTL from current metrics
            ctl_current = self.current_metrics.get("ctl", 0)

            if ctl_current == 0:
                print("  ⚠️ CTL non disponible, contexte périodisation ignoré", file=sys.stderr)
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

            # Format phase label
            phase_labels = {
                "reconstruction_base": "RECONSTRUCTION BASE",
                "consolidation": "CONSOLIDATION",
                "development_ftp": "DÉVELOPPEMENT FTP",
            }
            phase_label = phase_labels.get(phase_rec.phase.value, phase_rec.phase.value.upper())

            context = {
                "phase": phase_label,
                "phase_raw": phase_rec.phase.value,
                "ctl_current": ctl_current,
                "ctl_target": phase_rec.ctl_target,
                "ctl_deficit": phase_rec.ctl_deficit,
                "ftp_current": profile.ftp,
                "ftp_target": profile.ftp_target,
                "weeks_to_target": (
                    phase_rec.weeks_to_rebuild if phase_rec.weeks_to_rebuild > 0 else 0
                ),
                "pid_status": pid_status,
                "pid_override_active": integrated.override_active,
                "weekly_tss_load": phase_rec.weekly_tss_load,
                "weekly_tss_recovery": phase_rec.weekly_tss_recovery,
                "recovery_week_frequency": phase_rec.recovery_week_frequency,
                "intensity_distribution": phase_rec.intensity_distribution,
                "rationale": phase_rec.rationale,
            }

            print(
                f"  ✅ Phase {phase_label}, CTL {ctl_current:.1f} → {phase_rec.ctl_target:.0f}",
                file=sys.stderr,
            )
            return context

        except Exception as e:
            print(f"  ⚠️ Impossible de charger contexte périodisation : {e}", file=sys.stderr)
            return None

    def _load_mesocycle_context(self) -> str:
        """Load mesocycle enriched context if applicable (every 6 weeks).

        Returns:
            Markdown formatted mesocycle report or empty string

        Examples:
            >>> planner = WeeklyPlanner("S078", datetime(2026, 2, 10), Path("."))
            >>> context = planner._load_mesocycle_context()
            >>> "MÉSO-CYCLE" in context  # At cycle end
            True
        """
        try:
            from magma_cycling.analyzers.mesocycle_analyzer import (
                generate_mesocycle_context,
            )

            return generate_mesocycle_context(self.week_number)

        except Exception as e:
            print(f"  ⚠️ Erreur chargement contexte méso-cycle : {e}", file=sys.stderr)
            return ""

    def _load_available_zwift_workouts(self) -> str:
        """Load available Zwift workouts from cache for diversity.

        Returns:
            Formatted section describing available workouts
        """
        try:
            from magma_cycling.external.zwift_client import ZwiftWorkoutClient

            client = ZwiftWorkoutClient()
            stats = client.get_cache_stats()

            if stats["total_workouts"] == 0:
                return ""

            # Build section
            section = "\n\n## 🎨 Workouts Externes Disponibles (Diversité)\n\n"
            section += "**Source:** Cache Zwift (whatsonzwift.com)\n"
            section += f"**Total disponible:** {stats['total_workouts']} workouts\n\n"

            if stats.get("by_category"):
                section += "**Par catégorie:**\n"
                for category, count in sorted(
                    stats["by_category"].items(), key=lambda x: x[1], reverse=True
                ):
                    section += f"  - {category}: {count} workout(s)\n"

            section += "\n**Instructions:**\n"
            section += "- Ces workouts peuvent être utilisés pour introduire de la DIVERSITÉ\n"
            section += "- Utiliser la commande: `poetry run search-zwift-workouts --type [TYPE] --tss [TSS]`\n"
            section += "- Le système track automatiquement l'usage pour éviter répétitions (fenêtre 21 jours)\n"
            section += "- Privilégier ces workouts pour varier des structures habituelles\n"
            section += "- Format Wahoo-compatible garanti (explicit power % on every line)\n\n"

            return section

        except Exception as e:
            logger.warning(f"Could not load Zwift workouts: {e}")
            return ""
