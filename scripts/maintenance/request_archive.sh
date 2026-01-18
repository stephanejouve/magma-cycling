#!/bin/bash
# Request Claude Code archive creation on next project-clean run
#
# Usage:
#   ./request_archive.sh           # Request archive
#   ./request_archive.sh cancel    # Cancel request
#   ./request_archive.sh status    # Check status

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FLAG_FILE="$PROJECT_ROOT/.archive_needed"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RESET='\033[0m'

case "${1:-request}" in
    request)
        echo "TRUE" > "$FLAG_FILE"
        echo -e "${GREEN}✅ Archive requested${RESET}"
        echo -e "${BLUE}Next 'project-clean' run will create Claude Code archive${RESET}"
        echo -e "${BLUE}LaunchAgent runs daily at midnight or manually: poetry run project-clean${RESET}"
        ;;

    cancel)
        echo "FALSE" > "$FLAG_FILE"
        echo -e "${YELLOW}❌ Archive request cancelled${RESET}"
        ;;

    status)
        if [ -f "$FLAG_FILE" ]; then
            VALUE=$(cat "$FLAG_FILE" | tr -d '[:space:]' | tr '[:lower:]' '[:upper:]')
            if [ "$VALUE" = "TRUE" ]; then
                echo -e "${GREEN}📦 Archive REQUESTED (will be created on next cleanup)${RESET}"
            else
                echo -e "${BLUE}No archive requested${RESET}"
            fi
        else
            echo -e "${BLUE}No archive flag file (.archive_needed not found)${RESET}"
        fi
        ;;

    *)
        echo "Usage: $0 {request|cancel|status}"
        exit 1
        ;;
esac
