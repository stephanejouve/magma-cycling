# Guide Migration : Séparation Données/Code

## Vue d'ensemble

À partir de la version refactorée, `cyclisme-training-logs` sépare le code (public) des données d'entraînement (privées). Cette architecture permet :

- **Open-sourcing du code** sans exposer vos données personnelles
- **Versionnement séparé** du code et des données
- **Partage facile** du code avec d'autres athlètes
- **Sécurité renforcée** des données sensibles

## Architecture

```
~/cyclisme-training-logs/          # Dépôt CODE (public)
├── cyclisme_training_logs/        # Code Python
├── references/                    # Références d'entraînement
├── tests/                         # Tests unitaires
└── README.md

~/training-logs/                   # Dépôt DONNÉES (privé)
├── workouts-history.md            # Historique séances
├── metrics-evolution.md           # Évolution métriques
├── .workflow_state.json           # État workflow
├── bilans/                        # Analyses hebdomadaires
│   ├── S068/
│   ├── S069/
│   └── S070/
└── data/
    ├── week_planning/             # Plannings hebdomadaires
    └── workout_templates/         # Templates workouts
```

---

## Pour Utilisateurs Existants

Si vous avez déjà utilisé `cyclisme-training-logs` avant cette migration, suivez ces étapes :

### Étape 1 : Sauvegarder données actuelles

```bash
cd ~/cyclisme-training-logs

# Créer backup temporaire
mkdir ~/cyclisme-training-logs-backup
cp logs/workouts-history.md ~/cyclisme-training-logs-backup/
cp logs/metrics-evolution.md ~/cyclisme-training-logs-backup/ 2>/dev/null || true
cp -r logs/bilans ~/cyclisme-training-logs-backup/ 2>/dev/null || true
cp -r data ~/cyclisme-training-logs-backup/ 2>/dev/null || true
cp .workflow_state.json ~/cyclisme-training-logs-backup/ 2>/dev/null || true

echo "✅ Backup créé dans ~/cyclisme-training-logs-backup"
```

### Étape 2 : Mettre à jour code

```bash
cd ~/cyclisme-training-logs
git pull origin main
poetry install
```

### Étape 3 : Créer repo données

**Option A : Créer nouveau repo privé sur GitHub**

```bash
# Sur GitHub.com :
# 1. New repository
# 2. Nom : training-logs
# 3. ✅ Private
# 4. Ne pas initialiser avec README

# Localement :
cd ~
mkdir training-logs
cd training-logs
git init
git remote add origin https://github.com/VOTRE_USERNAME/training-logs.git

# Créer structure
mkdir -p bilans data/week_planning data/workout_templates
touch workouts-history.md
echo "# Logs d'Entraînement Cyclisme" > README.md
```

**Option B : Utiliser repo existant**

```bash
cd ~
git clone https://github.com/VOTRE_USERNAME/training-logs.git
```

### Étape 4 : Restaurer données

```bash
# Copier données depuis backup
cp ~/cyclisme-training-logs-backup/workouts-history.md ~/training-logs/
cp ~/cyclisme-training-logs-backup/metrics-evolution.md ~/training-logs/ 2>/dev/null || true

# Copier bilans si présents
if [ -d ~/cyclisme-training-logs-backup/bilans ]; then
    cp -r ~/cyclisme-training-logs-backup/bilans ~/training-logs/
fi

# Copier data si présent
if [ -d ~/cyclisme-training-logs-backup/data ]; then
    cp -r ~/cyclisme-training-logs-backup/data ~/training-logs/
fi

# Copier workflow state
cp ~/cyclisme-training-logs-backup/.workflow_state.json ~/training-logs/ 2>/dev/null || true

# Commiter
cd ~/training-logs
git add .
git commit -m "Import données existantes"
git push -u origin main

echo "✅ Données restaurées dans ~/training-logs"
```

### Étape 5 : Configurer variable d'environnement

**Pour zsh (macOS/Linux par défaut)** :

```bash
echo 'export TRAINING_DATA_REPO=~/training-logs' >> ~/.zshrc
source ~/.zshrc
```

**Pour bash** :

```bash
echo 'export TRAINING_DATA_REPO=~/training-logs' >> ~/.bashrc
source ~/.bashrc
```

**Vérifier configuration** :

```bash
echo $TRAINING_DATA_REPO
# Devrait afficher : /Users/vous/training-logs
```

### Étape 6 : Valider migration

```bash
cd ~/cyclisme-training-logs
poetry run workflow-coach

# Devrait afficher au démarrage :
# [INFO] Data repo: /Users/vous/training-logs
# [INFO] Workouts history: /Users/vous/training-logs/workouts-history.md
```

**Tests complets** :

```bash
# Test 1 : Lire historique
poetry run python -c "
from cyclisme_training_logs.config import get_data_config
config = get_data_config()
print(f'✅ Config OK: {config.workouts_history_path}')
"

# Test 2 : Vérifier workflow state
ls -la ~/training-logs/.workflow_state.json

# Test 3 : Workflow complet (mode test)
poetry run workflow-coach --skip-feedback --skip-git
```

### Étape 7 : Nettoyer backup (optionnel)

```bash
# SEULEMENT après validation complète !
rm -rf ~/cyclisme-training-logs-backup
echo "✅ Backup supprimé"
```

---

## Pour Nouveaux Utilisateurs

Si c'est votre première installation :

### 1. Cloner le code

```bash
git clone https://github.com/stephanejouve/cyclisme-training-logs.git
cd cyclisme-training-logs
poetry install
```

### 2. Créer votre repo données

```bash
cd ~
mkdir training-logs
cd training-logs
git init

# Structure minimale
mkdir -p bilans data/week_planning data/workout_templates
touch workouts-history.md
touch metrics-evolution.md
echo "# Mes Logs d'Entraînement" > README.md

# Premier commit
git add .
git commit -m "Initial structure"

# Push vers GitHub (repo privé créé au préalable)
git remote add origin https://github.com/VOTRE_USERNAME/training-logs.git
git push -u origin main
```

### 3. Configurer variable d'environnement

```bash
echo 'export TRAINING_DATA_REPO=~/training-logs' >> ~/.zshrc
source ~/.zshrc
```

### 4. Configurer Intervals.icu

```bash
cat > ~/.intervals_config.json <<'EOF'
{
  "athlete_id": "iXXXXXX",
  "api_key": "VOTRE_API_KEY"
}
EOF

chmod 600 ~/.intervals_config.json
```

### 5. Premier workflow

```bash
cd ~/cyclisme-training-logs
poetry run workflow-coach
```

---

## Troubleshooting

### Erreur : "Data repo not found"

**Symptôme** :
```
FileNotFoundError: Data repo not found: /Users/vous/training-logs
Set TRAINING_DATA_REPO env var or clone...
```

**Solutions** :

1. Vérifier variable d'environnement :
```bash
echo $TRAINING_DATA_REPO
# Si vide ou incorrect :
export TRAINING_DATA_REPO=~/training-logs
```

2. Vérifier que le repo existe :
```bash
ls -la ~/training-logs
# Si n'existe pas, créer la structure (voir section "Nouveaux Utilisateurs")
```

3. Rendre permanent (ajouter à shell config) :
```bash
echo 'export TRAINING_DATA_REPO=~/training-logs' >> ~/.zshrc
source ~/.zshrc
```

### Erreur : "workouts-history.md not found"

**Symptôme** :
```
FileNotFoundError: workouts-history.md not found in data repo
```

**Solution** :
```bash
touch ~/training-logs/workouts-history.md
cd ~/training-logs
git add workouts-history.md
git commit -m "Create workouts-history.md"
git push
```

### Tests échouent après migration

**Symptôme** :
```
Tests fail with FileNotFoundError in data repo
```

**Explication** : Les tests utilisent un repo temporaire, pas votre repo réel.

**Solution** :
```bash
# Vérifier tests unitaires passent en isolation
poetry run pytest tests/test_data_config.py -v

# Si tests workflow échouent, vérifier mocks :
poetry run pytest -v --tb=short
```

### Workflow ne trouve pas les fichiers

**Symptôme** :
Le workflow démarre mais ne trouve pas workouts-history.md ou .workflow_state.json

**Diagnostic** :
```bash
python3 -c "
from cyclisme_training_logs.config import get_data_config
config = get_data_config()
print('Data repo:', config.data_repo_path)
print('Workouts:', config.workouts_history_path)
print('Exists:', config.workouts_history_path.exists())
"
```

**Solution** :
Vérifier que tous les fichiers nécessaires existent dans training-logs :
```bash
cd ~/training-logs
ls -la workouts-history.md .workflow_state.json
```

### Migration incomplète

**Symptôme** :
Certaines données dans cyclisme-training-logs, d'autres dans training-logs

**Solution** :
```bash
# Identifier fichiers à migrer
cd ~/cyclisme-training-logs
find logs/ -name "*.md" -o -name "*.json"

# Copier vers training-logs
cp logs/workouts-history.md ~/training-logs/
cp -r logs/bilans ~/training-logs/
cp .workflow_state.json ~/training-logs/

# Commiter dans training-logs
cd ~/training-logs
git add .
git commit -m "Complete data migration"
git push
```

---

## Rollback (Retour en arrière)

Si la migration pose problème, vous pouvez revenir à l'ancien système :

```bash
# 1. Checkout commit avant migration
cd ~/cyclisme-training-logs
git log --oneline | head -10  # Trouver commit avant refactor
git checkout <commit-hash>

# 2. Restaurer données depuis training-logs
cp ~/training-logs/workouts-history.md logs/
cp ~/training-logs/.workflow_state.json .
cp -r ~/training-logs/bilans logs/

# 3. Réinstaller dépendances
poetry install

# 4. Tester
poetry run workflow-coach
```

---

## Support

- **Issues GitHub** : https://github.com/stephanejouve/cyclisme-training-logs/issues
- **Documentation** : Voir README.md et docs/
- **Contact** : Créer une issue avec tag `[migration]`

---

## Checklist Migration

- [ ] Backup données créé (~/cyclisme-training-logs-backup)
- [ ] Code mis à jour (git pull + poetry install)
- [ ] Repo training-logs créé (local + GitHub privé)
- [ ] Données restaurées dans training-logs
- [ ] Variable TRAINING_DATA_REPO configurée (dans ~/.zshrc ou ~/.bashrc)
- [ ] Premier workflow réussi (poetry run workflow-coach)
- [ ] Tests unitaires passent (poetry run pytest tests/test_data_config.py)
- [ ] Backup nettoyé (APRÈS validation complète)

**Migration réussie** ✅
