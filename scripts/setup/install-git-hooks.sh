#!/bin/bash
# Install git hooks for cyclisme-training-logs
# Run this after cloning or to update hooks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOKS_DIR="$PROJECT_ROOT/.git/hooks"

echo "🔧 Installing git hooks for cyclisme-training-logs..."
echo ""

# Create post-merge hook
cat > "$HOOKS_DIR/post-merge" << 'EOF'
#!/bin/bash
# Post-merge hook: Reload LaunchAgents after code update
# Prevents Python cache issues when daily-sync runs with outdated code

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo -e "${YELLOW}🔄 Post-merge hook: Checking if LaunchAgents need reload...${NC}"

# Check if any Python files were changed in this merge
CHANGED_PY_FILES=$(git diff-tree -r --name-only --no-commit-id ORIG_HEAD HEAD | grep '\.py$')

if [ -z "$CHANGED_PY_FILES" ]; then
    echo -e "${GREEN}✅ No Python files changed, LaunchAgents OK${NC}"
    exit 0
fi

echo -e "${YELLOW}📝 Python files changed:${NC}"
echo "$CHANGED_PY_FILES" | while read file; do
    echo "   - $file"
done

# Reload LaunchAgents that depend on this code
AGENTS=(
    "com.cyclisme.rept.10-daily-sync-21h30"
    "com.cyclisme.anls.10-pid-evaluation-daily-23h"
    "com.cyclisme.mon.10-adherence-daily-22h"
)

echo ""
echo -e "${YELLOW}🔄 Reloading LaunchAgents...${NC}"

for agent in "${AGENTS[@]}"; do
    PLIST="$HOME/Library/LaunchAgents/${agent}.plist"

    if [ -f "$PLIST" ]; then
        echo -e "   🔄 Reloading ${agent}..."
        launchctl unload "$PLIST" 2>/dev/null
        launchctl load "$PLIST" 2>/dev/null

        if [ $? -eq 0 ]; then
            echo -e "   ${GREEN}✅ ${agent} reloaded${NC}"
        else
            echo -e "   ${YELLOW}⚠️  ${agent} reload warning (may not be loaded)${NC}"
        fi
    fi
done

echo ""
echo -e "${GREEN}✅ LaunchAgent reload complete - Python cache cleared${NC}"
echo ""

exit 0
EOF

chmod +x "$HOOKS_DIR/post-merge"

echo "✅ Git hooks installed:"
echo "   - post-merge (reload LaunchAgents after pull/merge)"
echo ""
echo "🎯 Hooks will now automatically reload LaunchAgents when Python code changes"
echo ""
