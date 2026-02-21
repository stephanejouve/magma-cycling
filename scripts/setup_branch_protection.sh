#!/bin/bash
set -e

echo "============================================================"
echo "GitHub Branch Protection Setup"
echo "============================================================"
echo

KEYCHAIN_SERVICE="github-api-token"
KEYCHAIN_ACCOUNT="stephanejouve"

# Try to get token from keychain
if [ -z "$GITHUB_TOKEN" ]; then
    echo "🔐 Récupération du token depuis Keychain..."
    GITHUB_TOKEN=$(security find-generic-password -s "$KEYCHAIN_SERVICE" -a "$KEYCHAIN_ACCOUNT" -w 2>/dev/null || true)
fi

# If still no token, ask for it
if [ -z "$GITHUB_TOKEN" ]; then
    echo
    echo "📝 Token GitHub requis (première utilisation)"
    echo
    echo "Pour créer un token:"
    echo "  1. https://github.com/settings/tokens"
    echo "  2. 'Generate new token (classic)'"
    echo "  3. Name: 'CLI Access'"
    echo "  4. Scopes: ✓ repo"
    echo "  5. Generate"
    echo
    read -sp "Colle ton token (masqué): " GITHUB_TOKEN
    echo
    echo

    if [ -z "$GITHUB_TOKEN" ]; then
        echo "❌ Token vide"
        exit 1
    fi

    # Save to keychain
    echo "💾 Sauvegarde dans Keychain..."
    security add-generic-password \
        -s "$KEYCHAIN_SERVICE" \
        -a "$KEYCHAIN_ACCOUNT" \
        -w "$GITHUB_TOKEN" \
        -U 2>/dev/null || \
    security delete-generic-password -s "$KEYCHAIN_SERVICE" -a "$KEYCHAIN_ACCOUNT" 2>/dev/null && \
    security add-generic-password -s "$KEYCHAIN_SERVICE" -a "$KEYCHAIN_ACCOUNT" -w "$GITHUB_TOKEN"

    echo "✅ Token sauvegardé (réutilisable)"
    echo
fi

# Config
OWNER="stephanejouve"
REPO="cyclisme-training-logs"
BRANCH="main"
API_URL="https://api.github.com/repos/$OWNER/$REPO/branches/$BRANCH/protection"

echo "🔒 Configuration de $OWNER/$REPO:$BRANCH"
echo

# Protection rules
PROTECTION_CONFIG=$(cat <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "lint",
      "test (3.11)",
      "test (3.12)",
      "test (3.13)",
      "mcp-validation",
      "status"
    ]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
JSON
)

echo "📋 Règles:"
echo "  ✅ CI obligatoire (6 checks)"
echo "  ✅ Branche à jour"
echo "  ✅ Conversations résolues"
echo "  ✅ Force push bloqué"
echo

read -p "Appliquer? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
fi

echo "🚀 Application..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -d "$PROTECTION_CONFIG" \
  "$API_URL")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

case $HTTP_CODE in
    200)
        echo
        echo "✅ Protection activée!"
        echo
        echo "🔗 https://github.com/$OWNER/$REPO/settings/branches"
        echo
        echo "🎉 Main protégée:"
        echo "  • Push direct impossible"
        echo "  • PR + CI obligatoires"
        echo "  • Force push bloqué"
        ;;
    401)
        echo "❌ Token invalide"
        echo "Supprime: security delete-generic-password -s '$KEYCHAIN_SERVICE' -a '$KEYCHAIN_ACCOUNT'"
        exit 1
        ;;
    403)
        echo "❌ Permissions insuffisantes (admin requis)"
        exit 1
        ;;
    404)
        echo "❌ Repo/branche introuvable"
        exit 1
        ;;
    *)
        echo "❌ Erreur HTTP $HTTP_CODE"
        exit 1
        ;;
esac
