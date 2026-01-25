#!/bin/bash
# Unload old LaunchAgents after validation (Phase 2)
# Run this ONLY after 48h validation of new agents

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "Désactivation Anciens LaunchAgents"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

AGENTS_DIR="$HOME/Library/LaunchAgents"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}⚠ ATTENTION:${NC} Cette opération désactive les anciens agents."
echo "Les nouveaux agents DOIVENT être validés avant de continuer."
echo ""
read -p "Avez-vous validé les nouveaux agents pendant 48h ? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo -e "${RED}✗${NC} Opération annulée"
    exit 1
fi

echo ""
echo "📋 Désactivation anciens agents..."
echo "────────────────────────────────────────────────────────────────"

OLD_AGENTS=(
    "com.traininglogs.dailysync"
    "com.cyclisme.workout_adherence"
    "com.traininglogs.endofweek"
    "com.cyclisme.project-cleaner"
    "com.cyclisme.sync-docs-icloud"
    "com.user.sync.cyclisme"
)

for agent in "${OLD_AGENTS[@]}"; do
    if launchctl list | grep -q "$agent"; then
        launchctl unload "$AGENTS_DIR/$agent.plist" 2>/dev/null || true
        echo -e "${GREEN}✓${NC}  $agent désactivé"
    else
        echo -e "${YELLOW}⚠${NC}  $agent déjà inactif"
    fi
done

echo ""
echo "📊 Vérification agents actifs"
echo "────────────────────────────────────────────────────────────────"
echo ""
echo "Agents NOUVEAUX (doivent être présents):"
launchctl list | grep "com.cyclisme.rept\|com.cyclisme.mon\|com.cyclisme.anls\|com.cyclisme.flow\|com.cyclisme.mnt"
echo ""
echo "Agents ANCIENS (ne doivent PAS être présents):"
launchctl list | grep "com.traininglogs\|com.user.sync.cyclisme" && echo -e "${RED}✗ Anciens agents encore actifs!${NC}" || echo -e "${GREEN}✓ Aucun ancien agent actif${NC}"
echo ""

echo "═══════════════════════════════════════════════════════════════════"
echo "✅ Phase 2 Complète - Anciens Agents Désactivés"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "🎯 PROCHAINE ÉTAPE:"
echo ""
echo "Attendre 7 jours puis archiver les anciens .plist:"
echo "  ./archive_old_agents.sh"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
