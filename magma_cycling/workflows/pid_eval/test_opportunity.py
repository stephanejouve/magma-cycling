"""Test opportunity and CTL monitoring mixin for PID evaluation."""

import traceback
from datetime import date, datetime, timedelta
from typing import Any


class TestOpportunityMixin:
    """Check FTP test opportunities and monitor CTL progression."""

    def check_test_opportunity(self) -> dict[str, Any] | None:
        """Check if FTP test is recommended based on PID discrete cycle timing.

        Returns:
            Dict with recommendation details if test is due, None otherwise
        """
        # Get current wellness for TSB
        try:
            wellness_data = self.client.get_wellness(
                date.today().isoformat(), date.today().isoformat()
            )
            if not wellness_data:
                return None

            wellness = wellness_data[0]
            tsb = wellness.get("tsb", 0)
            ctl = wellness.get("ctl", 0)

        except Exception as e:
            print(f"  ⚠️  Could not fetch wellness data: {e}")
            return None

        # Check time since last test (look for high IF activities in past 16 weeks)
        weeks_back = 16
        start_check = date.today() - timedelta(weeks=weeks_back)

        try:
            activities = self.client.get_activities(
                start_check.isoformat(), date.today().isoformat()
            )

            # Look for test-like activities (IF > 0.90, duration 35-65 min)
            test_activities = [
                a
                for a in activities
                if a.get("icu_intensity", 0) > 0.90 and 35 <= a.get("moving_time", 0) / 60 <= 65
            ]

            if test_activities:
                last_test = max(test_activities, key=lambda x: x.get("start_date_local", ""))
                last_test_date_str = last_test.get("start_date_local", "")[:10]
                last_test_date = datetime.strptime(last_test_date_str, "%Y-%m-%d").date()
                weeks_since_test = (date.today() - last_test_date).days / 7
            else:
                weeks_since_test = 16

        except Exception:
            weeks_since_test = 8

        # Decision logic
        test_overdue = weeks_since_test >= 6
        form_ready = tsb >= 5
        form_neutral = -5 <= tsb <= 5
        fitness_adequate = ctl >= 40

        recommendation = None

        if test_overdue and form_ready and fitness_adequate:
            recommendation = {
                "status": "READY",
                "weeks_since_test": weeks_since_test,
                "tsb": tsb,
                "ctl": ctl,
                "message": f"Test FTP recommandé (dernier test: {weeks_since_test:.1f} sem)",
                "timing": "Cette semaine (TSB acceptable)",
            }
        elif test_overdue and form_neutral and fitness_adequate:
            recommendation = {
                "status": "NEEDS_TAPER",
                "weeks_since_test": weeks_since_test,
                "tsb": tsb,
                "ctl": ctl,
                "message": (
                    f"Test FTP recommandé avec affûtage (dernier: {weeks_since_test:.1f} sem)"
                ),
                "timing": "Semaine prochaine après réduction volume (-40% TSS)",
            }
        elif test_overdue:
            recommendation = {
                "status": "OVERDUE_LOW_FITNESS",
                "weeks_since_test": weeks_since_test,
                "tsb": tsb,
                "ctl": ctl,
                "message": f"Test overdue ({weeks_since_test:.1f} sem) mais condition limitée",
                "timing": "Prévoir après 2 semaines de préparation",
            }

        return recommendation

    def monitor_ctl_progression_vs_peaks(self) -> dict[str, Any] | None:
        """Monitor CTL progression vs Peaks Coaching targets.

        Returns:
            Dict with CTL monitoring results or None if failed
        """
        print(f"\n{'=' * 60}")
        print("📈 CTL Progression Monitoring (Peaks Coaching)")
        print(f"{'=' * 60}")

        try:
            # Get current wellness for CTL
            wellness_data = self.client.get_wellness(
                date.today().isoformat(), date.today().isoformat()
            )
            if not wellness_data:
                print("  ⚠️  No wellness data available")
                return None

            wellness = wellness_data[0]
            ctl_current = wellness.get("ctl", 0)
            atl_current = wellness.get("atl", 0)
            tsb_current = wellness.get("tsb", 0)

            # Load athlete profile from env for FTP and age
            from magma_cycling.config.athlete_profile import AthleteProfile

            athlete_profile = AthleteProfile.from_env()
            ftp_current = athlete_profile.ftp
            ftp_target = athlete_profile.ftp_target
            athlete_age = athlete_profile.age

            # Calculate Peaks Coaching thresholds
            ctl_minimum = (ftp_current / 220) * 55
            ctl_optimal = (ftp_current / 220) * 70

            # Calculate CTL progression rate (last 7 days)
            week_ago = date.today() - timedelta(days=7)
            wellness_week_ago = self.client.get_wellness(week_ago.isoformat(), week_ago.isoformat())

            if wellness_week_ago:
                ctl_week_ago = wellness_week_ago[0].get("ctl", ctl_current)
                ctl_weekly_change = ctl_current - ctl_week_ago
            else:
                ctl_weekly_change = 0

            # Estimate weeks to reach targets
            if ctl_weekly_change > 0:
                weeks_to_minimum = max(0, (ctl_minimum - ctl_current) / ctl_weekly_change)
                weeks_to_optimal = max(0, (ctl_optimal - ctl_current) / ctl_weekly_change)
            else:
                weeks_to_minimum = float("inf")
                weeks_to_optimal = float("inf")

            # Determine status
            if ctl_current < 50:
                status = "CRITICAL"
                status_emoji = "🚨"
                message = "CTL critique < 50 - Reconstruction base urgente"
            elif ctl_current < ctl_minimum:
                status = "LOW"
                status_emoji = "⚠️"
                message = f"CTL sous minimum Peaks ({ctl_minimum:.0f})"
            elif ctl_current < (ctl_optimal * 0.85):
                status = "SUBOPTIMAL"
                status_emoji = "📊"
                message = f"CTL sous-optimal (< 85% de {ctl_optimal:.0f})"
            else:
                status = "OPTIMAL"
                status_emoji = "✅"
                message = "CTL dans la zone optimale Peaks"

            print(f"\n{status_emoji} Status: {status}")
            print(f"   {message}")
            print("\n📊 Métriques Actuelles:")
            print(f"   CTL: {ctl_current:.1f}")
            print(f"   ATL: {atl_current:.1f}")
            print(f"   TSB: {tsb_current:+.1f}")
            print(f"   FTP: {ftp_current}W")
            print(f"\n🎯 Seuils Peaks (FTP {ftp_current}W):")
            print(f"   CTL minimum: {ctl_minimum:.0f}")
            print(f"   CTL optimal: {ctl_optimal:.0f}")
            print("\n📈 Progression:")
            print(f"   Changement 7 jours: {ctl_weekly_change:+.1f} points")

            if weeks_to_minimum < float("inf"):
                print(f"   Semaines → minimum: {weeks_to_minimum:.1f} semaines")
            if weeks_to_optimal < float("inf"):
                print(f"   Semaines → optimal: {weeks_to_optimal:.1f} semaines")

            # Determine Peaks phase
            from magma_cycling.planning.peaks_phases import determine_training_phase

            phase_rec = determine_training_phase(
                ctl_current=ctl_current,
                ftp_current=ftp_current,
                ftp_target=ftp_target,
                athlete_age=athlete_age,
            )

            print(f"\n🎯 Phase Peaks Coaching: {phase_rec.phase.value.upper()}")
            print(f"   TSS recommandé: {phase_rec.weekly_tss_load} TSS/semaine (charge)")
            print(f"   TSS recovery: {phase_rec.weekly_tss_recovery} TSS/semaine")

            # Recommendations
            recommendations = []
            if status == "CRITICAL":
                recommendations.append("🚨 PEAKS OVERRIDE actif (CTL < 50)")
                recommendations.append("Focus Tempo (35%) + Sweet-Spot (20%)")
                recommendations.append(f"Target: {phase_rec.weekly_tss_load} TSS/semaine")
            elif status == "LOW":
                recommendations.append("Reconstruction base progressive")
                recommendations.append(f"Maintenir {phase_rec.weekly_tss_load} TSS/semaine")
                recommendations.append(f"CTL target: {ctl_minimum:.0f} minimum")
            elif status == "SUBOPTIMAL":
                recommendations.append("PID peut devenir actif si CTL ≥ 50")
                recommendations.append("Continuer progression régulière")
            else:
                recommendations.append("Maintenir CTL à 90% du maximum (Masters 50+)")
                recommendations.append("PID autonome recommandé")

            if recommendations:
                print("\n💡 Recommandations:")
                for rec in recommendations:
                    print(f"   • {rec}")

            return {
                "ctl_current": ctl_current,
                "atl_current": atl_current,
                "tsb_current": tsb_current,
                "ftp_current": ftp_current,
                "ctl_minimum": ctl_minimum,
                "ctl_optimal": ctl_optimal,
                "ctl_weekly_change": ctl_weekly_change,
                "weeks_to_minimum": (weeks_to_minimum if weeks_to_minimum < float("inf") else None),
                "weeks_to_optimal": (weeks_to_optimal if weeks_to_optimal < float("inf") else None),
                "status": status,
                "message": message,
                "phase": phase_rec.phase.value,
                "weekly_tss_recommended": phase_rec.weekly_tss_load,
                "recommendations": recommendations,
            }

        except Exception as e:
            print(f"  ❌ Erreur monitoring CTL: {e}")
            traceback.print_exc()
            return None
