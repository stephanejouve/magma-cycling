#!/bin/bash
# MCP Server Wrapper - Supports dev mode with hot reload

cd /Users/stephanejouve/cyclisme-training-logs

VENV_PYTHON=/Users/stephanejouve/cyclisme-training-logs/.venv/bin/python
DEBUG_LOG=/tmp/mcp-server-debug.log

# Export transport mode from env or default to stdio
export MCP_TRANSPORT="${MCP_TRANSPORT:-stdio}"
export MCP_HTTP_HOST="${MCP_HTTP_HOST:-localhost}"
export MCP_HTTP_PORT="${MCP_HTTP_PORT:-3000}"

echo "[MCP] Transport mode: $MCP_TRANSPORT" >> "$DEBUG_LOG"

# Check if dev mode is enabled via environment variable
if [ "$MCP_DEV_MODE" = "1" ]; then
    echo "[MCP] Dev mode enabled - auto-reload on file changes" >> "$DEBUG_LOG"

    # Use watchdog's watchmedo for auto-restart (works for both stdio and http)
    exec $VENV_PYTHON -m watchdog.watchmedo auto-restart \
        -d cyclisme_training_logs \
        -p "*.py" \
        -R \
        --interval 1.0 \
        --debounce-interval 0.5 \
        -- $VENV_PYTHON -m cyclisme_training_logs.mcp_server 2>> "$DEBUG_LOG"
else
    echo "[MCP] Production mode - no auto-reload" >> "$DEBUG_LOG"

    # Standard mode - no auto-reload
    exec $VENV_PYTHON -m cyclisme_training_logs.mcp_server 2>> "$DEBUG_LOG"
fi
