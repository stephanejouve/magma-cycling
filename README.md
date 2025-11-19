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
/docs/              → Documentation système (Project Prompt v2.3)
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

Créer `.env` :
```bash
VITE_INTERVALS_ATHLETE_ID=your_id
VITE_INTERVALS_API_KEY=your_key
```

## 📚 Documentation

- Project Prompt actuel : [`docs/project-prompt-v2.3.md`](docs/project-prompt-v2.3.md)
- Changelog : [`docs/CHANGELOG.md`](docs/CHANGELOG.md)
