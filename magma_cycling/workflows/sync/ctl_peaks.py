"""CTLPeaksMixin — CTL/ATL/TSB analysis using Peaks Coaching principles."""

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from magma_cycling.config.athlete_profile import AthleteProfile
from magma_cycling.intelligence.discrete_pid_controller import DiscretePIDController
from magma_cycling.planning.peaks_phases import determine_training_phase
from magma_cycling.workflows.pid_peaks_integration import compute_integrated_correction


class CTLPeaksMixin:
    """Mixin for CTL/ATL/TSB analysis according to Peaks Coaching principles."""

    def analyze_ctl_peaks(self, check_date: date | None = None) -> dict[str, Any] | None:
        """
        Analyze CTL/ATL/TSB metrics according to Peaks Coaching principles.

        Checks current CTL against recommended thresholds for Masters 50+ athletes
        and generates alerts if critical conditions detected.

        NEW: Integrates PID + Peaks hierarchical recommendation system.

        Args:
            check_date: Date for wellness lookup (defaults to today)

        Returns:
            Dict with analysis results and alerts, or None if failed
            {
                "ctl_current": float,
                "atl_current": float,
                "tsb_current": float,
                "ftp_current": int,
                "ctl_minimum_for_ftp": float,
                "ctl_optimal_for_ftp": float,
                "alerts": list[str],
                "recommendations": list[str],
                "phase_recommendation": PhaseRecommendation,
                "pid_peaks_recommendation": IntegratedRecommendation (NEW)
            }
        """
        try:
            # Load athlete profile from env for FTP values
            athlete_profile = AthleteProfile.from_env()
            ftp_current = athlete_profile.ftp
            ftp_target = athlete_profile.ftp_target

            # Get wellness for CTL/ATL/TSB at check_date
            target_date = check_date or date.today()
            day_before = target_date - timedelta(days=1)

            wellness_data = self.client.get_wellness(
                oldest=day_before.isoformat(), newest=target_date.isoformat()
            )

            if not wellness_data:
                print("  ⚠️  Pas de données wellness récentes")
                return None

            # Get most recent wellness
            wellness = wellness_data[-1] if wellness_data else None
            if not wellness:
                return None

            ctl_current = wellness.get("ctl", 0)
            atl_current = wellness.get("atl", 0)
            tsb_current = wellness.get("tsb", 0)

            # Determine training phase (Peaks Coaching algorithm)
            # FTP values loaded from AthleteProfile (.env configuration)
            phase_rec = determine_training_phase(
                ctl_current=ctl_current, ftp_current=ftp_current, ftp_target=ftp_target
            )

            # Calculate thresholds using Peaks module for consistency
            # This ensures all CTL calculations use the same logic
            ctl_minimum = (ftp_current / 220) * 55  # Minimum threshold (FTP current)
            ctl_target = phase_rec.ctl_target  # Target for FTP goal (from phase_rec)

            alerts = []
            recommendations = []

            # Check 1: CTL too low for current FTP minimum
            if ctl_current < ctl_minimum:
                deficit_to_minimum = ctl_minimum - ctl_current
                weeks_to_minimum = deficit_to_minimum / 2.5  # +2.5 CTL/week sustainable
                alerts.append(
                    f"CTL critique: {ctl_current:.1f} < {ctl_minimum:.0f} minimum pour FTP {ftp_current}W"
                )
                recommendations.append(
                    f"Phase 1: Atteindre CTL minimum ({ctl_minimum:.0f}) en {weeks_to_minimum:.0f} semaines"
                )
                recommendations.append(
                    f"Phase 2: Atteindre CTL optimal ({ctl_target:.0f} pour FTP {ftp_target}W) en {phase_rec.weeks_to_rebuild} semaines total"
                )
                recommendations.append(
                    "Focus: Tempo (35% TSS) + Sweet-Spot (20% TSS), 350-400 TSS/semaine charge"
                )

            # Check 2: CTL below 85% of target (suboptimal but not critical)
            elif ctl_current < (ctl_target * 0.85):
                alerts.append(
                    f"CTL sous-optimal: {ctl_current:.1f} < 85% de {ctl_target:.0f} optimal"
                )
                recommendations.append(
                    "Citation Hunter Allen: 'At 60 years young, CTL drops take months to rebuild'"
                )
                recommendations.append("Maintenir CTL à 90% du maximum en permanence (Masters 50+)")

            # Check 3: TSB critical (form)
            if tsb_current < -15:
                alerts.append(f"TSB critique: {tsb_current:+.1f} (fatigue excessive)")
                recommendations.append("Semaine récupération recommandée: 250-280 TSS")
            elif tsb_current > +15:
                alerts.append(f"TSB élevé: {tsb_current:+.1f} (déconditionnement possible)")
                recommendations.append("Augmenter volume progressivement: +2-3 CTL points/semaine")

            # Initialize PID controller with calibrated gains (Masters 50+)
            print("\n🎛️  Initialisation PID Controller...")
            pid_controller = DiscretePIDController(
                kp=0.008,  # Proportional gain (Masters 50+ adjusted)
                ki=0.001,  # Integral gain (Masters 50+ adjusted)
                kd=0.12,  # Derivative gain (Masters 50+ adjusted)
                setpoint=ftp_target,
                dead_band=3.0,  # ±3W natural FTP variation
            )

            # Load PID state from previous runs (if available)
            state_file = Path("/tmp/sprint_r10_pid_initialization.json")
            if state_file.exists():
                try:
                    import json

                    with open(state_file, encoding="utf-8") as f:
                        state_data = json.load(f)
                        pid_state = state_data.get("pid_state", {})

                        pid_controller.integral = pid_state.get("integral", 0.0)
                        pid_controller.prev_error = pid_state.get("prev_error", 0.0)
                        pid_controller.prev_ftp = pid_state.get("prev_ftp", 0)
                        pid_controller.cycle_count = pid_state.get("cycle_count", 0)

                        print(
                            f"  ✅ État PID restauré: integral={pid_controller.integral:.2f}, "
                            f"cycles={pid_controller.cycle_count}"
                        )
                except Exception as e:
                    print(f"  ⚠️  Erreur restauration état PID: {e}")

            # Compute integrated PID + Peaks recommendation
            # PID output = delta TSS, added to Peaks base for absolute recommendation
            print("🔄 Calcul recommandation intégrée PID + Peaks...")

            adherence_rate = 0.85
            avg_coupling = 0.065
            tss_completion = 0.90

            try:
                pid_peaks_rec = compute_integrated_correction(
                    ctl_current=ctl_current,
                    ftp_current=ftp_current,
                    ftp_target=ftp_target,
                    athlete_age=54,
                    pid_controller=pid_controller,
                    adherence_rate=adherence_rate,
                    avg_cardiovascular_coupling=avg_coupling,
                    tss_completion_rate=tss_completion,
                )

                print(
                    f"  ✅ Recommandation: {pid_peaks_rec.tss_per_week} TSS/semaine "
                    f"(mode: {pid_peaks_rec.mode.value}, "
                    f"confiance: {pid_peaks_rec.confidence})"
                )

                if pid_peaks_rec.override_active:
                    print(f"  🚨 OVERRIDE ACTIF: {pid_peaks_rec.mode.value}")
                elif pid_peaks_rec.pid_delta is not None:
                    print(
                        f"  🎛️ PID actif: Peaks {pid_peaks_rec.peaks_suggestion} "
                        f"+ delta {pid_peaks_rec.pid_delta:+d} "
                        f"= {pid_peaks_rec.tss_per_week} TSS/semaine"
                    )

            except Exception as e:
                print(f"  ⚠️  Erreur calcul PID+Peaks: {e}")
                import traceback

                traceback.print_exc()
                pid_peaks_rec = None

            return {
                "ctl_current": ctl_current,
                "atl_current": atl_current,
                "tsb_current": tsb_current,
                "ftp_current": ftp_current,
                "ftp_target": ftp_target,
                "ctl_minimum_for_ftp": ctl_minimum,
                "ctl_optimal_for_ftp": ctl_target,  # Optimal for FTP target (not current)
                "alerts": alerts,
                "recommendations": recommendations,
                "phase_recommendation": phase_rec,
                "pid_peaks_recommendation": pid_peaks_rec,  # NEW
            }

        except Exception as e:
            print(f"  ❌ Erreur analyse CTL Peaks: {e}")
            import traceback

            traceback.print_exc()
            return None
