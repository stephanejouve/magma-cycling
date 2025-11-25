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
