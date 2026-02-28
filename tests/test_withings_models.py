"""
Tests for Withings Pydantic models - Black-box testing approach.

Tests data validation and model behavior without knowledge of
internal Pydantic implementation.
"""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from magma_cycling.models.withings_models import (
    HealthTrend,
    HeartRateData,
    SleepData,
    TrainingReadiness,
    WeightMeasurement,
)


class TestSleepDataModel:
    """Test SleepData model validation and behavior."""

    def test_valid_sleep_data(self):
        """Valid sleep data should create model successfully."""
        data = SleepData(
            date=date(2026, 2, 22),
            start_datetime=datetime(2026, 2, 21, 22, 30),
            end_datetime=datetime(2026, 2, 22, 7, 0),
            total_sleep_hours=7.5,
            deep_sleep_minutes=90,
            light_sleep_minutes=240,
            rem_sleep_minutes=120,
            sleep_score=85,
            wakeup_count=2,
            wakeup_minutes=5,
            breathing_disturbances=1,
        )

        assert data.total_sleep_hours == 7.5
        assert data.sleep_score == 85

    def test_minimal_sleep_data(self):
        """Sleep data with only required fields should be valid."""
        data = SleepData(
            date=date(2026, 2, 22),
            start_datetime=datetime(2026, 2, 21, 22, 30),
            end_datetime=datetime(2026, 2, 22, 7, 0),
            total_sleep_hours=7.5,
            wakeup_count=0,
        )

        assert data.deep_sleep_minutes is None
        assert data.sleep_score is None

    def test_negative_sleep_hours_invalid(self):
        """Negative sleep hours should be rejected."""
        with pytest.raises(ValidationError):
            SleepData(
                date=date(2026, 2, 22),
                start_datetime=datetime(2026, 2, 21, 22, 30),
                end_datetime=datetime(2026, 2, 22, 7, 0),
                total_sleep_hours=-1.0,
                wakeup_count=0,
            )

    def test_excessive_sleep_hours_invalid(self):
        """Sleep hours > 24 should be rejected."""
        with pytest.raises(ValidationError):
            SleepData(
                date=date(2026, 2, 22),
                start_datetime=datetime(2026, 2, 21, 22, 30),
                end_datetime=datetime(2026, 2, 22, 7, 0),
                total_sleep_hours=25.0,
                wakeup_count=0,
            )

    def test_invalid_sleep_score_range(self):
        """Sleep score outside 0-100 should be rejected."""
        with pytest.raises(ValidationError):
            SleepData(
                date=date(2026, 2, 22),
                start_datetime=datetime(2026, 2, 21, 22, 30),
                end_datetime=datetime(2026, 2, 22, 7, 0),
                total_sleep_hours=7.5,
                sleep_score=150,
                wakeup_count=0,
            )

    def test_negative_wakeup_count_invalid(self):
        """Negative wakeup count should be rejected."""
        with pytest.raises(ValidationError):
            SleepData(
                date=date(2026, 2, 22),
                start_datetime=datetime(2026, 2, 21, 22, 30),
                end_datetime=datetime(2026, 2, 22, 7, 0),
                total_sleep_hours=7.5,
                wakeup_count=-1,
            )


class TestWeightMeasurementModel:
    """Test WeightMeasurement model validation and behavior."""

    def test_valid_weight_measurement(self):
        """Valid weight measurement should create model successfully."""
        data = WeightMeasurement(
            date=date(2026, 2, 22),
            datetime=datetime(2026, 2, 22, 8, 0),
            weight_kg=75.5,
            fat_mass_kg=15.2,
            bone_mass_kg=3.5,
            muscle_mass_kg=35.8,
        )

        assert data.weight_kg == 75.5
        assert data.fat_mass_kg == 15.2

    def test_minimal_weight_measurement(self):
        """Weight measurement with only weight should be valid."""
        data = WeightMeasurement(
            date=date(2026, 2, 22), datetime=datetime(2026, 2, 22, 8, 0), weight_kg=75.5
        )

        assert data.weight_kg == 75.5
        assert data.fat_mass_kg is None

    def test_zero_weight_invalid(self):
        """Zero or negative weight should be rejected."""
        with pytest.raises(ValidationError):
            WeightMeasurement(
                date=date(2026, 2, 22), datetime=datetime(2026, 2, 22, 8, 0), weight_kg=0
            )

        with pytest.raises(ValidationError):
            WeightMeasurement(
                date=date(2026, 2, 22), datetime=datetime(2026, 2, 22, 8, 0), weight_kg=-5.0
            )

    def test_negative_body_composition_invalid(self):
        """Negative body composition values should be rejected."""
        with pytest.raises(ValidationError):
            WeightMeasurement(
                date=date(2026, 2, 22),
                datetime=datetime(2026, 2, 22, 8, 0),
                weight_kg=75.5,
                fat_mass_kg=-1.0,
            )


class TestTrainingReadinessModel:
    """Test TrainingReadiness model validation and behavior."""

    def test_valid_training_readiness(self):
        """Valid training readiness should create model successfully."""
        data = TrainingReadiness(
            date=date(2026, 2, 22),
            sleep_hours=7.5,
            sleep_score=85,
            deep_sleep_minutes=90,
            ready_for_intense=True,
            recommended_intensity="all_systems_go",
            veto_reasons=[],
            recommendations=["Optimal conditions for training"],
            weight_kg=75.5,
            resting_hr=55,
        )

        assert data.ready_for_intense is True
        assert data.recommended_intensity == "all_systems_go"

    def test_recovery_only_intensity(self):
        """Recovery only intensity should be valid."""
        data = TrainingReadiness(
            date=date(2026, 2, 22),
            sleep_hours=5.0,
            ready_for_intense=False,
            recommended_intensity="recovery_only",
        )

        assert data.recommended_intensity == "recovery_only"

    def test_invalid_intensity_rejected(self):
        """Invalid intensity value should be rejected."""
        with pytest.raises(ValidationError):
            TrainingReadiness(
                date=date(2026, 2, 22),
                sleep_hours=7.5,
                ready_for_intense=True,
                recommended_intensity="invalid_intensity",
            )

    def test_negative_sleep_hours_invalid(self):
        """Negative sleep hours should be rejected."""
        with pytest.raises(ValidationError):
            TrainingReadiness(
                date=date(2026, 2, 22),
                sleep_hours=-1.0,
                ready_for_intense=False,
                recommended_intensity="recovery_only",
            )

    def test_invalid_sleep_score_range(self):
        """Sleep score outside 0-100 should be rejected."""
        with pytest.raises(ValidationError):
            TrainingReadiness(
                date=date(2026, 2, 22),
                sleep_hours=7.5,
                sleep_score=150,
                ready_for_intense=True,
                recommended_intensity="all_systems_go",
            )


class TestHealthTrendModel:
    """Test HealthTrend model validation and behavior."""

    def test_valid_health_trend(self):
        """Valid health trend should create model successfully."""
        data = HealthTrend(
            start_date=date(2026, 2, 15),
            end_date=date(2026, 2, 22),
            avg_sleep_hours=7.2,
            avg_sleep_score=82.5,
            nights_above_7h=6,
            total_nights=7,
            sleep_debt_hours=-1.4,
            weight_start_kg=76.0,
            weight_end_kg=75.5,
            weight_delta_kg=-0.5,
            avg_resting_hr=56,
            status="optimal",
            alerts=[],
        )

        assert data.status == "optimal"
        assert data.avg_sleep_hours == 7.2

    def test_sleep_debt_status(self):
        """Sleep debt status should be valid."""
        data = HealthTrend(
            start_date=date(2026, 2, 15),
            end_date=date(2026, 2, 22),
            avg_sleep_hours=6.0,
            nights_above_7h=2,
            total_nights=7,
            sleep_debt_hours=7.0,
            status="debt",
        )

        assert data.status == "debt"
        assert data.sleep_debt_hours == 7.0

    def test_invalid_status_rejected(self):
        """Invalid status value should be rejected."""
        with pytest.raises(ValidationError):
            HealthTrend(
                start_date=date(2026, 2, 15),
                end_date=date(2026, 2, 22),
                avg_sleep_hours=7.2,
                nights_above_7h=6,
                total_nights=7,
                sleep_debt_hours=0,
                status="invalid_status",
            )

    def test_zero_total_nights_invalid(self):
        """Zero total nights should be rejected."""
        with pytest.raises(ValidationError):
            HealthTrend(
                start_date=date(2026, 2, 15),
                end_date=date(2026, 2, 22),
                avg_sleep_hours=7.2,
                nights_above_7h=0,
                total_nights=0,
                sleep_debt_hours=0,
                status="optimal",
            )

    def test_negative_avg_sleep_hours_invalid(self):
        """Negative average sleep hours should be rejected."""
        with pytest.raises(ValidationError):
            HealthTrend(
                start_date=date(2026, 2, 15),
                end_date=date(2026, 2, 22),
                avg_sleep_hours=-1.0,
                nights_above_7h=0,
                total_nights=7,
                sleep_debt_hours=0,
                status="critical",
            )


class TestHeartRateDataModel:
    """Test HeartRateData model validation and behavior."""

    def test_valid_heart_rate_data(self):
        """Valid heart rate data should create model successfully."""
        data = HeartRateData(
            date=date(2026, 2, 22),
            datetime=datetime(2026, 2, 22, 8, 0),
            resting_hr=55,
            hr_variability=45.5,
        )

        assert data.resting_hr == 55
        assert data.hr_variability == 45.5

    def test_minimal_heart_rate_data(self):
        """Heart rate data without HRV should be valid."""
        data = HeartRateData(
            date=date(2026, 2, 22), datetime=datetime(2026, 2, 22, 8, 0), resting_hr=55
        )

        assert data.resting_hr == 55
        assert data.hr_variability is None

    def test_zero_resting_hr_invalid(self):
        """Zero or negative resting HR should be rejected."""
        with pytest.raises(ValidationError):
            HeartRateData(
                date=date(2026, 2, 22), datetime=datetime(2026, 2, 22, 8, 0), resting_hr=0
            )

    def test_excessive_resting_hr_invalid(self):
        """Resting HR > 300 should be rejected."""
        with pytest.raises(ValidationError):
            HeartRateData(
                date=date(2026, 2, 22), datetime=datetime(2026, 2, 22, 8, 0), resting_hr=350
            )

    def test_negative_hrv_invalid(self):
        """Negative HRV should be rejected."""
        with pytest.raises(ValidationError):
            HeartRateData(
                date=date(2026, 2, 22),
                datetime=datetime(2026, 2, 22, 8, 0),
                resting_hr=55,
                hr_variability=-10,
            )


class TestModelSerialization:
    """Test model JSON serialization/deserialization - external behavior."""

    def test_sleep_data_to_dict(self):
        """SleepData should serialize to dict."""
        data = SleepData(
            date=date(2026, 2, 22),
            start_datetime=datetime(2026, 2, 21, 22, 30),
            end_datetime=datetime(2026, 2, 22, 7, 0),
            total_sleep_hours=7.5,
            sleep_score=85,
            wakeup_count=2,
        )

        result = data.model_dump()

        assert isinstance(result, dict)
        assert result["total_sleep_hours"] == 7.5
        assert result["sleep_score"] == 85

    def test_weight_measurement_to_json(self):
        """WeightMeasurement should serialize to JSON."""
        data = WeightMeasurement(
            date=date(2026, 2, 22), datetime=datetime(2026, 2, 22, 8, 0), weight_kg=75.5
        )

        json_str = data.model_dump_json()

        assert isinstance(json_str, str)
        assert "75.5" in json_str

    def test_training_readiness_from_dict(self):
        """TrainingReadiness should deserialize from dict."""
        input_data = {
            "date": "2026-02-22",
            "sleep_hours": 7.5,
            "ready_for_intense": True,
            "recommended_intensity": "all_systems_go",
        }

        data = TrainingReadiness(**input_data)

        assert data.sleep_hours == 7.5
        assert data.ready_for_intense is True


class TestSleepDataNewFields:
    """Test new universal sleep metrics added for provider abstraction."""

    def test_all_new_fields_optional(self):
        data = SleepData(
            date=date(2026, 2, 28),
            start_datetime=datetime(2026, 2, 27, 23, 0),
            end_datetime=datetime(2026, 2, 28, 6, 30),
            total_sleep_hours=7.5,
            wakeup_count=1,
        )
        assert data.sleep_efficiency is None
        assert data.hr_average is None
        assert data.hr_min is None
        assert data.hr_max is None
        assert data.rr_average is None
        assert data.rr_min is None
        assert data.rr_max is None
        assert data.sleep_latency_min is None
        assert data.out_of_bed_count is None

    def test_new_fields_populated(self):
        data = SleepData(
            date=date(2026, 2, 28),
            start_datetime=datetime(2026, 2, 27, 23, 0),
            end_datetime=datetime(2026, 2, 28, 6, 30),
            total_sleep_hours=7.5,
            wakeup_count=1,
            sleep_efficiency=92,
            hr_average=58,
            hr_min=48,
            hr_max=72,
            rr_average=14.5,
            rr_min=12.0,
            rr_max=18.0,
            sleep_latency_min=12.5,
            out_of_bed_count=1,
        )
        assert data.sleep_efficiency == 92
        assert data.hr_average == 58
        assert data.hr_min == 48
        assert data.hr_max == 72
        assert data.rr_average == 14.5
        assert data.rr_min == 12.0
        assert data.rr_max == 18.0
        assert data.sleep_latency_min == 12.5
        assert data.out_of_bed_count == 1

    def test_sleep_efficiency_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            SleepData(
                date=date(2026, 2, 28),
                start_datetime=datetime(2026, 2, 27, 23, 0),
                end_datetime=datetime(2026, 2, 28, 6, 30),
                total_sleep_hours=7.5,
                wakeup_count=1,
                sleep_efficiency=110,
            )

    def test_new_fields_in_model_dump(self):
        data = SleepData(
            date=date(2026, 2, 28),
            start_datetime=datetime(2026, 2, 27, 23, 0),
            end_datetime=datetime(2026, 2, 28, 6, 30),
            total_sleep_hours=7.5,
            wakeup_count=1,
            hr_average=55,
        )
        dumped = data.model_dump()
        assert dumped["hr_average"] == 55
        assert dumped["sleep_efficiency"] is None


class TestTrainingReadinessNewFields:
    """Test new readiness threshold fields."""

    def test_new_fields_optional(self):
        data = TrainingReadiness(
            date=date(2026, 2, 28),
            sleep_hours=7.5,
            ready_for_intense=True,
            recommended_intensity="all_systems_go",
        )
        assert data.sufficient_duration is None
        assert data.deep_sleep_ok is None

    def test_new_fields_populated(self):
        data = TrainingReadiness(
            date=date(2026, 2, 28),
            sleep_hours=7.5,
            ready_for_intense=True,
            recommended_intensity="all_systems_go",
            sufficient_duration=True,
            deep_sleep_ok=True,
        )
        assert data.sufficient_duration is True
        assert data.deep_sleep_ok is True

    def test_new_fields_in_model_dump(self):
        data = TrainingReadiness(
            date=date(2026, 2, 28),
            sleep_hours=5.0,
            ready_for_intense=False,
            recommended_intensity="recovery_only",
            sufficient_duration=False,
            deep_sleep_ok=False,
        )
        dumped = data.model_dump()
        assert dumped["sufficient_duration"] is False
        assert dumped["deep_sleep_ok"] is False
