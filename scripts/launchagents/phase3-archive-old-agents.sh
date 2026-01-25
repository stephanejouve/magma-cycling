#!/bin/bash
# Archive old LaunchAgents .plist files (Phase 3)
# Run this 7 days after unload_old_agents.sh

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "Archivage Anciens LaunchAgents"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

AGENTS_DIR="$HOME/Library/LaunchAgents"
ARCHIVE_DIR="$AGENTS_DIR/.archived-$(date +%Y%m%d)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}⚠ ATTENTION:${NC} Cette opération archive définitivement les anciens .plist"
echo "Assurez-vous que les nouveaux agents fonctionnent depuis 7+ jours."
echo ""
read -p "Confirmer archivage ? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Opération annulée"
    exit 1
fi

echo ""
echo "📋 Création répertoire archive..."
mkdir -p "$ARCHIVE_DIR"
echo -e "${GREEN}✓${NC}  $ARCHIVE_DIR créé"
echo ""

echo "📋 Déplacement anciens .plist..."
echo "────────────────────────────────────────────────────────────────"

OLD_PLIST=(
    "com.traininglogs.dailysync.plist"
    "com.cyclisme.workout_adherence.plist"
    "com.traininglogs.endofweek.plist"
    "com.cyclisme.project-cleaner.plist"
    "com.cyclisme.sync-docs-icloud.plist"
    "com.user.sync.cyclisme.plist"
)

for plist in "${OLD_PLIST[@]}"; do
    if [ -f "$AGENTS_DIR/$plist" ]; then
        mv "$AGENTS_DIR/$plist" "$ARCHIVE_DIR/"
        echo -e "${GREEN}✓${NC}  $plist archivé"
    else
        echo -e "${YELLOW}⚠${NC}  $plist déjà absent"
    fi
done

echo ""
echo "📊 Listing final ~/Library/LaunchAgents"
echo "────────────────────────────────────────────────────────────────"
ls -1 "$AGENTS_DIR" | grep cyclisme || echo "Aucun agent cyclisme trouvé"
echo ""

echo "═══════════════════════════════════════════════════════════════════"
echo "✅ Migration Complète!"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "📁 Anciens .plist archivés dans:"
echo "   $ARCHIVE_DIR"
echo ""
echo "🎯 CONVENTION FINALE:"
echo "   com.cyclisme.{CATEGORY}.{SEQUENCE}-{NAME}-{SCHEDULE}"
echo ""
echo "📊 Agents actifs:"
launchctl list | grep "com.cyclisme" | awk '{print "   • " $3}'
echo ""
echo "═══════════════════════════════════════════════════════════════════"
