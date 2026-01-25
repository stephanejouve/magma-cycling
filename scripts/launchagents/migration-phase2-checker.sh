#!/bin/bash
# Check if 48h have passed since Phase 1, then execute Phase 2
set -e

PHASE1_MARKER="/tmp/cyclisme-migration-phase1.timestamp"
PHASE2_DONE="/tmp/cyclisme-migration-phase2.done"
SCRIPT_DIR="/Users/stephanejouve/cyclisme-training-logs/scripts/launchagents"

# If Phase 2 already done, unload self
if [ -f "$PHASE2_DONE" ]; then
    echo "Phase 2 already completed. Unloading self..."
    launchctl unload ~/Library/LaunchAgents/com.cyclisme.migration.20-phase2-unload-48h.plist
    exit 0
fi

# If Phase 1 not done yet, wait
if [ ! -f "$PHASE1_MARKER" ]; then
    echo "Phase 1 not executed yet. Waiting..."
    exit 0
fi

# Check if 48h (172800 seconds) have passed
PHASE1_TIME=$(stat -f %m "$PHASE1_MARKER")
CURRENT_TIME=$(date +%s)
ELAPSED=$((CURRENT_TIME - PHASE1_TIME))
HOURS=$((ELAPSED / 3600))

echo "Time since Phase 1: ${HOURS}h (need 48h)"

if [ $ELAPSED -ge 172800 ]; then
    echo "✅ 48h elapsed! Executing Phase 2..."

    # Execute Phase 2
    "$SCRIPT_DIR/phase2-unload-old-agents.sh"

    # Mark Phase 2 done
    touch "$PHASE2_DONE"

    # Unload self
    echo "Phase 2 complete. Unloading self..."
    launchctl unload ~/Library/LaunchAgents/com.cyclisme.migration.20-phase2-unload-48h.plist
else
    echo "⏳ Waiting... ${HOURS}h/48h elapsed"
fi
