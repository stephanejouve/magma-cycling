#!/usr/bin/env python3
"""
Script d'initialisation et test du PID Controller Discret.

Sprint R10 - Jour 2
Initialise le PID avec les gains calibrés et simule un backtest sur données historiques.

Usage:
    poetry run python magma_cycling/scripts/initialize_pid_controller.py

Author: Claude Code + Stéphane Jouve
Created: 2026-02-15
"""

import json
from datetime import datetime
from pathlib import Path

from magma_cycling.intelligence.discrete_pid_controller import DiscretePIDController
from magma_cycling.utils.cli import cli_main


def load_historical_data():
    """Load historical data from Sprint R10 extraction."""
    data_file = Path("/tmp/sprint_r10_historical_data.json")

    if not data_file.exists():
        raise FileNotFoundError("Historical data not found. Run Sprint R10 Day 1 extraction first.")

    with open(data_file, encoding="utf-8") as f:
        return json.load(f)


def simulate_backtest(controller: DiscretePIDController, historical_data: dict):
    """
    Simulate backtest on S074-S080 to validate PID gains.

    Args:
        controller: Initialized PID controller
        historical_data: Historical data dict from Day 1 extraction

    Returns:
        Dict with backtest results
    """
    print("🔍 BACKTEST SIMULATION S074-S080")
    print("=" * 70)
    print()

    # Simulate FTP tests (we only have S080 real test at 223W)
    # Extrapolate backward assuming linear decline matching CTL decline

    # CTL declined from 45.4 to 42.4 over 49 days = -3.0 points
    # Assume FTP correlation: ~1W per CTL point (rough estimate)
    # CTL -3.0 → FTP likely declined too

    # Hypothetical FTP progression (conservative estimate):
    # S074 (day 0):  FTP ~226W (CTL 45.4)
    # S080 (day 49): FTP 223W (CTL 42.4, measured)

    # Simulate 2 test cycles (we don't have intermediate tests, this is hypothetical)
    test_scenarios = [
        {
            "cycle": "S074-S077",
            "week_start": 0,
            "week_end": 3,
            "measured_ftp": 226,  # Hypothetical start
            "duration_weeks": 3,
            "adherence": 0.85,
            "coupling": 0.065,
            "tss_completion": 0.88,
        },
        {
            "cycle": "S077-S080",
            "week_start": 3,
            "week_end": 7,
            "measured_ftp": 223,  # Real S080 test
            "duration_weeks": 4,
            "adherence": 0.72,  # Low (S078 was 16.7%)
            "coupling": 0.072,
            "tss_completion": 0.80,
        },
    ]

    results = []

    for scenario in test_scenarios:
        print(f"📊 Cycle {scenario['cycle']}")
        print(f"   Duration: {scenario['duration_weeks']} semaines")
        print(f"   FTP mesuré: {scenario['measured_ftp']}W")
        print()

        # Compute enhanced correction
        correction = controller.compute_cycle_correction_enhanced(
            measured_ftp=scenario["measured_ftp"],
            cycle_duration_weeks=scenario["duration_weeks"],
            adherence_rate=scenario["adherence"],
            avg_cardiovascular_coupling=scenario["coupling"],
            tss_completion_rate=scenario["tss_completion"],
        )

        # Display results
        print(f"   Error: {correction['error']:+.1f}W (setpoint 230W)")
        print(f"   P term: {correction['p_term']:.4f}W")
        print(f"   I term: {correction['i_term']:.4f}W")
        print(f"   D term: {correction['d_term']:.4f}W")
        print(f"   Output: {correction['output']:.4f}W")
        print(f"   TSS/semaine (original): {correction['tss_per_week']:+d}")
        print(f"   TSS/semaine (adjusted): {correction['tss_per_week_adjusted']:+d}")
        print()

        # Validation
        validation = correction["validation"]
        print(f"   ✅ Validated: {validation['validated']}")
        print(f"   Confidence: {validation['confidence']:.2f}")

        if validation["red_flags"]:
            print(f"   🚨 Red flags: {len(validation['red_flags'])}")
            for flag in validation["red_flags"]:
                print(f"      • {flag}")

        if validation["warnings"]:
            print(f"   ⚠️  Warnings: {len(validation['warnings'])}")
            for warning in validation["warnings"]:
                print(f"      • {warning}")

        if validation["adjustments"]:
            print("   🔧 Adjustments:")
            for adj in validation["adjustments"]:
                print(f"      • {adj}")

        print()
        print("   💬 Recommendation:")
        print(f"      {correction['recommendation']}")
        print()
        print("-" * 70)
        print()

        results.append(
            {
                "cycle": scenario["cycle"],
                "correction": correction,
            }
        )

    return results


def compute_s081_s086_correction(controller: DiscretePIDController):
    """
    Calculate PID correction for upcoming cycle S081-S086.

    Args:
        controller: PID controller with S080 state

    Returns:
        Dict with correction and recommendations
    """
    print("🎯 CORRECTION CYCLE S081-S086")
    print("=" * 70)
    print()

    # S080 metrics (baseline)
    ftp_s080 = 223  # Measured
    ctl_s080 = 42.4
    atl_s080 = 45.8
    tsb_s080 = -3.4

    print("📊 État S080 (baseline):")
    print(f"   FTP: {ftp_s080}W")
    print(f"   CTL: {ctl_s080}")
    print(f"   ATL: {atl_s080}")
    print(f"   TSB: {tsb_s080:+.1f}")
    print()

    # Hypothetical metrics for S081-S086 cycle
    # Assume we improve adherence and reduce coupling
    adherence_target = 0.88  # Target improvement
    coupling_target = 0.065  # Target quality
    tss_completion_target = 0.90  # Target capacity

    print("🎯 Cibles cycle S081-S086:")
    print(f"   Adherence: {adherence_target:.0%} (vs {0.72:.0%} S077-S080)")
    print(f"   Coupling: {coupling_target:.1%} (vs {7.2:.1%} S077-S080)")
    print(f"   TSS completion: {tss_completion_target:.0%}")
    print()

    # Compute correction for 6-week cycle
    correction = controller.compute_cycle_correction_enhanced(
        measured_ftp=ftp_s080,
        cycle_duration_weeks=6,  # Standard cycle
        adherence_rate=adherence_target,
        avg_cardiovascular_coupling=coupling_target,
        tss_completion_rate=tss_completion_target,
    )

    print("📈 CORRECTION PID:")
    print(f"   Error: {correction['error']:+.1f}W (setpoint 230W)")
    print(f"   P term: {correction['p_term']:.4f}W")
    print(f"   I term: {correction['i_term']:.4f}W")
    print(f"   D term: {correction['d_term']:.4f}W")
    print(f"   Output: {correction['output']:.4f}W")
    print()
    print(f"   TSS/semaine (original): {correction['tss_per_week']:+d}")
    print(f"   TSS/semaine (adjusted): {correction['tss_per_week_adjusted']:+d}")
    print()

    # Validation
    validation = correction["validation"]
    if validation["validated"]:
        print(f"   ✅ VALIDÉ (confidence: {validation['confidence']:.2f})")
    else:
        print("   ⚠️  VALIDATION ÉCHOUÉE")
        for flag in validation["red_flags"]:
            print(f"      • {flag}")

    print()
    print("💬 RECOMMANDATION:")
    print(f"   {correction['recommendation']}")
    print()

    # Calculate target CTL
    # Current: 42.4, Target for FTP 230W: ~56 (Peaks minimum adjusted)
    # With +8 TSS/semaine sustained, CTL increase ~1.14 points/week
    # Over 6 weeks: +6.84 points → CTL final ~49.2

    tss_increase = correction["tss_per_week_adjusted"]
    ctl_increase_per_week = tss_increase / 7  # Rough CTL formula
    ctl_final_estimated = ctl_s080 + (ctl_increase_per_week * 6)

    print("📊 PROJECTION CTL (6 semaines):")
    print(f"   CTL actuel: {ctl_s080}")
    print(f"   TSS augmentation: +{tss_increase} TSS/semaine")
    print(f"   CTL gain estimé: +{ctl_increase_per_week * 6:.1f} points")
    print(f"   CTL final estimé: {ctl_final_estimated:.1f}")
    print()

    # Peaks Coaching validation
    ctl_minimum_peaks = (230 / 220) * 55  # ~57.5 for FTP 230W
    ctl_optimal_peaks = (230 / 220) * 70  # ~73.2 for FTP 230W

    print("🎯 Seuils Peaks Coaching (FTP cible 230W):")
    print(f"   CTL minimum: {ctl_minimum_peaks:.1f}")
    print(f"   CTL optimal: {ctl_optimal_peaks:.1f}")
    print(
        f"   CTL final projeté: {ctl_final_estimated:.1f} "
        f"({(ctl_final_estimated / ctl_optimal_peaks) * 100:.1f}% optimal)"
    )

    if ctl_final_estimated < ctl_minimum_peaks:
        print("   ⚠️  Toujours sous minimum Peaks après S086")
        print("   → Nécessite 2-3 cycles supplémentaires")
    else:
        print("   ✅ Au-dessus minimum Peaks après S086")

    print()

    return {
        "correction": correction,
        "ctl_projection": {
            "current": ctl_s080,
            "final_estimated": ctl_final_estimated,
            "gain": ctl_final_estimated - ctl_s080,
            "peaks_minimum": ctl_minimum_peaks,
            "peaks_optimal": ctl_optimal_peaks,
        },
    }


@cli_main
def main():
    """Main execution."""
    print()
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║       SPRINT R10 - INITIALISATION PID CONTROLLER (Jour 2)     ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()

    # Load historical data
    print("📂 Chargement données historiques...")
    historical_data = load_historical_data()
    print(f"   ✅ {len(historical_data['activities'])} activités chargées")
    print()

    # Initialize PID controller with calibrated gains
    print("🎛️  Initialisation PID Controller")
    print("=" * 70)

    # Gains validés Jour 1
    kp = 0.008  # Proportionnel (-20% Masters)
    ki = 0.001  # Intégral (-50% Masters)
    kd = 0.12  # Dérivé (-20% Masters)
    setpoint = 230  # FTP cible (conservative +7W from 223W)

    print(f"   Kp (Proportionnel): {kp}")
    print(f"   Ki (Intégral):      {ki}")
    print(f"   Kd (Dérivé):        {kd}")
    print(f"   Setpoint (FTP):     {setpoint}W")
    print("   Dead-band:          ±3W")
    print()

    controller = DiscretePIDController(
        kp=kp,
        ki=ki,
        kd=kd,
        setpoint=setpoint,
        dead_band=3.0,
    )

    print("   ✅ PID Controller initialisé")
    print()

    # Run backtest simulation
    backtest_results = simulate_backtest(controller, historical_data)

    # Compute S081-S086 correction
    s081_correction = compute_s081_s086_correction(controller)

    # Display PID state
    print("=" * 70)
    print("📊 ÉTAT PID APRÈS S080")
    print("=" * 70)
    state = controller.get_state_info()
    print(f"   Integral accumulé: {state['integral']:.2f} W·cycles")
    print(f"   Erreur précédente: {state['prev_error']:+.1f}W")
    print(f"   FTP précédent:     {state['prev_ftp']}W")
    print(f"   Cycles traités:    {state['cycle_count']}")
    print()

    # Save results
    output_file = Path("/tmp/sprint_r10_pid_initialization.json")
    results = {
        "initialized_at": datetime.now().isoformat(),
        "gains": {"kp": kp, "ki": ki, "kd": kd},
        "setpoint": setpoint,
        "backtest_results": [
            {
                "cycle": r["cycle"],
                "tss_adjustment": r["correction"]["tss_per_week_adjusted"],
                "validated": r["correction"]["validation"]["validated"],
            }
            for r in backtest_results
        ],
        "s081_s086_correction": {
            "tss_per_week": s081_correction["correction"]["tss_per_week_adjusted"],
            "ctl_projection": s081_correction["ctl_projection"],
            "recommendation": s081_correction["correction"]["recommendation"],
        },
        "pid_state": state,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"💾 Résultats sauvegardés: {output_file}")
    print()

    # Summary
    print("=" * 70)
    print("✅ INITIALISATION COMPLÈTE")
    print("=" * 70)
    print()
    print("📋 PROCHAINES ÉTAPES:")
    print("   1. Appliquer correction +8 TSS/semaine sur S081-S086")
    print("   2. Prioriser régularité TSS hebdo (réduire CV de 48% à <20%)")
    print("   3. Améliorer adherence (cible >85%)")
    print("   4. Test FTP fin S086 (dans 6 semaines)")
    print()


if __name__ == "__main__":
    main()
