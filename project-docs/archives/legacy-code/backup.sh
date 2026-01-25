#!/bin/bash
# backup.sh - Créer une archive de backup du projet
#
# Usage: ./scripts/backup.sh [destination]

set -e

# Destination par défaut
DEST="${1:-$HOME/backups/cyclisme}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="cyclisme_training_${DATE}.tar.gz"

# Créer le répertoire de destination si nécessaire
mkdir -p "$DEST"

# Vérifier qu'on est dans le bon répertoire
if [ ! -d "logs" ] || [ ! -d "bilans_hebdo" ]; then
    echo "Erreur: Exécuter depuis la racine du dépôt"
    exit 1
fi

# Créer l'archive
echo "📦 Création du backup..."
tar -czf "${DEST}/${BACKUP_NAME}" \
    --exclude='.git' \
    --exclude='*.swp' \
    --exclude='__pycache__' \
    --exclude='venv' \
    .

# Vérifier la création
if [ -f "${DEST}/${BACKUP_NAME}" ]; then
    SIZE=$(du -h "${DEST}/${BACKUP_NAME}" | cut -f1)
    echo "✅ Backup créé: ${BACKUP_NAME} (${SIZE})"
    echo "📂 Emplacement: ${DEST}/"

    # Lister les backups existants
    echo ""
    echo "📋 Backups disponibles:"
    ls -lh "${DEST}"/cyclisme_training_*.tar.gz 2>/dev/null || echo "Aucun backup précédent"

    # Optionnel: supprimer les backups >30 jours
    read -p "Nettoyer les backups >30 jours? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        find "${DEST}" -name "cyclisme_training_*.tar.gz" -mtime +30 -delete
        echo "🧹 Anciens backups supprimés"
    fi
else
    echo "❌ Erreur lors de la création du backup"
    exit 1
fi
