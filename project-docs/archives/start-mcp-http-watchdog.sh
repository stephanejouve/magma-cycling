#!/bin/bash
# Start MCP server in HTTP/SSE mode with hot reload (watchdog)

cd /Users/stephanejouve/cyclisme-training-logs

export MCP_TRANSPORT=http
export MCP_HTTP_HOST=localhost
export MCP_HTTP_PORT=3000

echo "[$(date)] Starting MCP HTTP server with watchdog on port 3000..."

# Use watchdog to auto-restart on file changes
exec /Users/stephanejouve/cyclisme-training-logs/.venv/bin/python -m watchdog.watchmedo auto-restart \
    -d cyclisme_training_logs \
    -p "*.py" \
    -R \
    --interval 1.0 \
    --debounce-interval 0.5 \
    -- /Users/stephanejouve/cyclisme-training-logs/.venv/bin/python -m cyclisme_training_logs.mcp_server
