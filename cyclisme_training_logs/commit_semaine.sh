#!/bin/bash
# commit_semaine.sh - Commit du bilan hebdomadaire complet
#
# Usage: ./scripts/commit_semaine.sh 067

set -e

# Vérifier les arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <numéro_semaine>"
    echo "Exemple: $0 067"
    exit 1
fi

SEMAINE_NUM=$1
SEMAINE="s${SEMAINE_NUM}"

# Vérifier qu'on est dans le bon répertoire
if [ ! -d "bilans_hebdo" ]; then
    echo "Erreur: Exécuter depuis la racine du dépôt"
    exit 1
fi

# Vérifier que le répertoire de la semaine existe
if [ ! -d "bilans_hebdo/${SEMAINE}" ]; then
    echo "Erreur: Répertoire bilans_hebdo/${SEMAINE}/ n'existe pas"
    echo "Créer d'abord le répertoire et y placer les 6 fichiers"
    exit 1
fi

# Compter les fichiers markdown dans le répertoire
FILE_COUNT=$(find "bilans_hebdo/${SEMAINE}" -name "*.md" | wc -l)

if [ "$FILE_COUNT" -lt 6 ]; then
    echo "⚠️  Attention: Seulement $FILE_COUNT fichiers trouvés (attendu: 6)"
    echo "Fichiers présents:"
    ls bilans_hebdo/${SEMAINE}/*.md
    read -p "Continuer quand même? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Ajouter les bilans hebdomadaires
git add bilans_hebdo/${SEMAINE}/

# Ajouter aussi les logs principaux mis à jour
git add logs/

# Message de commit détaillé
MSG="Bilan hebdomadaire ${SEMAINE^^}

- ${FILE_COUNT} fichiers de bilan
- Mise à jour logs continus
- Enseignements et protocoles validés"

# Commit
git commit -m "$MSG"

echo "✅ Bilan hebdomadaire ${SEMAINE^^} commité"
echo "📁 Fichiers inclus: $FILE_COUNT bilans + logs"
echo "📤 Pour synchroniser: git push"

# Optionnel: créer un tag
read -p "Créer un tag pour cette semaine? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    TAG="${SEMAINE}"
    git tag -a "$TAG" -m "Fin semaine ${SEMAINE^^}"
    echo "🏷️  Tag créé: $TAG"
    echo "📤 Pour synchroniser le tag: git push --tags"
fi
