"""Tests for the BT-017 rich athlete profile fields."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

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
    clear_hrv_baseline,
    load_availability_pattern,
    load_hrv_baseline,
    load_injury_history,
    load_macro_plan,
    load_nutrition_strategy,
    load_sleep_baseline,
    save_availability_pattern,
    save_hrv_baseline,
    save_injury_history,
    save_macro_plan,
    save_nutrition_strategy,
    save_sleep_baseline,
)

# ---------------------------------------------------------------------------
# HrvBaseline + HrvAnomaly
# ---------------------------------------------------------------------------


class TestHrvBaseline:
    def test_minimal_valid(self):
        obj = HrvBaseline(rmssd_min=50, rmssd_max=53, alert_threshold=46)
        assert obj.rmssd_min == 50
        assert obj.rmssd_peak is None
        assert obj.anomalies == []

    def test_with_peak_and_anomaly(self):
        obj = HrvBaseline(
            rmssd_min=50,
            rmssd_max=53,
            rmssd_peak=61,
            alert_threshold=46,
            anomalies=[
                HrvAnomaly(
                    date=date(2026, 4, 26),
                    value=25,
                    context="insolation post-LBL",
                    exclude_from_stats=True,
                ),
            ],
            recovery_pattern="rebond 1-2 jours apres creux",
        )
        assert obj.rmssd_peak == 61
        assert obj.anomalies[0].exclude_from_stats is True

    def test_max_below_min_rejected(self):
        with pytest.raises(ValidationError, match="rmssd_max"):
            HrvBaseline(rmssd_min=60, rmssd_max=50, alert_threshold=46)

    def test_peak_below_max_rejected(self):
        with pytest.raises(ValidationError, match="rmssd_peak"):
            HrvBaseline(rmssd_min=50, rmssd_max=53, rmssd_peak=52, alert_threshold=46)

    def test_alert_above_min_rejected(self):
        with pytest.raises(ValidationError, match="alert_threshold"):
            HrvBaseline(rmssd_min=50, rmssd_max=53, alert_threshold=60)

    def test_negative_rmssd_rejected(self):
        with pytest.raises(ValidationError):
            HrvBaseline(rmssd_min=-1, rmssd_max=53, alert_threshold=46)

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            HrvBaseline(
                rmssd_min=50,
                rmssd_max=53,
                alert_threshold=46,
                unknown="oops",  # type: ignore[call-arg]
            )

    def test_anomaly_empty_context_rejected(self):
        with pytest.raises(ValidationError):
            HrvAnomaly(date=date(2026, 4, 26), value=25, context="")


# ---------------------------------------------------------------------------
# InjuryHistory
# ---------------------------------------------------------------------------


class TestInjuryHistory:
    def test_empty_defaults(self):
        obj = InjuryHistory()
        assert obj.active == []
        assert obj.watch_points == []

    def test_with_active_injury(self):
        obj = InjuryHistory(
            active=[
                Injury(
                    area="genou droit, insertion quadri",
                    status="active",
                    onset_date=date(2026, 6, 13),
                    notes="apparu Ardechoise J3",
                ),
            ],
            watch_points=["ne pas negliger muscu"],
        )
        assert obj.active[0].status == "active"
        assert obj.watch_points == ["ne pas negliger muscu"]

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            Injury(area="x", status="invalid")  # type: ignore[arg-type]

    def test_empty_area_rejected(self):
        with pytest.raises(ValidationError):
            Injury(area="", status="active")


# ---------------------------------------------------------------------------
# MacroPlan + PeakEvent
# ---------------------------------------------------------------------------


class TestPeakEvent:
    def test_minimal_valid(self):
        ev = PeakEvent(name="La Marmotte", date=date(2026, 6, 28))
        assert ev.tsb_target_min is None
        assert ev.tsb_target_max is None

    def test_tsb_range(self):
        ev = PeakEvent(
            name="La Marmotte",
            date=date(2026, 6, 28),
            ctl_target=64,
            tsb_target_min=10,
            tsb_target_max=15,
            strategy="68-72% FTP en montee, 70-80g glucides/h",
        )
        assert ev.tsb_target_min == 10

    def test_tsb_range_inverted_rejected(self):
        with pytest.raises(ValidationError, match="tsb_target_max"):
            PeakEvent(
                name="x",
                date=date(2026, 6, 28),
                tsb_target_min=20,
                tsb_target_max=10,
            )


class TestMacroPlan:
    def test_empty_defaults(self):
        obj = MacroPlan()
        assert obj.weekly_tss == []
        assert obj.peak_event is None

    def test_full(self):
        obj = MacroPlan(
            weekly_tss=[
                WeeklyTssTarget(week_label="S010", tss_target=550),
                WeeklyTssTarget(week_label="S011", tss_target=400, notes="taper"),
            ],
            ctl_target=64,
            peak_event=PeakEvent(name="La Marmotte", date=date(2026, 6, 28)),
        )
        assert obj.weekly_tss[1].notes == "taper"

    def test_zero_tss_rejected(self):
        with pytest.raises(ValidationError):
            WeeklyTssTarget(week_label="S001", tss_target=0)


# ---------------------------------------------------------------------------
# NutritionStrategy
# ---------------------------------------------------------------------------


class TestNutritionStrategy:
    def test_minimal_valid(self):
        obj = NutritionStrategy(carbs_per_hour_min=70, carbs_per_hour_max=80)
        assert obj.known_issues == []

    def test_with_issues(self):
        obj = NutritionStrategy(
            carbs_per_hour_min=70,
            carbs_per_hour_max=80,
            known_issues=["crampes d'estomac sur 4h+"],
        )
        assert "crampes" in obj.known_issues[0]

    def test_inverted_range_rejected(self):
        with pytest.raises(ValidationError, match="carbs_per_hour_max"):
            NutritionStrategy(carbs_per_hour_min=90, carbs_per_hour_max=60)


# ---------------------------------------------------------------------------
# SleepBaseline
# ---------------------------------------------------------------------------


class TestSleepBaseline:
    def test_minimal_valid(self):
        obj = SleepBaseline(avg_duration_minutes=446, deficit_per_night_minutes=34)
        assert obj.bedtime_target is None

    def test_with_bedtime(self):
        obj = SleepBaseline(
            avg_duration_minutes=446,
            deficit_per_night_minutes=34,
            bedtime_target="23:00",
        )
        assert obj.bedtime_target == "23:00"

    def test_invalid_bedtime_format_rejected(self):
        with pytest.raises(ValidationError):
            SleepBaseline(
                avg_duration_minutes=446,
                deficit_per_night_minutes=34,
                bedtime_target="2300",
            )

    def test_negative_deficit_rejected(self):
        with pytest.raises(ValidationError):
            SleepBaseline(avg_duration_minutes=446, deficit_per_night_minutes=-1)


# ---------------------------------------------------------------------------
# AvailabilityPattern
# ---------------------------------------------------------------------------


class TestAvailabilityPattern:
    def test_minimal_valid(self):
        obj = AvailabilityPattern()
        assert obj.weekly_slots == []

    def test_with_slots(self):
        obj = AvailabilityPattern(
            weekly_slots=[
                AvailabilitySlot(
                    day_of_week="mon",
                    time_window="12:00-13:30",
                    activity="velocommute",
                    typical_tss=16,
                ),
                AvailabilitySlot(
                    day_of_week="sat",
                    time_window="08:00-12:00",
                    activity="sortie longue",
                ),
            ],
        )
        assert obj.weekly_slots[0].typical_tss == 16

    def test_invalid_day_rejected(self):
        with pytest.raises(ValidationError):
            AvailabilitySlot(
                day_of_week="monday",  # type: ignore[arg-type]
                time_window="12:00-13:30",
                activity="velocommute",
            )

    def test_invalid_time_window_rejected(self):
        with pytest.raises(ValidationError):
            AvailabilitySlot(
                day_of_week="mon",
                time_window="12h-13h30",
                activity="velocommute",
            )


# ---------------------------------------------------------------------------
# YAML I/O — using HrvBaseline + InjuryHistory as representatives.
# The save/load/clear helpers share the same generic backend, so per-field
# duplication would be redundant; we still spot-check the round trip on each
# field below.
# ---------------------------------------------------------------------------


class TestHrvBaselineYamlIo:
    def test_load_returns_none_when_yaml_absent(self, tmp_path: Path):
        assert load_hrv_baseline(tmp_path / "absent.yaml") is None

    def test_load_returns_none_when_key_absent(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        yaml_path.write_text("athlete:\n  name: Test\n", encoding="utf-8")
        assert load_hrv_baseline(yaml_path) is None

    def test_invalid_payload_returns_none(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        yaml_path.write_text(
            "athlete:\n  hrv_baseline:\n    rmssd_min: 50\n",  # missing required
            encoding="utf-8",
        )
        assert load_hrv_baseline(yaml_path) is None

    def test_save_creates_yaml(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        obj = HrvBaseline(rmssd_min=50, rmssd_max=53, alert_threshold=46)
        save_hrv_baseline(obj, yaml_path)
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert data["athlete"]["hrv_baseline"]["rmssd_min"] == 50

    def test_save_preserves_other_athlete_fields(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        yaml_path.write_text("athlete:\n  name: Test\n  age: 54\n", encoding="utf-8")
        save_hrv_baseline(HrvBaseline(rmssd_min=50, rmssd_max=53, alert_threshold=46), yaml_path)
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert data["athlete"]["name"] == "Test"
        assert data["athlete"]["age"] == 54
        assert data["athlete"]["hrv_baseline"]["rmssd_min"] == 50

    def test_clear_returns_none_when_absent(self, tmp_path: Path):
        assert clear_hrv_baseline(tmp_path / "absent.yaml") is None

    def test_clear_removes_existing(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        save_hrv_baseline(HrvBaseline(rmssd_min=50, rmssd_max=53, alert_threshold=46), yaml_path)
        clear_hrv_baseline(yaml_path)
        assert load_hrv_baseline(yaml_path) is None


class TestRoundTripAllFields:
    def test_injury_history(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        original = InjuryHistory(
            active=[Injury(area="genou droit", status="monitoring")],
            watch_points=["volume montee progressif"],
        )
        save_injury_history(original, yaml_path)
        assert load_injury_history(yaml_path) == original

    def test_macro_plan(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        original = MacroPlan(
            weekly_tss=[WeeklyTssTarget(week_label="S010", tss_target=550)],
            ctl_target=64,
            peak_event=PeakEvent(
                name="La Marmotte",
                date=date(2026, 6, 28),
                tsb_target_min=10,
                tsb_target_max=15,
            ),
        )
        save_macro_plan(original, yaml_path)
        assert load_macro_plan(yaml_path) == original

    def test_nutrition_strategy(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        original = NutritionStrategy(
            carbs_per_hour_min=70,
            carbs_per_hour_max=80,
            known_issues=["crampes d'estomac sur 4h+"],
        )
        save_nutrition_strategy(original, yaml_path)
        assert load_nutrition_strategy(yaml_path) == original

    def test_sleep_baseline(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        original = SleepBaseline(
            avg_duration_minutes=446,
            deficit_per_night_minutes=34,
            bedtime_target="23:00",
        )
        save_sleep_baseline(original, yaml_path)
        assert load_sleep_baseline(yaml_path) == original

    def test_availability_pattern(self, tmp_path: Path):
        yaml_path = tmp_path / "athlete.yaml"
        original = AvailabilityPattern(
            weekly_slots=[
                AvailabilitySlot(
                    day_of_week="mon",
                    time_window="12:00-13:30",
                    activity="velocommute",
                    typical_tss=16,
                ),
            ],
        )
        save_availability_pattern(original, yaml_path)
        assert load_availability_pattern(yaml_path) == original

    def test_clear_keeps_other_rich_fields(self, tmp_path: Path):
        """Clearing one field must not touch the others."""
        yaml_path = tmp_path / "athlete.yaml"
        save_hrv_baseline(HrvBaseline(rmssd_min=50, rmssd_max=53, alert_threshold=46), yaml_path)
        save_sleep_baseline(
            SleepBaseline(avg_duration_minutes=446, deficit_per_night_minutes=34),
            yaml_path,
        )
        clear_hrv_baseline(yaml_path)
        assert load_hrv_baseline(yaml_path) is None
        sleep = load_sleep_baseline(yaml_path)
        assert sleep is not None
        assert sleep.avg_duration_minutes == 446
