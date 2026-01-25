#!/bin/bash
# List all cyclisme LaunchAgents with status and metadata

echo "═══════════════════════════════════════════════════════════════════"
echo "CYCLISME TRAINING LOGS - LaunchAgents Status"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Generated: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

check_agent_status() {
    local agent=$1
    if launchctl list | grep -q "$agent"; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi
}

echo "═══════════════════════════════════════════════════════════════════"
echo -e "${BLUE}REPORTING${NC} (Email/Rapports)"
echo "───────────────────────────────────────────────────────────────────"
agent="com.cyclisme.rept.10-daily-sync-21h30"
status=$(check_agent_status "$agent")
echo -e "$status  $agent"
echo "     📧 Command: poetry run daily-sync --send-email --ai-analysis"
echo "     ⏰ Schedule: Daily 21:30"
echo "     📊 Output: Email quotidien + analyses AI"
echo ""

echo "═══════════════════════════════════════════════════════════════════"
echo -e "${BLUE}MONITORING${NC} (Collecte Données)"
echo "───────────────────────────────────────────────────────────────────"
agent="com.cyclisme.mon.10-adherence-daily-22h"
status=$(check_agent_status "$agent")
echo -e "$status  $agent"
echo "     📊 Command: run_adherence_check.sh"
echo "     ⏰ Schedule: Daily 22:00"
echo "     📊 Output: ~/data/monitoring/workout_adherence.jsonl"
echo ""

echo "═══════════════════════════════════════════════════════════════════"
echo -e "${BLUE}ANALYSIS${NC} (Intelligence AI)"
echo "───────────────────────────────────────────────────────────────────"
agent="com.cyclisme.anls.10-pid-evaluation-daily-23h"
status=$(check_agent_status "$agent")
echo -e "$status  $agent"
echo "     🧠 Command: pid-daily-evaluation --days-back 7"
echo "     ⏰ Schedule: Daily 23:00"
echo "     📊 Output: ~/data/intelligence.json"
echo ""

echo "═══════════════════════════════════════════════════════════════════"
echo -e "${BLUE}WORKFLOW${NC} (Processus Complets)"
echo "───────────────────────────────────────────────────────────────────"
agent="com.cyclisme.flow.10-end-of-week-sun-20h"
status=$(check_agent_status "$agent")
echo -e "$status  $agent"
echo "     🔄 Command: end-of-week --auto-calculate --provider claude_api"
echo "     ⏰ Schedule: Sunday 20:00"
echo "     📊 Output: logs/planning/SXXX_planning.json"
echo ""

echo "═══════════════════════════════════════════════════════════════════"
echo -e "${BLUE}MAINTENANCE${NC} (Nettoyage/Sync)"
echo "───────────────────────────────────────────────────────────────────"
agent="com.cyclisme.mnt.10-project-clean-daily"
status=$(check_agent_status "$agent")
echo -e "$status  $agent"
echo "     🧹 Command: poetry run project-clean"
echo "     ⏰ Schedule: Daily (86400s)"
echo ""

agent="com.cyclisme.mnt.20-sync-docs-hourly"
status=$(check_agent_status "$agent")
echo -e "$status  $agent"
echo "     📁 Command: sync_docs_icloud.sh"
echo "     ⏰ Schedule: Hourly (3600s)"
echo ""

agent="com.cyclisme.mnt.30-rsync-sites-hourly"
status=$(check_agent_status "$agent")
echo -e "$status  $agent"
echo "     🌐 Command: rsync docs → Sites/"
echo "     ⏰ Schedule: Hourly (3600s)"
echo ""

echo "═══════════════════════════════════════════════════════════════════"
echo -e "${YELLOW}ANCIENS AGENTS${NC} (À Désactiver)"
echo "───────────────────────────────────────────────────────────────────"

OLD_AGENTS=(
    "com.traininglogs.dailysync"
    "com.traininglogs.endofweek"
    "com.cyclisme.workout_adherence"
    "com.user.sync.cyclisme"
)

found_old=false
for agent in "${OLD_AGENTS[@]}"; do
    if launchctl list | grep -q "$agent"; then
        echo -e "${YELLOW}⚠${NC}  $agent (ancien - à migrer)"
        found_old=true
    fi
done

if [ "$found_old" = false ]; then
    echo -e "${GREEN}✓${NC}  Aucun ancien agent actif"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "CHRONOLOGIE QUOTIDIENNE"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "  21:30 → rept.10-daily-sync      (Email rapport + analyses AI)"
echo "  22:00 → mon.10-adherence        (Collecte adherence metrics)"
echo "  23:00 → anls.10-pid-evaluation  (Intelligence 7 jours)"
echo ""
echo "HEBDOMADAIRE"
echo "───────────────────────────────────────────────────────────────────"
echo ""
echo "  Sun 20:00 → flow.10-end-of-week (Planning semaine suivante)"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
