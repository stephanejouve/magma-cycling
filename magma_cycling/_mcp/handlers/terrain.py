"""MCP handlers for terrain circuit extraction and workout adaptation."""

from mcp.types import TextContent

from magma_cycling._mcp._utils import mcp_response, suppress_stdout_stderr


async def handle_extract_terrain_circuit(args: dict) -> list[TextContent]:
    """Extract terrain profile from a past activity."""
    try:
        with suppress_stdout_stderr():
            from magma_cycling.config import create_intervals_client
            from magma_cycling.terrain.extraction import (
                extract_terrain_from_activity,
            )
            from magma_cycling.terrain.storage import save_circuit

            client = create_intervals_client()
            provider_info = client.get_provider_info()

            activity_id = args["activity_id"]
            should_save = args.get("save", True)

            circuit = extract_terrain_from_activity(client, activity_id)

            saved_path = None
            if should_save:
                saved_path = save_circuit(circuit)

            result = {
                "status": "success",
                "circuit": circuit.model_dump(mode="json"),
            }
            if saved_path:
                result["_saved_to"] = str(saved_path)

        return mcp_response(result, provider_info=provider_info, default=str)

    except Exception as e:
        return mcp_response({"error": f"Extraction failed: {e}"})


async def handle_adapt_workout_to_terrain(args: dict) -> list[TextContent]:
    """Adapt a structured workout to a terrain circuit."""
    try:
        with suppress_stdout_stderr():
            circuit_id = args.get("circuit_id")
            activity_id = args.get("activity_id")

            if not circuit_id and not activity_id:
                return mcp_response(
                    {
                        "error": (
                            "Fournir soit circuit_id (circuit sauvegarde) "
                            "soit activity_id (extraction a la volee)"
                        )
                    }
                )

            provider_info = None

            if circuit_id:
                from magma_cycling.terrain.storage import load_circuit

                circuit = load_circuit(circuit_id)
                if circuit is None:
                    return mcp_response({"error": f"Circuit non trouve: {circuit_id}"})
            else:
                from magma_cycling.config import create_intervals_client
                from magma_cycling.terrain.extraction import (
                    extract_terrain_from_activity,
                )

                client = create_intervals_client()
                provider_info = client.get_provider_info()
                circuit = extract_terrain_from_activity(client, activity_id)

            from magma_cycling.terrain.adaptation import (
                adapt_workout_to_terrain,
            )

            workout = args["workout"]
            ftp_watts = args["ftp_watts"]
            athlete_weight_kg = args.get("athlete_weight_kg", 70.0)
            profil_fibres = args.get("profil_fibres", "mixte")
            workout_name = args.get("workout_name", "Workout")
            original_tss = args.get("original_tss", 0)

            adapted = adapt_workout_to_terrain(
                workout=workout,
                circuit=circuit,
                ftp_watts=ftp_watts,
                athlete_weight_kg=athlete_weight_kg,
                profil_fibres=profil_fibres,
                original_workout_name=workout_name,
                original_tss=original_tss,
            )

            result = {
                "status": "success",
                "adapted_workout": adapted.model_dump(mode="json"),
            }

        return mcp_response(result, provider_info=provider_info, default=str)

    except Exception as e:
        return mcp_response({"error": f"Adaptation failed: {e}"})


async def handle_list_terrain_circuits(args: dict) -> list[TextContent]:
    """List all saved terrain circuits."""
    try:
        with suppress_stdout_stderr():
            from magma_cycling.terrain.storage import list_circuits

            circuits = list_circuits()

        return mcp_response(
            {
                "status": "success",
                "count": len(circuits),
                "circuits": circuits,
            }
        )

    except Exception as e:
        return mcp_response({"error": f"List circuits failed: {e}"})
