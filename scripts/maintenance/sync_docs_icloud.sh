#!/bin/bash
# Sync project documentation to iCloud (~/Documents) for easy MOA sharing from iPhone
#
# Usage:
#   ./sync_docs_icloud.sh          # Sync to iCloud
#   ./sync_docs_icloud.sh --dry-run  # Preview what would be synced
#   ./sync_docs_icloud.sh --stats    # Show sync statistics
#
# Syncs:
#   - Key docs (ROADMAP, CHANGELOG, README)
#   - Guides (developer references)
#   - Sprints (including MOA deliveries)
#   - Recent sessions (last 10)
#   - Architecture docs
#
# Excludes:
#   - Archives (historical, too large)
#   - Logs (technical)
#   - Audits (technical)
#   - Prompts (technical)

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
BOLD='\033[1m'
RESET='\033[0m'

# Directories
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="$PROJECT_ROOT/project-docs"
TARGET_DIR="$HOME/Documents/cyclisme-training-logs-docs"

# Parse arguments
DRY_RUN=""
STATS=""
VERBOSE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        --stats)
            STATS="--stats"
            shift
            ;;
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${RESET}"
            exit 1
            ;;
    esac
done

# Print header
echo -e "\n${BOLD}${BLUE}=====================================================================${RESET}"
echo -e "${BOLD}${BLUE}         📱 iCloud Docs Sync - MOA Documentation                     ${RESET}"
echo -e "${BOLD}${BLUE}=====================================================================${RESET}\n"

if [[ -n "$DRY_RUN" ]]; then
    echo -e "${YELLOW}${BOLD}DRY RUN MODE - No changes will be made${RESET}\n"
fi

echo -e "${BLUE}Source:${RESET} $SOURCE_DIR"
echo -e "${BLUE}Target:${RESET} $TARGET_DIR"
echo ""

# Create target directory if it doesn't exist
if [[ ! -d "$TARGET_DIR" ]]; then
    if [[ -z "$DRY_RUN" ]]; then
        mkdir -p "$TARGET_DIR"
        echo -e "${GREEN}✅ Created target directory: $TARGET_DIR${RESET}"
    else
        echo -e "${YELLOW}Would create: $TARGET_DIR${RESET}"
    fi
fi

# Rsync options
RSYNC_OPTS=(
    -a                          # Archive mode (recursive, preserve permissions, times, etc.)
    --update                    # Skip files that are newer in target
    --ignore-errors             # Continue on errors (iCloud sync conflicts)
    $VERBOSE                    # Verbose if requested
    $DRY_RUN                    # Dry run if requested
    $STATS                      # Stats if requested
)

# Files/directories to include (explicit)
INCLUDE_PATTERNS=(
    # Root files
    --include='ROADMAP.md'
    --include='CHANGELOG.md'
    --include='README.md'

    # Directories to include
    --include='guides/'
    --include='guides/**'
    --include='sprints/'
    --include='sprints/**'
    --include='sessions/'
    --include='sessions/**'
    --include='architecture/'
    --include='architecture/**'
    --include='workflows/'
    --include='workflows/**'
)

# Files/directories to exclude
EXCLUDE_PATTERNS=(
    # Exclude technical/historical content
    --exclude='archives/'
    --exclude='logs/'
    --exclude='audits/'
    --exclude='prompts/'

    # Exclude system files
    --exclude='.DS_Store'
    --exclude='*.pyc'
    --exclude='__pycache__'
    --exclude='.gitkeep'

    # Exclude very large files
    --exclude='*.jsonl'
    --exclude='*.tar.gz'
    --exclude='*.zip'
    --exclude='*.json'
)

# Build complete rsync command
RSYNC_CMD=(
    rsync
    "${RSYNC_OPTS[@]}"
    "${INCLUDE_PATTERNS[@]}"
    "${EXCLUDE_PATTERNS[@]}"
    --exclude='*'              # Exclude everything not explicitly included
    "$SOURCE_DIR/"             # Trailing slash = contents only
    "$TARGET_DIR/"
)

# Execute rsync
echo -e "${BLUE}Syncing documentation...${RESET}\n"

if "${RSYNC_CMD[@]}"; then
    if [[ -z "$DRY_RUN" ]]; then
        echo ""
        echo -e "${GREEN}${BOLD}✅ Sync completed successfully!${RESET}"
        echo -e "${BLUE}Documents available at: $TARGET_DIR${RESET}"
        echo -e "${BLUE}Access from iPhone: Files app → iCloud Drive → Documents → cyclisme-training-logs-docs${RESET}"
    else
        echo ""
        echo -e "${YELLOW}${BOLD}Dry run complete - no changes made${RESET}"
        echo -e "${YELLOW}Run without --dry-run to execute sync${RESET}"
    fi
else
    echo ""
    echo -e "${RED}${BOLD}❌ Sync failed${RESET}"
    exit 1
fi

# Show quick summary if not in stats mode
if [[ -z "$STATS" ]] && [[ -z "$DRY_RUN" ]]; then
    echo ""
    echo -e "${BOLD}Quick stats:${RESET}"
    echo -e "  Total size: $(du -sh "$TARGET_DIR" | cut -f1)"
    echo -e "  Files: $(find "$TARGET_DIR" -type f | wc -l | tr -d ' ')"
    echo -e "  Directories: $(find "$TARGET_DIR" -type d | wc -l | tr -d ' ')"
fi

echo ""
