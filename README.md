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

## 🧮 Advanced Metrics & Safety (Sprint R2.1)

### VETO Safety System ⚠️

Protection automatique contre le surmenage pour athlètes master (50+ ans):

```python
from cyclisme_training_logs.rest_and_cancellations import check_pre_session_veto
from cyclisme_training_logs.config import AthleteProfile

# Vérifier avant séance haute intensité (>85% FTP)
wellness = api.get_wellness(oldest=date, newest=date)[0]
profile = AthleteProfile.from_env()

result = check_pre_session_veto(wellness, profile.dict(), session_intensity=95.0)

if result['cancel']:
    print(f"⚠️  VETO: {result['recommendation']}")
    print(f"Facteurs: {result['factors']}")
    # Annuler la séance ou remplacer par Z1 <55% FTP
```

**Déclencheurs VETO** (athlète master 54 ans):
- TSB < -25 (fatigue critique)
- ATL/CTL > 1.8 (surcharge aiguë)
- Sommeil < 5.5h (récupération insuffisante)
- Sommeil < 6h + TSB < -15 (stress combiné)

### Analytics Functions

**6 fonctions avancées** pour analyse métriques (`utils/metrics_advanced.py`):

```python
from cyclisme_training_logs.utils.metrics_advanced import (
    calculate_ramp_rate,
    get_weekly_metrics_trend,
    detect_training_peaks,
    get_recovery_recommendation,
    format_metrics_comparison,
    detect_overtraining_risk
)

# 1. Taux progression CTL (points/semaine)
ramp_rate = calculate_ramp_rate(start_ctl=60, end_ctl=67, days=7)
# Master: max 5-7 pts/semaine recommandé

# 2. Tendance hebdomadaire
trend = get_weekly_metrics_trend(weekly_data, metric='ctl')
# Returns: {'trend': 'rising', 'slope': 2.3, 'volatility': 0.8}

# 3. Détection pics de charge
peaks = detect_training_peaks(ctl_history, threshold_percent=10.0)
# Identifie augmentations significatives (>10% baseline)

# 4. Recommandations récupération
rec = get_recovery_recommendation(tsb=-8, atl_ctl_ratio=1.15, profile)
# Returns: priority (low/medium/high/critical), limits, rest_days

# 5. Comparaison périodes
comparison = format_metrics_comparison(last_week, this_week, 'Week')
# "Week 1 → Week 2: CTL ↑ 3.5 | ATL ↓ 2.1 | TSB → 0.3"

# 6. Détection surmenage (CRITIQUE)
risk = detect_overtraining_risk(ctl, atl, tsb, sleep_hours, profile)
# VETO logic: veto boolean, risk_level, recommendation, factors
```

**Documentation complète:**
- [SPRINT_R2.1_DOCUMENTATION.md](project-docs/sprints/R2/SPRINT_R2.1_DOCUMENTATION.md)
- [GUIDE_INSTALLATION_R2.1.md](project-docs/sprints/R2/GUIDE_INSTALLATION_R2.1.md)
- [VETO_PROTOCOL.md](docs/VETO_PROTOCOL.md)

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
