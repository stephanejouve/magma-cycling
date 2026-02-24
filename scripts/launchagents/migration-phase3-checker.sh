#!/bin/bash
# Check if 7 days have passed since Phase 2, then execute Phase 3
set -e

PHASE2_MARKER="/tmp/cyclisme-migration-phase2.done"
PHASE3_DONE="/tmp/cyclisme-migration-phase3.done"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# If Phase 3 already done, unload self
if [ -f "$PHASE3_DONE" ]; then
    echo "Phase 3 already completed. Unloading self..."
    launchctl unload ~/Library/LaunchAgents/com.cyclisme.migration.30-phase3-archive-7d.plist
    exit 0
fi

# If Phase 2 not done yet, wait
if [ ! -f "$PHASE2_MARKER" ]; then
    echo "Phase 2 not executed yet. Waiting..."
    exit 0
fi

# Check if 7 days (604800 seconds) have passed
PHASE2_TIME=$(stat -f %m "$PHASE2_MARKER")
CURRENT_TIME=$(date +%s)
ELAPSED=$((CURRENT_TIME - PHASE2_TIME))
DAYS=$((ELAPSED / 86400))

echo "Time since Phase 2: ${DAYS}d (need 7d)"

if [ $ELAPSED -ge 604800 ]; then
    echo "✅ 7 days elapsed! Executing Phase 3..."

    # Execute Phase 3
    echo "yes" | "$SCRIPT_DIR/phase3-archive-old-agents.sh"

    # Mark Phase 3 done
    touch "$PHASE3_DONE"

    # Unload self
    echo "Phase 3 complete. Unloading self..."
    launchctl unload ~/Library/LaunchAgents/com.cyclisme.migration.30-phase3-archive-7d.plist
else
    echo "⏳ Waiting... ${DAYS}d/7d elapsed"
fi
