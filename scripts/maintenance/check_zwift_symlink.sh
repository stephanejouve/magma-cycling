#!/bin/bash
# Check and repair Zwift symlink to prevent iCloud pollution
#
# Usage:
#   ./check_zwift_symlink.sh           # Check only
#   ./check_zwift_symlink.sh --repair  # Repair if broken
#
# This script ensures ~/Documents/Zwift remains a symlink to ~/Nextcloud/Zwift

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
RESET='\033[0m'

DOCS_ZWIFT="$HOME/Documents/Zwift"
NEXTCLOUD_ZWIFT="$HOME/Nextcloud/Zwift"
REPAIR_MODE=false

# Parse arguments
if [[ "$1" == "--repair" ]]; then
    REPAIR_MODE=true
fi

echo -e "\n${BLUE}====================================================================${RESET}"
echo -e "${BLUE}           🚴 Zwift Symlink Check                                     ${RESET}"
echo -e "${BLUE}====================================================================${RESET}\n"

# Check Nextcloud/Zwift exists
if [[ ! -d "$NEXTCLOUD_ZWIFT" ]]; then
    echo -e "${RED}❌ Error: $NEXTCLOUD_ZWIFT does not exist${RESET}"
    echo -e "${YELLOW}Zwift data folder is missing from Nextcloud${RESET}"
    exit 1
fi

echo -e "${GREEN}✅ Nextcloud/Zwift exists${RESET}"
echo -e "   Location: $NEXTCLOUD_ZWIFT"
echo -e "   Size: $(du -sh "$NEXTCLOUD_ZWIFT" | cut -f1)"
echo ""

# Check Documents/Zwift status
if [[ ! -e "$DOCS_ZWIFT" ]]; then
    # Symlink doesn't exist
    echo -e "${YELLOW}⚠️  Warning: $DOCS_ZWIFT does not exist${RESET}"

    if [[ "$REPAIR_MODE" == true ]]; then
        echo -e "${BLUE}Creating symlink...${RESET}"
        ln -s "$NEXTCLOUD_ZWIFT" "$DOCS_ZWIFT"
        echo -e "${GREEN}✅ Symlink created successfully${RESET}"
    else
        echo -e "${YELLOW}Run with --repair to create symlink${RESET}"
        exit 1
    fi

elif [[ -L "$DOCS_ZWIFT" ]]; then
    # It's a symlink - check if it points to correct location
    TARGET=$(readlink "$DOCS_ZWIFT")

    if [[ "$TARGET" == "$NEXTCLOUD_ZWIFT" ]]; then
        echo -e "${GREEN}✅ Symlink exists and points to correct location${RESET}"
        echo -e "   $DOCS_ZWIFT → $TARGET"

        # Check if target is accessible
        if [[ -d "$TARGET" ]]; then
            echo -e "${GREEN}✅ Target is accessible${RESET}"
        else
            echo -e "${RED}❌ Target is not accessible (broken symlink)${RESET}"

            if [[ "$REPAIR_MODE" == true ]]; then
                echo -e "${BLUE}Recreating symlink...${RESET}"
                rm "$DOCS_ZWIFT"
                ln -s "$NEXTCLOUD_ZWIFT" "$DOCS_ZWIFT"
                echo -e "${GREEN}✅ Symlink recreated${RESET}"
            else
                echo -e "${YELLOW}Run with --repair to fix${RESET}"
                exit 1
            fi
        fi
    else
        echo -e "${YELLOW}⚠️  Warning: Symlink points to wrong location${RESET}"
        echo -e "   Current: $TARGET"
        echo -e "   Expected: $NEXTCLOUD_ZWIFT"

        if [[ "$REPAIR_MODE" == true ]]; then
            echo -e "${BLUE}Fixing symlink...${RESET}"
            rm "$DOCS_ZWIFT"
            ln -s "$NEXTCLOUD_ZWIFT" "$DOCS_ZWIFT"
            echo -e "${GREEN}✅ Symlink fixed${RESET}"
        else
            echo -e "${YELLOW}Run with --repair to fix${RESET}"
            exit 1
        fi
    fi

elif [[ -d "$DOCS_ZWIFT" ]]; then
    # It's a real directory (problem!)
    echo -e "${RED}❌ ERROR: $DOCS_ZWIFT is a real directory (not a symlink)${RESET}"
    echo -e "${YELLOW}This will cause Zwift data to be synchronized to iCloud${RESET}"

    FILE_COUNT=$(find "$DOCS_ZWIFT" -type f | wc -l | tr -d ' ')
    TOTAL_SIZE=$(du -sh "$DOCS_ZWIFT" | cut -f1)

    echo -e "   Files: $FILE_COUNT"
    echo -e "   Size: $TOTAL_SIZE"

    if [[ "$REPAIR_MODE" == true ]]; then
        echo -e "${BLUE}Migrating data and creating symlink...${RESET}"

        # Backup to Nextcloud
        echo -e "${BLUE}Syncing data to Nextcloud...${RESET}"
        rsync -av "$DOCS_ZWIFT/" "$NEXTCLOUD_ZWIFT/"

        echo -e "${BLUE}Removing directory...${RESET}"
        rm -rf "$DOCS_ZWIFT"

        echo -e "${BLUE}Creating symlink...${RESET}"
        ln -s "$NEXTCLOUD_ZWIFT" "$DOCS_ZWIFT"

        echo -e "${GREEN}✅ Migration complete${RESET}"
        echo -e "   Data preserved in: $NEXTCLOUD_ZWIFT"
        echo -e "   Symlink created: $DOCS_ZWIFT → $NEXTCLOUD_ZWIFT"
    else
        echo -e "${YELLOW}Run with --repair to migrate data and create symlink${RESET}"
        exit 1
    fi

else
    echo -e "${RED}❌ Unknown file type at $DOCS_ZWIFT${RESET}"
    exit 1
fi

# Final verification
echo ""
echo -e "${BLUE}====================================================================${RESET}"
echo -e "${BLUE}Final Status:${RESET}"
ls -lh "$DOCS_ZWIFT"

# Check iCloud pollution
ICLOUD_ZWIFT_COUNT=$(find "$HOME/Library/Mobile Documents/com~apple~CloudDocs/" -name "*Zwift*" 2>/dev/null | wc -l | tr -d ' ')

if [[ "$ICLOUD_ZWIFT_COUNT" -eq 0 ]]; then
    echo -e "${GREEN}✅ iCloud Drive is clean (no Zwift files)${RESET}"
else
    echo -e "${YELLOW}⚠️  Warning: Found $ICLOUD_ZWIFT_COUNT Zwift file(s) in iCloud${RESET}"
fi

echo ""
echo -e "${GREEN}${BOLD}✅ Check complete!${RESET}"
