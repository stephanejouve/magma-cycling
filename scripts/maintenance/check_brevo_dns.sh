#!/bin/bash
# Check Brevo DNS propagation for alliancejr.eu
# Run this script 30 min after DNS modifications

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
RESET='\033[0m'

DOMAIN="alliancejr.eu"

echo -e "\n${BOLD}${BLUE}=====================================================================${RESET}"
echo -e "${BOLD}${BLUE}         🔍 Brevo DNS Propagation Check - ${DOMAIN}                  ${RESET}"
echo -e "${BOLD}${BLUE}=====================================================================${RESET}\n"

# Track results
ALL_GOOD=true

# Function to check and display result
check_record() {
    local name=$1
    local type=$2
    local host=$3
    local expected=$4

    echo -e "${BOLD}Checking ${name}...${RESET}"
    echo -e "${BLUE}Command:${RESET} dig ${type} ${host} +short"

    result=$(dig ${type} ${host} +short 2>/dev/null | grep -v '^;' | head -1)

    if [ -z "$result" ]; then
        echo -e "${RED}✗ NOT FOUND${RESET}"
        echo -e "${YELLOW}Expected:${RESET} ${expected}"
        echo ""
        ALL_GOOD=false
        return 1
    fi

    # Clean up result (remove quotes if present)
    result_clean=$(echo "$result" | tr -d '"')
    expected_clean=$(echo "$expected" | tr -d '"')

    if [[ "$result_clean" == *"$expected_clean"* ]]; then
        echo -e "${GREEN}✓ FOUND${RESET}"
        echo -e "${GREEN}Value:${RESET} ${result}"
        echo ""
        return 0
    else
        echo -e "${YELLOW}⚠ FOUND BUT DIFFERENT${RESET}"
        echo -e "${YELLOW}Expected:${RESET} ${expected}"
        echo -e "${YELLOW}Got:${RESET} ${result}"
        echo ""
        ALL_GOOD=false
        return 1
    fi
}

# 1. Check Code Brevo
check_record "Code Brevo" "TXT" "${DOMAIN}" "brevo-code:7103aafe60a52f5a6216068a53dcf4a7"

# 2. Check DKIM 1
check_record "DKIM 1" "CNAME" "brevo1._domainkey.${DOMAIN}" "b1.alliancejr-eu.dkim.brevo.com"

# 3. Check DKIM 2
check_record "DKIM 2" "CNAME" "brevo2._domainkey.${DOMAIN}" "b2.alliancejr-eu.dkim.brevo.com"

# 4. Check DMARC
check_record "DMARC" "TXT" "_dmarc.${DOMAIN}" "v=DMARC1"

# 5. Check SPF (more complex - need to check both includes)
echo -e "${BOLD}Checking SPF (Hybrid iCloud + Brevo)...${RESET}"
echo -e "${BLUE}Command:${RESET} dig TXT ${DOMAIN} +short | grep spf"

spf_result=$(dig TXT ${DOMAIN} +short | grep spf | tr -d '"')

if [ -z "$spf_result" ]; then
    echo -e "${RED}✗ SPF NOT FOUND${RESET}"
    echo ""
    ALL_GOOD=false
else
    # Check for both includes
    has_icloud=$(echo "$spf_result" | grep -c "include:icloud.com" || true)
    has_brevo=$(echo "$spf_result" | grep -c "include:spf.brevo.com" || true)

    if [ "$has_icloud" -gt 0 ] && [ "$has_brevo" -gt 0 ]; then
        echo -e "${GREEN}✓ SPF CORRECT (iCloud + Brevo)${RESET}"
        echo -e "${GREEN}Value:${RESET} ${spf_result}"
        echo ""
    elif [ "$has_brevo" -gt 0 ]; then
        echo -e "${YELLOW}⚠ SPF HAS BREVO BUT MISSING ICLOUD${RESET}"
        echo -e "${YELLOW}Value:${RESET} ${spf_result}"
        echo ""
        ALL_GOOD=false
    elif [ "$has_icloud" -gt 0 ]; then
        echo -e "${YELLOW}⚠ SPF HAS ICLOUD BUT MISSING BREVO${RESET}"
        echo -e "${YELLOW}Value:${RESET} ${spf_result}"
        echo -e "${YELLOW}Expected:${RESET} v=spf1 include:icloud.com include:spf.brevo.com ~all"
        echo ""
        ALL_GOOD=false
    else
        echo -e "${RED}✗ SPF FOUND BUT INCORRECT${RESET}"
        echo -e "${RED}Value:${RESET} ${spf_result}"
        echo ""
        ALL_GOOD=false
    fi
fi

# Summary
echo -e "${BOLD}${BLUE}=====================================================================${RESET}"
if [ "$ALL_GOOD" = true ]; then
    echo -e "${GREEN}${BOLD}✅ ALL DNS RECORDS PROPAGATED SUCCESSFULLY!${RESET}\n"
    echo -e "${GREEN}Next steps:${RESET}"
    echo -e "  1. Go to Brevo: https://app.brevo.com"
    echo -e "  2. Settings → Senders & IP → Domains"
    echo -e "  3. Click on ${DOMAIN}"
    echo -e "  4. Click 'Check Authentication' or 'Verify'"
    echo -e "  5. Wait for status 'Verified' ✅"
    echo ""
    echo -e "${GREEN}Then test email sending:${RESET}"
    echo -e "  poetry run daily-sync --send-email --week-id S078"
else
    echo -e "${YELLOW}${BOLD}⚠️  SOME RECORDS NOT YET PROPAGATED${RESET}\n"
    echo -e "${YELLOW}This is normal - DNS propagation can take 1-4 hours.${RESET}"
    echo -e "${YELLOW}Wait another 30 minutes and run this script again:${RESET}"
    echo -e "  ./scripts/maintenance/check_brevo_dns.sh"
fi
echo -e "${BOLD}${BLUE}=====================================================================${RESET}\n"

# Exit with appropriate code
if [ "$ALL_GOOD" = true ]; then
    exit 0
else
    exit 1
fi
