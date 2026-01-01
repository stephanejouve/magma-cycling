# Documentation Projet Cyclisme Training Logs

Documentation complète du système d'entraînement et d'analyse.

## 📚 Guides Principaux

### 🗓️ Planification Entraînement ⭐ NEW
- **[guides/GUIDE_PLANNING.md](guides/GUIDE_PLANNING.md)** : Système de planification (Sprint R3)
  - Création plans 4-12 semaines
  - Gestion objectifs et échéances
  - Validation faisabilité (TSS, CTL)
  - Calendrier hebdomadaire ISO
  - Contraintes master athletes

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

### Créer un Plan d'Entraînement ⭐ NEW

```python
from datetime import date
from cyclisme_training_logs.planning import PlanningManager, PriorityLevel, ObjectiveType

# Initialiser gestionnaire
manager = PlanningManager()

# Créer plan 8 semaines
plan = manager.create_training_plan(
    name="Build Printemps",
    start_date=date(2026, 3, 1),
    end_date=date(2026, 4, 26),  # 8 semaines
    weekly_tss_targets=[250, 270, 290, 310, 320, 300, 280, 250],
    notes="Phase build vers objectif mai"
)

# Ajouter objectif principal
manager.add_deadline(
    plan_name="Build Printemps",
    deadline_date=date(2026, 5, 10),
    event_name="Gran Fondo Alpes",
    priority=PriorityLevel.HIGH,
    objective_type=ObjectiveType.EVENT
)

# Valider faisabilité
validation = manager.validate_plan_feasibility("Build Printemps", current_ctl=55.0)
print(f"Faisable: {validation['feasible']}")
print(f"Erreurs: {validation['errors']}")
```

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

**Version Documentation :** 2.0
**Dernière mise à jour :** 2026-01-01
**Sprint :** R3 - Planning Manager & Calendar
