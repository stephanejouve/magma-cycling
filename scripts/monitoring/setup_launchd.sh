#!/bin/bash
# Setup launchd job for workout adherence monitoring (macOS native)
#
# Usage:
#   bash scripts/monitoring/setup_launchd.sh
#
# This script installs a launchd job that runs daily at 22:00 to check
# if planned workouts were completed. Uses macOS native launchd (recommended
# over deprecated cron).

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLIST_NAME="com.cyclisme.workout_adherence.plist"
PLIST_SOURCE="$SCRIPT_DIR/$PLIST_NAME"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"
WRAPPER_SCRIPT="$SCRIPT_DIR/run_adherence_check.sh"

echo "=========================================="
echo "🔧 Setting up Workout Adherence Monitoring (launchd)"
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

# Get Poetry path
POETRY_PATH=$(which poetry)
echo "📦 Poetry: $POETRY_PATH"
echo ""

# Create LaunchAgents directory if doesn't exist
mkdir -p "$HOME/Library/LaunchAgents"

# Check if .plist source exists
if [ ! -f "$PLIST_SOURCE" ]; then
    echo "❌ Error: Could not find $PLIST_SOURCE"
    exit 1
fi

# Update .plist with actual paths
echo "📝 Generating launchd configuration..."
TEMP_PLIST=$(mktemp)

# Replace placeholder paths in .plist
# Note: Wrapper script (run_adherence_check.sh) is self-configuring
sed -e "s|/Users/stephanejouve/cyclisme-training-logs/scripts/monitoring/run_adherence_check.sh|$WRAPPER_SCRIPT|g" \
    -e "s|/Users/stephanejouve/cyclisme-training-logs|$PROJECT_ROOT|g" \
    -e "s|/Users/stephanejouve|$HOME|g" \
    "$PLIST_SOURCE" > "$TEMP_PLIST"

echo "✅ Configuration generated"
echo ""

# Check if job already loaded
if launchctl list | grep -q "com.cyclisme.workout_adherence"; then
    echo "⚠️  launchd job already loaded"
    echo ""
    read -p "Do you want to reload it? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Installation cancelled"
        rm "$TEMP_PLIST"
        exit 1
    fi

    # Unload existing job
    echo "🔄 Unloading existing job..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    echo "✅ Unloaded"
fi

# Copy .plist to LaunchAgents
echo "📋 Installing launchd configuration..."
cp "$TEMP_PLIST" "$PLIST_DEST"
rm "$TEMP_PLIST"

# Set correct permissions
chmod 644 "$PLIST_DEST"

# Load the job
echo "🚀 Loading launchd job..."
launchctl load "$PLIST_DEST"

# Verify it's loaded
if launchctl list | grep -q "com.cyclisme.workout_adherence"; then
    echo "✅ launchd job loaded successfully!"
else
    echo "❌ Error: Job not loaded"
    exit 1
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Schedule:"
echo "   - Runs daily at 22:00 (10:00 PM)"
echo "   - Checks if today's workouts were completed"
echo "   - Logs results to ~/data/monitoring/workout_adherence.jsonl"
echo "   - Sends notifications if workouts were skipped"
echo ""
echo "📝 Logs:"
echo "   - Main output: ~/data/monitoring/launchd.log"
echo "   - Stdout: ~/data/monitoring/launchd.stdout.log"
echo "   - Stderr: ~/data/monitoring/launchd.stderr.log"
echo ""
echo "🔍 To verify installation:"
echo "   launchctl list | grep workout_adherence"
echo ""
echo "📊 To check job status:"
echo "   launchctl print gui/\$(id -u)/com.cyclisme.workout_adherence"
echo ""
echo "🧪 To test manually (runs immediately):"
echo "   launchctl start com.cyclisme.workout_adherence"
echo ""
echo "📝 To view logs:"
echo "   tail -f ~/data/monitoring/launchd.log"
echo ""
echo "🗑️  To remove job:"
echo "   bash scripts/monitoring/remove_launchd.sh"
echo ""
echo "ℹ️  Note: launchd is macOS native (recommended over cron)"
echo ""
