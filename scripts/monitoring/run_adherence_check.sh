#!/bin/bash
# Wrapper script for launchd to run workout adherence check
# This script is called by launchd at scheduled time

set -e

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$HOME/data/monitoring"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Change to project directory
cd "$PROJECT_ROOT"

# Find poetry (check common locations)
if command -v poetry >/dev/null 2>&1; then
    POETRY_CMD="poetry"
elif [ -f "$HOME/.pyenv/shims/poetry" ]; then
    POETRY_CMD="$HOME/.pyenv/shims/poetry"
elif [ -f "/usr/local/bin/poetry" ]; then
    POETRY_CMD="/usr/local/bin/poetry"
else
    echo "ERROR: poetry not found" >> "$LOG_DIR/launchd.log"
    exit 1
fi

# Run the adherence check using Poetry
$POETRY_CMD run python scripts/monitoring/check_workout_adherence.py >> "$LOG_DIR/launchd.log" 2>&1
