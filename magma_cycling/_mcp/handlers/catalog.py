"""MCP handler for workout catalog queries."""

from mcp.types import TextContent

from magma_cycling._mcp._utils import mcp_response, suppress_stdout_stderr


async def handle_list_workout_catalog(args: dict) -> list[TextContent]:
    """List workouts from the catalog with optional filters."""
    try:
        with suppress_stdout_stderr():
            from magma_cycling.external.zwift_client import ZwiftWorkoutClient
            from magma_cycling.external.zwift_models import ZwiftCategory

            session_type = args.get("type")
            duration_min = args.get("duration_min")
            tss_target = args.get("tss_target")
            pattern = args.get("pattern")
            limit = args.get("limit", 5)

            client = ZwiftWorkoutClient()
            stats = client.get_cache_stats()

            if stats["total_workouts"] == 0:
                return mcp_response(
                    {
                        "status": "empty",
                        "message": "Catalogue vide. Lancer: poetry run populate-zwift-cache --all",
                    }
                )

            workouts = client.search_catalog(
                session_type=session_type,
                duration_target=duration_min,
                tss_target=tss_target,
                pattern=pattern,
                limit=limit,
            )

            results = []
            for w in workouts:
                entry = {
                    "name": w.name,
                    "category": w.category.value,
                    "session_type": ZwiftCategory.to_session_type(w.category),
                    "duration_minutes": w.duration_minutes,
                    "tss": w.tss,
                    "pattern": w.pattern,
                    "segments_count": len(w.segments),
                    "intervals_description": w.to_intervals_description(),
                }
                results.append(entry)

            return mcp_response(
                {
                    "status": "success",
                    "total_in_catalog": stats["total_workouts"],
                    "results_count": len(results),
                    "filters_applied": {
                        k: v
                        for k, v in {
                            "type": session_type,
                            "duration_min": duration_min,
                            "tss_target": tss_target,
                            "pattern": pattern,
                            "limit": limit,
                        }.items()
                        if v is not None
                    },
                    "workouts": results,
                }
            )

    except Exception as e:
        return mcp_response({"error": f"Error querying catalog: {str(e)}"})
