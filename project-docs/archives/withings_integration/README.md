# Intégration Withings

Synchronisation automatique Withings → Intervals.icu

## Installation
```bash
pip install -r requirements.txt
```

## Configuration
```bash
cp config/.env.example .env.withings
nano .env.withings  # Ajouter le Secret Withings
```

## Utilisation
```bash
# Configuration initiale (une seule fois)
python scripts/withings_setup.py

# Synchronisation quotidienne
python scripts/withings_sync.py sync

# Vérifier disponibilité VO2 max
python scripts/withings_sync.py readiness

# Résumé hebdomadaire
python scripts/withings_sync.py summary
```

Voir `docs/README_WITHINGS.md` pour la documentation complète.
