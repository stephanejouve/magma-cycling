#!/bin/bash
# MCP Server Wrapper - Supports dev mode with hot reload

cd /Users/stephanejouve/cyclisme-training-logs

VENV_PYTHON=/Users/stephanejouve/Library/Caches/pypoetry/virtualenvs/cyclisme-training-logs-L0Jb5TFj-py3.13/bin/python
DEBUG_LOG=/tmp/mcp-server-debug.log

# Check if dev mode is enabled via environment variable
if [ "$MCP_DEV_MODE" = "1" ]; then
    echo "[MCP] Dev mode enabled - auto-reload on file changes" >> "$DEBUG_LOG"

    # Use watchdog's watchmedo for auto-restart
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
