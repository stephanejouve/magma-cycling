#!/bin/bash
# Setup cron job for workout adherence monitoring
#
# Usage:
#   bash scripts/monitoring/setup_cron.sh
#
# This script installs a cron job that runs daily at 22:00 to check
# if planned workouts were completed.

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=========================================="
echo "🔧 Setting up Workout Adherence Monitoring"
echo "=========================================="
echo ""

# Check if project exists
if [ ! -f "$PROJECT_ROOT/pyproject.toml" ]; then
    echo "❌ Error: Could not find project root (pyproject.toml)"
    exit 1
fi

echo "📍 Project root: $PROJECT_ROOT"
echo ""

# Get Python path from Poetry
PYTHON_PATH=$(cd "$PROJECT_ROOT" && poetry run which python)
echo "🐍 Python: $PYTHON_PATH"
echo ""

# Create cron command
CRON_COMMAND="0 22 * * * cd $PROJECT_ROOT && $PYTHON_PATH scripts/monitoring/check_workout_adherence.py >> ~/data/monitoring/cron.log 2>&1"

echo "📝 Cron job to be installed:"
echo "$CRON_COMMAND"
echo ""

# Check if cron job already exists
EXISTING_CRON=$(crontab -l 2>/dev/null | grep "check_workout_adherence.py" || true)

if [ -n "$EXISTING_CRON" ]; then
    echo "⚠️  Cron job already exists:"
    echo "$EXISTING_CRON"
    echo ""
    read -p "Do you want to replace it? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Installation cancelled"
        exit 1
    fi

    # Remove existing cron job
    crontab -l 2>/dev/null | grep -v "check_workout_adherence.py" | crontab -
    echo "✅ Removed existing cron job"
fi

# Install cron job
(crontab -l 2>/dev/null; echo "$CRON_COMMAND") | crontab -

echo ""
echo "✅ Cron job installed successfully!"
echo ""
echo "📋 Schedule:"
echo "   - Runs daily at 22:00 (10:00 PM)"
echo "   - Checks if today's workouts were completed"
echo "   - Logs results to ~/data/monitoring/workout_adherence.jsonl"
echo "   - Sends notifications if workouts were skipped"
echo ""
echo "🔍 To verify installation:"
echo "   crontab -l | grep check_workout_adherence"
echo ""
echo "📝 To view logs:"
echo "   tail -f ~/data/monitoring/cron.log"
echo ""
echo "🧪 To test manually:"
echo "   cd $PROJECT_ROOT"
echo "   poetry run python scripts/monitoring/check_workout_adherence.py"
echo ""
echo "🗑️  To remove cron job:"
echo "   bash scripts/monitoring/remove_cron.sh"
echo ""
