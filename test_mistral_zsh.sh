#!/bin/zsh

# Test Configuration Mistral API
# ================================
# Utilise les alias définis dans ~/.zshrc

echo "🔍 Test Configuration Mistral API"
echo "=================================="
echo ""

# 1. Vérifier .env existe
cd ~/cyclisme-training-logs
if [ -f .env ]; then
    echo "✅ Fichier .env trouvé"
else
    echo "❌ Fichier .env INTROUVABLE"
    exit 1
fi

# 2. Vérifier MISTRAL_API_KEY définie
if grep -q "^MISTRAL_API_KEY=" .env; then
    echo "✅ MISTRAL_API_KEY définie dans .env (ligne active)"
    # Afficher longueur (sans révéler la clé)
    KEY_LENGTH=$(grep "^MISTRAL_API_KEY=" .env | cut -d'=' -f2 | wc -c)
    echo "   Longueur clé: ${KEY_LENGTH} caractères"
else
    echo "❌ MISTRAL_API_KEY NON définie ou commentée (#)"
fi

# 3. Vérifier CLAUDE_API_KEY
if grep -q "^CLAUDE_API_KEY=" .env; then
    echo "✅ CLAUDE_API_KEY définie dans .env (ligne active)"
    KEY_LENGTH=$(grep "^CLAUDE_API_KEY=" .env | cut -d'=' -f2 | wc -c)
    echo "   Longueur clé: ${KEY_LENGTH} caractères"
fi

# 4. Vérifier DEFAULT_AI_PROVIDER
DEFAULT_PROVIDER=$(grep "^DEFAULT_AI_PROVIDER=" .env | cut -d'=' -f2)
echo ""
echo "📋 Provider par défaut: ${DEFAULT_PROVIDER}"

# 5. Tester liste providers
echo ""
echo "📋 Providers disponibles (selon workflow):"
echo "-------------------------------------------"
pa workflow-coach --list-providers 2>&1

# 6. Test détection Mistral avec logs
echo ""
echo "🔍 Test workflow avec --provider mistral_api:"
echo "----------------------------------------------"
pa workflow-coach --activity-id i105842329 --skip-feedback --skip-git --provider mistral_api 2>&1 | head -30

echo ""
echo "=================================="
echo "✅ Test terminé"
echo ""
echo "💡 Interprétation des résultats:"
echo "   - Si '[WARNING] Provider mistral_api not configured' → Code Python ne lit pas .env"
echo "   - Si 'Creating MistralAPIAnalyzer' → Config OK, Mistral utilisé ✅"
echo "   - Si 'Creating ClipboardAnalyzer' → Fallback clipboard activé"
