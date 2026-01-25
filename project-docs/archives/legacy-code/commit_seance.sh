#!/bin/bash
# commit_seance.sh - Commit rapide après une séance
#
# Usage: ./scripts/commit_seance.sh S067 03 "Sweet-Spot 3x8min"

set -e

# Vérifier les arguments
if [ $# -lt 3 ]; then
    echo "Usage: $0 <semaine> <jour> <description>"
    echo "Exemple: $0 S067 03 'Sweet-Spot 3x8min @ 90% FTP'"
    exit 1
fi

SEMAINE=$1
JOUR=$2
DESC=$3

# Vérifier qu'on est dans le bon répertoire
if [ ! -d "logs" ]; then
    echo "Erreur: Exécuter depuis la racine du dépôt"
    exit 1
fi

# Message de commit standardisé
MSG="${SEMAINE}-${JOUR}: ${DESC}"

# Ajouter les logs modifiés
git add logs/workouts-history.md logs/metrics-evolution.md

# Commit optionnel des learnings si modifié
if git diff --cached --quiet logs/training-learnings.md 2>/dev/null; then
    echo "training-learnings.md non modifié"
else
    git add logs/training-learnings.md
fi

# Commit
git commit -m "$MSG"

echo "✅ Commit créé: $MSG"
echo "📤 Pour synchroniser: git push"
