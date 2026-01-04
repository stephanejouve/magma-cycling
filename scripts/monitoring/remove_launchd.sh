#!/bin/bash
# Remove launchd job for workout adherence monitoring
#
# Usage:
#   bash scripts/monitoring/remove_launchd.sh

set -e

PLIST_NAME="com.cyclisme.workout_adherence.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "=========================================="
echo "🗑️  Removing Workout Adherence Monitoring (launchd)"
echo "=========================================="
echo ""

# Check if job is loaded
if ! launchctl list | grep -q "com.cyclisme.workout_adherence"; then
    echo "ℹ️  No launchd job found for workout adherence monitoring"

    # Check if .plist file exists
    if [ -f "$PLIST_DEST" ]; then
        echo "⚠️  Found .plist file but job not loaded"
        echo "📝 File: $PLIST_DEST"
        echo ""
        read -p "Do you want to remove the .plist file? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm "$PLIST_DEST"
            echo "✅ .plist file removed"
        else
            echo "❌ Removal cancelled"
        fi
    fi
    exit 0
fi

echo "📝 Found launchd job: com.cyclisme.workout_adherence"
echo ""

# Show job info
echo "📊 Job status:"
launchctl list | grep "com.cyclisme.workout_adherence" || echo "   (not in list)"
echo ""

read -p "Do you want to remove it? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Removal cancelled"
    exit 1
fi

# Unload job
echo "🔄 Unloading launchd job..."
launchctl unload "$PLIST_DEST" 2>/dev/null || {
    echo "⚠️  Warning: Could not unload job (may not be loaded)"
}

# Remove .plist file
if [ -f "$PLIST_DEST" ]; then
    echo "🗑️  Removing .plist file..."
    rm "$PLIST_DEST"
    echo "✅ .plist file removed"
else
    echo "⚠️  .plist file not found: $PLIST_DEST"
fi

# Verify removal
if launchctl list | grep -q "com.cyclisme.workout_adherence"; then
    echo ""
    echo "⚠️  Warning: Job still appears in launchctl list"
    echo "   This may be a launchd cache issue"
    echo "   The job will not run and will be cleared on next login"
else
    echo ""
    echo "✅ launchd job removed successfully!"
fi

echo ""
echo "ℹ️  Note: Log files in ~/data/monitoring/ were not deleted"
echo "   To remove logs:"
echo "   rm ~/data/monitoring/launchd*.log"
echo "   rm ~/data/monitoring/workout_adherence.jsonl"
echo ""
