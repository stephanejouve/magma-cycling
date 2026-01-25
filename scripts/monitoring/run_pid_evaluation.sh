#!/bin/bash
# Wrapper script for launchd to run PID daily evaluation
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
elif [ -f "$HOME/.local/bin/poetry" ]; then
    POETRY_CMD="$HOME/.local/bin/poetry"
elif [ -f "$HOME/.pyenv/shims/poetry" ]; then
    POETRY_CMD="$HOME/.pyenv/shims/poetry"
elif [ -f "/usr/local/bin/poetry" ]; then
    POETRY_CMD="/usr/local/bin/poetry"
else
    echo "ERROR: poetry not found in PATH, ~/.local/bin, ~/.pyenv/shims, or /usr/local/bin" >> "$LOG_DIR/launchd.log"
    echo "Searched locations:" >> "$LOG_DIR/launchd.log"
    echo "  - PATH: $(echo $PATH)" >> "$LOG_DIR/launchd.log"
    echo "  - ~/.local/bin/poetry" >> "$LOG_DIR/launchd.log"
    echo "  - ~/.pyenv/shims/poetry" >> "$LOG_DIR/launchd.log"
    echo "  - /usr/local/bin/poetry" >> "$LOG_DIR/launchd.log"
    exit 1
fi

# Run the PID daily evaluation using Poetry
# Output goes to launchd stdout/stderr (configured in .plist)
echo "=== PID Daily Evaluation - $(date) ==="
$POETRY_CMD run pid-daily-evaluation --days-back 7
echo "=== Completed - $(date) ==="
