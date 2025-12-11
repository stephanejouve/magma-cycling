#!/bin/bash
# Script de correction automatique de la documentation
# Mise à jour GUIDE_UPLOAD_WORKOUTS.md suite au fix du parsing des noms

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "========================================================================"
echo "  CORRECTION DOCUMENTATION - GUIDE_UPLOAD_WORKOUTS.md"
echo "========================================================================"
echo ""

# Vérifier qu'on est dans le bon répertoire
if [ ! -d "docs" ]; then
    echo -e "${RED}❌ Répertoire 'docs/' non trouvé${NC}"
    echo "   Veuillez exécuter depuis la racine du projet"
    exit 1
fi

DOC_FILE="docs/GUIDE_UPLOAD_WORKOUTS.md"

if [ ! -f "$DOC_FILE" ]; then
    echo -e "${RED}❌ Fichier $DOC_FILE non trouvé${NC}"
    exit 1
fi

echo -e "${BLUE}📄 Fichier trouvé : $DOC_FILE${NC}"
echo ""

# Backup
BACKUP_FILE="${DOC_FILE}.backup-$(date +%Y%m%d-%H%M%S)"
cp "$DOC_FILE" "$BACKUP_FILE"
echo -e "${GREEN}✅ Backup créé : $BACKUP_FILE${NC}"
echo ""

# Compteur de modifications
CHANGES=0

# ============================================================================
# CORRECTION 1 : Section "Format des Workouts"
# ============================================================================
echo -e "${YELLOW}🔧 Correction 1 : Section 'Format des Workouts'${NC}"

# Chercher et remplacer les annotations obsolètes
if grep -q "Cette ligne devient le.*nom.*Intervals.icu" "$DOC_FILE" 2>/dev/null; then
    # Remplacer l'annotation pointant vers la première ligne
    sed -i.tmp '/Sweet Spot Adaptation.*65min.*65 TSS/,/^$/ {
        s/^.*↑.*Cette ligne devient le.*nom.*$/                          ↑ Première ligne = description courte (référence Claude)/
    }' "$DOC_FILE"
    
    # Ajouter annotation correcte sur le délimiteur si pas déjà présente
    if ! grep -q "Ce nom devient le.*nom.*Intervals.icu" "$DOC_FILE"; then
        sed -i.tmp '/=== WORKOUT S[0-9][0-9][0-9]-[0-9][0-9]-.*/a\
                          ↑ Ce nom devient le "nom" dans Intervals.icu
' "$DOC_FILE"
    fi
    
    echo -e "  ${GREEN}✓${NC} Annotations corrigées"
    CHANGES=$((CHANGES + 1))
else
    echo -e "  ${BLUE}ℹ${NC}  Pattern non trouvé ou déjà corrigé"
fi

# ============================================================================
# CORRECTION 2 : Section "Parsing des Workouts"
# ============================================================================
echo -e "${YELLOW}🔧 Correction 2 : Section 'Parsing des Workouts'${NC}"

# Remplacer description obsolète du parsing
sed -i.tmp 's/Nom du workout.*:.*Première ligne du contenu/Nom du workout** : Nom structuré depuis le délimiteur `=== WORKOUT ... ===/g' "$DOC_FILE"

# Vérifier si la modification a eu lieu
if grep -q "Nom structuré depuis le délimiteur" "$DOC_FILE" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} Description parsing mise à jour"
    CHANGES=$((CHANGES + 1))
else
    echo -e "  ${BLUE}ℹ${NC}  Section déjà à jour ou non trouvée"
fi

# ============================================================================
# CORRECTION 3 : Ajouter section "Format Nom Important" si absente
# ============================================================================
echo -e "${YELLOW}🔧 Correction 3 : Section 'Format Nom Important'${NC}"

if ! grep -q "Format Nom Important" "$DOC_FILE" 2>/dev/null; then
    # Créer le contenu à ajouter
    cat >> "$DOC_FILE" << 'EOF'

### ⚠️ Format Nom Important

Le nom du workout dans Intervals.icu provient **uniquement** du délimiteur :
- ✅ `=== WORKOUT S069-02-INT-SweetSpotAdaptation-V002 ===` → Nom utilisé
- ❌ `Sweet Spot Adaptation 2x10 (65min, 65 TSS)` → Description uniquement

**Avantages :**
- **Traçabilité** : Lien direct avec fichiers .zwo
- **Cohérence** : Respect convention de nommage SSSS-JJ-TYPE-NomExercice-VVVV
- **Parsing** : Extraction automatique type/jour/version depuis le nom

**Exemple :**
```
=== WORKOUT S069-02-INT-SweetSpotAdaptation-V002 ===
```
Devient dans Intervals.icu :
- Nom : `S069-02-INT-SweetSpotAdaptation-V002`
- Permet recherche par : S069, INT, SweetSpot, V002
- Lien fichier : `S069-02-INT-SweetSpotAdaptation-V002.zwo`

EOF

    echo -e "  ${GREEN}✓${NC} Section 'Format Nom Important' ajoutée"
    CHANGES=$((CHANGES + 1))
else
    echo -e "  ${BLUE}ℹ${NC}  Section déjà présente"
fi

# ============================================================================
# CORRECTION 4 : Mettre à jour CHANGELOG.md
# ============================================================================
echo ""
echo -e "${YELLOW}🔧 Correction 4 : Mise à jour CHANGELOG.md${NC}"

CHANGELOG_FILE="docs/CHANGELOG.md"

if [ -f "$CHANGELOG_FILE" ]; then
    # Vérifier si l'entrée v1.1.1 existe déjà
    if ! grep -q "1.1.1" "$CHANGELOG_FILE" 2>/dev/null; then
        # Créer backup CHANGELOG
        cp "$CHANGELOG_FILE" "${CHANGELOG_FILE}.backup-$(date +%Y%m%d-%H%M%S)"
        
        # Méthode simple : créer nouveau contenu complet
        # 1. Extraire le header (avant première version)
        # 2. Insérer nouvelle version
        # 3. Ajouter le reste
        
        # Trouver la ligne du premier ## [
        FIRST_VERSION_LINE=$(grep -n "^## \[" "$CHANGELOG_FILE" | head -1 | cut -d: -f1)
        
        if [ -n "$FIRST_VERSION_LINE" ]; then
            # Extraire header
            head -n $((FIRST_VERSION_LINE - 1)) "$CHANGELOG_FILE" > /tmp/changelog_header.txt
            
            # Créer nouvelle entrée
            cat > /tmp/changelog_entry.txt << 'NEWENTRY'

## [1.1.1] - 2025-11-25

### Documentation
- **GUIDE_UPLOAD_WORKOUTS.md** : Correction annotations format workouts
  - Nom workout extrait du délimiteur `=== WORKOUT ... ===` (et non première ligne)
  - Ajout section "Format Nom Important" avec exemples
  - Clarification avantages : traçabilité, cohérence, parsing automatique
- Référence : fix `upload_workouts.py` lignes 124+175 (v1.1.0)

NEWENTRY
            
            # Extraire le reste (à partir de la première version)
            tail -n +$FIRST_VERSION_LINE "$CHANGELOG_FILE" > /tmp/changelog_rest.txt
            
            # Assembler
            cat /tmp/changelog_header.txt /tmp/changelog_entry.txt /tmp/changelog_rest.txt > "$CHANGELOG_FILE"
            
            # Nettoyer
            rm -f /tmp/changelog_header.txt /tmp/changelog_entry.txt /tmp/changelog_rest.txt
            
            echo -e "  ${GREEN}✓${NC} Version 1.1.1 ajoutée au CHANGELOG"
            CHANGES=$((CHANGES + 1))
        else
            # Pas de version existante, ajouter à la fin
            cat >> "$CHANGELOG_FILE" << 'NEWENTRY'

## [1.1.1] - 2025-11-25

### Documentation
- **GUIDE_UPLOAD_WORKOUTS.md** : Correction annotations format workouts
  - Nom workout extrait du délimiteur `=== WORKOUT ... ===` (et non première ligne)
  - Ajout section "Format Nom Important" avec exemples
  - Clarification avantages : traçabilité, cohérence, parsing automatique
- Référence : fix `upload_workouts.py` lignes 124+175 (v1.1.0)

NEWENTRY
            echo -e "  ${GREEN}✓${NC} Version 1.1.1 ajoutée au CHANGELOG"
            CHANGES=$((CHANGES + 1))
        fi
    else
        echo -e "  ${BLUE}ℹ${NC}  Version 1.1.1 déjà présente"
    fi
else
    echo -e "  ${YELLOW}⚠${NC}  CHANGELOG.md non trouvé - ignoré"
fi

# Nettoyer fichiers temporaires
rm -f "${DOC_FILE}.tmp"

# ============================================================================
# RÉSUMÉ
# ============================================================================
echo ""
echo "========================================================================"
echo "  📊 RÉSUMÉ DES CORRECTIONS"
echo "========================================================================"
echo -e "${GREEN}✅ Modifications appliquées : $CHANGES${NC}"
echo -e "${GREEN}✅ Backup disponible : $BACKUP_FILE${NC}"
if ls "${CHANGELOG_FILE}.backup-"* 1> /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backup CHANGELOG disponible${NC}"
fi
echo ""

if [ $CHANGES -gt 0 ]; then
    echo -e "${BLUE}📝 Fichiers modifiés :${NC}"
    echo "   - $DOC_FILE"
    if [ -f "$CHANGELOG_FILE" ] && grep -q "1.1.1" "$CHANGELOG_FILE"; then
        echo "   - $CHANGELOG_FILE"
    fi
    echo ""
    
    echo -e "${YELLOW}🔍 Vérification recommandée :${NC}"
    echo "   git diff docs/GUIDE_UPLOAD_WORKOUTS.md"
    if [ -f "$CHANGELOG_FILE" ]; then
        echo "   git diff docs/CHANGELOG.md"
    fi
    echo ""
    
    echo -e "${GREEN}✅ Prêt pour commit :${NC}"
    echo '   git add docs/GUIDE_UPLOAD_WORKOUTS.md docs/CHANGELOG.md'
    echo '   git commit -m "docs(upload_workouts): Clarifier extraction nom depuis délimiteur'
    echo ''
    echo '   - Section Format Workouts: Annotation corrigée (délimiteur → nom)'
    echo '   - Ajout: Section Format Nom Important (traçabilité)'
    echo '   - CHANGELOG: Version 1.1.1 (documentation)'
    echo '   - Ref: fix upload_workouts.py v1.1.0 (lignes 124+175)"'
    echo ""
else
    echo -e "${BLUE}ℹ️  Aucune modification nécessaire - Documentation déjà à jour${NC}"
    echo ""
fi

echo "========================================================================"
echo ""
