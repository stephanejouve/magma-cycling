#!/bin/bash
# Validate .plist files syntax using macOS plutil tool

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "Validation Syntaxe .plist (macOS plutil)"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

error_count=0
success_count=0

echo "📋 Validation des 7 nouveaux .plist..."
echo "────────────────────────────────────────────────────────────────"
echo ""

for plist in "$SCRIPT_DIR"/*.plist; do
    filename=$(basename "$plist")

    # Validate syntax
    if plutil -lint "$plist" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}  $filename"
        success_count=$((success_count + 1))

        # Additional checks
        label=$(plutil -extract Label raw "$plist" 2>/dev/null)
        if [ -n "$label" ]; then
            echo "     Label: $label"
        fi

        # Check for required keys
        if plutil -extract ProgramArguments raw "$plist" > /dev/null 2>&1; then
            echo "     ✓ ProgramArguments présent"
        else
            echo -e "     ${YELLOW}⚠${NC} ProgramArguments manquant"
        fi

        # Check schedule (StartCalendarInterval or StartInterval)
        if plutil -extract StartCalendarInterval raw "$plist" > /dev/null 2>&1; then
            echo "     ✓ StartCalendarInterval présent"
        elif plutil -extract StartInterval raw "$plist" > /dev/null 2>&1; then
            echo "     ✓ StartInterval présent"
        else
            echo -e "     ${YELLOW}⚠${NC} Pas de schedule défini"
        fi

    else
        echo -e "${RED}✗${NC}  $filename"
        error_count=$((error_count + 1))
        echo "     Erreurs:"
        plutil -lint "$plist" 2>&1 | sed 's/^/       /'
    fi

    echo ""
done

echo "═══════════════════════════════════════════════════════════════════"
echo "RÉSULTAT VALIDATION"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo -e "${GREEN}✓${NC}  Fichiers valides: $success_count"
echo -e "${RED}✗${NC}  Fichiers invalides: $error_count"
echo ""

if [ $error_count -eq 0 ]; then
    echo -e "${GREEN}✅ Tous les .plist sont valides!${NC}"
    echo ""
    echo "🎯 PROCHAINE ÉTAPE:"
    echo "   ./migrate.sh"
    echo ""
    exit 0
else
    echo -e "${RED}❌ $error_count fichiers invalides détectés${NC}"
    echo ""
    echo "⚠️  Corriger les erreurs avant de continuer"
    echo ""
    exit 1
fi
