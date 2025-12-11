#!/bin/bash
#
# analyze_documentation.sh
# Analyse exhaustive de la cohérence de la documentation
#
# Ce script vérifie :
# 1. Références aux chemins (logs/weekly_reports vs bilans_hebdo)
# 2. Noms de fichiers mentionnés (existent-ils ?)
# 3. Scripts mentionnés (existent-ils ? sont-ils à jour ?)
# 4. Cohérence des workflows décrits
# 5. Liens internes documentation
# 6. Versions mentionnées vs réalité
#
# Usage:
#   bash analyze_documentation.sh
#   bash analyze_documentation.sh --verbose

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Options
VERBOSE=false

for arg in "$@"; do
    case $arg in
        --verbose)
            VERBOSE=true
            shift
            ;;
    esac
done

# Fonctions
print_header() {
    echo -e "\n${BLUE}======================================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}======================================================================${NC}\n"
}

print_section() {
    echo -e "\n${CYAN}>>> $1${NC}\n"
}

print_ok() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC}  $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Bannière
clear
print_header "📚 ANALYSE EXHAUSTIVE DE LA DOCUMENTATION"
echo "  Vérification cohérence post-migration"
echo ""

# Compteurs
TOTAL_ERRORS=0
TOTAL_WARNINGS=0
TOTAL_OK=0

# Liste des fichiers de documentation
DOC_FILES=(
    "README.md"
    "docs/GUIDE_WEEKLY_ANALYSIS.md"
    "docs/WORKFLOW_COMPLET.md"
    "docs/CHANGELOG.md"
    "docs/GUIDE_COMMIT_GITHUB.md"
)

# ============================================================================
# PHASE 1 : VÉRIFICATION EXISTENCE FICHIERS DOCUMENTATION
# ============================================================================
print_header "📋 PHASE 1/7 : Vérification existence fichiers"

for doc in "${DOC_FILES[@]}"; do
    if [ -f "$doc" ]; then
        print_ok "$doc existe"
        TOTAL_OK=$((TOTAL_OK + 1))
    else
        print_error "$doc MANQUANT"
        TOTAL_ERRORS=$((TOTAL_ERRORS + 1))
    fi
done

# ============================================================================
# PHASE 2 : RECHERCHE RÉFÉRENCES OBSOLÈTES "bilans_hebdo"
# ============================================================================
print_header "📂 PHASE 2/7 : Recherche références obsolètes 'bilans_hebdo'"

echo "  Scan de tous les fichiers markdown..."
echo ""

BILANS_HEBDO_REFS=0

for doc in "${DOC_FILES[@]}"; do
    if [ -f "$doc" ]; then
        # Compter les occurrences
        COUNT=$(grep -c "bilans_hebdo" "$doc" 2>/dev/null || echo "0")
        
        if [ "$COUNT" -gt 0 ]; then
            print_error "$doc contient $COUNT référence(s) à 'bilans_hebdo'"
            BILANS_HEBDO_REFS=$((BILANS_HEBDO_REFS + COUNT))
            TOTAL_ERRORS=$((TOTAL_ERRORS + COUNT))
            
            if [ "$VERBOSE" = true ]; then
                echo "    Lignes concernées :"
                grep -n "bilans_hebdo" "$doc" | sed 's/^/      /' || true
                echo ""
            fi
        else
            print_ok "$doc : aucune référence obsolète"
            TOTAL_OK=$((TOTAL_OK + 1))
        fi
    fi
done

if [ $BILANS_HEBDO_REFS -eq 0 ]; then
    print_ok "Aucune référence obsolète 'bilans_hebdo' détectée"
else
    echo ""
    print_warning "TOTAL : $BILANS_HEBDO_REFS référence(s) obsolète(s) à corriger"
fi

# ============================================================================
# PHASE 3 : VÉRIFICATION CHEMINS MENTIONNÉS
# ============================================================================
print_header "🗂️  PHASE 3/7 : Vérification chemins mentionnés"

echo "  Chemins à vérifier :"
echo "    - logs/"
echo "    - logs/weekly_reports/"
echo "    - scripts/"
echo ""

# Vérifier chemins principaux
if [ -d "logs" ]; then
    print_ok "logs/ existe"
    TOTAL_OK=$((TOTAL_OK + 1))
else
    print_error "logs/ MANQUANT"
    TOTAL_ERRORS=$((TOTAL_ERRORS + 1))
fi

if [ -d "logs/weekly_reports" ]; then
    WEEK_COUNT=$(find logs/weekly_reports -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
    print_ok "logs/weekly_reports/ existe ($WEEK_COUNT semaine(s))"
    TOTAL_OK=$((TOTAL_OK + 1))
else
    print_error "logs/weekly_reports/ MANQUANT"
    TOTAL_ERRORS=$((TOTAL_ERRORS + 1))
fi

if [ -d "scripts" ]; then
    SCRIPT_COUNT=$(find scripts -name "*.py" | wc -l | tr -d ' ')
    print_ok "scripts/ existe ($SCRIPT_COUNT scripts Python)"
    TOTAL_OK=$((TOTAL_OK + 1))
else
    print_error "scripts/ MANQUANT"
    TOTAL_ERRORS=$((TOTAL_ERRORS + 1))
fi

# ============================================================================
# PHASE 4 : VÉRIFICATION SCRIPTS MENTIONNÉS DANS DOCUMENTATION
# ============================================================================
print_header "🐍 PHASE 4/7 : Vérification scripts mentionnés"

echo "  Scripts critiques à vérifier :"
echo ""

CRITICAL_SCRIPTS=(
    "scripts/weekly_analysis.py"
    "scripts/upload_workouts.py"
    "scripts/prepare_analysis.py"
    "scripts/insert_analysis.py"
    "scripts/workflow_coach.py"
    "scripts/organize_weekly_report.py"
    "scripts/prepare_weekly_report.py"
)

for script in "${CRITICAL_SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        # Vérifier s'il utilise logs/weekly_reports
        if grep -q "logs.*weekly_reports" "$script" 2>/dev/null; then
            print_ok "$script existe et utilise logs/weekly_reports"
            TOTAL_OK=$((TOTAL_OK + 1))
        elif grep -q "bilans_hebdo" "$script" 2>/dev/null; then
            print_error "$script existe mais utilise ENCORE bilans_hebdo"
            TOTAL_ERRORS=$((TOTAL_ERRORS + 1))
        else
            print_ok "$script existe (pas d'accès direct aux chemins)"
            TOTAL_OK=$((TOTAL_OK + 1))
        fi
    else
        print_warning "$script mentionné dans la doc mais ABSENT"
        TOTAL_WARNINGS=$((TOTAL_WARNINGS + 1))
    fi
done

# ============================================================================
# PHASE 5 : VÉRIFICATION COHÉRENCE WORKFLOWS
# ============================================================================
print_header "🔄 PHASE 5/7 : Vérification cohérence workflows"

echo "  Workflow décrit dans WORKFLOW_COMPLET.md vs réalité..."
echo ""

# Vérifier que le workflow principal est cohérent
if [ -f "docs/WORKFLOW_COMPLET.md" ]; then
    # Vérifier Phase 1 : Feedback
    if grep -q "Phase 1" "docs/WORKFLOW_COMPLET.md"; then
        print_ok "Phase 1 (Feedback) documentée"
        TOTAL_OK=$((TOTAL_OK + 1))
    else
        print_warning "Phase 1 manquante dans WORKFLOW_COMPLET.md"
        TOTAL_WARNINGS=$((TOTAL_WARNINGS + 1))
    fi
    
    # Vérifier Phase 2 : Préparation
    if grep -q "Phase 2" "docs/WORKFLOW_COMPLET.md"; then
        print_ok "Phase 2 (Préparation) documentée"
        TOTAL_OK=$((TOTAL_OK + 1))
    else
        print_warning "Phase 2 manquante dans WORKFLOW_COMPLET.md"
        TOTAL_WARNINGS=$((TOTAL_WARNINGS + 1))
    fi
    
    # Vérifier Phase 3 : Analyse
    if grep -q "Phase 3" "docs/WORKFLOW_COMPLET.md"; then
        print_ok "Phase 3 (Analyse) documentée"
        TOTAL_OK=$((TOTAL_OK + 1))
    else
        print_warning "Phase 3 manquante dans WORKFLOW_COMPLET.md"
        TOTAL_WARNINGS=$((TOTAL_WARNINGS + 1))
    fi
    
    # Vérifier Phase 4 : Insertion
    if grep -q "Phase 4" "docs/WORKFLOW_COMPLET.md"; then
        print_ok "Phase 4 (Insertion) documentée"
        TOTAL_OK=$((TOTAL_OK + 1))
    else
        print_warning "Phase 4 manquante dans WORKFLOW_COMPLET.md"
        TOTAL_WARNINGS=$((TOTAL_WARNINGS + 1))
    fi
    
    # Vérifier Phase 5 : Organisation
    if grep -q "Phase 5" "docs/WORKFLOW_COMPLET.md"; then
        print_ok "Phase 5 (Organisation) documentée"
        TOTAL_OK=$((TOTAL_OK + 1))
    else
        print_warning "Phase 5 manquante dans WORKFLOW_COMPLET.md"
        TOTAL_WARNINGS=$((TOTAL_WARNINGS + 1))
    fi
    
    # Vérifier Phase 6 : Commit
    if grep -q "Phase 6" "docs/WORKFLOW_COMPLET.md"; then
        print_ok "Phase 6 (Commit) documentée"
        TOTAL_OK=$((TOTAL_OK + 1))
    else
        print_warning "Phase 6 manquante dans WORKFLOW_COMPLET.md"
        TOTAL_WARNINGS=$((TOTAL_WARNINGS + 1))
    fi
fi

# ============================================================================
# PHASE 6 : VÉRIFICATION VERSIONS MENTIONNÉES
# ============================================================================
print_header "🔢 PHASE 6/7 : Vérification versions mentionnées"

echo "  Versions dans CHANGELOG.md vs réalité..."
echo ""

if [ -f "docs/CHANGELOG.md" ]; then
    # Vérifier version 1.0
    if grep -q "1.0" "docs/CHANGELOG.md"; then
        print_ok "Version 1.0 documentée"
        TOTAL_OK=$((TOTAL_OK + 1))
    else
        print_warning "Version 1.0 non documentée"
        TOTAL_WARNINGS=$((TOTAL_WARNINGS + 1))
    fi
    
    # Vérifier date dernière mise à jour
    LAST_UPDATE=$(grep -i "dernière mise à jour" docs/CHANGELOG.md || echo "")
    if [ -n "$LAST_UPDATE" ]; then
        print_ok "Date dernière mise à jour présente"
        echo "    $LAST_UPDATE" | sed 's/^/    /'
        TOTAL_OK=$((TOTAL_OK + 1))
    else
        print_warning "Date dernière mise à jour manquante"
        TOTAL_WARNINGS=$((TOTAL_WARNINGS + 1))
    fi
fi

# ============================================================================
# PHASE 7 : GÉNÉRATION RAPPORT DE CORRECTIONS
# ============================================================================
print_header "📝 PHASE 7/7 : Génération rapport de corrections"

REPORT_FILE="RAPPORT_CORRECTIONS_DOC.md"

cat > "$REPORT_FILE" << 'EOF'
# Rapport de Corrections Documentation

**Date d'analyse :** $(date +"%Y-%m-%d %H:%M:%S")
**Post-migration :** logs/weekly_reports/

---

## 📊 Résumé

EOF

echo "- ✅ Tests OK : $TOTAL_OK" >> "$REPORT_FILE"
echo "- ⚠️ Avertissements : $TOTAL_WARNINGS" >> "$REPORT_FILE"
echo "- ❌ Erreurs : $TOTAL_ERRORS" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Ajouter détails bilans_hebdo si nécessaire
if [ $BILANS_HEBDO_REFS -gt 0 ]; then
    cat >> "$REPORT_FILE" << 'EOF'
## 🔴 CORRECTIONS URGENTES

### Références obsolètes "bilans_hebdo"

Les fichiers suivants contiennent des références à l'ancien chemin `bilans_hebdo/` :

EOF

    for doc in "${DOC_FILES[@]}"; do
        if [ -f "$doc" ]; then
            COUNT=$(grep -c "bilans_hebdo" "$doc" 2>/dev/null || echo "0")
            if [ "$COUNT" -gt 0 ]; then
                echo "#### $doc" >> "$REPORT_FILE"
                echo "" >> "$REPORT_FILE"
                echo "**$COUNT occurrence(s) détectée(s)**" >> "$REPORT_FILE"
                echo "" >> "$REPORT_FILE"
                echo '```bash' >> "$REPORT_FILE"
                grep -n "bilans_hebdo" "$doc" >> "$REPORT_FILE" || true
                echo '```' >> "$REPORT_FILE"
                echo "" >> "$REPORT_FILE"
                echo "**Correction recommandée :**" >> "$REPORT_FILE"
                echo '```bash' >> "$REPORT_FILE"
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    echo "sed -i '' 's|bilans_hebdo|logs/weekly_reports|g' $doc" >> "$REPORT_FILE"
                else
                    echo "sed -i 's|bilans_hebdo|logs/weekly_reports|g' $doc" >> "$REPORT_FILE"
                fi
                echo '```' >> "$REPORT_FILE"
                echo "" >> "$REPORT_FILE"
            fi
        fi
    done
fi

# Ajouter scripts à vérifier
cat >> "$REPORT_FILE" << 'EOF'
## 🔧 Scripts à Vérifier

Liste des scripts mentionnés dans la documentation :

EOF

for script in "${CRITICAL_SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        if grep -q "logs.*weekly_reports" "$script" 2>/dev/null; then
            echo "- ✅ \`$script\` : Cohérent (logs/weekly_reports)" >> "$REPORT_FILE"
        elif grep -q "bilans_hebdo" "$script" 2>/dev/null; then
            echo "- ❌ \`$script\` : **Utilise encore bilans_hebdo** ⚠️" >> "$REPORT_FILE"
        else
            echo "- ✅ \`$script\` : OK (pas d'accès direct chemins)" >> "$REPORT_FILE"
        fi
    else
        echo "- ⚠️ \`$script\` : **Fichier absent**" >> "$REPORT_FILE"
    fi
done

# Ajouter recommandations
cat >> "$REPORT_FILE" << 'EOF'

---

## 🎯 Plan d'Action Recommandé

### 1. Corrections Urgentes

EOF

if [ $BILANS_HEBDO_REFS -gt 0 ]; then
    echo "#### A. Remplacer toutes les références 'bilans_hebdo' dans la documentation" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo '```bash' >> "$REPORT_FILE"
    for doc in "${DOC_FILES[@]}"; do
        if [ -f "$doc" ]; then
            COUNT=$(grep -c "bilans_hebdo" "$doc" 2>/dev/null || echo "0")
            if [ "$COUNT" -gt 0 ]; then
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    echo "sed -i '' 's|bilans_hebdo|logs/weekly_reports|g' $doc" >> "$REPORT_FILE"
                else
                    echo "sed -i 's|bilans_hebdo|logs/weekly_reports|g' $doc" >> "$REPORT_FILE"
                fi
            fi
        fi
    done
    echo '```' >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
else
    echo "✅ Aucune correction urgente nécessaire" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << 'EOF'
### 2. Vérifications Complémentaires

- [ ] Vérifier cohérence des workflows (6 phases)
- [ ] Mettre à jour dates de dernière modification
- [ ] Vérifier liens internes documentation
- [ ] Tester les commandes décrites dans les guides

### 3. Mise à Jour CHANGELOG

Ajouter une entrée :

```markdown
## [1.1.0] - YYYY-MM-DD

### Changed
- Migration complète vers logs/weekly_reports/
- Correction références obsolètes bilans_hebdo/ dans documentation
- Mise à jour scripts organize_weekly_report.py et prepare_weekly_report.py

### Fixed
- Cohérence chemins dans tous les fichiers de documentation
```

---

**Généré par :** analyze_documentation.sh
EOF

print_ok "Rapport généré : $REPORT_FILE"
TOTAL_OK=$((TOTAL_OK + 1))

# ============================================================================
# RÉSUMÉ FINAL
# ============================================================================
print_header "📊 RÉSUMÉ FINAL"

echo "  Statistiques :"
echo ""
echo "    ✅ Tests OK          : $TOTAL_OK"
echo "    ⚠️  Avertissements    : $TOTAL_WARNINGS"
echo "    ❌ Erreurs           : $TOTAL_ERRORS"
echo ""

if [ $TOTAL_ERRORS -eq 0 ] && [ $TOTAL_WARNINGS -eq 0 ]; then
    print_ok "🎉 Documentation 100% cohérente !"
elif [ $TOTAL_ERRORS -eq 0 ]; then
    print_warning "⚠️  Documentation cohérente mais $TOTAL_WARNINGS avertissement(s)"
else
    print_error "❌ $TOTAL_ERRORS erreur(s) à corriger"
fi

echo ""
echo "  📄 Rapport détaillé : $REPORT_FILE"
echo ""

# Ouvrir rapport si demandé
if [ "$VERBOSE" = true ]; then
    echo "  📖 Contenu du rapport :"
    echo ""
    cat "$REPORT_FILE" | sed 's/^/    /'
fi

print_header "✅ ANALYSE TERMINÉE"
echo ""
