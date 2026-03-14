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

    def _derive_session_type_targets(self, periodization_context: dict) -> list[dict]:
        """Derive target session types from periodization intensity distribution.

        Maps intensity zones to Zwift session types, merges zones that map
        to the same type, and calculates TSS target per type.

        Args:
            periodization_context: Dict with intensity_distribution and weekly_tss_load

        Returns:
            List of dicts with session_type, tss_target, zone_label
        """
        zone_to_type = {
            "Endurance": "END",
            "Tempo": "END",
            "Sweet-Spot": "INT",
            "VO2": "INT",
            "FTP": "FTP",
        }
        # Recovery and AC_Neuro are skipped (not relevant for catalogue)

        distribution = periodization_context.get("intensity_distribution", {})
        weekly_tss = periodization_context.get("weekly_tss_load", 0)

        if not distribution or weekly_tss == 0:
            return []

        # Merge zones that map to the same session type
        merged: dict[str, dict] = {}
        for zone, pct in distribution.items():
            session_type = zone_to_type.get(zone)
            if session_type is None:
                continue
            if session_type not in merged:
                merged[session_type] = {"pct": 0.0, "zones": []}
            merged[session_type]["pct"] += pct
            merged[session_type]["zones"].append(zone)

        # Build targets, filter < 5%
        targets = []
        for session_type, info in merged.items():
            if info["pct"] < 0.05:
                continue
            tss_target = int(weekly_tss * info["pct"])
            zone_label = "/".join(info["zones"])
            targets.append(
                {
                    "session_type": session_type,
                    "tss_target": tss_target,
                    "zone_label": zone_label,
                }
            )

        return targets

    def _format_zwift_suggestions(
        self,
        suggestions: dict[str, list],
        targets: list[dict],
        stats: dict,
    ) -> str:
        """Format Zwift workout suggestions as prompt section.

        Args:
            suggestions: Dict mapping session_type to list of WorkoutMatch
            targets: List of target dicts from _derive_session_type_targets
            stats: Cache stats dict

        Returns:
            Formatted markdown section for prompt injection
        """
        section = "\n\n## Catalogue Workouts Zwift (Structures Recommandees)\n\n"
        section += f"**Source:** Cache Zwift ({stats['total_workouts']} workouts)\n\n"
        section += "**INSTRUCTIONS** :\n"
        section += "- Pour les seances INT et END, UTILISER ces structures comme MODELE\n"
        section += "- Adapter duree/intensite selon TSS cible de la semaine\n"
        section += "- Conserver le nom Zwift comme reference (ex: S085-03-INT-Halvfems-V001)\n"
        section += "- Si aucune suggestion ne convient, generer librement\n\n"

        target_map = {t["session_type"]: t for t in targets}

        for session_type in sorted(suggestions.keys()):
            matches = suggestions[session_type]
            target = target_map.get(session_type, {})
            tss_target = target.get("tss_target", "?")

            if not matches:
                section += f"### Aucune suggestion pour {session_type} (cache insuffisant)\n\n"
                continue

            section += f"### Suggestions {session_type} (TSS cible ~{tss_target})\n\n"
            for i, match in enumerate(matches, 1):
                w = match.workout
                section += (
                    f"**{i}. {w.name}** "
                    f"(Score: {match.score:.0f}, TSS: {w.tss}, {w.duration_minutes}min)\n"
                )
                section += w.to_intervals_description() + "\n\n"

        return section

    def _format_zwift_stats_only(self, stats: dict) -> str:
        """Format Zwift cache stats without concrete suggestions (fallback).

        Args:
            stats: Cache stats dict from ZwiftWorkoutClient.get_cache_stats()

        Returns:
            Formatted markdown section with stats only
        """
        section = "\n\n## Workouts Externes Disponibles (Diversite)\n\n"
        section += "**Source:** Cache Zwift (whatsonzwift.com)\n"
        section += f"**Total disponible:** {stats['total_workouts']} workouts\n\n"

        if stats.get("by_category"):
            section += "**Par categorie:**\n"
            for category, count in sorted(
                stats["by_category"].items(), key=lambda x: x[1], reverse=True
            ):
                section += f"  - {category}: {count} workout(s)\n"

        section += "\n**Instructions:**\n"
        section += "- Ces workouts peuvent etre utilises pour introduire de la DIVERSITE\n"
        section += "- Le systeme track automatiquement l'usage pour eviter repetitions\n\n"

        return section

    def _load_available_zwift_workouts(self) -> str:
        """Load Zwift workouts from cache with targeted suggestions.

        When periodization context is available, searches the cache for
        concrete workout suggestions matching each target session type
        and TSS budget. Falls back to stats-only display otherwise.

        Returns:
            Formatted section with workout suggestions or stats
        """
        try:
            from magma_cycling.external.zwift_client import ZwiftWorkoutClient
            from magma_cycling.external.zwift_models import WorkoutSearchCriteria

            client = ZwiftWorkoutClient()
            stats = client.get_cache_stats()

            if stats["total_workouts"] == 0:
                return ""

            # Check for periodization context
            periodization_context = getattr(self, "_periodization_context", None)
            if not periodization_context:
                return self._format_zwift_stats_only(stats)

            # Derive target session types from intensity distribution
            targets = self._derive_session_type_targets(periodization_context)
            if not targets:
                return self._format_zwift_stats_only(stats)

            # Search for matches per session type
            suggestions: dict[str, list] = {}
            for target in targets:
                criteria = WorkoutSearchCriteria(
                    session_type=target["session_type"],
                    tss_target=target["tss_target"],
                    tss_tolerance=10,
                    exclude_recent=True,
                    diversity_window_days=28,
                )
                matches = client.search_workouts(criteria)
                suggestions[target["session_type"]] = matches[:3]  # Top 3

            return self._format_zwift_suggestions(suggestions, targets, stats)

        except Exception as e:
            logger.warning(f"Could not load Zwift workouts: {e}")
            return ""
