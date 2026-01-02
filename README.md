# Cyclisme Training Logs

Système automatisé d'analyse et de planification d'entraînements cyclisme avec intelligence artificielle.

## Installation

```bash
cd ~/cyclisme-training-logs
poetry install
```

## Configuration

### Intervals.icu (Optionnel)

Pour la synchronisation avec Intervals.icu, configurer les variables d'environnement:

```bash
export INTERVALS_ATHLETE_ID="i123456"
export INTERVALS_API_KEY="your_api_key"
```

Ajouter au `~/.zshrc` ou `~/.bashrc` pour persistance.

## Commandes Principales

### Planification
```bash
poetry run weekly-planner --week S074 --start-date 2025-12-29
```

### Analyse Hebdomadaire
```bash
poetry run weekly-analysis --week 67
```

### Upload Workouts
```bash
poetry run upload-workouts workouts/S074-01.zwo
```

### Gestion Séances
```bash
# Annuler une séance (local uniquement)
poetry run update-session --week S074 --session S074-05 --status cancelled --reason "Fatigue"

# Annuler et synchroniser avec Intervals.icu (convertit en NOTE [ANNULÉE])
poetry run update-session --week S074 --session S074-05 --status cancelled --reason "Fatigue" --sync

# Sauter une séance avec synchronisation
poetry run update-session --week S074 --session S074-03 --status skipped --reason "Voyage" --sync

# Marquer comme complétée
poetry run update-session --week S074 --session S074-01 --status completed
```

## Documentation

Documentation complète disponible dans `project-docs/`:
- **[GUIDE_PLANNING.md](project-docs/guides/GUIDE_PLANNING.md)** - Planification entraînement
- **[GUIDE_INTELLIGENCE.md](project-docs/guides/GUIDE_INTELLIGENCE.md)** - Système d'apprentissage
- **[CHANGELOG.md](project-docs/CHANGELOG.md)** - Historique versions

## Version

**v2.1.1** - Intervals.icu Sync Fix (2026-01-02)
- Fixed: Session cancellation converts to NOTE instead of deleting
- Previous: **v2.1.0** - Sprint R4 (Training Intelligence & Feedback Loop)

## License

Propriétaire - Usage personnel
