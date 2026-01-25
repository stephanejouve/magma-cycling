#!/bin/bash
# Migration script for LaunchAgents reorganization
# New naming convention: com.cyclisme.{CATEGORY}.{SEQUENCE}-{NAME}-{SCHEDULE}

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "LaunchAgents Migration - Nouvelle Convention de Nommage"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_DIR="$HOME/Library/LaunchAgents"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "📋 Étape 1: Copier nouveaux .plist vers ~/Library/LaunchAgents"
echo "────────────────────────────────────────────────────────────────"

# Copy only the main agents (not migration agents)
for plist in "$SCRIPT_DIR"/com.cyclisme.{rept,mon,anls,flow,mnt}.*.plist; do
    cp "$plist" "$AGENTS_DIR/"
done
echo "✓ 7 fichiers .plist copiés"
echo ""

echo "📋 Étape 2: Charger nouveaux agents (en parallèle des anciens)"
echo "────────────────────────────────────────────────────────────────"

AGENTS=(
    "com.cyclisme.rept.10-daily-sync-21h30"
    "com.cyclisme.mon.10-adherence-daily-22h"
    "com.cyclisme.anls.10-pid-evaluation-daily-23h"
    "com.cyclisme.flow.10-end-of-week-sun-20h"
    "com.cyclisme.mnt.10-project-clean-daily"
    "com.cyclisme.mnt.20-sync-docs-hourly"
    "com.cyclisme.mnt.30-rsync-sites-hourly"
)

for agent in "${AGENTS[@]}"; do
    if launchctl list | grep -q "$agent"; then
        echo -e "${YELLOW}⚠${NC}  $agent déjà chargé, skip"
    else
        launchctl load "$AGENTS_DIR/$agent.plist"
        echo -e "${GREEN}✓${NC}  $agent chargé"
    fi
done

echo ""
echo "📊 Étape 3: Vérification agents actifs"
echo "────────────────────────────────────────────────────────────────"
echo ""
echo "Agents NOUVEAUX (convention moderne):"
launchctl list | grep "com.cyclisme.rept\|com.cyclisme.mon\|com.cyclisme.anls\|com.cyclisme.flow\|com.cyclisme.mnt" || echo "Aucun trouvé"
echo ""
echo "Agents ANCIENS (à désactiver après validation):"
launchctl list | grep "com.traininglogs\|com.user.sync.cyclisme" || echo "Aucun trouvé"
echo ""

echo "📋 Étape 4: Créer timestamp Phase 1"
echo "────────────────────────────────────────────────────────────────"
touch /tmp/cyclisme-migration-phase1.timestamp
echo -e "${GREEN}✓${NC}  Timestamp créé: $(date)"
echo ""

echo "📋 Étape 5: Activer agents de migration automatique"
echo "────────────────────────────────────────────────────────────────"
# Copy and load migration orchestration agents
cp "$SCRIPT_DIR/com.cyclisme.migration.20-phase2-unload-48h.plist" "$AGENTS_DIR/"
cp "$SCRIPT_DIR/com.cyclisme.migration.30-phase3-archive-7d.plist" "$AGENTS_DIR/"

launchctl load "$AGENTS_DIR/com.cyclisme.migration.20-phase2-unload-48h.plist"
echo -e "${GREEN}✓${NC}  Phase 2 agent activé (exécution dans 48h)"

launchctl load "$AGENTS_DIR/com.cyclisme.migration.30-phase3-archive-7d.plist"
echo -e "${GREEN}✓${NC}  Phase 3 agent activé (exécution dans 7j après Phase 2)"
echo ""

echo "═══════════════════════════════════════════════════════════════════"
echo "✅ Migration Phase 1 Complète - Automation Activée !"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "🤖 PHASES AUTOMATIQUES PROGRAMMÉES:"
echo ""
echo "✅ Phase 1: FAIT - 7 nouveaux agents chargés"
echo "⏳ Phase 2: AUTO dans 48h - Désactivation anciens agents"
echo "⏳ Phase 3: AUTO dans 7j après Phase 2 - Archivage .plist"
echo ""
echo "📊 SURVEILLANCE:"
echo ""
echo "1. MAINTENANT → 48H - Validation fonctionnement"
echo "   • Vérifier email 21h30 (daily-sync)"
echo "   • Vérifier adherence collecté 22h00"
echo "   • Vérifier PID evaluation 23h00 (NOUVEAU!)"
echo "   • Vérifier planning dimanche 20h00"
echo ""
echo "2. LOGS MIGRATION:"
echo "   • Phase 2: ~/Library/Logs/cyclisme-migration-phase2.log"
echo "   • Phase 3: ~/Library/Logs/cyclisme-migration-phase3.log"
echo ""
echo "3. LOGS AGENTS:"
echo "   • ~/Library/Logs/cyclisme-*.log"
echo "   • ~/data/monitoring/*.log"
echo ""
echo "🚨 ROLLBACK (si problème):"
echo "   launchctl unload ~/Library/LaunchAgents/com.cyclisme.*.plist"
echo "   (anciens agents restent actifs)"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
