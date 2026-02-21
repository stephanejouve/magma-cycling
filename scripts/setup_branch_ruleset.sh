#!/bin/bash
set -e

echo "============================================================"
echo "GitHub Branch Ruleset Setup (Free for private repos)"
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
API_URL="https://api.github.com/repos/$OWNER/$REPO/rulesets"

echo "🔒 Configuration du ruleset pour $OWNER/$REPO:main"
echo

# Ruleset configuration
RULESET_CONFIG=$(cat <<'JSON'
{
  "name": "Protect main branch",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [],
  "conditions": {
    "ref_name": {
      "include": ["refs/heads/main"],
      "exclude": []
    }
  },
  "rules": [
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [
          {
            "context": "lint",
            "integration_id": null
          },
          {
            "context": "test (3.11)",
            "integration_id": null
          },
          {
            "context": "test (3.12)",
            "integration_id": null
          },
          {
            "context": "test (3.13)",
            "integration_id": null
          },
          {
            "context": "mcp-validation",
            "integration_id": null
          },
          {
            "context": "status",
            "integration_id": null
          }
        ]
      }
    },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": true
      }
    },
    {
      "type": "non_fast_forward"
    },
    {
      "type": "deletion"
    }
  ]
}
JSON
)

echo "📋 Règles:"
echo "  ✅ CI obligatoire (6 checks)"
echo "  ✅ Branche à jour"
echo "  ✅ PR avec conversations résolues"
echo "  ✅ Force push bloqué"
echo "  ✅ Suppression bloquée"
echo

read -p "Appliquer? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
fi

echo "🚀 Application..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -d "$RULESET_CONFIG" \
  "$API_URL")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

case $HTTP_CODE in
    201)
        echo
        echo "✅ Ruleset créé avec succès!"
        echo
        echo "🔗 https://github.com/$OWNER/$REPO/settings/rules"
        echo
        echo "🎉 Main protégée:"
        echo "  • Push direct impossible sans CI"
        echo "  • PR + CI obligatoires"
        echo "  • Force push bloqué"
        echo "  • Suppression bloquée"
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
        echo "❌ Repo introuvable"
        exit 1
        ;;
    422)
        echo "⚠️ Ruleset déjà existant ou conflit"
        echo "Vérifie: https://github.com/$OWNER/$REPO/settings/rules"
        BODY=$(echo "$RESPONSE" | head -n -1)
        echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
        exit 1
        ;;
    *)
        echo "❌ Erreur HTTP $HTTP_CODE"
        BODY=$(echo "$RESPONSE" | head -n -1)
        echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
        exit 1
        ;;
esac
