# 🚀 Instructions Setup GitHub

Ce guide te permet de configurer le dépôt GitHub pour ton suivi d'entraînement.

---

## 📋 Prérequis

- [ ] Compte GitHub créé
- [ ] Git installé sur ton ordinateur
- [ ] Terminal/ligne de commande accessible
- [ ] Clé SSH GitHub configurée (recommandé) ou HTTPS

---

## 🎯 Étape 1 : Créer le Dépôt GitHub

### Sur GitHub.com

1. **Connexion** : https://github.com
2. **Nouveau dépôt** : Clic sur "+" → "New repository"
3. **Configuration** :
   ```
   Repository name: cyclisme-training-logs
   Description: Suivi structuré d'entraînement cycliste (FTP 220W→260W+)
   Visibility: ✅ Private (recommandé) ou Public
   ❌ Ne PAS initialiser avec README/gitignore/licence (on a déjà tout)
   ```
4. **Create repository**

### Copier l'URL du dépôt
Tu verras une URL du type :
```
SSH: git@github.com:tonusername/cyclisme-training-logs.git
HTTPS: https://github.com/tonusername/cyclisme-training-logs.git
```
Copie celle qui correspond à ta configuration (SSH recommandé).

---

## 🛠️ Étape 2 : Télécharger les Fichiers depuis Claude

### Depuis ce chat Claude

1. **Télécharge l'archive** que je vais créer ci-dessous
2. **Décompresse-la** sur ton ordinateur
3. **Note le chemin** du répertoire décompressé

---

## 💻 Étape 3 : Initialiser Git Localement

### Sur TON terminal

```bash
# 1. Aller dans le répertoire du projet
cd /chemin/vers/cyclisme-training-logs

# 2. Initialiser Git
git init

# 3. Ajouter tous les fichiers
git add .

# 4. Premier commit
git commit -m "Initial commit: Structure projet v2.0.1"

# 5. Créer la branche main (si pas déjà créée)
git branch -M main

# 6. Connecter au dépôt GitHub (remplace l'URL par la tienne)
git remote add origin git@github.com:tonusername/cyclisme-training-logs.git

# 7. Vérifier la connexion
git remote -v

# 8. Push initial
git push -u origin main
```

---

## ✅ Étape 4 : Vérifier

### Sur GitHub.com

1. Rafraîchir la page du dépôt
2. Tu dois voir :
   - ✅ README.md affiché
   - ✅ Répertoires : logs/, bilans_hebdo/, references/, scripts/
   - ✅ Fichiers : .gitignore, etc.

---

## 🔄 Étape 5 : Workflow Quotidien

### Après chaque séance

```bash
# Éditer les logs
vim logs/workouts-history.md
vim logs/metrics-evolution.md

# Commit rapide avec le script
./scripts/commit_seance.sh S067 03 "Sweet-Spot 3x8min @ 90% FTP"

# Synchroniser avec GitHub
git push
```

### Fin de semaine

```bash
# 1. Préparer les bilans avec Claude
# (Upload logs → Claude génère 6 fichiers → Download)

# 2. Créer le répertoire de la semaine
mkdir -p bilans_hebdo/s067

# 3. Déplacer les 6 fichiers dedans
mv bilan_*.md bilans_hebdo/s067/

# 4. Commit avec le script
./scripts/commit_semaine.sh 067

# 5. Synchroniser
git push
# Si tu as créé un tag:
git push --tags
```

---

## 🤝 Collaboration avec Claude

### Workflow Hybride

```
┌─────────────────────────────────┐
│  1. TON TERMINAL (local)        │
│     - Édition logs quotidiens   │
│     - git add / commit / push   │
└────────────┬────────────────────┘
             │
             ↓
┌─────────────────────────────────┐
│  2. GITHUB (remote)             │
│     - Stockage centralisé       │
│     - Historique versionné      │
│     - Backup automatique        │
└────────────┬────────────────────┘
             │
             ↓ (fin de semaine)
┌─────────────────────────────────┐
│  3. CLAUDE (analyse)            │
│     - Upload des 4 logs         │
│     - Génération 6 bilans       │
│     - Recommandations S+1       │
└────────────┬────────────────────┘
             │
             ↓
┌─────────────────────────────────┐
│  4. RETOUR TON TERMINAL         │
│     - Download bilans           │
│     - Commit semaine            │
│     - git push                  │
└─────────────────────────────────┘
```

### Commandes Git Essentielles

```bash
# Voir l'état actuel
git status

# Voir l'historique
git log --oneline --graph --all

# Voir les modifications
git diff

# Annuler des modifications locales (attention!)
git checkout -- fichier.md

# Récupérer la dernière version depuis GitHub
git pull

# Créer une branche (pour tester des modifications)
git checkout -b test-protocole
# ... faire des modifs ...
git checkout main  # revenir à main
git merge test-protocole  # fusionner si satisfait
```

---

## 🛡️ Bonnes Pratiques

### Commits

✅ **Bon commit**
```bash
git commit -m "S067-03: Sweet-Spot 3x8min @ 90% FTP, TSS 62, découplage 6.1%"
```

❌ **Mauvais commit**
```bash
git commit -m "update"
git commit -m "stuff"
```

### Messages Standardisés

```
Format séance:   SXXX-JJ: Type séance, détails
Format semaine:  Bilan hebdomadaire SXXX
Format protocole: Protocol: Nom du protocole ajusté/validé
Format fix:      Fix: Correction erreur dans [fichier]
```

### Fréquence Push

- **Minimum** : 1x/semaine (après bilan hebdo)
- **Recommandé** : Après chaque séance
- **Idéal** : Quotidien (fin de journée)

### Backup Local

Même avec GitHub, garde un backup local :

```bash
# Backup manuel
./scripts/backup.sh ~/Backups/Cyclisme

# Ou automatiser avec cron (Linux/Mac)
# Éditer crontab: crontab -e
# Ajouter: 0 22 * * 0 /chemin/vers/cyclisme-training-logs/scripts/backup.sh
# = Tous les dimanches à 22h
```

---

## 🆘 Troubleshooting

### "Permission denied (publickey)"

**Problème** : Clé SSH non configurée

**Solution** :
```bash
# Générer une clé SSH
ssh-keygen -t ed25519 -C "tonemail@example.com"

# Ajouter la clé à ssh-agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Copier la clé publique
cat ~/.ssh/id_ed25519.pub

# L'ajouter sur GitHub:
# Settings → SSH and GPG keys → New SSH key
```

### "Updates were rejected"

**Problème** : Version locale différente de GitHub

**Solution** :
```bash
# Récupérer les changements depuis GitHub
git pull --rebase origin main

# Résoudre les conflits si nécessaire, puis:
git push
```

### "Merge conflict"

**Problème** : Modifications simultanées du même fichier

**Solution** :
```bash
# Ouvrir le fichier en conflit
vim logs/workouts-history.md

# Chercher les marqueurs:
<<<<<<< HEAD
Ton contenu local
=======
Contenu depuis GitHub
>>>>>>> origin/main

# Garder la bonne version, supprimer les marqueurs

# Finaliser
git add logs/workouts-history.md
git commit -m "Résolution conflit workouts-history"
git push
```

---

## 📚 Ressources

### Documentation Git
- Officielle : https://git-scm.com/doc
- Tutoriel : https://www.atlassian.com/git/tutorials
- Cheatsheet : https://training.github.com/downloads/github-git-cheat-sheet.pdf

### Documentation GitHub
- Guides : https://guides.github.com/
- SSH : https://docs.github.com/en/authentication/connecting-to-github-with-ssh

---

## ✨ Étapes Suivantes

Une fois le setup terminé :

1. [ ] Vérifier que tous les fichiers sont sur GitHub
2. [ ] Tester un commit de séance avec le script
3. [ ] Configurer les scripts comme exécutables :
   ```bash
   chmod +x scripts/*.sh
   ```
4. [ ] Générer les premiers bilans hebdo avec Claude
5. [ ] Établir routine quotidienne (édition logs + commit)

---

**Besoin d'aide ?**

1. Vérifie la section Troubleshooting ci-dessus
2. Consulte la doc Git/GitHub
3. Demande à Claude dans ce chat !

Bon courage ! 🚴‍♂️
