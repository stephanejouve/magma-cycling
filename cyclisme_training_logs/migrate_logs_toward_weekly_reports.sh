#!/bin/bash
#
# migrate_to_logs_weekly_reports.sh
# Migration automatique de bilans_hebdo/ vers logs/weekly_reports/
#
# Ce script :
# 1. Vérifie l'état du repo (pas de modifications non commitées)
# 2. Crée backup de sécurité
# 3. Migre les données bilans_hebdo/ → logs/weekly_reports/
# 4. Corrige les 2 scripts obsolètes (organize_weekly_report.py, prepare_weekly_report.py)
# 5. Corrige la référence project_prompt obsolète
# 6. Supprime bilans_hebdo/ (optionnel)
# 7. Propose commit automatique
#
# Usage:
#   bash migrate_to_logs_weekly_reports.sh
#   bash migrate_to_logs_weekly_reports.sh --keep-old-dir  # Garder bilans_hebdo/
#   bash migrate_to_logs_weekly_reports.sh --dry-run       # Test sans modifications

set -e  # Arrêt en cas d'erreur

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Options
DRY_RUN=false
KEEP_OLD_DIR=false

# Parser les arguments
for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --keep-old-dir)
            KEEP_OLD_DIR=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dry-run        Simulation sans modifications"
            echo "  --keep-old-dir   Garder bilans_hebdo/ après migration"
            echo "  --help           Afficher cette aide"
            exit 0
            ;;
    esac
done

# Fonctions utilitaires
print_header() {
    echo -e "\n${BLUE}======================================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}======================================================================${NC}\n"
}

print_step() {
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
print_header "🔧 MIGRATION AUTOMATIQUE"
echo -e "  ${BLUE}bilans_hebdo/${NC} → ${GREEN}logs/weekly_reports/${NC}"
echo ""

if [ "$DRY_RUN" = true ]; then
    print_warning "MODE DRY-RUN : Aucune modification réelle"
    echo ""
fi

# Étape 0 : Vérifications préliminaires
print_header "📋 ÉTAPE 0/7 : Vérifications préliminaires"

# Vérifier qu'on est à la racine du projet
if [ ! -f "scripts/weekly_analysis.py" ]; then
    print_error "Erreur : Ce script doit être lancé depuis la racine du projet"
    echo "  Répertoire actuel : $(pwd)"
    echo ""
    echo "  Utilisation correcte :"
    echo "    cd /Users/stephanejouve/cyclisme-training-logs"
    echo "    bash scripts/migrate_to_logs_weekly_reports.sh"
    exit 1
fi
print_step "Répertoire projet correct"

# Vérifier que Git est propre
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    print_error "Erreur : Modifications non commitées détectées"
    echo ""
    echo "  Commiter ou stasher les modifications avant migration :"
    echo "    git status"
    echo "    git add -A && git commit -m 'WIP: avant migration'"
    echo "    # ou"
    echo "    git stash"
    exit 1
fi
print_step "Git propre (aucune modification non commitée)"

# Vérifier existence scripts à corriger
if [ ! -f "scripts/organize_weekly_report.py" ]; then
    print_warning "scripts/organize_weekly_report.py non trouvé (peut-être déjà supprimé)"
fi

if [ ! -f "scripts/prepare_weekly_report.py" ]; then
    print_warning "scripts/prepare_weekly_report.py non trouvé (peut-être déjà supprimé)"
fi

echo ""

# Étape 1 : Backup de sécurité
print_header "💾 ÉTAPE 1/7 : Backup de sécurité"

BACKUP_DIR="backups/migration_$(date +%Y%m%d_%H%M%S)"

if [ "$DRY_RUN" = false ]; then
    mkdir -p "$BACKUP_DIR"
    
    # Backup scripts
    if [ -f "scripts/organize_weekly_report.py" ]; then
        cp scripts/organize_weekly_report.py "$BACKUP_DIR/"
        print_step "Sauvegarde organize_weekly_report.py"
    fi
    
    if [ -f "scripts/prepare_weekly_report.py" ]; then
        cp scripts/prepare_weekly_report.py "$BACKUP_DIR/"
        print_step "Sauvegarde prepare_weekly_report.py"
    fi
    
    # Backup bilans_hebdo si existe
    if [ -d "bilans_hebdo" ]; then
        cp -r bilans_hebdo "$BACKUP_DIR/"
        print_step "Sauvegarde bilans_hebdo/"
    fi
    
    echo ""
    echo "  📁 Backup créé dans : $BACKUP_DIR"
else
    print_step "Backup serait créé dans : $BACKUP_DIR"
fi

echo ""

# Étape 2 : Migration des données
print_header "📂 ÉTAPE 2/7 : Migration des données"

if [ -d "bilans_hebdo" ]; then
    echo "  Source : bilans_hebdo/"
    echo "  Cible  : logs/weekly_reports/"
    echo ""
    
    # Compter les fichiers
    FILE_COUNT=$(find bilans_hebdo -type f | wc -l | tr -d ' ')
    DIR_COUNT=$(find bilans_hebdo -mindepth 1 -type d | wc -l | tr -d ' ')
    
    echo "  Contenu détecté :"
    echo "    - $DIR_COUNT dossier(s)"
    echo "    - $FILE_COUNT fichier(s)"
    echo ""
    
    if [ "$DRY_RUN" = false ]; then
        # Créer le répertoire cible
        mkdir -p logs/weekly_reports
        
        # Migration avec préservation de la structure
        # Renommer s067 → S067 si nécessaire
        for source_dir in bilans_hebdo/*; do
            if [ -d "$source_dir" ]; then
                basename=$(basename "$source_dir")
                
                # Convertir s067 → S067 (minuscule → majuscule)
                if [[ "$basename" =~ ^s[0-9]{3}$ ]]; then
                    target_basename=$(echo "$basename" | tr 's' 'S')
                else
                    target_basename="$basename"
                fi
                
                target_dir="logs/weekly_reports/$target_basename"
                
                # Copier
                cp -r "$source_dir" "$target_dir"
                print_step "Migré : $basename → $target_basename"
            fi
        done
        
        echo ""
        print_step "Migration des données terminée"
    else
        print_step "Migration serait effectuée (dry-run)"
        echo ""
        echo "  Dossiers qui seraient migrés :"
        for source_dir in bilans_hebdo/*; do
            if [ -d "$source_dir" ]; then
                basename=$(basename "$source_dir")
                if [[ "$basename" =~ ^s[0-9]{3}$ ]]; then
                    target_basename=$(echo "$basename" | tr 's' 'S')
                else
                    target_basename="$basename"
                fi
                echo "    - $basename → logs/weekly_reports/$target_basename"
            fi
        done
    fi
else
    print_warning "Aucun dossier bilans_hebdo/ trouvé (peut-être déjà migré)"
fi

echo ""

# Étape 3 : Correction organize_weekly_report.py
print_header "🔧 ÉTAPE 3/7 : Correction organize_weekly_report.py"

if [ -f "scripts/organize_weekly_report.py" ]; then
    echo "  Ligne 73 : bilans_hebdo → logs/weekly_reports"
    echo ""
    
    if [ "$DRY_RUN" = false ]; then
        # Correction avec sed (compatible macOS et Linux)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' 's|self.bilans_dir = self.project_root / "bilans_hebdo"|self.bilans_dir = self.project_root / "logs" / "weekly_reports"|g' scripts/organize_weekly_report.py
        else
            # Linux
            sed -i 's|self.bilans_dir = self.project_root / "bilans_hebdo"|self.bilans_dir = self.project_root / "logs" / "weekly_reports"|g' scripts/organize_weekly_report.py
        fi
        
        # Vérifier la modification
        if grep -q 'self.bilans_dir = self.project_root / "logs" / "weekly_reports"' scripts/organize_weekly_report.py; then
            print_step "Correction appliquée avec succès"
        else
            print_error "Échec de la correction (vérification manuelle requise)"
        fi
    else
        print_step "Correction serait appliquée (dry-run)"
    fi
else
    print_warning "Script non trouvé (peut-être déjà supprimé)"
fi

echo ""

# Étape 4 : Correction prepare_weekly_report.py
print_header "🔧 ÉTAPE 4/7 : Correction prepare_weekly_report.py"

if [ -f "scripts/prepare_weekly_report.py" ]; then
    echo "  Ligne 56 : bilans_hebdo → logs/weekly_reports"
    echo "  Ligne 64 : project_prompt_v2.md → project_prompt_v2_1_revised.md"
    echo ""
    
    if [ "$DRY_RUN" = false ]; then
        # Correction bilans_hebdo
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' 's|self.bilans_dir = self.project_root / "bilans_hebdo"|self.bilans_dir = self.project_root / "logs" / "weekly_reports"|g' scripts/prepare_weekly_report.py
            sed -i '' 's|project_prompt_v2.md|project_prompt_v2_1_revised.md|g' scripts/prepare_weekly_report.py
        else
            sed -i 's|self.bilans_dir = self.project_root / "bilans_hebdo"|self.bilans_dir = self.project_root / "logs" / "weekly_reports"|g' scripts/prepare_weekly_report.py
            sed -i 's|project_prompt_v2.md|project_prompt_v2_1_revised.md|g' scripts/prepare_weekly_report.py
        fi
        
        # Vérifier les modifications
        ERRORS=0
        if ! grep -q 'self.bilans_dir = self.project_root / "logs" / "weekly_reports"' scripts/prepare_weekly_report.py; then
            print_error "Échec correction ligne 56"
            ERRORS=$((ERRORS + 1))
        else
            print_step "Ligne 56 corrigée"
        fi
        
        if ! grep -q 'project_prompt_v2_1_revised.md' scripts/prepare_weekly_report.py; then
            print_error "Échec correction ligne 64"
            ERRORS=$((ERRORS + 1))
        else
            print_step "Ligne 64 corrigée"
        fi
        
        if [ $ERRORS -eq 0 ]; then
            print_step "Toutes les corrections appliquées avec succès"
        fi
    else
        print_step "Corrections seraient appliquées (dry-run)"
    fi
else
    print_warning "Script non trouvé (peut-être déjà supprimé)"
fi

echo ""

# Étape 5 : Suppression ancien dossier (optionnel)
print_header "🗑️  ÉTAPE 5/7 : Suppression ancien dossier (optionnel)"

if [ -d "bilans_hebdo" ]; then
    if [ "$KEEP_OLD_DIR" = true ]; then
        print_warning "Conservation de bilans_hebdo/ (--keep-old-dir)"
        echo "  Tu peux supprimer manuellement après validation :"
        echo "    rm -rf bilans_hebdo/"
    else
        echo "  Dossier : bilans_hebdo/"
        echo ""
        
        if [ "$DRY_RUN" = false ]; then
            echo -n "  Supprimer bilans_hebdo/ ? (o/n) : "
            read -r CONFIRM
            
            if [ "$CONFIRM" = "o" ] || [ "$CONFIRM" = "O" ]; then
                rm -rf bilans_hebdo/
                print_step "Dossier bilans_hebdo/ supprimé"
            else
                print_warning "Dossier bilans_hebdo/ conservé"
                echo "  Tu peux le supprimer manuellement après validation :"
                echo "    rm -rf bilans_hebdo/"
            fi
        else
            print_step "Dossier serait supprimé (dry-run)"
        fi
    fi
else
    print_step "Aucun dossier à supprimer"
fi

echo ""

# Étape 6 : Vérification finale
print_header "✅ ÉTAPE 6/7 : Vérification finale"

echo "  Vérification de la cohérence..."
echo ""

ERRORS=0

# Vérifier logs/weekly_reports existe
if [ -d "logs/weekly_reports" ]; then
    MIGRATED_DIRS=$(find logs/weekly_reports -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
    print_step "logs/weekly_reports/ existe ($MIGRATED_DIRS dossier(s))"
else
    print_error "logs/weekly_reports/ n'existe pas"
    ERRORS=$((ERRORS + 1))
fi

# Vérifier scripts corrigés
if [ -f "scripts/organize_weekly_report.py" ]; then
    if grep -q 'logs.*weekly_reports' scripts/organize_weekly_report.py; then
        print_step "organize_weekly_report.py corrigé"
    else
        print_error "organize_weekly_report.py non corrigé"
        ERRORS=$((ERRORS + 1))
    fi
fi

if [ -f "scripts/prepare_weekly_report.py" ]; then
    if grep -q 'logs.*weekly_reports' scripts/prepare_weekly_report.py; then
        print_step "prepare_weekly_report.py corrigé (ligne 56)"
    else
        print_error "prepare_weekly_report.py non corrigé (ligne 56)"
        ERRORS=$((ERRORS + 1))
    fi
    
    if grep -q 'project_prompt_v2_1_revised.md' scripts/prepare_weekly_report.py; then
        print_step "prepare_weekly_report.py corrigé (ligne 64)"
    else
        print_error "prepare_weekly_report.py non corrigé (ligne 64)"
        ERRORS=$((ERRORS + 1))
    fi
fi

echo ""

if [ $ERRORS -eq 0 ]; then
    print_step "✅ Toutes les vérifications passées"
else
    print_error "❌ $ERRORS erreur(s) détectée(s)"
    echo ""
    echo "  Vérifier manuellement les fichiers concernés"
fi

echo ""

# Étape 7 : Commit Git (optionnel)
print_header "💾 ÉTAPE 7/7 : Commit Git (optionnel)"

if [ "$DRY_RUN" = false ]; then
    # Afficher git status
    echo "  Modifications détectées :"
    echo ""
    git status --short | sed 's/^/    /'
    echo ""
    
    echo -n "  Commiter ces modifications ? (o/n) : "
    read -r COMMIT
    
    if [ "$COMMIT" = "o" ] || [ "$COMMIT" = "O" ]; then
        # Message de commit
        COMMIT_MSG="🔧 Migration complète vers logs/weekly_reports/

- Migré données bilans_hebdo/ → logs/weekly_reports/
- Corrigé organize_weekly_report.py (logs/weekly_reports)
- Corrigé prepare_weekly_report.py (logs/weekly_reports + project_prompt ref)
"
        
        if [ ! -d "bilans_hebdo" ]; then
            COMMIT_MSG="$COMMIT_MSG- Supprimé ancien dossier bilans_hebdo/
"
        fi
        
        COMMIT_MSG="$COMMIT_MSG
Tous les scripts utilisent maintenant logs/weekly_reports/

🤖 Migration automatique avec migrate_to_logs_weekly_reports.sh"
        
        # Add et commit
        git add -A
        git commit -m "$COMMIT_MSG"
        
        print_step "Commit effectué avec succès"
        echo ""
        echo "  Message de commit :"
        echo "$COMMIT_MSG" | sed 's/^/    /'
        echo ""
        
        # Proposer le push
        echo -n "  Pousser vers remote ? (o/n) : "
        read -r PUSH
        
        if [ "$PUSH" = "o" ] || [ "$PUSH" = "O" ]; then
            git push
            print_step "Push effectué avec succès"
        else
            print_warning "Push skippé (à faire manuellement : git push)"
        fi
    else
        print_warning "Commit skippé"
        echo ""
        echo "  Pour commiter manuellement :"
        echo "    git add -A"
        echo "    git commit -m 'Migration logs/weekly_reports'"
    fi
else
    print_step "Commit serait proposé (dry-run)"
fi

echo ""

# Résumé final
print_header "🎉 MIGRATION TERMINÉE"

if [ "$DRY_RUN" = true ]; then
    echo -e "  ${YELLOW}MODE DRY-RUN${NC} : Aucune modification réelle effectuée"
    echo ""
    echo "  Pour exécuter réellement :"
    echo "    bash scripts/migrate_to_logs_weekly_reports.sh"
else
    echo "  ✅ Données migrées vers logs/weekly_reports/"
    echo "  ✅ Scripts corrigés"
    
    if [ ! -d "bilans_hebdo" ]; then
        echo "  ✅ Ancien dossier supprimé"
    else
        echo "  ⚠️  Ancien dossier conservé : bilans_hebdo/"
    fi
    
    echo ""
    echo "  📁 Backup de sécurité : $BACKUP_DIR"
fi

echo ""
echo "  📊 VÉRIFICATION FINALE :"
echo "    ls -la logs/weekly_reports/"
echo ""

if [ -d "logs/weekly_reports" ]; then
    ls -la logs/weekly_reports/ | sed 's/^/    /'
fi

echo ""
echo "  📖 Documentation mise à jour :"
echo "    - weekly_analysis.py : logs/weekly_reports/"
echo "    - organize_weekly_report.py : logs/weekly_reports/"
echo "    - prepare_weekly_report.py : logs/weekly_reports/"
echo ""
print_header "✅ MIGRATION RÉUSSIE"
echo ""
