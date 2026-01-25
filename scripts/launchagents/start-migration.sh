#!/bin/bash
# Start LaunchAgents Migration with Automatic Orchestration
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_DIR="$HOME/Library/LaunchAgents"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "═══════════════════════════════════════════════════════════════════"
echo "🚀 LaunchAgents Migration - Démarrage Automatique"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo -e "${BLUE}Cette migration est ENTIÈREMENT AUTOMATISÉE:${NC}"
echo ""
echo "Phase 1: IMMÉDIAT    → Installation 7 nouveaux agents"
echo "Phase 2: AUTO (48h)  → Désactivation anciens agents"
echo "Phase 3: AUTO (7j)   → Archivage fichiers .plist"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo ""
read -p "Lancer la migration automatique ? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Migration annulée"
    exit 1
fi

echo ""
echo "📋 Copie et chargement agent Phase 1..."
cp "$SCRIPT_DIR/com.cyclisme.migration.10-phase1-install-now.plist" "$AGENTS_DIR/"
launchctl load "$AGENTS_DIR/com.cyclisme.migration.10-phase1-install-now.plist"

echo ""
echo -e "${GREEN}✅ Migration lancée !${NC}"
echo ""
echo "📊 Suivre la progression:"
echo ""
echo "  tail -f ~/Library/Logs/cyclisme-migration-phase1.log"
echo ""
echo "🎯 Timeline:"
echo ""
echo "  NOW      → Phase 1 s'exécute (quelques secondes)"
echo "  +48h     → Phase 2 désactive anciens agents"
echo "  +7j      → Phase 3 archive anciens .plist"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
