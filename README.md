# Cyclisme Training Logs - Système Automatisé

Système de suivi d'entraînement cyclisme avec automation Python.

## 🎯 Objectif

Développement FTP 220W → 260W via entraînement indoor structuré.

## 📊 Workflow Quotidien (2.5 min)
```bash
# 1. Capture feedback post-séance (30s)
python scripts/collect_athlete_feedback.py

# 2. Génération prompt analyse (30s)
python scripts/prepare_analysis.py

# 3. Analyse Coach dans Claude.ai (1min)
# Copier-coller le prompt généré

# 4. Injection analyse dans logs (30s)
python scripts/insert_analysis.py
```

## 📁 Structure
```
/project-docs/              → Documentation système (Project Prompt v2.3)
/references/        → Docs externes (Zwift, Intervals.icu)
/scripts/           → Automation Python
/logs/              → Logs entraînement (workouts, metrics, learnings)
/feedback/          → Feedback athlète JSON
```

## 🚀 Versions

- **v2.3** (18/11/2025) : Analyse planifié vs réalisé
- **v2.2** (17/11/2025) : Workflow automation v1.0
- **v2.1** (12/11/2025) : Structure initiale

## 📈 Performance

- Temps documentation : 20min → **2.5min** (-87.5%)
- Détection surmenage : **1-2 séances plus tôt**
- Gain hebdomadaire : **105 min/semaine**

## 🔧 Configuration

### Setup Initial

**1. Installer le code** :
```bash
git clone https://github.com/stephanejouve/cyclisme-training-logs.git
cd cyclisme-training-logs
poetry install
```

**2. Configurer Intervals.icu** :
```bash
cat > ~/.intervals_config.json <<'EOF'
{
  "athlete_id": "iXXXXXX",
  "api_key": "VOTRE_API_KEY"
}
EOF
chmod 600 ~/.intervals_config.json
```

**3. Configurer repo données** (requis) :

Ce projet sépare le **code** (public) des **données d'entraînement** (privées).

```bash
# Créer votre repo données privé
mkdir ~/training-logs
cd ~/training-logs
git init

# Structure minimale
mkdir -p bilans data/week_planning data/workout_templates
touch workouts-history.md metrics-evolution.md

# Lier avec GitHub (repo privé)
git remote add origin https://github.com/VOTRE_USERNAME/training-logs.git
git add .
git commit -m "Initial structure"
git push -u origin main
```

**4. Définir variable d'environnement** :
```bash
# Pour zsh (macOS/Linux par défaut)
echo 'export TRAINING_DATA_REPO=~/training-logs' >> ~/.zshrc
source ~/.zshrc

# Ou pour bash
echo 'export TRAINING_DATA_REPO=~/training-logs' >> ~/.bashrc
source ~/.bashrc
```

**5. Valider l'installation** :
```bash
cd ~/cyclisme-training-logs
poetry run workflow-coach

# Devrait afficher :
# [INFO] Data repo: /Users/vous/training-logs
# ✅ Configuration validée
```

### Migration (Utilisateurs Existants)

Si vous avez déjà des données dans `~/cyclisme-training-logs/logs/`, consultez le guide de migration complet :

**📖 [Guide de Migration](project-docs/MIGRATION_DATA_REPO.md)**

Le guide couvre :
- Backup et restauration des données existantes
- Configuration du nouveau repo données
- Validation et troubleshooting
- Rollback si nécessaire

## 📚 Documentation

- **Migration données/code** : [`project-docs/MIGRATION_DATA_REPO.md`](project-docs/MIGRATION_DATA_REPO.md) 🆕
- Project Prompt actuel : [`project-docs/project-prompt-v2.3.md`](project-docs/project-prompt-v2.3.md)
- Changelog : [`project-docs/CHANGELOG.md`](project-docs/CHANGELOG.md)
