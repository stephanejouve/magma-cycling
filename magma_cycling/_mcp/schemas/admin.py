"""Admin tool schemas."""

from mcp.types import Tool


def get_tools() -> list[Tool]:
    """Return admin tool schemas."""
    return [
        Tool(
            name="reload-server",
            description="[DEV] Reload MCP server modules to pick up code changes without restarting Claude Desktop",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="system-info",
            description="Return active providers and system metadata (health, calendar, AI). Use at conversation start to discover the runtime configuration.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="report-config-file-state",
            description=(
                "Report self-reported state (sha256, size, perms_octal, exists) of "
                "magma-cycling YAML config files as seen by the running container. "
                "Read-only, no side effect. Covers (a) the bundled fallback "
                "`magma_cycling/config/athlete_context.yaml` and (b) the user YAML "
                "resolved by `resolve_athlete_yaml_path()`. Not an external integrity "
                "attestation: a compromised container could mis-report. For external "
                "verification of bundle integrity, inspect image overlay layers from "
                "the host (docker cp / image diff)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "enum": ["bundle", "user_yaml", "both"],
                        "default": "both",
                        "description": (
                            "Which file(s) to inspect. 'bundle' = packaged read-only "
                            "fallback shipped with the code. 'user_yaml' = mutable "
                            "user config resolved by resolve_athlete_yaml_path(). "
                            "'both' (default) reports both."
                        ),
                    },
                },
            },
        ),
    ]
