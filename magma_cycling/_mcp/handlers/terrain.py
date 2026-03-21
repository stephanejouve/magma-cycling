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

            if name := args.get("name"):
                circuit.name = name

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


async def handle_evaluate_outdoor_execution(args: dict) -> list[TextContent]:
    """Evaluate outdoor execution against terrain-adapted prescription."""
    try:
        with suppress_stdout_stderr():
            from magma_cycling.config import create_intervals_client
            from magma_cycling.terrain.adaptation import adapt_workout_to_terrain
            from magma_cycling.terrain.evaluation import evaluate_outdoor_execution
            from magma_cycling.terrain.models import AdaptedWorkout
            from magma_cycling.terrain.storage import load_circuit

            client = create_intervals_client()
            provider_info = client.get_provider_info()

            activity_id = args["activity_id"]

            # Get activity streams for the realized ride
            streams = client.get_activity_streams(activity_id)

            # Get or build the AdaptedWorkout prescription
            if "adapted_workout" in args and args["adapted_workout"]:
                adapted = AdaptedWorkout(**args["adapted_workout"])
            else:
                # Need circuit + workout + ftp to generate prescription
                circuit_id = args.get("circuit_id")
                workout = args.get("workout")
                ftp_watts = args.get("ftp_watts")

                if not circuit_id or not workout or not ftp_watts:
                    return mcp_response(
                        {
                            "error": (
                                "Fournir soit adapted_workout, "
                                "soit circuit_id + workout + ftp_watts "
                                "pour generer la prescription"
                            )
                        }
                    )

                circuit = load_circuit(circuit_id)
                if circuit is None:
                    return mcp_response({"error": f"Circuit non trouve: {circuit_id}"})

                adapted = adapt_workout_to_terrain(
                    workout=workout,
                    circuit=circuit,
                    ftp_watts=ftp_watts,
                    athlete_weight_kg=args.get("athlete_weight_kg", 70.0),
                    profil_fibres=args.get("profil_fibres", "mixte"),
                )

            # Evaluate execution vs prescription
            evaluation = evaluate_outdoor_execution(streams, adapted, activity_id=activity_id)

            result = {
                "status": "success",
                "evaluation": evaluation.model_dump(mode="json"),
            }

        return mcp_response(result, provider_info=provider_info, default=str)

    except Exception as e:
        return mcp_response({"error": f"Evaluation failed: {e}"})
