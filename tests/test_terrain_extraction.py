"""Tests for terrain extraction from activity streams."""

from unittest.mock import MagicMock

import pytest

from magma_cycling.terrain.extraction import (
    classify_grade,
    extract_terrain_from_activity,
    extract_terrain_from_streams,
)
from magma_cycling.terrain.models import GradeCategory


class TestClassifyGrade:
    """Direct classify_grade tests."""

    def test_flat(self):
        assert classify_grade(0.0) == GradeCategory.plat

    def test_climb(self):
        assert classify_grade(3.0) == GradeCategory.montee

    def test_steep_descent(self):
        assert classify_grade(-6.0) == GradeCategory.descente_raide


def _make_flat_streams(n_km: int = 5) -> list[dict]:
    """Generate flat terrain streams (altitude constant at 100m)."""
    n_points = n_km * 100  # 100 points per km
    distances = [i * 10.0 for i in range(n_points)]  # 10m spacing
    altitudes = [100.0] * n_points
    return [
        {"type": "distance", "data": distances},
        {"type": "altitude", "data": altitudes},
    ]


def _make_climb_streams(n_km: int = 3, grade_pct: float = 5.0) -> list[dict]:
    """Generate climbing terrain streams."""
    n_points = n_km * 100
    distances = [i * 10.0 for i in range(n_points)]
    # grade = elevation_change / distance * 100
    # elevation_change per 10m = grade_pct / 100 * 10 = grade_pct * 0.1
    elev_per_step = grade_pct * 0.1
    altitudes = [100.0 + i * elev_per_step for i in range(n_points)]
    return [
        {"type": "distance", "data": distances},
        {"type": "altitude", "data": altitudes},
    ]


def _make_streams_with_gear(n_km: int = 3) -> list[dict]:
    """Generate streams with gear data (climb on small ring)."""
    n_points = n_km * 100
    distances = [i * 10.0 for i in range(n_points)]
    altitudes = [100.0 + i * 0.3 for i in range(n_points)]  # ~3% grade
    front_gear = [34] * n_points  # Small chainring
    rear_gear = [28] * n_points  # Large cog
    cadence = [80.0] * n_points
    watts = [200.0] * n_points
    return [
        {"type": "distance", "data": distances},
        {"type": "altitude", "data": altitudes},
        {"type": "FrontGear", "data": front_gear},
        {"type": "RearGear", "data": rear_gear},
        {"type": "cadence", "data": cadence},
        {"type": "watts", "data": watts},
    ]


class TestExtractTerrainFromStreams:
    """extract_terrain_from_streams tests."""

    def test_flat_terrain(self):
        """Flat streams produce flat-category segments."""
        streams = _make_flat_streams(5)
        circuit = extract_terrain_from_streams("i100", streams, activity_name="Flat")

        assert circuit.circuit_id == "TC_i100"
        assert circuit.name == "Flat"
        assert circuit.source_type == "activity"
        assert len(circuit.segments) >= 4
        for seg in circuit.segments:
            assert seg.grade_category == GradeCategory.plat
            assert abs(seg.grade_pct) <= 0.5

    def test_climb_terrain(self):
        """Climbing streams produce montee_raide segments."""
        streams = _make_climb_streams(3, grade_pct=6.0)
        circuit = extract_terrain_from_streams("i200", streams)

        assert len(circuit.segments) >= 2
        for seg in circuit.segments:
            assert seg.grade_category == GradeCategory.montee_raide
            assert seg.grade_pct > 4.0
        assert circuit.total_elevation_gain_m > 0

    def test_no_gear_streams(self):
        """Without gear streams, gear_profiles is empty."""
        streams = _make_flat_streams(3)
        circuit = extract_terrain_from_streams("i300", streams)
        assert circuit.gear_profiles == []

    def test_with_gear_streams(self):
        """With gear streams, gear_profiles are populated."""
        streams = _make_streams_with_gear(3)
        circuit = extract_terrain_from_streams("i400", streams)

        assert len(circuit.gear_profiles) > 0
        profile = circuit.gear_profiles[0]
        assert profile.primary_gear.front_teeth == 34
        assert profile.primary_gear.rear_teeth == 28
        assert profile.avg_cadence_rpm > 0
        assert profile.avg_power_watts > 0

    def test_missing_altitude_raises(self):
        """Missing altitude stream raises ValueError."""
        streams = [{"type": "distance", "data": [0, 100, 200]}]
        with pytest.raises(ValueError, match="altitude"):
            extract_terrain_from_streams("i500", streams)

    def test_missing_distance_raises(self):
        """Missing distance stream raises ValueError."""
        streams = [{"type": "altitude", "data": [100, 101, 102]}]
        with pytest.raises(ValueError, match="distance"):
            extract_terrain_from_streams("i600", streams)

    def test_mismatched_lengths_raises(self):
        """Mismatched stream lengths raise ValueError."""
        streams = [
            {"type": "distance", "data": [0, 100, 200]},
            {"type": "altitude", "data": [100, 101]},
        ]
        with pytest.raises(ValueError, match="same length"):
            extract_terrain_from_streams("i700", streams)

    def test_total_distance(self):
        """Total distance is computed correctly."""
        streams = _make_flat_streams(10)
        circuit = extract_terrain_from_streams("i800", streams)
        # 10 km of streams, expect close to 10 km total
        assert 9.0 <= circuit.total_distance_km <= 10.5

    def test_segment_distance(self):
        """Each segment is approximately 1000m."""
        streams = _make_flat_streams(5)
        circuit = extract_terrain_from_streams("i900", streams)
        for seg in circuit.segments:
            assert 900 <= seg.distance_m <= 1100


class TestExtractTerrainFromActivity:
    """extract_terrain_from_activity wrapper tests."""

    def test_delegates_to_streams(self):
        """Wrapper calls client methods and delegates to stream extraction."""
        mock_client = MagicMock()
        mock_client.get_activity.return_value = {"name": "Morning Ride"}
        mock_client.get_activity_streams.return_value = _make_flat_streams(3)

        circuit = extract_terrain_from_activity(mock_client, "i999")

        mock_client.get_activity.assert_called_once_with("i999")
        mock_client.get_activity_streams.assert_called_once_with("i999")
        assert circuit.circuit_id == "TC_i999"
        assert circuit.name == "Morning Ride"
