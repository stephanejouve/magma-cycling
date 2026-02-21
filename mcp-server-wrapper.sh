#!/bin/bash
# MCP Server Wrapper - Use virtualenv directly
cd /Users/stephanejouve/cyclisme-training-logs
exec /Users/stephanejouve/Library/Caches/pypoetry/virtualenvs/cyclisme-training-logs-L0Jb5TFj-py3.13/bin/python -m cyclisme_training_logs.mcp_server 2>> /tmp/mcp-server-debug.log
