"""Tests for BT-017 rich profile markdown formatter."""

from datetime import date

import pytest
import yaml

from magma_cycling.config.profile_rich import (
    AvailabilityPattern,
    AvailabilitySlot,
    HrvAnomaly,
    HrvBaseline,
    Injury,
    InjuryHistory,
    MacroPlan,
    NutritionStrategy,
    PeakEvent,
    SleepBaseline,
    WeeklyTssTarget,
    save_availability_pattern,
    save_hrv_baseline,
    save_injury_history,
    save_macro_plan,
    save_nutrition_strategy,
    save_sleep_baseline,
)
from magma_cycling.prompts.rich_profile_format import format_rich_profile


@pytest.fixture
def empty_yaml(tmp_path):
    p = tmp_path / "athlete.yaml"
    p.write_text(yaml.safe_dump({"athlete": {}}), encoding="utf-8")
    return p


def test_returns_empty_when_no_field_populated(empty_yaml):
    """Migration-noop: absent fields → no section noise."""
    assert format_rich_profile(empty_yaml) == ""


def test_hrv_baseline_only(empty_yaml):
    save_hrv_baseline(
        HrvBaseline(rmssd_min=38, rmssd_max=52, alert_threshold=35),
        empty_yaml,
    )
    out = format_rich_profile(empty_yaml)
    assert "## Contexte physiologique enrichi" in out
    assert "### HRV baseline (rMSSD)" in out
    assert "38-52 ms" in out
    assert "< 35 ms" in out
    assert "### Historique blessures" not in out


def test_hrv_with_anomalies_and_peak(empty_yaml):
    save_hrv_baseline(
        HrvBaseline(
            rmssd_min=40,
            rmssd_max=55,
            rmssd_peak=70,
            alert_threshold=32,
            recovery_pattern="rebond 24h post effort dur",
            anomalies=[
                HrvAnomaly(
                    date=date(2026, 5, 12),
                    value=25.0,
                    context="virose grippale",
                    exclude_from_stats=True,
                ),
            ],
        ),
        empty_yaml,
    )
    out = format_rich_profile(empty_yaml)
    assert "Plafond recuperation : 70 ms" in out
    assert "rebond 24h post effort dur" in out
    assert "2026-05-12" in out
    assert "[exclu stats]" in out


def test_injury_active_and_watch_points(empty_yaml):
    save_injury_history(
        InjuryHistory(
            active=[
                Injury(
                    area="tendon d'Achille D",
                    status="monitoring",
                    onset_date=date(2026, 4, 1),
                    notes="progression prudente",
                ),
            ],
            watch_points=["lombaires post sorties > 4h"],
        ),
        empty_yaml,
    )
    out = format_rich_profile(empty_yaml)
    assert "### Historique blessures" in out
    assert "tendon d'Achille D (monitoring)" in out
    assert "depuis 2026-04-01" in out
    assert "lombaires post sorties > 4h" in out


def test_macro_plan_with_peak_event_and_weekly_tss(empty_yaml):
    save_macro_plan(
        MacroPlan(
            weekly_tss=[
                WeeklyTssTarget(week_label="S103", tss_target=550),
                WeeklyTssTarget(week_label="S104", tss_target=600, notes="pic charge"),
            ],
            ctl_target=85.0,
            peak_event=PeakEvent(
                name="Marmotte",
                date=date(2026, 7, 5),
                ctl_target=90.0,
                tsb_target_min=-10.0,
                tsb_target_max=-5.0,
                strategy="tapering 10j",
            ),
        ),
        empty_yaml,
    )
    out = format_rich_profile(empty_yaml)
    assert "### Plan macro" in out
    assert "CTL cible (macrocycle) : 85" in out
    assert "Marmotte (2026-07-05)" in out
    assert "TSB cible J-0 : -10.0 a -5.0" in out
    assert "tapering 10j" in out
    assert "S103 : 550 TSS" in out
    assert "S104 : 600 TSS — pic charge" in out


def test_nutrition_strategy(empty_yaml):
    save_nutrition_strategy(
        NutritionStrategy(
            carbs_per_hour_min=70,
            carbs_per_hour_max=100,
            known_issues=["crampes sur >4h", "GI limits au-dela de 110 g/h"],
        ),
        empty_yaml,
    )
    out = format_rich_profile(empty_yaml)
    assert "### Strategie nutrition (evenement)" in out
    assert "70-100 g" in out
    assert "crampes sur >4h" in out


def test_sleep_baseline(empty_yaml):
    save_sleep_baseline(
        SleepBaseline(
            avg_duration_minutes=395,
            deficit_per_night_minutes=45,
            bedtime_target="22:30",
        ),
        empty_yaml,
    )
    out = format_rich_profile(empty_yaml)
    assert "### Sommeil baseline" in out
    assert "6h35" in out
    assert "Deficit nocturne : 45 min" in out
    assert "Heure coucher cible : 22:30" in out


def test_availability_pattern(empty_yaml):
    save_availability_pattern(
        AvailabilityPattern(
            weekly_slots=[
                AvailabilitySlot(
                    day_of_week="sat",
                    time_window="08:00-13:00",
                    activity="sortie longue",
                    typical_tss=300,
                ),
                AvailabilitySlot(
                    day_of_week="wed",
                    time_window="18:30-19:30",
                    activity="INT courte",
                ),
            ],
            notes="mardi soir souvent occupé",
        ),
        empty_yaml,
    )
    out = format_rich_profile(empty_yaml)
    assert "### Disponibilites hebdo" in out
    assert "SAT 08:00-13:00 : sortie longue" in out
    assert "~300 TSS" in out
    assert "WED 18:30-19:30 : INT courte" in out
    assert "mardi soir souvent occupé" in out


def test_all_six_fields_populated(empty_yaml):
    """Full profile → section order stable + all headers present."""
    save_hrv_baseline(HrvBaseline(rmssd_min=40, rmssd_max=55, alert_threshold=35), empty_yaml)
    save_injury_history(
        InjuryHistory(watch_points=["lombaires"]),
        empty_yaml,
    )
    save_macro_plan(MacroPlan(ctl_target=80.0), empty_yaml)
    save_nutrition_strategy(
        NutritionStrategy(carbs_per_hour_min=60, carbs_per_hour_max=90),
        empty_yaml,
    )
    save_sleep_baseline(
        SleepBaseline(avg_duration_minutes=420, deficit_per_night_minutes=30),
        empty_yaml,
    )
    save_availability_pattern(
        AvailabilityPattern(
            weekly_slots=[
                AvailabilitySlot(day_of_week="sun", time_window="09:00-12:00", activity="END long")
            ]
        ),
        empty_yaml,
    )
    out = format_rich_profile(empty_yaml)

    expected_order = [
        "## Contexte physiologique enrichi",
        "### HRV baseline (rMSSD)",
        "### Historique blessures",
        "### Plan macro",
        "### Strategie nutrition (evenement)",
        "### Sommeil baseline",
        "### Disponibilites hebdo",
    ]
    positions = [out.find(h) for h in expected_order]
    assert all(p >= 0 for p in positions), f"Missing headers in: {out}"
    assert positions == sorted(positions), "Section order not stable"


def test_injury_empty_active_and_empty_watch_skipped(empty_yaml):
    """Injury history with both lists empty → whole section skipped."""
    save_injury_history(InjuryHistory(), empty_yaml)
    out = format_rich_profile(empty_yaml)
    assert "### Historique blessures" not in out
    # The rest of the output should stay empty because it's the only saved field
    assert out == ""


def test_macro_empty_all_none_skipped(empty_yaml):
    """MacroPlan with weekly_tss=[] and ctl_target=None and peak_event=None → section skipped."""
    save_macro_plan(MacroPlan(), empty_yaml)
    out = format_rich_profile(empty_yaml)
    assert "### Plan macro" not in out
    assert out == ""
