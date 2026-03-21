"""Tests for MCP terrain handlers."""

import json
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling._mcp.handlers.terrain import (
    handle_adapt_workout_to_terrain,
    handle_evaluate_outdoor_execution,
    handle_extract_terrain_circuit,
    handle_list_terrain_circuits,
)


def _make_flat_streams(n_km=3):
    """Generate flat terrain streams for mocking."""
    n_points = n_km * 100
    return [
        {"type": "distance", "data": [i * 10.0 for i in range(n_points)]},
        {"type": "altitude", "data": [100.0] * n_points},
    ]


def _parse_response(result):
    """Parse MCP TextContent response to dict."""
    assert len(result) == 1
    return json.loads(result[0].text)


@pytest.mark.asyncio
class TestHandleExtractTerrainCircuit:
    """handle_extract_terrain_circuit tests."""

    async def test_extract_success(self, tmp_path):
        """Extract circuit from mocked activity streams."""
        mock_client = MagicMock()
        mock_client.get_activity.return_value = {"name": "Morning Ride"}
        mock_client.get_activity_streams.return_value = _make_flat_streams(5)
        mock_client.get_provider_info.return_value = {
            "provider": "intervals_icu",
            "athlete_id": "i42",
            "status": "ready",
        }

        with (
            patch(
                "magma_cycling.config.create_intervals_client",
                return_value=mock_client,
            ),
            patch(
                "magma_cycling.terrain.storage.save_circuit",
                return_value=tmp_path / "TC_i999.yaml",
            ),
        ):
            result = await handle_extract_terrain_circuit({"activity_id": "i999", "save": True})

        data = _parse_response(result)
        assert data["status"] == "success"
        assert "circuit" in data
        assert data["circuit"]["circuit_id"] == "TC_i999"
        assert "_metadata" in data
        assert data["_metadata"]["provider"]["provider"] == "intervals_icu"

    async def test_extract_with_custom_name(self, tmp_path):
        """Extract circuit with custom name overriding auto-generated one."""
        mock_client = MagicMock()
        mock_client.get_activity.return_value = {"name": "S084-04-END-EnduranceLongue-V001"}
        mock_client.get_activity_streams.return_value = _make_flat_streams(5)
        mock_client.get_provider_info.return_value = {
            "provider": "intervals_icu",
            "athlete_id": "i42",
            "status": "ready",
        }

        with (
            patch(
                "magma_cycling.config.create_intervals_client",
                return_value=mock_client,
            ),
            patch(
                "magma_cycling.terrain.storage.save_circuit",
                return_value=tmp_path / "TC_i131572602.yaml",
            ),
        ):
            result = await handle_extract_terrain_circuit(
                {"activity_id": "i131572602", "name": "Boucle Sud Chas-Billom"}
            )

        data = _parse_response(result)
        assert data["status"] == "success"
        assert data["circuit"]["name"] == "Boucle Sud Chas-Billom"

    async def test_extract_no_save(self):
        """Extract without saving."""
        mock_client = MagicMock()
        mock_client.get_activity.return_value = {"name": "Test"}
        mock_client.get_activity_streams.return_value = _make_flat_streams(3)
        mock_client.get_provider_info.return_value = {
            "provider": "intervals_icu",
            "athlete_id": "i42",
            "status": "ready",
        }

        with patch(
            "magma_cycling.config.create_intervals_client",
            return_value=mock_client,
        ):
            result = await handle_extract_terrain_circuit({"activity_id": "i100", "save": False})

        data = _parse_response(result)
        assert data["status"] == "success"
        assert "_saved_to" not in data


@pytest.mark.asyncio
class TestHandleAdaptWorkoutToTerrain:
    """handle_adapt_workout_to_terrain tests."""

    async def test_adapt_with_activity_id(self):
        """Adapt workout using on-the-fly extraction."""
        mock_client = MagicMock()
        mock_client.get_activity.return_value = {"name": "Hill Loop"}
        mock_client.get_activity_streams.return_value = _make_flat_streams(5)
        mock_client.get_provider_info.return_value = {
            "provider": "intervals_icu",
            "athlete_id": "i42",
            "status": "ready",
        }

        with patch(
            "magma_cycling.config.create_intervals_client",
            return_value=mock_client,
        ):
            result = await handle_adapt_workout_to_terrain(
                {
                    "activity_id": "i200",
                    "workout": {"phases": [{"duration_min": 30, "power_pct": 88}]},
                    "ftp_watts": 260,
                }
            )

        data = _parse_response(result)
        assert data["status"] == "success"
        assert "adapted_workout" in data
        adapted = data["adapted_workout"]
        assert adapted["ftp_watts"] == 260
        assert len(adapted["segments"]) > 0

    async def test_adapt_with_circuit_id(self):
        """Adapt workout using a saved circuit."""
        from magma_cycling.terrain.models import (
            GradeCategory,
            TerrainCircuit,
            TerrainSegment,
        )

        circuit = TerrainCircuit(
            circuit_id="TC_test",
            name="Test",
            total_distance_km=3.0,
            total_elevation_gain_m=0,
            total_elevation_loss_m=0,
            segments=[
                TerrainSegment(
                    km_index=i,
                    distance_m=1000.0,
                    elevation_start_m=100,
                    elevation_end_m=100,
                    elevation_gain_m=0,
                    elevation_loss_m=0,
                    grade_pct=0.0,
                    grade_category=GradeCategory.plat,
                )
                for i in range(3)
            ],
        )

        with patch(
            "magma_cycling.terrain.storage.load_circuit",
            return_value=circuit,
        ):
            result = await handle_adapt_workout_to_terrain(
                {
                    "circuit_id": "TC_test",
                    "workout": "10min@65% + 20min@88%",
                    "ftp_watts": 250,
                }
            )

        data = _parse_response(result)
        assert data["status"] == "success"

    async def test_error_no_circuit_no_activity(self):
        """Error when neither circuit_id nor activity_id provided."""
        result = await handle_adapt_workout_to_terrain(
            {
                "workout": {"phases": [{"duration_min": 30, "power_pct": 88}]},
                "ftp_watts": 260,
            }
        )

        data = _parse_response(result)
        assert "error" in data

    async def test_error_circuit_not_found(self):
        """Error when circuit_id does not exist."""
        with patch(
            "magma_cycling.terrain.storage.load_circuit",
            return_value=None,
        ):
            result = await handle_adapt_workout_to_terrain(
                {
                    "circuit_id": "TC_nonexistent",
                    "workout": {"phases": [{"duration_min": 30, "power_pct": 88}]},
                    "ftp_watts": 260,
                }
            )

        data = _parse_response(result)
        assert "error" in data
        assert "non trouve" in data["error"]


@pytest.mark.asyncio
class TestHandleListTerrainCircuits:
    """handle_list_terrain_circuits tests."""

    async def test_list_empty(self):
        """Empty list when no circuits saved."""
        with patch(
            "magma_cycling.terrain.storage.list_circuits",
            return_value=[],
        ):
            result = await handle_list_terrain_circuits({})

        data = _parse_response(result)
        assert data["status"] == "success"
        assert data["count"] == 0
        assert data["circuits"] == []

    async def test_list_with_circuits(self):
        """List returns saved circuits."""
        mock_circuits = [
            {
                "id": "TC_i131572602",
                "name": "Boucle Sud",
                "distance_km": 77.4,
                "elevation_gain_m": 486,
            },
            {
                "id": "TC_i999",
                "name": "Col Test",
                "distance_km": 12.0,
                "elevation_gain_m": 650,
            },
        ]
        with patch(
            "magma_cycling.terrain.storage.list_circuits",
            return_value=mock_circuits,
        ):
            result = await handle_list_terrain_circuits({})

        data = _parse_response(result)
        assert data["status"] == "success"
        assert data["count"] == 2
        assert data["circuits"][0]["id"] == "TC_i131572602"
        assert data["circuits"][1]["distance_km"] == 12.0


@pytest.mark.asyncio
class TestHandleEvaluateOutdoorExecution:
    """handle_evaluate_outdoor_execution tests."""

    async def test_evaluate_with_adapted_workout(self):
        """Evaluate with explicit AdaptedWorkout prescription."""
        from magma_cycling.terrain.models import (
            AdaptedSegment,
            AdaptedWorkout,
            GradeCategory,
        )

        adapted = AdaptedWorkout(
            workout_name="Test Workout",
            circuit_id="TC_test",
            circuit_name="Test Circuit",
            ftp_watts=250,
            segments=[
                AdaptedSegment(
                    km_index=i,
                    terrain_grade_pct=0.0,
                    terrain_category=GradeCategory.plat,
                    original_power_pct=75.0,
                    adapted_power_pct=75.0,
                    power_adjustment_pct=0.0,
                    target_cadence_rpm=85,
                    cadence_min_rpm=80,
                    cadence_max_rpm=95,
                    recommended_gear=None,
                    instruction="",
                )
                for i in range(3)
            ],
        )

        n_points = 300
        mock_streams = [
            {"type": "distance", "data": [i * 10.0 for i in range(n_points)]},
            {"type": "altitude", "data": [100.0] * n_points},
            {"type": "watts", "data": [190.0] * n_points},
            {"type": "cadence", "data": [85.0] * n_points},
        ]

        mock_client = MagicMock()
        mock_client.get_activity_streams.return_value = mock_streams
        mock_client.get_provider_info.return_value = {
            "provider": "intervals_icu",
            "athlete_id": "i42",
            "status": "ready",
        }

        with patch(
            "magma_cycling.config.create_intervals_client",
            return_value=mock_client,
        ):
            result = await handle_evaluate_outdoor_execution(
                {
                    "activity_id": "i300",
                    "adapted_workout": adapted.model_dump(mode="json"),
                }
            )

        data = _parse_response(result)
        assert data["status"] == "success"
        assert "evaluation" in data
        eval_data = data["evaluation"]
        assert eval_data["activity_id"] == "i300"
        assert eval_data["cadence_compliance_pct"] > 0
        assert "_metadata" in data
        assert data["_metadata"]["provider"]["provider"] == "intervals_icu"

    async def test_evaluate_generates_prescription(self):
        """Evaluate by generating prescription from circuit + workout."""
        from magma_cycling.terrain.models import (
            GradeCategory,
            TerrainCircuit,
            TerrainSegment,
        )

        circuit = TerrainCircuit(
            circuit_id="TC_eval",
            name="Eval Circuit",
            total_distance_km=3.0,
            total_elevation_gain_m=0,
            total_elevation_loss_m=0,
            segments=[
                TerrainSegment(
                    km_index=i,
                    distance_m=1000.0,
                    elevation_start_m=100,
                    elevation_end_m=100,
                    elevation_gain_m=0,
                    elevation_loss_m=0,
                    grade_pct=0.0,
                    grade_category=GradeCategory.plat,
                )
                for i in range(3)
            ],
        )

        n_points = 300
        mock_streams = [
            {"type": "distance", "data": [i * 10.0 for i in range(n_points)]},
            {"type": "altitude", "data": [100.0] * n_points},
            {"type": "watts", "data": [200.0] * n_points},
            {"type": "cadence", "data": [88.0] * n_points},
        ]

        mock_client = MagicMock()
        mock_client.get_activity_streams.return_value = mock_streams
        mock_client.get_provider_info.return_value = {
            "provider": "intervals_icu",
            "athlete_id": "i42",
            "status": "ready",
        }

        with (
            patch(
                "magma_cycling.config.create_intervals_client",
                return_value=mock_client,
            ),
            patch(
                "magma_cycling.terrain.storage.load_circuit",
                return_value=circuit,
            ),
        ):
            result = await handle_evaluate_outdoor_execution(
                {
                    "activity_id": "i400",
                    "circuit_id": "TC_eval",
                    "workout": "30min@75%",
                    "ftp_watts": 260,
                }
            )

        data = _parse_response(result)
        assert data["status"] == "success"
        assert "evaluation" in data

    async def test_evaluate_error_missing_params(self):
        """Error when no adapted_workout and missing circuit/workout/ftp."""
        mock_client = MagicMock()
        mock_client.get_activity_streams.return_value = []
        mock_client.get_provider_info.return_value = {
            "provider": "intervals_icu",
            "athlete_id": "i42",
            "status": "ready",
        }

        with patch(
            "magma_cycling.config.create_intervals_client",
            return_value=mock_client,
        ):
            result = await handle_evaluate_outdoor_execution(
                {
                    "activity_id": "i500",
                }
            )

        data = _parse_response(result)
        assert "error" in data
