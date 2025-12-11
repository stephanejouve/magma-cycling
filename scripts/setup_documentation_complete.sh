#!/bin/bash
#
# setup_documentation.sh
# Configuration automatique de la documentation dans docs/
#
# Ce script :
# 1. Copie les guides depuis scripts/ vers docs/ avec noms standardisés
# 2. Crée GUIDE_COMMIT_GITHUB.md (manquant)
# 3. Crée docs/README.md (index)
# 4. Met à jour CHANGELOG.md avec date
#
# Usage: bash setup_documentation.sh

set -e

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}======================================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}======================================================================${NC}\n"
}

print_ok() {
    echo -e "${GREEN}✓${NC} $1"
}

# Vérifier qu'on est à la racine
if [ ! -d "scripts" ] || [ ! -d "docs" ]; then
    echo "❌ Erreur : Lancer depuis la racine du projet"
    exit 1
fi

print_header "📚 SETUP DOCUMENTATION - Option A"

# Étape 1 : Copier les guides existants
print_header "📋 ÉTAPE 1/4 : Copie guides scripts/ → docs/"

if [ -f "scripts/WEEKLY_ANALYSIS_GUIDE.md" ]; then
    cp scripts/WEEKLY_ANALYSIS_GUIDE.md docs/GUIDE_WEEKLY_ANALYSIS.md
    print_ok "docs/GUIDE_WEEKLY_ANALYSIS.md créé"
fi

if [ -f "scripts/WORKFLOW_GUIDE.md" ]; then
    cp scripts/WORKFLOW_GUIDE.md docs/WORKFLOW_COMPLET.md
    print_ok "docs/WORKFLOW_COMPLET.md créé"
fi

if [ -f "scripts/UPLOAD_WORKOUTS_GUIDE.md" ]; then
    cp scripts/UPLOAD_WORKOUTS_GUIDE.md docs/GUIDE_UPLOAD_WORKOUTS.md
    print_ok "docs/GUIDE_UPLOAD_WORKOUTS.md créé (bonus)"
fi

# Étape 2 : Créer GUIDE_COMMIT_GITHUB.md
print_header "📝 ÉTAPE 2/4 : Création GUIDE_COMMIT_GITHUB.md"

cat > docs/GUIDE_COMMIT_GITHUB.md << 'EOF'
# Guide Commit et Push GitHub

## 🎯 Workflow Standard

### 1. Vérifier l'État

```bash
git status
```

### 2. Ajouter les Modifications

```bash
# Tout ajouter
git add -A

# Ou sélectif
git add logs/weekly_reports/SXXX/
git add scripts/nom_script.py
```

### 3. Commit avec Message Structuré

```bash
git commit -m "Type: Description courte

- Détail 1
- Détail 2

Contexte: Explication si nécessaire"
```

#### Types de Commit

- 🎯 `feat:` Nouvelle fonctionnalité
- 🐛 `fix:` Correction de bug
- 📝 `docs:` Documentation uniquement
- 🔧 `refactor:` Refactoring (pas de nouvelle feature)
- ✅ `test:` Ajout/modification tests
- 🎨 `style:` Formatage, whitespace
- ⚡ `perf:` Amélioration performance
- 🔨 `chore:` Maintenance (dependencies, etc.)

### 4. Push vers GitHub

```bash
# Push branche actuelle
git push

# Première fois (créer branche remote)
git push -u origin nom-branche
```

## 📊 Cas d'Usage Fréquents

### Rapport Hebdomadaire Complet

```bash
git add logs/weekly_reports/S067/
git commit -m "📊 Rapport hebdomadaire S067

- workout_history_s067.md
- metrics_evolution_s067.md
- training_learnings_s067.md
- protocol_adaptations_s067.md
- transition_s067_s068.md
- bilan_final_s067.md

Semaine complète, tous fichiers générés par weekly_analysis.py"

git push
```

### Modification Script

```bash
git add scripts/weekly_analysis.py
git commit -m "🔧 fix: Correction calcul TSS dans weekly_analysis.py

- Correction ligne 245 : formule TSS normalisée
- Ajout validation TSS < 0
- Tests unitaires ajoutés

Closes #12"

git push
```

### Mise à Jour Documentation

```bash
git add docs/
git commit -m "📝 docs: Mise à jour guides post-migration

- Migration références bilans_hebdo → logs/weekly_reports
- Ajout GUIDE_COMMIT_GITHUB.md
- Mise à jour CHANGELOG.md

Documentation v1.1"

git push
```

## 🔄 Workflows Avancés

### Commit Atomique (Un Changement = Un Commit)

```bash
# Séquence recommandée
git add logs/weekly_reports/S067/workout_history_s067.md
git commit -m "📊 Historique séances S067"

git add logs/weekly_reports/S067/metrics_evolution_s067.md
git commit -m "📊 Évolution métriques S067"

git push
```

### Amend (Corriger Dernier Commit)

```bash
# Oublié un fichier dans le dernier commit
git add fichier_oublie.md
git commit --amend --no-edit

# Corriger message du dernier commit
git commit --amend -m "Nouveau message"

# Push avec force (attention, seulement si pas encore partagé)
git push --force-with-lease
```

### Stash (Mettre de Côté)

```bash
# Sauvegarder travail en cours
git stash push -m "WIP: analyse S067"

# Lister les stash
git stash list

# Récupérer le stash
git stash pop

# Appliquer sans supprimer
git stash apply
```

## 🚨 Situations d'Urgence

### Annuler Dernier Commit (Pas Encore Pushé)

```bash
# Garder les modifications
git reset --soft HEAD~1

# Supprimer les modifications
git reset --hard HEAD~1
```

### Récupérer Fichier Supprimé

```bash
# Voir historique du fichier
git log -- chemin/fichier.md

# Restaurer depuis commit
git checkout COMMIT_HASH -- chemin/fichier.md
```

### Résoudre Conflit

```bash
# Lors d'un pull qui crée un conflit
git pull
# >>> CONFLICT

# Éditer fichiers en conflit (chercher <<<<<<<)
# Puis :
git add fichiers_resolus
git commit -m "🔧 Résolution conflit merge"
git push
```

## 📋 Checklist Pré-Commit

- [ ] `git status` : Vérifier fichiers modifiés
- [ ] Relire les modifications : `git diff`
- [ ] Tests passent (si applicable)
- [ ] Message commit clair et descriptif
- [ ] Pas de secrets/credentials dans le code
- [ ] .gitignore à jour si nouveaux fichiers temporaires

## 📖 Ressources

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Documentation](https://git-scm.com/doc)
- Workflow projet : `docs/WORKFLOW_COMPLET.md`

---

**Dernière mise à jour :** 2025-11-25
**Maintenu par :** Stéphane Jouve
EOF

print_ok "docs/GUIDE_COMMIT_GITHUB.md créé"

# Étape 3 : Créer docs/README.md (index)
print_header "📖 ÉTAPE 3/4 : Création docs/README.md (index)"

cat > docs/README.md << 'EOF'
# Documentation Projet Cyclisme Training Logs

Documentation complète du système d'entraînement et d'analyse.

## 📚 Guides Principaux

### 🎯 Analyse Hebdomadaire
- **[GUIDE_WEEKLY_ANALYSIS.md](GUIDE_WEEKLY_ANALYSIS.md)** : Utilisation de `weekly_analysis.py`
  - Génération automatique des 6 rapports hebdomadaires
  - Options de configuration
  - Exemples d'utilisation

### 🔄 Workflow Complet
- **[WORKFLOW_COMPLET.md](WORKFLOW_COMPLET.md)** : Les 6 phases du workflow
  - Phase 1 : Feedback athlète
  - Phase 2 : Préparation données
  - Phase 3 : Analyse Claude
  - Phase 4 : Insertion historique
  - Phase 5 : Organisation fichiers
  - Phase 6 : Commit GitHub

### 📤 Upload Workouts
- **[GUIDE_UPLOAD_WORKOUTS.md](GUIDE_UPLOAD_WORKOUTS.md)** : Upload séances Intervals.icu
  - Configuration API
  - Formats supportés (.zwo, .mrc, .erg)
  - Troubleshooting

### 💾 Commit GitHub
- **[GUIDE_COMMIT_GITHUB.md](GUIDE_COMMIT_GITHUB.md)** : Bonnes pratiques Git
  - Messages de commit structurés
  - Workflows avancés
  - Résolution conflits

## 📋 Références

### 📦 Versions
- **[CHANGELOG.md](CHANGELOG.md)** : Historique des versions
  - v1.0 : Système initial
  - v1.1 : Migration logs/weekly_reports/

### 🤖 Prompts Claude
- **[project-prompt-v2.1.md](project-prompt-v2.1.md)** : Prompt système
- **[project-prompt-v2.2.md](project-prompt-v2.2.md)** : Variante
- **[project-prompt-v2.3.md](project-prompt-v2.3.md)** : Dernière version

## 🗂️ Structure Projet

```
cyclisme-training-logs/
├── docs/                    # Documentation (vous êtes ici)
├── scripts/                 # Scripts Python/Bash
├── logs/
│   └── weekly_reports/     # Rapports hebdomadaires
│       └── SXXX/           # Par semaine
├── workouts/               # Fichiers .zwo
└── references/             # Protocoles et templates
```

## 🚀 Quick Start

### Premier Rapport Hebdomadaire

```bash
# 1. Collecter feedback
python scripts/prepare_analysis.py

# 2. Générer rapport complet
python scripts/weekly_analysis.py --week 67

# 3. Vérifier
ls logs/weekly_reports/S067/

# 4. Commit
git add logs/weekly_reports/S067/
git commit -m "📊 Rapport S067"
git push
```

### Workflow Quotidien

```bash
# Upload séance
python scripts/upload_workouts.py workouts/S067-03-INT-SweetSpot-V001.zwo

# Insertion historique
python scripts/insert_analysis.py

# Commit
git add logs/
git commit -m "📝 Ajout séance S067-03"
git push
```

## 🛠️ Maintenance

### Analyse Documentation

```bash
bash scripts/analyze_documentation.sh
```

### Migration Données

```bash
bash scripts/migrate_to_logs_weekly_reports.sh --dry-run
```

## 📞 Support

- Issues GitHub : [cyclisme-training-logs/issues](https://github.com/username/cyclisme-training-logs/issues)
- Discussions : [cyclisme-training-logs/discussions](https://github.com/username/cyclisme-training-logs/discussions)

---

**Version Documentation :** 1.1
**Dernière mise à jour :** 2025-11-25
EOF

print_ok "docs/README.md créé"

# Étape 4 : Mettre à jour CHANGELOG.md
print_header "📝 ÉTAPE 4/4 : Mise à jour CHANGELOG.md"

# Vérifier si déjà mis à jour
if ! grep -q "2025-11-25" docs/CHANGELOG.md; then
    # Créer backup
    cp docs/CHANGELOG.md docs/CHANGELOG.md.bak
    
    # Ajouter date si manquante
    if grep -q "## \[1.0\]" docs/CHANGELOG.md; then
        sed -i.tmp 's/## \[1.0\]/## [1.0] - 2025-11-23/' docs/CHANGELOG.md
        rm docs/CHANGELOG.md.tmp 2>/dev/null || true
    fi
    
    # Ajouter version 1.1
    cat > docs/CHANGELOG.md.new << 'CHANGELOG_EOF'
# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [1.1.0] - 2025-11-25

### Added
- `docs/GUIDE_COMMIT_GITHUB.md` : Guide complet commit et push GitHub
- `docs/README.md` : Index central de la documentation
- `scripts/setup_documentation.sh` : Setup automatique documentation
- `scripts/analyze_documentation.sh` : Analyse cohérence documentation

### Changed
- Migration complète vers `logs/weekly_reports/` (terminée)
- Documentation centralisée dans `docs/`
- Correction références obsolètes `bilans_hebdo/` dans tous scripts
- Standardisation noms fichiers documentation

### Fixed
- Cohérence chemins dans `organize_weekly_report.py`
- Cohérence chemins dans `prepare_weekly_report.py`
- Référence `project_prompt_v2.md` → `project_prompt_v2_1_revised.md`

CHANGELOG_EOF
    
    # Ajouter ancien contenu après
    tail -n +3 docs/CHANGELOG.md >> docs/CHANGELOG.md.new
    mv docs/CHANGELOG.md.new docs/CHANGELOG.md
    rm docs/CHANGELOG.md.bak
    
    print_ok "CHANGELOG.md mis à jour avec v1.1.0"
else
    print_ok "CHANGELOG.md déjà à jour"
fi

# Résumé final
print_header "✅ DOCUMENTATION SETUP TERMINÉE"

echo "  Fichiers créés/mis à jour :"
echo ""
echo "    ✅ docs/GUIDE_WEEKLY_ANALYSIS.md"
echo "    ✅ docs/WORKFLOW_COMPLET.md"
echo "    ✅ docs/GUIDE_UPLOAD_WORKOUTS.md"
echo "    ✅ docs/GUIDE_COMMIT_GITHUB.md (nouveau)"
echo "    ✅ docs/README.md (nouveau)"
echo "    ✅ docs/CHANGELOG.md (v1.1.0)"
echo ""
echo "  📚 Vérifier :"
echo "    ls -la docs/"
echo ""
echo "  📊 Relancer analyse :"
echo "    bash scripts/analyze_documentation.sh"
echo ""
echo "  💾 Commit :"
echo "    git add docs/"
echo "    git commit -m '📝 docs: Setup complet documentation v1.1'"
echo "    git push"
echo ""

print_header "🎉 SETUP RÉUSSI"
