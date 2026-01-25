#!/bin/bash
# Script d'analyse de l'état du repo avant commit

echo "🔍 ANALYSE DE L'ÉTAT DU REPO GITHUB"
echo "====================================="
echo ""

cd ~/cyclisme-training-logs

echo "📊 1. État Git Local"
echo "-------------------"
git status
echo ""

echo "📂 2. Structure des Dossiers"
echo "----------------------------"
echo "Scripts :"
ls -lh scripts/ 2>/dev/null | grep -E "\.(py|sh)$" || echo "  Dossier scripts/ vide ou absent"
echo ""
echo "Documentation :"
ls -lh docs/ 2>/dev/null || echo "  Dossier docs/ absent"
echo ""
echo "Logs :"
ls -lh logs/*.md 2>/dev/null || echo "  Pas de fichiers .md dans logs/"
echo ""

echo "📄 3. Fichiers à la Racine"
echo "-------------------------"
ls -lh *.md 2>/dev/null || echo "  Aucun fichier .md à la racine"
echo ""

echo "📜 4. Derniers Commits"
echo "---------------------"
git log --oneline -10
echo ""

echo "🌿 5. Branches"
echo "-------------"
git branch -a
echo ""

echo "🔄 6. Statut Sync avec GitHub"
echo "-----------------------------"
git fetch origin
echo ""
echo "Commits locaux non pushés :"
git log origin/main..HEAD --oneline || echo "  Aucun commit local non pushé"
echo ""
echo "Commits sur GitHub non récupérés :"
git log HEAD..origin/main --oneline || echo "  Aucun commit distant non récupéré"
echo ""

echo "📋 7. Fichiers Non Trackés"
echo "-------------------------"
git ls-files --others --exclude-standard
echo ""

echo "✅ Analyse terminée !"
echo ""
echo "📝 Prochaine étape :"
echo "   Copie cette sortie et partage-la avec Claude"
echo "   pour qu'il analyse les différences avec les nouveaux fichiers"
